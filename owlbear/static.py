# -*- coding: utf-8 -*-
"""Static file handling"""

import os
from typing import List, Optional

import aiofiles

import owlbear.request
import owlbear.response
from owlbear.types import RequestHandler


class StaticFileHandler:

    def __init__(self, prefix: str, local_path: str, only_files: Optional[List[str]]=None, handler_404: Optional[RequestHandler]=None):
        self.__name__ = 'StaticFileHandler'
        self._prefix = prefix
        self._local_path = os.path.abspath(local_path)
        self._only_files = set(only_files or [])
        self._handler_404 = handler_404 or self._default_404

    @staticmethod
    async def _default_404(request):
        return owlbear.response.html_response('Not found', 404)

    async def __call__(self, request: owlbear.request.Request):
        _, local_relpath = request.path.split(self._prefix, 1)
        local_relpath = local_relpath.lstrip("/")
        local_path = os.path.abspath(os.path.join(self._local_path, local_relpath))

        if not local_path.startswith(self._local_path):
            raise ValueError("Static file '{}' requested outside of static directory".format(local_path))

        if not os.path.exists(local_path):
            return await self._handler_404(request)

        _, resolved_relpath = local_path.split(self._local_path, 1)
        resolved_relpath.lstrip("/")

        if not resolved_relpath in self._only_files:
            return await self._handler_404(request)

        resp = owlbear.response.Response()
        async with aiofiles.open(local_path, 'rb') as f:
            resp.set_content(await f.read(), encoding=None)

        return resp
