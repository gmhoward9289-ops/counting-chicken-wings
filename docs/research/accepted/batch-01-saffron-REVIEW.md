# batch-01-saffron — human review record

The first batch to go all the way from a COOPER run to live corpus. This file
is the durable record of what was accepted, what was rejected, and why, because
`docs/research/outbox/` and `inbox/` are gitignored and the reasoning would
otherwise be lost with them.

**Outcome: 5 figures returned, 3 accepted as-is, 1 reframed, 1 dropped, 1 added
by a human.** Live in `data/taxonomy_saffron.yaml`,
`data/loss_chain_saffron.yaml`, `data/mixing_saffron.yaml`.

## What COOPER returned, and what happened to each row

| Field | Value | Verdict |
|---|---|---|
| `stigmas_per_flower` | 3 | **accepted**, 2/2 consensus, confirmed by a second document |
| `stigmas_per_pound` | 210,000 | **accepted** at `estimate` — the source hedges it "Supposedly", so we do too |
| `drying_mass_yield` | 0.2 | **reframed** to `drying_mass_loss: 0.8` |
| `flowers_per_gram_dried` | 210,000 `stigmas per pound` | **dropped** — misattributed |
| `yield_per_acre` | 8–12 lb/acre | **dropped** — conflicts with a second source; recorded as a conflict instead |
| `harvest_labour_hours` | — | not found in any source |

## The three interesting decisions

### The dropped row is the one that matters

COOPER answered `flowers_per_gram_dried` with a quote about **stigmas per
pound**. The quote was real, verbatim, and in the right document — it simply
answered a different question. A crocus has three stigmas per flower, so the
error was wrong by **exactly the factor this subject exists to measure**.

Verbatim-quote verification cannot catch this. It proves a sentence exists; it
says nothing about whether that sentence answers the question asked. That is
what the `unit_matches_field` check was added for, and this row is the reason
it exists.

### The reframed row: a finding reports a source, a corpus row models it

`drying_mass_yield: 0.2` was rejected because 0.2 appears nowhere in its quote
("the stigmas lose **80%** of their weight"). The arithmetic is right. The
reporting was not.

The fix was **not** to relax the gate. It was to record what the source says —
`drying_mass_loss: 0.8`, which the value check accepts against "80%" — and put
the inversion in `data/loss_chain_saffron.yaml`, where a human wrote
`survive_mode: 0.20` with a comment explaining it. This turned out to be the
generalisable rule: **a finding reports a source; a corpus row models it.**

It was also graded `industry`, not `derived`. Inverting a trade rule of thumb
yields a trade rule of thumb. In this project `derived` means computed from
*measured* figures, the way dressing yield comes out of two NASS totals, and
HS661 measured nothing.

### The added row: retrieval worked, extraction did not

The correct flowers-per-gram figure — **150**, stated outright — was sitting in
a document COOPER had already **fetched** and never extracted from. A human
found it by reading the returned artifact.

That is a pipeline finding, not a data one, and it splits the failure cleanly:
the fetch and embed stages found the right source; the extraction stage read
only the HS661 PDF and ignored the other two documents. It is also the concrete
justification for returning raw documents with every batch rather than just the
YAML — without the artifact, the figure would have been unrecoverable and the
misattributed row would have looked like the best available answer.

Its `agreement` field says `0/2 (human extraction)` and `verify` duly flags it
`needs_human`. That flag is accurate and was left in place.

## A conflict recorded rather than resolved

Two extension services disagree about per-acre yield by roughly three-fold:

- Penn State: "one acre of land produces only about 3 pounds"
- UF/IFAS HS661: "an annual yield of 8–10 pounds of dried saffron per acre is
  obtained in an established planting"

**Neither is loaded as data.** They are probably not measuring the same thing —
HS661 says "in an established planting", and a saffron field takes years to get
there. The disagreement is recorded in `data/sources.yaml` under
`psu-extension-saffron`, because a three-fold spread between two land-grant
extension services is the most honest thing we currently know about saffron
yields.

A third figure was left out entirely: Penn State's "about 50 flowers to produce
just one teaspoon". Converting it needs an assumed mass for a teaspoon of
threads, and that assumption would be ours, not the source's.

## The cross-check that makes the subject trustworthy

Two sources, two completely different routes, 3% apart:

```
UC ANR, stated:    150   flowers per gram
HS661, implied:    154.3 flowers per gram
                   (210,000 stigmas ÷ 3 per flower ÷ 453.59237 g/lb)
```

The HS661 route runs through the stigmas-per-flower constant, so the two are
not fully independent — but they come from different publications, different
decades, and different framings, and one of them hedges itself with
"Supposedly". This is tested in `tests/test_saffron.py`.

## Honest position on the corpus this produced

Saffron is **thin, and visibly so**. No `measured` figure exists or ever will
from these sources: there is no NASS for saffron because the US grows almost
none commercially. Everything tops out at `industry`, and the one stage that
would move the count — flowers not picked in time — is unsourced and therefore
**off by default**. The default saffron answer rests only on cited figures.

That is a stricter standard than the poultry chain got, deliberately. Wings
carry eight estimate-grade factors, five of which move the count. We did not
want to recreate that debt on day one in a new domain.

## What this cost, which was the point of going first

The translation step — 4 verified figures into live corpus — took roughly the
same effort as the COOPER run that produced them, and it surfaced **a real
model bug** the poultry corpus could never have exposed: the pooling maths
assumed every contributing individual gives at least one whole unit. True of
wings and eggs, false of a gram of saffron. Asking for one gram returned "came
from about 1 different flower" against a floor of 150 — two numbers in one run
contradicting each other.

So the "a new subject is four YAML files and zero Python" estimate was wrong.
It was four YAML files, one model fix, one CLI fix, and 16 tests. Worth knowing
before scaling to more subjects, and cheaper to learn on the second domain than
the fifth.
