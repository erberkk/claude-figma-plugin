

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import anthropic

from src.domain.exceptions import ClaudeError, ClaudeTimeoutError
from src.infrastructure.config import Settings
from src.infrastructure.logging import get_logger

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "system_prompt.md"

logger = get_logger(__name__)

_COMPLEX_KEYWORDS: frozenset[str] = frozenset(
    {
        "dashboard", "kanban", "table", "data table", "grid", "chart", "graph",
        "sidebar", "navigation", "modal", "multi-step", "wizard", "full page",
        "mobile app", "web app", "screen", "landing page", "e-commerce",
        "analytics", "report", "calendar", "timeline", "multi-column",
        "search filter", "pagination", "form with validation",
    }
)

_MAX_THINKING_ITERATIONS = 16

def _needs_thinking(prompt: str, forced: bool) -> bool:
    """Return True if sequential thinking should be used."""
    if forced:
        return True
    lower = prompt.lower()
    return any(kw in lower for kw in _COMPLEX_KEYWORDS)

_SEQUENTIAL_THINKING_TOOL: dict[str, Any] = {
    "name": "sequentialthinking",
    "description": (
        "Use this tool to think through the layout design step by step before "
        "producing the final JSON. Break down the UI into sections, plan the "
        "component hierarchy, choose spacing and colors, and verify your design "
        "decisions. You can revise earlier thoughts or branch into alternatives. "
        "When you have fully reasoned through the design, stop calling this tool "
        "and output the final JSON directly."
    ),
    "input_schema": {
        "type": "object",
        "required": ["thought", "thoughtNumber", "totalThoughts", "nextThoughtNeeded"],
        "properties": {
            "thought": {
                "type": "string",
                "description": "The current reasoning step.",
            },
            "thoughtNumber": {
                "type": "integer",
                "description": "Current step number (starts at 1).",
                "minimum": 1,
            },
            "totalThoughts": {
                "type": "integer",
                "description": "Estimated total steps needed (can be revised upward).",
                "minimum": 1,
            },
            "nextThoughtNeeded": {
                "type": "boolean",
                "description": "True if more reasoning steps are needed; False when ready to output JSON.",
            },
            "isRevision": {
                "type": "boolean",
                "description": "True if this thought revises a previous one.",
            },
            "revisesThought": {
                "type": "integer",
                "description": "Which thought number is being revised (if isRevision is true).",
                "minimum": 1,
            },
        },
        "additionalProperties": False,
    },
}

class ClaudeClient:
    """Thin async wrapper around the Anthropic Messages API."""

    def __init__(self, settings: Settings) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model
        self._timeout = settings.timeout_seconds
        self._timeout_thinking = settings.timeout_thinking_seconds
        self._max_output_tokens = settings.max_output_tokens
        self._max_retries = settings.max_retries
        self._system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")

    async def complete(self, user_prompt: str, *, use_thinking: bool = False) -> tuple[str, bool]:
        """Send a prompt to Claude and return (raw_text, thinking_was_used).

        All requests use a single direct API call for speed and reliability.
        The use_thinking flag is preserved in the return value for metadata only.
        """
        last_error: Exception | None = None

        for attempt in range(1 + self._max_retries):
            try:
                text = await asyncio.wait_for(
                    self._call_direct(user_prompt),
                    timeout=self._timeout,
                )
                return text, use_thinking
            except asyncio.TimeoutError:
                logger.warning("claude_timeout", attempt=attempt)
                last_error = ClaudeTimeoutError()
            except anthropic.APIStatusError as exc:
                logger.warning("claude_api_error", attempt=attempt, status=exc.status_code)
                last_error = ClaudeError(f"Claude API error: {exc.status_code}")
            except anthropic.APIConnectionError as exc:
                logger.warning("claude_connection_error", attempt=attempt, error=str(exc))
                last_error = ClaudeError(f"Claude connection error: {exc}")

        raise last_error

    async def _call_direct(self, user_prompt: str) -> str:
        stream = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_output_tokens,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=self._timeout,
            stream=True,
        )
        text_parts = []
        async for event in stream:
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                text_parts.append(event.delta.text)
        return "".join(text_parts)

    async def _call_with_thinking(self, user_prompt: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_prompt}
        ]
        thoughts_logged = 0

        for iteration in range(_MAX_THINKING_ITERATIONS):
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_output_tokens,
                system=self._system_prompt,
                tools=[_SEQUENTIAL_THINKING_TOOL],
                messages=messages,
                timeout=self._timeout_thinking,
            )

            if message.stop_reason == "max_tokens":
                # Return whatever text was produced so far;
                # the caller's validation pipeline will catch truncated JSON
                # and the retry mechanism will issue a simpler direct call.
                partial = self._extract_text(message.content)
                logger.warning("claude_max_tokens_hit", partial_length=len(partial))
                return partial if partial else ""

            if message.stop_reason == "end_turn":
                text = self._extract_text(message.content)
                if text:
                    return text
                # end_turn but no text block — Claude only produced tool_use blocks
                # Treat as a failed attempt so the caller can retry
                raise ClaudeError("end_turn with no text output — Claude did not produce JSON")

            if message.stop_reason == "tool_use":
                tool_uses = [b for b in message.content if b.type == "tool_use"]

                if not tool_uses:
                    raise ClaudeError("tool_use stop_reason but no tool_use blocks")

                content_blocks = []
                for block in message.content:
                    if block.type == "text":
                        content_blocks.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        content_blocks.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                messages.append({"role": "assistant", "content": content_blocks})

                tool_results = []
                for tool_use in tool_uses:
                    inp = tool_use.input
                    thoughts_logged += 1
                    logger.debug(
                        "sequential_thought",
                        n=inp.get("thoughtNumber"),
                        total=inp.get("totalThoughts"),
                        next_needed=inp.get("nextThoughtNeeded"),
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": "Reasoning step acknowledged. Continue.",
                        }
                    )

                messages.append({"role": "user", "content": tool_results})
                continue

            raise ClaudeError(f"Unexpected stop_reason: {message.stop_reason}")

        raise ClaudeError(
            f"Sequential thinking exceeded {_MAX_THINKING_ITERATIONS} iterations without producing JSON"
        )

    @staticmethod
    def _extract_text(content: list) -> str:
        """Concatenate all text blocks from a message content list."""
        parts = [block.text for block in content if block.type == "text"]
        return "".join(parts)
