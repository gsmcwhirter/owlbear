from collections import namedtuple
from unittest.mock import MagicMock

from owlbear import router, test_helpers


MockRequest = namedtuple('MockRequest', ['path', 'method'])


def test_add_route_and_lookup_handlers():
    mock_handler1 = MagicMock()
    coro_mock_handler1 = test_helpers.make_coroutine(mock_handler1)

    my_router = router.Router()
    my_router.add_route("/", coro_mock_handler1)

    handler, args = my_router.handler_and_args_for("/", "GET")
    assert handler is coro_mock_handler1
    assert args == {}
    request = MockRequest(path="/", method="GET")
    test_helpers.run_coroutine(my_router.dispatch(request))

    mock_handler1.assert_called_once_with(request)

    mock_handler2 = MagicMock()
    coro_mock_handler2 = test_helpers.make_coroutine(mock_handler2)

    my_router.add_route("/test/thing", coro_mock_handler2, methods=("GET", "POST",))
    handler, args = my_router.handler_and_args_for("/test/thing", "GET")
    assert handler is coro_mock_handler2
    assert args == {}

    handler, args = my_router.handler_and_args_for("/test/thing", "POST")
    assert handler is coro_mock_handler2
    assert args == {}

    handler, args = my_router.handler_and_args_for("/test/thing/", "GET")
    assert handler is coro_mock_handler2
    assert args == {}

    mock_handler3 = MagicMock
    coro_mock_handler3 = test_helpers.make_coroutine(mock_handler3)

    my_router.add_route("/test2/{thing: int}/{thing2: str}/test/{thing3: str}", coro_mock_handler3)

    handler, args = my_router.handler_and_args_for("/test2/13/foo/test/bar", "GET")
    assert handler is coro_mock_handler3
    assert args == {'thing': 13, 'thing2': 'foo', 'thing3': 'bar'}

    router.print_route_tree(my_router.tree)
    print()
    for item in my_router.tree.list_handlers():
        print(item)


def test_attach_router():
    mock_handler1 = MagicMock()
    coro_mock_handler1 = test_helpers.make_coroutine(mock_handler1)

    mock_handler2 = MagicMock()
    coro_mock_handler2 = test_helpers.make_coroutine(mock_handler2)

    my_router = router.Router()
    my_router.add_route("/", coro_mock_handler1)

    sub_router = router.Router()
    sub_router.add_route("/", coro_mock_handler2)

    print("*****")
    router.print_route_tree(sub_router.tree)
    print()
    for item in sub_router.tree.list_handlers():
        print(item)

    sub_router.tree.reset_prefix("/foo")

    print("*****")
    router.print_route_tree(my_router.tree)
    print()
    for item in my_router.tree.list_handlers():
        print(item)

    print("*****")
    router.print_route_tree(sub_router.tree)
    print()
    for item in sub_router.tree.list_handlers():
        print(item)

    my_router.attach(sub_router, "/foo")

    handler, args = my_router.handler_and_args_for("/", "GET")
    assert handler is coro_mock_handler1
    assert args == {}

    handler, args = my_router.handler_and_args_for("/foo/", 'GET')
    assert handler is coro_mock_handler2
    assert args == {}


