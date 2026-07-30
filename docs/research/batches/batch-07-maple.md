# Batch 07 — maple syrup

> **DRAFTED, not runnable yet.** Candidate URLs below are **leads, not yet
> confirmed 200 with the figure present**. Run a URL scout and replace each with
> a fetched-and-confirmed URL before `send`.

**Archetype:** `how-many`

**Question in one sentence:** If you have one bottle of maple syrup, how many
taps (and trees) and how much sap does it represent?

**Expected confidence ceiling:** `industry` for COOPER. Note for the human
reviewer: USDA NASS *does* publish a Maple Syrup report, so several of these
figures are promotable to `measured` on a human pass — but COOPER may not assign
it, and the extension figures below are the honest ceiling for the machine step.

---

## Why this subject

Honest framing: this **mostly adds rows and exercises `recurring` on a new
domain** rather than advancing the model — `continuous` (saffron) and `recurring`
(eggs) already exist. What it genuinely adds is a **two-step ratio** nothing in
the corpus has: a concentration step (sap → syrup) *stacked on* a seasonal rate
(sap per tap per season). Eggs are a rate; saffron is a concentration; maple is
both at once, and it is worth checking the model expresses that without hiding a
step. The season window (~6 weeks, not a year) is also a second, shorter
`recurring` period than eggs used — a good test that the period is data, not a
hardcoded year.

---

## Items

### Item 1 — sap_to_syrup_ratio

| | |
|---|---|
| `target_table` | `loss_factor` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `applies_to: volume`, `confidence` |
| `unit` | gallons sap per gallon syrup |
| `archetype` | `how-many` |

**Question:** How many gallons of sap make one gallon of maple syrup?

**Candidate URLs (unconfirmed leads — scout before send):**

- https://extension.umaine.edu/publications/7036e/ — UMaine Cooperative Extension, tapping & making syrup
- <Cornell / UVM Proctor "Rule of 86" page — confirm>

**Done means:** a ratio with a quote, plus the **sap sugar %** it assumes — the
ratio is meaningless without it (Rule of 86: gal sap ≈ 86 ÷ sugar %).

**Watch for:** a bare "40:1" with no sugar % attached; and volume vs mass.

---

### Item 2 — sap_sugar_content

| | |
|---|---|
| `target_table` | `quality_defect` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | percent sugar in raw sap |
| `archetype` | `how-many` |

**Question:** What is the typical sugar content of raw sugar-maple sap?

**Candidate URLs (unconfirmed leads — scout before send):**

- <UVM Proctor Maple sap-sugar page — confirm>

**Done means:** a percent (typically ~2%, range ~1.5–3) with a quote. This is
the driver behind Item 1's variance.

**Watch for:** sap sugar varies by tree, day, and season — a single point value
is weaker than a range; keep the range if given.

---

### Item 3 — sap_per_tap_per_season

| | |
|---|---|
| `target_table` | `product` (recurring yield) |
| `required_fields` | `value_lo/mode/hi`, `unit`, period = season |
| `unit` | gallons of sap per tap per season |
| `archetype` | `how-many` |

**Question:** How much sap does one tap yield over a full season?

**Candidate URLs (unconfirmed leads — scout before send):**

- https://nysmaple.com/how-much-sap-can-one-tree-produce/ — NY State Maple Producers Association
- https://files.dnr.state.mn.us/destinations/state_parks/maplesyrup_how.pdf — MN DNR

**Done means:** a per-tap seasonal figure (~10 gal, range ~5–15) with a quote,
stored as a `recurring` rate with the **season** as its period — not a year.

**Watch for:** **per tap vs per tree** — a tree may carry several taps; do not
conflate. And season length varies by latitude/year.

---

### Item 4 — taps_per_tree

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | taps per mature tree (by diameter class) |
| `archetype` | `how-many` |

**Question:** How many taps may a mature sugar maple carry?

**Candidate URLs (unconfirmed leads — scout before send):**

- https://extension.umaine.edu/publications/7036e/ — tapping guidelines by diameter

**Done means:** a count tied to trunk diameter (typically 1–3) with a quote.

**Watch for:** modern conservative tapping guidelines are lower than older ones;
keep the year and the diameter class with the number.

---

### Item 5 — season_length

| | |
|---|---|
| `target_table` | `quality_defect` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | days (or weeks) of the tapping season |
| `archetype` | `how-many` |

**Question:** How long is a typical maple tapping season?

**Candidate URLs (unconfirmed leads — scout before send):**

- <UVM / Cornell season-length page — confirm>

**Done means:** a duration with a quote — the period the `recurring` rate is
measured over.

**Watch for:** freeze-thaw dependent; a warming-climate trend is real but is a
different claim than a single typical length.

---

## Conflicts to report, not resolve

| Figure | Source | Year | Definition used |
|---|---|---|---|
| sap:syrup | rule of thumb | — | 40:1 at 2% sugar |
| sap:syrup | Rule of 86 | — | varies 30–50 by sugar % |
| sap/tap | varies | — | per tap vs per tree, region-dependent |

## What to explicitly NOT do

- Do not present 40:1 as fixed — it is a function of sap sugar %, which varies.
- Do not sum sap flow across multiple seasons, or add tree maturation years to
  the season length. Sequential stages of different kinds (the vanilla lesson).
- Do not reuse the egg `recurring` **period** as a year — maple's period is a
  ~6-week season, and treating it as annual overstates per-tap yield ~8×.

## Acceptance

- [ ] Every row carries a verbatim quote in a returned document
- [ ] No row claims `measured`/`derived` (human may promote NASS-backed figures)
- [ ] New sources in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check
- [ ] Every ratio names the sap sugar % it assumes
- [ ] The seasonal `recurring` period is stored as data, not a hardcoded year
