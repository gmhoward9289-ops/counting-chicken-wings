# Batch 07 — maple syrup

> **SCOUTED 2026-07-30.** Every candidate URL below was fetched and confirmed
> 200 with the figure present on this date. Ready to send.

**Archetype:** `how-many`

**Question in one sentence:** If you have one bottle of maple syrup, how many
taps (and trees) and how much sap does it represent?

**Expected confidence ceiling:** `industry` for COOPER. Note for the human
reviewer: USDA NASS *does* publish a Maple Syrup report, and UVM Extension is a
strong land-grant source, so several figures are promotable to `measured` on a
human pass — but COOPER may not assign it.

---

## Why this subject

Honest framing: this **mostly adds rows and exercises `recurring` on a new
domain** rather than advancing the model — `continuous` (saffron) and `recurring`
(eggs) already exist. What it genuinely adds is a **two-step ratio** nothing in
the corpus has: a concentration step (sap → syrup) *stacked on* a seasonal rate
(sap per tap per season). The season window (~6 weeks, not a year) is also a
second, shorter `recurring` period than eggs used — a good test that the period
is data, not a hardcoded year.

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

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.uvm.edu/extension/agriculture/maple/bizmodules/sites/default/files/imce/uploads/1013jonesruleof86.pdf
  — UVM Extension, "Jones Rule of 86". Quote: "an average sap sugar concentration
  of 2°Brix would require 43 gallons of sap to produce 1 gallon of syrup, or a
  sap:syrup ratio of close to 40:1."
- https://nysmaple.com/how-much-sap-can-one-tree-produce/ — NY State Maple
  Producers. Quote: "It takes approximately 40 gallons of sap to produce just one
  delicious gallon of fresh maple syrup."

**Done means:** a ratio with a quote **and the sap sugar % it assumes** (Rule of
86: gal sap ≈ 86 ÷ sugar %).

**Watch for:** a bare "40:1" with no sugar % attached; and volume vs mass.

---

### Item 2 — sap_sugar_content

| | |
|---|---|
| `target_table` | `quality_defect` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | percent / °Brix sugar in raw sap |
| `archetype` | `how-many` |

**Question:** What is the typical sugar content of raw sugar-maple sap, and what
is the Rule of 86?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.uvm.edu/extension/agriculture/maple/bizmodules/sites/default/files/imce/uploads/1013jonesruleof86.pdf
  — UVM Extension. Quotes: "if one divides 86 by the sugar content of sap, you
  can estimate the amount of sap required to produce a gallon of syrup"; average
  "2°Brix".

**Done means:** a percent/°Brix (typically ~2) with a quote — the driver behind
Item 1's variance.

**Watch for:** sap sugar varies by tree, day, and season — keep a range if given;
modern reverse osmosis raises effective concentration and breaks the rule at the
high end (the source says so).

---

### Item 3 — sap_per_tap_per_season

| | |
|---|---|
| `target_table` | `product` (recurring yield) |
| `required_fields` | `value_lo/mode/hi`, `unit`, period = season |
| `unit` | gallons of sap per tap per season |
| `archetype` | `how-many` |

**Question:** How much sap does one tap yield over a full season?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://extension.umaine.edu/publications/7036e/ — UMaine Extension. Quote:
  "The average full season yield for a taphole is from five to 15 gallons of sap.
  However, under favorable conditions, a single taphole can produce as much as 40
  to 60 gallons of sap in a single year."
- https://nysmaple.com/how-much-sap-can-one-tree-produce/ — Quote: "On average, a
  tapped maple will produce 10 to 20 gallons of sap per tap."

**Done means:** a per-tap seasonal figure with a quote, stored as a `recurring`
rate with the **season** as its period — not a year.

**Watch for:** **per tap vs per tree** — a tree may carry several taps. The two
sources bracket ~5–20 gal/tap; keep the range, do not average to a false point.

---

### Item 4 — taps_per_tree

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | taps per mature tree (by diameter class) |
| `archetype` | `how-many` |

**Question:** How many taps may a mature sugar maple carry?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://extension.umaine.edu/publications/7036e/ — Quote: "Trees between 10 and
  18 inches in diameter should have no more than one tap per tree. A second tap
  may be added to trees between 18 and 25 inches in diameter. Only very healthy
  trees over 25 inches in diameter can sustain three taps."
- https://nysmaple.com/how-much-sap-can-one-tree-produce/ — Quote: "Most trees
  today have only one tap; only those with an 80-inch or greater circumference
  generally get two taps."

**Done means:** a count tied to trunk diameter (typically 1–3) with a quote.

**Watch for:** modern conservative guidelines are lower than older ones; keep the
year and diameter class with the number.

---

### Item 5 — season_length

| | |
|---|---|
| `target_table` | `quality_defect` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | weeks/days of the tapping season |
| `archetype` | `how-many` |

**Question:** How long is a typical maple tapping season?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://extension.umaine.edu/publications/7036e/ — Quote: freeze-thaw cycles
  "typically occur from mid-February to early April in Southern Maine and
  mid-March to late April in Northern Maine."

**Done means:** a duration with a quote — the period the `recurring` rate is
measured over (~6 weeks).

**Watch for:** freeze-thaw dependent and latitude-dependent; a single typical
length is weaker than a range. A warming-climate trend is a different claim.

---

## Conflicts to report, not resolve

| Figure | Source | Year | Definition used |
|---|---|---|---|
| sap:syrup | UVM Rule of 86 | 1946/rev. | 43:1 at 2°Brix |
| sap:syrup | NY State Maple | — | "approximately 40 gallons" |
| sap/tap | UMaine | — | 5–15 gal/taphole/season |
| sap/tap | NY State Maple | — | 10–20 gal/tap |

## What to explicitly NOT do

- Do not present 40:1 as fixed — it is 86 ÷ sugar %, and sugar % varies.
- Do not sum sap flow across seasons, or add tree-maturation years to the season
  length. Sequential stages of different kinds (the vanilla lesson).
- Do not reuse the egg `recurring` **period** as a year — maple's period is a
  ~6-week season; treating it as annual overstates per-tap yield ~8×.

## Acceptance

- [ ] Every row carries a verbatim quote in a returned document
- [ ] No row claims `measured`/`derived` (human may promote NASS/UVM figures)
- [ ] New sources in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check
- [ ] Every ratio names the sap sugar % it assumes
- [ ] The seasonal `recurring` period is stored as data, not a hardcoded year
