
class RequestData:
    pass


class Request:

    __slots__ = ('app', 'raw_request', 'data', '_headers', '_body', '_body_channel', )

    def __init__(self, app, raw_request: dict, body_channel=None):
        self.app = app  # type: owlbear.app.Owlbear
        self.raw_request = raw_request
        self.data = RequestData()
        self._headers: dict = None
        self._body_channel = body_channel
        self._body = None

    @property
    def path(self) -> str:
        return self.raw_request.get('path')

    @property
    def scheme(self) -> str:
        return self.raw_request.get('scheme')

    @property
    def method(self) -> str:
        return self.raw_request.get('method').upper()

    @property
    def headers(self) -> dict:
        if self._headers is None:
            self._headers = {}
            for header_name, header_val in self.raw_request.get('headers', []):
                header_name = header_name.decode('ascii')
                header_val = header_val.decode('ascii')
                self._headers[header_name] = header_val

        return self._headers

    async def read_body(self, encoding=None):
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

