# Batch 08 — silk

> **DRAFTED, not runnable yet.** Candidate URLs below are **leads, not yet
> confirmed 200 with the figure present**. Run a URL scout and replace each with
> a fetched-and-confirmed URL before `send`. Silk figures are unusually
> blog-heavy — hold the confirm-200 bar high and prefer a sericulture
> extension/FAO source over craft sites where possible.

**Archetype:** `how-many`

**Question in one sentence:** If you have one silk tie (or shirt, or dress), how
many silkworms does it represent?

**Expected confidence ceiling:** `industry`, and lean toward `estimate` for the
per-garment counts. The cocoons-per-garment figures are widely repeated trade
lore with **no survey behind them** — that softness must be labelled, not
laundered.

---

## Why this subject

Honest framing: this **adds rows and a garment-level product** more than it
advances the model. Its two genuine contributions: a second near-anatomical
constant (**one cocoon per silkworm**, the analog of two wings), and a product
granularity the corpus has not tried — measured in **garments** (tie, shirt),
not pieces or mass. It also carries a small, honest mixing step (reeling
combines ~5 cocoons into one thread) that is real but does not dominate the
count, which is a clean contrast with ground beef where mixing is everything.
And it has a genuinely striking fact-card line: the pupa is killed inside the
cocoon so the single-filament count stays exact — the count is precise
*because* the individual's whole lifetime product must be taken unbroken.

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

**Candidate URLs (unconfirmed leads — scout before send):**

- <FAO/sericulture or university extension page on Bombyx mori lifecycle — confirm>

**Done means:** the figure **1**, lo = mode = hi = 1, `is_anatomical_constant: 1`,
with a quote. The degenerate constant, like vanilla's one-flower-one-bean.

**Watch for:** *Bombyx mori* only — do not merge with wild/tussah silk, a
different species with different yields.

---

### Item 2 — filament_length_per_cocoon

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | metres of filament per cocoon (name total vs reelable) |
| `archetype` | `how-many` |

**Question:** How long is the silk filament from a single cocoon?

**Candidate URLs (unconfirmed leads — scout before send):**

- <sericulture reference / journal on filament length — confirm>

**Done means:** a length with a quote, stating whether it is **total** filament
(~1,000–1,600 m) or **usable reelable** (~600–900 m). They differ and are
routinely conflated.

**Watch for:** total-vs-reelable is this subject's fresh-vs-cured trap.

---

### Item 3 — raw_silk_mass_per_cocoon

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | grams raw silk per cocoon |
| `archetype` | `how-many` |

**Question:** How much raw silk does one cocoon yield?

**Candidate URLs (unconfirmed leads — scout before send):**

- <sericulture yield table — confirm>

**Done means:** a mass (~0.3–0.4 g) with a quote.

**Watch for:** whole cocoon shell weight vs reeled raw-silk weight — different
numbers.

---

### Item 4 — cocoons_per_tie

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: industry` |
| `unit` | cocoons per silk necktie |
| `archetype` | `how-many` |

**Question:** How many cocoons go into one silk necktie?

**Candidate URLs (unconfirmed leads — scout before send):**

- https://www.suekayton.com/Silkworms/cloth.htm — education page (gives dress/shirt counts; confirm tie)
- <a second independent source for the tie figure — required, this is soft lore>

**Done means:** a count (~100–140) with a quote AND a second corroborating
source, or it ships flagged as single-source lore.

**Watch for:** tie vs scarf vs "square" — different garments, different masses.

---

### Item 5 — cocoons_per_shirt

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: industry` |
| `unit` | cocoons per silk shirt/blouse |
| `archetype` | `how-many` |

**Question:** How many cocoons go into one silk shirt or blouse?

**Candidate URLs (unconfirmed leads — scout before send):**

- https://www.suekayton.com/Silkworms/cloth.htm — "~1,000 cocoons to make a shirt"

**Done means:** a count (~630–1,000) with a quote.

**Watch for:** the wide spread across sources — keep it as lo/hi, not a false
point value.

---

### Item 6 — cocoons_per_dress

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `confidence: industry` |
| `unit` | cocoons per silk dress |
| `archetype` | `how-many` |

**Question:** How many cocoons go into one silk dress?

**Candidate URLs (unconfirmed leads — scout before send):**

- https://www.suekayton.com/Silkworms/cloth.htm — "1,700 to 2,000 cocoons to make one silk dress"

**Done means:** a count (~1,700–2,000) with a quote.

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

**Candidate URLs (unconfirmed leads — scout before send):**

- https://www.suekayton.com/Silkworms/cloth.htm — "winding the silk from five cocoons together"

**Done means:** a count (~3–8) with a quote — the one small mixing step, recorded
as such, shown NOT to dominate the garment count.

**Watch for:** this is real mixing but minor; do not inflate it into a wing-style
cascade.

---

## Conflicts to report, not resolve

| Figure | Source | Year | Definition used |
|---|---|---|---|
| cocoons/garment | craft/education sites | — | vary widely, no survey |
| filament length | sericulture refs | — | total vs reelable |

## What to explicitly NOT do

- Do not grade per-garment counts above `industry`; prefer `estimate` if the
  only sources are craft blogs. No survey exists.
- Do not claim `study` for a sericulture journal figure — the README `study`
  withdrawal applies; a human promotes.
- Do not merge *Bombyx mori* with wild/tussah/eri silk.
- Do not conflate total filament length with reelable length.

## Acceptance

- [ ] Every row carries a verbatim quote in a returned document
- [ ] No row claims `measured`/`derived`/`study`
- [ ] Per-garment figures graded `industry`/`estimate` with the softness noted
- [ ] `cocoons_per_worm` = 1 with `is_anatomical_constant: 1`
- [ ] Filament length names total vs reelable on every figure
- [ ] New sources in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check
