# batch-07-maple — human review record

Run on COOPER 2026-07-30. `verify` **PASSED**: 5 figures, every quote matched
character-for-character in the returned document, no row claimed a human-only
grade, and the trial build + audit came back clean. This file is the durable
record because `docs/research/outbox/` and `inbox/` are gitignored.

**Outcome: 5 figures returned and verified, 1 at 2/2 consensus, 4 resting on a
single model and flagged `needs_human`. Nothing is in the corpus yet.**

## What COOPER returned

| Field | Value | Agreement | Note |
|---|---|---|---|
| `sap_to_syrup_ratio` | 40 gal sap : 1 gal syrup | **2/2** | the only consensus row |
| `sap_sugar_content` | 2% (range 1–5) | 1/1 | qwen returned nothing |
| `sap_per_tap_per_season` | 20 (lo 10) gal/tap | 1/2 disagree | 20 vs None |
| `taps_per_tree` | 2 (lo 1) | 1/1 | qwen returned nothing |
| `season_length` | **no number** | 1/1 | quote present, value null |

Call rates: qwen2.5-coder:7b answered 2 of 10, gemma4-32k 5 of 10. Consistent
with qwen's known conservatism (3 of 14 on honey) rather than a new problem.

## Three things a human has to decide

**1. `season_length` returned a quote but no number, and that is correct.**
The UMaine source gives calendar windows — "from mid-February to early April in
Southern Maine and mid-March to late April in Northern Maine" — not a duration.
Turning that into "~6 weeks" is *our* arithmetic, not the source's, and the
batch spec asked for the period the `recurring` rate is measured over. Either
store the windows verbatim and derive nothing, or find a source that states a
duration. Do not quietly subtract two dates and call it measured — this is the
saffron teaspoon-to-gram situation again.

**2. Two live conflicts, recorded rather than resolved.**

| Figure | Source | Value |
|---|---|---|
| sap : syrup | NY State Maple | "approximately 40 gallons" |
| sap : syrup | UVM, Jones Rule of 86 | 43:1 at 2°Brix |
| gal/tap/season | NY State Maple | 10–20 |
| gal/tap/season | UMaine 7036e | 5–15 |

The sap:syrup pair is not really a disagreement — 86 ÷ 2 = 43, and "about 40"
is the rounded folk form of the same rule. Worth storing the *rule* rather than
the constant, because the constant is only true at 2°Brix. The gal/tap pair is
a genuine regional spread and should stay a range, not an average.

**3. The strongest source contributed nothing — and it is NOT a retrieval bug.**
*(Corrected 2026-07-30, after checking. The commit message and PR #16 for this
run said the Rule-of-86 passage "may never have been retrieved." That was wrong,
and this is the durable record, so the correction belongs here.)*

Every row except `season_length` came off the NY State Maple page; the UVM
Rule-of-86 PDF produced nothing. The first guess was thin chunking — 4 chunks
across ~30k chars. Checking it kills that theory:

- The UVM PDF is 7,042 chars, so at `CHUNK_CHARS = 12000` it is exactly **one**
  chunk, never split and never truncated.
- `sap_to_syrup_ratio` lists exactly two URLs, so `allowed` was 2 chunks and
  `best_chunks(..., k=2)` returned **both**. The UVM chunk was in front of the
  model.
- The text is demonstrably there: the fetched document carries "one divides 86
  by the sugar content of sap" and "an average sap sugar concentration of
  2°Brix".

So both models saw the rule and quoted the folk constant anyway. That is a model
preference, not a pipeline fault, and it is worth knowing that the gate cannot
catch it: 40 is not *wrong*, it is the rounded form, and the UVM document itself
says "a sap:syrup ratio of close to 40:1" a sentence later.

**The consequence for promotion:** the accepted quote cites the weaker source
for a figure the stronger source both states and *explains*. If this row goes
into the corpus, cite UVM and store the rule (86 ÷ °Brix) with its 2°Brix basis,
not NY State Maple's bare 40 — otherwise the corpus records a constant that is
only true at one sugar concentration, which is precisely what the batch spec
said to avoid.

## Portability fixes this run required

`verify` could not complete on COOPER (Windows) for two reasons unrelated to
the data. Both are fixed:

- `build.py` opened YAML and `schema.sql` without an explicit encoding, so
  Windows used cp1252 and died on the `℉` and en dashes in the quotes. YAML is
  UTF-8 by spec; the read is now explicit and correct on every platform.
- `trial_build()` computed the audit verdict *inside* a `TemporaryDirectory`
  block, so a Windows teardown failure on `trial.db` discarded a result already
  correctly arrived at. Now `ignore_cleanup_errors=True`.

Neither touches what the gate checks. The citation rule is unchanged.

## Not done

These figures are **not** in `data/`. Promoting them means choosing the schema
shape, adding the sources to `data/sources.yaml`, setting confidence
deliberately (COOPER cannot exceed `industry`), and running build + audit +
pytest on a Python 3.12 venv. All of that is a human's call.
