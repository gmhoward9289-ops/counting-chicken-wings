# Batch 03 — wagyu

> **Authored 2026-08-15**, following a consult pass plus independent
> re-verification (every URL below was fetched a second time via WebFetch and
> the quoted sentences confirmed present, not just trusted from the first
> pass). It remains the only specced subject that tests quality-as-a-dimension
> — BMS marbling grade, which should reuse the `quality_defect` pattern built
> for woody breast and must not change a count. Worth noting it would also be
> the project's first subject where the individual is a large animal and the
> product is most of it, which inverts the wing ratio rather than extending
> it.

**Archetype:** `comparison`

**Question in one sentence:** How much beef does one wagyu animal yield, and
what does its marbling grade actually measure?

**Expected confidence ceiling:** `industry`

Japanese grading is defined by the **Japan Meat Grading Association**, which is
an authoritative standards body — so a JMGA grade definition is stronger than
most sources in these three batches. But a *yield* figure from trade press is
not, and the two must not inherit each other's credibility.

**No fetchable JMGA primary source exists.** `jmga.or.jp/en/` returns 404, and
the widely-linked English translation of the standard
(`twinwoodcattle.com/.../TWRA120_Japan_Beef_Carcass_Grading_Standard.pdf`) is a
**scanned image with no text layer** — the verbatim-quote gate can never pass
against it. Discarded rather than left in looking authoritative. The practical
ceiling for JMGA-defined terms in this batch is a peer-reviewed review paper's
*description* of the JMGA system (below), not the standard itself.

---

## Why this subject

Wagyu is the one of the three that is **not** about a floor. It is about a
**quality dimension**, and it should reuse machinery already built rather than
adding any.

The `quality_defect` table exists because of woody breast: a condition that
degrades meat without removing product, so it is deliberately **outside** the
loss chain — a woody-breast fillet still sells. Marbling is the same shape with
the sign flipped. **BMS (Beef Marbling Standard) 1–12 is a quality axis that
does not change a count**, exactly as white striping does not.

If `quality_defect` can hold a *desirable* grade as cleanly as it holds a
defect, that validates the abstraction. If it cannot, the table is really a
`quality_axis` and was misnamed — which is worth discovering.

The second thing it stresses: wagyu is `continuous` yield from a single large
individual, where the floor is a fraction far below 1. Boneless wings already
proved the model handles sub-1 floors (0.35 of a chicken), but a steak is a
much larger fraction of a much larger animal.

---

## Items to cover

1. **carcass_yield_pct** — live weight to carcass. The cattle analogue of the
   broiler's measured 75.67% dressing yield, and a direct comparison.
2. **saleable_meat_pct** — carcass to saleable, which is a second and distinct
   step. Do not collapse the two.
3. **bms_scale_definition** — what BMS 1–12 measures, from JMGA if possible.
   `target_table: quality_defect`, with the sign question above resolved.
4. **marbling_vs_yield_tradeoff** — does higher marbling cost saleable yield?
   If so this is the beef version of "is fatter better?", which found that
   heavier broilers give more meat per bird and worse meat quality per pound.
5. **days_on_feed** — wagyu finishing runs far longer than US beef, which is
   itself far longer than a broiler's 47 days. A good scale comparison.
6. **feed_per_kg_beef** — the comparison axis against the broiler's 1.69 FCR.

## Watch for

- **A5 is not a yield grade.** Japanese grades pair a *yield* letter (A/B/C)
  with a *quality* number (1–5), and BMS 1–12 sits inside the quality score.
  "A5" conflates two axes and is routinely misreported as one.
- Japanese wagyu versus American wagyu crossbreeds — different animals,
  different grading systems, frequently blurred in marketing copy.
- Live weight, carcass weight, and saleable weight are three different
  denominators. A percentage without its denominator named is unusable.

## What to explicitly NOT do

- Do not put marbling in the loss chain. It changes quality and price, not
  count — the same rule that keeps cook loss and chilling method out of the
  wing count.
- Do not let a JMGA grade definition lend its credibility to a trade-press
  yield figure in the same document. Grade each row on its own source.
