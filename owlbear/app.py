
from owlbear.request import Request
from owlbear.response import Response
from owlbear.router import Methods, Middleware, RequestHandler, Router


def html_response(content: str, status=200) -> Response:
    # TODO
    return Response()


def json_response(content: dict, status=200) -> Response:
    # TODO
    return Response()


class Owlbear:

    def __init__(self):
        self.router = Router()

    async def __call__(self, message, channels):
        # TODO: parse message into request -- more? at least check...
        request = Request(self, message, channels.get('body'))
        response = await self.router.dispatch(request)
        await response.send_to(channels['reply'])

    def add_route(self, uri_path: str, handler: RequestHandler, methods: Methods=('GET', )):
        self.router.add_route(uri_path=uri_path, handler=handler, methods=methods)

    def register_middleware(self, middleware: Middleware):
        self.router.register_middleware(middleware=middleware)

    def route(self, uri_path: str, methods: Methods=('GET', )):

        def wrapper(handler: RequestHandler) -> RequestHandler:
            self.add_route(uri_path=uri_path, handler=handler, methods=methods)
            return handler

        return wrapper

    def middleware(self):

        def wrapper(middleware: Middleware) -> Middleware:
            self.register_middleware(middleware)
            return middleware

        return wrapper

    def attach(self, app, base_path: str="/"):
        self.router.attach(app.router, base_path)
