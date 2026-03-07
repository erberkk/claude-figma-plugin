// Figma Plugin — Node Creation Engine
// Receives a layout JSON tree from the UI and creates Figma nodes recursively.

// ──────────────────────────────────────────────
// Shadow presets (matching backend tokens)
// ──────────────────────────────────────────────
const SHADOWS = {
  none: [],
  sm: [{ type: "DROP_SHADOW", color: { r: 0, g: 0, b: 0, a: 0.05 }, offset: { x: 0, y: 1 }, radius: 2, spread: 0, visible: true, blendMode: "NORMAL" }],
  md: [{ type: "DROP_SHADOW", color: { r: 0, g: 0, b: 0, a: 0.1 }, offset: { x: 0, y: 4 }, radius: 6, spread: -1, visible: true, blendMode: "NORMAL" }],
  lg: [{ type: "DROP_SHADOW", color: { r: 0, g: 0, b: 0, a: 0.1 }, offset: { x: 0, y: 10 }, radius: 15, spread: -3, visible: true, blendMode: "NORMAL" }],
  xl: [{ type: "DROP_SHADOW", color: { r: 0, g: 0, b: 0, a: 0.1 }, offset: { x: 0, y: 20 }, radius: 25, spread: -5, visible: true, blendMode: "NORMAL" }],
  "2xl": [{ type: "DROP_SHADOW", color: { r: 0, g: 0, b: 0, a: 0.15 }, offset: { x: 0, y: 25 }, radius: 50, spread: -12, visible: true, blendMode: "NORMAL" }],
  inner: [{ type: "INNER_SHADOW", color: { r: 0, g: 0, b: 0, a: 0.06 }, offset: { x: 0, y: 2 }, radius: 4, spread: 0, visible: true, blendMode: "NORMAL" }],
};

// ──────────────────────────────────────────────
// Hex → Figma color
// ──────────────────────────────────────────────
function hexToRgb(hex) {
  hex = hex.replace("#", "");
  return {
    r: parseInt(hex.substring(0, 2), 16) / 255,
    g: parseInt(hex.substring(2, 4), 16) / 255,
    b: parseInt(hex.substring(4, 6), 16) / 255,
  };
}

function solidPaint(hex) {
  return [{ type: "SOLID", color: hexToRgb(hex) }];
}

// ──────────────────────────────────────────────
// Font loading
// ──────────────────────────────────────────────
const FONT_MAP = {
  "Inter": "Inter",
  "Roboto": "Roboto",
  "SF Pro Display": "SF Pro Display",
  "SF Pro Text": "SF Pro Text",
  "Roboto Mono": "Roboto Mono",
  "JetBrains Mono": "JetBrains Mono",
};

const WEIGHT_MAP = {
  100: "Thin",
  200: "ExtraLight",
  300: "Light",
  400: "Regular",
  500: "Medium",
  600: "SemiBold",
  700: "Bold",
  800: "ExtraBold",
  900: "Black",
};

async function loadFont(family, weight) {
  const fontFamily = FONT_MAP[family] || "Inter";
  const fontStyle = WEIGHT_MAP[weight] || "Regular";
  try {
    await figma.loadFontAsync({ family: fontFamily, style: fontStyle });
    return { family: fontFamily, style: fontStyle };
  } catch (_e) {
    // Fallback to Inter Regular if font not available
    await figma.loadFontAsync({ family: "Inter", style: "Regular" });
    return { family: "Inter", style: "Regular" };
  }
}

