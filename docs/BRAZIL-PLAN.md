# Brazil data — research plan

**Status, 2026-08-16: Brazil answers the question at `measured` grade, on
both halves, plus a real subnational breakdown covering 19 of 27 states —
the second country in this project (after Canada) where the primary
statistical agency itself, not a secondhand attaché report, supplies a
same-year head count and tonnage.** IBGE (Instituto Brasileiro de
Geografia e Estatística — the NASS/StatCan-equivalent) publishes a
genuine REST API (SIDRA) with a table that isolates chicken ("frangos")
slaughter, quarterly, by state, with head count AND carcass weight from
the same government census-based survey. ABPA (the industry trade body)
independently supplies a second, richer picture — national production,
exports by tonnage and value, per-capita consumption, and its own
state-level slaughter and export breakdowns — at `industry` grade.

Loaded at `GET /api/output/BRA`, alongside `GET /api/countries`.

## Mexico's problem was access. Brazil's problem was choosing.

Mexico's plan spent most of its length explaining that SIAP, Mexico's
NASS-equivalent, was simply unreachable — DNS failure on one host,
connection refused on the other. Brazil is the opposite case: **IBGE
answered directly**, with a working REST API, real head counts, real
carcass weights, and a real per-state suppression flag for confidential
cells — the same shape Statistics Canada's Web Data Service was for
Canada. That made this pass's hard problem a different one: **two
independent, real, government-adjacent sources (IBGE directly, and ABPA
citing MAPA and SECEX) each publish a national head count for 2025, and
they disagree by 17%** — 6.695 billion (IBGE, all inspection types) vs
5.706 billion (ABPA, quoting MAPA's federal-inspection-only figure). The
schema allows exactly one head_slaughtered row per country per year, so
this project had to pick — see "Two national head counts" below for how
and why.

## Priority 1 — Core production figures

| Field | Why the model needs it | Status 2026-08-16 |
|---|---|---|
| Broilers slaughtered per year (head) | The denominator for everything | **LOADED at `measured`.** 6,695,465 thousand head for 2025, from IBGE's Pesquisa Trimestral do Abate de Animais (SIDRA table 1094), summed from the four published 2025 quarters — a genuine government census-type survey covering federal-, state- and municipal-inspected slaughter. A second, lower, `industry`-grade figure exists (ABPA/MAPA, 5.706 billion, federal-inspection only) and is documented but NOT loaded — see below |
| Average live weight (kg) | Drives wing size | **NOT LOADED.** IBGE reports carcass weight, not live weight, and no source in this pass stated a live-weight figure directly. A derived carcass-basis average (`v_output_derived_weight`) is available automatically from the loaded head/tonnage pair — 2.14 kg/head — but is carcass, not live, basis, and is labelled as such the same way Canada's derived figure is |
| Total chicken meat production (tonnes) | Cross-check against head × weight | **LOADED**, two grades. 14,304,261 t for 2025 at `measured` (IBGE, carcass weight, summed from quarters). 14,972,000 t for 2024 at `industry` (ABPA Annual Report 2026, its own broader production-estimate methodology) |
| Standing flock (head) | Not throughput, but a real figure elsewhere | **NOT LOADED.** Neither IBGE's quarterly abate survey nor ABPA's annual report publishes a national standing-flock census for broilers; ABPA publishes housed BREEDER stock (63.0 million head, 2025 — parent stock producing hatching eggs, a different population from the meat-bird flock) as a fact instead |
| Output value (BRL) | Scale in the local currency | **LOADED as a fact,** not an `output_stat_year` row. ABPA reports Gross Production Value R$112.6 billion for 2025 `industry` grade — loaded as `output_value` for 2025 since IBGE's table carries no value figure at all, so there is no collision to resolve |
| Subnational breakdown | Gives the choropleth a Brazilian counterpart | **LOADED**, 19 of 27 states, `measured` grade, reconciling to within 1.13% of the national total (the gap is the 8 suppressed/not-applicable states) — see below |
| Per-capita consumption (kg) | The headline | **LOADED as a fact.** 46.7 kg/person, 2025, ABPA — `industry` grade (ABPA's own decade-long series, not a government-published ratio the way Canada's AAFC figure was), but internally consistent year-over-year and not contested by a second source the way Mexico's five conflicting figures were |
| Self-sufficiency / import share | Framing used for Canada and Mexico | **NOT MEANINGFUL FOR BRAZIL, AND SAID SO RATHER THAN FORCED.** Brazil is overwhelmingly a net exporter (34.82% of production exported, 2025) with negligible chicken imports — it does not appear among the world's top chicken-importing countries in ABPA's own trade table. Loaded instead as an export-share FACT (34.82% exported / 65.18% domestic) rather than a `self_sufficiency_ratio` row, since that measure's own schema comment frames it as an import-share question, which is not Brazil's shape |

### Two national head counts, and why only one is loaded

The schema's uniqueness constraint on `output_stat_year` — one row per
`(species, country, region, year, measure)` — allows exactly one value
per cell, regardless of how many sources report one. For Brazil, 2025
`head_slaughtered` at the national level had two real candidates:

| Source | Value (2025) | Scope | Grade |
|---|---|---|---|
| IBGE, SIDRA table 1094 | 6,695,465 thousand head | Federal + state + municipal inspection combined | `measured` |
| ABPA Annual Report 2026, citing MAPA | 5,706,000 thousand head | Federal inspection only | `industry` |

IBGE wins on grade — it is a direct government survey, reached at first
hand via its own API, not a trade body's citation of a government
agency one step removed (the same distinction that kept Mexico's GAIN-
sourced figures at `industry` rather than `measured`). ABPA's figure is
documented here, in the source library, and in `sources.yaml`, rather
than silently dropped — this is the "conflicts get reported side-by-side"
discipline applied to a case where the schema itself forces a single
winner into the database, so the losing figure's home is prose instead of
a row.

**The scope difference plausibly explains part of the gap but not all of
it.** MAPA's federal-inspection-only population is a real subset of
IBGE's all-inspection-types population, so IBGE's higher head count is
expected. What is NOT fully explained: IBGE's implied average carcass
weight (2.14 kg/head) is noticeably lower than ABPA's own implied average
(2.68 kg/head, from ABPA's own tonnage ÷ ABPA's own head count — the two
ABPA figures are at least internally consistent with each other). A
plausible hypothesis — state- and municipal-inspected plants
disproportionately process smaller-format birds, pulling IBGE's blended
average down — was not chased to a citation in this pass and is offered
as a hypothesis, not a finding. See `docs/research/library/poultry-brazil.yaml`
for the full numeric trail.

### The subnational reconciliation

Unlike Canada's exact partition (806,000 thousand birds, provinces and
national total agreeing to the last thousand) or Israel's 4.76% marketing
gap, Brazil's is a **suppression-driven gap of about 1.1%, on both head
count and tonnage independently** — a coherence check in itself, since
two independently-summed quantities (head and weight) landing on almost
the same percentage gap suggests the suppression pattern is real rather
than a parsing artifact on one side.

