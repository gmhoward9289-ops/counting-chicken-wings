# Israel data — research plan

**Why this jumped the queue:** the platform is being demoed to people in
Israel. The roadmap put international work after v1.0; this supersedes that
for Israel specifically. Everything else international stays post-1.0.

**Status, 2026-07-29: Israel answers the question, at two different grades.**
Three CBS
tables from Statistical Abstract chapter 21 are loaded and cited — broiler
output in tonnes and shekels 2000–2024, an end-of-year flock series back to
1960, and broiler marketing for 47 districts and regional councils. Served at
`GET /api/output/ISR`, with coverage per country at `GET /api/countries`.

**The denominator, resolved at industry grade — and both readings kept.** CBS
publishes no head-slaughtered series anywhere in chapter 21. A second pass found
one outside CBS: **~260 million broilers a year**, attributed to Moti Elkabetz,
secretary of the Poultry Breeders Association, in the Times of Israel
(2025-09-07). Loaded at `industry`, never `measured`, because nobody enumerated
it.

Neither reading is imposed on the reader:

| Call | What Israel answers |
|---|---|
| `GET /api/output/ISR` | scale **and** count. 260M birds, and ~2.31 kg a bird derived against CBS tonnage |
| `GET /api/output/ISR?min_confidence=measured` | scale only. No bird count, and the response names the row it dropped |

**The cross-check is what makes the industry figure worth having.** 600,072
tonnes (CBS, measured) ÷ 260 million birds (industry) = **2.31 kg a bird**, which
is what a 40-day broiler weighs — and the 40 days comes from the same interview.
Two sources that were not derived from each other, agreeing. It lives in
`v_output_derived_weight`, carries the *weaker* parent's grade, and reports its
`year_gap` of 1 rather than implying a same-year measurement.

Still refused: deriving head from tonnage using the **US** 6.62 lb. That would
turn an American assumption into an Israeli fact, which the rules at the foot of
this document forbid, and it is now unnecessary.

This document is written to be handed to a research agent. Each item states
the exact question, where to look, and what "done" means.

---

## The headline the demo should NOT lead with

Israel is, or has recently been, the highest per-capita chicken consumer in the
world. It is the obvious hook for an Israeli audience, and after two research
passes it is the one claim in this document that **still cannot be sourced**.

Five figures, all claiming the same rank:

| Figure | Source | Year | Reachable? |
|---|---|---|---|
| 58.2 kg/person | OECD-FAO Outlook, via Euromeatnews | unclear | **No — 404** |
| 57.7 kg/person | trade press, "ranked first in the world" | unclear | No |
| 64.9 kg/person | circulating without clear provenance | 2026 | n/a |
| **70.83 kg/person** | World Population Review, citing FAOSTAT food balances | 2022 | Yes |
| Kuwait 65.43 kg — *ahead of Israel* | separate trade-press dataset | 2023 | No |

**A 20% spread across sources that all claim first place is not a citation, it
is a warning.** The likely cause is definition drift — poultry meat versus
chicken meat, carcass versus retail weight, different years — and the primary
series that would settle it are both closed: FAOSTAT's API and bulk downloads
return 401/403/521, and the OECD-FAO annex PDF extracts as font-encoded
gibberish.

So `country.population` stays NULL, `/api/countries` reports
`per_capita: false`, and a test fails if any of these numbers turns up in a
fact. **Lead the demo on the mangal instead** — chicken wings on the Yom
Ha'atzmaut grill is sourced, twice, and cannot be disproved on a phone.

**Done means:** one primary series, one definition stated explicitly, the year
named, and Israel's rank as of that year — even if the answer is "second".
`batch-05-israel-hebrew.md` item 5 carries this, and says not to ship one
otherwise.

---

## Priority 1 — Core production figures

Everything here is what the model actually needs to answer the wing question
for Israel rather than just decorate a slide.

| Field | Why the model needs it | Status 2026-07-29 |
|---|---|---|
| Broilers slaughtered per year (head) | The denominator for everything | **LOADED at `industry`.** ~260 million/yr, named official via Times of Israel. A government figure is still wanted — see `batch-05-israel-hebrew.md` items 1–2 |
| Average live weight (kg) | Drives wing size, mirrors our US state data | **DERIVED at `industry`.** 2.31 kg/bird from CBS tonnage ÷ the industry head count, consistent with the 40-day grow-out the same source gives. CBS publishes no per-bird weight directly |
| Total chicken meat production (tonnes) | Cross-check against head × weight | **LOADED.** 600,072 t for 2024 (provisional), back to 2000. `cbs-st21-11-output-2025` |
| Standing flock (head) | Not throughput, but the only head figure that exists | **LOADED.** 37,895 thousand at end of 2024, series back to 1960. `cbs-st21-08-livestock-2025` |
| Output value (NIS) | Scale in the local currency, uncconverted | **LOADED.** NIS 5,367.6m for 2024 |
| Subnational breakdown | Gives the choropleth an Israeli counterpart | **LOADED.** 47 districts and councils, 8 suppressed. `cbs-st21-04-marketing-2025` |
| Per-capita consumption (kg) | The headline | **UNSOURCEABLE for now** — see below. Population is deliberately NULL |
| Self-sufficiency / import share | Israel is reported as a **net surplus** producer, which is unusual and interesting | Not attempted |

