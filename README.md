# counting-chicken-wings

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
| 50 birds | 11.3 |
| 1,000 birds | 11.96 |
| 40,000 birds | **11.99** — one plant shift |

Six is reachable only by hand. Everything from a commodity supply chain is pinned
just under twelve.

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

## Scope

Broiler chickens only. The schema carries a species dimension so turkey can be
added later without migration.

## Status

Early. Research and schema are in place; the model and CLI are being built.
