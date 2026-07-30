# Changelog

## Unreleased

### Three new "how many X" subjects, scouted and ready to run

Ground beef, maple syrup, and silk are drafted as research work-orders under
`docs/research/batches/` (06, 07, 08). Every candidate URL has been fetched,
confirmed 200, and pinned to the verbatim sentence that carries its figure — so
the quote-gate has a real target before COOPER ever runs. Nothing is in `data/`
yet: these are specs, not corpus, so the version does not move until COOPER runs
them and a human accepts. The batches were the surviving third of a larger idea
(saffron already shipped; honey and milk were already drafted as 04 and 05).

Each was chosen to exercise something the poultry corpus does not:

- **Ground beef** is the mixing model with **no anatomical floor** — the count is
  set by grinding, not biology, so it is the purest test of pooling standing
  alone. The floor is 1 (ground at home by hand); a documented contamination
  traceback puts one patty's trimmings at **four separate sources** (Nebraska,
  Texas, Uruguay, and a South Dakota trim plant).
- **Maple syrup** stacks a concentration ratio (~40 gal sap to 1 gal syrup, by
  the Jones Rule of 86) on a `recurring` per-tap rate over a **~6-week season** —
  a shorter period than eggs' year, and a test that the period is data rather
  than a hardcoded assumption.
- **Silk** adds a **garment-level** product (tie, shirt, dress) on a
  one-cocoon-per-worm constant, with a small honest reeling step (~5 cocoons per
  thread) that is real mixing but does not dominate the count.

Honest about grade: none rises above `industry`. Ground beef's headline "100+
cattle" is a corporate statement, the per-garment silk counts are craft-site
lore, and the sourced silk filament (**300–900 m**) is deliberately the cited
figure over the higher number that circulates. Said here so that proximity to
the NASS-backed poultry rows lends them no credibility they have not earned.

## v1.6.0 — 2026-07-30

Israel's head count stops being a single-source figure.

### Two figures promoted, from a document COOPER downloaded and could not read

The growers' organisation summary for 2021 carries a sector table that the
batch-05 extraction missed entirely and a human found by reading the returned
artifact. Both figures are now in the corpus at `industry` grade, from a new
`trade_body` source:

- **604 broiler growers** (2021), against the Times of Israel's "about 600 large
  chicken farms" from the Poultry Breeders Association. Two industry bodies, two
  publications, one number.
- **244 million chicks placed** (2021), against 260 million birds a year
  reported for 2025 by the other body — a ~6% gap over four years, which is
  roughly what growth looks like.

**Chicks placed is NOT birds slaughtered**, and it has its own measure for that
reason: grow-out mortality sits between the two, and the model already carries a
factor for it, so merging them would overstate throughput and then double-count
the mortality downstream. A test asserts the two measures stay distinct.

**The corroboration itself is now tested**, not just asserted in a note: the
chick and head figures must stay within 25% of each other and the grower count
within 550–650. If a future edit breaks the agreement that justified promoting
these, the suite says so rather than the claim quietly becoming false.

The learning-centre fact "Nobody officially counts Israel's chickens" now
carries both checks; it previously described only the kg-per-bird one.

### COOPER could not print Hebrew, and it cost a completed run

`runner.py` now reconfigures stdout and stderr to UTF-8 at startup. COOPER is
Windows, its console is cp1252, and any non-Latin character reaching stdout
killed the run — **after** the work was done, which is the worst possible place.
The first Hebrew-question batch extracted two figures and then died printing the
item's name, taking `findings.yaml` with it.

## v1.5.0 — 2026-07-30

The Israeli data gets a page, and the reader chooses how much of it to believe.

### The evidence toggle, on the "By country" view

The view itself arrived in a concurrent commit; this adds the choice it was
missing. Two radio buttons — **All evidence** and **Government figures only** —
re-query `/api/output/{iso3}` with `min_confidence` and re-render:

| | Birds/year | Implied average bird |
|---|---|---|
| All evidence | 260M `industry` | 2.31 kg `industry` |
| Government figures only | — | — |

