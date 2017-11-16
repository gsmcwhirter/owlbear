
import functools
import re
from typing import (
    Any, Callable, Coroutine, Iterable,
    List, Mapping, MutableMapping, Optional,
    Tuple, Type, Union,
)

from owlbear.request import Request
from owlbear.response import Response


Methods = Iterable[str]
RequestHandler = Callable[[Request], Coroutine[Response, None, None]]
WrappedRequestHandler = Callable[[Request], Coroutine[Response, None, None]]
Middleware = Callable[[Request, WrappedRequestHandler], Coroutine[Response, None, None]]


class BadRouteParameter(Exception):
    pass


class RouteNotFound(Exception):
    pass


class ParameterTypeError(Exception):
    pass


class ConflictingRoutes(Exception):
    pass


_STAR_TYPES = {
    'int': int,
    'str': str,
}
_URI_PARAMETER_RE = re.compile(
    r"^{{([a-zA-Z_][a-zA-Z0-9_]*)(?::\s*({star_types}))?}}$".format(
        star_types="|".join(_STAR_TYPES.keys())
    )
)


def _get_star_attrs(key: str,
                    parent_parameter_names: List[str]) \
        -> Union[Tuple[str, Callable], Tuple[None, None]]:
    """

    Args:
        key ():
        parent_parameter_names ():

    Returns:

    """
    matches = _URI_PARAMETER_RE.match(key)
    if matches:
        star_name = matches.group(1)
        if not star_name:
            raise BadRouteParameter("Route parameter definition must have a non-empty name.")

        if star_name in parent_parameter_names:
            raise BadRouteParameter("Route parameter has a conflicting name.")

        star_type_name = matches.group(2) or 'str'
        if star_type_name not in _STAR_TYPES:
            raise BadRouteParameter(f"Route parameter type '{star_type_name}' was not recognized")

        star_type = star_type_name
        parent_parameter_names.append(star_name)
    else:
        star_name = None
        star_type = None

    return star_name, star_type


def _make_uri_parts(path: str) -> List[str]:
    """

    Args:
        path ():

    Returns:

    """
    path = path.strip("/")
    if path != "":
        path = f"/{path}"

    return path.split("/")


def print_route_tree(route_tree: 'RouteTree', indent: str=""):
    """

    Args:
        route_tree ():
        indent ():

    Returns:

    """
    print(indent, "-", repr(route_tree.prefix), f"{', '.join(route_tree.methods.keys())}")
    indent = indent + "  "

    for key, child in route_tree.children.items():
        print_route_tree(child, indent)

# async def example_middleware(request: Request,
#                              next_handler: WrappedRequestHandler) -> Response:
#     # do sutff pre; can return here and next_handler won't run
#     resp = await next_handler(request)
#     # do stuff post; can return here and return value will override
#     return resp


