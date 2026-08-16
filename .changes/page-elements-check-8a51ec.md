---
bump: second
---
### The suppressed states get their published aggregates, and the census layer says it is data

NASS will not name a state in the Production and Value summary if a figure
could identify individual farms — but it does publish those states, as
combined rows: "California, Tennessee, and West Virginia" as one line, and
an "Other States" row (fourteen states in 2025, twelve in 2024) with every
member named in the footnote. Those aggregates now live in the corpus as a
new table, `regional_production_aggregate`, served on `/api/states` and
shown on the By-state view — a real cited figure for exactly the states the
map cannot colour. They are shown as aggregates and never split across
members, because allocating a combined row would be inventing data. The
derived lb/bird column (pounds over head, ~5.8 lb against the national 6.6)
is arithmetic the source never printed and travels at `derived` grade,
labelled as such wherever it appears.

What makes the rows safe to carry is arithmetic: named states plus
aggregates reproduce the published United States total exactly — head,
pounds and dollars, both years. `tools/parse_production_value.py` now
refuses to emit a YAML that fails that check, a test re-asserts it from the
built database, and a second test proves no aggregate member is ever also a
named state. The parser also gained `--from-pdf` (pdfplumber, rebuilding
rows from word coordinates), because `pdftotext -layout` was caught drifting
values between rows on this document — three plausible numbers per line,
every one wrong, no error anywhere.

Three new facts cover the suppression machinery: fourteen states published
as one number, the smaller birds the arithmetic of hiding leaks anyway, and
Florida's row vanishing between 2024 and 2025 because the disclosure line
moved, not the chickens.

Separately, the state map's census-presence layer now announces itself: the
gray fill was read — including from inside the project — as state data
failing to load. The caption now opens with a swatch of the same `--grey`
the trace is drawn in and says the gray states are data, not gaps; the
census year still comes from `/api/states`, never the markup.
