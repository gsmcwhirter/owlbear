# -*- coding: utf-8 -*-
"""Classes to handle request routing"""
import functools
import logging
import re
from typing import (
    Any, Callable, Dict,
    List, Mapping, MutableMapping, Optional,
    Set, Tuple, Union,
)

from owlbear.logging import setup_logger
from owlbear.static import StaticFileHandler
from owlbear.types import Methods, Middleware, RequestHandler


class BadRouteParameter(Exception):
    """Represents invalid route parameters when adding a route"""
    pass


class RouteNotFound(Exception):
    """Represents a route not being there when finding a route"""
    pass


class ParameterTypeError(Exception):
    """Represents the data in a path not being valid for a route"""
    pass


class ConflictingRoutes(Exception):
    """Represents trying to add a route that is already added"""
    pass


class HandlerNameNotFound(Exception):
    """Represents trying to lookup the url for a handler and it not being found"""
    pass


class BadHandlerParameters(Exception):
    """Represents trying to form the path for a handler without the right parameters"""
    pass


_STAR_TYPES = {
    'int': int,
    'str': str,
}
_URI_PARAMETER_RE = re.compile(
    r"^<([a-zA-Z_][a-zA-Z0-9_]*)?(?::\s*([^>]*))?>$"
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
        star_name = (matches.group(1) or '').strip()
        if not star_name:  # pragma: no cover
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


class RouteTree:
    """Manages the routes and methods in a tree-like manner"""
    prefix: str
    children: MutableMapping[str, 'RouteTree']
    methods: MutableMapping[str, RequestHandler]

    __slots__ = ('prefix', 'children', 'methods', 'star_name', 'star_type', 'logger', )

    def __init__(self,
                 prefix: str,
                 star_name: Optional[str]=None,
                 star_type: Optional[str]=None,
                 *, logger: Optional[logging.Logger]=None):
        """

        Args:
            prefix ():
            star_name ():
            star_type ():
        """
        self.logger = logger or setup_logger("owlbear.routetree")

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
        self.logger.debug("Resetting prefix", old_prefix=self.prefix, new_prefix=new_prefix)

        if self.prefix != "":
            self.prefix = new_prefix.rstrip("/")

        for key, rtree in self.children.items():
            rtree.reset_prefix(f"{new_prefix}/{key}".rstrip("/"))

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
        self.logger.debug("Adding child", key=key, star_name=star_name, star_type=star_type)

        child_prefix = f"{self.prefix.rstrip('/')}/{key}"
        self.children[key] = RouteTree(child_prefix, star_name=star_name, star_type=star_type, logger=self.logger)

    def add_handler(self,
                    uri_parts: List[str],
                    handler: RequestHandler,
                    methods: Methods=('GET', ),
                    parent_parameter_names: Optional[List[str]]=None,
                    allow_stars: bool=True) \
            -> Dict[Tuple[str, str], Tuple[str, Set[str]]]:
        """

        Args:
            uri_parts ():
            handler ():
            methods ():
            parent_parameter_names ():
            allow_stars ():

        Returns:

        """

        self.logger.debug("Adding handler", uri_parts=uri_parts, handler=handler, methods=methods, parent_parameter_names=parent_parameter_names, allow_stars=allow_stars)

        if not methods:
            raise ValueError("No route methods were provided.")

        if not uri_parts:
            updates = {}
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
                updates[(handler.__name__, method)] = ('', set())

            return updates

        else:
            key, *rest = uri_parts

            if parent_parameter_names is None:
                parent_parameter_names = []

            star_name, star_type = _get_star_attrs(key, parent_parameter_names)

            if star_name and not allow_stars:
                raise BadRouteParameter("Parameterized routes are not allowed.")

            if star_name:
                key = '*'

            if key not in self.children:
                self._add_child(key, star_name, star_type)

            key_route = self.children[key]

            if star_name != key_route.star_name:
                raise BadRouteParameter("Route parameter has a conflicting name.")
            if star_type != key_route.star_type:
                raise BadRouteParameter("Route parameter has a conflicting type.")

            updates = key_route.add_handler(rest, handler=handler, methods=methods, parent_parameter_names=parent_parameter_names, allow_stars=allow_stars)
            for k, (path, req_args) in updates.items():
                if star_name:
                    req_args.add(star_name)
                    path = "/{{{}}}{}".format(star_name, path)
                elif key or not path:
                    path = "/{}{}".format(key, path)

                updates[k] = (path, req_args)

            return updates

    def _parse_last_uri_part(self,
                            last_part: str) \
            -> Tuple[Optional[str], Optional[Any]]:
        """

        Args:
            last_part ():

        Returns:

        """
        if self.star_type is None:  # pragma: no cover
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
        self.logger.debug("Finding handler and args for", uri_parts=uri_parts, method=method, handler_args=handler_args)

        if handler_args is None:
            handler_args = {}

        if not uri_parts:
            return self.methods.get(method.upper()), handler_args

        key, *rest = uri_parts
        if key in self.children:
            try:
                return self.children[key].get_handler_and_args(rest, method.upper(), handler_args=handler_args)
            except RouteNotFound:  # pragma: no cover
                pass


        if '*' in self.children:
            param_name, param_val = self.children['*']._parse_last_uri_part(key)

            if param_name is not None:
                handler_args[param_name] = param_val

            try:
                return self.children['*'].get_handler_and_args(rest, method, handler_args=handler_args)
            except RouteNotFound:  # pragma: no cover
                pass

        if '__static__' in self.children:
            try:
                return self.children['__static__'].get_handler_and_args([], method='GET', handler_args=None)
            except RouteNotFound:  # pragma: no cover
                pass

        raise RouteNotFound(f"Could not find route for '{self.prefix.rstrip('/')}/{key}'")

    def list_handlers(self, prefix: str=None) -> List[Tuple[str, str, RequestHandler]]:
        """

        Args:
            prefix ():

        Returns:

        """
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
                   other: 'RouteTree') \
            -> Dict[Tuple[str, str], Tuple[str, Set[str]]]:
        """

        Args:
            other ():

        Returns:

        """
        updates = {}

        for path, method, handler in other.list_handlers():
            uri_parts = _make_uri_parts(path)
            updates.update(self.add_handler(uri_parts, handler, methods=(method, )))

        return updates


