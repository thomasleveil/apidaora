import asyncio
from http import HTTPStatus
from logging import getLogger
from typing import Any, Awaitable, Callable, Coroutine, Dict, Iterable
from urllib import parse

from jsondaora.exceptions import DeserializationError

from ...exceptions import MethodNotFoundError, PathNotFoundError
from .response import (
    send_not_found,
    send_method_not_allowed_response,
    send_response
)
from ..router import ResolvedRoute


logger = getLogger(__name__)


Scope = Dict[str, Any]
Receiver = Callable[[], Awaitable[Dict[str, Any]]]
Sender = Callable[[Dict[str, Any]], Awaitable[None]]
AsgiCallable = Callable[[Scope, Receiver, Sender], Coroutine[Any, Any, None]]


def asgi_app(router: Callable[[str, str], ResolvedRoute]) -> AsgiCallable:
    async def handler(scope: Scope, receive: Receiver, send: Sender) -> None:
        try:
            resolved = router(scope['path'], scope['method'])

        except PathNotFoundError:
            await send_not_found(send)

        except MethodNotFoundError:
            await send_method_not_allowed_response(send)

        else:
            route = resolved.route

            if route.has_query:
                query_dict = _get_query_dict(scope)
            else:
                query_dict = {}

            if route.has_body:
                body = await _read_body(receive)
            else:
                body = b''

            if route.has_headers:
                headers = scope['headers']
            else:
                headers = []

            response_body = route.caller(
                resolved.path_args,
                query_dict,
                headers,
                body,
            )

            if asyncio.iscoroutine(response_body):
                response_body = await response_body

            response, body = (
                (response_body[0], response_body[1])
                if len(response_body) > 1
                else (response_body[0], b'')
            )
            await send_response(send, response, body)

    return handler


def _get_query_dict(scope: Dict[str, Any]) -> Dict[str, Any]:
    qs = parse.parse_qs(scope['query_string'].decode())
    return qs


async def _read_body(receive: Callable[[], Awaitable[Dict[str, Any]]]) -> Any:
    body = b''
    more_body = True

    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)

    return body
