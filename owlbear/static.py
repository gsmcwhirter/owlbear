# -*- coding: utf-8 -*-
"""Static file handling"""

import os

import aiofiles

import owlbear.request
import owlbear.response


class StaticFileHandler:

    def __init__(self, prefix, local_path):
        self._prefix = prefix
        self._local_path = os.path.abspath(local_path)

    async def __call__(self, request: owlbear.request.Request):
        _, local_relpath = request.path.split(self._prefix, 1)
        local_relpath = local_relpath.lstrip("/")
        local_path = os.path.abspath(os.path.join(self._local_path, local_relpath))

        if not local_path.startswith(self._local_path):
            raise ValueError("Static file '{}' requested outside of static directory".format(local_path))

        if not os.path.exists(local_path):
            return owlbear.response.html_response('Not found', 404)

        resp = owlbear.response.Response()
        async with aiofiles.open(local_path, 'rb') as f:
            resp.set_content(await f.read(), encoding=None)

        return resp