Nineteen of Brazil's 27 states (26 states + the Distrito Federal) publish
non-suppressed 2025 figures in IBGE's table; the other eight — Acre,
Amazonas, Roraima, Rio Grande do Norte, Alagoas, Sergipe, the Distrito
Federal (all marked confidential, IBGE's "X") and Amapá (marked "..",
IBGE's not-applicable code, loaded suppressed rather than asserted as a
true zero) — are loaded as suppressed rows, the same presence-without-
volume pattern Canada's Atlantic provinces and Mexico's unreached SIAP
data both use in spirit. The published 19 states sum to 14,143,105 tonnes
against a national total of 14,304,261 tonnes (99% capture) and
6,621,286,613 of 6,695,465,295 head (99% capture) — both gaps land within
a tenth of a point of each other.

**South region concentration is Brazil's version of Canada's Ontario/
Quebec or Mexico's Veracruz.** Paraná alone accounts for 34.8% of
national chicken meat output in this project's IBGE-derived 2025 figures
(4,974,439 of 14,304,261 tonnes); Paraná, Santa Catarina and Rio Grande do
Sul together — the "South" macro-region — account for 57.9%. This is
independently corroborated by the USDA FAS GAIN report's own state map
(sourced by GAIN to IBGE, for the first half of 2025 only): 35.2% Paraná,
58.48% South region — landing within a point of this project's own full-
year figures despite being a different subset of the year and a step
further removed from IBGE. Two independent readings converging is worth
stating plainly, the same way Canada's exact provincial reconciliation
was.

