# -*- coding: utf-8 -*-
"""Exception handling functionality (types and example)"""
import sys
import traceback
from typing import Callable, Coroutine, Iterable, Optional, Type, Union

from owlbear.request import Request
from owlbear.response import Response

ExceptionHandler = Callable[[Request, Exception], Coroutine[Optional[Response], None, Optional[Response]]]
ExceptionTypes = Union[Type, Iterable[Type]]


async def default_exception_handler(request: Request, e: Exception) -> Optional[Response]:
    """Catches all exceptions, prints a message and traceback to stderr, and returns a text/plain 500

    Args:
        request (Request): the Owlbear request
        e (Exception): the exception to handle

    Returns:

    """
    print(request, file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    resp = Response()
    resp.status = 500
    resp.content_type = "text/plain"
    resp.set_content(f'An error occurred: {e}')

    return resp
