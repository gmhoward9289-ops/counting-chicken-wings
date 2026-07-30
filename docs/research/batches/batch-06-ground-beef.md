# Batch 06 — ground beef

> **SCOUTED 2026-07-30.** Every candidate URL below was fetched and confirmed
> 200 with the figure present on this date. Ready to send.

**Archetype:** `how-many`

**Question in one sentence:** If you have one ground-beef patty, how many
different cattle does it represent?

**Expected confidence ceiling:** `industry` — and the mixing/pool figures are
`estimate`. There is no NASS-equivalent enumeration of animals-per-patty; the
strongest public figures are trade press, a corporate disclosure, and an FSIS
sampling notice. Read the result without borrowing the poultry corpus's
credibility.

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
the famous "100+ cattle" number is a corporate statement, not a survey. The
strongest hard evidence of the pool is a contamination traceback (Item 5), where
a single patty's trimmings were traced to four separate sources.

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

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.foodrepublic.com/1459051/burger-actually-isnt-made-from-single-cow/
  — trade press; attributes to McDonald's (2014) via *Washington Post*.
  Quote: "meat from more than 100 cows can be used to make one hamburger."

**Done means:** a count with the verbatim quote and the year, plus whether the
figure describes a *typical* patty or a *maximum* ("can be used"). Name which.

**Watch for:** **patty vs lot vs "can be used".** "100+ cows can be used" is a
ceiling, routinely misread as a typical patty count. Keep the distinction the
source draws. This is a secondary source quoting a corporate statement — grade
`industry`, not higher.

---

### Item 2 — cattle_per_production_lot

| | |
|---|---|
| `target_table` | `loss_factor` (mixing pool proxy) |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: estimate` |
| `unit` | container/lot structure of ground beef (pool proxy) |
| `archetype` | `how-many` |

**Question:** How is a lot of beef manufacturing trimmings structured, and does
source material commingle across a lot?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.fsis.usda.gov/policy/fsis-notice/05-23 — FSIS, cloth/N60 sampling
  of beef manufacturing trimmings. Quote: "IPP are to use 1 cloth for up to 5
  containers from the same lot of product." Combo bins are held as a
  "multi-combo lot pending STEC test results."

**Done means:** the lot/combo structure with a verbatim quote, graded
`estimate` as a **pool proxy** — FSIS defines the container, not an animal count.
The animals-per-lot number itself stays `estimate` and is explicitly *not* in
this source.

**Watch for:** do not read a combo-bin or lot definition as an animal count. It
bounds the container, not the herd. No agency enumerates animals per lot.

---

### Item 3 — beef_per_animal_proxy

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | lbs packaged beef per animal (upper-bound proxy for trim) |
| `archetype` | `how-many` |

**Question:** How much packaged beef does one animal yield (to bound
parcels-per-patty)?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://extension.msstate.edu/publications/how-much-meat-expect-beef-animal-farm-direct-beef
  — MSU Extension. Quote: "the take-home weight of packaged beef will be
  approximately 40 percent of the animal's live weight" (~470 lb from a 1,200 lb
  steer).

**Done means:** a per-animal packaged-beef figure with the quote, used only to
bound parcels-per-patty — not to claim a count.

**Watch for:** this is **total packaged beef**, not grinding trim specifically —
an upper bound, and it must be labelled as a proxy. Imported lean trim blended
in changes the animal pool without changing mass.

---

### Item 4 — patty_mass_standard

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | grams per patty (note foodservice count, e.g. 1:4, 1:10) |
| `archetype` | `how-many` |

**Question:** What is a standard ground-beef patty weight (retail quarter-pound
and common foodservice portions)?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://en.wikipedia.org/wiki/Quarter_Pounder — Quote: "a precooked weight of
  approximately one quarter of a pound, originally portioned as four ounces
  (113.4 g) but increased to 4.25 oz (120.5 g) in 2015." A quarter-pound is the
  1:4 foodservice count; grade `industry`.
- https://www.ars.usda.gov/ARSUserFiles/80400525/data/retn/usda_cookingyields_meatpoultry.pdf
  — USDA ARS cooking-yields table. Ground beef patties retain ~63–77% of raw
  weight when cooked (fat content and method dependent) — supports the raw-vs-
  cooked note, and is `industry` for COOPER (a human may grade the USDA table
  higher).

**Done means:** a mass with the portion convention named.

**Watch for:** raw vs cooked patty weight — cook loss (~20%) changes mass, never
the animal count (the wings cook-loss lesson, reused).

---

### Item 5 — provenance_can_it_be_known

| | |
|---|---|
| `target_table` | `quality_defect` (provenance note) |
| `required_fields` | `value_lo/mode/hi`, `unit`, `notes` |
| `unit` | source establishments named in a documented traceback |
| `archetype` | `how-many` |

**Question:** In a documented ground-beef contamination traceback, how many
source establishments were the trimmings in a single patty made from?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://marlerclark.com/media_relations/e.-coli-path-shows-flaws-in-ground-beef-inspection
  — reprint of Michael Moss, *NYT* 2009 (Stephanie Smith case). Quote: "The
  ingredients came from slaughterhouses in Nebraska, Texas and Uruguay, and from
  a South Dakota company that processes fatty trimmings and treats them with
  ammonia to kill bacteria." → **four sources for one patty.**

**Done means:** the count of implicated sources with the quote — the hardest
evidence that the pool is real and large.

**Watch for:** this is one documented patty, not a typical count; frame it as an
existence proof of large pooling, not an average.

---

## Conflicts to report, not resolve

| Figure | Source | Year | Definition used |
|---|---|---|---|
| cattle per unit | McDonald's / WaPo (via Food Republic) | 2014 | "can be used" (max, corporate) |
| sources per patty | Moss / NYT (via Marler Clark) | 2009 | one documented patty, 4 sources |

Lay the max-vs-documented gap out; do not pick one.

## What to explicitly NOT do

- Do not treat the "100+ cattle" figure as a **typical** patty count. It is a
  maximum from a corporate statement.
- Do not treat the FSIS lot/combo definition as an animal count.
- Do not reuse the wing combo-bin / IQF pool sizes as beef pool sizes. Grade any
  borrowed number `estimate` and say it was borrowed.
- Do not claim `measured`/`derived`. No agency enumerates animals per patty.

## Acceptance

- [ ] Every sent row carries a quote verbatim in a returned document
- [ ] No row claims `measured` or `derived`; pool figures are `estimate`
- [x] Item 4 patty-mass URLs confirmed (Wikipedia Quarter Pounder; USDA cooking yields)
- [ ] New sources in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check
- [ ] `ground_beef_patty` carries `is_anatomical_constant: 0`; floor = 1 (hand)
