---
bump: third
---
### The state map's census layer now says it is data

The "By state" choropleth carries two layers: average live weight for the
states the annual survey publishes, and a flat gray census-presence fill for
the states it suppresses under disclosure rules. The gray layer worked — it
carries Census of Agriculture hover detail and a companion table — but a
flat gray is also exactly what "no data" looks like, and nothing on the page
said which it was. It was read, including from inside the project, as state
data failing to load.

The map's caption now opens with a swatch of the same `--grey` the trace is
drawn in and states outright that the gray states are data, not gaps — what
the census covers there, why no weight is shown at census scale, and where
to read the figures. The intro copy names the fallback too. The census year
in the caption still comes from `/api/states`, never the markup, and no
figure moved anywhere: this is legibility, not data.
