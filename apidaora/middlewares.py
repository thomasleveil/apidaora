from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type

from .exceptions import BadRequestError
from .header import Header
from .responses import Response
from .route.controller_input import ControllerInput


@dataclass
class MiddlewareRequest:
    path_pattern: str
    path_args: Optional[Dict[str, Any]] = None
    query_dict: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Header]] = None
    body: Any = None
    kwargs: Optional[Dict[str, Any]] = None


@dataclass
class Middlewares:
    post_routing: List[Callable[[str, Dict[str, Any]], None]] = field(
        default_factory=list
    )
    pre_execution: List[Callable[[MiddlewareRequest], None]] = field(
        default_factory=list
    )
    post_execution: List[
        Callable[[MiddlewareRequest, Response], None]
    ] = field(default_factory=list)


def make_asgi_input_from_requst(
    request: MiddlewareRequest, input_cls: Type[ControllerInput]
) -> ControllerInput:
    kwargs = {}

    if request.path_args:
        kwargs.update(request.path_args)
    if request.query_dict:
        kwargs.update(request.query_dict)
    if request.headers:
        kwargs.update(request.headers)
    if request.body:
        kwargs['body'] = request.body
    if request.kwargs and (input_cls.__annotations_info__.has_kwargs):
        kwargs.update(request.kwargs)

    return input_cls(**kwargs)


class AllowOriginHeader(
    Header, type=str, http_name='access-control-allow-origin'
):
    ...


class ExposeHeadersHeader(
    Header, type=str, http_name='access-control-expose-headers'
):
    ...


class AllowHeadersHeader(
    Header, type=str, http_name='access-control-allow-headers'
):
    ...


class AllowMethodsHeader(
    Header, type=str, http_name='access-control-allow-methods'
):
    ...


class CorsMiddleware:
    def __init__(
        self,
        *,
        allow_origin: Optional[str] = None,
        expose_headers: Optional[str] = None,
        allow_headers: Optional[str] = None,
        allow_methods: Optional[str] = None,
        servers_all: Optional[str] = '*',
    ):
        if (
            not allow_origin
            and not expose_headers
            and not allow_headers
            and not allow_methods
        ):
            self.headers = [
                AllowOriginHeader(servers_all),
                ExposeHeadersHeader(servers_all),
                AllowHeadersHeader(servers_all),
                AllowMethodsHeader(servers_all),
            ]
        else:
            self.headers = []
            if allow_origin:
                self.headers.append(AllowOriginHeader(allow_origin))
            if expose_headers:
                self.headers.append(ExposeHeadersHeader(expose_headers))
            if allow_headers:
                self.headers.append(AllowHeadersHeader(allow_headers))
            if allow_methods:
                self.headers.append(AllowMethodsHeader(allow_methods))

        self.headers_tuple = tuple(self.headers)

    def __call__(self, request: MiddlewareRequest, response: Response) -> None:
        if isinstance(response.headers, list):
            response.headers.extend(self.headers)

        elif isinstance(response.headers, tuple):
            response.headers = response.headers + self.headers_tuple

        elif response.headers is None:
            response.headers = self.headers_tuple


@dataclass
class LockRequestMiddleware:
    locks: Set[str] = field(default_factory=set)

    def lock(self, path_pattern: str, path_args: Dict[str, Any]) -> None:
        if path_pattern in self.locks:
            raise BadRequestError(
                'lock-request', {'path_pattern': path_pattern}
            )

        self.locks.add(path_pattern)

    def unlock_pre_execution(self, request: MiddlewareRequest) -> None:
        self.locks.remove(request.path_pattern)

    def unlock_post_execution(
        self, request: MiddlewareRequest, response: Response
    ) -> None:
        self.locks.remove(request.path_pattern)
