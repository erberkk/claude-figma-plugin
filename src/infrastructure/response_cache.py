from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

class ResponseCache:
    """Read/write Claude responses from/to disk.

    Parameters
    ----------
    enabled:
        When ``False`` (default in production) the cache is a no-op —
        ``get`` always returns ``None`` and ``put`` does nothing.
    cache_dir:
        Directory where ``.json`` fixture files are stored.
        Created automatically if it does not exist.
    prompt_version:
        Optional hash of the system prompt. When set, cached entries
        whose ``prompt_version`` differs are treated as a cache miss.
        This ensures that system prompt changes automatically invalidate
        stale cache entries without manual cleanup.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        cache_dir: Path,
        prompt_version: str | None = None,
    ) -> None:
        self._enabled = enabled
        self._dir = cache_dir
        self._version = prompt_version
        if enabled:
            self._dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                "response_cache_enabled",
                cache_dir=str(self._dir),
                prompt_version=self._version,
            )
        else:
            logger.debug("response_cache_disabled")

    def get(self, prompt: str) -> tuple[str, bool] | None:
        """Return ``(raw_text, thinking_used)`` from cache, or ``None`` on miss."""
        if not self._enabled:
            return None

        path = self._path_for(prompt)
        if not path.exists():
            logger.debug("cache_miss", key=path.stem)
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw: str = data["raw"]
            thinking_used: bool = data.get("thinking_used", False)

            if self._version is not None:
                stored_version = data.get("prompt_version")
                if stored_version != self._version:
                    logger.info(
                        "cache_version_mismatch",
                        key=path.stem,
                        stored=stored_version,
                        current=self._version,
                    )
                    return None

            logger.info("cache_hit", key=path.stem)
            return raw, thinking_used
        except (KeyError, json.JSONDecodeError) as exc:
            logger.warning("cache_read_error", key=path.stem, error=str(exc))
            return None

    def put(self, prompt: str, raw: str, thinking_used: bool) -> None:
        """Persist a Claude response to disk."""
        if not self._enabled:
            return

        path = self._path_for(prompt)
        payload: dict = {
            "prompt": prompt,
            "raw": raw,
            "thinking_used": thinking_used,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        if self._version is not None:
            payload["prompt_version"] = self._version

        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("cache_saved", key=path.stem)

    def _path_for(self, prompt: str) -> Path:
        key = hashlib.sha256(prompt.encode()).hexdigest()
        return self._dir / f"{key}.json"