// ──────────────────────────────────────────────
// Dimension helper
// ──────────────────────────────────────────────
function applySize(node, style, prop, axis) {
  const val = style[prop];
  if (val === undefined || val === null) return;

  const parentIsAutoLayout = node.parent && "layoutMode" in node.parent && node.parent.layoutMode !== "NONE";

  if (val === "fill") {
    if (parentIsAutoLayout) {
      if (axis === "width") node.layoutSizingHorizontal = "FILL";
      else node.layoutSizingVertical = "FILL";
    } else {
      // Root node or non-auto_layout parent: use sensible defaults
      const fallback = axis === "width" ? 1440 : 900;
      if (axis === "width") node.resize(fallback, node.height);
      else node.resize(node.width, fallback);
    }
  } else if (val === "hug") {
    if (parentIsAutoLayout) {
      if (axis === "width") node.layoutSizingHorizontal = "HUG";
      else node.layoutSizingVertical = "HUG";
    }
    // For non-auto_layout parents, "hug" is a no-op (node sizes to its content naturally)
  } else if (typeof val === "number") {
    if (axis === "width") node.resize(val, node.height);
    else node.resize(node.width, val);
  }
}

// ──────────────────────────────────────────────
// Apply common style properties
// ──────────────────────────────────────────────
function applyCommonStyle(node, style) {
  // Fill
  if (style.fill) node.fills = solidPaint(style.fill);

  // Stroke / Border (uniform)
  if (style.stroke || style.border_color) {
    node.strokes = solidPaint(style.stroke || style.border_color);
    node.strokeWeight = style.border_width || 1;
  }

  // Per-side borders — Figma supports individual stroke weights
  const hasPerSideBorder =
    style.border_top_width != null ||
    style.border_right_width != null ||
    style.border_bottom_width != null ||
    style.border_left_width != null;

  if (hasPerSideBorder && "strokeTopWeight" in node) {
    // Determine stroke color from per-side or fallback to uniform
    const borderCol =
      style.border_top_color ||
      style.border_bottom_color ||
      style.border_left_color ||
      style.border_right_color ||
      style.border_color ||
      style.stroke;
    if (borderCol) node.strokes = solidPaint(borderCol);

    node.strokeTopWeight = style.border_top_width || 0;
    node.strokeRightWeight = style.border_right_width || 0;
    node.strokeBottomWeight = style.border_bottom_width || 0;
    node.strokeLeftWeight = style.border_left_width || 0;
  }

  // Corner radius
  if (style.corner_radius != null) {
    node.cornerRadius = style.corner_radius === 9999 ? 999 : style.corner_radius;
  }
  if (style.corner_radius_top_left != null) node.topLeftRadius = style.corner_radius_top_left;
  if (style.corner_radius_top_right != null) node.topRightRadius = style.corner_radius_top_right;
  if (style.corner_radius_bottom_left != null) node.bottomLeftRadius = style.corner_radius_bottom_left;
  if (style.corner_radius_bottom_right != null) node.bottomRightRadius = style.corner_radius_bottom_right;

  // Opacity
  if (style.opacity != null) node.opacity = style.opacity;

  // Visibility
  if (style.visible === false) node.visible = false;

  // Shadow
  if (style.shadow && SHADOWS[style.shadow]) {
    node.effects = SHADOWS[style.shadow];
  }

  // Dimensions
  applySize(node, style, "width", "width");
  applySize(node, style, "height", "height");

  // Overflow (clip content)
  if (style.overflow === "hidden" || style.overflow === "scroll") {
    if ("clipsContent" in node) node.clipsContent = true;
  }
}

