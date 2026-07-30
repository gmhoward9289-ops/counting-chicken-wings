# Batch 06 — ground beef

> **DRAFTED, not runnable yet.** Candidate URLs below are **leads from a
> frontier-model search pass, not yet confirmed 200 with the figure present**.
> Run a URL scout and replace each lead with a fetched-and-confirmed URL before
> `send` — COOPER fetches exactly what is listed and never searches, so an
> unconfirmed URL returns empty for a reason nobody can see (see
> `README.md` and the batch-02 header).

**Archetype:** `how-many`

**Question in one sentence:** If you have one ground-beef patty, how many
different cattle does it represent?

**Expected confidence ceiling:** `industry` — and the mixing/pool figures are
`estimate`. There is no NASS-equivalent enumeration of animals-per-patty; the
strongest public figures are trade-press and a corporate disclosure. Read the
result without borrowing the poultry corpus's credibility.

---

## Why this subject

This is the wing question on a mammal, and it **breaks the assumption harder
than wings do**. For wings the floor is anatomy (two per bird) and mixing pushes
6 → ~12. For a patty there is **no anatomical constant at all**: the count is set
entirely by industrial commingling. Grinding is a more total mixer than
size-grading — it destroys the individual — so the patty is the purest test in
the corpus of the pooling model standing on its own, with the floor (1, a
home-ground single animal) reachable only by hand, exactly like whole-bird wings.

It also forces an honest confrontation with *how little is actually enumerated*:
the famous "100+ cattle" number is a corporate statement, not a survey. If the
subject only added rows it should say so — but it does more, by isolating the
mixing engine from any anatomical floor.

`is_anatomical_constant: 0` for the patty product, and that is the point.

---

## Items

### Item 1 — cattle_per_patty_typical

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence` |
| `unit` | distinct cattle per single retail/foodservice patty |
| `archetype` | `how-many` |

**Question:** How many different cattle contribute meat to a single ground-beef
patty in a commodity supply chain?

**Candidate URLs (unconfirmed leads — scout before send):**

- https://www.foodrepublic.com/1459051/burger-actually-isnt-made-from-single-cow/ — cites McDonald's 2014 statement via *Washington Post*
- https://www.farmprogress.com/cattle-news/how-many-cattle-in-a-ground-beef-patty- — ag trade press; 2017 consumer survey (returned 403 on one pass — find a live mirror)

**Done means:** a count with a verbatim quote and the year, plus whether the
figure describes a *typical* patty or a *maximum* ("can contain"). Name which.

**Watch for:** **patty vs lot vs "can contain".** "Meat from 100+ cattle can be
used" is a ceiling on a production lot, routinely misread as a typical patty.
Keep the distinction the source actually draws.

---

### Item 2 — cattle_per_production_lot

| | |
|---|---|
| `target_table` | `loss_factor` (mixing pool proxy) |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: estimate` |
| `unit` | distinct cattle per grinder production lot |
| `archetype` | `how-many` |

**Question:** How many cattle are represented in a single production lot at a
commercial grinder?

**Candidate URLs (unconfirmed leads — scout before send):**

- <USDA FSIS ground-beef / "N60" lot-sampling guidance — find and confirm>
- <peer-reviewed traceability / recall-lot study — find and confirm>

**Done means:** a lot size (in animals, or in lbs with a trim-per-animal figure
to convert) with a quote, graded `estimate` and labelled as a pool size, not a
patty count.

**Watch for:** lot size given in **pounds**, not animals — needs Item 3 to
convert, and the conversion must be shown, not assumed.

---

### Item 3 — lean_trim_per_animal

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | lbs of grindable lean trim per carcass |
| `archetype` | `how-many` |

**Question:** How much grindable trim does one beef carcass yield?

**Candidate URLs (unconfirmed leads — scout before send):**

- <USDA ERS or land-grant extension beef-cutout / trim-yield table — confirm>

**Done means:** a per-carcass trim mass with a quote, used only to bound
parcels-per-patty — not to claim a count.

**Watch for:** trim destined for grinding vs total carcass weight; imported
lean trim blended in changes the animal pool without changing the mass.

---

### Item 4 — patty_mass_standard

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | grams per patty (note the foodservice count, e.g. 1:4, 1:10) |
| `archetype` | `how-many` |

**Question:** What is a standard ground-beef patty weight (retail quarter-pound
and common foodservice portions)?

**Candidate URLs (unconfirmed leads — scout before send):**

- <foodservice spec / USDA FoodData Central patty entry — confirm>

**Done means:** a mass with the portion convention named.

**Watch for:** raw vs cooked patty weight — cook loss (~20%) changes mass, never
the animal count (the wings cook-loss lesson, reused).

---

### Item 5 — provenance_can_it_be_known

| | |
|---|---|
| `target_table` | `quality_defect` (provenance note) |
| `required_fields` | `value_lo/mode/hi`, `unit`, `notes` |
| `unit` | source establishments / animals named in a documented traceback |
| `archetype` | `how-many` |

**Question:** In a documented ground-beef contamination traceback, how many
source establishments or animals were implicated in a single patty or lot?

**Candidate URLs (unconfirmed leads — scout before send):**

- <NYT 2009 Stephanie Smith E. coli traceback — confirm a live, fetchable copy>
- <USDA FSIS recall notice with lot breadth — confirm>

**Done means:** a count of implicated sources with a quote, framed as evidence
that the pool is real and large — the "does anyone actually know?" element,
like the honey batch's provenance-audit.

**Watch for:** a recall's breadth (all product from a shift) is not the same as
one patty's animal count; report which the source measured.

---

## Conflicts to report, not resolve

| Figure | Source | Year | Definition used |
|---|---|---|---|
| cattle per unit | McDonald's / WaPo | 2014 | "can be used to make one hamburger" (max, corporate) |
| cattle per unit | trade press / survey | 2017 | consumer-facing typical |

Lay the max-vs-typical gap out; do not pick one.

## What to explicitly NOT do

- Do not treat the "100+ cattle" figure as a **typical** patty count. It is a
  maximum from a corporate statement.
- Do not reuse the wing combo-bin / IQF pool sizes as beef pool sizes. A beef
  grinder combo is a different container and a different `k`; grade any borrowed
  number `estimate` and say it was borrowed.
- Do not claim `measured`/`derived`. No agency enumerates animals per patty.

## Acceptance

- [ ] Every row carries a quote verbatim in a returned document
- [ ] No row claims `measured` or `derived`; pool figures are `estimate`
- [ ] New sources in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check
- [ ] max-vs-typical patty figures flagged as a conflict, not averaged
- [ ] `ground_beef_patty` carries `is_anatomical_constant: 0`; floor = 1 (hand)
