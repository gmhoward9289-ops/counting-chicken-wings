# Mexico data — research plan

Second country after Israel, and the second data point for whether the
comparison framing generalises. Mirrors `docs/ISRAEL-PLAN.md`'s structure
deliberately, including its discipline: a headline this document refuses to
lead with, a priority-1 table stating what is loaded and at what grade, and
a "what NOT to do" section written before any figure landed rather than
after.

**Status, 2026-08-16: Mexico answers the scale question at `industry`
grade, and nothing else yet.** One national broiler-meat-output series is
loaded — 3,447,600 tonnes for 2019 (peer-reviewed citation of a dated SIAP
publication, `measured`) and 3,888,000 / 3,985,000 tonnes for 2023 / 2024
(USDA FAS GAIN report quoting SIAP secondhand, `industry`) — plus one
cross-validated fact (self-sufficiency ~79–80% for 2023) and five
industry-structure facts. No head count, no standing flock, no output
value in pesos, and no subnational table landed. Served at
`GET /api/output/MEX` once built.

---

## The headline this demo should NOT lead with

Two claims looked ready to be Mexico's memorable line, and both turned out
to be exactly the kind of trap Israel's per-capita ranking was.

**Claim 1 — "Mexico is the Nth largest poultry producer in the world."**
Three different values of N, from three different publishers, describing
overlapping years:

| Claim | Source | Year |
|---|---|---|
| 6th largest producer | USDA FAS GAIN MX2024-0040 | 2024 |
| 5th largest producer | avicola.com.mx | 2025 |
| **1st** producer of poultry carcass meat worldwide | Consejo Nacional Agropecuario (CNA) | 2021 |

The CNA claim is not a rounding difference from the other two — it is a
different rank entirely, on what is described as a narrower product
category ("carcass meat"). That is very likely definition drift, the same
species as Israel's poultry-vs-chicken, carcass-vs-retail confusion, but it
was not chased to ground in this pass. **Do not publish any world-rank
claim for Mexico.** State only what is directly checkable: production
tonnage, cited, dated, and left to speak for itself.

**Claim 2 — per-capita chicken consumption.** Five figures, spanning a
~70% range, none reachable from a single authoritative series:

| Figure (kg/person/yr) | Source | Year |
|---|---|---|
| 22.4 | bmeditores, citing "OCDE/FAO data" | 2023 |
| 28.7 | UNA, via Rebollar-Rebollar (2021) | 2019 |
| 34.5 | Consejo Nacional Agropecuario | 2021 |
| 35.82 | UNA (own site) | 2025 |
| 37.75 | USDA FAS GAIN MX2024-0040 | 2024 |

This is Israel's per-capita problem again, in the opposite direction: there
Israel's own rank was contested across sources that all agreed it should be
high; here the *level* itself will not converge across sources that are not
even trying to make a ranking claim. `country.population` stays **NULL**
for MEX, exactly as it does for ISR, and no fact or output row states a
per-capita figure. See `docs/research/library/poultry-mexico.yaml` for the
full accounting of both traps.

**What the demo can lead with instead:** Mexico is self-sufficient in
chicken meat to a cross-validated ~79–80% (three independent sources agree
within a point — production ÷ total supply from the USDA GAIN table
itself, corroborated separately by two trade-press figures), and the
industry ships roughly 39.3 million live birds a week per its own trade
body. Both are checkable and both are honestly graded.

---

## Priority 1 — Core production figures

