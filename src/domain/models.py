
from __future__ import annotations

import enum
from typing import Optional

from pydantic import BaseModel, Field

class NodeType(str, enum.Enum):
    FRAME = "frame"
    AUTO_LAYOUT = "auto_layout"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    TEXT = "text"
    LINE = "line"
    GROUP = "group"
    COMPONENT_INSTANCE = "component_instance"

class NodeStyle(BaseModel):
    """Style properties for a Figma node.

    Every property is optional — the validator enforces token membership.
    """

    fill: Optional[str] = None
    stroke: Optional[str] = None
    border_width: Optional[int] = None
    border_color: Optional[str] = None

    corner_radius: Optional[int] = None
    corner_radius_top_left: Optional[int] = None
    corner_radius_top_right: Optional[int] = None
    corner_radius_bottom_left: Optional[int] = None
    corner_radius_bottom_right: Optional[int] = None

    padding_top: Optional[int] = None
    padding_right: Optional[int] = None
    padding_bottom: Optional[int] = None
    padding_left: Optional[int] = None
    gap: Optional[int] = None

    layout_direction: Optional[str] = None
    align_items: Optional[str] = None
    justify_content: Optional[str] = None
    wrap: Optional[str] = None

    width: Optional[int | str] = None
    height: Optional[int | str] = None
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    flex_grow: Optional[int] = Field(None, ge=0, le=1)

    position: Optional[str] = None
    top: Optional[int] = None
    right: Optional[int] = None
    bottom: Optional[int] = None
    left: Optional[int] = None

    shadow: Optional[str] = None

    font_size: Optional[int] = None
    font_family: Optional[str] = None
    font_weight: Optional[int] = None
    line_height: Optional[float] = None
    letter_spacing: Optional[float] = None
    text_align: Optional[str] = None
    text_decoration: Optional[str] = None
    text_transform: Optional[str] = None
    text_overflow: Optional[str] = None
    text_content: Optional[str] = None
    max_lines: Optional[int] = Field(None, ge=1)

    opacity: Optional[float] = Field(None, ge=0.0, le=1.0)
    overflow: Optional[str] = None
    visible: Optional[bool] = None

    component_name: Optional[str] = None
    icon_name: Optional[str] = None
    image_placeholder: Optional[str] = None
    svg_markup: Optional[str] = None

class FigmaNode(BaseModel):
    """Recursive Figma node tree."""

    node_type: NodeType
    name: str
    style: NodeStyle = Field(default_factory=NodeStyle)
    children: list[FigmaNode] = Field(default_factory=list)

class GenerateRequest(BaseModel):
    """Inbound request from the Figma plugin."""

    prompt: str = Field(..., min_length=1, max_length=4000)
    use_thinking: bool = Field(
        False,
        description=(
            "Enable MCP-style sequential thinking for complex prompts. "
            "The model will chain intermediate reasoning steps before producing JSON. "
            "Auto-enabled for prompts containing complexity keywords."
        ),
    )

class GenerateResponse(BaseModel):
    """Outbound response to the Figma plugin."""

    layout: FigmaNode
    retried: bool = False
    thinking_used: bool = False