The **~260 million broilers/year** figure is now loaded, and the inventory series
supports rather than substitutes for it: a flock of 37.9 million turning over
five to seven times a year is consistent with 260 million, which is why the two
are separate measures (`inventory_eoy` and `head_slaughtered`) and a test asserts
the throughput figure exceeds the flock several times over.

**Two figures a demo can use honestly today:** 600,072 tonnes of broiler output
in 2024, and Lakhish as the largest regional council at 72,354 tonnes. Both are
CBS-measured, dated, and provisional where CBS says provisional.

**One cross-check fails and must travel with either figure.** The districts sum
to 571,500 tonnes against 600,072 tonnes of output — a gap of 4.76%. Marketing
excludes self-consumption and private sale by CBS's own footnote, so the gap is
probably real; but a reader who adds up the districts will find it, and finding
it unannounced reads as our error. A test asserts the gap is still there and
that the citation still explains it.

**Sources in order of preference:**

1. **Israel Central Bureau of Statistics (CBS)** — `cbs.gov.il`, has an
   English interface and a statistical abstract with an agriculture chapter.
   This is the equivalent of NASS and should be the primary. Check whether
   it offers an API or only PDF/XLSX.
2. **FAOSTAT** — `fao.org/faostat`, free bulk download and API, covers every
   country on consistent definitions. Best for *comparability* with the US
   even where CBS is better for Israel alone. Domain: `QCL` (Crops and
   livestock products), items "Meat of chickens, fresh or chilled".
3. **Israeli Poultry Board / מועצת הלול** — industry body, likely the
   equivalent of the National Chicken Council. Expect Hebrew-only.
4. **USDA FAS GAIN reports** — US attaché reports on Israeli agriculture,
   in English, often with good structural commentary.

### Access findings — first pass, superseded in part

**Read `docs/research/library/poultry-israel.yaml` first.** It is the machine-
readable version of this section and it is more current: it records the route
that actually worked, per-file coverage, and what each file explicitly cannot
answer. The table below is kept because a dead source costs the next attempt the
same hour it cost this one.

The one correction that matters: the CBS *series* API works but is **the wrong
database** — 400 series sampled across the id space returned foreign trade,
industry, prices and population, and no agriculture at all. Agriculture exists
only in the Statistical Abstract, on the **Hebrew** web, in chapter 21 (not 19),
and the English path returns a 200 soft-404 of exactly 2,056 bytes so a wrong
guess looks like a working URL.



All four were tried in the order above. Recorded because a dead source costs
the next attempt the same hour it cost this one, and because
`docs/research/SOURCE-LIBRARY.md` is right that coverage, not existence, is
what a source entry is worth.

| Source | Result |
|---|---|
| **CBS series API** | **Works, and is the way in.** `GET https://apis.cbs.gov.il/series/data/list?id=<N>&format=json` returns real series JSON, and `https://api.cbs.gov.il/index/data/price?id=120010` returns CPI. Answers the open question above: there *is* an API, not just PDF/XLSX. |
| CBS catalog endpoints | Not navigable. `/series/catalog/{tree,maintopic,level}` return HTML error pages, so series IDs cannot be discovered from the API itself. **This is the one blocker left** — find the poultry series IDs via the web UI, then the data endpoint serves them. |
| CBS abstract chapter pages | JS-rendered. The agriculture chapter returns HTTP 200 and ~37 KB with **zero** occurrences of "poultry" — a shell, not content. Do not list these URLs in a batch; COOPER would fetch the shell and return empty. |
| FAOSTAT | Closed off three ways. API returns `Missing Authorization Header`; `bulks-faostat.fao.org` returns **403**; `fenixservices.fao.org` returns **521**. The plan's assumption of "free bulk download and API" no longer holds. |
| OECD-FAO Outlook 2025-2034 | Statistical annex PDF downloads fine (2 MB) but uses a **custom font encoding**: table text extracts as shifted gibberish (`7DEOH&:RUOG...` for "Table C. World..."). Not machine-readable, and a keyword search for "Israel" on the extracted text proves nothing. The HTML full-report chapter returns **403**. |
| USDA FAS GAIN | **No Israel poultry report exists.** Israel gets Grain and Feed / Exporter Guide reports, where poultry appears only as feed demand. The 2026 Grain and Feed Annual PDF returns **403** from `fas.usda.gov` anyway. |

