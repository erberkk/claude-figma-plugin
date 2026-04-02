
from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from src.api.middleware import InputSizeLimitMiddleware
from src.infrastructure.config import Settings


def _make_settings(max_input_size: int = 100) -> Settings:
    return Settings(anthropic_api_key="test-key", max_input_size=max_input_size)


def _build_app(max_input_size: int = 100) -> Starlette:
    """Build a minimal Starlette app wrapped with InputSizeLimitMiddleware."""

    async def echo(request: Request) -> PlainTextResponse:
        body = await request.body()
        return PlainTextResponse(f"ok:{len(body)}")

    app = Starlette(routes=[])
    app.add_middleware(InputSizeLimitMiddleware, settings=_make_settings(max_input_size))

    # Mount route manually so middleware wraps it
    from starlette.routing import Route
    inner = Starlette(routes=[Route("/upload", echo, methods=["POST"])])
    app.mount("/", inner)
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client(max_input_size: int = 100) -> TestClient:
    return TestClient(_build_app(max_input_size), raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Content-Length present — existing behaviour must still work
# ---------------------------------------------------------------------------

class TestContentLengthPresent:
    def test_rejects_oversized_body_with_content_length(self):
        """A POST with Content-Length > max_input_size must be rejected with 413."""
        client = _client(max_input_size=10)
        body = b"x" * 20
        response = client.post(
            "/upload",
            content=body,
            headers={"content-length": str(len(body))},
        )
        assert response.status_code == 413

    def test_allows_undersized_body_with_content_length(self):
        """A POST with Content-Length <= max_input_size must be allowed through."""
        client = _client(max_input_size=100)
        body = b"small"
        response = client.post(
            "/upload",
            content=body,
            headers={"content-length": str(len(body))},
        )
        assert response.status_code == 200

    def test_413_response_has_correct_error_fields(self):
        """413 response must include 'error' and 'message' keys."""
        client = _client(max_input_size=10)
        body = b"x" * 20
        response = client.post(
            "/upload",
            content=body,
            headers={"content-length": str(len(body))},
        )
        assert response.status_code == 413
        data = response.json()
        assert data["error"] == "INPUT_TOO_LARGE"
        assert "10" in data["message"]

    def test_get_request_is_not_checked(self):
        """GET requests are not checked regardless of Content-Length."""
        client = _client(max_input_size=5)
        response = client.get("/upload")
        # Route only accepts POST but the middleware must not interfere (404 from router)
        assert response.status_code != 413


# ---------------------------------------------------------------------------
# Content-Length absent — the bug: body size NOT enforced previously
# ---------------------------------------------------------------------------

class TestNoContentLength:
    def test_rejects_oversized_body_without_content_length(self):
        """A POST without Content-Length that exceeds max_input_size must return 413.

        This is the core regression test for issue #5. Before the fix, this
        request would have been passed through (200 / 404) instead of rejected.
        """
        client = _client(max_input_size=10)
        oversized_body = b"x" * 20

        # httpx (used by TestClient) normally adds Content-Length automatically.
        # We strip it by sending a raw stream with transfer-encoding chunked.
        response = client.post(
            "/upload",
            content=oversized_body,
            headers={"transfer-encoding": "chunked", "content-length": ""},
        )
        assert response.status_code == 413

    def test_allows_undersized_body_without_content_length(self):
        """A POST without Content-Length whose body is within limit must be allowed."""
        client = _client(max_input_size=100)
        small_body = b"hello"

        response = client.post(
            "/upload",
            content=small_body,
            headers={"transfer-encoding": "chunked", "content-length": ""},
        )
        assert response.status_code == 200

    def test_downstream_handler_receives_body_when_no_content_length(self):
        """After reading the body for size check, downstream must still receive it."""
        client = _client(max_input_size=100)
        body = b"payload_data"

        response = client.post(
            "/upload",
            content=body,
            headers={"transfer-encoding": "chunked", "content-length": ""},
        )
        assert response.status_code == 200
        # The echo handler responds with "ok:<body_length>"
        assert response.text == f"ok:{len(body)}"

    def test_exactly_at_limit_is_allowed_without_content_length(self):
        """A body exactly equal to max_input_size must NOT be rejected."""
        client = _client(max_input_size=10)
        body = b"x" * 10

        response = client.post(
            "/upload",
            content=body,
            headers={"transfer-encoding": "chunked", "content-length": ""},
        )
        assert response.status_code == 200

    def test_one_byte_over_limit_rejected_without_content_length(self):
        """A body one byte over max_input_size must be rejected with 413."""
        client = _client(max_input_size=10)
        body = b"x" * 11

        response = client.post(
            "/upload",
            content=body,
            headers={"transfer-encoding": "chunked", "content-length": ""},
        )
        assert response.status_code == 413
