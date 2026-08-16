---
bump: second
---
### The United Kingdom joins the corpus as a third country

`GET /api/output/GBR` now answers the wing question for the UK, and answers
it more directly than Israel's did on its own first pass: DEFRA's monthly
poultry statistics publish a genuine head-slaughtered series — 1,131.6
million broilers for 2024, government-enumerated, `measured` grade — where
Israel's CBS publishes no head count at all and the project had to reach for
a named industry official's press interview instead. Meat output (1,832,700
tonnes carcase weight for 2024), chicks placed, and DEFRA's own 83%
poultry-meat self-sufficiency ratio are loaded alongside it, all four DEFRA,
all four `measured`. A fresh FAOSTAT bulk download — closed off three ways
during the Israel research and open again now — corroborates DEFRA's head
count and tonnage within 2%.

What did not ship, deliberately: no subnational breakdown, because DEFRA
itself stopped publishing any nation-level split in July 2025 "to protect
commercial confidentiality across the nations," and even before that cutoff
the only split was England & Wales versus the UK total, never a genuine
four-nation one. No UK-wide average bird weight, because DEFRA's own
liveweight survey covers England & Wales only and pairing it with the
UK-wide head count would quietly narrow the geography. No population, and
therefore no per-capita claim of any kind — ONS has an uncontested UK
figure, but no per-capita consumption source was found, so the population
column stays NULL for the UK exactly as it already does for Israel and the
US, pending a consumption figure to divide it into.

`output_stat_year.measure` gained `self_sufficiency_ratio` to hold DEFRA's
production-to-supply ratio directly, the only schema change this needed —
every other UK figure fits measures Israel's rows already exercise, which is
the schema built ahead of Israel's data paying off for a second country.

Full research trail in `docs/UK-PLAN.md` and
`docs/research/library/poultry-uk.yaml`, mirroring the Israel plan's format
including its dead ends: neither AHDB nor the British Poultry Council
publishes an independent production series of their own, and USDA FAS has no
standalone UK poultry GAIN report, the same finding the Israel research made
for Israel.