**And the citation the headline rests on is gone.** The 58.2 kg figure at the
top of this document traces to a Euromeatnews article which now returns
**404**. WATTAgNet's per-capita ranking piece returns 403. So the "Israel is
#1" claim currently has *no reachable source at all*, which settles the
question of whether to lead the demo with it: not until it is re-sourced from
a series, not a headline.

---

## Priority 2 — What makes the demo land

- **Kosher slaughter (shechita).** This is the single most interesting
  modelling question Israel raises, and it is not cosmetic — it plausibly
  changes the loss chain in ways the US model does not capture:
  - Shechita requires a specific cut by a trained *shochet*; birds are not
    stunned in the way US plants stun them. Our `transport_doa` and
    `wing_damage` stages assume electrical waterbath or CAS stunning.
  - Post-slaughter inspection (*bedikah*) rejects birds for defects that
    FSIS would pass. That is an **additional loss stage with no US
    analogue**, and it should raise the birds-required number.
  - Salting and soaking (*melichah*) is a mass-loss step, not a count step —
    so by our own rules it must not move the count answer. Good test of
    whether the `applies_to` discipline holds up in a new context.

  **This is the strongest content in the whole Israel plan.** It shows the
  model generalising rather than just swapping numbers.

- **Wings specifically.** Does Israel report wings as a separate cut, the way
  USDA does for cold storage? If so we can run the same analysis. If not, say
  so — an honest gap is fine, a silently missing panel is not.

- **Scale comparison.** Israel ~260M birds/yr against the US 9.58bn is roughly
  **37× smaller**. Per capita it inverts: Israel eats *more* chicken per
  person than Americans do. That inversion is the memorable line.

---

## Framing decision — COMPARISON (settled)

George chose **comparison framing**: Israel shown alongside the US, not
standalone. "A dozen wings in Tel Aviv vs a dozen in Buffalo."

Consequences, and they are the reason the schema work below got done first:

- Every figure is now a *pair*, so unit mismatches become wrong answers
  rather than cosmetic. The US reports pounds, Israel kilograms — a
  comparison that forgets is off by 2.2× and still looks plausible.
- The thinner-data objection is real and should be **pre-empted on the
  page**, not defended when asked. A visible "US: 50 states, 31 sources /
  Israel: national only, N sources" is more credible than a comparison that
  implies parity it does not have.
- Per-capita is the strongest comparison axis, because it *inverts*: the US
  produces ~37× more chicken, Israel eats more of it per person. That
  inversion needs population for both countries, which is why `population`
  is now a column.

## Schema work — DONE, after one correction

Completed 2026-07-29, ahead of any Israeli data, so that adding figures is
data rather than a migration.

**It was not done the first time, and the gap was invisible.** `country_id`
went onto all five tables; the UNIQUE keys were left alone. Every one of them
still keyed on `(species_id, year)` or `(species_id, region, …)`, so an
Israeli broiler row for a year the US already had was rejected by the
database. The dimension existed and each table could hold exactly one
country. Fixed by putting `country_id` in all five keys.

Worth knowing *why* the seven guard tests passed anyway: they all read, and a
read-only assertion over a single-country corpus cannot detect a key that
admits only one country — `test_israel_is_stubbed_with_no_data` even asserts
the absence of the rows that would have exposed it. The suite now includes the
insert it was missing.

- New `country` table: `iso3`, `name`, `native_mass_unit`, `native_currency`,
  `population`, `population_year`. USA and an ISR stub are seeded.
- `country_id NOT NULL` added to all five country-scoped observation tables:
  `slaughter_stat_year`, `husbandry_stat_year`, `regional_size_stat`,
  `regional_production_year`, `regional_census_stat`.
- `population` is deliberately **NULL** for both countries. It is a statistic,
  it is the denominator of every per-capita claim, and it needs a citation
  like everything else. Filling it is a research task, not a schema task.
- Guarded by `tests/test_country.py` (7 tests), which discovers country-scoped
  tables from the schema rather than a hand-kept list, and asserts that a
  national total still agrees with a country-filtered one — the exact query
  that silently breaks the day Israeli rows land.

Still open:

- `species`/`product` need no change: Israeli broilers are the same species
  and a wing is still a wing.
- The loss chain **does** need a way to vary by country, since the shechita
  stages have no US equivalent. `loss_factor` already carries an optional
  `region` column — decide whether that suffices or whether `loss_stage`
  itself needs country scoping. Do this when the kosher research lands, not
  before; the shape of the answer should follow the data.
