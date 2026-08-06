# Batch 08 — silk

> **RE-SCOUTED 2026-07-31 with `scout`, after two failed runs.** Every quote
> below was confirmed present in what **this project's own fetcher** retrieves —
> not in what a browser renders. That distinction is what killed the first two
> runs and it is now the only standard this spec accepts.
>
> Three cautions:
> (1) the per-garment counts rest on craft/education/museum pages with **no
> survey** behind them — grade `industry`/`estimate` and say so;
> (2) sourced filament length is **300–900 m**, lower than commonly-repeated
> "1,000–1,600 m" — use the sourced figure, in **metres**, and note the spread;
> (3) `cocoons_per_worm` has been **removed from this batch** — see
> "Withdrawn from COOPER" at the end. It is not a COOPER item.
>
> **Changes since the 2026-07-30 spec:**
> - `cocoons_per_tie`: bows-n-ties **dropped**. Its article body is truncated by
>   JavaScript and the fetch ends mid-word at "The average wor"; it contains
>   neither 120 nor 130. Two fetchable replacements substituted, and they
>   disagree — report that, do not resolve it.
> - `cocoons_per_shirt`: the quote in the old spec was a **paraphrase** and
>   appeared in no document. Corrected to the page's actual words.
> - `cocoons_per_worm`: withdrawn (below).

**Archetype:** `how-many`

**Question in one sentence:** If you have one silk tie (or shirt, or dress), how
many silkworms does it represent?

**Expected confidence ceiling:** `industry`, leaning `estimate` for per-garment
counts. The cocoons-per-garment figures are trade lore; that softness must be
labelled, not laundered.

---

## Why this subject

Honest framing: this **adds rows and a garment-level product** more than it
advances the model. Its two genuine contributions: a second near-anatomical
constant (**one cocoon per silkworm**, the analog of two wings), and a product
granularity the corpus has not tried — measured in **garments** (tie, shirt),
not pieces or mass. It also carries a small, honest mixing step (reeling combines
~5 cocoons into one thread) that is real but does not dominate the count — a
clean contrast with ground beef where mixing is everything. And it has a striking
fact-card line: the pupa is killed inside the cocoon so the single-filament count
stays exact.

`is_anatomical_constant: 1` for cocoons-per-worm; the per-garment figures are
NOT constants and must not be graded as if they were.

---

## Items

### Item 1 — filament_length_per_cocoon

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | metres of filament per cocoon |
| `archetype` | `how-many` |

**Question:** How long is the silk filament from a single cocoon?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.newworldencyclopedia.org/entry/Silkworm — Quote: "The cocoon of the
  domesticated silkworm is made of a single continuous thread of raw silk from
  300 to 900 meters (1000 to 3000 feet) long."

**Done means:** a length with the quote. Record the sourced **300–900 m**, not
the folk "1,000–1,600 m"; note the spread as a conflict if a second source gives
the higher range.

**Watch for:** total filament vs usable reelable length — this subject's
fresh-vs-cured trap. State which the source means (NEW says the whole thread).
**The unit is METRES.** The quote gives the same length twice, "300 to 900
meters (1000 to 3000 feet)"; those are one measurement in two units, not a
range from 300 to 3000. Report `value_lo: 300`, `value_hi: 900`,
`unit: metres of filament per cocoon`. The previous run returned the *feet*
pair and then invented a third number, `hi: 9000`, that appears in no silk
document anywhere. Do not compute, extrapolate or round a bound: `value_lo` and
`value_hi` must each be a number you can see inside the sentence you quoted.

---

### Item 2 — cocoons_per_pound_raw_silk

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | cocoons per pound of raw silk (→ per-cocoon mass) |
| `archetype` | `how-many` |

**Question:** How many cocoons make one pound of raw silk?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.newworldencyclopedia.org/entry/Silkworm — Quote: "About 2,000 to
  3,000 cocoons are required to make a pound of silk." (→ ~0.15–0.23 g raw silk
  per cocoon.)

**Done means:** the cocoons-per-pound figure with the quote; the per-cocoon mass
is a human `derived` step, not COOPER's to assert.

**Watch for:** cocoons-per-pound of **raw reeled silk** vs of finished fabric —
different denominators.

---

### Item 3 — cocoons_per_tie

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: industry` |
| `unit` | cocoons per silk necktie |
| `archetype` | `how-many` |

**Question:** How many cocoons go into one silk necktie?

**Candidate URLs (re-scouted 2026-07-31; quotes confirmed present in what this
project's fetcher retrieves, not merely in a browser):**

- https://afbeducation.org/silkworm-eggs/ — Quote: "Depending on the thread
  count it would take about 120 to 130 cocoons or the equivalent of 180,000 –
  325,000 feet of silk thread to produce a single necktie."
- https://festival.si.edu/2002/the-silk-road/the-silk-road-connecting-peoples-and-cultures/smithsonian
  — Quote: "about 150 cocoons are needed for a necktie."

**Done means:** a count with **one** verbatim quote from **one** of these two
pages. Prefer the AFB sentence, because it states a range (120–130) inside a
single sentence and so supports `value_lo` and `value_hi` honestly. Ship
flagged `industry`.

**Watch for:** **the two sources disagree — 120–130 against 150 — and you must
NOT resolve it.** Do not average them, and above all do not build a band out of
two different documents: `value_lo` and `value_hi` have to come from the *same*
sentence you quote, or the row is a splice of two sources wearing one citation.
Answer from one page, then say in `notes:` that the other gives a different
figure. Also: tie vs scarf vs "square" are different garments with different
masses — the AFB page's other numbers (180,000–325,000 feet) are thread length,
not a cocoon count, so do not let them into a value field.

---

### Item 4 — cocoons_per_shirt

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: industry` |
| `unit` | cocoons per silk shirt/blouse |
| `archetype` | `how-many` |

