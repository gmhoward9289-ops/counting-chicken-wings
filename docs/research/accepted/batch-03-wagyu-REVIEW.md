# batch-03-wagyu — human review record

Authored 2026-08-15 from a consult pass plus independent re-verification —
every candidate URL was fetched a second time before being written into the
spec, and all six resolved with real content. This file is the durable
record of what was accepted, what was rejected, and why, because
`docs/research/outbox/` and `inbox/` are gitignored and the reasoning would
otherwise be lost with them.

**Outcome: 1 figure returned, 1 accepted, 5 items found nothing.** Live in
neither `data/` yet — see the same follow-up note as batch-02-vanilla. This
is the thinnest extraction of the three batches run this pass, and it is
worth stating plainly rather than dressing up: **six well-sourced items, one
figure survived.**

## What COOPER returned, and what happened to it

| Field | Value | Verdict |
|---|---|---|
| `days_on_feed` | 30 months | **accepted** at `industry`, single-model (`needs_human` flag left in place) |
| `carcass_yield_pct` | — | not found — despite Gotoh's two weights (756 kg / 476 kg) and two extension dressing-percentage ranges sitting in the fetched documents |
| `saleable_meat_pct` | — | not found — despite SDSU's worked 1,200-lb → ~490-lb example |
| `bms_scale_definition` | — | not found — despite two plain-text sentences confirmed present at spec-authoring time |
| `marbling_vs_yield_tradeoff` | — | not found (an acceptable outcome — the spec allowed for "sources treat the axes as independent" as the honest answer) |
| `feed_per_kg_beef` | — | not found — despite the beefresearch.ca 6:1 feed-to-gain sentence sitting in the fetched document |

## The gap between "the source has it" and "the model found it"

Every one of the six items had at least one candidate document independently
confirmed, via `WebFetch`, to contain a directly relevant sentence *before*
this batch was ever sent to extraction. `carcass_yield_pct`, `bms_scale_definition`,
and `feed_per_kg_beef` all had verbatim text sitting in the 76,295-character
Gotoh document or the other five fetched pages — and the extraction pass
found none of it.

This is a different failure shape than vanilla's. Vanilla's dropped rows were
*wrong extractions* (a real quote, answering the wrong question) or a *gate
limit* (a true fact stated too plainly to contain a numeral). Wagyu's problem
is upstream of both: the model mostly **did not return a candidate row at
all** for five of six items, against documents that demonstrably contained
the answer. `qwen2.5-coder:7b` returned 0/12 calls with a figure; `gemma4-32k`
returned 1/12.

Two candidate explanations, neither confirmed here:

1. **Document length.** The Gotoh review is 76,295 characters chunked into
   19 pieces across all six documents combined — an item's answer could sit
   in a chunk that never reached the model, or reached it without enough
   surrounding context to recognize the sentence as answering the specific
   question asked.
2. **Multi-fact density.** Several of the target sentences sit inside
   paragraphs carrying two or three other numbers (the Gotoh feed sentence is
   immediately followed by an unrelated import-percentage statistic). A model
   asked a narrow question against a dense paragraph may decline rather than
   pick the wrong number — which, if true, is the *correct* conservative
   behavior and a real limit of this extraction stage rather than a bug in
   it.

Worth a follow-up pass with the same URLs and no spec changes, to see if a
second run (a different chunking pass, or a lower-context single-item
extraction) recovers any of the five nulls — the sources are not the
constraint here.

## The one accepted row

`days_on_feed: 30 months`, quoted verbatim: "Moreover, it takes 30 months to
complete the Wagyu fattening process." This is consistent with — and a third,
independent phrasing of — the same paper's separately-stated "28 to 30
months of age" slaughter range and 29.2-month mean, all confirmed present at
spec-authoring time. Single-model result (`gemma4-32k` only), so `verify`
correctly flags it `needs_human`; the flag is accurate and left in place, and
a human accepted it here on the strength of the number's internal consistency
with the rest of the same document, not on model agreement.

## Honest position on the corpus this produced

The spec-authoring bottleneck this project has repeatedly named held again —
every source was real, verified, and on-topic — but it did not translate into
a well-populated batch. That is itself the finding worth carrying forward:
**source quality does not guarantee extraction yield**, and a future pass
worth spending should look at chunk size and per-item prompt framing before
authoring another spec on the assumption that better sources alone fix a thin
result.
