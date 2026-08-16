# European Union data — research plan

**Why the EU, and why now:** the roadmap has named "EU via Eurostat" as one of
the few places with real slaughter detail since the international item was
first written (`docs/ROADMAP.md`, the country-selector item). What makes it
worth doing *fifth* rather than later is the shape of the source: Eurostat is
the project's first **supranational** source — one API, one regulation, one
set of definitions, covering 27 countries at once. Every country so far has
cost its own research pass against its own national agency. If Eurostat holds
up, each additional EU member state is rows, not research.

**Status, 2026-08-16: the EU answers the count question at `measured` grade
for Poland, on the first pass — and does NOT answer it for the EU as a
whole.** Eurostat's annual slaughtering table (`apro_mt_pann`) publishes head
slaughtered (thousand heads) *and* carcass tonnage (thousand tonnes) for
chicken, per member state, from an exhaustive census of slaughterhouses under
Regulation (EC) No 1165/2008. Poland — the EU's largest producer — is loaded
first: 1,297,913.7 thousand head and 2,433.02 thousand tonnes of chicken in
2024, both `measured`, both from the same table. The EU-27 **aggregate**
publishes zero values in this table for poultry, in any year — see "What NOT
to do".

**Scope guard, written before anything landed:** a concurrent session
("Sources: Brazil, Mexico, China, Japan, Russia, Germany") is working
**Germany** among other countries. This pass therefore enters the EU via
**Poland only** and deliberately loads no German rows, even though the same
API call returns them. France, Spain, Italy and the rest are follow-on rows
once the two streams reconcile. The verified 2024 figures for the other large
producers are recorded in `docs/research/library/poultry-eu.yaml` so the next
pass starts from verified coverage, not from scratch.

This document follows `docs/ISRAEL-PLAN.md`'s shape: the headline question
first, a table of what landed at what grade, and a "what NOT to do" section
written from what the verification pass actually found.

---

## The headline claim question — Poland's is uncontested in-source

The candidate headline is "Poland is the EU's largest poultry producer." It
does not need a trade-press citation, because the claim is checkable inside
the single harmonised table this plan loads: Poland's 2024 chicken tonnage
(2,433.02 thousand tonnes) and poultry tonnage (2,891.97 thousand tonnes)
exceed every other member state's in the same table, same year, same
definition — Spain is next at 1,807.89 thousand tonnes of poultry, then
France at 1,722.21. That is the safest kind of superlative this project has
had: one publisher, one regulation, one weight basis, all 27 candidates in
the same file.

What the headline must NOT drift into: "Poland is Europe's largest producer"
(the UK and Russia are in Europe and outside this table) or any per-capita
consumption claim (Eurostat's slaughter table says nothing about consumption,
and no consumption source was attempted — the same honest gap the UK plan
recorded).

## Priority 1 — what landed, at what grade

| Question | Status |
|---|---|
| Head slaughtered (chicken, PL) | **LOADED, `measured`.** `B7100 Chicken`, `THS_HD`: 1,297,913.7 (2024), 1,233,208.9 (2023). Census of slaughterhouses under Regulation (EC) No 1165/2008. |
| Meat output (chicken, PL) | **LOADED, `measured`.** `B7100 Chicken`, `THS_T` carcass weight: 2,433.02 (2024), 2,284.95 (2023). Same table, same census — the Canada property (same-year, same-grade head count and tonnage) from a second source family. |
| Poultry-total context (PL) | **VERIFIED, NOT LOADED.** `B7000 Poultry meat`: 1,378,481.38 thousand head / 2,891.97 thousand tonnes (2024). It spans turkeys, ducks and geese, and an `output_*.yaml` file carries one species — loading it under `broiler` would be false. Recorded in the library entry for the headline comparison and for any future all-poultry view. |
| Broiler-specific split (PL) | **NOT AVAILABLE.** `B7110 Broiler` and `B7120 Boiling hen` return no values for Poland. `B7100 Chicken` is the finest split and includes spent laying hens. This is the one place the EU data is *coarser* than Canada's, which separates broilers from fowl. |
| EU-27 aggregate | **NOT AVAILABLE — do not derive.** See below. |
| Carcass weight per bird | **NOT PUBLISHED for poultry.** `KG_HD` exists as a unit in the table but carries no poultry values. The implied ~1.87 kg/head (chicken, 2024) lives in notes as a consistency check, not as a figure. |

