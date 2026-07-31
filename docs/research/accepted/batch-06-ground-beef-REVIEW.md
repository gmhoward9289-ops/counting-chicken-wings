# batch-06-ground-beef — human review record

Second attempt, run on COOPER 2026-07-31. `verify` **PASSED**: 9 items sent, 7
figures returned, every quote matched character-for-character in the returned
document, no row claimed a human-only grade, and the trial build + audit came
back clean.

**This file replaces a NEGATIVE RESULT.** The first run (2026-07-30) failed
`verify` with nothing accepted. That record is not deleted so much as answered —
each of its three failure modes is named below with what was actually done about
it, because two of them could not be fixed by trying harder.

## What the first run got wrong, and what fixed it

**1. `provenance_can_it_be_known` asked a question that could only be answered by
counting.** The quote named Nebraska, Texas, Uruguay and a South Dakota trim
plant; the answer is four; the digit `4` appears nowhere in the text. The gate
refused it — correctly, because counting entities in a sentence is derivation,
and `derived` is a claim only a human may make.

*Fixed by deleting the item.* Not by rewording it. A question whose answer must
be counted out of prose is not an extraction question, and no `Watch for` makes
it one. The Marler Clark / Moss traceback is parked in the spec as a human lead.

**2. `patty_mass_standard` returned 112 g — a laboratory patty-mould size** from
the methods section of the USDA ARS cooking-yields PDF, about one gram from the
real quarter-pound and therefore invisible on review.

*Fixed by removing that document from the batch entirely.* This is the part
worth remembering: `runner.run()` builds its chunk pool across **every document
in the batch** and ranks per item (`allowed = [...] or True`), so a document
cited by one item is reachable by all of them. Dropping the URL from the item
would have changed nothing. The document had to leave the batch.

It worked. This run returned **120.5 g** from the Quarter Pounder definition, at
2/2 consensus.

**3. `cattle_per_patty_typical` flattened "more than 100 cows can be used" into
`100/100/100`.** The spec's `Watch for` named that exact trap and did not stop
it — the second time a spec predicted a failure in writing and the prediction
did not prevent it.

*Fixed by renaming the field to `cattle_per_patty_max`* and telling the model to
leave `value_lo` null. The reasoning: **a field name travels with the row into
the corpus and a warning does not.** In the event, neither model returned a
figure for it at all, so the corporate "100+" number is not in this batch. That
is a better outcome than storing it wrong, and the item stays in the spec.

## The blocker that started this: solved

`fsis.usda.gov` still returns HTTP 403 to `fetch_once()` site-wide — re-confirmed
2026-07-31. The lot/commingling question is no longer blocked by it, because the
FSIS draft risk assessment is **quoted at length by the National Academies'
review of it**, which sits on NCBI Bookshelf and fetches cleanly:

| What was wanted | Where it actually lives |
|---|---|
| lot / combo bin definition | NRC 2002, *E. coli O157:H7 in Ground Beef: Review of a Draft Risk Assessment* — NBK221092, NBK221105 |
| animals per grind batch | Hu et al., *PLoS ONE* 7(3):e34191 (2012), via PMC |
| ground beef lb per animal | SDSU Extension, "How Much Meat Can You Expect from a Fed Steer?" |

The general lesson, and it is not specific to FSIS: **when an agency document is
unfetchable, look for the body that reviewed it.** Oversight literature quotes
the thing it reviews, and oversight publishers host differently.

## Cross-host check, prompted by batch-05-milk (`967d31e`)

L1 established that `scout()`'s docstring is wrong where it claims reachability
"is a property of the fetcher and its user agent, not of the host running it".
PMC served 41,579 chars to the Mac and a 167-char reCAPTCHA page to COOPER for
the same URL minutes apart, and the scout logged the CAPTCHA as a successful
fetch. That is worse than a 403, which at least fails loudly.

This batch leans on PMC for its single most important figure, so the claim was
checked rather than assumed. **Every one of the seven documents is identical
between the Mac scout and COOPER's own fetch** — same character counts, and
equal SHA-256 over whitespace-normalised text:

| chars | document |
|---|---|
| 82,331 | PMC3316629 (Hu et al.) |
| 60,421 | NBK221092 |
| 37,709 | NBK221105 |
| 21,108 | MSU Extension |
| 19,661 | Wikipedia |
| 9,840 | SDSU Extension |
| 6,127 | Food Republic |

So no figure here rests on a document COOPER could not see. The comparison was
free, because `runner.py` fetches on COOPER anyway and leaves the artifacts in
`inbox/` — the scout's copies are still in `inbox/_scout-*`, so any batch can be
checked this way after the fact.

**The uncomfortable part is that PMC served COOPER cleanly here and did not for
L1.** The wall is per-request, not per-host and not per-site, which means a
single passing fetch is not a property of the source you can rely on next time.
The check has to be redone per run. It cannot be inferred from this one.

## The second trap, and where it was caught

L1 also flagged the failure that has now cost three batches: a **figure whose
basis cannot be read off its own quote** — batch-09's `"Eggs, 5.1, 1.3%"` (a
share of total food loss read as a loss rate, wrong by twenty-fold), batch-05's
`"Fluid milk 109 13 12 22 20 35 32"` (a table row severed from its header), and
this batch's own `100/100/100` last run. All verbatim, all correctly located,
all meaningless.

Two rows in this run had the same shape and were caught **before** promotion
rather than after — see the corrections above:

- `combo_bin_mass` came back as `"(60 pounds versus 2,000 pounds)"`. Nothing in
  it says which figure is the bin.
- `ground_beef_lbs_per_steer` came back as `"150 -185"`. No unit, no subject, no
  per-animal basis.

