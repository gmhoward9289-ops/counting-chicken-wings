# Batch 01 — saffron

**Archetype:** `how-many`

**Question in one sentence:** How many crocus flowers does it take to make one
gram of saffron?

**Expected confidence ceiling:** `industry`

There is no USDA NASS for saffron. The best available sources are land-grant
university extension publications, which are institutional and careful but not
peer-reviewed journals. So `industry` is the honest ceiling, and COOPER cannot
assign higher anyway. Nothing here should be read with the confidence a NASS
figure earns.

---

## Why this subject

Saffron is not a novelty pick. It is **the closest structural twin to the wing
that exists**, and it is a real test of whether the model generalises.

*Crocus sativus* has **exactly three stigmas per flower.** That is an
anatomical constant of precisely the kind that makes the wing floor a real
floor rather than an average — a chicken has two wings, a crocus has three
stigmas, and no amount of agriculture changes either. If the model is right,
`is_anatomical_constant: 1` should behave identically here.

It also stresses two things wings never did:

- **Two nested units.** A flower yields 3 stigmas; ~150 flowers yield 1 gram.
  So "how many flowers per gram" is a *countable → continuous* chain, where
  wings were countable throughout.
- **`applies_to: mass` in a new domain.** Drying is a huge mass loss — fresh
  stigmas to dried threads — and by the project's own rules it must **not**
  change the flower count. Same discipline that keeps cook loss out of the wing
  count. If that rule holds here, it is a real rule and not a wing-specific
  accident.

---

## Items

### Item 1 — stigmas_per_flower

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `units_per_individual_lo/mode/hi`, `is_anatomical_constant` |
| `unit` | stigmas per flower |
| `archetype` | `how-many` |

**Question:** How many stigmas does a single Crocus sativus flower produce?

**Candidate URLs:**

- https://extension.psu.edu/saffron-a-tale-of-red-gold-and-how-to-produce-your-own — Penn State Extension, land-grant, likely the best-written of the three
- https://www.growables.org/informationVeg/documents/Saffron.pdf — University of Florida IFAS HS661
- https://ucanr.edu/site/uc-master-gardeners-santa-clara-county/saffron — UC Agriculture and Natural Resources

**Done means:** the figure **3**, with lo = mode = hi = 3, and a quote saying so.
This is a constant, not a range. If a source gives a range, that is interesting
and should be reported — but the expected answer is exactly three.

**Watch for:** sources conflating *stigmas* with *stamens*. A crocus has three
stigmas (the female parts, which are the spice) and three stamens (male, which
are not). A quote about stamens is the wrong plant part and must not be
accepted as an answer to this question.

---

### Item 2 — flowers_per_gram_dried

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | flowers per unit mass — **whatever unit the source uses** |
| `archetype` | `how-many` |

**Question:** How many saffron crocus flowers does the document say are needed
to produce a stated quantity of dried saffron? Report the number **and the
quantity it refers to**, in the source's own units.

**Candidate URLs:** as Item 1.

**Done means:** a figure with its own unit attached, whatever that unit is.

**This question was rewritten after the first run returned nothing for it.** The
original asked for "flowers per **gram**". The Penn State page states "4,000
blossoms to yield just one **ounce**" and "50 flowers to produce just one
**teaspoon**" — neither is a gram. The model correctly declined rather than
converting ounces to grams to manufacture an answer, which is exactly the
behaviour the contract asks for. The fault was the question, not the model:
demanding a unit the literature does not use guarantees a miss.

Unit conversion is a separate, checkable step performed after extraction. Do
not fold it into the extraction, or the quote stops matching the number.

For reference, the conversions close: 4,000/oz ÷ 28.35 g = **141 flowers/gram**,
against the ~150 figure quoted elsewhere. Consistent — but that arithmetic is
ours to do and to label `derived`, not COOPER's to assert.

**Watch for:** **fresh versus dried.** This is the trap. Saffron loses most of
its mass drying, so "flowers per gram" means something completely different
depending on which state the gram is in. A figure without the state named is
unusable. Also watch pound-vs-gram: 75,000/lb and 150/g are the *same claim*,
and reporting both as if independent would be double-counting one source.

---

### Item 3 — stigmas_per_pound cross-check

| | |
|---|---|
| `target_table` | *(validation only — no table)* |
| `unit` | stigmas per pound |
| `archetype` | `how-many` |

**Question:** How many individual stigmas are in one pound of saffron?

**Candidate URLs:** as Item 1, plus any that state a per-pound figure.

