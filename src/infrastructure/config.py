from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or .env file."""

    anthropic_api_key: str
    api_key: str = "changeme"
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"
    max_retries: int = 1
    timeout_seconds: int = 300
    timeout_thinking_seconds: int = 300
    max_output_tokens: int = 32000
    max_input_size: int = 10_240
    claude_model: str = "claude-sonnet-4-6"
    claude_cache_enabled: bool = False
    claude_cache_dir: Path = Path("fixtures")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
