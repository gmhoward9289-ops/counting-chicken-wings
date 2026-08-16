---
bump: second
---
### The state map now shows all 50 states, not the 22 the annual survey is allowed to publish

`regional_census_stat` — the Census of Agriculture table `build.py` has
loaded since `census_states()` landed — was sitting unread. Nothing queried
it: no view, no API field, no line on the map. The annual NASS survey that
`/api/states` already served is capped at 22 states by disclosure rules, and
California, a top-ten broiler state, is the clearest casualty: it appears in
no year of that survey at all.

`/api/states` now carries a `census` block alongside the existing survey
response — every one of the 50 states the census enumerates, each flagged
`presence_only` when the requested year's survey has nothing to say for it.
The two never blend: Census of Agriculture sales counts are a different USDA
programme from annual slaughter and live-weight figures, and the response
keeps them in separate fields rather than folding one into the other's
`avg_size` or `volume`.

The map gained a second choropleth trace for the presence-only states, filled
a single flat colour rather than placed on the size colourscale — there is no
comparable weight figure for them, and putting one on the same scale would
imply there were. Its tooltip cites the Census of Agriculture and shows
operations, inventory and sales instead. The state table below the map picked
up a matching section, and `wings export` now writes a `states_census` file
alongside `states`.

`bump: second` because this is a new database view and a new field on an
existing endpoint — capability the corpus diff cannot see on its own.
