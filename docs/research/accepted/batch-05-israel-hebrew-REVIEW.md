# Batch 05 — Israel, Hebrew sources: review

**Result: 0 figures returned, and that is the finding.** Run 2026-07-30 against
10 documents in 3 items. Both models — `qwen2.5-coder:7b` and `gemma4-32k`, six
calls each — returned nothing from any of them.

**The documents are fine.** Every URL fetched, including a 40-page State
Comptroller PDF that `pypdf` extracted to 103,610 characters, and the Hebrew
came through intact: 18,137 Hebrew characters in the Badatz page, 10,285 in
Kosharot, 8,738 in the Comptroller landing page. Chunking produced 21 chunks
across ~290,000 characters, which is the expected count at 12,000 chars a chunk.
So this is not a fetch failure and not a chunking failure.

## The pipeline cannot read Hebrew, and a human reading the same artifact can

A manual pass over the returned documents found real figures in two of them
within minutes. That is the same shape as the saffron finding — the retrieval
stage fetched a UC ANR page and the extraction stage never read it, and the
flowers-per-gram figure was recovered by a human reading the returned artifact.
**It is the second time the artifacts have been worth more than the extraction**,
and it is why the raw documents come back with every batch.

**Most likely cause: cross-language retrieval.** The questions in the spec are
English, the chunks are Hebrew, and `nomic-embed-text` is English-centric. An
English query embedding scored against Hebrew chunk embeddings is close to
noise, so the top-k chunks handed to the model are probably not the ones holding
the numbers. The models are also small and not Hebrew-tuned, which would
compound it.

**Two things to try before concluding Hebrew is out of reach**, cheapest first:

1. **Ask in Hebrew.** Put the question text in the spec in Hebrew for
   Hebrew-language items, so query and chunk share a language. This is a spec
   change, not a code change.
2. **A multilingual embedder** (`bge-m3` or `paraphrase-multilingual`) for
   documents detected as non-Latin. This is a real change to `runner.py` and
   should wait on whether (1) helps.

Until one of them works, **Hebrew sources are a human-read job, not a COOPER
job**, and a batch of them should not be sent again as-is.

## What the human pass found — PROMOTED 2026-07-30

Both figures were accepted into the corpus at `industry` grade, from a new
source `ofot-sector-summary-2021` graded `trade_body`. The section below is kept
as written so the reasoning that justified the promotion stays with it.

### 1. A second, independent industry figure for the head count

`ofot.co.il`, the growers' organisation summary "ענף הלול - סיכום 2021", carries
a sector table. Verbatim, as fetched:

> סוג התוצרת / מספר מגדלים / כמות תוצרת / יחידות / מיליוני ₪ / אחוזים
> **בשר פטמים 604 · 515,400 טון · 3,414 · 57.3%**
> בשר הודים 84 · 81,530 טון · 553 · 9.3%
> ביצי מאכל 2863 · 2,230 מיל' ביצים · 1,010 · 17.0%
> **שלוחות הרבייה 78 · 244 מיל' אפרוחים · 980 · 16.4%**
> סה"כ 3,629 · 5,957 · 100%

Two things here matter.

**604 broiler growers**, against the Times of Israel's "about 600 large chicken
farms" from the Poultry Breeders Association. Two industry bodies, two
publications, one number — that is corroboration rather than repetition, and it
is the kind of agreement the corpus is built to record.

**244 million chicks** placed by the breeding branch in 2021. Chicks placed is a
throughput proxy for birds raised, and it sits just under the 260 million a year
the Times of Israel reports for 2025. Four years apart, from two different
industry bodies, differing by ~6% — which is roughly what four years of growth
looks like. **This is the strongest corroboration the Israeli head count has**,
and it arrived from a source the pipeline had already fetched and failed to read.

Before loading it, note what it is not: chicks placed is not birds slaughtered.
Mortality sits between them, and the model already carries a grow-out mortality
factor. Loading 244M as `head_slaughtered` would overstate throughput by that
mortality; loading it as its own measure is the honest option.

515,400 tonnes for 2021 is also loadable and would extend the CBS output series
backwards — but CBS is the better publisher for that figure and covers 2020
already, so the value here is the cross-check, not the coverage.

### 2. Sector scale, from the State Comptroller

> כ-5.5 מיליארד ש"ח בשנה - כ-17% מכלל התפוקה החקלאית בארץ

The poultry sector at ~NIS 5.5bn a year, ~17% of Israeli agricultural output.
From annual report 65c, so it describes 2013–2014 and is a decade stale. Useful
for a sentence about the sector's weight in Israeli agriculture, not for a
series.

### 3. No bedikah rate in any of the four halachic sources

The pre-batch search suggested 5–7% treif at the tendon junction. **None of the
four documents fetched contains a percentage at all** — zero `%` or `אחוז`
matches across Badatz, Kosharot, Toraland and Pninei Halacha. The figure exists
somewhere in the discussion literature, but not on these four pages.

So the position is unchanged and should be stated plainly: **kosher inspection
is described in the model and not quantified.** The next attempt should target
responsa collections and slaughterhouse-facing kashrut training material rather
than consumer-facing certification pages, which explain the rules and never the
rates.

## Outcome

1. **Promoted, both, at `industry`.** `chicks_placed` and `grower_count` are
   their own measures in `output_stat_year`; the chick figure is never
   `head_slaughtered`, and a test asserts the two stay distinct. Two further
   tests pin the corroboration itself — the chick and head figures must stay
   within 25% of each other, and the grower count within 550–650 — so if a
   future edit breaks the agreement that justified promotion, the suite says so
   rather than the claim quietly becoming false.

   The learning-centre fact "Nobody officially counts Israel's chickens" was
   updated to carry the second check, because it previously described only the
   kg-per-bird one.

2. **The Hebrew-question experiment ran as `batch-05b-israel-hebrew-questions`.**
   Same documents, questions rewritten in Hebrew, with item 1 targeting a table
   whose answer is already known — 604 growers and 515,400 tonnes — and item 3
   as a negative control over four documents that provably contain no
   percentage.

3. **Bedikah stays described and unquantified.** Nothing found here changes
   that, and the next attempt should target responsa and slaughterhouse kashrut
   training material rather than consumer-facing certification pages.
