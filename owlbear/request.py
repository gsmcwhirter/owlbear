# -*- coding: utf-8 -*-
"""Classes wrapping ASGI requests in a nicer interface"""

import http.cookies
import re
from typing import Tuple
import urllib.parse


class FormDataError(Exception):
    """Represents an error handling form data"""
    pass


class RequestData:
    """Simple object container for attaching data to a request"""
    pass


# parts from https://github.com/defnull/multipart/blob/master/multipart.py
# MIT license Copyright (c) 2010, Marcel Hellkamp
_special = re.escape('()<>@,;:\\"/[]?={} \t')
_re_special = re.compile('[%s]' % _special)
_qstr = '"(?:\\\\.|[^"])*"'
_value = '(?:[^%s]+|%s)' % (_special, _qstr)
_option = '(?:;|^)\s*([^%s]+)\s*=\s*(%s)' % (_special, _value)
_re_option = re.compile(_option) # key=value part of an Content-Type like header


class Request:
    """Class to wrap an ASGI request"""

    __slots__ = (
        'app', 'raw_request', 'data', '_headers',
        '_body', '_body_channel', '_query_args',
        '_form_values', '_form_files', '_form_parsed',
        '_cookies', )

    def __init__(self, app: 'owlbear.app.Owlbear', raw_request: dict, body_channel=None):
        self.app = app
        self.raw_request = raw_request
        self.data = RequestData()
        self._headers: dict = None
        self._body_channel = body_channel
        self._body = None
        self._query_args = None
        self._form_values = None
        self._form_files = None
        self._form_parsed = False
        self._cookies = None

    def __str__(self):
        return f"{self.method} {self.path}"

    @property
    def path(self) -> str:
        """Return the request uri_path"""
        return self.raw_request.get('path')

    @property
    def query_string(self) -> str:
        """Return the request query string"""
        return self.raw_request.get('query_string').decode()

    @staticmethod
    def _fix_query_args(query_args):
        for key in query_args.keys():
            if not key.endswith("[]"):
                if len(query_args[key]) == 1:
                    query_args[key] = query_args[key][0]
                elif len(query_args[key]) == 0:
                    query_args[key] = ''

    @property
    def query_args(self) -> dict:
        """Return the parsed query string args"""
        if self._query_args is None:
            if self.query_string is not None:
                self._query_args = urllib.parse.parse_qs(self.query_string, keep_blank_values=True)
            else:
                self._query_args = {}

            self._fix_query_args(self._query_args)

        return self._query_args

    @property
    def cookies(self) -> dict:
        """Return cookie values"""
        if self._cookies is None:
            self._cookies = {}
            cookie_header = self.headers.get('cookie')
            if cookie_header:
                cookie_parser = http.cookies.SimpleCookie(cookie_header)
                for key, morsel in cookie_parser.items():
                    self._cookies[key] = morsel.value

        return self._cookies

    @staticmethod
    def _header_unquote(val, filename=False):
        if val[0] == val[-1] == '"':
            val = val[1:-1]
            if val[1:3] == ':\\' or val[:2] == '\\\\':
                val = val.split('\\')[-1]  # fix ie6 bug: full path --> filename
            return val.replace('\\\\', '\\').replace('\\"', '"')

        return val

    @classmethod
    def _parse_options_header(cls, header: str, options=None) -> Tuple[str, dict]:
        if ';' not in header:
            return header.lower().strip(), {}

        ctype, tail = header.split(';', 1)
        options = options or {}

        for match in _re_option.finditer(tail):
            key = match.group(1).lower()
            value = cls._header_unquote(match.group(2), key=='filename')
            options[key] = value

        return ctype, options

    async def parse_form(self, *, charset='utf8'):
        if self._form_parsed:
            return

        # TODO: files
        form_data, files = {}, {}

        if self.method not in ('POST', 'PUT'):
            raise FormDataError("Request method other than POST or PUT.")

        try:
            content_length = int(self.headers.get('content-length'))
        except TypeError:
            content_length = -1

        content_type = self.headers.get('content-type', '')
        if not content_type:
            raise FormDataError("Missing Content-Type header.")

        content_type, options = self._parse_options_header(content_type)
        charset = options.get('charset', charset)

        if content_type == 'multipart/form-data':
            pass
            # boundary = options.get('boundary', '')
            # if not boundary:
            #     raise MultipartError("No boundary for multipart/form-data.")
            # for part in MultipartParser(stream, boundary, content_length, **kw):
            #     if part.filename or not part.is_buffered():
            #         files[part.name] = part
            #     else:  # TODO: Big form-fields are in the files dict. really?
            #         forms[part.name] = part.value
        elif content_type in ('application/x-www-form-urlencoded',
                              'application/x-url-encoded'):

            form_data_raw = await self.read_body(encoding=charset)
            form_data = urllib.parse.parse_qs(form_data_raw, keep_blank_values=True)
            self._fix_query_args(form_data)
        else:
            raise FormDataError("Unsupported content type.")

        self._form_values, self._form_files = form_data, files
        self._form_parsed = True

    @property
    def form(self) -> dict:
        """Return the parsed form data, if any"""
        if self._form_values is None:
            raise FormDataError("You must call request.parse_form first")

        return self._form_values

    @property
    def host(self) -> str:
        """Return the request host"""
        return self.headers.get('host')

    @property
    def scheme(self) -> str:
        """Return the request scheme"""
        return self.raw_request.get('scheme')

    @property
    def method(self) -> str:
        """Return the request verb"""
        return self.raw_request.get('method').upper()

    @property
    def headers(self) -> dict:
        """Return the request headers"""
        if self._headers is None:
            self._headers = {}
            for header_name, header_val in self.raw_request.get('headers', []):
                header_name = header_name.decode('ascii').lower()
                header_val = header_val.decode('ascii')
                self._headers[header_name] = header_val

        return self._headers

    async def read_body(self, encoding=None):
        """Read the request body, if there is one"""
        if self._body is None:
            self._body = self.raw_request.get('body', b'')
            if self._body_channel:
                while True:
                    chunk = await self._body_channel.receive()
                    self._body += chunk['content']
                    if not chunk.get('more_content'):
                        break

        if encoding:
            return self._body.decode(encoding)
        else:
            return self._body

