# -*- coding: utf-8 -*-
from typing import Callable, Coroutine, Iterable, Optional, Type, Union

from owlbear.request import Request
from owlbear.response import Response

ExceptionHandler = Callable[[Request, Exception], Coroutine[Optional[Response], None, Optional[Response]]]
ExceptionTypes = Union[Type, Iterable[Type]]


async def default_exception_handler(request: Request, e: Exception) -> Optional[Response]:
    print(f"{e.__class__.__name__}: {e}")
    resp = Response()
    resp.status = 500
    resp.set_content(f'An error occurred: {e}')

    return resp
