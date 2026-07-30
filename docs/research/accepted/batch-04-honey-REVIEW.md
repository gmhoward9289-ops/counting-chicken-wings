# batch-04-honey — human review record

**Outcome: nothing accepted. Zero figures from two full runs.**

Recorded because a negative result that cost two runs is worth as much as a
positive one, and because `outbox/` is gitignored — without this file the only
trace would be the absence of a `batch-04-honey-findings.yaml` beside
saffron's.

## What was returned, and what the gate did

| run | fetched | figures | accepted |
|---|---|---|---|
| 1 | 12 of 17 docs (5 SSL failures) | 7 | 0 |
| 2 | **17 of 17**, 59 chunks | 7 | 0 |

Run 2's rejected rows, with every source present:

```
honey_per_bee_lifetime       "1 and ½ teaspoons"   a string, for a mass
flowers_per_pound_honey      2670588               not in its own quote
forager_fraction             "Several thousand"    prose, for a fraction
honey_yield_per_colony_year  (empty quote)
nectar_to_honey_ratio        2670588               same number, again
extraction_recovery          (empty quote)
colony_size                  null                  survived, and useless
```

**One number, 2670588, appeared as the answer to three unrelated questions.**
That is the signature of answering from proximity rather than from meaning.

## Two independent causes, and it matters which is which

**1. The subject genuinely lacks sourced numbers.** This was the spec's own
prediction and it held. The scouting found that "1/12 teaspoon per bee" is
attributed by Iowa State to *"National Honey Board trivia"*, and that "two
million flowers per pound" traces to a cancer-biology review where the sentence
carries no reference at all. Asking a model to extract a figure that no document
states will produce either a refusal or a fabrication — never a citation.

So part of this outcome is the pipeline **correctly reporting an absence.** The
provenance audit succeeded; it just produced no corpus, which is the honest
result for a subject built on folklore.

**2. The second model fabricates rather than declining.** Independent of the
subject. Fixed by reverting `LONG_CONTEXT` to `gemma4-32k` — see the reasoning
block in `tools/cooper/runner.py`.

## What was fixed because of this batch

- **A hole in the gate.** `band_in_quote` passed anything `float()` could not
  parse, so `"32 mg"`, `"industry"` and `"Several thousand"` skipped the
  strongest check entirely. Three junk rows would have reached `accept`.
- **COOPER had no CA bundle.** `cafile: None`, `capath: None`, certifi absent.
  Five URLs — including all three PMC articles and the U. Arkansas PDF, the four
  best documents in the batch — failed verification while fetching fine from the
  Mac. Each printed one line among sixteen successes, so the run *looked* like a
  model problem and was plumbing.
- **The API's ceiling.** Not from this batch, but found while working on it: the
  web UI was still serving `ceiling` as the request's unit count, so a gram of
  saffron reported ceiling=1 beside floor=150.

That is three real defects for two runs of a subject that yielded nothing. The
batch paid for itself in the gate rather than in the corpus.

## If honey is picked up again

Do not re-run this spec as written. Items 1, 2 and 7 are provenance audits whose
answer is already known — *no traceable origin* — and re-running them just
invites another fabrication. What is left worth extracting:

- **Item 5, `honey_yield_per_colony_year`.** The one item that can reach
  `measured`. NASS publishes it as plain text: *"Yield per colony averaged 48.0
  pounds"*, 2026-03-13 release. A single-item batch, or frankly a human reading
  one sentence.
- **Item 6, `nectar_to_honey_ratio`.** Nicolson, Human & Pirk 2022 in
  *Scientific Reports* is real, peer-reviewed, on-topic, and now fetchable. The
  ratio itself is `derived` and human-only, but its inputs are citable.
- **Item 3, `colony_size`.** Several sources agree once definitions are
  separated (peak vs annual, feral vs managed).

The remaining four items should be written up as **prose about what is not
known**, not chased for numbers. "The most repeated statistic about honeybees
has no source" is a better fact than any of the figures would have been.
