
from __future__ import annotations

import json

import pytest

from src.domain.exceptions import ValidationError
from src.services.validator import enforce_tokens, parse_json, validate_output, validate_schema

def _valid_node() -> dict:
    """A realistic card component using the expanded design tokens."""
    return {
        "node_type": "auto_layout",
        "name": "DashboardCard",
        "style": {
            "fill": "#FFFFFF",
            "padding_top": 24,
            "padding_right": 24,
            "padding_bottom": 24,
            "padding_left": 24,
            "gap": 16,
            "layout_direction": "vertical",
            "align_items": "stretch",
            "corner_radius": 12,
            "shadow": "md",
            "width": 320,
        },
        "children": [
            {
                "node_type": "auto_layout",
                "name": "CardHeader",
                "style": {
                    "layout_direction": "horizontal",
                    "align_items": "center",
                    "justify_content": "space-between",
                    "gap": 8,
                },
                "children": [
                    {
                        "node_type": "text",
                        "name": "Title",
                        "style": {
                            "font_size": 18,
                            "font_family": "Inter",
                            "font_weight": 600,
                            "text_content": "Revenue",
                            "fill": "#1E293B",
                            "line_height": 1.5,
                        },
                    },
                    {
                        "node_type": "component_instance",
                        "name": "MoreIcon",
                        "style": {"icon_name": "more-horizontal", "component_name": "Icon"},
                    },
                ],
            },
            {
                "node_type": "text",
                "name": "Value",
                "style": {
                    "font_size": 36,
                    "font_family": "Inter",
                    "font_weight": 700,
                    "text_content": "$48,250",
                    "fill": "#0F172A",
                    "letter_spacing": -0.025,
                },
            },
            {
                "node_type": "auto_layout",
                "name": "BadgeRow",
                "style": {"layout_direction": "horizontal", "gap": 8, "align_items": "center"},
                "children": [
                    {
                        "node_type": "ellipse",
                        "name": "StatusDot",
                        "style": {"fill": "#22C55E", "width": 8, "height": 8},
                    },
                    {
                        "node_type": "text",
                        "name": "Change",
                        "style": {
                            "font_size": 14,
                            "font_family": "Inter",
                            "font_weight": 500,
                            "text_content": "+12.5%",
                            "fill": "#16A34A",
                        },
                    },
                ],
            },
            {
                "node_type": "line",
                "name": "Divider",
                "style": {"stroke": "#E2E8F0", "width": "fill", "border_width": 1},
            },
            {
                "node_type": "rectangle",
                "name": "InputField",
                "style": {
                    "border_width": 1,
                    "border_color": "#CBD5E1",
                    "corner_radius": 6,
                    "height": 40,
                    "width": "fill",
                    "fill": "#FFFFFF",
                },
            },
        ],
    }

class TestParseJson:
    def test_valid_json(self):
        raw = json.dumps({"node_type": "frame", "name": "x"})
        result = parse_json(raw)
        assert result["node_type"] == "frame"

    def test_strips_markdown_fences(self):
        raw = '```json\n{"node_type": "frame", "name": "x"}\n```'
        result = parse_json(raw)
        assert result["name"] == "x"

    def test_invalid_json_raises(self):
        with pytest.raises(ValidationError, match="Invalid JSON"):
            parse_json("not json at all")

    def test_non_object_raises(self):
        with pytest.raises(ValidationError, match="Root must be a JSON object"):
            parse_json("[1, 2, 3]")

class TestValidateSchema:
    def test_valid_node_passes(self):
        validate_schema(_valid_node())

    def test_missing_node_type_fails(self):
        with pytest.raises(ValidationError, match="Schema validation failed"):
            validate_schema({"name": "x"})

    def test_extra_property_fails(self):
        node = _valid_node()
        node["unknown_field"] = True
        with pytest.raises(ValidationError, match="Schema validation failed"):
            validate_schema(node)

    def test_new_node_types_accepted(self):
        for nt in ("ellipse", "line", "group"):
            validate_schema({"node_type": nt, "name": f"test_{nt}"})

