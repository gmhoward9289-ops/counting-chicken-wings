# China data — research plan

Fifth country, and mirrors `docs/MEXICO-PLAN.md`'s shape deliberately: a
headline this document does and does not lead with, a priority-1 table
naming what is loaded and at what grade, and a "what NOT to do" section
written to be checked against rather than discovered after the fact.

**Status, 2026-08-16: China answers the scale question at `industry` grade,
with one genuinely unresolved production-estimate conflict this pass could
not adjudicate.** National chicken meat output is loaded for 2023-2025
(14.80 / 15.35 / 16.20 million tonnes, USDA FAS attaché reports quoting a
"Meat, Chicken" PSD table annotated "Not official USDA data"), alongside a
derived self-sufficiency series (95.1% → 97.4%, rising, and China became a
net exporter in 2024) and five industry-structure and taxonomy facts. No
head count, no standing flock, no output value in yuan, and no provincial
breakdown landed. Served at `GET /api/output/CHN` once built.

---

## The headline this demo CAN lead with, carefully

**China is the world's second largest chicken meat producer — and this is
one of the rare claims in this project with no competing rank found.**
USDA's own global circular (`Livestock and Poultry: World Markets and
Trade`, April 2026) states it plainly: *"China is the world's second
largest producer of chicken meat, significantly behind the United States
and often on par with Brazil."* Unlike Mexico, where three sources gave
three different world ranks for overlapping years, no second source
surfaced in this pass that contradicts this one. It is loaded as a fact.

**What keeps this from being a clean headline on its own: China produces a
lot and eats comparatively little of it per person.** The same USDA
circular gives China's 2025 per-capita chicken consumption as about 11
kg/person — low next to pork within China itself (43 kg) and far below the
United States (55 kg), Japan (24 kg) and Taiwan (42 kg). That is a genuinely
interesting contrast (world's #2 producer, not a top-tier per-capita eater)
and is loaded as a fact — but it is carried at `industry` grade and flagged
explicitly as **single-source**: unlike Mexico's five conflicting per-capita
figures, or Israel's contested ranking, this pass found exactly one number
and no second Chinese domestic figure to corroborate or conflict with it.
That is a gap, not a resolved question, and the fact says so.

## The headline this demo should NOT lead with — a real, unresolved conflict

Two credible-looking figures for the SAME thing (chicken meat production,
2024) disagree by 44%, and this pass could not resolve which is right:

| Figure | Source | Scope |
|---|---|---|
| 15.35 million tonnes | USDA FAS GAIN CH2025-0170 ("Meat, Chicken" PSD table) | Chicken meat, all types |
| 22.11 million tonnes | China's National Broiler Industry Technology System, via AgriPost.CN | White + yellow feather broiler meat ONLY — a third category (small white-feather) is not even included |

Both describe chicken specifically, not an all-poultry aggregate, so the
taxonomy trap that explains several of this project's other cross-source
gaps does not explain this one. The most likely explanation — that one
figure is live weight and the other is processed/carcass-equivalent weight,
the same basis ambiguity this project already tracks for Canada (StatCan
eviscerated vs. Chicken Farmers of Canada live) and the US (live vs.
ready-to-cook) — was **not confirmed**: neither source states its weight
basis. **Do not assert a resolution.** This project loads the more
conservatively and precisely sourced of the two (the USDA PSD figure) into
`output_stat_year`, and records the larger industry estimate as a fact
(`china-production-estimate-conflict`) rather than silently dropping it —
the same "report the spread, don't adjudicate" discipline the task brief
asked for.

**Consequence for the head count.** The 22.11-million-tonne figure comes
bundled with China's only broiler-specific bird count found in this pass —
14.84 billion birds for 2024. It is **not loaded as `head_slaughtered`**,
because it cannot be reconciled against the tonnage this project actually
loads: pairing an unreconciled head count with a tonnage figure from a
different source and a different implied weight basis would silently
assert an average bird weight nobody measured. See
`v_output_derived_weight` in `schema.sql` — that view exists specifically
to divide a country's own head count by its own tonnage, and feeding it two
figures that disagree by 44% would produce a number that looks precise and
is not.

---

## Priority 1 — Core production figures

| Field | Why the model needs it | Status 2026-08-16 |
|---|---|---|
| Broilers slaughtered per year (head) | The denominator for everything | **NOT LOADED.** The only figure found (14.84 billion, 2024, China's National Broiler Industry Technology System via trade press) cannot be reconciled with the tonnage this project loads for the same year — see "The production-estimate conflict" above. Kept as a fact, not a table row. |
| Average live weight (kg) | Drives wing size | **NOT LOADED.** No source stating it directly, and the head-count/tonnage conflict above means there is no reconciled pair to derive it from the way Israel's or Canada's were. |
| Total chicken meat production (tonnes) | The scale figure | **LOADED**, `industry` grade, three years: 14,800,000 t (2023), 15,350,000 t (2024), 16,200,000 t (2025, provisional). All from USDA FAS GAIN "Meat, Chicken" PSD tables, annotated by the reports themselves as "Not official USDA data". |
| Standing flock (head) | Not throughput, but a real figure elsewhere | **NOT LOADED.** No source found publishing a national broiler inventory total; China's fast broiler turnover makes this an unusual thing for any source to publish, and none did. |
| Output value (yuan) | Scale in local currency | **NOT LOADED.** The GAIN PSD tables carry quantities, not values; no aggregate CNY figure for chicken meat output specifically was found elsewhere. |
| Subnational / provincial breakdown | The choropleth's Chinese counterpart | **NOT LOADED as a table.** See "The subnational question" below — provincial poultry data is genuinely published, but every figure this pass could reach is for all-poultry (家禽), not chicken specifically, and the one primary provincial page checked directly failed on a TLS certificate error. |
| Per-capita consumption (kg) | The headline candidate | **LOADED as a fact, `industry` grade, single-source.** ~11 kg/person, 2025, USDA FAS. Not cross-validated — see above. |
| Self-sufficiency / import share | China is a large producer; is it also import-dependent? | **LOADED as a fact, `derived` grade.** 95.1% (2023) → 97.0% (2024) → 97.4% (2025), rising; China became a net exporter in 2024. |

---

## Sources, in order of preference

1. **National Bureau of Statistics of China (NBS)** — China's NASS
   equivalent. Its national communique is reachable, in Chinese, and gives
   a real government-grade production figure — but only for 禽肉 (poultry
   meat broadly), never broken out to chicken specifically. This is the
   single most consequential finding of this pass: **the primary source is
   reachable, and still cannot answer the chicken-specific question**,
   which is a different shape of gap from Mexico's (SIAP unreachable) or
   Israel's (CBS reachable, but the count itself was never published by
   anyone government-grade).
2. **USDA FAS GAIN reports** (`China: Poultry and Products Annual`,
   CH2024-0108 and CH2025-0170) — the route this project actually used for
   chicken-specific tonnage, exactly as Mexico's plan used its own GAIN
   report. Both explicitly caption their own PSD table "Not official USDA
   data" — a Post estimate reconciling NBS and trade data, one step
   further removed from a primary measurement than a government census.
3. **USDA FAS `Livestock and Poultry: World Markets and Trade`** — a
   different USDA publication from the country-specific GAIN reports, and
   the source of this project's one clean world-rank statement and its
   only per-capita figure. Blends settled figures with forecasts
   throughout, so treated as `industry` grade like the GAIN reports rather
   than promoted for being government-published.
4. **China's National Broiler Industry Technology System**
   (中国肉鸡产业技术体系) — reached only secondhand, via AgriPost.CN trade
   press, not this system's own publication directly. The source of the
   conflicting production estimate and the only broiler head count found —
   flagged for a future pass to reach directly, the same shape of gap
   Mexico's plan left for SIAP.
5. **Provincial statistics bureaus** (Shandong, Henan, etc.) — genuinely
   publish poultry production data, but every figure reachable this pass
   was for all-poultry, and the one bureau page fetched directly
   (Shandong) failed on a TLS certificate hostname mismatch. Not chased
   further this pass.
6. **FAOSTAT** — not attempted this pass. Israel's and Canada's research
   both independently found FAOSTAT's API and bulk downloads closed off
   (2026-07-29 and again in Canada's pass); not re-tested for China, and
   re-testing is a fair thing for a future pass to do before assuming it
   is still closed.

### Access findings

**Read `docs/research/library/poultry-china.yaml` first** — it is the
machine-readable version of this section.

| Source | Result |
|---|---|
| **NBS national communique** (`stats.gov.cn`) | **Reachable, clean text extraction, no font-encoding trap.** Chinese-language, government. Gives 禽肉 (all-poultry) production only — no chicken-specific breakout, no head count in the production section. |
| **USDA FAS GAIN PDFs** (CH2024-0108, CH2025-0170) | **Reachable, 200 OK.** WebFetch's own text extraction refuses both PDFs as "binary content, cannot read" — the same failure Mexico's GAIN PDF hit — but the files WebFetch saves to disk as a side effect extract cleanly with PyMuPDF (`fitz`): ordinary embedded text, no font-encoding trap either. |
| **USDA FAS `Livestock and Poultry: World Markets and Trade`** | **Reachable, 200 OK, same PDF-extraction route.** English, government, the source of this project's one uncontested world-rank claim. |
| AgriPost.CN broiler-industry article | **Reachable.** Trade press citing China's National Broiler Industry Technology System by name — a real, checkable attribution, even though this pass did not reach that system's own report directly. |
| Shandong Provincial Bureau of Statistics | **TLS certificate hostname mismatch** on every fetch attempt (`tjj.shandong.gov.cn`'s certificate is issued for `*.ybj.shandong.gov.cn`) — a genuine access failure, the same shape as Canada's `www150.statcan.gc.ca` TLS handshake reset, but not resolved by forcing an older TLS version in this pass. Flagged as the highest-value target for a future subnational pass. |
| Secondary province-ranking aggregators (search-result summaries) | **Not independently read, therefore not cited.** Describe Shandong as the leading poultry province by a wide margin, but every number seen this way is for all-poultry, not chicken specifically — the same discipline that excluded El Sitio Avícola and aviNews from Mexico's citations. |
| feedandadditive.com | **403 Forbidden** to this fetcher. A "13.56 billion broilers slaughtered" figure attributed to it circulated in search results but was never independently read on the page itself — not cited, for the same reason Mexico's unread trade-press pages were not cited. |

---

## The taxonomy question, resolved (mostly)

**China's national statistics distinguish 禽肉 (poultry meat — chicken,
duck, goose and other fowl together) from 鸡肉/肉鸡 (chicken meat / broiler
chickens specifically), and the NBS national communique — the one genuinely
primary, government-grade document this project reached — publishes only
the former.** *"禽肉产量2660万吨，增长3.8%"* (poultry meat production
reached 26.6 million tonnes, up 3.8% year-on-year, 2024) sits in the same
sentence as pork, beef and mutton, with no chicken-specific breakout
anywhere in the document.

**Consequence for this corpus: nothing loaded into `data/output_china.yaml`
comes from the NBS communique.** Every figure actually loaded is from the
USDA FAS GAIN reports' "Meat, Chicken" PSD table, which the reports
themselves title and scope to chicken specifically — checked against the
report text before loading, the same discipline Mexico's plan applied to
"carne de ave" vs. "carne de pollo".

This is a different shape of taxonomy problem from Mexico's. Mexico's trap
was that *secondary* sources sometimes blurred "ave" and "pollo"; the
primary source (SIAP) itself, when reachable, was expected to separate
them cleanly. China's trap is sharper: **the one primary, government-grade
document this project could actually reach does not separate them at
all**, at the national level. Whether NBS publishes a chicken-specific
breakdown somewhere this pass did not find (a more detailed yearbook, a
sector-specific bulletin) is an open question for a future pass, not a
settled "NBS doesn't have this."

## The production-estimate conflict, in full

See "The headline this demo should NOT lead with" above for the numbers.
Worth restating the discipline explicitly: this project's rule (per the
research brief) is to report disagreeing production estimates side by
side and name the likely cause without picking a winner. Applied here:

- The USDA figure (15.35 million tonnes, 2024) is loaded into
  `output_stat_year` because it is the more precisely scoped of the two —
  a single PSD line item with an explicit "Not official USDA data" caveat
  already carried at `industry` grade — rather than because it is judged
  more accurate.
- The larger industry estimate (22.11+ million tonnes) is recorded as a
  fact, not suppressed, specifically so a reader comparing this project
  against another source that cites the larger figure can see why the two
  disagree rather than concluding one of them made an error.
- The likely explanation (live vs. processed weight basis) is stated as a
  hypothesis, explicitly not confirmed. A future pass that can locate
  either source's own stated basis — the National Broiler Industry
  Technology System's original report, or USDA's underlying PSD
  methodology notes — should resolve this properly rather than this
  project asserting an unverified guess.

## The subnational question

**Chinese provincial statistics bureaus genuinely publish poultry
production data — this project just could not turn it into a chicken-specific,
self-reconciling table this pass.** Two separate problems, not one:

- **Scope.** Every provincial figure reachable this pass (Shandong leading
  by a wide margin per secondary reporting, Henan a distant second) is for
  家禽 (all poultry), not 肉鸡 (chicken specifically) — the same taxonomy
  gap that blocks the national figure, one level down.
- **Access.** The one provincial statistics bureau page fetched directly
  (Shandong, China's presumptive leading poultry province) failed with a
  TLS certificate hostname mismatch — the certificate served is issued for
  a completely different subdomain (`*.ybj.shandong.gov.cn`). This is a
  genuine access failure in the shape of Canada's `www150.statcan.gc.ca`
  TLS handshake reset, but unlike Canada's, forcing an older TLS version
  was not attempted in this pass and may or may not fix it.

Building a `districts:` block from search-result summaries of pages never
independently read, for a measure (all-poultry) that is not even this
corpus's species, would compound two unverified steps into a table that
looks authoritative. **The honest choice is no `districts:` block at all**,
with both blockers named explicitly here for whoever attempts the next
pass — unlike Mexico's subnational gap, where the blocker was purely
access, China's is scope AND access together.

---

## What "done" looks like for this pass

1. [x] National chicken meat output loaded and cited, at an honestly
   stated grade (`industry`, three years, 2023-2025).
2. [x] The taxonomy trap (禽肉 vs. 鸡肉/肉鸡) resolved in writing, with
   every loaded figure checked against it.
3. [x] Self-sufficiency shipped as a derived fact, computed transparently
   from the same table the production figures come from.
4. [x] The world-rank claim and the per-capita figure both loaded, each
   with its evidentiary limits stated plainly (single source for
   per-capita; no competing claim found for world rank, which is itself
   worth stating since most other countries in this corpus DO have one).
5. [x] The production-estimate conflict documented in full, with neither
   figure silently dropped and no resolution asserted.
6. [ ] A head count, at any grade. **Blocked on the conflict above, not
   forgotten** — the only figure found cannot be reconciled with the
   tonnage this project already loads. Resolving the weight-basis question
   would unblock this.
7. [ ] A real subnational table. **Blocked on scope AND access** — see
   above. The single most valuable next step is reaching either NBS's more
   detailed publications or a provincial bureau's chicken-specific
   (not all-poultry) table directly.
8. [ ] Output value in yuan. Not attempted seriously this pass; worth a
   dedicated search next time.

## What to explicitly NOT do

- **Do not load NBS's 禽肉 (poultry meat) figure as if it were
  chicken-specific.** It is this project's most consequential taxonomy
  trap for China precisely because the primary source itself, when
  reachable, does not separate the species out — check every NBS-derived
  figure against this before loading.
- **Do not resolve the production-estimate conflict by picking a source.**
  Both the USDA and the National Broiler Industry Technology System
  figures describe chicken meat specifically for the same year and
  disagree by 44%; a future pass with a confirmed weight basis for either
  should resolve this, not a guess dressed up as a decision.
- **Do not load the 14.84-billion-bird head count without first
  reconciling it against a compatible tonnage figure.** Pairing it with
  the USDA tonnage this project already loads would silently assert an
  implausible average bird weight; pairing it with its own source's
  tonnage would still be an unreconciled industry estimate at both ends.
- **Do not build a `districts:` table from unread secondary summaries.**
  Every provincial figure surfaced this pass came from search-result
  summaries of pages this project did not independently fetch and verify
  — the same discipline that kept El Sitio Avícola and aviNews out of
  Mexico's citations applies here to every province-ranking blog post.
- **Do not publish a per-capita consumption figure as cross-validated.**
  Exactly one Chinese per-capita figure was found (USDA, 11 kg/person,
  2025) — loaded as a fact, but explicitly flagged single-source, unlike
  Canada's uncontested AAFC figure or Mexico's five-way conflict. A second
  figure, agreeing or disagreeing, would change how confidently this
  project can state it either way.
- **Do not fill in `country.population` for CHN.** Same discipline as
  every other country in this project — a per-capita ratio is loaded as a
  fact when a source publishes one; population itself stays NULL until a
  concrete need for it arises with its own citation.
- **Do not reuse US, Canadian or Mexican loss factors for China without
  saying so.** Nothing in this pass investigated China's slaughter,
  inspection or grow-out loss chain — that is future work, not something
  to paper over with a borrowed assumption relabeled as Chinese.
