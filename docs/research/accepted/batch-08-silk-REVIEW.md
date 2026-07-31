# batch-08-silk — human review record (PASSED, third run)

Run on COOPER 2026-07-31. **`verify` passed. Five figures promoted, one
recorded as a human judgement, one item still unanswered.**

This replaces a NEGATIVE RESULT record covering two failed runs on 2026-07-30.
The earlier record is not deleted so much as superseded: everything it
diagnosed was correct, and this run is what those diagnoses bought. The
sections below say what changed and what it cost.

## What actually rescued this batch

**The entity-decode fix, and it is worth being precise that it was the whole
story for one row and none of the story for the others.**

`fetch_url()` never called `html.unescape()`, so `&nbsp;` and numeric entities
survived into the inbox — and the inbox is what `verify` matches quotes
against. A model that read the prose correctly and wrote it back as ordinary
words produced a quote that could *never* match. It read exactly like a model
inventing a citation.

It cost the batch's single best row. `reeling_cocoons_per_thread` came back at
2/2 consensus in run one and was rejected as "quote does not appear in the
document". The suekayton page carries 47 `&nbsp;`, one of them inside the
sentence in question.

**Confirmed fixed and confirmed decisive.** The same row came back at 2/2 this
run, verified clean, and is now the only mixing pool in the entire project with
a citation that is not our own estimate:

> Then a machine unrolls the cocoon, winding the silk from five cocoons
> together to make one silk thread.

Three documents that previously carried entities now carry zero. That is one
row rescued by one bug fix. **The other four rows failed for unrelated reasons
and needed unrelated fixes**, which is the part worth carrying forward — the
entity bug was the loudest problem, not the only one, and fixing it alone would
have produced a fourth failed run.

## What COOPER returned

Six items asked, five figures returned, all five verified, all five checked by
hand and found semantically correct.

| Field | Value | Agreement | Source |
|---|---|---|---|
| `cocoons_per_pound_raw_silk` | 2,000–3,000 | 1/1 (gemma declined) | New World Encyclopedia |
| `cocoons_per_tie` | 150 | **2/2** | Smithsonian Folklife Festival |
| `cocoons_per_shirt` | 1,000 | 1/1 (qwen declined) | Sue Kayton |
| `cocoons_per_dress` | 1,700–1,850–2,000 | 1/2 disagree | Sue Kayton |
| `reeling_cocoons_per_thread` | 5 | **2/2** | Sue Kayton |

`filament_length_per_cocoon` returned **nothing** — see below.

## The three fixes that were not the entity bug

### 1. A source that only exists in a browser

`cocoons_per_tie` was cited to bows-n-ties for "a single tie requires about 120
to 130 cocoons". Real sentence, live page, confirmed 200 during the original
scout. COOPER's fetch of that URL contains **no 120 and no 130**: the article
body is rendered by JavaScript and the fetched text stops mid-word at *"The
average wor"*. Both models correctly returned nothing, twice, and it read as
model weakness for a week.

Replaced with two sources that survive a no-JS fetch, both verified with the
project's own fetcher before sending rather than in a browser:

- Smithsonian Folklife Festival — "about 150 cocoons are needed for a necktie"
- AFB Education — "about 120 to 130 cocoons ... to produce a single necktie"

**They disagree, and the disagreement is reported rather than resolved.** A
third figure, 110, circulates across several retail pages, all reproducing one
unattributed sentence verbatim down to its closing exclamation. The Smithsonian
figure is used on provenance alone, not on any evidence it is more accurate.
The honest reading is "roughly a hundred and something".

A 15-URL sweep found no source stating 140 at all, despite search snippets
attributing it to two publishers. Treat 140 as unsourced.

### 2. The semantic hole `verify` cannot see, and the fix that worked

The previous run's `cocoons_per_shirt` stored `lo 1700 / mode 1800 / hi 2000`
for a **shirt**. Those are the *dress* numbers, from a sentence that answers two
questions at once:

> It takes 1700 to 2000 cocoons to make one silk dress (or about 1,000 cocoons
> for a silk shirt).

Every figure in the row genuinely appears in the quote, the quote is verbatim,
and the document is the right one. **No mechanical check reaches this.** The
band rule added since (`lo` and `hi` must each appear in the quote) does not
touch it either, and the docstring at `band_in_quote` says so explicitly.

What fixed it was the spec's `Watch for` block, which `parse_spec` now feeds to
the model. Reworded to name the trap outright — *1700 and 2000 are the dress,
1,000 is the shirt, read the clause and not the sentence* — the row came back
**1000**. Two other `Watch for` warnings in the same spec also held: the dress
row took the correct pair, and nothing leaked the AFB page's thread-length
figures into a value field.

That is one data point, not a proof. But it is the first evidence in this
project that the `Watch for` channel changes behaviour, and it is the only
defence that exists for this class of error.

