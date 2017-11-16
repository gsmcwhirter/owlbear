# -*- coding: utf-8 -*-
"""Example app for owlbear"""

import time

from owlbear.app import Owlbear
from owlbear.request import Request
from owlbear.router import WrappedRequestHandler
from owlbear.response import json_response, Response


class MyApp(Owlbear):

    def __init__(self):
        super().__init__()


app = MyApp()


@app.middleware
async def example_middleware(request: Request,
                             next_handler: WrappedRequestHandler) -> Response:
    print("foo!")
    # do sutff pre; can return here and next_handler won't run
    request.data.start_time = time.time()

    resp = await next_handler(request)
    # do stuff post; can return here and return value will override

    duration = time.time() - request.data.start_time
    print(f"Elapsed sec: {duration}")

    return resp


@app.route("/", methods=("GET", ))
async def hello(request):
    return json_response({
        'message': "Hello, world! \u263a"
    })
