# -*- coding: utf-8 -*-
"""Example app for owlbear"""

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
    try:
        # do sutff pre; can return here and next_handler won't run
        resp = await next_handler(request)
        # do stuff post; can return here and return value will override
        return resp
    except Exception as e:
        print(f"{e.__class__.__name__}: {e}")
        return json_response({"error": format(e)}, status=500)


@app.route("/", methods=("GET", ))
async def hello(request):
    return json_response({
        'message': "Hello, world! \u263a"
    })
