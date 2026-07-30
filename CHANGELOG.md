# Changelog

## v1.2.0 — 2026-07-29

Eggs get their own supply chain. **This is a correctness fix**: v1.1.0 shipped
eggs with the right number and the wrong explanation.

### The bug

Eggs had zero mixing stages and zero supply chains, and
`default_supply_chain()` took no product argument — so an egg query resolved to
the single global default, which was the **wing** chain, and walked eight
stages that do not exist for an egg:

```
cut-up line → wing chiller → size grading → combo bin
  → IQF freezer → case pack → distributor → fryer basket
```

The *count* was right (12 hens), because a hen's one-egg-a-day ceiling
dominates and any large pool yields twelve. But the reasoning panel told anyone
asking about a carton that "the cut-up line a chicken's two wings drop onto the
same conveyor and part company, then size grading actively splits any pair."

For a project whose entire claim is that every number is traceable, a confident
and detailed explanation of the wrong animal is the worst defect available.

### What changed

- **Egg mixing cascade** — nest and belt collection, on-farm cooler, washing,
  candling and grading, carton pack, distributor, retail case, your fridge.
- **Three egg routes** — `commercial_carton` (default), `farmers_market`,
  `backyard_eggs`. Only the backyard route can reach the floor of one hen.
- **Egg grading is `random`, not `separating`.** Weighing wings splits a bird's
  pair because a bird has exactly two. Each egg is already a lone contribution,
  so there is no pair for grading to break; calling it separating would invent
  a mechanism.
- **Supply chains are scoped to a species**, and `species_slug` is now
  **required** on `default_supply_chain()`. A species-less default is not a
  meaningful thing to ask for, and its being answerable is exactly how this
  happened. There is deliberately no cross-species fallback — returning
  another animal's route fails silently, which is worse than failing.
- **The floor explanation moved into data** as `supply_chain.floor_note`. It
  was hardcoded wing prose in both `cli.py` and `static/index.html`, so fixing
  the data alone would not have fixed the output. Per `CLAUDE.md`, a figure or
  claim hardcoded in a module is a bug.

### Also fixed

`resolve_pool()` clamped the lower bound to `container / upi` without capping
it at the container size. For wings (`upi ≥ 1`) that is always safe. For eggs
over a single day (`upi = 0.789`) it reported a 12-egg carton as "representing
roughly 15 individuals" — more contributors than units, which cannot happen.
The count was unaffected because the caller re-clamped, but the audit trail
printed the impossible figure.

### Channel-aware loss stages

A second instance of the same defect, one level down. `supply_chain` selected
which **mixing** stages applied but had no say over **losses**, so every route
got every stage. `retail_shrink` was therefore parked `optional`/default-off
purely to stop it double-counting against `kitchen_loss` — a workaround
standing in for a model, and the grocery path could not be expressed at all.

Routes now declare their own losses via `supply_chain_loss_stage`, and a new
`grocery_retail` chain demonstrates it:

| Route | `kitchen_loss` | `retail_shrink` |
|---|---|---|
| `commodity_foodservice` | yes | no |
| `grocery_retail` | no | **yes** |

A wing does not pass both a supermarket meat counter and a restaurant kitchen,
and no route may now claim both — asserted by a test over every chain. A chain
that declares nothing still gets the species defaults, so existing routes are
untouched.

### Egg grading is documented, not just decided

Modelling egg grading as ordinary mixing rather than active separation is a
judgement about mechanism, not a sourced figure, so it is now stated where
readers can find it: the stage description, and a learning-centre fact. A bird
has two wings and weighing them pulls the pair apart; an egg reaches the grader
already alone, so there is no pair to break.

### Unchanged

Wings still answer 6 → 11.99997, and still explain themselves via the cut-up
line. 261 tests pass.

## v1.1.0 — 2026-07-29

Eggs become a first-class product rather than a proof that the schema
generalises. Per [docs/VERSIONING.md](docs/VERSIONING.md) data additions are
MINOR, so this is a MINOR release.

### The recurring-yield window

`model.py` had `RecurringYield` and `recurring_floor` and nothing called them,
so `wings 12 --product table_egg` reported a floor of **0.042 hens** — the
annual rate applied to a same-day question — while the distinct count on the
same screen said 12. The two contradicted each other by 285x.

