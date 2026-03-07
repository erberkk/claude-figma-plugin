
from __future__ import annotations

import json
import re
from typing import Any

import jsonschema

from src.domain.exceptions import ValidationError
from src.domain.schemas import FIGMA_NODE_SCHEMA
from src.domain.tokens import (
    ALLOWED_ALIGN_ITEMS,
    ALLOWED_BORDER_RADII,
    ALLOWED_BORDER_WIDTHS,
    ALLOWED_COLORS,
    ALLOWED_DIMENSION_KEYWORDS,
    ALLOWED_FONT_FAMILIES,
    ALLOWED_FONT_SIZES,
    ALLOWED_FONT_WEIGHTS,
    ALLOWED_JUSTIFY_CONTENTS,
    ALLOWED_LAYOUT_DIRECTIONS,
    ALLOWED_LETTER_SPACINGS,
    ALLOWED_LINE_HEIGHTS,
    ALLOWED_NODE_TYPES,
    ALLOWED_OVERFLOWS,
    ALLOWED_POSITIONS,
    ALLOWED_SHADOWS,
    ALLOWED_SPACING,
    ALLOWED_TEXT_ALIGNS,
    ALLOWED_TEXT_DECORATIONS,
    ALLOWED_TEXT_OVERFLOWS,
    ALLOWED_TEXT_TRANSFORMS,
    ALLOWED_WRAPS,
)

def parse_json(raw: str) -> dict[str, Any]:
    """Parse raw string as JSON. Aggressively extracts first valid JSON object."""
    text = raw.strip()
    
    # Try finding markdown code block
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    
    # Stack-based isolation to prevent "Extra data" trailing chars
    start = text.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
                
            if not in_string:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0: # Found the closed object
                        text = text[start:i+1]
                        break
        # If we didn't hit depth==0, it means it's truncated or malformed;
        # we just pass `text` and let json.loads fail naturally so retry can kick in.
    
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON: {exc}", details={"raw_preview": text[:200]})
    if not isinstance(data, dict):
        raise ValidationError("Root must be a JSON object")
    return data