## Sources, in order of preference

1. **IBGE** (Instituto Brasileiro de Geografia e Estatística) — Brazil's
   NASS/StatCan-equivalent, and the actual way in. Its Pesquisa Trimestral
   do Abate de Animais (Quarterly Animal Slaughter Survey), table 1094 on
   the SIDRA platform, is a genuine REST API (`apisidra.ibge.gov.br`) that
   isolates chicken slaughter specifically, by state, with head count and
   carcass weight from the same census-based survey, and a machine-
   readable suppression code. This is the strongest source this project
   has reached for a non-US, non-Canada country.
2. **ABPA** (Associação Brasileira de Proteína Animal) — the national
   poultry (and pork) trade body, the equivalent of the National Chicken
   Council. Reached directly as a 43 MB PDF (its Annual Report 2026,
   English edition), not secondhand — unusually rich for a trade body:
   national production, exports (tonnage, value, 153 destination
   countries), per-capita consumption, Gross Production Value, breeder
   stock, and two independent state-level breakdowns (slaughter, sourced
   by ABPA to MAPA; exports, sourced by ABPA to SECEX). Never promoted
   past `industry` confidence, the same discipline UNA's figures received
   for Mexico.
3. **USDA FAS GAIN** (`Brazil: Poultry and Products Annual`, BR2025-0038)
   — reached directly, English, PDF. Not used for any loaded figure (IBGE
   is both more current and closer to the primary source), but kept and
   cited for its independent corroboration of Brazil's South-region
   concentration via IBGE data the report itself quotes for the first
   half of 2025.
4. **FAOSTAT** — not attempted this pass. Israel's and Canada's research
   both found it closed (API host unresponsive, bulk downloads timing
   out); Mexico's pass did not re-test it. Brazil's did not either, given
   how much ground IBGE and ABPA alone covered — a fair thing for a future
   pass to check, per Canada's plan's own note.

### Access findings

**Read `docs/research/library/poultry-brazil.yaml` first** — the
machine-readable version of this section, with every URL, its status, and
what it does and does not cover.

| Source | Result |
|---|---|
| **IBGE SIDRA API (table 1094)** | **Works, and is a real API,** queried directly via `apisidra.ibge.gov.br/values/...`. National and 27-state (19 published, 8 suppressed) head count and carcass weight for 2025, summed from four published quarters. |
| **ABPA Annual Report 2026 (PDF)** | **Works.** 43 MB PDF, too large for WebFetch's own 10 MB cap — downloaded directly and read with PyMuPDF. Rich, multi-page chicken-meat section with two independent state-level charts. |
| ABPA press release / secondary pickup | Corroborates the PDF's headline figures verbatim; used to confirm quotes where the PDF's own OCR of chart-embedded numbers was ambiguous. |
| **USDA FAS GAIN BR2025-0038 (PDF)** | **Works**, read with PyMuPDF after WebFetch's first-pass extraction misread the PSD table's columns (an error caught by re-extracting rather than trusting a first read at face value — see the source library entry). Used for corroboration only, not a loaded figure. |
| FAOSTAT | Not attempted this pass. |

## Priority 2 — What makes the demo land

- **Two real government-adjacent sources disagreeing by 17% on the same
  country's same year is a stronger "the data is the product" story than
  either Canada's exact reconciliation or Mexico's total access failure.**
  It shows the corpus's discipline working exactly as designed: pick the
  better-graded figure, load it, and document the runner-up rather than
  averaging the two or silently preferring the bigger number.

- **Export concentration is sharper than production concentration.** The
  South region is 57.9% of production but 77.3% of exports (per ABPA's
  own framing, quoted directly) — Paraná alone ships 40.76% of Brazil's
  chicken meat exports against 34.8% of its production. That gap (export
  share exceeding production share for the same region) is worth a
  learning-centre fact: the South's plants are disproportionately
  export-oriented relative to their share of national output.

