# counting-chicken-wings

+[![discussions](https://img.shields.io/github/discussions/gmhoward9289-ops/counting-chicken-wings)](https://github.com/gmhoward9289-ops/counting-chicken-wings/discussions)
+
**How many chickens does it take to make a dozen chicken wings?**

The naive answer is 6. A chicken has two wings, so twelve wings is six chickens.

That answer is a floor, not a fact. The twelve wings on your plate almost certainly
did *not* come from six chickens — they came from something closer to twelve
different birds, and this program explains exactly why.

> **It always takes 6 or more chickens. Never fewer. Usually close to 12.**

---

## The two questions

This program answers two genuinely different questions and never conflates them.

**1. How many birds' worth of wing did this consume?**
A supply-chain question. Start at twelve wings on a plate and walk backwards
through every loss in the system — condemnation at the plant, wings broken during
catching and shackling, trim, downgrade, cook loss. Each loss means more birds had
to enter the top of the funnel. The answer is 6 plus the losses.

**2. How many individual chickens are physically represented on the plate?**
A pooling question, and the more interesting one. Bounded hard below by 6 and above
by 12. Where you land depends entirely on how much mixing happened between the
processing plant and the fryer.

## Why the answer is near 12, not 6

**Mixing starts the instant the wings leave the bird.**

On the cut-up line a bird's left and right wing drop onto the same conveyor and
immediately diverge. They are then *actively separated* by size grading — jumbo,
large, and medium wings are sorted into different streams, so if a bird's two wings
differ even slightly in weight they are deliberately routed into different boxes.

After that they are pooled again, repeatedly:

| Stage | What happens |
|---|---|
| Cut-up line | Wings separated from bird — mixing begins here |
| Wing chiller | Bulk commingling |
| Size grading | *Actively splits* a bird's two wings |
| Combo bin | ~2,000 lb bulk container |
| IQF freezer tunnel | Continuous flow, no lot boundaries |
| Case pack | Boxed |
| Distributor warehouse | Pallets from many lots |
| Restaurant freezer | Restocked from many boxes, many deliveries |
| Fryer basket | Your order |

Draw `n` wings from a pool holding `B` birds, each contributing 2 wings. Expected
distinct birds:

```
E[distinct] = B × [ 1 − C(2B−2, n) / C(2B, n) ]
```

For a dozen whole wings:

| Pool size | Expected distinct chickens |
|---:|---:|
| 6 birds | **6.00** — you broke down six birds by hand |
| 50 birds | 11.33 |
| 500 birds | 11.93 |
| 1,000 birds | 11.97 |
| 100,000 birds | **12.00** — a distributor warehouse |

Six is reachable only by hand. Everything from a commodity supply chain is pinned
just under twelve.

### The real reason is saturation, not grading

That table is the whole answer, and it is worth being precise about *why* — because
this README used to say something else. It called size grading "the single strongest
driver pushing the answer toward 12", and the model has never agreed.

Sweep the grader's separation efficiency across its entire possible range, on the real
commodity cascade, for a 12-wing draw:

| Separation efficiency | Expected distinct birds |
|---:|---:|
| 0.00 — mechanism fully off | 11.9997 |
| 0.90 — the shipped value | 12.0000 |
| 0.99 | 12.0000 |

Turning the mechanism completely **off** costs 0.0003 of a bird. Scaling every pool in
the cascade down 100-fold still returns 11.9966.

What pins the answer is **saturation**. The curve above flattens hard, and
`saturation_threshold` computes where: above **661 commingled birds** a dozen wings is
already within 0.05 of twelve, and above 3,301 it is within 0.01. The smallest pool
anywhere in the commodity cascade is thirty times the first figure *at the pessimistic
end of its band*. By the time the wings reach the grader the container is already
essentially all-different-birds.

This is a **stronger** result than the one it replaces. Every pool size in
`data/mixing.yaml` is our estimate, unsourced and flagged as such — and the commodity
answer does not depend on any of them. `tests/test_scientific.py` fails if that stops
being true.

The cut-up line and the grader are still real, still described above, and still decide
the **small-pool** routes, where nothing is saturated. A local butcher's 40-bird tray
sits well below the threshold, which is exactly why that route reads meaningfully under
twelve. What is no longer claimed is that they determine the commodity number.

### The one force that pushes back down: clustering

Everything above pushes the count **up**, which is why the headline sat at the ceiling
carrying almost no information. A fryer scoop is not an exchangeable draw — it is a grab
of contiguous units from a bin filled case by case, and cases are packed from contiguous
belt runs. Wings that travelled together tend to stay together, and that positive
intra-cluster correlation is the only thing in the whole model that can lower the answer.

It is modelled with standard cluster-sampling machinery: a scoop size, an
adjacency-retention parameter per stage kind, and Kish's design effect
`deff = 1 + (c−1)·ICC` reported so the loss of effective sample size is explicit. The
retention of a *route* is the product of its stages' retentions, so a cascade's
`random` / `separating` / `none` sequence finally determines something it could not
before.

Two things must be said plainly about what fell out.

**The mechanism works.** Take the commodity pool sizes, delete every stage that destroys
adjacency, and vary how much survives:

| Cascade retention | Scoop | Expected distinct birds |
|---:|---:|---:|
| 0.00 (exchangeable draw) | 1 | 12.00 |
| 0.20 | 4 | 11.80 |
| 0.50 | 4 | 10.85 |
| 1.00 | 4 | 7.50 |
| 1.00 | 12 (one grab) | **6.50** — essentially the floor |

**And it does not move the commodity answer.** A real commodity cascade runs a bird's
wings through six bulk commingling stages and a grader. A wing chiller is a stirred
immersion vessel with a residence time in tens of minutes — it is a mixing tank by
design. Multiplying the per-stage retentions out gives a cascade retention of about
**0.000001**, and the commodity answer stays at 11.99997.

| Route | Cascade retention | Answer |
|---|---:|---:|
| Commodity foodservice | 0.0000012 | 11.99997 |
| Grocery retail | 0.0000061 | 11.99996 |
| Local butcher | 0.040 | **11.01** (was 11.16) |
| Whole birds at home | 1.0 | 6.00 |

So clustering changes exactly the route where it physically should: the short cascade,
where a tray of forty birds' wings never goes through anything that would separate them.

The parameters were picked from case packs, combo-bin sizes and how a portion is
actually taken from a bin, then graded `estimate` and left alone. They were **not** tuned
to produce a more interesting headline, and the honest report is that the headline did
not move. Where a judgement call existed it was made in clustering's favour, so the
finding is stated against the thumb on the scale rather than with it.

---

## Data

Every number in the database carries a citation, a confidence level, and a
lo/mode/hi range. The data is as real as public sources allow — and where it
cannot be known for certain, it is explicitly an estimate rather than a fabricated
precision.

Anchor figures, measured by USDA NASS for 2025:

- **9,579,797,000** broilers slaughtered
- **63,443,212,000 lbs** live weight
- **48,006,482,000 lbs** certified ready-to-cook
- **75.67%** dressing yield (derived from the two totals above)
- **0.45%** post-mortem condemnation
- **6.62 lbs** average live weight — but **4.5 lbs in Ohio** and **8.6 lbs in
  North Carolina**, because small-bird and big-bird programs are different
  businesses

See [docs/RESEARCH.md](docs/RESEARCH.md) for the full sourced dataset.

## Confidence levels

Every stored figure is tagged:

| Level | Meaning |
|---|---|
| `measured` | Reported directly by USDA |
| `derived` | Computed from measured figures |
| `study` | Peer-reviewed, may not generalize |
| `industry` | Trade rule of thumb |
| `estimate` | Our reasoning, flagged as such |

Nothing is presented as more certain than it is.

## Usage

```bash
wings 12
```

Gives the answer plainly, then offers the reasoning:

```
A dozen wings took at least 6 chickens.
The wings on your plate came from about 11.97 different birds.

Show the reasoning? [y/N]
```

Answer `y` and it unfolds the full audit trail — every stage, the factor applied,
the running bird count, and the citation for each number.

### The web interface

```bash
pip install -e ".[gui]"
wings gui
```

Nine views: the calculator with its reasoning panel, scientific mode, a mixing
simulator, a state choropleth, a by-country panel, "is fatter better?",
nutrition and impact, year-over-year trends, chicken facts, and a sources
table. Every figure carries a colour-coded confidence badge — green measured, blue study,
cyan industry, amber estimate — so you can see at a glance which numbers are
solid and which are placeholders.

### Rebuilding the database

```bash
python -m counting_chicken_wings.build
```

Facts live in readable YAML under `data/`; the `.db` is a build artifact and is
gitignored. The build **fails** if any statistic cites a source that isn't in
`sources.yaml`. `python -m counting_chicken_wings.audit` reports citation
coverage and how much of the model still rests on estimates.

## Scope

The question generalises to "how many X does it take to produce Y", and it is no
longer only about chickens. Three subjects are live — broiler wings, table eggs,
and saffron — and each answers the question by a different mechanism. Turkey is
stubbed as an inactive species, waiting on figures rather than on code.

The abstraction splits three ways on yield:

| Mode | Floor comes from | Subject |
|---|---|---|
| `countable` | anatomy — `ceil(n ÷ units_per_individual)`, the 6-or-more logic | a wing belongs to one bird; a crocus has exactly three stigmas |
| `recurring` | a rate over **time** | a hen lays at most one egg a day, so a same-day dozen needs twelve hens |
| `continuous` | a reported ratio, and the ceiling collapses onto the floor | one gram of saffron is the combined stigmas of ~150 flowers, so no unit traces to one individual |

The mixing model applies to all three: a gallon of milk from a bulk tank holds
milk from hundreds of cows for exactly the reason a dozen wings comes from
twelve chickens. Eggs are the case where it *cannot* apply — the floor has
already risen to meet the ceiling, leaving mixing nothing to move.

## Honesty about the data

<!-- BEGIN GENERATED: audit --stats -->

Of the 25 loss factors in the model, **12 are unsourced estimates (48%)**. Only 9 of those affect the **count** answer; the other 3 are mass-only and cannot move it. That distinction is tracked and reported by the audit rather than glossed over.

Corpus: **63 sources**, 59 facts, 12 products across 6 active species, 35 tables. Every statistic is cited and the build fails if one is not.

*Generated by `python -m counting_chicken_wings.audit --stats`. Do not hand-edit — `tests/test_readme.py` fails on drift.*

<!-- END GENERATED -->

The estimate share has risen as the corpus grew, and that is expected rather
than a regression: wings rest on an enumerated federal survey, while eggs and
saffron reach into subjects no agency counts. A figure with no NASS behind it is
still worth holding if its grade says so.

The single biggest source of uncertainty is not a processing figure at all. It's
whether "a dozen wings" means twelve whole wings or twelve menu pieces. That one
ambiguity changes the answer more than every loss in the chain combined.

## Status

Latest release and what moved in it: [CHANGELOG.md](CHANGELOG.md). The version
is not repeated here — it went stale twice, and `GET /api/version` is the only
answer that is true of the deployment rather than of a file.

+Questions or ideas? → [Discussions](https://github.com/gmhoward9289-ops/counting-chicken-wings/discussions)
+

Live at https://counting-chicken-wings.onrender.com/ (free tier; a first visit
may wait ~20s for a cold start).

Corpus figures are in [Honesty about the data](#honesty-about-the-data) above,
generated from the audit. They are not repeated here — two hand-kept copies of
the same count is how the last one went stale.

Every page carries a build stamp in the footer — version, commit, and corpus
counts, read from `/api/version`. Because Render tracks `master` rather than
tags, the commit is the honest answer to "what am I looking at?"; the version
alone is not.

Ongoing work, tracked in [docs/ROADMAP.md](docs/ROADMAP.md): replacing the
estimate-grade loss factors with sourced ones, US regions, more producers and
breeds, chicken manure, and USDA programs. International data and a Discord
bot are deliberately post-1.0.

## License

Dual-licensed: the source code is [MIT](LICENSE); the research corpus and
written documentation under `docs/` and `data/` are
[CC BY 4.0](LICENSE-DOCS) — reuse them freely with credit. The figures
themselves are facts from the cited primary sources and carry no copyright.
