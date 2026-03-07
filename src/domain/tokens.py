

from __future__ import annotations

ALLOWED_NODE_TYPES: frozenset[str] = frozenset(
    {
        "frame",
        "auto_layout",
        "rectangle",
        "ellipse",
        "text",
        "line",
        "group",
        "component_instance",
    }
)

ALLOWED_COLORS: frozenset[str] = frozenset(
    {
        "#FFFFFF", "#000000",

        "#F8FAFC", "#F1F5F9", "#E2E8F0", "#CBD5E1", "#94A3B8",
        "#64748B", "#475569", "#334155", "#1E293B", "#0F172A",

        "#F9FAFB", "#F3F4F6", "#E5E7EB", "#D1D5DB", "#9CA3AF",
        "#6B7280", "#4B5563", "#374151", "#1F2937", "#111827",

        "#EFF6FF", "#DBEAFE", "#BFDBFE", "#93C5FD", "#60A5FA",
        "#3B82F6", "#2563EB", "#1D4ED8", "#1E40AF", "#1E3A8A",

        "#EEF2FF", "#E0E7FF", "#C7D2FE", "#A5B4FC", "#818CF8",
        "#6366F1", "#4F46E5", "#4338CA", "#3730A3", "#312E81",

        "#FAF5FF", "#F3E8FF", "#E9D5FF", "#D8B4FE", "#C084FC",
        "#A855F7", "#9333EA", "#7E22CE", "#6B21A8", "#581C87",

        "#FDF2F8", "#FCE7F3", "#FBCFE8", "#F9A8D4", "#F472B6",
        "#EC4899", "#DB2777", "#BE185D", "#9D174D", "#831843",

        "#FEF2F2", "#FEE2E2", "#FECACA", "#FCA5A5", "#F87171",
        "#EF4444", "#DC2626", "#B91C1C", "#991B1B", "#7F1D1D",

        "#FFF7ED", "#FFEDD5", "#FED7AA", "#FDBA74", "#FB923C",
        "#F97316", "#EA580C", "#C2410C", "#9A3412", "#7C2D12",

        "#FFFBEB", "#FEF3C7", "#FDE68A", "#FCD34D", "#FBBF24",
        "#F59E0B", "#D97706", "#B45309", "#92400E", "#78350F",

        "#F0FDF4", "#DCFCE7", "#BBF7D0", "#86EFAC", "#4ADE80",
        "#22C55E", "#16A34A", "#15803D", "#166534", "#14532D",

        "#F0FDFA", "#CCFBF1", "#99F6E4", "#5EEAD4", "#2DD4BF",
        "#14B8A6", "#0D9488", "#0F766E", "#115E59", "#134E4A",

        "#ECFEFF", "#CFFAFE", "#A5F3FC", "#67E8F9", "#22D3EE",
        "#06B6D4", "#0891B2", "#0E7490", "#155E75", "#164E63",

        "#ECFDF5", "#D1FAE5", "#A7F3D0", "#6EE7B7", "#34D399",
        "#10B981", "#059669", "#047857", "#065F46", "#064E3B",
    }
)

ALLOWED_SPACING: frozenset[int] = frozenset(
    {0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 36, 40, 44, 48, 56, 64, 72, 80, 96}
)

ALLOWED_BORDER_RADII: frozenset[int] = frozenset(
    {0, 2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 9999}
)

ALLOWED_BORDER_WIDTHS: frozenset[int] = frozenset({0, 1, 2, 3, 4})

ALLOWED_SHADOWS: frozenset[str] = frozenset(
    {"none", "sm", "md", "lg", "xl", "2xl", "inner"}
)

ALLOWED_FONT_SIZES: frozenset[int] = frozenset(
    {10, 11, 12, 13, 14, 16, 18, 20, 24, 30, 36, 48, 60, 72, 96}
)

ALLOWED_FONT_FAMILIES: frozenset[str] = frozenset(
    {"Inter", "Roboto", "SF Pro Display", "SF Pro Text", "Roboto Mono", "JetBrains Mono"}
)

ALLOWED_FONT_WEIGHTS: frozenset[int] = frozenset(
    {100, 200, 300, 400, 500, 600, 700, 800, 900}
)

ALLOWED_LINE_HEIGHTS: frozenset[float] = frozenset(
    {1.0, 1.25, 1.375, 1.5, 1.625, 1.75, 2.0}
)

ALLOWED_LETTER_SPACINGS: frozenset[float] = frozenset(
    {-0.05, -0.025, 0.0, 0.025, 0.05, 0.1}
)

ALLOWED_TEXT_ALIGNS: frozenset[str] = frozenset(
    {"left", "center", "right", "justify"}
)

ALLOWED_TEXT_DECORATIONS: frozenset[str] = frozenset(
    {"none", "underline", "line-through"}
)

ALLOWED_TEXT_TRANSFORMS: frozenset[str] = frozenset(
    {"none", "uppercase", "lowercase", "capitalize"}
)

ALLOWED_TEXT_OVERFLOWS: frozenset[str] = frozenset(
    {"visible", "clip", "ellipsis"}
)

ALLOWED_LAYOUT_DIRECTIONS: frozenset[str] = frozenset({"horizontal", "vertical"})

ALLOWED_ALIGN_ITEMS: frozenset[str] = frozenset({"start", "center", "end", "stretch", "baseline"})

ALLOWED_JUSTIFY_CONTENTS: frozenset[str] = frozenset(
    {"start", "center", "end", "space-between", "space-around", "space-evenly"}
)

ALLOWED_OVERFLOWS: frozenset[str] = frozenset({"visible", "hidden", "scroll"})

ALLOWED_WRAPS: frozenset[str] = frozenset({"no-wrap", "wrap"})

ALLOWED_DIMENSION_KEYWORDS: frozenset[str] = frozenset({"fill", "hug"})

ALLOWED_POSITIONS: frozenset[str] = frozenset({"auto", "absolute"})
