
from collections import defaultdict
from datetime import datetime
from typing import NamedTuple, Optional, Union

class Cookie(NamedTuple):
    name: str
    value: str
    expires: Optional[datetime] = None
    max_age: Optional[int] = None
    domain: Optional[str] = None
    path: Optional[str] = "/"
    secure: bool = True
    http_only: bool = True
    same_site: Optional[str] = "Strict"

    def formatted(self) -> str:
        extras = []
        if self.expires is not None:
            extras.append("Expires={}")

        if self.max_age is not None:
            extras.append("Max-Age={}".format(self.max_age))

        if self.domain is not None:
            extras.append("Domain={}".format(self.domain))

        if self.path is not None:
            extras.append("Path={}".format(self.path))

        if self.secure:
            extras.append("Secure")

        if self.http_only:
            extras.append("HttpOnly")

        if self.same_site is not None:
            extras.append("SameSite={}".format(self.same_site))

        extras_str = ""
        if extras:
            extras_str = "; {}".format("; ".join(extras))

        formatted = "{name}={value}{extras}".format(
            name=self.name,
            value=self.value,
            extras=extras_str,
        )

        return formatted


class ResponseError(Exception):
    pass


class Response:

    __slots__ = ('_headers', '_content', 'status', '_cookies', 'content_type', '_charset', '_headers_sent', '_done', )

    def __init__(self):
        self.status = 200
        self.content_type = 'text/plain'
        self._headers = defaultdict(list)
        self._cookies = {}
        self._content = b''
        self._charset = None
        self._headers_sent = False
        self._done = False

    @staticmethod
    def _encode_if_necessary(str_or_bytes: Union[str, bytes], encoding: str='ascii') -> bytes:
        if isinstance(str_or_bytes, bytes):
            return str_or_bytes
        else:
            return str_or_bytes.encode(encoding)

    def _form_full_response(self) -> dict:
        resp = self._form_header_response()
        resp.update(self._form_content_response(self._content), done=True)

        return resp

    def _form_header_response(self):
        headers = []

        for header_name, header_vals in self._headers.items():
            header_name = header_name.lower().encode('ascii')
            for header_val in header_vals:
                header_val = self._encode_if_necessary(header_val, 'ascii')

                headers.append((header_name, header_val))

        for cookie in self._cookies:
            headers.append((b'set-cookie', self._encode_if_necessary(cookie.formatted(), 'ascii')))

        content_type_val = self._encode_if_necessary(self.content_type)
        if self._charset:
            content_type_val += b"; charset=" + self._encode_if_necessary(self._charset)
        headers.append((b'content-type', content_type_val))

        return {
            'status': self.status,
            'headers': headers
        }

    def _form_content_response(self, content: bytes, done: bool=True) -> dict:
        return {
            'content': content,
            'more_content': not done
        }

    def set_cookie(self, cookie: Cookie):
        self._cookies[cookie.name] = cookie

    def set_content(self, content: Union[str, bytes], encoding: Union[str, bytes]='utf-8'):
        if isinstance(content, str):
            self._content = content.encode(encoding)
        else:
            self._content = content

        self._charset = encoding

    async def stream_to(self, channel, content: bytes, done: bool=False):
        if self._done:
            raise ResponseError("A full response has already been sent.")

        resp = self._form_content_response(content, done=done)
        if not self._headers_sent:
            resp.update(self._form_header_response())

        await channel.send(resp)
        if done:
            self._done = True

    async def send_to(self, channel):
        if self._headers_sent:
            raise ResponseError("A set of response headers has already been sent.")

        if self._done:
            raise ResponseError("A full response has already been sent.")

        resp = self._form_full_response()
        self._headers_sent = True
        self._done = True
        await channel.send(resp)