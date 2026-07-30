# batch-06-ground-beef — human review record (NEGATIVE RESULT)

Run on COOPER 2026-07-30. **`verify` FAILED; nothing accepted.** 4 items sent,
3 figures returned, 1 rejected by the gate — and of the two that passed, one is
subtly wrong in a way the gate cannot see. Do not promote this batch as it
stands.

## The re-scout worked, and it was worth doing

Applying the batch-08-silk lesson, every URL was re-fetched with **COOPER's own
`fetch_once()`** and checked to contain its figure, rather than trusted from a
browser. That caught a blocker before any model time was spent:
**`fsis.usda.gov` returns HTTP 403 to COOPER, site-wide** — verified against
`/policy/fsis-notice/05-23` plus two PDF paths. The scout renders JavaScript and
follows a browser UA; COOPER does neither.

`cattle_per_production_lot` was therefore excluded rather than left to fail. Two
details of *how* matter, because the obvious way to exclude an item is unsafe:
its heading no longer begins `### Item` (so `parse_spec` skips the block), and
its URL is no longer a bullet. An item that keeps its `**Question:**` but loses
its URLs does not get skipped — it **inherits the previous item's URLs**, which
would have asked a burger article how grinder lots are structured and invited a
verbatim, confident, wrong answer.

## What came back

| Field | Value | Agreement | Verdict |
|---|---|---|---|
| `cattle_per_patty_typical` | 100 | **2/2** | passes, **but see below** |
| `patty_mass_standard` | 112 g | 1/1 | passes, **and is misleading** |
| `provenance_can_it_be_known` | 4 | 1/1 | **rejected — correctly** |
| `beef_per_animal_proxy` | — | — | no figure returned |

### The rejection is the gate at its best

> none of the reported values (4, 4, 4) appear in the quoted sentence

The quote names Nebraska, Texas, Uruguay and a South Dakota trim plant. **Four
is the right answer** — and the model reached it by *counting entities in a
sentence*, which is derivation, not extraction. The digit `4` is nowhere in the
text. The gate refused it for exactly the right reason: `derived` is a claim
about provenance, and only a human may make it. A correct answer, correctly
refused. If it goes into the corpus it goes in graded `derived`, by hand.

### The row to actually worry about: 112 g

`patty_mass_standard` verifies perfectly and means something other than what the
item asked. Its quote:

> To achieve uniform sizing for the broiled and pan-broiled patties, 112 grams
> of ground beef were pressed into each patty mold.

That is the **laboratory's test-patty size from a cooking-yield methods
section** — an internal protocol detail of the USDA ARS study, not a retail or
foodservice standard. The item asked for a market patty weight and named
Wikipedia's quarter-pound (113.4 g, raised to 120.5 g in 2015) as the source.

What makes it dangerous is the near-miss: **112 g sits about one gram from the
real quarter-pound**, so nothing looks wrong. Same shape as the EIB-121
pie-chart label in `08a4cf1` — a real number, from the right document, on the
right subject, stripped of the header that gave it meaning. Both URLs were in
front of the model and it took the methods line over the definition.

### And the one that passed is a ceiling wearing a point value

`cattle_per_patty_typical` stores `lo = mode = hi = 100` from:

> Meat from more than 100 cows **can be used** to make one hamburger.

That is a maximum, and a hedged one. The spec warned about this in as many
words — *"patty vs lot vs 'can be used'... routinely misread as a typical patty
count"* — and predicting it did not prevent it, which is now the second time a
spec's own `Watch for` has failed to stop the thing it named. Storing it as a
typical value with zero spread is the one reading the sentence does not support.

## Conclusion

Three rows, three different failure modes, none of them a pipeline bug: one
correct refusal, one context-stripped near-miss, one ceiling flattened into a
point. The re-scout and the gate both did their jobs. Promote nothing here
without reading each quote against its own document first — and if
`patty_mass_standard` is wanted, take it from the Quarter Pounder definition,
not from a lab's mold.
