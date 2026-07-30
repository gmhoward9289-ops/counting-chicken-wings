# Batch 03 — wagyu

**Archetype:** `comparison`

**Question in one sentence:** How much beef does one wagyu animal yield, and
what does its marbling grade actually measure?

**Expected confidence ceiling:** `industry`

Japanese grading is defined by the **Japan Meat Grading Association**, which is
an authoritative standards body — so a JMGA grade definition is stronger than
most sources in these three batches. But a *yield* figure from trade press is
not, and the two must not inherit each other's credibility.

> **Candidate URLs not filled in.** Same reason as batch 02: COOPER fetches only
> what is listed and does not search, so an invented URL fails silently. Fill
> from a real search pass before sending.

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
