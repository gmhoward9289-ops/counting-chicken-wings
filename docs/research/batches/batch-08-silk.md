# Batch 08 — silk

> **SCOUTED 2026-07-30.** Candidate URLs below were fetched and confirmed 200
> with the figure present on this date. Two cautions carried from the scout:
> (1) the per-garment counts rest on craft/education sites with **no survey**
> behind them — grade `industry`/`estimate` and say so; (2) sourced filament
> length is **300–900 m**, lower than commonly-repeated "1,000–1,600 m" — use the
> sourced figure and note the spread.

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

### Item 1 — cocoons_per_worm

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `units_per_individual_lo/mode/hi`, `is_anatomical_constant` |
| `unit` | cocoons per silkworm |
| `archetype` | `how-many` |

**Question:** How many cocoons does one silkworm spin?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.newworldencyclopedia.org/entry/Silkworm — describes each larva
  enclosing itself in "a cocoon of raw silk" (one per worm through the lifecycle).

**Done means:** the figure **1**, lo = mode = hi = 1, `is_anatomical_constant: 1`,
with a quote. The degenerate constant, like vanilla's one-flower-one-bean.

**Watch for:** the source *implies* one cocoon per worm through the lifecycle
rather than stating "exactly one" — flag it `needs_human` if a stricter phrasing
is wanted. *Bombyx mori* only; do not merge with wild/tussah silk.

---

### Item 2 — filament_length_per_cocoon

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
fresh-vs-cured trap. State which the source means (NWE says the whole thread).

---

### Item 3 — cocoons_per_pound_raw_silk

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

### Item 4 — cocoons_per_tie

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: industry` |
| `unit` | cocoons per silk necktie |
| `archetype` | `how-many` |

**Question:** How many cocoons go into one silk necktie?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.bows-n-ties.com/mens-fashion-tips/how-much-silk-is-needed-to-make-a-necktie/
  — Quote: "a single tie requires about 120 to 130 cocoons."

**Done means:** the count (~120–130) with the quote. Single-source trade lore —
ship flagged `industry`, and note a second source was not found.

**Watch for:** tie vs scarf vs "square" — different garments, different masses.

---

### Item 5 — cocoons_per_shirt

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: industry` |
| `unit` | cocoons per silk shirt/blouse |
| `archetype` | `how-many` |

**Question:** How many cocoons go into one silk shirt?

**Candidate URLs (confirmed 200, 2026-07-30):**

- https://www.suekayton.com/Silkworms/cloth.htm — education page. Quote:
  "it takes about 1000 cocoons to make a silk shirt" (~1,000 cocoons).

**Done means:** the count (~1,000) with the quote.

**Watch for:** the wide spread across sources — keep lo/hi, not a false point.

---

### Item 6 — cocoons_per_dress

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

---

### Item 7 — reeling_cocoons_per_thread

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
| cocoons/garment | craft/education sites | — | vary widely, no survey |

## What to explicitly NOT do

- Do not grade per-garment counts above `industry`; prefer `estimate` where the
  only source is a craft/education page. No survey exists.
- Do not claim `study` for a sericulture journal figure — the README `study`
  withdrawal applies; a human promotes.
- Do not merge *Bombyx mori* with wild/tussah/eri silk.
- Do not silently upgrade the sourced 300–900 m filament to the folk higher range.

## Acceptance

- [ ] Every row carries a verbatim quote in a returned document
- [ ] No row claims `measured`/`derived`/`study`
- [ ] Per-garment figures graded `industry`/`estimate` with the softness noted
- [ ] `cocoons_per_worm` = 1 with `is_anatomical_constant: 1` (flagged if implied)
- [ ] Filament length uses the sourced 300–900 m, spread noted
- [ ] New sources in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check