Under the filter both cards disappear, because the figure they rest on does, and
the page names what it dropped: *"Hidden by this filter: Birds slaughtered per
year (industry, toi-poultry-imports-2025)."* A filtered answer that does not say
what it filtered is just a different number.

The choice **survives a country change** rather than resetting: a reader who
asked for government figures only should not have that quietly undone by
clicking a different country.

### region_level, so counting regions does not double-count

Israel nests 50 regional councils inside 4 districts inside a grand total.
Counting every row as a "region" claimed **55 Israeli regions against 23 US
states** — more granularity than exists. `output_stat_year.region_level` records
the publisher's hierarchy as a column rather than as a prefix inside a prose
note; the coverage count reads leaves only (50), the district cross-check reads
the column instead of matching a string, and a test pins the level counts.

### Batch 05 ran, and returned nothing — which is the finding

Three items, ten Hebrew documents, two models, twelve extraction calls, **zero
figures**. The fetch worked (including a 40-page State Comptroller PDF) and the
Hebrew survived chunking intact, so the failure is retrieval and extraction:
English questions scored against Hebrew chunks with an English-centric embedder.

A human read of the same returned artifacts found figures in minutes — the
second time the artifacts have been worth more than the extraction. Written up
in `docs/research/accepted/batch-05-israel-hebrew-REVIEW.md`, with **604 broiler
growers** and **244 million chicks placed (2021)** proposed for promotion. The
chick figure corroborates the 260-million head count from a second industry body
four years earlier, and the review is explicit that chicks placed must not be
loaded as birds slaughtered.

Nothing from the batch is in `data/`. The verify gate exists precisely so a zero
is allowed to be a zero.

## v1.4.0 — 2026-07-29

Israel gets the sources CBS is not, and the reader gets to choose how much to
believe.

### Both readings of Israel, and neither is hidden

CBS answers scale and nothing else, so with government data alone Israel cannot
answer "how many chickens" at all. A named industry official — Moti Elkabetz,
secretary of the Poultry Breeders Association, in the Times of Israel — puts
throughput at **260 million broilers a year**. That figure is loaded at
`industry` grade, and the government-only picture stays reachable rather than
being overwritten:

```
GET /api/output/ISR                          260 million birds, industry grade
GET /api/output/ISR?min_confidence=measured  no bird count, and it says which
                                             row it dropped and why
```

`output_stat_year` gained a `confidence` column to make that possible. The table
stopped being government-only the day this row arrived, and "government figures
only" is now a WHERE clause instead of a promise in a comment. `/api/countries`
reports `head_slaughtered_grade` and `head_slaughtered_measured` alongside the
boolean, so a caller cannot render "we have a bird count" without also knowing
who counted.

### The cross-check that makes it believable

600,072 tonnes (CBS, measured) over 260 million birds (industry) is **2.31 kg a
bird** — what a 40-day broiler weighs. Two sources that were not derived from
each other, agreeing.

It is a view, `v_output_derived_weight`, never a stored row, so it cannot drift
from its parents. Its confidence is the **weaker** parent's, never the better
one, and it reports `year_gap` because the years genuinely do not line up: CBS
has no 2025 output figure and the interview named no year. A same-year pairing
would have been tidier and would have required pretending otherwise.

### A hole in the government data, now explained

CBS output for 2023 is **553,068 tonnes — below its own 2020 figure** and 8%
below 2024. Poultry World reports 16 million head lost to Newcastle disease
outbreaks in Q4 2023, wartime closures in the north and south, and a labour
shortage that pushed slaughterhouses to a six-day week. The standing flock
agrees: 34,121 thousand at end-2023 against 38,239 thousand at end-2020.

The dip was already in the corpus. The explanation came from a trade
publication. Neither meant much alone, and a test asserts the fact's prose still
matches the rows it describes.

### Six Israeli facts, including the demo hook

- **Chicken wings are on the Yom Ha'atzmaut grill**, alongside pargiyot, with
  falafel and shawarma barely featuring. The project's exact product is part of
  an Israeli national holiday.
