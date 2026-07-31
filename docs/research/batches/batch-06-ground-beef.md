# Batch 06 — ground beef

> **SECOND ATTEMPT, 2026-07-31.** The first run passed `scout`, reached COOPER,
> and then failed `verify` with nothing accepted — see
> `docs/research/accepted/batch-06-ground-beef-REVIEW.md` for the full record.
> Three rows, three different failure modes, none of them a pipeline bug:
>
> 1. `provenance_can_it_be_known` asked a question whose answer had to be
>    *counted out of a sentence*. The model counted correctly and the gate
>    rejected it correctly, because counting is derivation and `4` appears
>    nowhere in the text. **That item is gone from this spec.** A question that
>    can only be answered by enumerating entities is not an extraction question
>    and must not be sent.
> 2. `patty_mass_standard` returned 112 g — a **laboratory patty-mould size**
>    from the methods section of the USDA ARS cooking-yields PDF, about one gram
>    from the real quarter-pound and therefore invisible to review. Both URLs
>    were in front of the model and it took the methods line over the
>    definition. **The ARS PDF is removed from this spec entirely**, because
>    `runner.run()` pools chunks across every document in the batch: leaving a
>    document in the batch leaves its sentences reachable by every item,
>    whichever item cited it.
> 3. `cattle_per_patty_typical` flattened "more than 100 cows **can be used**"
>    into `100/100/100`. The `Watch for` named that exact trap and did not stop
>    it. It is now handled by **renaming the field to what the sentence
>    actually supports** — a maximum — rather than by warning harder. A field
>    name travels with the row into the corpus; a warning does not.
>
> **Re-scouted 2026-07-31** with `runner.fetch_once()`, the same code that does
> the real fetch. Every URL below was re-fetched and checked to contain its
> quote.

**Archetype:** `how-many`

**Question in one sentence:** If you have one ground-beef patty, how many
different cattle does it represent?

**Expected confidence ceiling:** `industry` — and the mixing/pool figures are
`estimate`. There is no NASS-equivalent enumeration of animals-per-patty; the
strongest public figures are trade press, a corporate disclosure, and an
extension bulletin. Read the result without borrowing the poultry corpus's
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
the famous "100+ cattle" number is a corporate statement, not a survey, and it
is a **ceiling**. Nobody publishes animals-per-lot.

`is_anatomical_constant: 0` for the patty product, and that is the point.

---

## Items