**Every returned row was still read by hand against its surrounding document
context.** That check is not optional and the gate passing is not a substitute
for it.

### 3. A figure no machine could produce, withdrawn rather than coerced

`cocoons_per_worm` returned nothing across all three runs, and **the models
were right every time.**

`value_in_quote` requires the figure to appear in the quoted sentence.
Sericulture writers never state one-cocoon-per-worm as a number — they write
"the larvae enclose themselves in a cocoon", which contains no number word at
all, so an honest answer of `1` has nothing to ground against. A 35-URL sweep
across FAO, Britannica, Wikipedia, Saint Louis Zoo, Carolina Biological,
extension PDFs and museum pages found exactly one fetchable sentence stating
the relation, and it states it sideways:

> A normal silkworm cocoon (NSC) with a unique nonwoven structure is usually
> spun by a single silkworm larva.

"a single silkworm larva", not "one cocoon" — the number is in the meaning and
not in the characters, so `value_in_quote` would reject it, correctly, since it
does not know that "single" is a number word here.

**The item was removed from the batch and the figure recorded as a human
judgement instead.** Its heading no longer begins `### Item` and its URL is
written inline rather than as a bullet, so the parser cannot sweep it into the
preceding item's URL list.

The tempting alternative was to keep the item and have it write
`units_per_individual_*`, which `band_in_quote` does not read. That would have
passed. It would also have been gaming the gate through a field-name loophole,
which is worse than failing, and it is recorded here so nobody tries it later
thinking it clever.

Three hedges were kept on the promoted row rather than tidied away: the paper's
own "usually"; its counterexample (a *Bombyx mori* strain where three or more
larvae spin one cocoon collectively); and a grade of `industry` rather than
`study`, **even though the paper is peer-reviewed**, because the sentence is
uncited scene-setting in a materials-science study. That is the Jaganathan
honey distinction exactly.

## What is still unanswered

`filament_length_per_cocoon` returned **nothing this run**, having returned a
wrong answer last run. Its previous output stored `hi = 9000`, a number
appearing in no silk document, riding beside a legitimate 1000 and 3000 from
"300 to 900 meters (1000 to 3000 feet)" — and flipped the spec's unit from
metres to feet while doing so.

The `lo`/`hi` bound rule now in `band_in_quote` catches that, and it was **not**
worked around. The spec's `Watch for` was also strengthened to say the unit is
metres and that the two number pairs are one measurement in two units, not a
range from 300 to 3000.

The model then declined the item entirely. That is a **loss, and an honest
one** — a decline is strictly better than the confident wrong answer it
replaced, and it is the correct behaviour when a model is unsure. The figure is
carried as prose in `data/taxonomy_silk.yaml` and as an open item in
`docs/RESEARCH.md`, not as a row. A second independent source would settle the
300–900 m against folk 1,000–1,600 m spread; we could not source the higher
range at all.

## Checks that were run and passed

- **Bot-wall check** (L1's finding, applied here). `scout`'s docstring claims
  reachability is host-independent; L1 measured that it is not — PMC served
  41,579 chars to the Mac and 167 chars of reCAPTCHA to COOPER, logged as a
  successful fetch. **All four silk documents fetched to identical character
  counts on both hosts** (16,299 / 49,272 / 6,849 / 1,479). On-disk byte counts
  differ by exactly the line count in every case, which is CRLF and not
  content.

  Worth recording that a size comparison would **not** have caught the
  bows-n-ties failure: JS truncation returns a plausible, long document that is
  truncated identically on both hosts. The two checks are complementary and
  neither substitutes for the other.
- **Semantic hand-check** of all five rows against surrounding document
  context. All five answer the question actually asked. None is a bare table
  row severed from its header.
- `build` + `audit` clean, exit 0. Full suite green.

## What was NOT the problem

**Chunking.** The going theory after maple was that 4 chunks across ~30k chars
was starving retrieval. It is not, and this run confirms it a third time: 9
chunks across 4 documents, every item's own document in front of the model, and
the one item that failed did so with the right text on screen.

## Verdict

**Promoted.** Five figures into `data/taxonomy_silk.yaml`,
`data/mixing_silk.yaml` and `data/loss_chain_silk.yaml`, plus the
cocoons-per-worm constant as a documented human judgement, four sources into
`data/sources.yaml`, two fact cards, and `tests/test_silk.py`.

Silk is the thinnest-sourced subject in the corpus. It pushes the
unsourced-estimate share of loss factors from 46% to 48% and the README says
so — which is the audit doing its job, not a regression.

Two figures worth flagging to anyone citing this subject later: the necktie
count is one of three disagreeing numbers, and the one-cocoon-per-silkworm
constant that the entire subject rests on is its weakest-sourced figure. Both
are stated plainly on the rows themselves, not just here.