- **"Pargiyot" means "baby chickens"** and no longer does — the same name drift
  that makes "a dozen wings" ambiguous.
- An Israeli chicken goes from **NIS 6.5/kg at the farm to ~NIS 20/kg at
  retail**.
- **Nobody officially counts Israel's chickens**, and the fact says so.
- **Kosher bedikah has no FSIS analogue** — and no published rejection rate, so
  it is described and deliberately not quantified.

### What is deliberately still absent

No per-capita figure. Three reachable sources give three "world's highest"
numbers — 58.2, 64.9 and 70.83 kg — a 20% spread that is almost certainly
definition drift, so `population` stays NULL and a test fails if any of those
numbers appears in a fact. `batch-05-israel-hebrew.md` is written to resolve it
from a primary series, and says not to ship one otherwise.

Also recorded as reachable-but-unused: the Ministry of Agriculture (403 to every
fetcher, an Akamai filter rather than a missing page) and the plant market shares
in Poultry World, which are third-hand.

## v1.3.0 — 2026-07-29

Israel becomes the second country with data, and the README stops claiming the
corpus is better sourced than it is.

### Israeli broiler figures, and the one they do not include

Three tables from the CBS Statistical Abstract 2025, chapter 21, cited and
audited like everything else:

- **Output** — 600,072 tonnes of broiler output for 2024 (CBS-provisional),
  with a series back to 2000, and value in NIS millions.
- **Inventory** — 37,895 thousand broilers at end of 2024, a series back to
  1960. This is a **standing flock, not annual throughput**; broilers turn over
  several times a year, so reading it as slaughter understates the answer
  several times over. Stored as `measure='inventory_eoy'` so the distinction is
  in the data rather than only in a comment.
- **Districts** — broiler marketing for 47 districts and regional councils,
  8 of them suppressed by CBS and loaded as presence without volume.

**Head slaughtered per year does not exist in any of them**, and it is the
denominator the count question needs. So Israel can answer scale and cannot
answer "how many chickens" from Israeli sources. Deriving it would need an
Israeli average bird weight, which CBS also does not publish; borrowing the US
6.62 lb would make an American assumption look like an Israeli measurement.
A test asserts no Israeli head figure exists, so nothing can quietly fill it.

Per-capita consumption is still unclaimable: the article behind the "Israel is
the world's highest per-capita chicken consumer" headline now returns 404, so
`country.population` stays NULL and `/api/countries` reports
`per_capita: false` rather than rendering a claim with no reachable source.

### New table, because the US-shaped ones would have lied

`output_stat_year` stores the measure and the unit as data instead of implying
them in column names. The alternatives were mapping CBS tonnage onto
`certified_rtc_lb` — asserting that "agricultural output" means ready-to-cook
weight, which the publication never says — or converting shekels with an
exchange rate we would have to source. Israeli rows keep tonnes, shekels and
thousands of head; a test fails if a pound or a dollar ever appears on one.

### A cross-check that fails, on purpose

District marketing sums to 571,500 tonnes against 600,072 tonnes of output, a
gap of **4.76%**. Marketing excludes self-consumption and private sale by CBS's
own footnote, so the gap is probably real — but a reader who adds up the
districts will find it, and finding it unannounced reads as our error. Both the
gap and its explanation are asserted by tests.

### New endpoints

- `GET /api/countries` — what each country can actually answer, not just its
  name. A selector built from names alone would imply a parity that does not
  exist between enumerated US head counts and Israeli tonnage.
- `GET /api/output/{iso3}` — output, value and inventory in native units, with
  suppressed regions flagged rather than zeroed.

### README figures are generated

"Honesty about the data" had drifted three times while hand-maintained, most
recently claiming **7 of 12** loss factors were unsourced estimates when the
true figure was **11 of 21** — an error in the direction that overstates the data's
quality. `audit --stats` now emits that block, `tools/update_readme.py` writes
it, and CI fails if a data change skipped the regeneration. The test count is no
longer quoted: it is not a fact about the data and it moved on every commit.

The Scope section was three subjects out of date and now documents all three
yield modes — countable, recurring, continuous.

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
