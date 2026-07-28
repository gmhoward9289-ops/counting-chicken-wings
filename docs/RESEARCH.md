# Research Notes — Broiler Processing & Wing Supply Chain

Every figure here carries a source and a confidence note. Nothing in this file is
invented. Where a number is an estimate or an industry rule of thumb rather than a
measured statistic, it says so explicitly.

**Scope: broiler chickens only.** Turkey is deliberately out of scope for v1; the
schema carries a `species` dimension so it can be added later without migration.

---

## 1. National baseline — USDA NASS, measured

Source: [Poultry Slaughter 2025 Summary, USDA NASS, February 2026](https://www.nass.usda.gov/Publications/Todays_Reports/reports/pslaan26.pdf)

NASS calls the category **"Young Chickens"** — defined in the report as
"commercially grown broilers-fryers and other young immature birds such as roasters
and capons." This is the broiler population.

| Metric | 2025 | 2024 |
|---|---:|---:|
| Head slaughtered | 9,579,797,000 | 9,460,743,000 |
| Total live weight (lbs) | 63,443,212,000 | 62,139,063,000 |
| Pounds certified, ready-to-cook (lbs) | 48,006,482,000 | 46,995,202,000 |
| Average live weight (lbs) | 6.62 | 6.57 |
| Post-mortem condemnation | 0.45% | 0.46% |

**Derived national dressing yield (RTC ÷ live weight): 75.67%** (2025).
This is a *measured* national figure, not an estimate — it falls straight out of two
reported totals. It is the single most reliable number in the whole model.

Post-mortem condemnation is reported as *pounds condemned as a percent of pounds
certified plus post-mortem condemnations* — note the denominator, it is not a
percent of live weight. 2025: 216,531,000 lbs condemned.

**Upper bound on the whole system:** 9.58 billion birds × 2 wings =
**19.16 billion whole wings** physically available in the US in 2025.

### 1a. Bird size programs are visible in the state data

Average live weight by state, 2025 — this is the small-bird / big-bird split showing
up directly in government data, and it is the most useful producer-linked signal in
the entire dataset:

| State | Avg live wt (lb) | Program type |
|---|---:|---|
| Ohio | 4.51–4.75 | Small bird (fast-food / tray pack) |
| Iowa | 4.99–5.59 | Small bird |
| New York | 5.02–5.22 | Small bird |
| Missouri | 5.44–5.56 | Small bird |
| Alabama | 5.44–5.64 | Small/medium |
| Georgia | 6.06–6.22 | Medium |
| Texas | 6.57–6.98 | Medium |
| Mississippi | 6.57–6.79 | Medium |
| Louisiana | 6.70–7.06 | Medium/large |
| Arkansas | 7.28–7.44 | Large |
| South Carolina | 6.93–7.40 | Large |
| Delaware | 7.52–7.72 | Large |
| Oklahoma | 7.80–8.51 | Big bird (deboning) |
| **North Carolina** | **8.32–8.59** | **Big bird (deboning)** |

Range: **Ohio 4.5 lb → North Carolina 8.6 lb.** A North Carolina bird is ~1.9× an
Ohio bird by live weight, and its wings scale roughly with it. This is why "how many
chickens" depends on *where the wings came from* — a dozen wings from a big-bird
deboning plant represents meaningfully fewer birds' worth of wing mass than a dozen
from a small-bird plant, even though the bird *count* floor stays at 6.

---

## 2. Farm-stage losses

Source: [National Chicken Council, U.S. Broiler Performance](https://www.nationalchickencouncil.org/about-the-industry/statistics/u-s-broiler-performance/)

| Year | Market age (days) | Market weight (lb) | Feed conversion | Mortality % |
|---|---:|---:|---:|---:|
| 2015 | 48 | 6.12 | 1.89 | 4.8 |
| 2016 | 47 | 6.16 | 1.86 | 4.5 |
| 2017 | 47 | 6.20 | 1.83 | 4.5 |
| 2018 | 47 | 6.26 | 1.82 | 5.0 |
| 2019 | 47 | 6.32 | 1.80 | 5.0 |
| 2020 | 47 | 6.41 | 1.79 | 5.0 |
| 2021 | 47 | 6.46 | 1.79 | 5.3 |
| 2022 | 47 | 6.56 | 1.77 | 5.3 |
| 2023 | 47 | 6.54 | 1.75 | 5.7 |
| 2024 | 47.4 | 6.57 | 1.69 | 5.93 |

Grow-out mortality is **rising** — 3.7% in 2013 was the historic low, now 5.93%.

**Modeling caveat:** farm mortality is arguably *upstream* of the question. A bird
that dies at day 20 never becomes a wing, but it also never enters the wing supply.
Whether to count it depends on the question being asked:
- "How many chickens' wings are on my plate?" → exclude farm mortality.
- "How many chicks had to be placed to put these wings on my plate?" → include it.

The program should expose this as an explicit toggle, not bury it in a constant.

---

## 3. Wing yield

Source: [Yield of Carcass, Parts, Meat, Skin, and Bone of Eight Strains of Broilers, Poultry Science](https://www.sciencedirect.com/science/article/pii/S003257911946625X/pdf)

- Whole wing as **% of chilled carcass weight: 9.1% – 10.2%** (across 8 strains)
- Whole wing as **% of live weight: 6.7% – 7.3%**

Cross-check: 9.65% (carcass midpoint) × 75.67% (dressing yield) = 7.30% of live
weight — lands at the top of the independently reported 6.7–7.3% live-weight range.
The two sources are consistent. Good confidence here.

### 3a. Wing segment split

Source: [Method of production of boneless chicken wings, Poultry Science](https://www.sciencedirect.com/science/article/pii/S0032579119322989)

| Segment | Bone-in weight | Boneless yield |
|---|---:|---:|
| Drumette | 39.9 g | 74.9% |
| Flat / wingette | 30.7 g | 80.1% |
| Tip | — (mostly skin, bone, cartilage) | negligible meat |

Drumette + flat = 70.6 g of the whole wing. Tips are typically diverted to stock,
export, or rendering rather than sold as wings.

**Terminology decision for this project:** per project definition, a "wing" means a
**whole wing** — 2 per bird. A dozen wings = 6 birds minimum. Note that restaurant
menus commonly mean 12 *segments* (drumettes + flats), which would be 6 whole wings
= 3 birds. The program will support both conventions via an explicit unit setting,
defaulting to whole wings.

---

## 4. Damage and downgrade

Source: [Rearing and handling injuries in broiler chickens and risk factors for wing injuries during loading, Can. J. Anim. Sci.](https://cdnsciencepub.com/doi/10.1139/cjas-2019-0204)

- **Median wing injuries per load: 5.7%** — an order of magnitude worse than any
  other body region. Injuries to legs, breast, and shoulders were each **< 1% per load**.

Sources: [The Influence of Welfare Training on Bird Welfare and Carcass Quality](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6719098/) and industry processing guidance.

- **90% of bruising occurs in the 12–24 hours before processing** — i.e. during
  catching, loading, transport, and shackling, not during grow-out.
- Bruise distribution by body region: **breast 42%, wings 33%, legs 25%.**
- Damage points specific to wings: live production, harvest/catching, tipping,
  shackling, stunning, bleeding, and picking/defeathering.

**Why this matters more than it looks:** wings are the single most-damaged part of
the bird. A damaged wing is downgraded out of the intact-wing stream. So the number
of *sellable whole wings* is meaningfully below 2 per slaughtered bird, which pushes
the required bird count above the naive floor.

**Confidence: medium.** The 5.7% figure is a median across loads in one study, with
wide load-to-load variance. Treat as lo/mode/hi, not a point estimate.

---

## 5. Industry structure

Sources: [WATTPoultry Top Broiler Companies](https://www.wattagnet.com/broilers-turkeys/processing-slaughter/article/15516740/top-10-us-chicken-producers-grow-in-new-directions-wattagnet),
[NCC Broiler Chicken Industry Key Facts](https://www.nationalchickencouncil.org/about-the-industry/statistics/broiler-chicken-industry-key-facts/)

| Producer | US market share |
|---|---:|
| Tyson Foods | 21.3% |
| Pilgrim's Pride | 15.8% |
| Wayne-Sanderson Farms | 14.4% |
| *Top 4 combined* | *~58%* |

- Tyson processes **~45 million birds/week**.
- Wayne-Sanderson: ~1,071.2 million birds/year, 23 processing facilities across 7 states.
- Industry-wide: **~180 slaughter/evisceration plants**, ~30 federally inspected
  vertically integrated companies, ~25,000 contract family farms.

Wayne-Sanderson is the product of the **2022 Sanderson Farms + Wayne Farms merger**,
which increased top-4 concentration.

**Still needed:** FSIS establishment numbers per plant, and each plant's bird size
program. The [FSIS Meat, Poultry and Egg Product Inspection Directory](https://www.fsis.usda.gov/inspection/apply-grant-inspection/meat-poultry-egg-inspection-directory)
is the public source for establishment-level data.

---

## 6. The mixing cascade — why 12 wings ≈ 12 chickens

This is the conceptual core of the project.

**Mixing begins the instant the wings are separated from the bird.** On the cut-up
line, a bird's left and right wing drop onto a shared conveyor and immediately
diverge. They are then *actively* separated by size grading. The two wings of one
chicken essentially never travel together again.

Stages, each of which only ever *increases* the pool:

1. **Cut-up line / wing separation** — first and most important mixing point
2. **Wing chiller / drum** — bulk commingling in water or air
3. **Size grading** (jumbo / large / medium, by count-per-pound) — *actively splits*
   a bird's two wings into different streams if they differ in weight
4. **Combo bin** (bulk container, commonly ~2,000 lb)
5. **IQF freezer tunnel** — continuous flow, no lot boundaries preserved
6. **Case pack / box**
7. **Distributor warehouse / pallet**
8. **Restaurant walk-in freezer bin** — restocked from multiple boxes, often
   multiple deliveries
9. **Fryer basket / the order itself**

### The math

Draw `n` wings from a pool containing `B` birds, each contributing 2 wings
(2B wings total). Expected number of *distinct* birds represented:

```
E[distinct] = B × [ 1 − C(2B−2, n) / C(2B, n) ]
```

For n = 12 whole wings:

| Pool size B (birds) | E[distinct chickens] | Scenario |
|---:|---:|---|
| 6 | 6.0000 | You break down exactly 6 birds yourself |
| 7 | 6.9231 | Tiny batch |
| 10 | 8.5263 | Very small batch |
| 12 | 9.1304 | Small batch |
| 25 | 10.6531 | Butcher-scale |
| 50 | 11.3333 | Single-restaurant small lot |
| 100 | 11.6683 | Small lot |
| 1,000 | 11.9670 | One combo bin |
| 40,000 | 11.9992 | One plant shift |
| 1,000,000 | 12.0000 | Effectively the limit |

Verified numerically. The curve rises steeply then flattens hard — by 100 birds
you are already at 11.67, and everything past ~1,000 is indistinguishable from 12
for practical purposes.

**Conclusion: 6 is a hard floor, but it is only reachable by hand.** For anything
that passed through a commodity supply chain, the answer is pinned just under 12.
The size-grading step makes this even stronger than the formula suggests, because it
is not random shuffling — it is deliberate separation of a bird's two wings.

The interesting output of the program is therefore not a single number but
**where in the 6–12 band you land, and which mixing stage put you there.**

---

## 7. Open research items

- [ ] FSIS establishment numbers and plant-level bird size programs
- [ ] Transport DOA (dead-on-arrival) rate — sought, not yet sourced
- [ ] Ante-mortem condemnation rate for young chickens specifically
- [ ] Wing count-per-pound grading bands (jumbo / large / medium)
- [ ] Cook loss / yield for fried wings
- [ ] Marinade and glaze pickup (can be *negative* loss — adds weight)
- [ ] Imported wing volume (Brazil) as a share of US wing supply
- [ ] Combo bin and case pack standard sizes, to ground pool sizes in stage 6
