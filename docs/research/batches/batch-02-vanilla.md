# Batch 02 — vanilla

**Archetype:** `how-many`

**Question in one sentence:** How many vanilla orchid flowers does it take to
make one vanilla bean, and how much green bean makes one kilogram of cured
vanilla?

**Expected confidence ceiling:** `industry`

No NASS equivalent. Expect extension publications, FAO commodity notes, and
trade press.

> **Candidate URLs are not filled in yet.** They are deliberately blank rather
> than plausible-looking. COOPER fetches exactly the URLs listed and does not
> search — so an invented URL means it silently fetches nothing and the batch
> comes back empty for a reason nobody can see. Fill these from a real search
> pass before sending. Batch 01 has real ones and is the pipeline test.

---

## Why this subject

Vanilla stresses the model in two ways wings and saffron do not.

**A 1:1 anatomical constant.** One hand-pollinated flower becomes exactly one
bean. That is the *degenerate* case of the constant that makes a floor a floor —
`units_per_individual = 1`. Worth testing precisely because it is boring: if the
floor machinery misbehaves at 1, it is fragile.

**A large concentration ratio on a continuous product.** Roughly 5–6 kg of green
beans cure down to 1 kg. That is `continuous` yield with a big multiplier, which
nothing in the corpus exercises yet — wings and saffron are both countable at
the point of the floor.

**And a labour step with no biological necessity.** Outside its native range,
vanilla has no natural pollinator, so every flower is pollinated by hand within
a few hours of opening. That is not a loss stage and not a yield rate; it is a
*labour input without which the yield is zero*. The schema has no place for
that today, and finding out whether it needs one is the interesting part.

---

## Items to cover

1. **flowers_per_bean** — expect exactly 1. Test the degenerate constant.
2. **green_to_cured_ratio** — the concentration figure, `applies_to: mass`.
   Watch for kg-green-per-kg-cured versus percent-yield, which invert.
3. **beans_per_kg_cured** — count per kilogram, for the countable view.
4. **hand_pollination_window_hours** — how long a flower is receptive. Not a
   model field yet; record it and let the shape follow the data.
5. **labour_hours_per_kg** — the comparison axis shared with saffron.
6. **curing_duration_days** — months-long, and a contrast with poultry's
   47-day grow-out.

## Watch for

- **Green versus cured, everywhere.** This is vanilla's version of saffron's
  fresh-versus-dried trap and egg's tolerance-versus-rate trap. Every mass
  figure is meaningless without the state named.
- *Vanilla planifolia* versus *tahitensis* — different species, different yields.
  Do not merge them.
- Vanilla **extract** is a different product from a vanilla **bean**. A figure
  about extract does not answer a question about beans.

## What to explicitly NOT do

- Do not treat hand-pollination as a loss stage. Nothing is lost; a flower that
  is not pollinated simply never becomes a bean. If it needs modelling it is a
  new concept, not a reused one.
- Do not borrow saffron's loss chain because both are hand-harvested spices.
  Similar labour profile is not similar biology.

## Acceptance

- [ ] Quotes verbatim in returned documents; no `measured`/`derived`
- [ ] `flowers_per_bean` = 1 with `is_anatomical_constant: 1`
- [ ] Every mass figure names green or cured
- [ ] Concentration recorded as `applies_to: mass` and shown not to move a count
- [ ] Species named on every yield figure

---

## Items

<!--
URLs below were each fetched and confirmed 200 with real content on 2026-07-29
before being written here, per the warning above. A guessed PSU URL
(extension.psu.edu/vanilla) returned 404 during that pass and was discarded
rather than left in looking plausible.

Coverage was checked per source, not assumed. The World Bank guide is strong on
pollination and field yields (43 and 48 keyword hits over 4,433 lines) but
mentions "cured" exactly ONCE, so it cannot answer the curing ratio. The
Package of Practice PDF is short but carries that figure verbatim. Sources are
therefore listed per item by what they actually contain.
-->

### Item 1 — flowers_per_bean

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `units_per_individual_lo/mode/hi`, `is_anatomical_constant` |
| `unit` | flowers per bean |
| `archetype` | `how-many` |

**Question:** How many vanilla flowers produce one vanilla bean?

**Candidate URLs:**

- https://gardeningsolutions.ifas.ufl.edu/plants/edibles/vegetables/vanilla/ — UF/IFAS extension
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11547731/ — Vanilla planifolia pollination, peer-reviewed
- https://documents1.worldbank.org/curated/en/099032424233135653/pdf/P17027419430cf08b18e671563dbd6cce04.pdf — World Bank sustainable vanilla cultivation guide

**Done means:** the figure **1**, with lo = mode = hi = 1 and
`is_anatomical_constant: 1`, plus a quote supporting it.