class RouteTree:
    prefix: str
    children: MutableMapping[str, 'RouteTree']
    methods: MutableMapping[str, RequestHandler]

    __slots__ = ('prefix', 'children', 'methods', 'star_name', 'star_type',)

    def __init__(self,
                 prefix: str,
                 star_name: Optional[str]=None,
                 star_type: Optional[str]=None):
        """

        Args:
            prefix ():
            star_name ():
            star_type ():
        """
        self.prefix = prefix
        self.children = {}
        self.methods = {}

        if prefix.endswith("/*"):
            assert star_name is not None
            assert star_type is not None
        else:
            assert star_name is None
            assert star_type is None

        self.star_name = star_name
        self.star_type = star_type

    def reset_prefix(self, new_prefix: str):
        """

        Args:
            new_prefix ():

        Returns:

        """
        if self.prefix != "":
            self.prefix = new_prefix.rstrip("/")

        for key, rtree in self.children.items():
            rtree.reset_prefix(f"{new_prefix}/{key}")

    def _add_child(self,
                   key: str,
                   star_name: Optional[str],
                   star_type: Optional[str]):
        """

        Args:
            key ():
            star_name ():
            star_type ():

        Returns:

        """
        child_prefix = f"{self.prefix.rstrip('/')}/{key}"
        self.children[key] = RouteTree(child_prefix, star_name=star_name, star_type=star_type)

    def add_handler(self,
                    uri_parts: List[str],
                    handler: RequestHandler,
                    methods: Methods=('GET', ),
                    parent_parameter_names: Optional[List[str]]=None):
        """

        Args:
            uri_parts ():
            handler ():
            methods ():
            parent_parameter_names ():

        Returns:

        """
        if not methods:
            raise ValueError("No route methods were provided.")

        if not uri_parts:
            for method in methods:
                method = method.upper()
                if self.methods.get(method):
                    raise ConflictingRoutes("Trying to add route '{method} {path}' -> {handler} conflicts with existing handler {old_handler}".format(
                        method=method,
                        path=self.prefix,
                        handler=handler,
                        old_handler=self.methods.get(method),
                    ))

                self.methods[method] = handler

        else:
            key, *rest = uri_parts

            if parent_parameter_names is None:
                parent_parameter_names = []

            star_name, star_type = _get_star_attrs(key, parent_parameter_names)

            if star_name:
                key = '*'

            if key not in self.children:
                self._add_child(key, star_name, star_type)

            key_route = self.children[key]

            if star_name != key_route.star_name:
                raise BadRouteParameter("Route parameter has a conflicting name.")
            if star_type != key_route.star_type:
                raise BadRouteParameter("Route parameter has a conflicting type.")

            key_route.add_handler(rest, handler=handler, methods=methods, parent_parameter_names=parent_parameter_names)

    def _parse_last_uri_part(self,
                            last_part: str) \
            -> Tuple[Optional[str], Optional[Any]]:
        """

        Args:
            last_part ():

        Returns:

        """
        if self.star_type is None:
            return None, None

        try:
            return self.star_name, _STAR_TYPES[self.star_type](last_part)
        except Exception:
            raise ParameterTypeError(f"Paramter value '{last_part}' could not be converted to type {_STAR_TYPES[self.star_type]} for parameter {self.star_name}")

    def get_handler_and_args(self,
                             uri_parts: List[str],
                             method: str,
                             handler_args: Optional[MutableMapping[str, Any]]=None) \
            -> Optional[Tuple[RequestHandler, Mapping[str, Any]]]:
        """

        Args:
            uri_parts ():
            method ():
            handler_args ():

        Returns:

        """
        if handler_args is None:
            handler_args = {}

        if not uri_parts:
            return self.methods.get(method.upper()), handler_args

        key, *rest = uri_parts
        if key in self.children:
            try:
                return self.children[key].get_handler_and_args(rest, method.upper(), handler_args=handler_args)
            except RouteNotFound:
                pass


        if '*' in self.children:
            param_name, param_val = self.children['*']._parse_last_uri_part(key)

            if param_name is not None:
                handler_args[param_name] = param_val

            try:
                return self.children['*'].get_handler_and_args(rest, method, handler_args=handler_args)
            except RouteNotFound:
                pass

        raise RouteNotFound(f"Could not find route for '{self.prefix.rstrip('/')}/{key}'")

    def list_handlers(self, prefix=None):
        if prefix is None:
            prefix = self.prefix.rsplit("/", 1)[0]

        key = self.prefix.split("/")[-1]
        if key == "*":
            key = f"<{self.star_name}: {self.star_type}>"

        full_key = f"{prefix.rstrip('/')}/{key}"

        handlers = [
            (full_key, method, handler)
            for method, handler in self.methods.items()
        ]

        for child in self.children.values():
            handlers.extend(child.list_handlers(prefix=full_key))

        return handlers

    def merge_with(self,
                   other: 'RouteTree'):
        """

        Args:
            other ():

        Returns:

        """
        for path, method, handler in other.list_handlers():
            uri_parts = _make_uri_parts(path)
            self.add_handler(uri_parts, handler, methods=(method, ))

        # if routes.prefix == self.prefix:
        #     print("other methods", routes.methods)
        #     for method, reqhandler in routes.methods.items():
        #         print("this", self.prefix, method, reqhandler)
        #         if self.methods.get(method):
        #             raise ConflictingRoutes(
        #                 "Trying to merge route '{method} {path}' -> {handler} conflicts with existing handler {old_handler}".format(
        #                     method=method,
        #                     path=self.prefix,
        #                     handler=reqhandler,
        #                     old_handler=self.methods.get(method),
        #                 ))
        #
        #         self.methods[method] = reqhandler
        # else:
        #     assert routes.prefix.startswith(self.prefix), (routes.prefix, self.prefix)
        #
        #     uri_parts = _make_uri_parts(routes.prefix[len(self.prefix) + 1:])
        #     print("uri_parts", uri_parts)
        #     key, *rest = uri_parts
        #
        #     if parent_parameter_names is None:
        #         parent_parameter_names = []
        #
        #     if self.star_name is not None:
        #         parent_parameter_names.append(self.star_name)
        #
        #     star_name, star_type = _get_star_attrs(key, parent_parameter_names)
        #
        #     if star_name:
        #         key = '*'
        #
        #     if key not in self.children:
        #         self._add_child(key, star_name, star_type)
        #
        #     self.children[key].merge_with(routes, parent_parameter_names=parent_parameter_names)


class Router:
    __slots__ = ('tree', 'middleware',)

    def __init__(self):
        """

        """
        self.tree = RouteTree("")
        self.middleware = []

    def register_middleware(self, middleware: Middleware):
        """

        Args:
            middleware ():

        Returns:

        """
        self.middleware.append(middleware)

    def add_route(self,
                  uri_path: str,
                  handler: RequestHandler,
                  methods: Methods=('GET', )):
        """

        Args:
            uri_path ():
            handler ():
            methods ():

        Returns:

        """
        uri_parts = _make_uri_parts(uri_path)
        self.tree.add_handler(uri_parts, handler=handler, methods=methods)

    def attach(self,
               router: 'Router',
               base_path: str):
        """

        Args:
            router ():
            base_path ():

        Returns:

        """
        if not base_path.startswith("/"):
            base_path = "/{}".format(base_path)

        if base_path == "/":
            base_path = ""

        router.tree.reset_prefix(base_path)
        self.tree.merge_with(router.tree)

    def handler_and_args_for(self,
                             uri_path: str,
                             method: str) \
            -> Tuple[RequestHandler, Mapping[str, Any]]:
        """

        Args:
            uri_path ():
            method ():

        Returns:

        """
        uri_parts = _make_uri_parts(uri_path)
        return self.tree.get_handler_and_args(uri_parts, method=method)

    async def dispatch(self, request):
        """

        Args:
            request ():

        Returns:

        """
        _handler, handler_args = self.handler_and_args_for(request.path, method=request.method)
        handler = functools.partial(_handler, **handler_args)
        functools.update_wrapper(handler, _handler)

        for middleware in self.middleware:
            handler = functools.partial(middleware, next_handler=handler)
            functools.update_wrapper(handler, middleware)

        return await handler(request)
