# Canada data — research plan

**Status, 2026-08-16: Canada answers the question at `measured` grade, on
both halves.** Israel's plan opened by explaining what CBS could not do;
this one opens with the opposite finding. Statistics Canada publishes a real,
queryable API (the Web Data Service) with a table that separates broiler
chicken from spent laying hens ("fowl") and reports both head slaughtered
and meat output, by province, for the same year, from the same government
census-based survey. That is the first time this project has had a
same-year, same-grade, government head count and tonnage for a country
other than the US.

Loaded at `GET /api/output/CAN`, alongside `GET /api/countries`.

## The headline this demo CAN lead with — unlike Israel's

Israel's plan spent most of its length explaining why the "highest
per-capita chicken consumer" claim had no reachable source. Canada's does not
have that problem: Agriculture and Agri-Food Canada's chicken-industry page
states plainly, for 2025, that chicken was "the most consumed animal meat
protein in Canada... with a per capita disappearance of 35.64 kilograms."
One primary source, one year, one number, government-published. It is
loaded as a **fact**, not as `country.population` plus a derived query —
see "What NOT to do" below for why.

"Disappearance" is the standard term of art (supply minus exports minus
stock change, a demand proxy) and is kept as the word AAFC uses rather than
silently retitled "consumption" — the two are close but not identical, and
the project's own discipline on not inventing precision applies to prose as
much as to numbers.

## Priority 1 — Core production figures

| Field | Why the model needs it | Status 2026-08-16 |
|---|---|---|
| Broilers slaughtered per year (head) | The denominator for everything | **LOADED at `measured`.** 806,000 thousand (806.0 million) for 2025, from StatCan table 32-10-0118-01, which isolates "Chicken" from "Fowl" (spent hens). Sourced to registered-plant slaughter reports via AAFC/CFIA, per StatCan's own survey methodology page — a genuine enumeration, not an interview |
| Average live weight (kg) | Drives wing size | **NOT LOADED as `live` weight.** StatCan's production weight is (per AAFC, independently) **eviscerated**, not live. A `v_output_derived_weight` row is produced automatically from head_slaughtered ÷ meat_output — 1.76 kg/bird — but that is an eviscerated-basis average, not a live weight, and is labelled as such. CFC's own "live weight" farm-size figures use a different basis again and are deliberately NOT merged with the head count — see "What NOT to do" |
| Total chicken meat production (tonnes) | Cross-check against head × weight | **LOADED.** 1,416,554 tonnes for 2025 (chicken only, eviscerated weight), five-year series back to 2021 |
| Standing flock (head) | Not throughput, but the only head figure that exists for Israel | **NOT PUBLISHED THIS WAY.** Canada's supply-managed system allocates production quota in advance rather than publishing a national standing-flock census the way CBS or NASS do for inventory. This is a real structural difference, not a research gap — recorded as absent rather than estimated |
| Output value (CAD) | Scale in the local currency | **LOADED.** $4,060.369 million CAD for 2025, five-year series back to 2021 |
| Subnational breakdown | Gives the choropleth a Canadian counterpart | **LOADED**, and it reconciles exactly — see below |
| Per-capita consumption (kg) | The headline | **LOADED as a fact.** 35.64 kg/person, 2025, AAFC. See above |
| Self-sufficiency / import share | Canada is nominally supply-managed for self-sufficiency | **DERIVED, `derived` grade.** ≈91.9% — see below |

### The provincial reconciliation is the opposite finding from Israel's

Israel's district marketing figures summed to 4.76% short of national
output, for a real and documented reason (marketing excludes
self-consumption). Canada's six individually-published provinces plus the
Atlantic aggregate (a StatCan-defined grouping of Newfoundland and Labrador,
Prince Edward Island, Nova Scotia and New Brunswick, each of which is
individually suppressed for confidentiality) sum to **exactly** the national
total: 806,000 thousand birds, to the last thousand. Output tonnage and
output value reconcile to within **one rounding unit** rather than exactly —
the provinces sum to 1,416,555 thousand kg against a published national
1,416,554, and to $4,060,368 thousand against $4,060,369, because StatCan
rounds every series row to the nearest thousand independently (confirmed
against the WDS API itself, not a transcription error on this side). One
part in 1.4 million, in opposite directions, is a publication artifact, not
a second survey. This is worth stating plainly
rather than leaving a reader to notice it, the same way the Israeli gap
needed stating: a partition that closes exactly is itself informative,
because it means the provincial figures and the national figure are the
same underlying count, not two different surveys that happen to agree.

