import asyncio

from uvicorn.protocols.http import HttpProtocol

class MockLoop(object):
    def create_task(self, *args):
        pass


class MockTransport(object):
    content = b''
    closed = False

    def close(self):
        self.closed = True

    def write(self, content):
        self.content += content

    def get_extra_info(self, name):
        if name == 'sockname':
            return ('127.0.0.1', 8000)
        elif name == 'peername':
            return ('123.456.789.0', 1234)
        return None


def mock_consumer(message, channels):
    pass


def get_protocol():
    loop = MockLoop()
    transport = MockTransport()
    protocol = HttpProtocol(mock_consumer, loop)
    protocol.connection_made(transport)
    return protocol


def run_coroutine(coroutine):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine)


def read_body(message, channels):
    body = message.get('body', b'')
    if 'body' in channels:
        while True:
            message_chunk = run_coroutine(channels['body'].receive())
            body += message_chunk['content']
            if not message_chunk.get('more_content', False):
                break
    return body


def make_coroutine(mock):
    async def coroutine(*args, **kwargs):
        return mock(*args, **kwargs)
    return coroutine
