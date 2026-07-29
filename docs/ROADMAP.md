# Roadmap

Captured from the "Chicken Scratch" note, 2026-07-28, and organised into
milestones around a **v1.0** release.

The organising principle: **v1.0 is the complete, polished US picture.**
International data, the Discord bot, and anything gated on data we cannot
currently get are deliberately after 1.0, so the release is not held hostage
to a source that may not exist.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done ·
`[!]` blocked or constrained by data availability

---

## Where we are now

| | |
|---|---|
| Deployed | https://counting-chicken-wings.onrender.com/ — live, 200 OK |
| Cold start | 12–23s (Render free tier spins down; see M4) |
| Tests | 156 passing (model 28, scientific 31, build 23, api 47, db 27) |
| Facts | 31 |
| Sources | 30 — 5 cited by nothing yet |
| Loss factors | 14, of which 8 are unsourced estimates (5 affect the count) |
| States with data | 22 |
| Products | whole wing, boneless wing |
| Unreachable data | nutrition, resource_footprint, economic_stat — built and cited, no API or UI |

---

## M1 — Data completeness (US)

The biggest single lever on the project's credibility. Everything here is
data, not code.

- [~] **Remaining US states.** NASS reports broilers slaughtered in **40
  states** but publishes only **22** individually — the rest are suppressed
  under disclosure rules precisely because too few companies operate there.

  **The ceiling is softer than it first looked.** Suppression is decided per
  publication and per year, so the union across sources is larger than any
  one of them. Adding the NASS *Poultry - Production and Value* summary took
  coverage to **23 states**: Florida is named there for 2024 and appears in
  no year of the slaughter summary. Louisiana and Florida are both named in
  2024 and suppressed in 2025, which is the pattern in miniature.

  That publication also **independently confirms** the state live weights we
  already had — production pounds over head reproduces the slaughter
  average for all 14 states the 2025 table names. Locked in as
  `tests/test_cross_validation.py`.

  Remaining routes, in order of promise:
  1. **NASS QuickStats API** — needs a free key from quickstats.nass.usda.gov
     (George has to register; it takes a minute). Suppression is a legal
     disclosure rule rather than a formatting choice, so it will likely
     apply there too — but it may expose series the PDF aggregates away,
     and it is cheap to test once there is a key.
  2. **Back years of both publications.** Each additional year is another
     roll of the suppression dice. Cheapest remaining win by far, and the
     parser already handles multi-year tables.
  3. FSIS Meat, Poultry and Egg Inspection Directory — gives which states
     have plants, and plant counts, even where volume is suppressed
  4. State departments of agriculture for the larger missing states

  Accept that some states may only ever have presence, not volume, and
  render them differently on the map rather than leaving them blank. The
  Production and Value footnotes **name** the suppressed states, so "known
  producer, volume withheld" is renderable today.

- [ ] **US regions.** Roll states into regions (Southeast, Delmarva, Mid-South,
  Midwest, Northeast, West). Regions are also the honest way to show
  suppressed states: a state with no published figure can still contribute to
  a regional total. Turns a data limitation into a feature.

- [ ] **Data by producer.** Extend beyond the three producers currently held.
  Target Perdue, Koch, Mountaire, Foster Farms, House of Raeford, Case Farms.
  Market share, throughput, plant count, states of operation.

- [!] **Independent and small producers.** Explicitly wanted, and the hardest
  ask in the whole roadmap — small operators are exactly who NASS disclosure
  rules protect. Realistic sources: FSIS directory (small plants are listed
  even when volumes are not), USDA Certified Organic and Animal Welfare
  Approved registries, and state ag directories. Expect qualitative coverage,
  not comparable statistics. Say so on the page rather than implying parity.

- [ ] **Breeds.** Ross 308, Cobb 500, Hubbard, plus heritage and slow-growing
  strains. Growth rate, feed conversion, breast yield, wing yield, mortality,
  and myopathy susceptibility. We already have the eight-strain yield study as
  a starting point. The interesting question: how much of "modern broiler
  performance" is genetics versus husbandry?

- [ ] **Imports.** Wings arrive from Brazil and Chile, especially around demand
  spikes. Imported wings come from entirely different flocks under different
  regulatory regimes, so **none of our USDA loss figures legitimately apply to
  them.** Needs its own loss chain, or an explicit refusal to model them.
  Sources: USDA FAS import data, ABPA for Brazil.

- [ ] **Seasonality.** We already load month-by-month NASS live weights for all
  22 states and currently only surface annual averages. Summer heat raises both
  DOA and condemnation; the Super Bowl tightens wing supply enough to change
  grade mix and import share. The monthly data is sitting in
  `regional_size_stat` unused — this is the cheapest unexploited data in the
  project.

---

## M1.5 — Model fidelity