### Item 1 — cattle_per_patty_max

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence` |
| `unit` | cattle per hamburger, maximum claimed |
| `archetype` | `how-many` |

**Question:** What is the largest number of cattle the source says *can* be
used to make one hamburger?

**Candidate URLs (re-fetched with `fetch_once` 2026-07-31):**

- https://www.foodrepublic.com/1459051/burger-actually-isnt-made-from-single-cow/
  — trade press; attributes to McDonald's (2014) via *Washington Post*.
  Quote: "meat from more than 100 cows can be used to make one hamburger."

**Done means:** the maximum, with the verbatim quote. The field is named
`_max` because the sentence supports a ceiling and nothing else.

**Watch for:** this is a CEILING, not a typical patty count. The sentence says
"can be used", which is a hedge on a maximum. Do NOT report it as a typical or
average value, and do NOT set value_lo to it — a lo is a claim that no patty has
fewer, and the source says no such thing. If you must give a band, value_hi is
the only bound this sentence licenses; leave value_lo null. Grade `industry`:
this is trade press quoting a corporate statement.

---

### Item 2 — patty_mass_standard

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | grams per patty |
| `archetype` | `how-many` |

**Question:** What is the precooked weight in grams of a standard quarter-pound
hamburger patty?

**Candidate URLs (re-fetched with `fetch_once` 2026-07-31):**

- https://en.wikipedia.org/wiki/Quarter_Pounder — Quote: "a precooked weight of
  approximately one quarter of a pound, originally portioned as four ounces
  (113.4 g) but increased to 4.25 oz (120.5 g) in 2015."

**Done means:** a mass in grams with the portion convention named (a
quarter-pound is the 1:4 foodservice count). Both bounds must be numbers the
sentence states.

**Watch for:** the previous run returned **112 g**, which is a laboratory
patty-mould size from a cooking-yields methods section — a real number, from a
real USDA document, answering a different question, and only one gram from the
right answer. That document is no longer in this batch. Take the mass from the
definition of the product, not from anybody's experimental protocol, and never
from a sentence about pressing meat into a mould. Raw vs cooked also matters:
cook loss changes mass and never changes the animal count. Grade `industry`.

---

### Item 3 — dressing_percentage

| | |
|---|---|
| `target_table` | `loss_factor` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | percent of live weight remaining as hot carcass |
| `archetype` | `how-many` |

**Question:** What is the average dressing percentage of beef cattle?

**Candidate URLs (re-fetched with `fetch_once` 2026-07-31):**

- https://extension.msstate.edu/publications/how-much-meat-expect-beef-animal-farm-direct-beef
  — MSU Extension. Quote: "The average dressing percentage of beef cattle is 60
  to 64 percent."

**Done means:** both bounds, each stated in the sentence, with the quote.

**Watch for:** dressing percentage is **hot carcass over live weight**. It is
not the take-home yield and it is not a ground-beef yield — a great deal more is
lost after it. Do not confuse it with the take-home fraction in Item 4, which
comes off the same page and is a smaller number for a reason.

---

### Item 4 — packaged_beef_fraction_of_live_weight

| | |
|---|---|
| `target_table` | `loss_factor` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | percent of live weight taken home as packaged beef |
| `archetype` | `how-many` |

**Question:** What percentage of a beef animal's live weight is taken home as
packaged beef?

**Candidate URLs (re-fetched with `fetch_once` 2026-07-31):**

- https://extension.msstate.edu/publications/how-much-meat-expect-beef-animal-farm-direct-beef
  — MSU Extension. Quote: "A general rule of thumb is that the take-home weight
  of packaged beef will be approximately 40 percent of the animal's live
  weight, or 75 percent of the hot carcass weight."

**Done means:** the percentage, with the quote, and the basis named (live
weight).

**Watch for:** report the figure **as a percentage**, which is what the sentence
gives. Do NOT convert it into pounds: multiplying 40 percent by an example
steer's live weight is *our* arithmetic on a rule of thumb, which is a `derived`
claim and human-only. This is also **total packaged beef, not grinding trim** —
an upper bound on how much of one animal could turn into patties, and it must be
labelled a proxy. Grade `industry`; the source itself says "rule of thumb".

---

### Item 5 — animals_per_grind_batch

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence` |
| `unit` | distinct animals per commercial grind batch |
| `archetype` | `how-many` |

**Question:** How many animals were estimated to be present in the six
commercial grind batches that were measured?

**Candidate URLs (re-fetched with `fetch_once` 2026-07-31):**

- https://pmc.ncbi.nlm.nih.gov/articles/PMC3316629/ — Hu et al., *PLoS ONE*
  7(3):e34191, 2012. DNA-marker mark-recapture estimate of distinct animals in
  commercial grind batches. Quote: "An average of 411 to1367 animals was present
  in the six grind batches."

**Done means:** both bounds, each stated in the sentence, with the quote. The
missing space in "411 to1367" is how the document reads — quote it as it is.

**Watch for:** this is a **grind batch**, not a patty and not a combo bin. A
batch is compounded from several bins of trim, so this number is larger than a
per-bin count and much larger than any per-patty count, and it must not be
relabelled as either. It is also **one manufacturer, one production line, one
shift** — six batches, not a national figure. Report the range, never a single
average across the six. Do not claim `study` or `measured`; grade `industry` and
let a human decide whether the paper earns more.

---

### Item 6 — combo_bins_per_grinder_load

| | |
|---|---|
| `target_table` | `loss_factor` (mixing pool proxy) |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | combo bins of trim per grinder load |
| `archetype` | `how-many` |

**Question:** How many combo bins of trim make up a grinder load?