class TestEnforceTokens:
    def test_valid_tree_no_violations(self):
        violations = enforce_tokens(_valid_node())
        assert violations == []

    def test_invalid_color(self):
        node = {"node_type": "rectangle", "name": "Box", "style": {"fill": "#FF0000"}}
        violations = enforce_tokens(node)
        assert any("disallowed color" in v for v in violations)

    def test_invalid_spacing(self):
        node = {"node_type": "auto_layout", "name": "X", "style": {"gap": 7}}
        violations = enforce_tokens(node)
        assert any("disallowed spacing" in v for v in violations)

    def test_invalid_font_size(self):
        node = {"node_type": "text", "name": "T", "style": {"font_size": 15}}
        violations = enforce_tokens(node)
        assert any("disallowed font size" in v for v in violations)

    def test_invalid_font_family(self):
        node = {"node_type": "text", "name": "T", "style": {"font_family": "Comic Sans"}}
        violations = enforce_tokens(node)
        assert any("disallowed font family" in v for v in violations)

    def test_invalid_node_type(self):
        node = {"node_type": "ellipse_star", "name": "X"}
        violations = enforce_tokens(node)
        assert any("disallowed node_type" in v for v in violations)

    def test_invalid_dimension_keyword(self):
        node = {"node_type": "rectangle", "name": "X", "style": {"width": "auto"}}
        violations = enforce_tokens(node)
        assert any("disallowed dimension" in v for v in violations)

    def test_invalid_shadow(self):
        node = {"node_type": "rectangle", "name": "X", "style": {"shadow": "huge"}}
        violations = enforce_tokens(node)
        assert any("disallowed shadow" in v for v in violations)

    def test_valid_shadow(self):
        node = {"node_type": "rectangle", "name": "X", "style": {"shadow": "lg"}}
        violations = enforce_tokens(node)
        assert violations == []

    def test_invalid_border_radius(self):
        node = {"node_type": "rectangle", "name": "X", "style": {"corner_radius": 5}}
        violations = enforce_tokens(node)
        assert any("disallowed border radius" in v for v in violations)

    def test_pill_radius(self):
        node = {"node_type": "ellipse", "name": "Avatar", "style": {"corner_radius": 9999}}
        violations = enforce_tokens(node)
        assert violations == []

    def test_invalid_border_width(self):
        node = {"node_type": "rectangle", "name": "X", "style": {"border_width": 5}}
        violations = enforce_tokens(node)
        assert any("disallowed border width" in v for v in violations)

    def test_invalid_border_color(self):
        node = {"node_type": "rectangle", "name": "X", "style": {"border_color": "#ABCDEF"}}
        violations = enforce_tokens(node)
        assert any("disallowed color" in v for v in violations)

    def test_invalid_text_align(self):
        node = {"node_type": "text", "name": "T", "style": {"text_align": "middle"}}
        violations = enforce_tokens(node)
        assert any("disallowed text align" in v for v in violations)

    def test_valid_text_properties(self):
        node = {
            "node_type": "text", "name": "T",
            "style": {
                "text_align": "center", "text_decoration": "underline",
                "text_transform": "uppercase", "text_overflow": "ellipsis",
                "line_height": 1.5, "letter_spacing": -0.025,
            },
        }
        violations = enforce_tokens(node)
        assert violations == []

    def test_invalid_justify_content(self):
        node = {"node_type": "auto_layout", "name": "X", "style": {"justify_content": "between"}}
        violations = enforce_tokens(node)
        assert any("disallowed value" in v for v in violations)

    def test_valid_layout_wrap(self):
        node = {"node_type": "auto_layout", "name": "Grid", "style": {"wrap": "wrap", "overflow": "hidden"}}
        violations = enforce_tokens(node)
        assert violations == []

    def test_invalid_position(self):
        node = {"node_type": "frame", "name": "X", "style": {"position": "relative"}}
        violations = enforce_tokens(node)
        assert any("disallowed value" in v for v in violations)

    def test_deep_nested_violation(self):
        """Token violation 3 levels deep should still be caught."""
        node = {
            "node_type": "frame", "name": "Root",
            "children": [{
                "node_type": "auto_layout", "name": "L1",
                "children": [{
                    "node_type": "text", "name": "L2",
                    "style": {"font_weight": 350},
                }],
            }],
        }
        violations = enforce_tokens(node)
        assert any("disallowed font weight" in v for v in violations)
        assert any("children[0].children[0]" in v for v in violations)

class TestValidateOutput:
    def test_valid_full_tree(self):
        raw = json.dumps(_valid_node())
        data = validate_output(raw)
        assert data["node_type"] == "auto_layout"

    def test_rejects_invalid_json(self):
        with pytest.raises(ValidationError, match="Invalid JSON"):
            validate_output("{broken")

    def test_rejects_token_violation(self):
        node = _valid_node()
        node["style"]["fill"] = "#BADA55"
        with pytest.raises(ValidationError, match="Design token violations"):
            validate_output(json.dumps(node))

    def test_rejects_invalid_shadow(self):
        node = _valid_node()
        node["style"]["shadow"] = "xl2"
        with pytest.raises(ValidationError):
            validate_output(json.dumps(node))
