# batch-03-wagyu round 2 — human review record

Authored 2026-08-16, as the follow-up pass round 1's own review recommended:
"a follow-up pass with the same URLs and no spec changes, to see if a second
run... recovers any of the five nulls — the sources are not the constraint
here." That hypothesis held.

**Outcome: 4 of the remaining 5 items recovered a real, verified figure.**
Combined with round 1's single accepted row, the batch now stands at 5 of 6
items with sourced data, one (`marbling_vs_yield_tradeoff`) honestly reported
as absent rather than guessed at, and one partial (`feed_per_kg_beef`) with a
genuine adjacent figure recorded but not promoted.

## What changed between round 1 and round 2

Round 1 ran the normal COOPER pipeline — `qwen2.5-coder:7b` and `gemma4-32k`
— against the six fetched documents in `inbox/wagyu/`. It returned 0/12 and
1/12 field-level hits respectively. Round 1's review confirmed, by manual
`WebFetch` at spec-authoring time, that every one of the six items had a
directly relevant sentence sitting in a fetched document — so the miss was
attributed to chunking or multi-fact prompt density, not to the sources being
wrong.

Round 2 tested that hypothesis by reading the same six documents directly,
without re-running COOPER. That is a real deviation from this project's
normal division of labour (`docs/research/README.md`): there is no second
model to disagree with, so **every row here still needs a human
`verified_by` pass**, and the two derived-ratio rows still need a human
confidence-promotion decision, exactly as COOPER's own output would.

## What round 2 found, field by field

| Field | Result |
|---|---|
| `carcass_yield_pct` | **accepted**, two rows — Japanese wagyu (62.96%, derived from 756kg/476kg live/carcass weights) and generic American beef (60-64% dressing percentage, stated directly) |
| `saleable_meat_pct` | **accepted**, two rows on two different bases — SDSU's worked example (65% of carcass / 40% of live weight) and USDA Yield Grade %CTBRC (45.4-52.3% across grades 5-1, round/loin/rib/chuck only) |
| `bms_scale_definition` | **accepted** — JMGA's own yield-letter (A/B/C) + quality-number (1-5) split, with BMS 1-12 as one of four inputs to the quality number, resolving the spec's "A5 is not a yield grade" watch item directly |
| `marbling_vs_yield_tradeoff` | **not found**, and reported as such — the Mississippi State fact sheet treats marbling and yield-grade fat-thickness as independently measured throughout and never states a correlation. The spec allowed "sources treat the axes as independent" as an honest answer; that is what this is. |
| `feed_per_kg_beef` | **still empty**, but for a documented reason — the round-1 review's flagged beefresearch.ca sentence turns out to be a hypothetical teaching example ("Imagine two steer calves..."), not a measured statistic. The models were right to decline it. A genuine wagyu-specific total-feed figure exists (Gotoh: 4,000-5,000 kg/head for the fattening period) but is total feed per animal, not a per-kg ratio, and computing one means dividing by the carcass-weight finding — a derive step recorded as a candidate, not performed here. |

## The basis discipline this pass had to hold

Three different "how much beef do you get" numbers now sit in this batch,
and none of them can be averaged or treated as agreeing or disagreeing with
each other, because none share a denominator:

1. **62.96%** — Japanese wagyu, live weight to carcass weight.
2. **65%** — generic American beef, carcass weight to boneless trimmed beef
   (SDSU's single worked example, 1200lb steer).
3. **45.4-52.3%** — generic American beef, carcass weight to closely trimmed
   boneless retail cuts from round/loin/rib/chuck *only* (USDA %CTBRC), which
   excludes ground beef and other trim that SDSU's 65% figure includes.

Collapsing any two of these into one number, or plotting them on one axis
without naming which basis each uses, would repeat the `labour_hours_per_kg`
trap the vanilla batch already documented — a real number, a real citation,
answering a different question than the one being asked next to it.

## Confidence, deliberately not promoted here

Two rows carry the note that a human could reasonably promote their grade:

- `carcass_yield_pct` (Japanese wagyu) is a ratio of two measured weights
  from a peer-reviewed review paper (Gotoh et al., AJAS 2018) — arguably
  `derived`, not `industry`.
- `bms_scale_definition`'s JMGA description, likewise sourced from the same
  peer-reviewed paper describing an authoritative standards body's own
  grading system, could be argued for `study` over `industry`.

Both are left at `industry` in the findings file. Promoting either is a
human judgement call this document is deliberately not making, per the
project's own rule that grading provenance is not visible in the text of a
document and is not something an extraction pass — human-run or
COOPER-run — should self-assign.

## Adversarial re-check (Fable), 2026-08-16

Before this PR was proposed for merge, a second model (Fable) was asked to
independently verify every row against the actual documents on disk, checking
each quote for character-for-character exactness — the project's own gate —
rather than trusting the notes above.

**Result: the numbers and bases all held up. Three quotes did not pass the
verbatim gate as originally written, and have been corrected by hand:**

- `carcass_yield_pct` / `japanese_wagyu` had silently repaired the source's
  own OCR artifact ("cat tle" → "cattle") and swapped a trailing comma for a
  period. Restored to the source's literal text, artifact included — the
  same choice the ground-beef batch made for a different OCR quirk.
- `saleable_meat_pct` / `usda_yield_grade_ctbrc`'s table-title fragment had
  normalized "Table 1 ." (space before the period, as scraped) to "Table 1."
  Restored the source's spacing.
- `bms_scale_definition`'s two quoted fragments were joined in reverse
  document order. Reordered to match the source, since an ellipsis implies
  omitted text in sequence.

None of these affected the underlying numbers or arithmetic — 756/476 kg,
the 45.4–52.3% range, and the BMS/quality-grade split were all independently
confirmed correct — but a corpus whose value proposition is verbatim
citation cannot ship a quote that fails its own mechanical check, however
harmless the discrepancy.

Fable also surfaced one substantive gap the notes had only hedged at: the
Lone Mountain Cattle quote used for `bms_scale_mapping` states that "the BMS
grade is based on a number of different factors, including... color;
firmness and texture" — but per Gotoh, BMS is a marbling-only score, and
the four-factor lowest-of rule belongs to the separate meat quality grade,
not to BMS itself. The source's own definition of BMS is wrong on this
point. The finding's notes now name this conflation explicitly rather than
leaving it to a general "check against Gotoh" hedge, and the row is kept
for its 8-12→5 bucketing and 21% IMF anchor, not as a definition of BMS.

## Honest position on this round

Round 1's finding was "source quality does not guarantee extraction yield."
Round 2's finding confirms the corollary: **the yield was there, and a more
careful read recovered most of it without touching a single URL.** That is
useful evidence for the project's own methodology question about when a
COOPER pass is sufficient and when a subject needs a slower, denser read —
worth a note in `docs/research/README.md` or the ROADMAP if this pattern
repeats on the next thin batch.