The four Atlantic provinces are loaded as suppressed rows (no value, not
zero) — the same "presence without volume" pattern CBS and NASS both use,
confirmed here by StatCan's own machine-readable `securityLevelCode`.

### Self-sufficiency, worked from two AAFC figures

AAFC's chicken-industry page states 2025 production (1,416.554 million kg
eviscerated), imports (231.4 million kg, $1.1B), and exports (106.7 million
kg, $754M) — three real figures, one page, one year — but does not state a
self-sufficiency percentage itself. Dividing:

```
production / (production + imports − exports)
= 1,416.554 / (1,416.554 + 231.4 − 106.7)
≈ 91.9%
```

Carried at `derived` grade, citing the same AAFC page for both halves of the
calculation, rather than presented as an AAFC-published percentage it is not.

## Sources, in order of preference

1. **Statistics Canada (StatCan)** — the NASS-equivalent, and unusually the
   one country here with a genuinely queryable API rather than a locked
   PDF or a JS-shell website. See "The StatCan Web Data Service" below.
2. **Agriculture and Agri-Food Canada (AAFC)** — poultry market information
   pages, government, English, and the source for the weight-basis
   confirmation and the per-capita figure that StatCan's own tables never
   state.
3. **Chicken Farmers of Canada (CFC)** — industry-grade, the equivalent of
   the National Chicken Council, and useful for provincial producer counts
   and economic-contribution estimates that AAFC does not publish itself.