Gaps in what the model can *express*, as opposed to gaps in the data. Listed
separately because these need code, and one of them is a genuine design flaw.

- [ ] **Channel-aware loss stages.** *This is a real architectural gap.*
  `supply_chain` currently selects which **mixing** stages apply but has no
  say over which **loss** stages apply. So the grocery path and the restaurant
  path cannot be modelled properly: `retail_shrink` is parked as
  `optional`/default-off purely to stop it double-counting against
  `kitchen_loss`, which is a workaround, not a model. Fix is a
  `supply_chain_loss_stage` join table so a chain declares its own loss chain.
  Until then, "grocery vs restaurant" is a manual flag rather than a real
  scenario.

- [ ] **Stunning method: CAS vs electrical waterbath.** The most promising
  unexplored factor in the model. Controlled-atmosphere stunning does not
  shackle live birds; electrical waterbath stunning does, and live shackling is
  a leading cause of wing damage. Since wing damage is the **largest
  count-affecting loss we have**, this plausibly moves the headline number more
  than anything else on this list. Producer-specific and researchable.

- [ ] **Line speed.** FSIS grants evisceration line-speed waivers and publishes
  which establishments hold them. Faster lines plausibly mean more damage —
  testable against the wing-damage figure.

- [ ] **Fresh vs frozen.** Probably the largest single lever on the *distinct*
  count, which nothing else on this list touches. Fresh wings move through a
  short, fast chain with far less pooling; IQF frozen product passes more mixing
  stages and sits longer. Fresh should land measurably lower on the 6–12 band.
  Also covers pre-portioned supplier bags (the draw pool becomes the bag, not
  the bin) and multi-distributor sourcing (roughly doubles the pool).

- [ ] **Catching method.** Mechanical harvesters vs hand-catching crews have
  different injury profiles.

---

## M2 — Content and analysis

Where the project earns repeat visits rather than one look.

- [ ] **"Why are chickens fatter in some states — and is fatter better?"**
  A flagship analysis piece, and we can already answer most of it:
  - *Why:* Ohio 4.6 lb vs North Carolina 8.4 lb is not biology, it is market
    segment. Small-bird programs serve fast food and tray pack; big-bird
    programs serve deboning and further processing.
  - *Is fatter better:* **No, and we have the evidence.** Big birds give more
    meat per bird and better processing economics, but myopathy risk rises
    with live weight — white striping affects 96% of fillets and severe woody
    breast ~12%, concentrated in exactly the heavy deboning flocks. Bigger
    birds also carry more wing damage risk from handling mass.
  - The honest conclusion: fatter is better for *yield per bird* and worse for
    *meat quality per pound*. The industry has traded one for the other, and
    the trade is visible in the data we already hold.

- [ ] **Chicken manure.** Genuinely rich subject and nobody expects it. Litter
  as fertiliser (N-P-K values), tonnage per bird per cycle, its role in
  Delmarva and Chesapeake Bay nutrient runoff, litter as biomass fuel, and the
  economics of litter as a secondary income stream for growers. Ties directly
  into the resource-footprint work already done.

- [ ] **USDA programs and support.** FSA loans, EQIP cost-share for litter
  management and housing upgrades, the Packers and Stockyards Act, and the
  January 2025 AMS grower-payment rule already flagged in RESEARCH.md.
  Answers "what does the government actually do here?"

---

## M3 — Presentation and identity

- [ ] **Interactive / slideshow facts page.** Current page is a flat list of
  31 facts. Options, cheapest first: card deck with keyboard and swipe
  navigation; filter by surprise rating; "random fact" button; a "did you
  know" that cycles. Recommend the card deck — it suits the existing
  surprise-ranked data with no new data model.

- [ ] **ASCII chicken and project logo.** Wanted explicitly. ASCII art is
  zero-risk on copyright since we author it, works in the CLI banner *and*
  the web header, and suits the project's tone. Do this before hunting for
  images.

- [ ] **Fact voting: upvote, downvote, and a like button — no dislike.**
  *From the note, missing on first capture.* Two separate signals, and the note
  is precise about why they are separate:
  - **Upvote / downvote = accuracy.** "Outsource accuracy" — let readers flag
    figures that look wrong. This is genuinely valuable here, because 8 of 14
    loss factors are unsourced estimates and readers who work in the industry
    will spot bad numbers faster than we will.
  - **Like = enjoyment**, with deliberately **no dislike**. Nothing to gain from
    letting people register that a fact bored them.

  Design notes: needs a `fact_vote` table, and a decision on identity — anonymous
  votes are trivially gameable, but requiring accounts on a project like this
  will kill participation. Recommend anonymous with rate limiting, and treat the
  result as a **triage queue for us**, never as a published score. A downvote
  should open a research task, not silently change what the page claims.
  Pairs naturally with the card deck above.