The window is now plumbed through `run()`, `db`, the CLI (`--window-days`) and
the API (`window_days`), defaulting to one day:

| Window | Hard floor | Expected | Distinct |
|---|---|---|---|
| 1 day | **12 hens** | 15.2 | 12 |
| 15 days | 1 hen | 1.01 | ~12 |

Both floors are reported, because either alone misleads: 12 is physiology,
15.2 is what you need since hens do not lay daily.

**Eggs invert the wing story.** Wings have a floor of 6 that mixing pushes up
toward 12. Same-day eggs have a floor that *rises to meet* the ceiling at 12,
leaving the supply chain nothing to move.

### Eggs get their own loss chain

Almost nothing carried over — an egg is never slaughtered, cut up, or breaded.
Five new stages in `data/loss_chain_eggs.yaml`, built on USDA's own grading
distinction:

- **Check** — shell cracked, membranes intact. A *downgrade*: it leaves the
  shell-egg stream for the breaker plant and becomes liquid egg.
- **Leaker** — contents escaping. A true loss.

Plus in-transit breakage, kitchen breakage, and layer mortality (off by
default, like grow-out mortality). A dozen eggs now needs **16.1 hens** into
the system against a 15.2 floor.

Note the contrast with wings: frozen IQF wings are robust enough that no
citable transit figure exists, while eggs are fragile enough that the industry
measures breakage closely.

### Egg data

- **Nutrition** (FDC 171287): 143 kcal, 12.56 g protein, 9.51 g fat, 372 mg
  cholesterol per 100 g. Raw only — a wing has one dominant preparation, an
  egg has none, and asserting one would invent a default.
- **National totals**: 365.1M layers, 288 eggs each, 105.2B eggs (90.1B table).
  The corpus had 34 states but no US row.
- **Three new facts**, including the companion to the bird-flu figure: layers
  fell 3% and production 4%, while broilers lost ~0.05%. Same virus, same
  country — a broiler lives 47 days and a layer lives years.

### Also

- `data/<prefix>*.yaml` globbing now applies to `loss_chain` and `nutrition`,
  not just `taxonomy`, so a new product line stays a new file.
- Fixed `fmtDistinct` printing `12.000000` for same-day eggs, in Python and
  JS. Wings approach the ceiling and never arrive; eggs arrive, and six
  decimals implied the opposite.
- Fixed the GUI band running from the expected floor, so eggs showed
  "floor 15.21" against a ceiling of 12 — above its own scale.
- The calculator had **no product selector**, so eggs were unreachable from
  the web UI entirely. Added, with the window control shown only for
  recurring products.
- Scientific mode now defaults to **2,000** Monte Carlo iterations rather than
  20,000. This is a hosting concession, and it does move a published band, so:
  the draws are seeded, so both figures are reproducible rather than noisy, and
  at 12 wings the 90% interval goes from 6.7833–7.3957 to 6.7794–7.3930 — a
  shift in the third decimal, or 0.01 on the upper bound as displayed. Render's
  free tier runs the CPU-bound resample 11-13x slower than a laptop, which made
  the old default a 6-second wait on every visit to the tab and 30 seconds for
  anyone choosing 100,000. Both larger counts are still in the dropdown.

### Known gaps

- Layer mortality and kitchen breakage are unsourced estimates.
- Check and leaker rates are grading *tolerances*, which are ceilings a pack
  must stay under rather than measured rates, so they overstate real loss.
- No egg mixing cascade of its own; eggs reuse the broiler chains, which is
  wrong in detail — an egg carton is not a combo bin.


## v1.0.0 — 2026-07-29

First release. Answers "how many chickens does it take to make a dozen
chicken wings?" for US broilers, with every number traced to a source.

### The answer

For a dozen whole wings through a commodity foodservice chain:

| | |
|---|---|
| Hard floor | **6 chickens** — a chicken has exactly two wings |
| Distinct chickens on the plate | **11.99997** |
| Chickens required, all losses counted | **6.90** |

The floor is arithmetic. The 11.99997 is the interesting part: mixing starts
the instant the wings leave the bird, and size grading actively splits a
bird's two wings into different grade streams, so a dozen wings from a
commodity chain is very nearly a dozen different chickens. Six is only
reachable if you cut up six birds yourself.

