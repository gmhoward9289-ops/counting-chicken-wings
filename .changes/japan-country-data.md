### What changed

Added Japan (JPN) as the fifth country in the corpus: a national broiler
head count at `measured` grade (both a standing-flock inventory and an
annual shipment/throughput figure, from MAFF's Livestock Statistics
Survey), a full 47-prefecture breakdown of the shipment figure that
reconciles exactly against the national total, and a production-tonnage /
chicken-specific self-sufficiency-ratio series from MAFF's Food Balance
Sheet, cross-validated within 0.2% against an independent USDA FAS GAIN
estimate. Per-capita supply (14.4 kg/person, FY2023) is loaded as a fact;
`country.population` stays `NULL`, matching every other country in the
corpus. See `docs/JAPAN-PLAN.md` for the full research trail, including the
shipped-vs-slaughtered basis caveat carried on the head count.

No `bump:` declared — per `docs/VERSIONING.md`, another country's series
landing in tables the schema already models (`output_stat_year`,
`output_stat_district`, `country`, `fact`) is more rows of a kind already
present, the same shape Canada's and Mexico's additions took, so
`release_check.py` should land this at `third` on its own.