// ──────────────────────────────────────────────
// Apply auto-layout properties
// ──────────────────────────────────────────────
function applyAutoLayout(node, style) {
  node.layoutMode = style.layout_direction === "horizontal" ? "HORIZONTAL" : "VERTICAL";

  if (style.gap != null) node.itemSpacing = style.gap;

  // Padding — expand shorthands, explicit ternaries for Figma sandbox JS compatibility
  var pt = style.padding_top != null ? style.padding_top : (style.padding_vertical != null ? style.padding_vertical : 0);
  var pb = style.padding_bottom != null ? style.padding_bottom : (style.padding_vertical != null ? style.padding_vertical : 0);
  var pl = style.padding_left != null ? style.padding_left : (style.padding_horizontal != null ? style.padding_horizontal : 0);
  var pr = style.padding_right != null ? style.padding_right : (style.padding_horizontal != null ? style.padding_horizontal : 0);
  node.paddingTop = pt;
  node.paddingBottom = pb;
  node.paddingLeft = pl;
  node.paddingRight = pr;

  // Alignment
  const alignMap = {
    start: "MIN",
    center: "CENTER",
    end: "MAX",
    stretch: "MIN",
    baseline: "BASELINE",
  };
  if (style.align_items) node.counterAxisAlignItems = alignMap[style.align_items] || "MIN";

  const justifyMap = { start: "MIN", center: "CENTER", end: "MAX", "space-between": "SPACE_BETWEEN" };
  if (style.justify_content) node.primaryAxisAlignItems = justifyMap[style.justify_content] || "MIN";

  // Wrap
  if (style.wrap === "wrap") node.layoutWrap = "WRAP";

  // Sizing
  node.primaryAxisSizingMode = "AUTO";
  node.counterAxisSizingMode = "AUTO";
}

// ──────────────────────────────────────────────
// Recursive node creator
// ──────────────────────────────────────────────
let nodeCount = 0;

