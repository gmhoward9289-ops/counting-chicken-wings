# Changelog

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