Both were widened to full sentences from the same documents. The rule this
run adopts, stated so it survives: **if a quote is a bare table row, a
parenthetical, or a number without the words that give it its basis, reject it
regardless of what the gate says.** `quote_looks_truncated` catches some of
these and not others — it tests the last character, so a fragment ending in `)`
reads to it as a complete sentence.

## What COOPER returned

| Field | Value | Agreement | Grade |
|---|---|---|---|
| `patty_mass_standard` | 120.5 g | **2/2** | industry |
| `packaged_beef_fraction_of_live_weight` | 40% of live weight | **2/2** | industry |
| `dressing_percentage` | 60–64%, mode 62 | 1/2 disagree | industry |
| `animals_per_grind_batch` | **411–1,367 animals** | 1/1 | industry |
| `combo_bins_per_grinder_load` | 2–15 bins | 1/1 | estimate |
| `combo_bin_mass` | 2,000 lb | 1/1 | industry |
| `ground_beef_lbs_per_steer` | 150–185 lb | **2/2** | industry |
| `cattle_per_patty_max` | — | — | no figure returned |
| `truckloads_per_lot` | — | — | no figure returned |

Call rates: qwen2.5-coder:7b 4 of 18, gemma4-32k 8 of 18. Consistent with qwen's
known conservatism, not a new problem.

## Three quotes corrected by hand, and exactly what was changed

Values were **not** touched. Only quote text, and only to the literal text of the
document already in `inbox/`. Each is recorded in a comment in
`batch-06-ground-beef-findings.yaml` beside the row.

- **`patty_mass_standard` — the only row that failed the gate.** The Wikipedia
  text reads "one quarter of a pound , originally" with a space before the comma;
  the model tidied it. `normalise()` folds whitespace and typography but not
  punctuation, so a genuinely correct quote failed `quote_in_document`. Restored
  to the document's literal text. This is a transcription artifact, and it is the
  gate working: a rejected true quote costs a minute, an accepted false one costs
  the corpus.
- **`combo_bin_mass`** came back as the parenthetical "(60 pounds versus 2,000
  pounds)". Verbatim, right number, and **unreviewable** — nothing in it says
  which figure is the bin. Widened to the sentence in the same document that
  states it outright. This is the 112 g failure mode caught *before* promotion.
- **`ground_beef_lbs_per_steer`** came back as the bare span "150 -185", which
  proves nothing: no unit, no subject, no per-animal basis. Widened to the full
  sentence. The odd space before the dash is the document's own typography and is
  preserved deliberately — tidying it is what broke the patty row.

`quote_looks_truncated` flagged the third of these and not the second, which is
worth knowing: it tests the last character, so a fragment ending in `)` reads as
a complete sentence. **A short verbatim quote is not the same as a checkable
one**, and no arithmetic check reaches that distinction.

## The number that matters, and what it is not

`animals_per_grind_batch = 411–1,367` is the strongest figure this project has
found outside the poultry corpus, and the only *measured* animal count in the
whole subject: Hu et al. profiled DNA markers in six commercial grind batches and
estimated abundance by mark-recapture. It is the first hard evidence that the
pool is real and large rather than asserted.

Four things it is **not**, all of which are easy to get wrong:

1. **Not a per-patty count.** A grind batch is compounded from several combo
   bins. A patty is a sample from it.
2. **Not a per-lot or per-bin count.** A "lot" in the FSIS model is *the cattle
   needed to fill one combo bin*; a grinder load is 2–15 bins.
3. **Not a national figure.** Six batches, one manufacturer, one production line,
   one shift. The paper's own point is the **variance** between batches, not the
   mean.
4. **Not `industry`, and not COOPER's to grade.** COOPER graded it `industry`
   because it cannot grade higher. It is promoted to `study` by hand in
   `data/sources.yaml`, on the narrow ground that 411–1,367 is the paper's own
   primary result rather than uncited scene-setting — the distinction the honey
   batch turned on. The same paper's "may consist of many hundreds of animals"
   sentence **is** scene-setting and is deliberately not used as a figure.

## The corporate "100+ cows" figure is absent, and that is fine

Both models declined `cattle_per_patty_max`. The Food Republic / McDonald's
"more than 100 cows can be used" sentence is therefore not in the corpus at all,
where last run it was in as a point value. Nothing is lost: it is a hedged
ceiling in trade press quoting a corporate statement, and the measured 411–1,367
is a stronger claim about the same phenomenon from a source that counted.

They are also **not the same quantity** — one is a hamburger, one is a batch —
and the corpus records both framings without reconciling them.

## What went into the corpus

See `data/taxonomy_ground_beef.yaml`, `data/mixing_ground_beef.yaml`,
`data/loss_chain_ground_beef.yaml`, and `tests/test_ground_beef.py`.

The structural claim the subject exists to test: **a patty has no anatomical
floor.** `is_anatomical_constant: 0`, and the floor is 1 — one animal, ground at
home, exactly as `whole_bird_home` is the one route where a wing count can touch
its floor. Everything above 1 is commingling and nothing else, which is why this
is the purest test of the mixing engine in the project.

## Leads not taken

- Northeastern University news (2024) quotes food-policy professor Darin
  Detwiler at "up to 400 heads of cattle being mixed together". Fetchable and
  verified, but it is a quoted expert claim in a press release and another hedged
  ceiling of exactly the shape that produced last run's worst row. Not used.
- McDonald's own product page carries "*Weight before cooking 4 oz." Fetchable,
  but the quote is four words and unreviewable on its face.
- Oklahoma State and Missouri extension both return **HTTP 403** to
  `fetch_once()`, like FSIS. Do not spend a run on them.
- The MSU Extension bulletin E3228 PDFs fetch but defeat text extraction.
