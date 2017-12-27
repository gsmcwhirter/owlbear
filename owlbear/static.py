# -*- coding: utf-8 -*-
"""Static file handling"""

import logging
import mimetypes
import os
from typing import List, Optional

import aiofiles

from owlbear.logging import setup_logger
import owlbear.request
import owlbear.response
from owlbear.types import RequestHandler


mimetypes.init()
# https://stackoverflow.com/questions/2871655/proper-mime-type-for-fonts/10864297#10864297
# svg   as "image/svg+xml"                  (W3C: August 2011)
# ttf   as "application/x-font-ttf"         (IANA: March 2013)
#       or "application/x-font-truetype"
# otf   as "application/x-font-opentype"    (IANA: March 2013)
# woff  as "application/font-woff"          (IANA: January 2013)
# woff2 as "application/font-woff2"         (W3C W./E.Draft: May 2014/March 2016)
# eot   as "application/vnd.ms-fontobject"  (IANA: December 2005)
# sfnt  as "application/font-sfnt"          (IANA: March 2013)

mimetypes.add_type("image/svg+xml", "svg", strict=False)
mimetypes.add_type("application/x-font-ttf", "ttf", strict=False)
mimetypes.add_type("application/x-font-opentype", "otf", strict=False)
mimetypes.add_type("application/font-woff", "woff", strict=False)
mimetypes.add_type("application/font-woff2", "woff2", strict=False)
mimetypes.add_type("application/vnd.ms-fontobject", "eot", strict=False)
mimetypes.add_type("application/font-sfnt", "sfnt", strict=False)


class StaticFileHandler:

    def __init__(self,
                 prefix: str,
                 local_path: str,
                 only_files: Optional[List[str]]=None,
                 handler_404: Optional[RequestHandler]=None,
                 *, logger: Optional[logging.Logger]=None):
        self.__name__ = 'StaticFileHandler'
        self._prefix = prefix
        self._local_path = os.path.abspath(local_path)
        self._handler_404 = handler_404 or self._default_404

        self.logger = logger or setup_logger("owlbear.staticfilehandler")

        if only_files is None:
            self._only_files = None
        else:
            self._only_files = set(only_files or [])

    @staticmethod
    async def _default_404(request):
        return owlbear.response.html_response('Not found', 404)

    async def __call__(self, request: owlbear.request.Request):
        _, local_relpath = request.path.split(self._prefix, 1)
        local_relpath = local_relpath.lstrip("/")
        local_path = os.path.abspath(os.path.join(self._local_path, local_relpath))

        self.logger.debug("Finding static file", prefix=self._prefix, request_path=request.path, local_relpath=local_relpath, local_path=local_path)

        if not local_path.startswith(self._local_path):
            self.logger.debug("Static file '{}' requested outside of static directory".format(local_path))
            raise ValueError("Static file '{}' requested outside of static directory".format(local_path))

        if not os.path.exists(local_path):
            self.logger.debug("Static file '{}' does not exist".format(local_path))
            return await self._handler_404(request)

        _, resolved_relpath = local_path.split(self._local_path, 1)
        resolved_relpath.lstrip("/")

        if self._only_files is not None and resolved_relpath not in self._only_files:
            self.logger.debug("Static file '{}' is not in the only_files list".format(local_path), only_files=self._only_files)
            return await self._handler_404(request)

        resp = owlbear.response.Response()
        async with aiofiles.open(local_path, 'rb') as f:
            resp.set_content(await f.read(), encoding=None)

        guess = mimetypes.guess_type(local_path, strict=False)
        if guess is not None:
            resp.content_type = guess[0] or "application/octet-stream"
        else:
            resp.content_type = "application/octet-stream"

        self.logger.debug("Static file '{}' found".format(local_path), content_type=resp.content_type)

        return resp