- Do not model a mixing cascade. A single steak comes from a single animal, and
  the pooling question that dominates wings barely applies. Saying so plainly
  is a finding, not a gap.

## Acceptance

- [ ] Quotes verbatim in returned documents; no `measured`/`derived`
- [ ] Every percentage names its denominator (live / carcass / saleable)
- [ ] BMS lands in `quality_defect` **without** entering the loss chain, or the
      spec explains why the table cannot hold a desirable grade
- [ ] Japanese and American wagyu kept as separate rows
- [ ] The marbling-versus-yield question gets a direction, even if the honest
      answer is that the sources disagree

---

## Items

<!--
Every URL below was fetched and its quoted sentence confirmed present via
WebFetch on 2026-08-15, independently of the search pass that first found it.
Coverage was checked per source, not assumed -- see per-item notes for what
each source does and does not carry.

One source carries most of this batch: Gotoh, Nishimura, Kuchida & Mannen
(2018), "The Japanese Wagyu beef industry: current situation and future
prospects -- A review," Asian-Australasian J. Animal Sciences 31(7). Full text
fetched clean from the publisher (animbiosci.org); the PMC mirror
(PMC6039323) returned a reCAPTCHA wall on the day this was written and is
listed only as a backup. Peer-reviewed, but COOPER may not assign `study` --
expect `industry`, a human promotes if warranted.
-->

### Item 1 — carcass_yield_pct (live → carcass)

| | |
|---|---|
| `target_table` | `loss_factor` |
| `required_fields` | `survive_lo/mode/hi`, `applies_to`, `confidence` |
| `unit` | percent of live weight |
| `archetype` | `comparison` |

**Question:** What percentage of a wagyu (Japanese Black) animal's live weight
becomes carcass weight?

**Candidate URLs:**

- https://www.animbiosci.org/journal/view.php?doi=10.5713/ajas.18.0333 — Gotoh
  et al. 2018 review, wagyu-specific: "The mean body and carcass weights of
  Japanese Black cattle at slaughter were 756 kg and 476 kg, respectively, at
  29.2 months of age." (476/756 = 63.0% — **do not write the percentage in as
  a value; the model must report the two weights and let the ratio be a
  separate, clearly-labeled arithmetic step, same as saffron's drying-ratio
  lesson**)
- https://extension.sdstate.edu/how-much-meat-can-you-expect-fed-steer —
  updated 2022-07-13. "for fed beef is usually around 62-64%" — US commodity
  comparison row, not wagyu-specific. Extension source.
- https://extension.msstate.edu/publications/beef-grades-and-carcass-information
  — dated Jan 2024 (POD-01-24). "Dressing percentage is HCW as a percentage of
  the animal's live weight at harvest. It typically ranges from 60 to 64
  percent…averaged 64 percent for the Mississippi Farm to Feedlot program
  cattle from 1993 through 2007."

**Done means:** two rows — a wagyu-specific pair of weights from Gotoh, and a
US-commodity dressing-percentage range from the extension sources — kept
separate, each naming which population it describes.

**Watch for:** the Gotoh figure is two weights, not a percentage. Do not let
the model (or a human) silently divide them into a ratio and report it as
`industry` — that division is a `derived` claim once it becomes a percentage,
exactly the saffron `drying_mass_yield` lesson.

---

### Item 2 — saleable_meat_pct (carcass → retail cuts)

| | |
|---|---|
| `target_table` | `loss_factor` |
| `required_fields` | `survive_lo/mode/hi`, `applies_to`, `confidence` |
| `unit` | percent of carcass weight |
| `archetype` | `comparison` |

**Question:** What percentage of carcass weight becomes saleable retail cuts?

**Candidate URLs:**

- https://extension.sdstate.edu/how-much-meat-can-you-expect-fed-steer —
  "The expected yield of retail cuts from beef carcasses ranges from
  approximately 55% to 75%…" plus a worked example: a 1,200-lb steer at 63%
  dressing yields a 750-lb carcass, of which roughly 65% becomes boneless,
  trimmed beef — about 490 lb.