- [ ] **Graphics upgrade without copyright risk.** Ranked by safety:
  1. **Author our own** — ASCII, CSS/SVG shapes, generated diagrams. Zero risk.
  2. **Public domain** — USDA and other federal imagery is public domain by
     statute and is *on topic*. Best source of real photographs here.
  3. **CC0 / Unsplash / Pexels** — permissive but verify each licence.
  4. Never scrape image search results.
  Recommend 1 + 2: a self-drawn identity plus genuine USDA photography.

---

## M4 — v1.0 release

- [ ] **Define and cut v1.0.** Gate: M1 data complete or explicitly bounded,
  M2 analysis pieces live, M3 identity done. Tag `v1.0.0`, write release
  notes, update README status.

- [ ] **Deployment hardening.** Currently ~23s cold start on Render free tier.
  Options: accept it and add a loading state so it doesn't look broken;
  external ping to keep warm; or paid tier. Recommend a loading state first —
  cheapest, and honest about what is happening.

- [ ] **Plotly is loaded from CDN.** Works, but a public deployment now depends
  on `cdn.plot.ly` staying up and on the client having network access to it.
  Decide: vendor it locally, or accept the dependency and document it.

- [ ] **Data exports as .txt / .csv.** From the note: emit the fact sheets and
  data tables into the repo as plain text and CSV, chunked small, so local
  models can read them fast. This is genuinely useful beyond the AI use case —
  it makes the dataset citable and reusable by anyone. Add `wings export`
  writing to `data/exports/`.

- [ ] **Messy-table parser.** A reusable version of the ad-hoc NASS PDF parser
  already written, generalised to turn agricultural PDF and HTML tables into
  small clean fragments. Would have saved real time on the NASS work and will
  pay off again on every new state and country source.

---

## M4.5 — Eggs

> *"How many chickens to make this dozen eggs! Commercial, small farm, free
> range etc, this is deep!"* — from the note, missing on first capture.

He is right that it is deep, and it is the most interesting thing on this
roadmap, because **eggs break an assumption the model currently makes.**

- [ ] **The floor becomes 1, not 12.** A hen lays repeatedly. One hen can
  produce an entire dozen, so the hard floor for a dozen eggs is **one
  chicken** — where a dozen wings can never come from fewer than six. Same
  question, same 1-to-n band structure, completely different floor. That
  contrast is a better teaching device than anything currently on the facts page.

- [!] **`units_per_individual` stops being a constant and becomes a RATE.**
  *This is a schema gap, not just new data.* Two wings per chicken is
  timeless. "About 300 eggs per hen" is 300 eggs **per year** — meaningless
  without a time window. The schema has `yield_mode` of `countable` or
  `continuous` and no notion of production over time at all. Options:
  1. Add `yield_mode: 'recurring'` plus a period field. Most honest.
  2. Store eggs-per-hen-per-year and let the question always be
     "per laying cycle". Cheaper, hides the assumption.
  Recommend option 1 — the whole project's credibility rests on not hiding
  assumptions, and this one is load-bearing.

- [ ] **Layers are not broilers.** A different bird, a different industry, and
  largely different sources. Laying strains (Hy-Line, Lohmann, ISA Brown) are
  bred for eggs, not meat. Needs a new `species` row and its own production
  programs — this is exactly the generalisation the schema was built for, so
  it is a fair test of whether that work paid off.

- [ ] **Production system is the headline variable, and it is already named in
  the note.** Commercial cage / cage-free / free range / pasture-raised /
  backyard. Unlike wings, where the interesting variable is *mixing*, for eggs
  the interesting variable is *flock size*:
  - Commercial house: 100,000+ hens, eggs onto belts, graded by weight, packed
    by machine. A dozen eggs is plausibly **12 different hens** — the same
    near-ceiling result as commodity wings, by the same mechanism.
  - Backyard flock of six: a dozen eggs gathered over a week comes from
    **about six hens**, and you could name them.
  So the 1-to-12 band maps onto production system almost perfectly.

- [ ] **Data availability is good.** NASS publishes **Chickens and Eggs**
  monthly — layer inventory, eggs produced, rate of lay, by state. That is a
  better cadence than the annual slaughter summary we currently lean on, and
  the messy-table parser from M4 should handle it. USDA AMS covers shell egg
  grading and the marketing claims behind cage-free and free range.

- [ ] **Egg-specific loss chain.** Cracks and checks at grading, wash loss,
  candling rejects, and retail breakage. Genuinely different from anything in
  the wing chain, and it needs the channel-aware loss stages from M1.5 to be
  in place first.

---

## M5 — After 1.0

