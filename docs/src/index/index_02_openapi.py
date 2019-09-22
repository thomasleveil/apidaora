from dataclasses import dataclass

from apidaora import JSONResponse, MethodType, app_daora, path


@dataclass
class Response(JSONResponse):
    body: str


@path('/hello', MethodType.GET)
def controller(name: str) -> Response:
    message = f'Hello {name}!'
    return Response(body=message)


app = app_daora(operations=[controller])