- **Scale comparison.** Brazil's ~15.3 million tonnes of chicken meat
  production, 2025, sits behind only the United States (21.8M t) and
  China (16.2M t) worldwide, per ABPA's own World Chicken Meat Market
  table — the third data point (after Canada's ~12x-smaller-than-US
  scale and Mexico's ~1/4-of-US-tonnage scale) in this project's growing
  set of scale comparisons.

- **Wings specifically.** Neither IBGE nor ABPA reports wings as a
  separate cut in what this pass reached. Not attempted further this
  round, matching Canada's and Mexico's own "not chased this pass" notes.

## What "done" looks like for this pass

1. [x] National head count and tonnage loaded at `measured` grade, from a
   government census-based survey reached directly via its own API — the
   second time (after Canada) this project has reached that combination
   for a non-US country.
2. [x] Subnational breakdown loaded (19 of 27 states), with the
   suppression-driven reconciliation gap stated explicitly and cross-
   checked on two independent quantities (head and weight).
3. [x] The competing national head-count figure (ABPA/MAPA, 5.706 billion)
   documented as a real, unresolved conflict rather than silently dropped
   or averaged in.
4. [x] Per-capita figure and export-share loaded as facts, each at the
   grade its source actually supports.
5. [ ] Wings as a separate reported cut — not found this pass, flagged for
   a future pass, matching Canada's and Mexico's plans.
6. [ ] A longer time series. This pass queried only 2025's four quarters
   from IBGE's table, which itself covers back to 1997 Q1 — a real,
   readily reachable extension for a future pass, not a research gap.
7. [ ] The average-carcass-weight discrepancy between IBGE's and ABPA's
   implied figures (2.14 vs 2.68 kg/head) is flagged as a hypothesis
   (inspection-scope composition) rather than resolved to a citation.

## What to explicitly NOT do

- **Do not load ABPA's 5.706 billion head count, or its state-level
  slaughter/export breakdowns, into `output_stat_year`.** Doing so would
  either collide with IBGE's rows under the schema's uniqueness
  constraint (for the national and state head counts, where both
  publishers cover the same cell) or would misuse the `marketed` measure
  to mean "exported", which is not what that measure means elsewhere in
  this project. Both figures are fully recorded in `sources.yaml` and
  `docs/research/library/poultry-brazil.yaml` instead.
- **Do not average or otherwise reconcile IBGE's and ABPA's competing head
  counts into a single "best estimate" number.** That would manufacture a
  figure neither publisher stated, the same discipline Mexico's plan
  applied to its own multi-source state-ranking conflicts.
- **Do not treat ABPA's per-capita or output-value figures as government-
  grade.** ABPA is a trade body; its figures are loaded at `industry`
  confidence throughout, even where they cite a government source (MAPA,
  SECEX) one step removed — the same rule Mexico's GAIN-sourced figures
  and Canada's CFC-sourced figures both follow.
- **Do not compute or publish a `self_sufficiency_ratio` for Brazil.**
  Brazil's shape is net-exporter, not net-importer, and forcing this
  measure would either produce a number over 100% (confusing against
  Canada's and the UK's import-share readings of the same measure) or
  require inventing an import figure this pass did not find one large
  enough to matter. An export-share fact carries the same information
  honestly.
- **Do not conflate ABPA's "aves" figures (eggs, turkey, duck meat — all
  reported separately in the same report, at page 20) with chicken meat.**
  Every figure loaded into `data/output_brazil.yaml` and `data/facts.yaml`
  is explicitly captioned "Chicken Meat" / "Frango" in its source, checked
  the same way Mexico's carne-de-ave/carne-de-pollo split was checked.
- **`country.population` stays `NULL`,** the same discipline as every
  other non-US country in this project. Brazil's per-capita figure (46.7
  kg/person, 2025) is loaded as a fact rather than as this column, for the
  same reason Canada's 35.64 kg figure was: it is already published as a
  ratio, and no other calculation in this project needs a Brazilian
  population estimate.
