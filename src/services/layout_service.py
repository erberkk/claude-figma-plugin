
from __future__ import annotations

import re

from src.domain.exceptions import PromptInjectionError, ValidationError
from src.domain.models import FigmaNode, GenerateResponse
from src.infrastructure.claude_client import ClaudeClient
from src.infrastructure.logging import get_logger
from src.infrastructure.response_cache import ResponseCache
from src.services.validator import validate_output

logger = get_logger(__name__)

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|above|prior)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"ADMIN\s*OVERRIDE", re.IGNORECASE),
]

class LayoutService:
    """Core business logic: sanitize, generate, validate, return."""

    def __init__(self, claude_client: ClaudeClient, cache: ResponseCache | None = None) -> None:
        self._claude = claude_client
        self._cache = cache

    async def generate(self, prompt: str, *, use_thinking: bool = False) -> GenerateResponse:
        """Generate a validated Figma layout tree from a natural-language prompt.

        Args:
            prompt: Natural-language description of the UI to generate.
            use_thinking: Explicitly enable sequential thinking. Auto-enabled
                          for prompts matching complexity keywords.
        """
        self._guard_injection(prompt)

        logger.info("layout_generate_start", prompt_length=len(prompt), use_thinking=use_thinking)

        if self._cache is not None:
            cached = self._cache.get(prompt)
            if cached is not None:
                raw_cached, thinking_cached = cached
                try:
                    data = validate_output(raw_cached)
                    layout = FigmaNode.model_validate(data)
                    logger.info("layout_generate_success", retried=False, thinking_used=thinking_cached)
                    return GenerateResponse(layout=layout, retried=False, thinking_used=thinking_cached)
                except ValidationError as cache_err:
                    logger.warning("layout_cache_invalid", error=cache_err.message)

        raw, thinking_used = await self._claude.complete(prompt, use_thinking=use_thinking)
        try:
            data = validate_output(raw)
            layout = FigmaNode.model_validate(data)
            if self._cache is not None:
                self._cache.put(prompt, raw, thinking_used)
            logger.info("layout_generate_success", retried=False, thinking_used=thinking_used)
            return GenerateResponse(layout=layout, retried=False, thinking_used=thinking_used)
        except ValidationError as first_err:
            logger.warning("layout_first_attempt_failed", error=first_err.message)

        retry_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Your previous response failed JSON validation. "
            "Output ONLY a single compact JSON object. "
            "No markdown fences, no explanation, no comments."
        )
        raw, thinking_used = await self._claude.complete(retry_prompt, use_thinking=False)
        try:
            data = validate_output(raw)
            layout = FigmaNode.model_validate(data)
            if self._cache is not None:
                self._cache.put(prompt, raw, thinking_used)
            logger.info("layout_generate_success", retried=True, thinking_used=thinking_used)
            return GenerateResponse(layout=layout, retried=True, thinking_used=thinking_used)
        except ValidationError as retry_err:
            logger.error("layout_retry_failed", error=retry_err.message)
            raise retry_err

    @staticmethod
    def _guard_injection(prompt: str) -> None:
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(prompt):
                raise PromptInjectionError()