## The weight basis — stated by the regulation, with named deviations

Eurostat's quality report states the basis outright: carcass weight, defined
for poultry as "plucked and drawn, without head and feet and without neck,
heart, liver and gizzard, known as '65 % chicken'". That is a *stated* basis
— the thing Israel's CBS tonnage never had — and it comes with named
member-state deviations worth keeping: the Netherlands uses a "74% chicken"
presentation and Hungary includes heads for some small-scale operations.
Poland is not among the named deviations. Any future pass loading NL rows
must carry the 74% caveat in the row notes, not just here.

## What NOT to do

- **Do not derive an EU-27 aggregate by summing member states.** The table
  publishes no EU aggregate for poultry slaughter — zero values in any year,
  verified across the full time axis. A sum of 27 member-state rows would be
  our computation, graded by us, silently including whatever member-state
  gaps exist that Eurostat itself declined to bridge. If an EU total is ever
  wanted, find a source that publishes one.
- **Do not load Germany.** Claimed by the concurrent sources session. The
  verified DE figures sit in the library entry for reconciliation, nothing
  more.
- **Do not read the Polish rows as broiler-pure.** `B7100 Chicken` includes
  boiling hens (spent layers); Canada's data separates these, Eurostat's
  Polish rows do not. The rows still load under the project's `broiler`
  species — that is the API's default lens, and Israel's CBS chicken series
  set the precedent — but every block's notes state the mix, and any
  broiler-vs-fowl comparison against Canada must read those notes first.
- **Do not reuse US loss factors on Polish birds without grading the
  result** — same rule every country plan carries.
- **Do not treat Eurostat and national-agency figures as interchangeable.**
  Poland's own GUS publishes national statistics that may differ from what
  Eurostat harmonises. This pass deliberately loads the *harmonised* series
  because comparability across member states is the point of entering via
  Eurostat; a future Poland-in-depth pass may add GUS figures alongside, but
  they are a second series, not corrections to this one.
- **Population stays NULL**, same discipline as every country since Israel:
  no per-capita consumption figure was sourced, so no denominator ships.

## The adapter question this pass answers

`docs/ROADMAP.md` (M4) says the adapter layer should wait for evidence, not
lead it. This pass is that evidence: one JSON API, stable dimension codes
(`meat`, `meatitem`, `unit`, `geo`, `time`), and 25+ more countries behind
the same call. When France/Spain/Italy land, they should land through a
fetcher in `tools/` (extend, don't fork — `fetch_census_states.py` sets the
pattern), and *that* is the moment the adapter conversation is real. This
first pass is hand-verified and hand-curated exactly like the UK's, because
one country through a new source proves the source, not the pipeline.

## Retrieval route

- API: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/apro_mt_pann?format=JSON&lang=EN`
  with `meat=B7100&meatitem=SLAUGHT&geo=PL&unit=THS_HD` (and `THS_T`).
  No auth, no key. JSON-stat 2.0 shape: values keyed by flattened index over
  the `id`/`size` arrays.
- Quality report (weight basis, census methodology, deviations):
  `https://ec.europa.eu/eurostat/cache/metadata/EN/apro_mt_esqrs.htm`.
  Note the plain `apro_mt_esms.htm` and `apro_mt_sims.htm` guesses both
  404 — the ESQRS page is the one that resolves.
- Verified 2026-08-16. Coverage per URL recorded in
  `docs/research/library/poultry-eu.yaml`.