### Two products, and one of them is a lie

- **Whole wing** — 2 per bird, anatomical constant. A dozen is 6 chickens.
- **Boneless wing** — contains **no wing meat**. It is breast, and Tyson's own
  ingredient statement reads "boneless, skinless chicken breast chunks with
  rib meat". A dozen takes about **0.35 of a chicken** — a seventeenfold
  difference from the same menu section.

"Wings" is a regulated term: USDA requires the entire wing, muscle and skin
intact, and requires the name to disclose removed bone. "Boneless wing"
complies. The problem is the name, not the meat.

### What ships

**Three questions, never conflated** — the anatomical floor, the individuals
required after walking the loss chain backwards, and the distinct individuals
actually represented in your portion.

**A 12-stage loss chain** with 14 factors, each carrying lo/mode/hi bands.
Stages are tagged by what they affect, and the model enforces it: cook loss
makes a wing lighter, not fractional, so it cannot move a count.

**A 9-stage mixing cascade** from the cut-up line to the fryer basket, with
`separating` stages modelled distinctly from `random` ones because grading
pulls pairs apart rather than merely shuffling them.

**Scientific mode** — Monte Carlo with a selectable confidence interval
(50–99%), a tornado chart showing which unsourced figure actually moves the
answer, and an evidence floor that recomputes using only figures at or above
a chosen grade. Using measured government data alone gives 6.03 chickens
required; including our estimates gives 6.90. That gap is a more honest
statement of uncertainty than any single error bar.

**"Is fatter better?"** — Ohio runs 4.6 lb birds, North Carolina 8.4 lb, a
1.83× spread that is market segment rather than biology. The verdict: better
for yield per bird, worse for quality per pound, and irrelevant to the wing
count. White striping affects 96% of fillets and worsens with live weight;
wings develop no equivalent myopathy at all.

**Nutrition and footprint**, mass-allocated. A dozen wings carries ~1.3 kg
CO₂e, not the 17.4 kg a naive six-birds multiplication gives — wings are ~7%
of the bird. The grower was paid about **12 cents** for the wings' share.

**Nine views** in the web GUI, a CLI with progressive-disclosure reasoning,
and `wings export` writing 25 self-describing .txt/.csv files.

### Data

| | |
|---|---|
| Sources | 31, every statistic cited |
| Facts | 34, surprise-ranked |
| States | 22 (NASS publishes only these individually) |
| Tables | 26 |
| Tests | 163 |

The build **fails** if any statistic cites a source that does not exist, and
a separate CI job audits citation coverage across all 15 data tables.

### Known limits, stated rather than hidden

- **8 of 14 loss factors are unsourced estimates**, 5 of which affect the
  count. Listed in `docs/RESEARCH.md` and surfaced by `wings`' own audit.
- **Only 22 states.** NASS reports broilers slaughtered in 40 but publishes
  22 individually; the rest are suppressed to avoid disclosing individual
  companies. This is a ceiling on the source, not a gap in the work.
- **No per-producer loss factors.** Line speed (175 vs 140 birds/min) and
  chilling method (a ~10 point mass swing) demonstrably differ between
  plants, but no one publishes per-plant damage rates.
- **HPAI is deliberately not modelled.** Broilers are ~8% of the 168.62M
  birds lost since 2022 — about 0.05% of annual throughput, inside the noise
  of every other factor. It is an egg story.
- **Mixing pool sizes are our estimates.** The qualitative conclusion is
  robust to them: the curve flattens above ~1,000 birds, so any
  commodity-scale pool lands within a hair of the ceiling.
- **Boneless wings have no nutrition row yet** — the view says so rather than
  showing a blank.

### Deployment

Live at https://counting-chicken-wings.onrender.com/

Render's free tier spins down when idle, so a first visit can wait ~20s for
a cold start. A `/healthz` endpoint exists to be pinged by an external cron;
that is the only real fix short of an always-on instance. Client-side
loading UI cannot help, because the stall happens on the HTML document before
any script runs.

Plotly is loaded from a CDN. If it is unreachable the charts degrade to a
message and every figure remains available in the tables and the API.
