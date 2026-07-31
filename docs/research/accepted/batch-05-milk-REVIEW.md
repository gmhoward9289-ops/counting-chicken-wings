# batch-05-milk — human review record (NEGATIVE RESULT)

Run on COOPER 2026-07-31. **`verify` FAILED. Nothing was accepted and nothing
reached the corpus.**

Recorded here in the batch-08-silk tradition. Milk was the richest spec the
project has written and the first subject outside poultry where `measured` was
reachable; it returned four rows, one of which failed the gate mechanically and
**three of which passed every check and are unusable**. That ratio is the
finding.

| | |
|---|---|
| Items asked | 7 |
| URLs fetched | 19 distinct, 211 chunks |
| Fetch failures reported by the runner | **0** |
| Fetch failures actually suffered | **1** — see §1, the runner did not know |
| qwen2.5-coder:7b | **1 of 14** calls returned a figure |
| gemma4-32k | **5 of 14** |
| Rows returned | 4, covering items 2, 3, 4 and 6 |
| Items returning nothing at all | **1, 5 and 7** |
| Gate verdict | **FAILED** (1 row) |
| Rows that passed the gate and are still wrong | **3 of 3** |
| Accepted | **nothing** |

Items 1, 5 and 7 are the three the spec rated most promotable — the headline
annual yield per cow (`measured`), the AMS component yield factors (`measured`),
and the tanker/silo pooling question that is the entire reason the project cares
about milk. All three came back empty.

## 1. The scout's core promise is false, and this run disproves it

`scout()` says, in its own docstring:

> Reachability is a property of the fetcher and its user agent, not of the host
> running it, so this is faithful from either machine — but running it on COOPER
> removes the last doubt.

**It is not faithful from either machine.** Scouted from the Mac, every one of
the 19 URLs was reachable and every claimed quote present; the run was declared
"Safe to send". One URL then behaved completely differently on COOPER:

| Document | Mac (scout) | COOPER (real run) |
|---|---|---|
| `pmc.ncbi.nlm.nih.gov/articles/PMC10289513/` | **41,579 chars** | **167 chars** |

Those 167 characters are:

```
Checking your browser - reCAPTCHA Checking your browser before accessing
pmc.ncbi.nlm.nih.gov ... Click here if you are not automatically redirected
after 5 seconds.
```

Same fetcher, same user agent, same code — different IP. PMC serves a reCAPTCHA
interstitial to COOPER and the article to the Mac. The runner logged it as
`fetched`, because 167 characters is a successful HTTP response.

This is the batch-09 lesson repeating with the roles reversed. There the note
was "a URL verified from one host is not verified for another", written about
eCFR after a Mac scout wrongly cleared it. The scout was then built to close
that hole, and its docstring asserts the hole is closed. It is not: the
docstring's reasoning is wrong, because bot-walling keys on **address and
reputation**, which are properties of the host, not of the fetcher.

The comparison is only strictly meaningful for the seven HTML fetches, since the
PDFs went through different extractors on the two hosts (`pdftotext` on the Mac,
`pypdf` on COOPER). Of those seven, six matched to within 5 characters —
12,947/12,947, 62,520/62,520, 3,194/3,194, 30,469/30,469, 39,883/39,883,
34,661/34,656 — and PMC is the sole divergence. A clean single-host result, not
a flaky one.

**Consequence for this batch.** Gross 2023 (*Animal Frontiers*) is the source
the spec called "the strongest source in the batch" and the only one that
carries the sentence declining to define a maximum daily yield. It was invisible
to both models. Items 2 and 3 were built on it and item 3's stated deliverable —
*"reporting the absence is the deliverable"* — was therefore impossible from the
moment the fetch returned.

**Fix worth making before any re-run:** `scout` should reject a document whose
body is implausibly short or matches a known interstitial, and should be run
**on COOPER**, not merely be *runnable* there. A 200 with 167 bytes is the same
class of lie as batch-08's JavaScript-rendered page.

## 2. Row by row — three clean passes, three wrong answers

### `milk_yield_per_cow_day` = 20,501 pounds — wrong three ways at once