- `slaughter_stat_year` bakes units into its column names
  (`live_weight_lb`, `certified_rtc_lb`, `avg_live_weight_lb`). Fine while
  the loader converts on the way in, but revisit if Israeli reporting does
  not map cleanly onto those fields.

---

## What "done" looks like for the demo

1. [ ] Per-capita consumption claim is verified, dated, and defensible —
   including if the honest answer is that Israel is no longer first.
   **Blocked, not forgotten:** the only citation 404s, so population stays NULL
   and `/api/countries` reports `per_capita: false` rather than rendering a
   claim we cannot back.
2. [x] Israel broiler **production** loaded from CBS, cited, passing the audit —
   plus a head count and a derived bird weight at `industry` grade. A
   *government* head count is still wanted and is batch-05 items 1-2.
3. [x] A country selector — built as a **comparison panel, not a dropdown**.
   The Countries view opens with what each country can actually answer, so a
   reader sees that the US bird count is `measured` and Israel's is `industry`
   before seeing either number. Israel then renders twice, on a toggle: with
   the industry head count, and government-only, where the bird count and the
   derived weight both read "unknown" and the page names the row it dropped.
   Switching the *calculator's* country was rejected: with no government head
   figure it would have had to hide the count answer or compute it from US
   assumptions.
4. [!] At least one Israel-specific loss stage (kosher inspection). **Blocked
   on evidence, not on effort.** Two kosher certification agencies describe
   bedikah in detail - for poultry it inspects lungs, intestines and tendon
   junctions, and a mashgiach pulls blemished birds off the line - and neither
   publishes a rejection RATE. Certification agencies have no reason to. So the
   stage is described in the learning centre and deliberately not quantified;
   putting a number on it would mean inventing one, in a country where
   essentially all commercial slaughter is kosher and the number would move the
   headline answer. batch-05 item 4 tries the Hebrew sources and says to return
   an absence rather than an estimate.
5. [x] Two or three Israel facts in the learning centre, surprise-ranked. **Six
   shipped**, and the lead one is better than any production statistic: chicken
   wings are on the Yom Ha'atzmaut mangal alongside pargiyot, while falafel and
   shawarma barely feature. The others: pargiyot means "baby chickens" and no
   longer does; the 2023 output dip explained by Newcastle disease and the war;
   NIS 6.5/kg at the farm against ~NIS 20/kg at retail; nobody officially counts
   Israel's chickens; and kosher inspection having no FSIS analogue.

## What to explicitly NOT do

- Do not extend to other countries yet. Israel is the demo; a country
  selector with one foreign option is honest, a half-populated world map is
  not.
- Do not reuse US loss factors for Israel without saying so. Different
  stunning, different inspection, different chain. If a US figure is being
  borrowed as a placeholder it must be graded `estimate` and labelled.
- ~~Do not translate the UI. Out of scope for a demo unless asked.~~
  **Superseded 2026-07-29 — he asked.** The Chicken Scratch note wants EN / FR /
  HE localization, so translation is now a planned milestone (M7 in
  `docs/ROADMAP.md`) rather than out of scope. It is still **not a
  prerequisite for this demo**: ship the Israel data in English first, because
  the figures are what the demo is about and Hebrew brings RTL layout work with
  it. Two things this document should hand to that milestone — Israeli reporting
  is in kilograms where ours is in pounds (a comparison that forgets is off by
  2.2× and still looks plausible), and the Israeli Poultry Board is
  *מועצת הלול* with no English publication to cite instead, so source titles
  are already mixed-language before any UI work starts.

---

## ~~Next question, when the research lands~~ — answered 2026-07-29

The question was whether Israel would have national figures only, leaving the
choropleth without a counterpart and the comparison visibly lopsided.

**It does have subnational data.** CBS table 21.4 breaks broiler marketing down
to districts and regional councils, and it uses suppression markers — `-` and
`. .` — with exactly the meaning NASS's withheld cells have, so the existing
"presence, not volume" rendering applies unchanged rather than needing new
handling. Eight councils are suppressed and are loaded as rows with no value,
never as zeros.

Two caveats the map must carry:

- The measure is **marketed, not produced**, and by CBS's footnote it excludes
  self-consumption and private sale. It is also "by source of product", not by
  place of slaughter — so a district figure is where the birds came from, not
  where they were processed.
- `Outside regional councils` appears once per district in the source, so the
  bare label is not unique. Each is qualified with its district; the figure
  means nothing without knowing which district it sits outside of.

The new open question is smaller and sharper: **is a 47-region Israeli map next
to a 50-state US map an honest comparison when one is districts of marketing and
the other is states of slaughter?** They are not the same measurement. Label
each map with its own measure rather than sharing one legend.