| Field | Why the model needs it | Status 2026-08-16 |
|---|---|---|
| Broilers slaughtered per year (head) | The denominator for everything | **NOT LOADED.** No enumerated count found anywhere. UNA reports "approximately 39.3 million chickens per week" (2025, industry) — deliberately not annualized into a head count; multiplying by 52 would assert a constant weekly rate nobody published, stacking one unsourced assumption on an already-unenumerated figure. Kept as a fact, in UNA's own units. |
| Average live weight (kg) | Drives wing size | **NOT LOADED.** No source found that reports it directly, and with no head count to divide against, there is nothing to derive it from the way Israel's 2.3 kg/bird was derived from CBS tonnage ÷ an industry head count. |
| Total chicken meat production (tonnes) | The scale figure | **LOADED**, two grades. 3,447,600 t for 2019 at `measured` (peer-reviewed citation of a dated SIAP table). 3,888,000 t (2023) and 3,985,000 t (2024, provisional) at `industry` (USDA FAS GAIN report quoting SIAP secondhand; the report's own PSD table is annotated "Not official USDA data"). |
| Standing flock (head) | Not throughput, but a real figure elsewhere | **NOT LOADED.** The GAIN report ranks flock SIZE by state (Jalisco leads) but gives no national total, and that ranking is for **all poultry**, not broilers specifically — Jalisco leads it partly because Jalisco also leads egg-layer population. |
| Output value (pesos) | Scale in local currency | **NOT LOADED.** No aggregate peso figure for chicken meat output was found in this pass; several sources give VALUE for the whole livestock sector or for feed spend, not for chicken meat output specifically, and mixing those in would misattribute a bigger number to a smaller category. |
| Subnational / state breakdown | The choropleth's Mexican counterpart | **NOT LOADED as a table.** See "The taxonomy and subnational question" below — SIAP genuinely publishes this, but this project could not reach SIAP's own portal, and the secondary sources that do report state shares disagree with each other on ranking order for 2023–24. Carried as a fact (top state, and the documented conflict) rather than a `districts:` block. |
| Per-capita consumption (kg) | The headline candidate | **DELIBERATELY UNSOURCED.** See the trap above. Population is NULL. |
| Self-sufficiency / import share | Mexico imports roughly a fifth of demand, unlike Israel's net-surplus story | **LOADED as a fact.** ~79.4% (2023), cross-validated by two independent trade-press figures within a point. |

---

## Sources, in order of preference

1. **SIAP** (Servicio de Información Agroalimentaria y Pesquera, part of
   SADER) — Mexico's NASS-equivalent, publishes "Avance de la Producción
   Pecuaria" and a by-state livestock closure at
   `infosiap.siap.gob.mx` / `nube.agricultura.gob.mx`. **Unreachable from
   this environment** — DNS failure on the first host, connection refused
   on the second, for every path tried. This is the single biggest gap in
   this research pass: SIAP genuinely publishes exactly the by-state
   "carne en canal de ave" table this project wants, and nobody has yet
   read it directly. See the dead-ends in
   `docs/research/library/poultry-mexico.yaml`.
2. **SADER / Compendio Estadístico** — reached only for a consumer-facing
   taxonomy article (`gob.mx/agricultura`), not a statistical table.
3. **UNA** (Unión Nacional de Avicultores) — Mexico's poultry trade body,
   reached at `una.org.mx`. Industry-grade by construction, and its
   figures never get promoted past `industry` on that basis alone.
4. **FAOSTAT** — not directly queried this pass (Israel's research already
   found FAOSTAT's API and bulk downloads closed off as of 2026-07-29;
   this was not re-tested for Mexico specifically, and re-testing is a
   fair thing for the next pass to do before assuming it is still closed).
5. **USDA FAS GAIN** (`Mexico: Poultry and Products Annual`, MX2024-0040)
   — reached directly, and turned out to be the single most useful
   document in this pass: English-language, PDF, quoting SIAP under its
   own chart, and carrying trade, price, and structural detail (TIF
   inspection coverage) that neither SIAP nor UNA's own pages gave up.
   Israel had no equivalent GAIN report; Mexico does, and it is why this
   plan reaches `industry` grade on national tonnage rather than nothing
   at all.
6. **Peer-reviewed literature** — not in Israel's source list at all, and
   worth adding here: Rebollar-Rebollar (2021), in a Mexican agricultural
   economics journal, cites a specific dated SIAP publication for a 2019
   figure. A peer-reviewed paper naming its primary source with a
   publication date is a legitimate route to a government figure this
   project could not reach directly, and it is graded `measured` rather
   than `industry` on that basis.

### Access findings

**Read `docs/research/library/poultry-mexico.yaml` first** — it is the
machine-readable version of this section, records exactly what happened
for every URL tried, and is more current than the summary below.

The single correction that matters: **SIAP's own portals could not be
reached at all**, not even partially. Every other country plan in this
project so far (Israel included) eventually found a way into the primary
agency's own data, even if via an unexpected route (CBS's SharePoint REST
API rather than its published pages). Mexico is the first case where the
primary agency simply did not answer, for reasons that look like network
policy rather than the data not existing — `infosiap.siap.gob.mx` fails at
the DNS level, `nube.agricultura.gob.mx` resolves but refuses the TCP
connection. A human with a browser, or an agent with real browser tooling
rather than a bare fetch, is very likely to succeed where this pass did
not; that is the highest-value next step for anyone building on this.