```yaml
value_mode: 20501
unit: pounds
quote: "For example, Joe Dairyman has a herd of 110 Holstein cows in South
        Carolina with a rolling herd average for milk of 20,501 pounds."
```

The quote is verbatim and the number is in it. It is still not a figure:

1. **It is annual, stored in a per-day field.** The same document says the RHA
   "is an indicator of herd management during the last 365 days". Out by ~365×.
2. **"Joe Dairyman" is a fictional worked example.** The surrounding paragraph
   is teaching a reader how to look themselves up in Tables 1–4. It is a
   textbook illustration, not an observation of anything.
3. **It is one South Carolina herd** in the top 25% of its size group — the
   passage says so in the next sentence — not a national average.

The dangerous part is that **20,501 lb/cow/year is roughly the right order of
magnitude for a real US annual per-cow yield**, so this row would read as a
plausible answer to *item 1* to anyone skimming. It is the wrong item, the wrong
population, and a made-up farmer.

Every gate check passed it. The quote matches, `20501` is in it, the quote ends
in a period so truncation did not flag, and `unit_matches_field` saw no
`SUBJECT_TERMS` collision because neither "day" nor "pounds" is in that list.
Only the `1/1` agreement flag fired.

### `physiological_ceiling_per_day` = 123.61 litres — correctly extracted, and the exact trap the spec named

The one **2/2 consensus** row in the batch, and the extraction is genuinely
right: Guinness does say 123.61 L in 24 hours, by Marília FIV Teatro de Naylo,
at a Brazilian dairy tournament in 2019.

Its target column is `product.max_units_per_day`, and **it must not go there.**
Trap 1 of the spec, verbatim:

> Any ceiling we use will be an *observed record*, not a physiological limit,
> and it must be graded and labelled as such.

`max_units_per_day` is what makes a hen's floor a *hard* floor — twelve same-day
eggs need twelve hens because no hen can lay two. A single competition record set
by one exceptional animal supports no such claim about any other cow. Writing
123.61 into that column would make milk's floor look like eggs' floor while
resting on nothing, in the corpus whose entire product is that numbers mean what
they say.

And because PMC was walled (§1), COOPER returned **the record without its
counterweight**. Item 3 asked for two things — the record *and* the sentence
declining to define a maximum — precisely so the record could never stand alone.
Half of a two-part item is worse than none of it here: the half that survived is
the half that invites the mistake.

### `herd_size` = `'9.3 million'` — the row that failed the gate

```
findings.yaml:findings[2]: value(s) '9.3 million' are not numbers.
```

The gate is right and the message is exact. `value_lo` must become a REAL
column; `'9.3 million'` is prose. This is the batch-04-honey non-numeric hole,
already closed, catching a new instance — the check working as designed.

The underlying fact is fine — Census of Agriculture 2022, 9.3 million milk cows —
but the row is unusable as returned on two further counts:

- The quote stops mid-sentence: `"U.S. farmers had 9.3 million milk cows at"`.
  The document continues "…the end of 2022", which is the part that dates it.
- It answers only the national-herd half of item 4 and returns **nothing** on
  cows per operation. So the spec's trap 3 — mean 283 vs midpoint 1,300, both
  correct, 4.6× apart — was never engaged at all. Neither statistic came back,
  which means the trap is untested rather than survived.

### `chain_loss` lo=12 / mode=20 — batch-09's failure class, predicted again, uncaught again

```yaml
value_lo: 12
value_mode: 20
unit: percent
quote: "Fluid milk 109 13 12 22 20 35 32"
```

A table row with its header amputated. The header, eleven lines up in the same
document:

```
                          Retail level      Consumer level    Total retail and
                                                              consumer level
Calories        Calories  Percent   Calories  Percent  Calories  Percent
Grain products       881       106       12        166      19       271     31
...
Dairy products       367        34        9         75      21       109     30
     Fluid milk      109        13       12         22      20        35     32
```

So the numbers **are** the right ones — 12% retail, 20% consumer, exactly what
the spec said EIB-121 carries. They are recorded wrongly anyway:

- **They are two sequential stages, stored as one band.** `lo=12, mode=20` reads
  as "somewhere between 12% and 20%". The truth is 12% at retail **and then** 20%
  at consumer, which compound to 1 − (0.88 × 0.80) = **29.6%**. As a band this
  understates the chain; as two stages it is a `loss_stage` pair. The gate cannot
  see the difference — both numbers are in the quote, so `band_in_quote` is
  satisfied.
- **The basis is calories**, per that header. batch-09's review already flagged
  that LAFA's percentages are believed to carry across bases but that the
  equivalence "should be confirmed against the quantity table before the figure
  ships". It still has not been.
- Nothing came back on the **2% farm shrink** (trap 2), so the most important
  warning in the spec — that a price-classification allowance under 7 CFR
  1000.43(b) must never become a loss factor — is, like trap 3, untested rather
  than survived.

The spec predicted this row exactly: *"The ERS figures are table cells, not
sentences. A verbatim-quote gate will struggle. Expect this item to need a
human."* batch-09 predicted it too, and named the rule that follows from it:

> **A figure whose basis cannot be read off its own quote is not usable, however
> well it verifies.** That is the source-verify rule, and it needs to become a
> gate check or a standing instruction, not a note in one spec.

It has now cost two batches. `"Fluid milk 109 13 12 22 20 35 32"` is the second
verbatim, correctly-located, entirely unreadable quote to pass every check. On
this evidence the rule should stop being advice.

## 3. What this says about the subject, separately from the pipeline

Worth stating plainly, because it is easy to read this run as "milk is thin". It
is not — milk is the best-documented subject in the corpus. What failed is
retrieval and extraction, on documents that demonstrably contain the answers:

- Item 1's NASS *Milk Production* release fetched and extracted cleanly at
  74,500 chars. Nothing was returned from it.
- Item 5's AMS Class III worksheet fetched at 2,039 chars — small enough to be a
  single chunk, certainly in front of the model. Nothing was returned.
- Item 7's FDA residue database fetched at 44,323 chars. Nothing was returned.

Call rates were **1/14 and 5/14**, consistent with qwen's known conservatism
(2/10 on maple, 3/14 on honey, 0/8 on own-loss-factors) rather than with a new
fault. This remains the pipeline's dominant cost: the documents are right, the
chunks are in front of the models, and the models decline.

The three traps the spec was written around — no per-day ceiling, the 2% shrink,
mean vs midpoint — were **not** disproved by this run. Two of them were never
reached, and the third (the ceiling) was engaged from the wrong side: the record
came back, the absence did not.

## 4. Recommendation

**Promote nothing.** No `data/taxonomy_milk.yaml`, no `data/mixing_milk.yaml`,
no `data/loss_chain_milk.yaml`, no new source slugs, no tests. Milk stays out of
the corpus.

Before a re-run, in this order:

1. **Fix the scout** so it runs on COOPER and rejects implausibly short bodies.
   Until then the spec's pre-flight is checking the wrong machine, and PMC will
   fail silently again.
2. **Replace or supplement the PMC URL.** Gross 2023 is open-access and mirrored;
   a host COOPER can read is needed before items 2 and 3 mean anything.
3. **Decide the basis-legibility rule** from batch-09 — as a gate check or a
   standing prompt instruction. It has now cost two batches and is the only
   failure class in this run that a machine could plausibly catch.
4. **Split item 6** into two fields, retail and consumer, so a two-stage figure
   cannot be returned as one band.

The one thing that would be safe to do by hand today is item 4's national herd
total, which is a clean sentence in a NASS Census highlights PDF. It is
deliberately **not** being done here: one figure does not make a subject, and
promoting the single easiest row out of a failed run is how a subject ends up in
the corpus represented by whatever happened to survive.

## 5. What the run cost and bought

Nothing shipped. What it produced: **the scout's central assumption falsified
with a measurement**, a second instance of the basis-stripping failure class
strong enough to justify making the rule mechanical, and a fully documented
demonstration that the `max_units_per_day` trap is real — COOPER walked into it
on the first attempt, at 2/2 consensus, with a perfectly good quote.

The pipeline is still getting more trustworthy while shipping nothing. That is
the right order, and milk is worth coming back to.
