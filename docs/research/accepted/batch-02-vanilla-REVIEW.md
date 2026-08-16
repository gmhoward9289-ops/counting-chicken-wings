# batch-02-vanilla — human review record

Deferred at spec-authoring in July, picked up 2026-08-15 once a search pass
had produced six items against four curl-verified URLs. This file is the
durable record of what was accepted, what was rejected, and why, because
`docs/research/outbox/` and `inbox/` are gitignored and the reasoning would
otherwise be lost with them.

**Outcome: 3 figures returned, 1 accepted, 2 dropped by human review, 3 items
found nothing in any source.** The accepted figure is promoted to
`docs/research/accepted/batch-02-vanilla-findings.yaml` but is **not yet in
`data/`** — that translation (schema shape, source entry, confidence,
build/audit/pytest) is a separate follow-up, deliberately not done in the same
pass as a repo that already had unrelated in-progress work on `model.py` and
`schema.sql`.

## What COOPER returned, and what happened to each row

| Field | Value | Verdict |
|---|---|---|
| `flowers_per_bean` | 1 | **dropped** — see below |
| `green_to_cured_ratio` | 6 kg green per kg cured | **accepted** at `industry`, 2/2 consensus |
| `curing_duration_days` | 7 | **dropped** — answers a different question |
| `beans_per_kg_cured` | — | not found in any source |
| `hand_pollination_window_hours` | — | not found in any source |
| `labour_hours_per_kg` | — | not found in any source, as the spec predicted |

## The two dropped rows

### `flowers_per_bean`: the degenerate case behaved exactly as warned

The spec called this out in advance as "the point is that it is boring" — a
test of whether the floor machinery misbehaves at the constant `1`. It did,
just not in the model. The supporting quote —

> A flower gives a vanilla bean after hand pollination.

— genuinely supports `1` grammatically (singular article, singular noun on
both sides) but never states the numeral. The mechanical bound-in-quote gate
requires the literal figure when there's no lo/hi band to interpolate within,
so it correctly refused to pass `1` on an implication.

This is not a gate bug. `measured` and `derived` are human-only grades this
project's `verify` step rejects outright regardless of who sets them, by
design — so there is no path through the candidate/accept pipeline for "the
grammar implies it." Recording `flowers_per_bean = 1` properly means a human
writing it directly into `data/taxonomy_vanilla.yaml` as `derived`, citing
this same quote as supporting context rather than as a verbatim source of the
number. Left for that follow-up rather than forced through here.

### `curing_duration_days`: a real misextraction, not a borderline bound

The model returned `7` against:

> Post Harvest Management: The curing should be done within a week of
> harvesting the beans.

That sentence answers *when curing must begin relative to harvest*, not *how
long curing takes*. The spec expected curing to run months-long — the explicit
contrast drawn was against poultry's 47-day grow-out — so a 7-day figure
attributed to "curing duration" is the same failure mode saffron's
`flowers_per_gram_dried` row hit: a real, verbatim, in-document quote that
simply answers a different question than the field name claims. `verify`'s
`band_in_quote` check caught this one on the numeral not appearing standalone
(`7` inside "a week" parses as a unit conversion the check doesn't perform,
not a literal match) — the semantic mismatch is the actual reason to drop it,
the syntactic failure was just how it surfaced first.

## The three nulls

`beans_per_kg_cured`, `hand_pollination_window_hours`, and
`labour_hours_per_kg` returned no figure from any of the four fetched
documents. The spec treated a null on `labour_hours_per_kg` as a real and
expected outcome in advance — saffron's equivalent item found nothing either —
so this is reported plainly rather than treated as three fetch failures. No
walled documents this run; all four URLs returned real, extractable content
(two HTML, two PDF via `pdftotext`).

## Honest position on the corpus this produced

One figure, at `industry` grade, from a subject that was supposed to stress
the pipeline at both extremes — a degenerate anatomical constant and a large
continuous-mass concentration ratio. The concentration ratio came through
clean. The constant did not, and the reason it did not is instructive: the
mechanical gate cannot distinguish "the model didn't look hard enough" from
"no document states this as a number," and for vanilla's flower-to-bean
relationship, no document needed to — it's implicit in ordinary grammar. A
subject where the interesting fact is *too obvious to state* is a real gap in
what a verbatim-quote gate can certify, worth carrying into `batch-03-wagyu`
and future specs as a known blind spot rather than re-discovering it each
time.
