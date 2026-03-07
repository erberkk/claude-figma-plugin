# gen-figma

A FastAPI backend service that converts natural-language prompts into structured Figma layout trees using Claude. Paired with a Figma plugin that renders the generated layouts directly onto the canvas.

---

## Overview

The system works in two parts:

**Backend** — receives a text prompt, sends it to the Claude API, validates the response against a strict JSON schema and design token set, and returns a structured node tree. The output is deterministic and renderer-agnostic: any client that understands the schema can consume it.

**Figma plugin** — a lightweight plugin that sends prompts to the backend and walks the returned node tree to build real Figma layers (frames, auto-layouts, text, shapes, component instances) directly on the canvas.

---

## Architecture

```
Figma Plugin (plugin/)
    │
    │  POST /api/v1/generate
    ▼
FastAPI Application (src/)
    ├── api/          — route handlers, auth middleware, input size guard
    ├── services/     — layout orchestration, prompt injection detection, validator
    ├── infrastructure/ — Claude API client, disk response cache, config, logging
    └── domain/       — Pydantic models, JSON schema, design tokens, exceptions
```

### Request flow

1. Plugin sends `{ "prompt": "...", "use_thinking": false }` with an `X-API-Key` header.
2. `AuthMiddleware` validates the key. `InputSizeLimitMiddleware` rejects oversized bodies.
3. `LayoutService` checks for a prompt injection attempt, then looks up the response cache.
4. On a cache miss, the prompt is sent to Claude. The client chooses between a direct call (simple prompts) and a sequential-thinking tool loop (complex prompts or when `use_thinking` is set).
5. The raw response goes through a three-stage validation pipeline: JSON parsing → JSON Schema → design token enforcement.
6. On the first validation failure, a single retry is issued with a corrective hint. On the second failure, a `ValidationError` is raised.
7. A successful response is written to the disk cache and returned to the plugin.

---

## Sequential Thinking

For complex layouts (dashboards, kanban boards, multi-column pages), the client runs a tool-use loop that mirrors the MCP sequential-thinking server pattern. Claude calls the `sequentialthinking` tool repeatedly to chain reasoning steps before producing the final JSON. This happens automatically based on keyword detection in the prompt, or can be forced via `use_thinking: true`.

---

## Design Token Enforcement

All Claude output is validated against a fixed token vocabulary before it reaches the plugin. Allowed values are defined in `src/domain/tokens.py` and cover:

- **Colors** — Tailwind-derived palette (slate, gray, blue, indigo, purple, red, green, amber, teal, cyan, emerald, others)
- **Spacing** — 4px base grid: 0, 1, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96 (px)
- **Typography** — font families, sizes, weights, line heights, letter spacings
- **Layout** — direction, alignment, justification, wrap
- **Elevation** — shadow scale: none, sm, md, lg, xl, 2xl, inner
- **Border radius, border width, positioning, opacity, overflow**

Any token violation causes the response to be rejected and retried.

---

## Response Cache

When `CLAUDE_CACHE_ENABLED=true`, validated responses are written to disk as JSON files under `CLAUDE_CACHE_DIR` (default: `fixtures/`). The cache key is the SHA-256 hash of the exact prompt string.

Each cache entry stores the system prompt version alongside the response. If the system prompt is edited, all existing entries are automatically treated as misses and regenerated on next request — no manual cache clearing needed.

The `fixtures/*.json` files are excluded from version control via `.gitignore`.

---

## Prerequisites

- Python 3.11+
- An Anthropic API key (`claude-sonnet-4` or compatible model)

---

## Setup

**Clone and install**

```bash
git clone <repo-url>
cd gen-figma
pip install -e ".[dev]"
```

**Configure environment**

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```
ANTHROPIC_API_KEY=sk-ant-...
API_KEY=your-internal-api-key
```

**Run the server**

```bash
uvicorn src.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## Docker

```bash
docker compose up --build
```

The service binds to port `8000` and reads configuration from `.env`.

---

## Figma Plugin

1. Open Figma Desktop.
2. Go to **Plugins → Development → Import plugin from manifest**.
3. Select `plugin/manifest.json` from this repository.
4. Run the backend locally (the plugin calls `http://localhost:8000` in development).
5. Open the plugin panel, enter a prompt, and click **Generate**.

The plugin requires the backend to be running. Production deployments must update `devAllowedDomains` in `manifest.json` accordingly.

---