---
bump: second
---
### MCP server for cited answers (xycalc#100)

Optional `.[mcp]` extra and `wings-mcp` entrypoint expose `wings_meta`,
`wings_scope`, `wings_calculate`, `wings_sources`, and `wings_facts` over
stdio — the same citation-preserving payloads as `/api/calculate`, so agents
cannot answer from vibes. `/api/calculate` now builds through
`tools.wings_calculate` so HTTP and MCP cannot drift. In-repo skill at
`skills/wings/SKILL.md`.
