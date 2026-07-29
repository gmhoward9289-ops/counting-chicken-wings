# Israel data — research plan

**Why this jumped the queue:** the platform is being demoed to people in
Israel. The roadmap put international work after v1.0; this supersedes that
for Israel specifically. Everything else international stays post-1.0.

**Status:** plan only. No Israel data has been added yet. The two figures
quoted below are from a first search pass and are **not yet verified or
loaded** — they are here to show what the shape of the answer looks like,
and one of them already has a conflict that needs resolving.

This document is written to be handed to a research agent. Each item states
the exact question, where to look, and what "done" means.

---

## The headline the demo should lead with

Israel is, or has recently been, **the highest per-capita chicken consumer in
the world**. That is a genuinely strong hook for an Israeli audience and it
is the first thing to nail down.

**But there is already a conflict in the sources, and it must be resolved
before anything ships:**

| Figure | Source | Year |
|---|---|---|
| 58.2 kg/person | OECD-FAO Agricultural Outlook, via trade press | unclear |
| 57.7 kg/person | trade press, "ranked first in the world" | unclear |
| Kuwait 65.43 kg — *ahead of Israel* | separate trade-press dataset | 2023 |

So "Israel is #1" may be **out of date**. Resolve before the demo — claiming
a #1 that a guest can disprove on their phone is worse than claiming an
honest #2. The likely cause is definition drift: *poultry meat* vs *chicken
meat*, carcass weight vs retail weight, and different years.

**Done means:** one primary series (OECD-FAO or FAOSTAT), one definition
stated explicitly, the year named, and Israel's rank as of that year — even
if the answer is "second".

---

## Priority 1 — Core production figures

Everything here is what the model actually needs to answer the wing question
for Israel rather than just decorate a slide.

| Field | Why the model needs it | Likely source |
|---|---|---|
| Broilers slaughtered per year (head) | The denominator for everything | Israel CBS; FAOSTAT `Producing Animals/Slaughtered` |
| Average live weight (kg) | Drives wing size, mirrors our US state data | CBS; Israeli Poultry Board |
| Total chicken meat production (tonnes) | Cross-check against head × weight | FAOSTAT `Production` |
| Per-capita consumption (kg) | The headline | OECD-FAO Outlook |
| Self-sufficiency / import share | Israel is reported as a **net surplus** producer, which is unusual and interesting | CBS trade data; FAS GAIN reports |

An unverified first-pass figure of **~260 million broilers/year** and an
industry turnover of **NIS 10 billion** appeared in trade press. Treat as a
lead, not a fact, until it comes from CBS or FAOSTAT.

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

## Schema work — DONE

Completed 2026-07-29, ahead of any Israeli data, so that adding figures is
data rather than a migration.

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

1. Per-capita consumption claim is verified, dated, and defensible — including
   if the honest answer is that Israel is no longer first.
2. Israel broiler head, live weight, and production loaded from CBS or
   FAOSTAT, cited like everything else, and passing the audit.
3. A country selector that switches the calculator between US and Israel.
4. At least one Israel-specific loss stage (kosher inspection) with an honest
   confidence grade — `estimate` is fine if that is the truth.
5. Two or three Israel facts in the learning centre, surprise-ranked.

## What to explicitly NOT do

- Do not extend to other countries yet. Israel is the demo; a country
  selector with one foreign option is honest, a half-populated world map is
  not.
- Do not reuse US loss factors for Israel without saying so. Different
  stunning, different inspection, different chain. If a US figure is being
  borrowed as a placeholder it must be graded `estimate` and labelled.
- Do not translate the UI. Out of scope for a demo unless asked.

---

## Next question, when the research lands

How thin is too thin? If Israel ends up with national figures only and no
subnational breakdown, the state choropleth has no Israeli counterpart and
the comparison is lopsided in a visible way. Options are a national-level
comparison that simply omits the map, or districts if CBS publishes them.
Worth deciding once we know what CBS actually has, not before.
