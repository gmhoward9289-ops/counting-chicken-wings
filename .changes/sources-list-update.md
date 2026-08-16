---
bump: second
---

### Fixed

- The Sources page reported "0 figures" for 21 of the sources the corpus
  actually cites — including every source behind the international data
  (Israel's CBS series, DEFRA, Destatis, Eurostat, StatCan, NASS Census).
  `/api/sources` counted usage from a hand-written list of tables that had
  not been touched since before any country data landed, so figures stored
  in `output_stat_year`, `regional_production_year`, `regional_census_stat`,
  `economic_stat`, `nutrition`, `resource_footprint`, `quality_defect` and
  `model_parameter` counted for nothing. The endpoint now discovers its
  tables from the schema via `audit.cited_tables()`, which is where that
  contract already lives, so the list cannot go stale again when the next
  table is added.
