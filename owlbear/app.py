# -*- coding: utf-8 -*-
"""The main app server class"""
import logging
import pprint
from typing import Callable, List, Optional, Union

from owlbear.exceptions import default_exception_handler
from owlbear.logging import setup_logger
from owlbear.request import Request
from owlbear.router import Router
from owlbear.types import ExceptionHandler, ExceptionTypes, Methods, Middleware, RequestHandler


class Owlbear:
    """The main app server class"""

    def __init__(self, *, logger: Optional[logging.Logger]=None):
        self.logger = logger or setup_logger("owlbear")
        self.router = Router(logger=logger)
        self.exception_handlers = []

    async def __call__(self, message, channels):
        """The uvicorn interface"""
        request = Request(self, message, channels.get('body'))
        self.logger.debug("Request", raw_data=pprint.pformat(request.raw_request))

        try:
            response = await self.router.dispatch(request)
            self.logger.debug("Response", raw_data=pprint.pformat(response._form_full_response()))
            await response.send_to(channels['reply'])
        except Exception as e:
            for exception_types, handler in reversed(self.exception_handlers):
                if isinstance(e, exception_types):
                    response = await handler(request, e)

                    if response is not None:
                        break
            else:
                response = await default_exception_handler(request, e)

            self.logger.debug("Response", raw_data=pprint.pformat(response._form_full_response()))
            await response.send_to(channels['reply'])

    def url_for(self, handler_name: str, method: str='GET', param_args: Optional[dict]=None) -> str:
        """

        Args:
            handler_name ():
            method ():
            param_args ():

        Returns:

        """
        return self.router.url_for(handler_name=handler_name, method=method, param_args=param_args)

    def add_route(self, uri_path: str, handler: RequestHandler, methods: Methods=('GET', )):
        """Add a route handler to the app

        Args:
            uri_path (str): the path for the route. You can use <var_name: var_type>
                            placeholders as path components for path-based parameters
            handler (RequestHandler): the handler function
            methods (Iterable of str): the http verbs that the handler responds to

        """
        self.router.add_route(uri_path=uri_path, handler=handler, methods=methods)

    def register_middleware(self, middleware: Middleware):
        """Add a middleware handler that will wrap all request handlers

        Args:
            middleware (Middleware): the middleware function
        """
        self.router.register_middleware(middleware=middleware)

    def register_exception_handler(self, exception_types: ExceptionTypes, handler: ExceptionHandler):
        """Add a handler to catch and handle exceptions

        Args:
            exception_types (ExceptionTypes): the types of exceptions this handler catches (in the style of isinstance)
            handler (ExceptionHandler): the function to handle the exception
        """
        self.exception_handlers.append((exception_types, handler))

    def route(self, uri_path: str, methods: Methods=('GET', )) -> Callable[[RequestHandler], RequestHandler]:
        """Decorator that wraps add_route

        Args:
            uri_path (str): the path for the route. You can use <var_name: var_type>
                            placeholders as path components for path-based parameters
            methods (Iterable of str): the http verbs that the handler responds to
        """
        def _wrapper(handler: RequestHandler) -> RequestHandler:
            self.add_route(uri_path=uri_path, handler=handler, methods=methods)
            return handler

        return _wrapper

    def middleware(self, mw: Optional[Middleware]=None) -> Union[Middleware, Callable[[Middleware], Middleware]]:
        """Decorator that wraps register_middleware

        Args:
            mw (Middleware or None): the middleware function (if used like @app.middleware)
                                     or None (if used like @app.middleware())
        """
        if mw is not None:
            self.register_middleware(mw)
            return mw

        def _wrapper(middleware: Middleware) -> Middleware:
            self.register_middleware(middleware)
            return middleware

        return _wrapper

    def exception_handler(self, exception_types: ExceptionTypes) -> Callable[[ExceptionHandler], ExceptionHandler]:
        """Decorator that wraps register_exception_handler

        Args:
            exception_types (ExceptionTypes): the types of exceptions this handler catches (in the style of isinstance)
        """
        def _wrapper(exception_handler: ExceptionHandler) -> ExceptionHandler:
            self.register_exception_handler(exception_types, exception_handler)
            return exception_handler

        return _wrapper


    def attach(self, app: Union['Owlbear', Router], base_path: str="/"):
        """Merge an app or router into this one

        Args:
            app (Owlbear or Router): the app or router to merge into this app
            base_path (str): the path to merge them in on

        """
        if isinstance(app, Owlbear):
            self.router.attach(app.router, base_path)
        else:
            self.router.attach(app, base_path)

    def static(self, prefix: str, local_dir: str, only_files: Optional[List[str]]=None):
        """

        Args:
            prefix ():
            local_dir ():
            only_files ():

        Returns:

        """
        self.router.static(prefix, local_dir, only_files=only_files)
