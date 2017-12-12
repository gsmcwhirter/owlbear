# -*- coding: utf-8 -*-
"""Type definitions"""

from typing import Callable, Coroutine, Iterable, Optional, Union, Type

from owlbear.request import Request
from owlbear.response import Response

ExceptionHandler = Callable[[Request, Exception], Coroutine[Optional[Response], None, Optional[Response]]]
ExceptionTypes = Union[Type, Iterable[Type]]
Methods = Iterable[str]
RequestHandler = Callable[[Request], Coroutine[Response, None, Response]]
WrappedRequestHandler = Callable[[Request], Coroutine[Response, None, Response]]
Middleware = Callable[[Request, WrappedRequestHandler], Coroutine[Response, None, Response]]
