# -*- coding: utf-8 -*-
"""Classes to handle composing and sending an ASGI response"""
from collections import defaultdict
from datetime import datetime
import http.cookies
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

try:
    import ujson as json
except ImportError:
    import json


class Cookie(NamedTuple):
    """Represents a cookie"""
    name: str
    value: str
    expires: Optional[datetime] = None
    max_age: Optional[int] = None
    domain: Optional[str] = None
    path: Optional[str] = "/"
    secure: bool = True
    http_only: bool = True
    same_site: Optional[str] = "Strict"  # TODO: support this

    def load_into_parser(self, cookie_parser: http.cookies.BaseCookie):
        cookie_parser[self.name] = self.value
        if self.expires:
            cookie_parser[self.name]['expires'] = self.expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        if self.path:
            cookie_parser[self.name]['path'] = self.path
        if self.domain:
            cookie_parser[self.name]['domain'] = self.domain
        if self.max_age:
            cookie_parser[self.name]['max-age'] = self.max_age
        if self.secure:
            cookie_parser[self.name]['secure'] = self.secure
        if self.http_only:
            cookie_parser[self.name]['httponly'] = self.http_only


class ResponseError(Exception):
    """Represents an error composing a response"""
    pass


class Response:
    """Interface to compose and send an ASGI response"""

    __slots__ = ('_headers', '_content', 'status', '_cookies', 'content_type', '_charset', '_headers_sent', '_done', "_full_response", )

    def __init__(self):
        self.status = 200
        self.content_type = 'text/plain'
        self._headers = defaultdict(list)
        self._cookies = {}
        self._content = b''
        self._charset = None
        self._headers_sent = False
        self._done = False
        self._full_response = None

    @staticmethod
    def _encode_if_necessary(str_or_bytes: Union[str, bytes], encoding: str='ascii') -> bytes:
        if isinstance(str_or_bytes, bytes):
            return str_or_bytes
        else:
            return str_or_bytes.encode(encoding)

    def _form_full_response(self) -> dict:
        if self._full_response is None:
            resp = self._form_header_response()
            resp.update(self._form_content_response(self._content), done=True)

            self._full_response = resp

        return self._full_response

    def _form_header_response(self):
        headers = []

        for header_name, header_vals in self._headers.items():
            header_name = header_name.lower().encode('ascii')
            for header_val in header_vals:
                header_val = self._encode_if_necessary(header_val, 'ascii')

                headers.append((header_name, header_val))

        cookie_parser = http.cookies.SimpleCookie()
        for cookie_name, cookie in self._cookies.items():
            cookie.load_into_parser(cookie_parser)

        for cookie_name, morsel in cookie_parser.items():
            cookie_val = morsel.OutputString()
            if self._cookies[cookie_name].same_site is not None:
                cookie_val += "; SameSite={}".format(self._cookies[cookie_name].same_site)

            headers.append((b'set-cookie', self._encode_if_necessary(cookie_val)))

        content_type_val = self._encode_if_necessary(self.content_type)
        if self._charset:
            content_type_val += b"; charset=" + self._encode_if_necessary(self._charset)
        headers.append((b'content-type', content_type_val))

        return {
            'status': self.status,
            'headers': headers
        }

    @staticmethod
    def _form_content_response(content: bytes, done: bool=True) -> dict:
        return {
            'content': content,
            'more_content': not done
        }

    def set_cookie(self, cookie: Cookie):
        """Add a cookie to the list that will be returned in the response"""
        self._cookies[cookie.name] = cookie

    def set_content(self, content: Union[str, bytes], encoding: Optional[Union[str, bytes]]='utf-8'):
        """Set the response content"""

        if not isinstance(content, bytes):
            self._content = content.encode(encoding)
        else:
            self._content = content

        self._charset = encoding

    def add_header(self, header_name: str, header_val: str):
        """Add a header to the response"""
        self._headers[header_name.lower()].append(header_val)

    def clear_headers(self, header_name: Optional[str]):
        """Clear one or all headers"""
        if header_name is not None:
            self._headers[header_name.lower()] = []
        else:
            self._headers = defaultdict(list)

    async def stream_to(self, channel, content: bytes, done: bool=False):
        """Stream the response to an ASGI channel"""
        if self._done:
            raise ResponseError("A full response has already been sent.")

        resp = self._form_content_response(content, done=done)
        if not self._headers_sent:
            resp.update(self._form_header_response())

        await channel.send(resp)
        if done:
            self._done = True

    async def send_to(self, channel):
        """Send the response, in full, to an ASGI channel"""
        if self._headers_sent:
            raise ResponseError("A set of response headers has already been sent.")

        if self._done:
            raise ResponseError("A full response has already been sent.")

        resp = self._form_full_response()
        self._headers_sent = True
        self._done = True
        await channel.send(resp)


def text_response(content: str, status: int=200, headers: Optional[Union[Dict[str, str], List[Tuple[str, str]]]]=None) -> Response:
    """Wrapper to send a text response"""
    resp = Response()
    resp.status = status
    resp.content_type = "text/plain"
    resp.set_content(content)

    if headers:
        if isinstance(headers, dict):
            for hname, hval in headers.items():
                resp.add_header(hname, hval)
        else:
            for hname, hval in headers:
                resp.add_header(hname, hval)

    return resp


def html_response(content: str, status: int=200, headers: Optional[Union[Dict[str, str], List[Tuple[str, str]]]]=None) -> Response:
    """Wrapper to send an html response"""
    resp = Response()
    resp.status = status
    resp.content_type = "text/html"
    resp.set_content(content)

    if headers:
        if isinstance(headers, dict):
            for hname, hval in headers.items():
                resp.add_header(hname, hval)
        else:
            for hname, hval in headers:
                resp.add_header(hname, hval)

    return resp


def json_response(content: dict, status: int=200, headers: Optional[Union[Dict[str, str], List[Tuple[str, str]]]]=None) -> Response:
    """Wrapper to send a json response"""
    resp = Response()
    resp.status = status
    resp.content_type = "application/json"
    resp.set_content(json.dumps(content))

    if headers:
        if isinstance(headers, dict):
            for hname, hval in headers.items():
                resp.add_header(hname, hval)
        else:
            for hname, hval in headers:
                resp.add_header(hname, hval)

    return resp


def redirect_response(location: str, permanent: bool=False, headers: Optional[Union[Dict[str, str], List[Tuple[str, str]]]]=None) -> Response:
    """Issue a redirect to a new url"""

    resp = Response()
    if permanent:
        resp.status = 301
    else:
        resp.status = 302

    resp.set_content("Moved to {}".format(location))
    resp.add_header("location", location)

    if headers:
        if isinstance(headers, dict):
            for hname, hval in headers.items():
                resp.add_header(hname, hval)
        else:
            for hname, hval in headers:
                resp.add_header(hname, hval)

    return resp