async function createNode(data, parent) {
  const style = data.style || {};
  let node;

  switch (data.node_type) {
    case "frame": {
      node = figma.createFrame();
      node.fills = style.fill ? solidPaint(style.fill) : []; // transparent by default
      break;
    }

    case "auto_layout": {
      node = figma.createFrame();
      applyAutoLayout(node, style);
      if (!style.fill) node.fills = [];
      break;
    }

    case "rectangle": {
      // If rectangle has children, upgrade to a frame so appendChild works
      if (data.children && data.children.length > 0) {
        node = figma.createFrame();
        node.fills = style.fill ? solidPaint(style.fill) : [];
      } else {
        node = figma.createRectangle();
      }
      break;
    }

    case "ellipse": {
      // If ellipse has children, upgrade to a frame with full border-radius
      if (data.children && data.children.length > 0) {
        node = figma.createFrame();
        node.fills = style.fill ? solidPaint(style.fill) : [];
        node.cornerRadius = 9999;
      } else {
        node = figma.createEllipse();
      }
      break;
    }

    case "text": {
      node = figma.createText();
      const fontLoaded = await loadFont(style.font_family || "Inter", style.font_weight || 400);
      node.fontName = fontLoaded;
      if (style.text_content) node.characters = style.text_content;
      if (style.font_size) node.fontSize = style.font_size;
      if (style.line_height) node.lineHeight = { unit: "PERCENT", value: style.line_height * 100 };
      if (style.letter_spacing) node.letterSpacing = { unit: "PERCENT", value: style.letter_spacing * 100 };

      const textAlignMap = { left: "LEFT", center: "CENTER", right: "RIGHT", justify: "JUSTIFIED" };
      if (style.text_align) node.textAlignHorizontal = textAlignMap[style.text_align] || "LEFT";

      if (style.text_decoration === "underline") node.textDecoration = "UNDERLINE";
      if (style.text_decoration === "line-through") node.textDecoration = "STRIKETHROUGH";

      if (style.text_transform === "uppercase") node.textCase = "UPPER";
      if (style.text_transform === "lowercase") node.textCase = "LOWER";
      if (style.text_transform === "capitalize") node.textCase = "TITLE";

      if (style.text_overflow === "ellipsis") node.textTruncation = "ENDING";
      if (style.max_lines) node.maxLines = style.max_lines;
      break;
    }

    case "line": {
      node = figma.createLine();
      if (style.width && typeof style.width === "number") {
        node.resize(style.width, 0);
      } else {
        node.resize(200, 0);  // default line length
      }
      if (style.stroke) node.strokes = solidPaint(style.stroke);
      break;
    }

    case "group": {
      // Groups need at least one child; create a frame as container
      node = figma.createFrame();
      node.fills = [];
      break;
    }

    case "component_instance": {
      // If SVG markup is provided, create vector nodes from SVG
      if (style.svg_markup) {
        try {
          const svgNodes = figma.createNodeFromSvg(style.svg_markup);
          // createNodeFromSvg returns a frame containing the vector(s)
          // If it's a single vector, use it directly; otherwise use the frame
          if (svgNodes.children.length === 1) {
            node = svgNodes.children[0];
            svgNodes.remove(); // Remove the wrapper frame
          } else {
            node = svgNodes;
          }
          // Apply size if specified
          if (style.width && typeof style.width === "number") {
            const targetWidth = style.width;
            const targetHeight = style.height && typeof style.height === "number" ? style.height : targetWidth;
            const currentWidth = node.width;
            const currentHeight = node.height;
            const scale = Math.min(targetWidth / currentWidth, targetHeight / currentHeight);
            node.resize(currentWidth * scale, currentHeight * scale);
          }
        } catch (err) {
          // Fallback to placeholder if SVG parsing fails
          node = figma.createFrame();
          node.resize(style.width || 24, style.height || 24);
          node.fills = style.fill ? solidPaint(style.fill) : [{ type: "SOLID", color: { r: 0.6, g: 0.6, b: 0.6 } }];
          node.cornerRadius = 4;
        }
      } else {
        // Component instances are represented as frames with a special marker
        node = figma.createFrame();
        node.fills = style.fill ? solidPaint(style.fill) : [];
        const label = style.icon_name || style.component_name || "Component";

        // For icons, create a small placeholder with the icon name
        if (style.icon_name) {
          node.resize(style.width || 24, style.height || 24);
          node.fills = style.fill ? solidPaint(style.fill) : [{ type: "SOLID", color: { r: 0.6, g: 0.6, b: 0.6 } }];
          node.cornerRadius = 4;
        }
      }
      break;
    }

    default: {
      node = figma.createFrame();
      node.fills = [];
    }
  }

  // Name the node
  node.name = data.name || data.node_type;
  nodeCount++;

  // Append to parent FIRST so FILL/HUG sizing can be applied (Figma requires node to be inside auto_layout)
  if (parent) {
    parent.appendChild(node);
  }

  // Apply common styling (after append so layoutSizingHorizontal/Vertical work correctly)
  applyCommonStyle(node, style);

  // Absolute positioning
  if (style.position === "absolute" && parent) {
    node.layoutPositioning = "ABSOLUTE";
    if (style.top !== undefined && style.left !== undefined) {
      node.x = style.left;
      node.y = style.top;
    }
  }

  // Flex grow
  if (style.flex_grow === 1 && parent) {
    node.layoutGrow = 1;
  }

  // Recursively create children
  if (data.children && data.children.length > 0) {
    for (const child of data.children) {
      await createNode(child, node);
    }
  }

  return node;
}

// ──────────────────────────────────────────────
// Plugin entry point
// ──────────────────────────────────────────────
figma.showUI(__html__, { width: 400, height: 480, themeColors: true });

figma.ui.onmessage = async (msg) => {
  if (msg.type !== "create-layout" && msg.type !== "render") return;

  const layout = msg.layout;

  try {
    nodeCount = 0;
    const rootNode = await createNode(layout, null);

    figma.currentPage.appendChild(rootNode);
    figma.viewport.scrollAndZoomIntoView([rootNode]);

    figma.ui.postMessage({
      type: "done",
      nodeCount,
      thinking_used: msg.thinking_used || false,
    });

    figma.notify(`✅ Created ${nodeCount} nodes`);
  } catch (err) {
    figma.ui.postMessage({
      type: "error",
      message: err.message || "Failed to create nodes",
    });
    figma.notify("❌ " + (err.message || "Failed to create nodes"), { error: true });
  }
};