4. **FAOSTAT** — attempted for cross-validation, as with Israel. **Closed
   again**, differently this time: the API host returned no response at all
   (not the 401/403/521 Israel's pass got), and bulk downloads timed out.
   Two independent research passes, three weeks and one country apart, both
   found FAOSTAT unusable. Worth flagging upstream if this project ever
   needs it badly enough to justify a support ticket to FAO.

### The StatCan Web Data Service is worth its own note

This matters for future tooling decisions, not just for Canada's numbers.
Every other country source in this project so far — CBS's Statistical
Abstract, USDA's PDF summaries, the OECD-FAO annex — has been a document to
be scraped or parsed, with the failure modes that implies (font encoding,
JS shells, PDF layout). StatCan's WDS is a real REST API: POST a
dimension-coordinate to `getDataFromCubePidCoordAndLatestNPeriods` and get
back exact JSON values with a machine-readable suppression flag. No OCR, no
`--layout` guessing, no "does this PDF actually contain the number" doubt.
If this project ever builds a proper fetcher/updater tool rather than a
one-shot research pass, Canada is the one country where an automated
nightly pull is realistic without re-doing scraping work every release.

The one wrinkle: `www150.statcan.gc.ca`, the host both the WDS API and the
table-viewer pages live on, resets a plain TLS 1.3 handshake from this
research environment. Forcing TLS 1.2 (`curl --tlsv1.2`) fixes it
completely — see `docs/research/library/poultry-canada.yaml` for the full
diagnostic trail, because a source that looks dead over a plain fetch and
is actually one flag away from working is worth exactly one comment so it
does not get written off twice.

### Access findings

**Read `docs/research/library/poultry-canada.yaml` first** — it is the
machine-readable version of this section, with every URL, its status, and
what it does and does not cover.

| Source | Result |
|---|---|
| **StatCan WDS API** | **Works, and is a real API.** Table 32-10-0118-01 gives head-slaughtered and meat-output by province, chicken isolated from fowl, at `measured` grade. Table 32-10-0117-01 gives the blended "Chicken (including stewing hen)" line used for the AAFC narrative's Ontario/Quebec share. |
| StatCan Daily release PDF | Clean text extraction, no font-encoding trap. Narrative context (provincial growth direction, turkey decline cause) rather than exact figures — those come from the API. |
| AAFC chicken-industry page | The source that settles the weight-basis question StatCan's own footnotes leave open, and the source of the per-capita figure. |
| AAFC poultry import regime page | Corroborates eviscerated-weight as the sector convention (TRQs stated in "kg eviscerated"), independently of the chicken-industry page. |
| CFC 2025 Annual Report | Corroborates AAFC's producer count exactly (2,834). Also the source of a live-weight-basis provincial table that is deliberately **not** merged with StatCan's eviscerated-basis figures — see "What NOT to do". |
| FAOSTAT (API + bulk) | **Closed**, for the second country running. No response from the API host; bulk downloads time out. Not usable as a cross-check. |

## Priority 2 — What makes the demo land

- **Supply management is the single most interesting modelling contrast**
  Canada raises this the way kosher slaughter raised it for Israel, but
  from the opposite direction: Israel's difference was a loss-chain stage
  with no US analogue, Canada's is that *production itself* is quota-set
  rather than demand-set. There is no "how many chickens will be raised
  this year" answer independent of the allocation the marketing board sets
  six weeks at a time. That is worth a learning-centre fact on its own,
  and it is why "standing flock" does not exist here the way it does for
  Israel or the US: the system does not need to publish one.

- **The weight-basis contrast, twice over, inside one country.** StatCan
  reports (probably) eviscerated weight for production; CFC reports LIVE
  weight for farm size and producer price, in the same annual report.
  That is a sharper version of the trap this project already tracks (US
  live vs ready-to-cook, Israel's basis-unstated tonnage) because here it
  is the *same country's own two publishers* disagreeing on basis, not a
  cross-country comparison. A strong candidate fact.

- **Wings specifically.** Neither StatCan nor AAFC reports wings as a
  separate cut in what this pass reached. Not attempted further this
  round — an honest gap, flagged for a future pass rather than guessed at.

- **Scale comparison.** Canada's 806 million broilers/year against the US
  9.58 billion is roughly 11.9x smaller — a much closer scale than Israel's
  ~35x, and worth stating since "how does Canada compare to the US" is the
  obvious question a Canadian reader asks.

## What "done" looks like for this pass

1. [x] National head count and tonnage loaded at `measured` grade, same
   year, from a government census-based survey — the strongest evidence
   grade this project has achieved for a non-US country.
2. [x] Provincial breakdown loaded, and the reconciliation gap (or lack of
   one) stated explicitly, mirroring Israel's district cross-check.
3. [x] Per-capita figure loaded and dated, unlike Israel's unresolved one —
   as a fact, with population left `NULL` (see below).
4. [ ] Wings as a separate reported cut — not found this pass, not chased
   further; flagged for a future pass.
5. [ ] An automated updater against the WDS API — plausible given the
   API's shape, not attempted this pass, which was a one-shot research
   pull like every other country's.

## What to explicitly NOT do

- **Do not merge CFC's live-weight provincial figures with StatCan's
  eviscerated-weight head count to compute an average live bird weight.**
  The two publishers use different weight bases for the same industry in
  the same year, and dividing one by the other's head count would
  understate live weight by roughly a dressing-percentage's worth (broiler
  eviscerated yield is typically ~70% of live weight) while looking like a
  legitimate derived figure. `v_output_derived_weight` only ever combines a
  country's own `head_slaughtered` and `meat_output` rows — both are
  StatCan's, both are (per AAFC) eviscerated-basis, so the view's 1.76
  kg/bird figure is internally consistent. CFC's live-weight table is kept
  in the source library and cited in the plan, never loaded into
  `output_stat_year`.
- **Do not reuse US loss factors on Canadian data without grading
  `estimate` and saying so.** Canada's loss chain has its own structure —
  quota-driven production timing, a different disease and biosecurity
  regime — and nothing in this pass characterised it. If a US figure is
  ever borrowed as a placeholder, it must be labelled as such.
- **`country.population` stays `NULL`.** The per-capita figure this project
  actually wants (35.64 kg/person, 2025) is already published as a ratio by
  AAFC; loading it as a fact answers the question this project needs
  answered without also having to source, date, and defend a Canadian
  population estimate for a calculation nothing else in the corpus
  performs. If a future need arises for `head_slaughtered ÷ population` as
  a live query rather than a static fact, source population then, with its
  own citation, the same discipline Israel's plan already established.
- **Do not treat the Atlantic aggregate as a province.** It is a
  StatCan-defined four-province statistical region, loaded at
  `region_level='district'` — the same concept Israel's plan uses for a
  multi-council grouping — precisely so a reader counting "how many
  Canadian provinces have data" gets ten, not eleven.
