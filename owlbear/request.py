# -*- coding: utf-8 -*-
"""Classes wrapping ASGI requests in a nicer interface"""

import http.cookies
import urllib.parse

class RequestData:
    """Simple object container for attaching data to a request"""
    pass


class Request:
    """Class to wrap an ASGI request"""

    __slots__ = ('app', 'raw_request', 'data', '_headers', '_body', '_body_channel', '_query_args', '_form_values', '_cookies', )

    def __init__(self, app: 'owlbear.app.Owlbear', raw_request: dict, body_channel=None):
        self.app = app
        self.raw_request = raw_request
        self.data = RequestData()
        self._headers: dict = None
        self._body_channel = body_channel
        self._body = None
        self._query_args = None
        self._form_values = None
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
        return self.raw_request.get('query_string')

    @property
    def query_args(self) -> dict:
        """Return the parsed query string args"""
        if self._query_args is None:
            if self.query_string is not None:
                self._query_args = urllib.parse.parse_qs(self.query_string, keep_blank_values=True)
            else:
                self._query_args = {}

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

    @property
    def form(self) -> dict:
        """Return the parsed form data, if any"""
        # TODO
        return {}

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

