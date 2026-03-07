from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware import AuthMiddleware, InputSizeLimitMiddleware
from src.api.routes import router
from src.domain.exceptions import AppError
from src.infrastructure.claude_client import ClaudeClient
from src.infrastructure.config import get_settings
from src.infrastructure.logging import setup_logging
from src.infrastructure.response_cache import ResponseCache
from src.services.layout_service import LayoutService

_app_state: dict[str, Any] = {}

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.md"

def _prompt_version() -> str:
    """Return a short SHA-256 hash of the system prompt file.

    Used as a cache versioning key so that prompt changes automatically
    invalidate stale cached responses.
    """
    content = _PROMPT_PATH.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="Figma Layout Generator",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(InputSizeLimitMiddleware, settings=settings)
    app.add_middleware(AuthMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": exc.code, "message": exc.message},
        )

    cache = ResponseCache(
        enabled=settings.claude_cache_enabled,
        cache_dir=settings.claude_cache_dir,
        prompt_version=_prompt_version(),
    )
    claude_client = ClaudeClient(settings)
    layout_service = LayoutService(claude_client, cache=cache)
    _app_state["layout_service"] = layout_service

    app.include_router(router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