**Done means:** a figure that can be checked against Items 1 and 2. The
arithmetic should close:

```
75,000 flowers/lb  ×  3 stigmas/flower  =  225,000 stigmas/lb
150 flowers/g      ×  3                 =  450 stigmas/g
225,000 / 454 g                         ≈  495 stigmas/g
```

450 against 495 is a ~10% gap — consistent within rounding, not identical.
**Report the gap, do not reconcile it.** The egg corpus has a fact called "the
egg numbers check out against themselves, twice"; this is the saffron
equivalent, and it is only worth anything if the check is honest about its
residual.

**Watch for:** a source that derived its per-pound figure *from* the per-gram
one. Then it is not an independent check at all, and saying so is the finding.

---

### Item 4 — drying_mass_yield

| | |
|---|---|
| `target_table` | `loss_factor` |
| `required_fields` | `survive_lo/mode/hi`, `applies_to` |
| `unit` | fraction of fresh mass retained |
| `archetype` | `how-many` |

**Question:** What fraction of fresh stigma mass remains after drying?

**Candidate URLs:** as Item 1.

**Done means:** a surviving fraction, and **`applies_to: mass`**.

**Watch for:** this must be recorded as a mass stage, never a product stage.
Drying makes each stigma lighter; it does not make it a fraction of a stigma.
Getting this wrong would let drying corrupt the flower count, which is exactly
the error `applies_to` exists to prevent — the same reason cook loss cannot
change how many chickens a dozen wings took.

---

### Item 5 — harvest_labour_hours

| | |
|---|---|
| `target_table` | `economic_stat` |
| `required_fields` | `value_lo/mode/hi`, `unit`, `basis` |
| `unit` | labour-hours per gram, or per pound |
| `archetype` | `comparison` |

**Question:** How much hand labour does one gram of saffron require?

**Candidate URLs:** as Item 1.

**Done means:** an hours figure with its basis named (per gram, per pound, or
per acre — all three appear in the literature). This is the axis on which
saffron can be compared to every other subject, and the comparison is the point:
the chicken corpus records that a grower earned about **12 cents** for the wings
behind a dozen wings.

**Watch for:** "19-hour days" is a *shift length*, not a productivity rate, and
it does not answer this question. Anecdote about how hard the work is is not the
same as hours per unit.

---

### Item 6 — yield_per_acre

| | |
|---|---|
| `target_table` | `regional_size_stat` or `economic_stat` |
| `unit` | pounds of dried saffron per acre |
| `archetype` | `comparison` |

**Question:** What does one acre of saffron yield?

**Candidate URLs:** as Item 1.

**Done means:** a per-acre figure with the drying state named. First-pass
reading suggests ~3 lb/acre, which if true is a startling contrast to poultry
land use and worth a fact.

**Watch for:** establishment year versus mature year. Saffron corms take
several seasons to reach full yield, so a first-year figure and a steady-state
figure differ substantially.

---

## Conflicts to report, not resolve

| Figure | Source | Basis stated? | Notes |
|---|---|---|---|
| | | | |

Fill this in. Expect disagreement on flowers-per-gram in particular — published
figures range widely, and the range is usually definition drift (fresh vs
dried, stigma vs whole flower) rather than genuine disagreement about the plant.

---

## What to explicitly NOT do

- Do not borrow any poultry loss factor. Nothing in the broiler chain applies:
  a crocus is not slaughtered, transported live, or chilled.
- Do not invent a mixing cascade. Whether a tin of saffron pools across fields
  and seasons is a real and interesting question, but if the documents do not
  say, the honest answer is that it is unknown. Eggs already borrowed the
  broiler cascade and it is wrong in detail; do not repeat that here.
- Do not treat the per-pound and per-gram figures as independent sources.
- Do not upgrade an extension publication to `study`. Extension documents are
  institutional, careful, and not peer-reviewed journal articles.

---

## Acceptance

- [ ] Every row carries a quote that appears verbatim in a returned document
- [ ] No row claims `measured` or `derived`
- [ ] New sources are in `proposed_sources:`, not `data/sources.yaml`
- [ ] `build` + `audit` pass on COOPER's self-check
- [ ] Model disagreements are flagged, not averaged
- [ ] **`stigmas_per_flower` comes back as exactly 3** with
      `is_anatomical_constant: 1` — the floor must rest on a constant, as the
      wing floor rests on two wings
- [ ] **Drying is `applies_to: mass`** and demonstrably does not move the
      flower count
- [ ] The Item 3 cross-check is reported with its residual, not reconciled away
