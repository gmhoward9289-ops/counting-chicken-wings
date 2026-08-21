---
name: wings
description: >-
  Cited poultry/commodity counts from counting-chicken-wings — how many
  individuals a plate of wings (or eggs, syrup, …) represents. Use when George
  asks chicken-wing counts, supply-chain vs plate distinct, corpus citations,
  mixing simulator questions, or wings MCP tools. Prefer MCP tools over guessing
  numbers; every figure must cite sources.yaml.
---

# counting-chicken-wings (wings)

Canonical repo: `C:\Users\gmhow\dev\counting-chicken-wings` ·
GitHub: `github.com/gmhoward9289-ops/counting-chicken-wings` ·
Site: [wings.swamplink.com](https://wings.swamplink.com/)

**The data is the product.** If a number has no source in `data/sources.yaml`,
it does not ship — and you must not invent one.

## Two questions, never conflated

1. **`required`** — birds' worth of wing through the supply funnel (loss chain).
2. **`distinct`** — expected individual chickens physically on the plate (mixing).

For a dozen whole wings: floor ≥ 6, distinct usually near 12 (hard ceiling 12).
Say both aloud when answering; never merge them into one vague "chickens".

## MCP tools (Cursor: `counting-chicken-wings` / `wings-mcp`)

| Tool | When |
|------|------|
| `wings_meta` | Discover product / chain slugs before calculating |
| `wings_scope` | Species depth, corpus anchor, borrow notes |
| `wings_calculate` | Cited answer + trace + sources map |
| `wings_sources` | Full citation catalog + `used_by` |
| `wings_facts` | Surprising cited facts |

### Workflow

1. `wings_meta()` — pick a product slug (default `whole_wing`).
2. Optional: `wings_scope(product=...)` if the product may borrow another species.
3. `wings_calculate(count=12, product="whole_wing")`.
4. Cite from `sources[trace[i].source]` — title, publisher, URL.

Install: `pip install -e ".[mcp]"` then run `wings-mcp` (stdio).

Cursor `mcp.json` sketch:

```json
"counting-chicken-wings": {
  "command": "<venv>/python.exe",
  "args": ["-m", "counting_chicken_wings.server"],
  "cwd": "C:\\Users\\gmhow\\dev\\counting-chicken-wings"
}
```

Build the DB first (`python -m counting_chicken_wings.build`) or let
`db.connect()` self-build on first use.

## CLI (no MCP)

```powershell
wings 12
wings sources
wings facts
wings gui
```

## Estate pointer

Thin skill at `~/.claude/skills/wings/SKILL.md` should only redirect here —
do not fork a second workflow.
