# Batch 09 — our own unsourced loss factors

**Archetype:** `provenance-audit` + `how-many`

**Question in one sentence:** Can the four estimate-grade loss factors that are
live in our published answer be replaced with cited figures?

**Expected confidence ceiling:** item by item. One can probably reach
`measured`; two are likely to end as documented absences.

---

## Why this batch, and why it comes before more subjects

Every other batch so far has widened the corpus. This one repairs it.

`audit.py` currently reports **11 of 21 loss factors resting on unsourced
estimates (52%)**, and four of those are **enabled by default**, which means
they are shaping the number on the front page right now:

| stage | applies to | current mode | loss |
|---|---|---|---|
| `transport_doa` | all broiler products | 0.996 | 0.40% |
| `grading_downgrade` | whole wing | 0.980 | 2.00% |
| `transit_rejection` | boneless wing | 0.995 | 0.50% |
| `egg_kitchen_breakage` | table egg | 0.990 | 1.00% |

Their source is `project-estimate-unsourced` — us. For a project whose whole
claim is that every number traces to a real source, this is the largest
outstanding gap, and it sits in the flagship subject rather than in a novelty
one. The research pipeline was built, proved on saffron, and debugged on honey,
and it has never once been pointed at this.

**Two more unsourced factors are deliberately excluded**: `saffron_field_loss`
and `layer_mortality` are both `default_enabled: 0`, so they do not move the
published answer. Off-by-default is already the honest handling of an
unsourced figure; leave them.

---

## Scouting already done — read before queueing

**18 candidate URLs were verified before this spec was written. 10 are
readable, 8 are dead.** The dead ones are listed so nobody spends the hour
again.

| Host | Result |
|---|---|
| `fsis.usda.gov` | **403 wholesale**, and NOT User-Agent fixable — tested with both a browser UA and the runner's own. FSIS's condemnation data sets are the obvious primary source for item 1 and cannot be fetched at all. |
| `ams.usda.gov/grades-standards/poultry-*` | **404, as ~40 KB soft-404 shells.** Three separate paths. A status-only check would have called these hits. |
| `sciencedirect.com` | 403, returning 832 KB of block page — big enough to look like a document. |
| `mdpi.com` | 403 |
| `ers.usda.gov/.../meatpoultfish.xlsx` | 404 — path guessed wrong; the egg file at the sibling path works |

**The decisive negative: the phrase "dead on arrival" appears in ZERO of the
ten readable documents.** Not in NASS Poultry Slaughter, not in 9 CFR 381, not
in the eCFR text. That is a finding, not a search failure — see item 1.

---

## Items

### Item 1 — transport_doa

| | |
|---|---|
| `target_table` | `loss_factor` (stage `transport_doa`) |
| `unit` | fraction of birds, or birds per thousand, **as stated** |
| `archetype` | `provenance-audit` |
| `expected outcome` | **likely a documented absence** |

**Question:** Does any fetchable US source state a rate for broilers that die
between catching and the plant?

**Candidate URLs:**

- https://www.nass.usda.gov/Publications/Todays_Reports/reports/pslaan26.pdf — NASS Poultry Slaughter 2025 Summary. **Verified:** 1.3 MB PDF, `condemned` ×33, `ante-mortem` ×4. **Does NOT contain "dead on arrival".**
- https://www.govinfo.gov/content/pkg/CFR-2024-title9-vol2/pdf/CFR-2024-title9-vol2-part381.pdf — 9 CFR 381. **Verified:** 805 KB, `condemned` ×60, `transport` ×63. Defines the categories; states no rates.
- https://www.ecfr.gov/current/title-9/chapter-III/subchapter-A/part-381 — same regulation as HTML, `condemned` ×82. **Note:** eCFR was bot-walled in an earlier batch's scouting and returned 1.4 MB of real text here, so the block is path-specific rather than domain-wide.

**Done means:** either a cited DOA rate, or a plain statement that none of these
documents carries one.

**THE TRAP, and it is the whole reason this item is a provenance audit:**
**ante-mortem condemnation is NOT dead-on-arrival.** A DOA bird died in
transit. An ante-mortem condemned bird was *alive at inspection* and rejected.
NASS publishes the second and not the first, and they are different populations
with different causes.

Substituting one for the other would produce a real number, with a real USDA
citation, answering a different question — precisely the failure that
`unit_matches_field` was added for after saffron. **Do not report an
ante-mortem figure under this field.** If ante-mortem is what a document
states, report it as `ante_mortem_condemnation` and let a human decide whether
it belongs anywhere.

---

### Item 2 — grading_downgrade

| | |
|---|---|
| `target_table` | `loss_factor` (stage `grading_downgrade`) |
| `unit` | fraction of wings downgraded, **as stated** |
| `archetype` | `provenance-audit` |
| `expected outcome` | **grading framework yes, occurrence rate probably not** |

**Question:** Does USDA publish a rate at which wings are pulled from the
primary pack for size, colour or trim defects?

**Candidate URLs:**

- https://www.govinfo.gov/content/pkg/CFR-2024-title7-vol3/pdf/CFR-2024-title7-vol3-part70.pdf — 7 CFR 70, poultry grading. **Verified:** 262 KB, `grade` ×186, and **`tolerance` appears zero times.**
- https://www.govinfo.gov/content/pkg/CFR-2024-title9-vol2/pdf/CFR-2024-title9-vol2-part381.pdf — 9 CFR 381. **Verified:** `tolerance` ×21, `wings` ×8.
- https://www.govinfo.gov/content/pkg/CFR-2024-title9-vol2/pdf/CFR-2024-title9-vol2-sec381-90.pdf — 9 CFR 381.90, condemnation specifically. **Verified:** `condemned` ×11.

