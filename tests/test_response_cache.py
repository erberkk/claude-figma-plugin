

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.infrastructure.response_cache import ResponseCache

@pytest.fixture()
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "fixtures"

def make_cache(
    cache_dir: Path,
    *,
    enabled: bool = True,
    prompt_version: str | None = None,
) -> ResponseCache:
    return ResponseCache(
        enabled=enabled,
        cache_dir=cache_dir,
        prompt_version=prompt_version,
    )

class TestResponseCache:
    def test_miss_on_empty_dir(self, cache_dir: Path) -> None:
        cache = make_cache(cache_dir)
        assert cache.get("hello") is None

    def test_round_trip(self, cache_dir: Path) -> None:
        cache = make_cache(cache_dir)
        cache.put("my prompt", '{"node_type": "frame"}', thinking_used=True)
        result = cache.get("my prompt")
        assert result is not None
        raw, thinking = result
        assert raw == '{"node_type": "frame"}'
        assert thinking is True

    def test_different_prompts_do_not_collide(self, cache_dir: Path) -> None:
        cache = make_cache(cache_dir)
        cache.put("prompt A", "response A", thinking_used=False)
        cache.put("prompt B", "response B", thinking_used=True)
        assert cache.get("prompt A") == ("response A", False)
        assert cache.get("prompt B") == ("response B", True)

    def test_same_prompt_is_overwritten(self, cache_dir: Path) -> None:
        cache = make_cache(cache_dir)
        cache.put("p", "first", thinking_used=False)
        cache.put("p", "second", thinking_used=True)
        raw, thinking = cache.get("p")
        assert raw == "second"
        assert thinking is True

    def test_disabled_cache_always_misses(self, cache_dir: Path) -> None:
        cache = make_cache(cache_dir, enabled=False)
        cache.put("p", "response", thinking_used=False)
        result = cache.get("p")
        assert result is None
        assert not cache_dir.exists()

    def test_corrupt_file_returns_none(self, cache_dir: Path) -> None:
        """A malformed JSON file should be handled gracefully."""
        cache = make_cache(cache_dir)
        cache.put("my prompt", "ok", thinking_used=False)
        import hashlib
        key = hashlib.sha256("my prompt".encode()).hexdigest()
        (cache_dir / f"{key}.json").write_text("NOT VALID JSON", encoding="utf-8")

        result = cache.get("my prompt")
        assert result is None

    def test_fixtures_dir_created_automatically(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "fixtures"
        cache = ResponseCache(enabled=True, cache_dir=nested)
        cache.put("x", "y", thinking_used=False)
        assert nested.exists()
        assert (cache.get("x")) == ("y", False)

    def test_json_file_structure(self, cache_dir: Path) -> None:
        """Saved JSON must contain prompt, raw, thinking_used, saved_at."""
        cache = make_cache(cache_dir)
        cache.put("structured", "body", thinking_used=True)
        files = list(cache_dir.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["prompt"] == "structured"
        assert data["raw"] == "body"
        assert data["thinking_used"] is True
        assert "saved_at" in data

class TestCacheVersioning:
    """Tests for prompt_version-based cache invalidation."""

    def test_same_version_hits_cache(self, cache_dir: Path) -> None:
        """Cache hit when prompt_version matches."""
        cache = make_cache(cache_dir, prompt_version="v1abc")
        cache.put("prompt", "response", thinking_used=False)
        result = cache.get("prompt")
        assert result == ("response", False)

    def test_different_version_misses_cache(self, cache_dir: Path) -> None:
        """Cache miss when prompt_version changed (system prompt was edited)."""
        cache_v1 = make_cache(cache_dir, prompt_version="v1abc")
        cache_v1.put("prompt", "old response", thinking_used=False)

        cache_v2 = make_cache(cache_dir, prompt_version="v2def")
        result = cache_v2.get("prompt")
        assert result is None

    def test_no_version_skips_check(self, cache_dir: Path) -> None:
        """When prompt_version is None, version checking is skipped entirely."""
        cache_v1 = make_cache(cache_dir, prompt_version="v1abc")
        cache_v1.put("prompt", "response", thinking_used=True)

        cache_no_ver = make_cache(cache_dir)
        result = cache_no_ver.get("prompt")
        assert result == ("response", True)

    def test_version_stored_in_json(self, cache_dir: Path) -> None:
        """prompt_version should be persisted in the cache JSON file."""
        cache = make_cache(cache_dir, prompt_version="abc123")
        cache.put("p", "r", thinking_used=False)
        files = list(cache_dir.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["prompt_version"] == "abc123"

    def test_version_not_stored_when_none(self, cache_dir: Path) -> None:
        """prompt_version key should be absent when version is None."""
        cache = make_cache(cache_dir, prompt_version=None)
        cache.put("p", "r", thinking_used=False)
        files = list(cache_dir.glob("*.json"))
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert "prompt_version" not in data

    def test_overwrite_updates_version(self, cache_dir: Path) -> None:
        """Re-putting updates the stored version."""
        cache_v1 = make_cache(cache_dir, prompt_version="old")
        cache_v1.put("prompt", "response v1", thinking_used=False)

        cache_v2 = make_cache(cache_dir, prompt_version="new")
        cache_v2.put("prompt", "response v2", thinking_used=True)

        result = cache_v2.get("prompt")
        assert result == ("response v2", True)