| Source | Result |
|---|---|
| **USDA FAS GAIN MX2024-0040** | **Works, and is the way in.** PDF, 200 OK, extracts cleanly with PyMuPDF once fetched (WebFetch's own summarizer refuses PDFs as "binary" but the file it saves to disk is ordinary text underneath). Cites SIAP directly for its production chart. |
| **Redalyc peer-reviewed PDF** | **Works, same PDF-extraction route.** Cites a dated SIAP publication (9 Oct 2020) for a 2019 figure, and UNA (15 Oct 2020) for consumption context. |
| SIAP `infosiap.siap.gob.mx` | **DNS failure.** Does not resolve from this environment at all. |
| SIAP `nube.agricultura.gob.mx` | **Connection refused.** Resolves to an IP, refuses port 443 on every path (`/cierre_pecuario/`, `/avance_pecuario/`, `/datosAbiertos/Pecuario.php`), http and https alike. |
| `web.archive.org` | **Blocked by the fetch tool itself**, not by the archive — "Claude Code is unable to fetch from web.archive.org". No snapshot fallback was available for either SIAP host. |
| El Sitio Avícola, aviNews | **403 Forbidden** to this fetcher on both. Not used as citations because the pages were never actually read (a search-result summary is not a source). |
| UNA `industria/` and `indicadores-economicos/` | **Reachable.** The first carries real numbers (weekly throughput, per-capita, 2025 production forecast); the second is a landing page linking to PDF reports that were not opened in this pass. |
| Trade press (bmeditores, CNA, avicola.com.mx) | **Reachable, and the trap.** Each independently reachable, each carrying at least one figure that conflicts with another source — the taxonomy definition (bmeditores) is the one piece of unambiguous, load-bearing value among them. |

---

## The taxonomy question, resolved

**"Carne de ave" (poultry meat) and "carne de pollo" (chicken meat) are
not the same category in Mexican statistical usage, and SIAP's own
aggregate figures can mix broiler chicken with turkey.** This is stated
explicitly, in English, by a trade-press source (bmeditores): *"Carne de
ave (poultry meat): Includes chicken, poultry products/pasta, and turkey"*
against *"Carne de pollo (chicken meat): Specific to chicken only."* A
second, independent source — a SADER consumer-facing article — corroborates
the same three-way split in its own words: *pollo de engorda* (broiler,
the meat bird), *gallina* (hen, further split by breed weight — light for
eggs, heavy for meat, semi-heavy dual-purpose), and *guajolote/pavo*
(turkey, a separate bird entirely, mostly consumed at holidays).

**Consequence for this corpus: every figure loaded into
`data/output_mexico.yaml` is checked against its source's own wording and
loaded only when the source itself says "pollo" (chicken) rather than
"ave" (poultry in general).** The USDA FAS GAIN report's PSD table is
titled "Meat, Chicken" specifically, not "Meat, Poultry" — checked, and
it qualifies. The peer-reviewed 2019 figure is captioned "carne de pollo"
in the paper's own words — checked, and it qualifies. Neither figure is
silently promoted from a broader "ave" aggregate, and no aggregate figure
found in this pass (UNA's "7.31 million tonnes" combined food-production
number, for instance) is loaded as if it were chicken-specific.

The one place this discipline could not be fully verified: the GAIN
report's own **flock-size** ranking by state ("Jalisco... 50 percent of
Mexico's poultry population") is explicitly a poultry-wide figure — stated
plainly in the plan's priority-1 table above — and is not loaded as a
broiler statistic anywhere, unlike the report's separate and genuinely
broiler-specific state ranking for chicken *meat production*.

---

## The subnational question

**SIAP genuinely publishes a by-state "carne en canal de ave" report,
described identically to Israel's CBS district table in every search
result found — but this project could not reach it.** Unlike Israel, where
the open question was *whether* subnational data existed at all (it did,
47 districts and councils), Mexico's open question is narrower and sharper:
the data almost certainly exists in a genuinely complete, citable form, and
simply was not reachable by the tools available in this pass.

What *is* available, and why it does not become a `districts:` block:

- The **USDA FAS GAIN report** names an ordinal ranking for chicken-meat
  production specifically (Veracruz, then Aguascalientes, then Jalisco,
  then Querétaro, then — more loosely — Durango, Chiapas, Guanajuato,
  Puebla; the top eight are said to total 70% of national output) but
  gives **no percentages or absolute tonnages per state**.
- A **2019 peer-reviewed citation** of SIAP gives percentages for exactly
  four states (Veracruz 11.7%, Jalisco 11.6%, Aguascalientes 11.5%,
  Querétaro 10.3%) — real numbers, but only a third of the country's 32
  states, with no grand total to reconcile against the way Israel's
  district table reconciled (imperfectly, but transparently) against its
  own national output figure.
- A **2024 trade-press figure** (bmeditores) gives percentages for five
  states (Veracruz 13.6%, Jalisco 11.5%, Aguascalientes 10.7%, Querétaro
  9.8%, Durango 7.4%) that **conflict with the GAIN report's own ordinal
  ranking** for essentially the same years — bmeditores has Jalisco ahead
  of Aguascalientes; GAIN has Aguascalientes ahead of Jalisco. A third
  source (CNA, 2021) agrees with bmeditores's ordering, not GAIN's.

None of these is a `districts:` block in the shape `output_stats()`
expects: none is a complete, self-reconciling table with a grand total,
and two of the three partial pictures disagree with each other on state
rank for the same span of years. Forcing four or five named states into a
`region_level='district'` table, computed by multiplying a contested
percentage against a well-sourced national total, would manufacture a
number nobody actually published. **The honest choice is to carry the
state concentration as a fact** — naming Veracruz as the consistent
national leader across every year and source checked from 2019 onward
(2019, 2021, 2023-24; the one earlier year checked, 2014, had
Aguascalientes on top per a SADER article), and naming the
Jalisco/Aguascalientes conflict explicitly rather than picking a side — **and to leave the full state table for whoever next
gets a working connection to SIAP's own portal.**

---

## What "done" looks like for this plan

1. [x] National broiler meat output loaded and cited, at an honestly
   stated grade (`measured` for 2019, `industry` for 2023-24).
2. [x] The taxonomy trap (carne de ave vs. carne de pollo) resolved in
   writing, with every loaded figure checked against it.
3. [x] Self-sufficiency shipped as a cross-validated fact.
4. [x] The two headline traps (world rank, per-capita) documented and
   deliberately not shipped, mirroring Israel's per-capita discipline.
5. [ ] A head count, at any grade. **Blocked, not forgotten** — UNA's
   weekly figure is the nearest thing found, and annualizing it ourselves
   was rejected as inventing a rate nobody published. A monthly or annual
   UNA/SIAP throughput series, if one exists, would unblock this.
6. [ ] A real subnational table. **Blocked on SIAP access, not on SIAP
   publishing the data** — the single most valuable thing a follow-up pass
   with working browser access to `infosiap.siap.gob.mx` or
   `nube.agricultura.gob.mx` could add.
7. [ ] Output value in pesos. Not attempted seriously this pass; worth a
   dedicated search next time (SIAP's PSD-equivalent likely carries it).

## What to explicitly NOT do

- **Do not load any figure captioned "carne de ave" as if it were
  broiler-specific.** Check the source's own wording every time; "ave"
  routinely includes turkey in Mexican statistical usage.
- **Do not annualize UNA's weekly throughput figure into a
  `head_slaughtered` row.** Multiplying by 52 asserts a constant rate
  nobody published. If an annual figure is wanted, find one; do not
  manufacture one.
- **Do not build a `districts:` table from percentages that disagree with
  each other.** Two of the three partial state-share pictures found in
  this pass conflict on ranking order for the same years; resolving that
  conflict by picking a source would be deciding it on the reader's
  behalf.
- **Do not publish a world-rank claim** ("Nth largest producer") — three
  sources give three different ranks for overlapping years, one of them
  radically different ("1st" vs "5th/6th") in a way that reads as a
  different product definition rather than three measurements converging.
- **Do not publish a per-capita consumption figure or fill in
  `country.population` for MEX.** Five sources, a ~70% spread, no
  reachable primary series that would settle it — the same reasoning, and
  the same NULL, as Israel.
- **Do not reuse US loss factors for Mexico without saying so.** Nothing
  in this pass investigated Mexico's slaughter/inspection chain (TIF
  federal inspection is noted as a structural fact, not modelled as a loss
  stage) — that is future work, not something to paper over with an
  American assumption relabeled as Mexican.
- **Do not treat the GAIN report's PSD table as `measured`.** It is
  self-annotated "Not official USDA data" and is one step removed from
  SIAP's own publication; `industry` is the honest grade even though the
  publisher is a government body.
