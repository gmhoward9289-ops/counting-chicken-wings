# United Kingdom data — research plan

**Why third:** the roadmap (`docs/ROADMAP.md`) already named DEFRA as the
expected UK source for international expansion, and Israel's plan proved out
the schema (`country_id` on every observation table, `output_stat_year` for
countries that don't fit US-shaped columns). The UK is the first test of
whether that schema generalises to a country whose statistics agency
*does* publish everything NASS publishes, rather than the CBS case where it
mostly doesn't.

**Status, 2026-08-16: the UK answers the count question at `measured`
grade, on the first pass.** DEFRA's monthly poultry statistics publish a
genuine head-slaughtered series — UK-wide, government-enumerated, monthly
back to 1994. That is the opposite of Israel's experience, where CBS
publishes tonnage and a standing flock but no head count at all, and the
head figure had to come from an industry interview. The UK does not need
that workaround. Loaded at `GET /api/output/GBR`: head slaughtered, meat
output in tonnes, chicks placed, and DEFRA's own self-sufficiency ratio —
all four `measured` grade, all four DEFRA.

**What did not make it in, and why, up front:** no subnational breakdown
(DEFRA stopped publishing any nation-level split in July 2025, and even
before that it was never a genuine four-nation split — see below), no
population (left NULL, matching USA and ISR — see "What NOT to do"), and no
per-capita consumption claim of any kind (DEFRA and FAOSTAT both publish
production and slaughter, not consumption; a consumption figure was never
sought because no source for one was tried, which is different from
Israel's per-capita headline having been tried and found unsourceable — the
UK simply never had a controversy to resolve here, since no conflicting
per-capita figures were surfaced by this pass).

This document is written to be handed to a research agent, following
`docs/ISRAEL-PLAN.md`'s shape and using the same headline-claims-first
structure.

---

## The headline claim question — resolved: there isn't one to avoid

Israel's plan opens with a claim that "cannot be sourced" — five per-capita
consumption figures spanning a 20% range, all claiming Israel is the
world's top chicken eater. The UK research pass asked the same question
first: is there a UK headline claim (biggest European producer, top
per-capita consumer, etc.) that different sources disagree on?

**No conflicting headline claim was found, because no per-capita
consumption claim was searched for or surfaced.** This is a real
difference from Israel, not an oversight to flag the same way. The UK
research here focused on *production* statistics (DEFRA publishes
excellent ones), and production is not consumption — the two questions
were never in tension because only one of them was asked. If a future pass
wants a UK per-capita consumption headline, treat it exactly as Israel's
was treated: as an open question needing its own primary-source search, not
as a fact to infer from the production figures already loaded here.

**The genuinely interesting UK number, and it is uncontested:** DEFRA
publishes the UK's poultry meat self-sufficiency (production-to-supply)
ratio directly, at 83% for 2024 (Table 14.2, `Agriculture in the United
Kingdom 2024`). Israel's plan flagged self-sufficiency as "not attempted"
and noted Israel is unusually a *net surplus* producer. The UK is the
opposite and more typical shape — an 83% self-sufficient net importer of
the remainder — which is worth stating as the contrast between the two
countries' data, rather than a fact needing its own resolution.

---

## Priority 1 — Core production figures

| Field | Why the model needs it | Status 2026-08-16 |
|---|---|---|
| Broilers slaughtered per year (head) | The denominator for everything | **LOADED at `measured`.** 1,131.6 million for 2024, from DEFRA's own slaughterhouse survey (FSA-sourced for England & Wales since July 2020). This is the government enumeration Israel never got |
| Average live weight (kg) | Drives wing size | **PARTIALLY AVAILABLE, not loaded as a UK-wide figure.** DEFRA publishes it, but the series is explicitly England & Wales ONLY (~26 respondents to Defra's own slaughterhouse survey) — not UK-wide like the head count and production tonnage. 2.3 kg (2024) for E&W. Not loaded into `output_uk.yaml` because pairing a UK-wide head count with an E&W-only weight would silently narrow the geography without saying so; see "What NOT to do" |
| Total chicken meat production (tonnes) | Cross-check against head × weight | **LOADED.** 1,832,700 tonnes carcase weight for 2024 (whole-bird-equivalent, net of offal — a stated basis, unlike CBS's unstated one for Israel), back to 2020 |
| Standing flock / inventory | Not throughput, but a real head figure | **NOT LOADED.** DEFRA's datasets are throughput-oriented (slaughter, placements); no end-of-year standing-flock series equivalent to Israel's CBS table 21.8 was found in the two datasets checked. Not pursued further because head_slaughtered already answers the priority question directly, unlike Israel where it did not |
| Output value (GBP) | Scale in the local currency, unconverted | **NOT LOADED.** DEFRA's poultry statistics release covers volumes, not farmgate value; a GBP output-value series analogous to CBS table 21.11 was not found in this pass. Worth a dedicated search (Defra's separate "Agriculture in the UK" farm-income chapters may carry it) but not pursued to keep this pass scoped to the datasets actually verified |
| Subnational breakdown | Choropleth counterpart | **NOT AVAILABLE, and DEFRA says so itself.** See below — this is a genuine absence, not a research gap |
| Per-capita consumption (kg) | A demo hook, if sourceable | **NOT ATTEMPTED.** See "the headline claim question" above |
| Self-sufficiency / import share | UK is a net *importer*, the mirror of Israel's net-surplus case | **LOADED.** 83% for 2024 (volume-based production-to-supply ratio), DEFRA Table 14.2 |
| Chicks placed per year (head) | An independent cross-check on the head-slaughtered figure | **LOADED at `measured`.** 1,163.1 million for 2024, from DEFRA's separate hatcheries survey — a second government series, not a second opinion from industry the way Israel's corroboration was |

**Two figures a demo can use honestly today:** 1,131.6 million broilers
slaughtered and 1,832,700 tonnes of meat produced in the UK in 2024, both
DEFRA-measured and both more directly sourced than anything the Israel plan
managed for the equivalent figures — the UK's head count did not need an
industry proxy or a derived-weight cross-check the way Israel's did.

**One cross-check that holds up rather than fails.** Unlike Israel's
4.76%-gap district/output reconciliation, the UK's two DEFRA series
(chicks placed vs. head slaughtered) sit 2.7% apart in the direction
grow-out mortality predicts, and an independent third source — FAOSTAT,
freshly reachable as of this pass — corroborates DEFRA's own head count and
tonnage within 0.8–1.9%. Three sources, two of them government, in close
agreement is the strongest data position any country in this corpus has had
so far.

---

## Sources, in order of preference — and what changed from the plan

1. **DEFRA "Poultry and poultry meat statistics"** — `gov.uk`, monthly
   Accredited Official Statistics, ODS spreadsheets. **This is the UK's
   NASS-equivalent and it works exactly as hoped**, unlike CBS. Covers head
   slaughtered, average liveweight (E&W only), and meat production.
2. **FAOSTAT** — reachable now (200, real 25 MB bulk zip) as of 2026-08-16,
   where it 401/403/521'd throughout the Israel research on 2026-07-29.
   Used here for cross-validation only, not as a primary, because DEFRA is
   more current and more granular for the UK specifically.
3. **AHDB and the British Poultry Council** — both checked, both **dead
   ends** for original statistics. AHDB does not run a poultry sector team
   (poultry data feeds its Cereals & Oilseeds feed-demand analysis, not the
   other way round); BPC interprets DEFRA's own chick-placings series as an
   industry indicator rather than publishing an independent one. Neither
   publishes a production or slaughter series DEFRA does not already
   publish first.
4. **USDA FAS GAIN** — no standalone UK poultry report exists, mirroring
   Israel's "no Israel poultry report exists" finding exactly. Post-Brexit
   UK poultry coverage is folded into the EU-wide Poultry and Products
   Annual/Semi-annual reports (trade context, not UK production statistics)
   filed from the Paris post; the London post's own GAIN output covers
   import regulations and organic-market reports, not poultry production.

### Access findings

**Read `docs/research/library/poultry-uk.yaml` first** — it is the
machine-readable version of this section, with every URL tried, its HTTP
status, and exactly what it does and does not cover, following the same
discipline as `poultry-israel.yaml`.

| Source | Result |
|---|---|
| **DEFRA poultry slaughter dataset** | **Works, and is the primary.** Real ODS spreadsheet (188 KB), parsed with the `odf` Python package the same way CBS's `.xlsx` files are parsed with `zipfile`+`ElementTree` — an ODS is likewise a zip of XML. Ten sheets, units stated on each. |
| **DEFRA hatcheries dataset** | **Works.** 187 KB ODS, chicks/eggs placed. Carries a genuine GB-vs-NI split through 2024 that was deliberately NOT loaded (see "What NOT to do"). |
| **DEFRA "Agriculture in the UK 2024"** | **Works.** Full PDF (3.28 MB), self-sufficiency ratio confirmed on the actual table page (188 of 194), not inferred from a summary. |
| **FAOSTAT bulk download** | **Now open**, where it was closed three ways during the Israel pass one URL earlier. Worth re-trying on any future country rather than assuming the earlier 403/521 still holds. |
| **British Poultry Council statistics page** | 404. No independent BPC production series exists; confirmed via general search that BPC is a reader of DEFRA's numbers, not a second publisher. |
| **AHDB poultry page** | 404. AHDB has no poultry sector team; poultry data is consumed by its cereals/feed-demand analysis, not produced by a poultry team of its own. |
| **USDA FAS UK regional page** | 403, an Akamai-style bot block — the same failure mode ISRAEL-PLAN.md hit on `gov.il`/`moag.gov.il`. Needs a human with a browser. |
| **USDA "Livestock and Poultry: World Markets and Trade"** | 200, downloaded and read in full (22 pages). Has UK rows for beef, pork and swine but **no chicken/broiler table exists in this document at all** — the word "Broiler" never appears. |
| **USDA FAS GAIN report search** | No standalone UK poultry report found. UK poultry trade context lives in the EU-wide reports instead. |

---

## Priority 2 — What makes the comparison land

- **Three-country scale comparison.** UK ~1.13 billion broilers/year against
  US ~9.58 billion and Israel ~260–275 million (industry/CBS-quarterly
  figures): the UK sits at roughly 1/8th the US scale and about 4× Israel's.
  Per-capita framing is deliberately not attempted here (see above) so this
  stays a *production*-scale comparison, not a consumption one.
- **Self-sufficiency as the Israel/UK contrast.** Israel: net surplus
  producer (unusual, per ISRAEL-PLAN.md). UK: 83% self-sufficient net
  importer (the more typical developed-economy shape). Two data points on
  the same axis from two different countries, both DEFRA/CBS-sourced rather
  than asserted.
- **Wings specifically.** Not researched in this pass — DEFRA's product
  breakdown (if any exists below whole-bird carcase weight) was not
  checked. A genuine gap, not a "no" — worth a dedicated look before this
  scales to a UK wing-specific claim the way the Israel mangal fact does
  for Israel.
- **A loss-chain question the UK could raise, not yet researched:** the UK
  has both religious (halal/kosher) and standard (CAS/waterbath-stun)
  slaughter running in parallel commercially, unlike Israel's near-universal
  kosher slaughter. Whether UK statistics separate the two, and whether it
  changes the loss chain the way shechita does for Israel, was not
  investigated here.

---

## Schema work

**No table changes were needed beyond one CHECK-constraint addition.**
`output_stat_year.measure` gained `'self_sufficiency_ratio'` (a percentage)
to hold DEFRA's Table 14.2 figure directly rather than deriving it from
production and a consumption figure this project does not otherwise have.
Every other UK figure fits the existing `meat_output`, `head_slaughtered`,
and `chicks_placed` measures Israel already exercises — the schema Israel's
plan built (`country_id` on every key, `output_stat_year` for
non-US-shaped reporting) generalised to a second real country with no
further migration, which was exactly the point of doing that work ahead of
any Israeli data.

`region_level`'s CHECK constraint (`'total','district','council'`) was
**not** extended. The UK genuinely has no subnational data that maps onto
those three levels (see below), so there was nothing to add a value for.

---

## Why there is no subnational UK breakdown

This is the UK's version of the "is a 47-region Israeli map an honest
comparison" question ISRAEL-PLAN.md closes on — except here the answer is
simpler: **there is currently no UK subnational poultry breakdown to
compare with at all.**

DEFRA's own Information sheet states it outright: "From July 2025 onwards
only UK totals will be published for the [poultry slaughter/hatcheries]
data to protect commercial confidentiality across the nations. No country
breakdowns are available for this dataset." That is a stated, deliberate
suppression — the same kind of real constraint NASS's 22-state disclosure
ceiling and CBS's suppressed councils represent, not a gap to fill by
estimating.

It is also worth recording precisely what existed *before* that cutoff,
because it was never as granular as either the US 50-state or Israeli
47-region tables: the historical split was England & Wales (one combined
figure, from the FSA survey) versus the UK total, from which Scotland plus
Northern Ireland combined could be inferred by subtraction but neither was
ever reported individually in the slaughter dataset. The one place a real
constituent-level split does exist is the hatcheries dataset's chick
placings, which carries a genuine Great-Britain-vs-Northern-Ireland split
through 2024 (2024: GB 1,027.9m, NI 135.2m). That is two-way (GB/NI), not
four-nation, ends at the same July-2025 cutoff, and applies to a
throughput-proxy measure rather than the priority head-slaughtered figure —
which is why it was recorded in the source library but not loaded into
`output_uk.yaml`.

**So the UK choropleth question resolves to: there isn't one yet, and
that's an honest state to ship rather than something to paper over with an
England-only or GB/NI map that implies more granularity than the source
actually gives.**

---

## What "done" looks like for this pass

1. [x] UK head-slaughtered loaded at `measured` grade — the thing Israel's
   plan spent most of its effort trying to get to `industry` grade, the UK
   got directly from its primary source on the first pass.
2. [x] UK meat output, chicks placed, and self-sufficiency ratio loaded,
   all `measured`, all DEFRA.
3. [x] A cross-check against an independent source (FAOSTAT) that holds up
   within 2%, recorded rather than asserted without evidence.
4. [x] Explicit statement of why no subnational data ships (DEFRA says so
   itself) rather than a silently blank map.
5. [ ] Per-capita consumption — not attempted, and correctly so per "the
   headline claim question" above; a future pass should treat it as its
   own primary-source search, the way Israel's was, not infer it from
   production figures already here.
6. [ ] Output value in GBP — not found in the datasets checked this pass.
   Worth a dedicated look at DEFRA's farm-income chapters before
   concluding it does not exist.
7. [ ] Standing flock / inventory — not found in the datasets checked this
   pass, and not pursued because head_slaughtered already answers the
   priority question, unlike Israel's case where inventory was the only
   head-adjacent figure available.
8. [ ] Wings as a separately-reported cut, and any religious-slaughter loss
   stage analogous to Israel's shechita/bedikah — neither investigated in
   this pass.

## What to explicitly NOT do

- **Do not pair the UK-wide head-slaughtered figure with the England &
  Wales-only average liveweight to derive a UK-wide weight-per-bird.** The
  two series have different geographic scope (UK vs. E&W), and DEFRA's own
  Information sheet is explicit that Scotland and Northern Ireland run
  separate liveweight surveys not merged into the published column. A
  derived figure built across that scope mismatch would look like a UK
  number while actually describing England & Wales.
- **Do not reuse US loss factors on UK data without grading the result
  `estimate` and labelling it as such.** Same rule as Israel's plan states
  for shechita — different slaughter methods, different inspection regimes,
  different chain, and nothing here has investigated whether UK-specific
  loss stages exist yet.
- **Do not fill `country.population` for GBR.** ONS publishes an
  uncontested UK population figure, unlike anything in Israel's contested
  per-capita spread — but no per-capita *consumption* figure was sourced
  here, and loading population alone would let `/api/countries` mark
  `per_capita: true` for a claim this pass never built. Wait for a
  consumption figure, and load both together.
- **Do not invent a four-nation (England/Scotland/Wales/Northern Ireland)
  breakdown from the GB/NI split that does exist in the hatcheries data.**
  GB is not England, and the hatcheries split does not decompose further.
  A choropleth built from it would imply a granularity that does not exist
  in the source.
- **Do not treat the 2.7% chicks-placed-vs-slaughtered gap or the
  0.8–1.9% DEFRA-vs-FAOSTAT gap as errors needing resolution.** Both are
  within the range two independently-compiled measurements of overlapping
  categories should agree to, and Israel's plan already establishes the
  precedent of asserting a small gap explicitly rather than hiding it or
  chasing it to zero.
