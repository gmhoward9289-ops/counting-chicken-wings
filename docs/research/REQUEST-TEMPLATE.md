# Batch NN — <subject>

<!--
Template for a research work-order. Generalised from docs/ISRAEL-PLAN.md, which
already had the right shape: every item states the question, where to look, and
what "done" means, plus an explicit "do NOT do" section.

Copy to batches/batch-NN-<subject>.md and fill in. Delete these comments.

Read docs/research/README.md first -- it holds the contract, and the rules
about which confidence grades COOPER may assign are not negotiable per-batch.
-->

**Archetype:** `how-many` | `comparison`

- **how-many** — "if you have X, how many does it take to produce Y". Needs a
  species, a product, a yield mode, and a floor. The wing model.
- **comparison** — "X over Y". Needs a shared axis, a shared unit, and a shared
  year, or it is not a comparison.

**Question in one sentence:** <the thing a visitor would type>

**Expected confidence ceiling:** <industry | estimate>

State this up front. Chicken had USDA NASS; most subjects do not. If the honest
ceiling is `estimate`, say so here so nobody reads the result with borrowed
credibility from the poultry corpus.

---

## Why this subject

What it teaches, beyond adding rows. The best subjects **break an assumption**:

- boneless wings forced `named_part` apart from `source_part` — the name lied
- eggs forced a time window, because a rate is not a fact until you say per what
- Israel forced a `country` dimension and unit normalisation

If a subject only adds rows, say that honestly — it is still worth doing, but it
should not be dressed up as a model advance.

---

## Items

<!--
One block per figure. 5-8 per batch. Each is independently verifiable, so a
batch can partly pass -- `verify` reports per-row, and `accept` takes only the
rows that passed.
-->

### Item 1 — <field name>

| | |
|---|---|
| `target_table` | `product` \| `loss_factor` \| `quality_defect` \| `nutrition` \| ... |
| `required_fields` | the columns that must come back |
| `unit` | and whether conversion is needed |
| `archetype` | `how-many` \| `comparison` |

**Question:** <precise enough that two people would agree on whether an answer
is correct>

**Candidate URLs:**

- <url> — <why this one, and what it is likely to contain>
- <url>

COOPER fetches these. It does **not** search for others, and it does not decide
one is better than another — it extracts from each and reports what each says.

**Done means:** <the specific condition>. Name the unit and the year. "Found a
number" is not done.

**Watch for:** <the definition trap>. This field exists because it is where
these go wrong. Real examples from work already done:

- *poultry meat* vs *chicken meat*; carcass weight vs retail weight
  (`ISRAEL-PLAN.md`)
- a grading **tolerance** is a ceiling a pack must stay under, not a measured
  rate — treating one as the other overstated egg loss until caught
- per-100g vs per-piece: breading makes a fried wing *less* calorie-dense per
  gram while raising its total calories

---

## Conflicts to report, not resolve

If sources disagree, lay them out and name the likely cause. Do not pick a
winner — that is a human call.

| Figure | Source | Year | Definition used |
|---|---|---|---|
| | | | |

`ISRAEL-PLAN.md` is the worked example: three per-capita figures, one of which
contradicts the intended headline, presented without a verdict.

---

## What to explicitly NOT do

Per-batch additions to the standing rules in `README.md`:

- Do not reuse another subject's loss factors as placeholders without grading
  them `estimate` and labelling the borrowing.
- Do not invent a mixing cascade by analogy. Eggs borrowed the broiler cascade
  and it is wrong in detail — an egg carton is not a combo bin. If the real
  cascade is unknown, say so.
- <subject-specific>

---

## Acceptance

- [ ] Every row carries a quote that appears verbatim in a returned document
- [ ] No row claims `measured` or `derived`
- [ ] New sources are in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check
- [ ] Disagreements between the two models are flagged, not averaged
- [ ] <subject-specific: e.g. the floor derives from an anatomical constant>
