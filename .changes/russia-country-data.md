---
bump: second
---
### Russia joins the corpus, thin and honestly graded

`GET /api/output/RUS` now answers the wing question for Russia, at
`industry` grade, for 2019-2020 only. A 2020 USDA FAS GAIN report (the only
source this research pass found that isolates chicken meat from Russia's
blended national poultry total) gives 4,668,000 tonnes (2019, final) and
4,715,000 tonnes (2020, in-year estimate), both ready-to-cook weight. No
head count, standing flock, output value, or subnational breakdown shipped.

The taxonomy problem here is a level worse than Mexico's carne-de-ave/
carne-de-pollo split: Rosstat's own national bulletins report a single
"птица" (poultry, all species) line with no chicken-only row to select even
in principle, at the national level. Three Russian trade-press sources
describing the SAME 2023 poultry-meat total disagree with each other by up
to 3.5%, and two of the three are numerically indistinguishable from
Rosstat's own all-poultry aggregate despite one being explicitly labelled
"broiler meat" — a real, unresolved conflict, reported rather than
adjudicated, and not loaded as a corpus figure at any grade.

rosstat.gov.ru itself was unreachable from this research environment: every
fetch attempt (WebFetch, curl, raw Python) failed on TLS certificate trust,
a different failure shape than Canada's handshake reset or Mexico's DNS/
connection failures, consistent with Rosstat using a Russian government CA
not carried by the trust stores available here. rosptitsesoyuz.ru failed at
the DNS level outright. `country.population` stays NULL for RUS, as for
every other non-US country here. See `docs/RUSSIA-PLAN.md` and
`docs/research/library/poultry-russia.yaml` for the full research trail.
