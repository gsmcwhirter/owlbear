# -*- coding: utf-8 -*-
from typing import Callable, Optional, Union

from owlbear.exceptions import default_exception_handler, ExceptionHandler, ExceptionTypes
from owlbear.request import Request
from owlbear.router import Methods, Middleware, RequestHandler, Router


class Owlbear:

    def __init__(self):
        self.router = Router()
        self.exception_handlers = []

    async def __call__(self, message, channels):
        request = Request(self, message, channels.get('body'))

        try:
            response = await self.router.dispatch(request)
        except Exception as e:
            for exception_types, handler in reversed(self.exception_handlers):
                if isinstance(e, exception_types):
                    response = await handler(request, e)

                    if response is not None:
                        break
            else:
                response = await default_exception_handler(request, e)

        await response.send_to(channels['reply'])

    def add_route(self, uri_path: str, handler: RequestHandler, methods: Methods=('GET', )):
        self.router.add_route(uri_path=uri_path, handler=handler, methods=methods)

    def register_middleware(self, middleware: Middleware):
        self.router.register_middleware(middleware=middleware)

    def register_exception_handler(self, exception_types: ExceptionTypes, handler: ExceptionHandler):
        self.exception_handlers.append((exception_types, handler))

    def route(self, uri_path: str, methods: Methods=('GET', )) -> Callable[[RequestHandler], RequestHandler]:

        def wrapper(handler: RequestHandler) -> RequestHandler:
            self.add_route(uri_path=uri_path, handler=handler, methods=methods)
            return handler

        return wrapper

    def middleware(self, mw: Optional[Middleware]=None) -> Union[Middleware, Callable[[Middleware], Middleware]]:

        if mw is not None:
            self.register_middleware(mw)
            return mw

        def wrapper(middleware: Middleware) -> Middleware:
            self.register_middleware(middleware)
            return middleware

        return wrapper

    def exception_handler(self, exception_types: ExceptionTypes) -> Callable[[ExceptionHandler], ExceptionHandler]:

        def wrapper(exception_handler: ExceptionHandler) -> ExceptionHandler:
            self.register_exception_handler(exception_types, exception_handler)
            return exception_handler

        return wrapper


    def attach(self, app, base_path: str="/"):
        self.router.attach(app.router, base_path)
