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

## 7. What the "chunks" actually are

Tyson files the product line as **"boneless wings & chunks"**, which invites the
question of whether *chunks* are a different cut that might contain wing meat.

They are not. The ingredient statement across the line reads:

> boneless, skinless chicken **breast** chunks **with rib meat**

Source: [Tyson Foodservice product line](https://www.tysonfoodservice.com/products/tyson/chicken/boneless-wings--chunks/00023700035608)

**"With rib meat" is the phrase to understand here**, because it sounds like a
different cut sneaking in. It isn't. Rib meat is the portion left attached to the
breast when the bird is deboned — part of the front quarter. FSIS permits a
specified amount to remain on a boneless breast. It is not wing, not thigh, and
not mechanically separated meat.

So `named_part_content = 0.0` holds for both boneless wings *and* chunks: neither
contains any wing meat.

### "Wings" is a regulated term

Source: [FSIS Food Standards and Labeling Policy Book](https://www.usda.gov/sites/default/files/guidance-documents/FSIS-GD-2005-0003-Food-Standards-and-Labeling-Policy-Book.pdf)

A product labelled *wings* must be the entire wing, all muscle and skin intact,
with only the tip removable. Where bone has been removed, the product name must
disclose it. "Boneless wing" satisfies that rule — the label is not a loophole,
it is doing what the regulation asks. Which is precisely why a name containing no
wing meat survives regulatory scrutiny.

The policy book also defines **solid muscle** vs **chunked and formed** vs
**ground and formed**. Tyson's is "whole muscle", the strongest of the three —
real intact breast, not a reformed slurry. Worth stating, because the honest
criticism of boneless wings is the *name*, not the meat quality.

---

## 8. Disease and historical shocks

### Avian influenza is an egg story, not a wing story

Sources: [CRS R48518](https://www.congress.gov/crs-product/R48518),
[APHIS HPAI detections](https://www.aphis.usda.gov/livestock-poultry-disease/avian/avian-influenza/hpai-detections/commercial-backyard-flocks)

168.62 million birds lost across 1,689 flocks between 2022 and April 2025. Split
by sector:

| Sector | Share of losses |
|---|---:|
| Table-egg layers | ~75% |
| Turkeys | ~11% |
| **Broilers** | **~8%** |

That is roughly 4.5 million broilers a year against **9.58 billion** slaughtered —
about **0.05%**. Broilers are less exposed because they live only ~47 days, sit on
smaller farms, and are restocked quickly after a depopulation.

**Modelling conclusion: HPAI does not get a loss stage.** It is a price-and-supply
event for eggs, and at 0.05% of broiler throughput it sits well inside the noise
of every other factor in the chain. Adding it would imply a precision we do not
have. Noted here so the omission is a decision rather than an oversight.

### Breast myopathies — the boneless-only problem

Source: [PLOS ONE, Ontario prevalence study](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0267019)

| Condition | Prevalence |
|---|---:|
| White striping | **96.0%** |
| Spaghetti meat | 36.3% |
| Severe woody breast | 11.8% |
| Fillets with >1 myopathy | 85.1% |

Woody breast rose from ~5% in 2012 to 29% by 2015. **Risk increases with live
weight**, so big-bird deboning flocks are the worst affected — and those are
exactly the birds boneless product comes from.

**This is a genuine asymmetry between the two products.** A bone-in wing loses
~5.7% to *handling damage*. A boneless "wing" is drawn from a breast supply with
a *muscle-quality* problem affecting nearly every fillet. Wings are small working
muscles and do not develop these myopathies at all — the modern broiler's breast
grew fast enough to outrun its own blood supply; its wings did not.

---

## 9. Resource footprint

Source: [NCC Broiler Production System LCA, 2020 Update](https://www.nationalchickencouncil.org/wp-content/uploads/2021/09/Broiler-Production-System-LCA_2020-Update.pdf)

Reference flow: one broiler at **6.37 lb live weight**.

| Metric | Per bird | Per kg LW | 2010→2020 |
|---|---:|---:|---:|
| Global warming (kg CO₂ eq) | 2.90 | 1.00 | −18.1% |
| Land use (m²a crop eq) | 5.26 | 1.85 | −13.0% |
| Water (m³) | 0.73 | 0.25 | −13.0% |
| Fossil resources (kg oil eq) | 0.61 | 0.21 | −22.1% |
| Fine particulates (g PM2.5 eq) | 5.87 | 2.03 | −13.8% |

The report also gives **1.053 baby chicks per broiler produced** to cover
mortality — an independent corroboration of our `farm_mortality` stage (5.3%
implies 1.056).

### Allocation is the thing to get right

**A dozen wings does not carry six birds' worth of footprint.** Wings are ~7.3%
of live weight; the breast, thighs, and drums went onto other people's plates.

- Naive: 6 birds × 2.90 kg = **17.4 kg CO₂e** — wrong by ~14×
- Mass-allocated: ≈ **1.3 kg CO₂e**

Mass allocation is the conservative standard. **Economic allocation would give a
higher number**, because wings sell at a premium per pound relative to the rest
of the carcass. The model uses mass and says so, rather than quietly picking the
flattering one.

Feed, derived from FCR 1.69 × 6.57 lb market weight: **~11 lb per bird**, so ~67 lb
across six birds, of which the wings' honest share is **~4.9 lb**.

---

## 10. Economic impact

Sources: [ERS grower fees](http://www.ers.usda.gov/data-products/charts-of-note/chart-detail?chartId=104642),
[Poultry Site contract economics](https://www.thepoultrysite.com/articles/contract-broiler-production-questions-and-answers),
[NCC key facts](https://www.nationalchickencouncil.org/about-the-industry/statistics/broiler-chicken-industry-key-facts/)

- **Grower pay: 3.8–4.6 ¢ per lb live weight**, set by a relative *tournament*
  system — a farm's rate depends on its performance against other farms
  delivering the same week, so identical work can be paid differently.
- Six birds at 6.62 lb = 39.7 lb → grower received **~$1.67** for raising them.
  Allocated to the wings alone: **~12 cents**.
- A 20,000 sq ft house grosses **$34–40k/yr** against **$28–30k** of costs,
  leaving **$6–12k** to land, labour, and management during the 15-year mortgage.
- **355,000 direct workers**, ~1.2 million indirect, **~25,000 contract family
  farms**, **~180 plants**.

A USDA AMS rule proposed in January 2025 would end negative performance-based pay
adjustments and guarantee a minimum base rate. Worth tracking — if finalised it
changes the grower-pay figure structurally, not just numerically.

---

## 11. Open research items

- [ ] FSIS establishment numbers and plant-level bird size programs
- [ ] **Producer-level processing differences** — Tyson vs Pilgrim's vs
      Wayne-Sanderson line speeds, chiller type (air vs immersion), and whether
      loss rates differ enough to justify per-producer factors
- [ ] Transport DOA (dead-on-arrival) rate — sought, not yet sourced
- [ ] Ante-mortem condemnation rate for young chickens specifically
- [ ] Wing count-per-pound grading bands (jumbo / large / medium)
- [ ] Cook loss / yield for fried wings
- [ ] Marinade and glaze pickup (can be *negative* loss — adds weight)
- [ ] Imported wing volume (Brazil) as a share of US wing supply
- [ ] Combo bin and case pack standard sizes, to ground pool sizes
- [ ] Sodium, saturated fat, and cholesterol for both wing preparations —
      currently only kcal / protein / fat / carbohydrate are populated
- [ ] Whether myopathy rates justify a boneless-specific downgrade loss stage