**Watch for:** this is the degenerate case and the point is that it is boring.
One pollinated flower becomes one bean. If the floor machinery misbehaves at 1
it is fragile, so a clean 1 here is a test result, not a null result. Do NOT
accept a figure about flowers per *vine* or per *inflorescence* — a vine carries
many flowers, and that is a different question.

---

### Item 2 — green_to_cured_ratio

| | |
|---|---|
| `target_table` | `loss_factor` |
| `required_fields` | `survive_lo/mode/hi`, `applies_to`, `confidence` |
| `unit` | kg green per kg cured — **report the direction the source uses** |
| `archetype` | `how-many` |

**Question:** How many kilograms of green vanilla beans produce one kilogram of
cured vanilla beans?

**Candidate URLs:**

- https://www.advancingnortheast.in/wp-content/uploads/2021/10/Vanilla-Cultivation-PP-converted-3.pdf — Package of Practice, Vanilla Cultivation
- https://gardeningsolutions.ifas.ufl.edu/plants/edibles/vegetables/vanilla/ — UF/IFAS extension

**Done means:** a ratio with a verbatim quote. The Package of Practice document
is known to contain this figure, so an empty return on this item means the
retrieval step failed, not that the fact is unavailable — say which.

**Watch for:** the direction inverts and inverting it silently is the whole
risk. "6 kg green per 1 kg cured" and "a 17% yield" are the same fact; "6:1"
with no units attached is ambiguous and must be reported as stated rather than
normalised. Record `applies_to: mass` — curing concentrates mass and does not
change a bean count, so this must be shown NOT to move a count answer.

---

### Item 3 — beans_per_kg_cured

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | beans per kg cured |
| `archetype` | `how-many` |

**Question:** How many cured vanilla beans are in one kilogram?

**Candidate URLs:**

- https://www.advancingnortheast.in/wp-content/uploads/2021/10/Vanilla-Cultivation-PP-converted-3.pdf — Package of Practice, Vanilla Cultivation
- https://documents1.worldbank.org/curated/en/099032424233135653/pdf/P17027419430cf08b18e671563dbd6cce04.pdf — World Bank guide

**Done means:** a count per kilogram with a quote, or an explicit "not found".

**Watch for:** bean count per kg depends on grade and length, so a single number
without a grade is weaker than it looks. If the source gives a range or ties it
to a grade, keep the grade with the figure.

---

### Item 4 — hand_pollination_window_hours

| | |
|---|---|
| `target_table` | `quality_defect` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `notes` |
| `unit` | hours a flower remains receptive |
| `archetype` | `how-many` |

**Question:** For how many hours after opening can a vanilla flower be
successfully pollinated?

**Candidate URLs:**

- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11547731/ — Vanilla planifolia pollination, peer-reviewed
- https://documents1.worldbank.org/curated/en/099032424233135653/pdf/P17027419430cf08b18e671563dbd6cce04.pdf — World Bank guide

**Done means:** a duration in hours with a quote. `target_table` is a
placeholder — there is no field for this yet, which is deliberate. Record it and
let the shape follow the data.

**Watch for:** "the flower lasts one day" is not the same claim as "the flower
is receptive for N hours". Opening duration and receptive window may differ, and
conflating them overstates how forgiving the work is. Report which was said.

---

### Item 5 — labour_hours_per_kg

| | |
|---|---|
| `target_table` | `economic_stat` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | labour hours per kg cured |
| `archetype` | `comparison` |

**Question:** How many hours of labour does one kilogram of cured vanilla
require?

**Candidate URLs:**

- https://documents1.worldbank.org/curated/en/099032424233135653/pdf/P17027419430cf08b18e671563dbd6cce04.pdf — World Bank guide
- https://www.advancingnortheast.in/wp-content/uploads/2021/10/Vanilla-Cultivation-PP-converted-3.pdf — Package of Practice

**Done means:** a figure with a quote, or "not found". Saffron's equivalent item
found nothing in any source, so a null here is a real and expected outcome —
report it plainly rather than reaching for a weaker source.

**Watch for:** this is the shared axis with saffron, so it is only a comparison
if the unit and the basis match. Labour per kg and labour per hectare are not
the same measurement.

---

### Item 6 — curing_duration_days

| | |
|---|---|
| `target_table` | `quality_defect` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | days |
| `archetype` | `how-many` |

**Question:** How many days or months does the vanilla curing process take?

**Candidate URLs:**

- https://www.advancingnortheast.in/wp-content/uploads/2021/10/Vanilla-Cultivation-PP-converted-3.pdf — Package of Practice
- https://gardeningsolutions.ifas.ufl.edu/plants/edibles/vegetables/vanilla/ — UF/IFAS extension

**Done means:** a duration with a quote, converted to days with the original
value kept alongside.

**Watch for:** do not add bean maturation on the vine (about nine months) to the
curing time. They are sequential stages of different kinds, and summing them
answers a question nobody asked.
