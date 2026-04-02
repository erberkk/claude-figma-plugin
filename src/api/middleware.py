
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from src.domain.exceptions import AuthError, InputTooLargeError
from src.infrastructure.config import Settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header against the configured API key."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._api_key = settings.api_key

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        key = request.headers.get("X-API-Key")
        if not key or key != self._api_key:
            err = AuthError()
            return JSONResponse(
                status_code=err.status,
                content={"error": err.code, "message": err.message},
            )
        return await call_next(request)


class InputSizeLimitMiddleware:
    """Rejects request bodies exceeding the configured maximum size.

    Two-stage enforcement:
    1. Fast path — if Content-Length is present and already over the limit,
       reject immediately without reading the body.
    2. Fallback — when Content-Length is absent (chunked transfer, malicious
       client), read the body and check its actual length before forwarding.
       The consumed bytes are re-injected into the ASGI receive stream so that
       downstream handlers can still read them normally.
    """

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self._app = app
        self._max_size = settings.max_input_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        method: str = scope.get("method", "")
        if method not in _BODY_METHODS:
            await self._app(scope, receive, send)
            return

        # Build a temporary Request to inspect headers without consuming the body.
        request = Request(scope, receive)
        raw_content_length = request.headers.get("content-length", "").strip()

        # Fast path: Content-Length present and already over the limit.
        if raw_content_length:
            try:
                declared_size = int(raw_content_length)
            except ValueError:
                declared_size = 0

            if declared_size > self._max_size:
                err = InputTooLargeError(self._max_size)
                response = JSONResponse(
                    status_code=err.status,
                    content={"error": err.code, "message": err.message},
                )
                await response(scope, receive, send)
                return

            # Content-Length present and within limit — forward unchanged.
            await self._app(scope, receive, send)
            return

        # Fallback: Content-Length absent — read the body to check actual size.
        body = await request.body()
        if len(body) > self._max_size:
            err = InputTooLargeError(self._max_size)
            response = JSONResponse(
                status_code=err.status,
                content={"error": err.code, "message": err.message},
            )
            await response(scope, receive, send)
            return

        # Body is within limit — re-inject it into the receive stream so
        # downstream handlers can read it normally.
        body_consumed = False

        async def replay_receive() -> dict:
            nonlocal body_consumed
            if not body_consumed:
                body_consumed = True
                return {"type": "http.request", "body": body, "more_body": False}
            # Subsequent calls (e.g. disconnect events) fall through to real receive.
            return await receive()

        await self._app(scope, replay_receive, send)
