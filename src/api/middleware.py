
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.domain.exceptions import AuthError, InputTooLargeError
from src.infrastructure.config import Settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

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

class InputSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects request bodies exceeding the configured maximum size."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._max_size = settings.max_input_size

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self._max_size:
                err = InputTooLargeError(self._max_size)
                return JSONResponse(
                    status_code=err.status,
                    content={"error": err.code, "message": err.message},
                )
        return await call_next(request)