**Question:** How many cocoons go into one silk shirt?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.suekayton.com/Silkworms/cloth.htm — education page. Quote:
  "or about 1,000 cocoons for a silk shirt".

**Done means:** `value_lo`, `value_mode` and `value_hi` all **1000**, with that
quote. The page gives the shirt exactly one number and no range.

**Watch for:** **this is the trap that beat the last run, and it beat it because
every number involved really is in the quote.** The full sentence reads "It
takes 1700 to 2000 cocoons to make one silk dress (or about 1,000 cocoons for a
silk shirt)." — it answers **two** questions at once. 1700 and 2000 are the
**dress**. 1,000 is the **shirt**, and the shirt is what this item asks about.
The previous run stored 1700/1800/2000 here and no automatic check could catch
it, because those figures are genuinely in the sentence; they are simply about
the other garment. Read the clause your number sits in, not just the sentence.
If you return anything other than 1000 for a shirt you have answered the wrong
question.

---

### Item 5 — cocoons_per_dress

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: industry` |
| `unit` | cocoons per silk dress |
| `archetype` | `how-many` |

**Question:** How many cocoons go into one silk dress?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.suekayton.com/Silkworms/cloth.htm — Quote: "It takes 1700 to 2000
  cocoons to make one silk dress."

**Done means:** the count (~1,700–2,000) with the quote.

**Watch for:** dress vs kimono (~9,000) — very different garments; do not blur.
The same sentence also carries the **shirt** figure (~1,000) in a trailing
parenthesis; that one belongs to the previous item, not this one. Here the
answer is the 1700–2000 pair.

---

### Item 6 — reeling_cocoons_per_thread

| | |
|---|---|
| `target_table` | `loss_factor` (mixing step) |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | cocoons combined into one reeled thread |
| `archetype` | `how-many` |

**Question:** How many cocoons are reeled together to form one silk thread?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.suekayton.com/Silkworms/cloth.htm — Quote: "a machine unrolls the
  cocoon, winding the silk from five cocoons together to make one silk thread."

**Done means:** the count (~5) with the quote — the one small mixing step,
recorded as such, shown NOT to dominate the garment count.

**Watch for:** this is real mixing but minor; do not inflate it into a wing-style
cascade.

---

## Conflicts to report, not resolve

| Figure | Source | Year | Definition used |
|---|---|---|---|
| filament length | New World Encyclopedia | — | 300–900 m (vs folk 1,000–1,600) |
| cocoons per necktie | AFB Education | — | 120–130 |
| cocoons per necktie | Smithsonian Folklife Festival | 2002 | 150 |
| cocoons/garment | craft/education/museum pages | — | vary widely, no survey |

## What to explicitly NOT do

- Do not grade per-garment counts above `industry`; prefer `estimate` where the
  only source is a craft/education page. No survey exists.
- Do not claim `study` for a sericulture journal figure — the README `study`
  withdrawal applies; a human promotes.
- Do not merge *Bombyx mori* with wild/tussah/eri silk.
- Do not silently upgrade the sourced 300–900 m filament to the folk higher range.
- Do not answer `cocoons_per_worm`. It is not an item in this batch.
- Do not build a lo/hi band out of two different documents. A band is one
  source's claim, so both bounds live in the one sentence you quote.

## Acceptance

- [ ] Every row carries a verbatim quote in a returned document
- [ ] No row claims `measured`/`derived`/`study`
- [ ] Per-garment figures graded `industry`/`estimate` with the softness noted
- [ ] Filament length uses the sourced 300–900 m **in metres**, spread noted
- [ ] Shirt = 1000; the 1700/2000 pair belongs to the dress
- [ ] Necktie answered from one page, with the other's figure reported as a conflict
- [ ] New sources in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check

## Withdrawn from COOPER — cocoons_per_worm

**This is deliberately not an item, and its heading deliberately does not begin
`### Item`, so the parser will not pick it up.** Its URL is written inline
rather than as a list bullet for the same reason: a bulleted URL under a
non-item heading is still swept into the preceding item's URL list.

One cocoon per silkworm is the anatomical constant this whole subject rests on,
and it is the one figure COOPER cannot return. Both models declined it twice,
and **they were right to**. The gate requires the figure to appear in the quoted
sentence, and no fetchable source states it as a number. Sericulture writers
treat it as too obvious to count: they write "the larvae enclose themselves in a
cocoon", which contains no number word at all, so an honest answer of `1` could
never ground against it.

A 35-URL sweep on 2026-07-31 — FAO, Wikipedia, Britannica, Saint Louis Zoo,
Carolina Biological, extension PDFs — found exactly one page that states the
one-to-one relation in a single fetchable sentence, PubMed 38061509
(`https://pubmed.ncbi.nlm.nih.gov/38061509/`):

> A normal silkworm cocoon (NSC) with a unique nonwoven structure is usually
> spun by a single silkworm larva.

That says "a single silkworm larva", not "one cocoon", so the number `1` is in
the *meaning* and not in the *characters* — `value_in_quote` would reject it,
correctly, since it does not know that "single" is a number word here.

Reading `1` out of that sentence is a human judgement about what a source means,
which is precisely the class of call the README reserves for a human. So it is
recorded as one, by a human, in the review record — not laundered through COOPER
by renaming the field to one the band check does not read. Note also that the
same abstract supplies the exception: a *multi-silkworm cocoon* strain in which
three or more larvae spin one cocoon collectively, which is why the honest
grade here is not `measured` and the constant carries a caveat.