class Router:
    """The programmer-facing router"""
    __slots__ = ('tree', 'middleware', 'handler_to_url', 'logger', )

    def __init__(self, *, logger: Optional[logging.Logger]=None):
        """

        """
        self.logger = logger or setup_logger("owlbear.router")
        self.tree = RouteTree("", logger=self.logger)
        self.middleware = []
        self.handler_to_url = {}

    def static(self, prefix: str, local_path: str, only_files: Optional[List[str]]=None):
        """

        Args:
            prefix ():
            local_path ():
            only_files ():

        Returns:

        """
        self.logger.debug("Serving static files", prefix=prefix, local_path=local_path, only_files=only_files)
        self.add_route('{}/__static__'.format(prefix), StaticFileHandler(prefix, local_path, only_files=only_files, logger=self.logger), methods=('GET', ))

    def url_for(self, handler_name: str, method: str='GET', param_args=None) -> str:
        """

        Args:
            handler_name ():
            method ():
            param_args ():

        Returns:

        """
        if param_args is None:
            param_args = {}

        path, req_params = self.handler_to_url.get((handler_name, method), (None, set()))
        if not path:
            raise HandlerNameNotFound("No path was found for handler={}, method={}".format(handler_name, method))

        param_args_keys = set(param_args.keys())
        missing_params = req_params - param_args_keys
        if req_params and missing_params:
            raise BadHandlerParameters("Missing parameter values for: {}".format(", ".join(sorted(missing_params))))

        extra_params = param_args_keys - req_params
        if extra_params:
            raise BadHandlerParameters("Extra parameter values for: {}".format(", ".join(sorted(extra_params))))

        return path.format(**param_args)

    def register_middleware(self, middleware: Middleware):
        """

        Args:
            middleware ():

        Returns:

        """
        self.middleware.insert(0, middleware)

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
        handler_to_url_updates = self.tree.add_handler(uri_parts, handler=handler, methods=methods)
        self.handler_to_url.update(handler_to_url_updates)

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
        handler_to_url_updates = self.tree.merge_with(router.tree)
        self.handler_to_url.update(handler_to_url_updates)

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