**Candidate URLs (re-fetched with `fetch_once` 2026-07-31):**

- https://www.ncbi.nlm.nih.gov/books/NBK221105/ — National Research Council /
  Institute of Medicine, *Escherichia coli O157:H7 in Ground Beef: Review of a
  Draft Risk Assessment*, National Academies Press, 2002. Quote: "Grinder loads
  are presumed to vary in size from the equivalent of 2 to 15 combo bins of
  trim."

**Done means:** both bounds with the quote, and the word "presumed" carried into
the notes.

**Watch for:** this bounds the **container**, not the herd — it counts bins, not
animals, and converting bins to animals is arithmetic a human does, not you. The
source says "presumed", which means it is a modelling assumption in a risk
assessment rather than an observation; grade `estimate`, not `industry`.

---

### Item 7 — combo_bin_mass

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | pounds of trim per combo bin |
| `archetype` | `how-many` |

**Question:** How many pounds of trim does one combo bin hold?

**Candidate URLs (re-fetched with `fetch_once` 2026-07-31):**

- https://www.ncbi.nlm.nih.gov/books/NBK221105/ — as Item 6. Quote: "Trim is
  removed from each carcass and combined into 2,000-pound combo bins during the
  slaughter process."

**Done means:** the mass in pounds with the quote.

**Watch for:** this is the bin, not the batch and not the animal. Trim from many
carcasses goes into one bin *and* one carcass's trim can be split across several
bins depending on fat sorting — so a bin mass tells you nothing about a head
count on its own.

---

### Item 8 — truckloads_per_lot

| | |
|---|---|
| `target_table` | `loss_factor` (mixing pool proxy) |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | truckloads of cattle per lot |
| `archetype` | `how-many` |

**Question:** How many truckloads of cattle may a single lot take?

**Candidate URLs (re-fetched with `fetch_once` 2026-07-31):**

- https://www.ncbi.nlm.nih.gov/books/NBK221092/ — same NRC 2002 volume,
  Slaughter Module chapter. Quote: "Lot is defined in the draft as the number of
  cattle necessary to fill one combo bin with trim; and a single lot may take one
  or more truckloads of cattle."

**Done means:** the number of truckloads with the quote, and the definition of a
lot stated in the notes.

**Watch for:** the sentence gives a **floor and no ceiling** — "one or more". Set
value_lo only; leave value_hi null rather than inventing an upper bound. This is
the item that replaces the FSIS notice the pipeline cannot fetch, and it is a
*definition of a container*, not an animal count. Do not multiply it by anything.

---

### Item 9 — ground_beef_lbs_per_steer

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | pounds of lean trim packaged as ground beef, per fed steer |
| `archetype` | `how-many` |

**Question:** How many pounds of lean trim from one fed steer are likely to be
packaged as ground beef?

**Candidate URLs (re-fetched with `fetch_once` 2026-07-31):**

- https://extension.sdstate.edu/how-much-meat-can-you-expect-fed-steer — SDSU
  Extension, updated 2022. Quote: "This 150 -185 pounds of lean trim would likely
  be packaged as ground beef."

**Done means:** both bounds with the quote, and the example animal named (a
1,200-pound fed steer with a 63 percent dressing percent).

**Watch for:** the document writes it as **"150 -185"**, with a space before the
dash. That is the text; quote it exactly as it appears rather than tidying it,
or the gate will reject a true quote. This is **lean trim specifically**, which
is the ground-beef stream — it is a smaller and more relevant number than the
total packaged beef in Item 4, and the two must not be merged. It is also one
worked example, not a survey: grade `industry`.

---

## Conflicts to report, not resolve

| Figure | Source | Year | Definition used |
|---|---|---|---|
| cattle per hamburger | McDonald's / WaPo (via Food Republic) | 2014 | "can be used" (max, corporate) |
| animals per grind batch | Hu et al., PLoS ONE (via PMC) | 2012 | measured, 6 batches, one plant |
| yield fraction | MSU Extension | — | dressing % (60–64) vs take-home % (40) |