def validate_schema(data: dict[str, Any]) -> None:
    """Validate raw dict against the Figma node JSON Schema."""
    try:
        jsonschema.validate(instance=data, schema=FIGMA_NODE_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise ValidationError(
            f"Schema validation failed: {exc.message}",
            details={"path": list(exc.absolute_path)},
        )

def enforce_tokens(node: dict[str, Any], *, path: str = "root") -> list[str]:
    """Recursively validate that all style values use allowed design tokens.

    Returns a list of violation messages. Empty list = valid.
    """
    violations: list[str] = []
    style = node.get("style", {})

    nt = node.get("node_type", "")
    if nt not in ALLOWED_NODE_TYPES:
        violations.append(f"{path}: disallowed node_type '{nt}'")

    for key in ("fill", "stroke", "border_color"):
        val = style.get(key)
        if val is not None and val.upper() not in ALLOWED_COLORS:
            violations.append(f"{path}.style.{key}: disallowed color '{val}'")

    spacing_keys = (
        "padding_top", "padding_right", "padding_bottom", "padding_left",
        "padding_horizontal", "padding_vertical", "gap",
    )
    for key in spacing_keys:
        val = style.get(key)
        if val is not None and val not in ALLOWED_SPACING:
            violations.append(f"{path}.style.{key}: disallowed spacing value {val}")

    for key in ("corner_radius", "corner_radius_top_left", "corner_radius_top_right",
                "corner_radius_bottom_left", "corner_radius_bottom_right"):
        val = style.get(key)
        if val is not None and val not in ALLOWED_BORDER_RADII:
            violations.append(f"{path}.style.{key}: disallowed border radius {val}")

    for key in ("border_width", "border_top_width", "border_right_width",
                 "border_bottom_width", "border_left_width"):
        val = style.get(key)
        if val is not None and val not in ALLOWED_BORDER_WIDTHS:
            violations.append(f"{path}.style.{key}: disallowed border width {val}")

    for key in ("border_color", "border_top_color", "border_right_color",
                 "border_bottom_color", "border_left_color"):
        val = style.get(key)
        if val is not None and val.upper() not in ALLOWED_COLORS:
            violations.append(f"{path}.style.{key}: disallowed color '{val}'")

    shadow = style.get("shadow")
    if shadow is not None and shadow not in ALLOWED_SHADOWS:
        violations.append(f"{path}.style.shadow: disallowed shadow '{shadow}'")

    for key in ("width", "height"):
        val = style.get(key)
        if val is not None and isinstance(val, str) and val not in ALLOWED_DIMENSION_KEYWORDS:
            violations.append(f"{path}.style.{key}: disallowed dimension '{val}'")

    fs = style.get("font_size")
    if fs is not None and fs not in ALLOWED_FONT_SIZES:
        violations.append(f"{path}.style.font_size: disallowed font size {fs}")

    ff = style.get("font_family")
    if ff is not None and ff not in ALLOWED_FONT_FAMILIES:
        violations.append(f"{path}.style.font_family: disallowed font family '{ff}'")

    fw = style.get("font_weight")
    if fw is not None and fw not in ALLOWED_FONT_WEIGHTS:
        violations.append(f"{path}.style.font_weight: disallowed font weight {fw}")

    lh = style.get("line_height")
    if lh is not None and lh not in ALLOWED_LINE_HEIGHTS:
        violations.append(f"{path}.style.line_height: disallowed line height {lh}")

    ls = style.get("letter_spacing")
    if ls is not None and ls not in ALLOWED_LETTER_SPACINGS:
        violations.append(f"{path}.style.letter_spacing: disallowed letter spacing {ls}")

    ta = style.get("text_align")
    if ta is not None and ta not in ALLOWED_TEXT_ALIGNS:
        violations.append(f"{path}.style.text_align: disallowed text align '{ta}'")

    td = style.get("text_decoration")
    if td is not None and td not in ALLOWED_TEXT_DECORATIONS:
        violations.append(f"{path}.style.text_decoration: disallowed text decoration '{td}'")

    tt = style.get("text_transform")
    if tt is not None and tt not in ALLOWED_TEXT_TRANSFORMS:
        violations.append(f"{path}.style.text_transform: disallowed text transform '{tt}'")

    to = style.get("text_overflow")
    if to is not None and to not in ALLOWED_TEXT_OVERFLOWS:
        violations.append(f"{path}.style.text_overflow: disallowed text overflow '{to}'")

    ld = style.get("layout_direction")
    if ld is not None and ld not in ALLOWED_LAYOUT_DIRECTIONS:
        violations.append(f"{path}.style.layout_direction: disallowed value '{ld}'")

    ai = style.get("align_items")
    if ai is not None and ai not in ALLOWED_ALIGN_ITEMS:
        violations.append(f"{path}.style.align_items: disallowed value '{ai}'")

    jc = style.get("justify_content")
    if jc is not None and jc not in ALLOWED_JUSTIFY_CONTENTS:
        violations.append(f"{path}.style.justify_content: disallowed value '{jc}'")

    wr = style.get("wrap")
    if wr is not None and wr not in ALLOWED_WRAPS:
        violations.append(f"{path}.style.wrap: disallowed value '{wr}'")

    ov = style.get("overflow")
    if ov is not None and ov not in ALLOWED_OVERFLOWS:
        violations.append(f"{path}.style.overflow: disallowed value '{ov}'")

    pos = style.get("position")
    if pos is not None and pos not in ALLOWED_POSITIONS:
        violations.append(f"{path}.style.position: disallowed value '{pos}'")

    for i, child in enumerate(node.get("children", [])):
        violations.extend(enforce_tokens(child, path=f"{path}.children[{i}]"))

    return violations

def validate_output(raw: str) -> dict[str, Any]:
    """Full validation pipeline: parse → schema → tokens. Raises on failure."""
    data = parse_json(raw)
    validate_schema(data)
    violations = enforce_tokens(data)
    if violations:
        raise ValidationError(
            "Design token violations found",
            details={"violations": violations},
        )
    return data
