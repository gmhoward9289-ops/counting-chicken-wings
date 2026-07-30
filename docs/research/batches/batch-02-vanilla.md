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