- [ ] **Turkey.** *Stated from the outset as the second species, and it was
  missing from this roadmap entirely — flagged on review.* The schema was
  generalised specifically so this is data rather than a migration:
  `species.turkey` is already seeded with `active: 0`, waiting on figures.

  Most of the source work is already done and simply not extracted. The same
  NASS Poultry Slaughter summary we parse for broilers reports **Young Turkeys**
  in parallel tables — head slaughtered, live weight, pounds certified, and
  post-mortem condemnation — so the national anchor and the derived dressing
  yield come almost free. `tools/parse_nass.py` needs pointing at the turkey
  page ranges, not rewriting.

  What genuinely differs and must not be inherited from chicken:
  - Turkeys are far heavier (~30+ lb live against 6.62 lb), so every mass-based
    figure changes even though the wing *count* floor stays at 2 per bird.
  - Turkey wings are rarely sold as wings — they go to further processing, deli
    meat, and stock. The interesting turkey question is probably breast, not
    wings, which is a good test of whether the product abstraction really holds.
  - Grow-out is ~14-20 weeks against 47 days, with its own mortality profile.
  - NCC has no turkey series; the National Turkey Federation is the analogue.

  Do **not** copy chicken loss factors across. Wing damage, condemnation, and
  mixing pool sizes all need turkey-specific sourcing or an explicit note that
  a figure is chicken-derived.

- [ ] **Repo governance: branch protection.** Requires GitHub Pro on a private
  repo — both the classic branch-protection and rulesets APIs return 403 on the
  current plan. `.github/CODEOWNERS` is already in place and auto-requests
  George's review on every PR, but nothing *blocks* a merge yet. Revisit when
  Pro is added; the config to apply is settled (require PR, require Code Owner
  review, 1 approval, admins exempt so solo work is not deadlocked).

- [!] **International: country selector, top 50 max.** Only countries with
  readily available data, per the note. Realistic tiers: FAOSTAT gives
  production for nearly every country; slaughter *and* processing loss detail
  exists for maybe a dozen (EU via Eurostat, Brazil via ABPA, UK via DEFRA).
  Design the selector so a country can be present with production-only data
  and be honest that the loss chain is US-derived. **Do not silently apply US
  loss factors to Brazilian birds.**

- [ ] **Chicken facts Discord bot.** Consumes the existing API. The API is
  already the right shape for it — `/api/facts` and `/api/calculate` are all a
  bot needs. Genuinely small once v1.0 is stable.

---

## Environment notes

- PyCharm is now available on the machine for working on this project.
- Local models and additional hardware are being added; the `.txt`/`.csv`
  export task in M4 is the enabling piece for that.

---

## Housekeeping

- [ ] **README status section is stale.** It claims 21 tests and "7 of 12 loss
  factors are unsourced estimates"; actual is 156 tests and 8 of 14. Since the
  README's credibility rests on being honest about data quality, a wrong count
  there is worse than no count. Consider generating that section from
  `audit.py` output so it cannot drift again.

- [ ] **Unreachable data has no route to the user.** `nutrition`,
  `resource_footprint`, and `economic_stat` are built and cited but exposed by
  neither the API nor the UI. Either surface them or mark them explicitly
  deferred — cited data nobody can see is cost without benefit.

- [ ] **Five sources are cited by nothing.** The audit reports these. Each is
  either a research lead not yet used or a leftover from a dropped fact; worth
  triaging which.

---

## Sequencing recommendation

1. **M3 identity first** — ASCII logo and the facts card deck are fast, visible,
   and make every subsequent demo better.
2. **M2 "is fatter better"** — highest payoff per unit effort, since the data
   is already in the database.
3. **M1.5 channel-aware loss stages** — promoted, because it is a genuine design
   flaw rather than a missing feature. It is also small, and it unblocks any
   honest treatment of retail vs foodservice vs imports.
4. **M1 seasonality** — cheapest data win available: the monthly series is
   already loaded and unused.
5. **M1 data** — the long pole. Start with regions and producers, which are
   unblocked; treat the suppressed states as bounded rather than open.
6. **M4 cut 1.0.**
7. **M4.5 eggs** — see the argument below for why this outranks turkey.
8. **M5 turkey**, then international once 1.0 is stable.

Two judgement calls worth revisiting:

**Fresh vs frozen (M1.5)** is the only item on the list that moves the
*distinct* number, which is the project's headline answer. Everything else
refines birds-required. If the distinct figure is the point, that item deserves
to be earlier than its milestone suggests.

**Eggs should probably come before turkey**, despite turkey being named first.
Eggs are the same species, so no new husbandry research is needed; NASS
publishes egg data *monthly* rather than annually; and the floor-of-1 versus
floor-of-6 contrast is the single best teaching device available to the project.
Turkey mostly re-runs the wing analysis on a bigger bird, whereas eggs force a
real schema improvement — production as a rate over time — that the project
needs anyway before it can ever touch milk or honey. Eggs are the harder and
more valuable piece of work.