Lay the gap out; do not pick one. The two MSU figures are not in conflict — they
measure different points in the same chain — and saying so is part of the job.
The corporate "100+ per hamburger" and the measured "411–1,367 per grind batch"
are **not the same quantity** and neither refutes the other: one is a hamburger,
one is a batch. Say that; do not reconcile them.

## What to explicitly NOT do

- Do not treat the "100+ cattle" figure as a **typical** patty count. It is a
  maximum from a corporate statement, and the field is named `_max` for that
  reason.
- Do not answer any question by counting things named in a sentence. If the
  number is not written in the text, there is no number.
- Do not reuse the wing combo-bin / IQF pool sizes as beef pool sizes. Grade any
  borrowed number `estimate` and say it was borrowed.
- Do not claim `measured`/`derived`. No agency enumerates animals per patty.

## Acceptance

- [ ] Every sent row carries a quote verbatim in a returned document
- [ ] No row claims `measured` or `derived`; pool figures are `estimate`
- [ ] `cattle_per_patty_max` is stored as a ceiling, not a point value
- [ ] `patty_mass_standard` comes from the product definition, not a lab protocol
- [ ] the grind-batch count is never relabelled as a per-patty or per-bin count
- [ ] New sources in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check
- [ ] `ground_beef_patty` carries `is_anatomical_constant: 0`; floor = 1 (hand)

---

## Excluded — the FSIS notice itself (superseded by Items 6–8)

> The lot/commingling question is **no longer blocked**. Items 6, 7 and 8 reach
> it through the National Academies' 2002 review of the FSIS draft risk
> assessment, which quotes the lot definition directly and sits on NCBI
> Bookshelf — a host `fetch_once()` handles fine. The FSIS notice below stays
> excluded because the host, not the content, is what the pipeline cannot reach.
>
> **This heading deliberately does not begin `### Item`**, so `parse_spec` skips
> the whole block, and the URLs below are deliberately **not** bullets. Both
> matter: an item that keeps its `**Question:**` but loses its URLs does not get
> skipped — it **inherits the previous item's URLs**, which would send a
> question about grinder lot structure to a burger article and invite a
> verbatim, confident, wrong answer.
>
> **`fsis.usda.gov` returns HTTP 403 to `fetch_once()`, site-wide.** Verified
> 2026-07-30 against `/policy/fsis-notice/05-23` and two PDF paths; re-confirmed
> 2026-07-31. A browser fetches them fine, which is exactly the batch-08-silk
> trap: a source can be real, correct and cited, and still be invisible to the
> pipeline.
>
> Blocked URL: https://www.fsis.usda.gov/policy/fsis-notice/05-23
> (N60 sampling of beef manufacturing trimmings: "IPP are to use 1 cloth for up
> to 5 containers from the same lot of product"; combo bins held as a
> "multi-combo lot pending STEC test results".)

**What would revive this item:** a lot/combo definition, or an animals-per-lot
figure, on a host `fetch_once()` can reach. eCFR fetches fine but §325.1 carries
none of the relevant terms.

## Excluded — provenance_can_it_be_known (question invited counting)

> Also deliberately not an `### Item`, and its URL deliberately not a bullet.
>
> The first run asked how many source establishments the trimmings in one
> documented patty came from. The answer is four, and the quote names Nebraska,
> Texas, Uruguay and a South Dakota trim plant — but the digit `4` appears
> nowhere in the text. The model reached it by counting entities in a sentence,
> which is derivation, and `verify` rejected it: *"none of the reported values
> (4, 4, 4) appear in the quoted sentence"*. A correct answer, correctly
> refused.
>
> This is not a source problem and re-asking it with a better warning will not
> help. **A question whose answer must be counted out of prose cannot be an
> extraction item.** If the traceback belongs in the corpus, a human puts it
> there graded `derived`, by hand, citing the article.
>
> Source, for a human: https://marlerclark.com/media_relations/e.-coli-path-shows-flaws-in-ground-beef-inspection
> (reprint of Michael Moss, *NYT* 2009, the Stephanie Smith case).