- https://extension.msstate.edu/publications/beef-grades-and-carcass-information
  — USDA yield-grade cutability definition (YG1 highest yielding cutability,
  YG5 lowest), with a 2007 grade-distribution table.
- https://www.beefresearch.org/resources/product-quality/fact-sheets/beef-grading
  — Beef Checkoff, author Daryl Tatum (Colorado State), dated 2020-10-26.
  Carries a yield-grade table (YG1 "&gt;52.3%" closely trimmed boneless
  retail cuts, by grade band).

**Done means:** a percentage range with its denominator named as carcass
weight, distinct from item 1's live-weight denominator, plus the worked
example if the model can extract it cleanly.

**Watch for:** the beefresearch.org source presents its figure as a table.
Copy the column header alongside the number, or a bare percentage with no
named grade band is unusable — the same trap the vanilla batch hit on
beans-per-kg-cured grades.

---

### Item 3 — bms_scale_definition

| | |
|---|---|
| `target_table` | `quality_defect` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `notes` |
| `unit` | BMS score (1-12 scale) |
| `archetype` | `how-many` |

**Question:** What is the BMS (Beef Marbling Standard) scale, and how does it
map to the JMGA quality grade (1-5)?

**Candidate URLs:**

- https://www.animbiosci.org/journal/view.php?doi=10.5713/ajas.18.0333 —
  "assigns both a yield grade (A, B, or C) and a meat quality grade (1 to 5)"
  and "Graders determine the BMS score (from 1 to 12) by comparing the actual
  carcass marbling with the marbling standard photograph." Both sentences
  confirmed present, plain text — ideal for the quote gate.
- https://www.lonemountaincattle.com/breeding-guide/technical-resources/carcass-grading/
  — commercial wagyu breeder, undated, `industry`/`estimate` ceiling only.
  Plain text (confirmed, not an image): "BMS scores of 8 to 12 are given a 5;
  BMS 5 through 7 are given a 4" and "Currently a BMS 3 grade requires a
  minimum of 21% IMF." Its yield-grade A/B/C percentage cutoffs exist only in
  embedded images on the same page — do not extract those; they cannot clear
  the quote gate. Record `does_not_cover: yield grade cutoffs` for this
  source.
- Backup only, not fetched today (walled): https://pmc.ncbi.nlm.nih.gov/articles/PMC6039323/
  — same Gotoh 2018 paper, in case the animbiosci host is unavailable at run
  time.

**Done means:** the yield/quality/BMS three-axis structure (A/B/C ×
1-5 × 1-12) from Gotoh, plus the BMS→quality-grade band mapping from Lone
Mountain at `industry`/`estimate`, landed in `quality_defect` and explicitly
NOT in any loss-chain table.

**Watch for:** A5 conflates a yield letter and a quality number into one
label — the model must not report "A5" as a single BMS value. If the
`quality_defect` table cannot cleanly hold a desirable (rather than
defective) grade, that is itself the finding the spec's "Why this subject"
section predicted might happen — say so rather than forcing a fit.

---

### Item 4 — marbling_vs_yield_tradeoff

| | |
|---|---|
| `target_table` | `quality_defect` |
| `required_fields` | `notes` |
| `unit` | n/a — qualitative finding |
| `archetype` | `comparison` |

**Question:** Does higher marbling (quality grade) come at the cost of lower
saleable yield?

**Candidate URLs:**

- https://www.beefresearch.org/resources/product-quality/fact-sheets/beef-grading
  — presents quality grade and yield grade as two independent axes with no
  stated tradeoff between them.

**Done means:** honestly, "no source found states a tradeoff; the sources
that discuss both axes treat them as independent" is an acceptable and
expected outcome for this item — write it up as a finding, not a gap. Two
other PDF candidates (Tennessee Extension SP755; Texas A&M
`agrilife.org/animalscience/files/2012/04/beefgrading.pdf`) were tried and
discarded: both appear to be scanned/image-based and returned no extractable
text.

