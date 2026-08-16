---
bump: second
---
### Wagyu's own comparison figures were printing as 0%

`/api/footprint`'s "Who got paid" table read only `value_mode`, so a stat
carrying just `value_lo`/`value_hi` — the shape wagyu's own batch used for
the US fed-cattle dressing percentage (60–64%) and USDA %CTBRC (45.4–52.3%)
comparison figures — fell through `?? 0` and printed **0%**, asserting a
number no source ever stated. It now prints the range. Wagyu's two figures
that do carry a mode (30-month finishing period, 62.96% carcass yield) were
unaffected and already rendered correctly.

Wagyu itself has been reachable since v2.1.0 via
`/api/footprint?product=ground_beef_patty` (it shares beef cattle's
`livestock` domain) and the facts feed, but `docs/ROADMAP.md` still read
"still drafted and still not run" — corrected to describe what actually
shipped and what's still missing (no species/product row, so no calculator
answer or BMS-marbling quality axis of its own).
