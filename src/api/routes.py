
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from src.domain.models import GenerateRequest, GenerateResponse, FigmaNode
from src.infrastructure.config import get_settings
from src.services.layout_service import LayoutService
from src.services.validator import validate_output

router = APIRouter(prefix="/api/v1", tags=["layout"])

_VALID_CACHE_KEY = re.compile(r"^[a-fA-F0-9]{64}$")

def _get_layout_service() -> LayoutService:
    """FastAPI dependency — returns the LayoutService singleton from app state.

    The actual instance is set in main.py via app.state.
    This is overridden in tests.
    """
    from src.main import _app_state

    return _app_state["layout_service"]

@router.post("/generate", response_model=GenerateResponse)
async def generate_layout(
    request: GenerateRequest,
    service: LayoutService = Depends(_get_layout_service),
) -> GenerateResponse:
    """Accept a natural-language prompt and return a validated Figma layout tree."""
    return await service.generate(request.prompt, use_thinking=request.use_thinking)

@router.get("/fixtures")
async def list_fixtures() -> dict:
    """List all available cached fixtures."""
    settings = get_settings()
    fixtures_dir = settings.claude_cache_dir
    
    if not fixtures_dir.exists():
        return {"fixtures": []}
    
    fixtures = []
    for file_path in fixtures_dir.glob("*.json"):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            fixtures.append({
                "key": file_path.stem,
                "prompt": data.get("prompt", ""),
                "thinking_used": data.get("thinking_used", False),
                "saved_at": data.get("saved_at", ""),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    
    fixtures.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
    return {"fixtures": fixtures}

@router.get("/fixtures/{key}")
async def get_fixture(key: str) -> GenerateResponse:
    """Load a specific fixture by its cache key."""
    if not _VALID_CACHE_KEY.match(key):
        raise HTTPException(status_code=400, detail="Invalid fixture key format")

    settings = get_settings()
    fixture_path = settings.claude_cache_dir / f"{key}.json"
    
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail="Fixture not found")
    
    try:
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        raw = data["raw"]
        thinking_used = data.get("thinking_used", False)
        
        layout_data = validate_output(raw)
        layout = FigmaNode.model_validate(layout_data)
        
        return GenerateResponse(
            layout=layout,
            retried=False,
            thinking_used=thinking_used
        )
    except (json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(status_code=500, detail=f"Invalid fixture format: {exc}")