**Done means:** the grading categories and any stated tolerance, with the
tolerance-versus-rate distinction recorded explicitly.

**Watch for — the same trap the egg corpus already documented:** a **tolerance
is a ceiling a pack must stay under, not a measured occurrence rate.** The
project already holds `ams-shell-egg-grades` on exactly those terms, graded
`industry` and flagged as an upper bound. Any tolerance found here inherits
that treatment: it bounds the loss, it does not measure it. A pack running at
tolerance would be barely passing.

The AMS web pages that would carry actual grading practice are 404 and were not
replaced — so if this item ends as "the regulation defines grades and nobody
publishes a downgrade rate", that is the answer.

---

### Item 3 — transit_rejection

| | |
|---|---|
| `target_table` | `loss_factor` (stage `transit_rejection`) |
| `unit` | percent lost between plant and kitchen, **as stated** |
| `archetype` | `how-many` |

**Question:** What fraction of poultry is lost between the plant and the
kitchen?

**Candidate URLs:**

- https://ers.usda.gov/sites/default/files/_laserfiche/publications/43833/43680_eib121.pdf — ERS EIB-121. **Verified:** 3.7 MB PDF, extracts cleanly, `poultry` ×28, `eggs` ×14, `retail loss` ×1. **The anchor for this item and item 4.**
- https://www.ers.usda.gov/data-products/food-availability-per-capita-data-system/loss-adjusted-food-availability-documentation — LAFA documentation, `poultry` ×10
- https://www.ers.usda.gov/data-products/food-availability-per-capita-data-system — LAFA landing, `poultry` ×11

**Done means:** the ERS retail and consumer loss percentages for poultry, each
with its stage named.

**Watch for — the reason our current placeholder is deliberately low:** wings
ship **IQF frozen**, and essentially the whole cold-chain loss literature
concerns *fresh or chilled* product. Frozen tolerates transit far better, so a
fresh-meat loss rate borrowed here would overstate it badly. Our existing note
already records that the peer-reviewed cold-chain modelling declines to break
transport out as a stage at all.

So: record whether the ERS figure distinguishes frozen from fresh. **If it does
not, say so** — that is the caveat that has to travel with the number, and
without it this figure cannot honestly replace the placeholder.

---

### Item 4 — egg_kitchen_breakage

| | |
|---|---|
| `target_table` | `loss_factor` (stage `egg_kitchen_breakage`) |
| `unit` | percent of eggs lost at consumer level, **as stated** |
| `archetype` | `how-many` |
| `expected outcome` | **the best prospect in the batch** |

**Question:** What fraction of eggs is lost at the consumer level?

**Candidate URLs:**

- https://ers.usda.gov/sites/default/files/_laserfiche/publications/43833/43680_eib121.pdf — ERS EIB-121, `eggs` ×14. The table carries retail and consumer loss for eggs alongside every other food group.
- https://www.ers.usda.gov/data-products/food-availability-per-capita-data-system/loss-adjusted-food-availability-documentation — LAFA documentation

**Done means:** the consumer-level loss percentage for eggs, and the retail one
separately, because our stage is specifically the *kitchen* and conflating the
two would double-count against `egg_checks`.

**Watch for — three things, and the third is a hard stop:**

1. **These are table cells, not sentences.** A verbatim-quote gate will
   struggle, exactly as the milk scouting predicted. Expect this to need a
   human, or a quote that is a table row.
2. **Vintage.** The underlying ERS estimates are 2010 data on a series last
   refreshed in 2022. Old is not disqualifying; undated is.
3. **The LAFA egg data file is `.xlsx`.** `https://www.ers.usda.gov/sites/default/files/_laserfiche/DataFiles/50472/eggs.xlsx`
   returns 200 and is a real workbook — and the runner has a `pdftotext` path
   with a `pypdf` fallback and **no xlsx path at all**. So the cleanest form of
   this figure is in a format the pipeline cannot read. Take it from the PDF, or
   hand it to a human. Do not add an xlsx reader for one number.

---

## Honest expectation

| Item | Likely outcome |
|---|---|
| 1 `transport_doa` | **documented absence.** FSIS is 403, "dead on arrival" is in none of the readable documents, and the nearest published category answers a different question. |
| 2 `grading_downgrade` | **tolerance at best**, treated as an upper bound like the shell-egg grades. Possibly a documented absence. |
| 3 `transit_rejection` | a real ERS figure, with a frozen-versus-fresh caveat that may weaken it |
| 4 `egg_kitchen_breakage` | **the best prospect** — a real ERS consumer-loss figure |

So the plausible best case is **two of four replaced**, and the two that fail
become properly documented absences instead of silent placeholders. That is
still the highest-value batch available: it moves the audit's headline number
and it removes our own guesswork from the answer people actually read.

If an item ends as an absence, the corpus change is to say so in the stage's
`notes` and consider flipping it `default_enabled: 0` — the same treatment the
saffron field-loss factor already gets. **An unsourced factor that is off is
honest; an unsourced factor that is on and quiet is not.**