**Watch for:** do not let a model manufacture a tradeoff by reasoning from
general beef-industry knowledge rather than from a document in hand — that is
exactly the fabrication risk `verify` exists to catch. A null or
independent-axes result here is a real answer.

---

### Item 5 — days_on_feed

| | |
|---|---|
| `target_table` | `quality_defect` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | months on feed |
| `archetype` | `how-many` |

**Question:** How long does a wagyu (Japanese Black) animal spend on feed
before slaughter?

**Candidate URLs:**

- https://www.animbiosci.org/journal/view.php?doi=10.5713/ajas.18.0333 —
  "Overall, cattle are fed a high-energy diet twice or three times daily from
  11 months of age until slaughter at 28 to 30 months of age." Also states a
  mean slaughter age of 29.2 months and a mean daily gain of 0.77 kg —
  sufficient alone for this item.

**Done means:** the 28-30 month slaughter-age range (or the 29.2-month mean),
contrasted in the write-up against the broiler's measured 47-day grow-out —
the scale comparison the spec calls for.

**Watch for:** "from 11 months of age" is when high-energy fattening begins,
not birth — do not report 28-30 months as "days on feed" without noting feed
regime starts at 11 months, so days_on_feed (the fattening phase) and total
lifespan-to-slaughter are two different numbers this source can support.

---

### Item 6 — feed_per_kg_beef

| | |
|---|---|
| `target_table` | `economic_stat` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | kg feed (dry matter) per kg live-weight gain |
| `archetype` | `comparison` |

**Question:** How much feed does it take to produce one kilogram of live-weight
gain in a beef steer?

**Candidate URLs:**

- https://www.animbiosci.org/journal/view.php?doi=10.5713/ajas.18.0333 —
  "Total feed consumption during fattening is normally 4,000 to 5,000 kg/head"
  — wagyu-specific total, not a per-kg-gain ratio.
- https://www.beefresearch.ca/topics/optimizing-feedlot-efficiency/ — Beef
  Cattle Research Council (Canadian industry body), last reviewed June 2025.
  "Steer A consumes an average of 21 lbs (9.53 kg) DM per day, which equates
  to a 6:1 feed to gain ratio." US/Canadian commodity comparison row.

**Done means:** the wagyu total-feed figure and the commodity-beef 6:1
feed-to-gain ratio, kept as separate rows with their basis stated (total
feed for the finishing period vs. a daily feed-to-gain ratio).

**Watch for:** the 6:1 ratio is feed-to-*live-weight-gain*, not feed-to-final-
carcass-weight, and it is dry matter. Check this basis against the broiler's
1.69 FCR before putting the two on one axis in the write-up — the
denominators (live gain vs. carcass vs. boneless) differ by the same dressing
chain item 1 and 2 already establish, and mismatching them would repeat the
labour_hours_per_kg trap from vanilla (comparing figures that share a unit
but not a basis).

---

## Tried and discarded

Recorded so the next author doesn't re-spend the same search effort:

- `https://pmc.ncbi.nlm.nih.gov/articles/PMC6039323/` — the Gotoh 2018 paper's
  PMC mirror, walled (reCAPTCHA) on 2026-08-15. Kept as a documented backup
  URL for item 3 only, not a primary candidate.
- `https://extension.okstate.edu/.../custom-beef-processing...` — 403 on
  fetch.
- `https://jmga.or.jp/en/` — 404. No fetchable JMGA primary source exists (see
  note at top of spec).
- `https://www.twinwoodcattle.com/.../TWRA120_Japan_Beef_Carcass_Grading_Standard.pdf`
  — scanned image, no text layer, cannot clear the quote gate.
- Tennessee Extension `SP755` and Texas A&M
  `agrilife.org/animalscience/files/2012/04/beefgrading.pdf` — both appear
  image-based; zero extractable text with the tools used to write this spec.
  Worth a second try with `pdftotext` directly before final discard, since
  extraction quality varies by tool.
- `https://en.wikipedia.org/wiki/Beef_carcass_classification` — fetches fine,
  but contains no Japanese/JMGA section at all despite looking like it should.
  Not useful for this batch.
