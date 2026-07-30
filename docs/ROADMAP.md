# Roadmap

Captured from the "Chicken Scratch" note, 2026-07-28, and organised into
milestones around a **v1.0** release. **Re-read against the note 2026-07-29**,
after v1.0 through v1.2 shipped.

The organising principle held: **v1.0 was the complete, polished US picture**,
and international data, the Discord bot, and anything gated on unavailable data
stayed after it. Post-1.0 the note has three items that had never been
captured at all — localization, an ingestion adapter layer, and the project's
comic voice — plus one thing the note does not mention because it came later:
the project now answers the same question about things that are not chickens.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done ·
`[!]` blocked or constrained by data availability

---

## Where we are now

Verified 2026-07-30 against the working tree, not carried forward from the last
edit of this file.

| | |
|---|---|
| Released | **v1.7.0**, 2026-07-30 — seasonality. Seven releases in two days, and v1.5.0/v1.6.0 the same day were a concurrent session's Israel work; see [CHANGELOG](../CHANGELOG.md) |
| Deployed | https://counting-chicken-wings.onrender.com/ — auto-deploys `master`, so the site is normally *ahead* of the latest tag. Ask `GET /api/version` |
| Cold start | ~21s after ~15 min idle. `/healthz` exists for an external keep-warm cron; the only real fixes are `plan: starter` ($7/mo) or Fly.io |
| Render CPU | **11–13× slower than the laptop.** Not architecture — the app boots in 0.28s. Scientific mode's Monte Carlo default dropped to 2,000 iterations because of it |
| Tests | 368 collected |
| Corpus counts | **Do not hand-maintain these.** `python -m counting_chicken_wings.audit --stats` prints sources, facts, products and the estimate ratio, and the README block is generated from it. As of v1.7.0: 49 sources, 55 facts |
| Loss factors | **21**, of which **11 are unsourced estimates (52%)** and **8 affect the count**. Worse than the 8-of-14 this file used to claim — the ratio got worse as eggs and saffron were added, which is what a new domain with no federal survey behind it does |
| Mixing stages | 21 |
| States with data | 23 broiler (22 slaughter + Florida from production); 34 egg (union across two years) |
| Species | broiler, layer hen, saffron crocus. Turkey seeded `active: 0` |
| Products | whole wing, boneless wing, table egg, saffron stigma, saffron gram |
| Countries | USA and **Israel**, both with data. Israel: CBS output, value, a flock series to 1960, 47 districts, plus an `industry`-grade head count. `min_confidence=measured` gives the government-only reading |
| GUI views | 11 tabs, including scientific mode, By country and Seasons |
| Exports | `wings export` → .txt/.csv into `data/exports/` |
| Research pipeline | COOPER work-orders under `docs/research/` — batch 01 saffron run; 02 vanilla, 03 wagyu, 04 honey and 05 Israel-Hebrew drafted. Source library at `docs/research/library/` |

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

- [x] **Seasonality of bird weight.** *Shipped in v1.7.0.* It was the cheapest
  unexploited data in the project and it paid off as a **negative result with a
  second-order positive one behind it**: the swing is 2.7% nationally and no
  single series — not one of the 22 states, not the national one — can be told
  apart from twelve noisy numbers. But 13 of 22 states peak in August–October
  against 5.5 expected by chance, so the states agree even though none of them
  is evidence on its own.

  Two lessons worth keeping. **A range over twelve numbers is not a season**,
  and finding out required three tests rather than one: Texas shipped as "the
  one seasonal state" on the strength of a single June, because a flat year with
  one dip scores *exactly* the ideal-cycle score on amplitude over jitter. And
  **the thresholds are ours, not a source's**, so the classification is graded
  `estimate` while the weights it reads are `measured`.

  Seasonality is deliberately not wired into the count — see the item below for
  what that would take.

- [ ] **Monthly volume, condemnation and DOA — what seasonality actually needs
  to move the count.** *Opened by v1.7.0, which could only do weight.* Weight
  seasonality does not touch the answer: a chicken has two wings in every month.
  The count-affecting seasonal factors are condemnation and dead-on-arrival,
  both plausibly worse in summer heat, and the corpus holds annual figures only.

  The sources exist and are the ones already parsed. NASS *Poultry Slaughter*
  publishes **monthly** national tables — head slaughtered, pounds, and
  post-mortem condemnation — and `tools/parse_nass.py` reads the annual pages of
  that same document. This is a parser pointing job, not a new source hunt, and
  it is the cheapest remaining count-affecting data in the project now that
  weight is done.

  It would also answer the Super Bowl question v1.7.0 had to leave open:
  February is the third-lightest month, so the demand spike is absorbed by
  something that is not bird size. Monthly head slaughtered would say whether
  it is throughput; imports (above) and fresh-vs-frozen (M1.5) are the other two
  candidates.

---

## M1.5 — Model fidelity

Gaps in what the model can *express*, as opposed to gaps in the data. Listed
separately because these need code, and one of them is a genuine design flaw.

- [x] **Channel-aware loss stages.** *Was the one real architectural gap; closed
  2026-07-29 (`4fe60b2`).* Routes now declare their own losses through a
  `supply_chain_loss_stage` join table, and a `grocery_retail` chain
  demonstrates it: foodservice pays `kitchen_loss` and not `retail_shrink`,
  grocery pays the reverse, and a test asserts no route claims both. A chain
  that declares nothing still inherits the species defaults, so nothing that
  existed had to move. `retail_shrink` is no longer parked default-off as a
  workaround — it belongs to one route.

  Worth recording *why* this was the same bug as the egg/wing chain defect one
  level down: in both cases a selector existed for one kind of stage and not
  the other, so the wrong stages were walked and the answer stayed plausible.
  A plausible answer with a fictional audit trail is the failure mode this
  project is built to prevent, and it has now happened twice. **When adding any
  new stage dimension, ask what selects it before asking what the numbers are.**

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

- [x] **"Why are chickens fatter in some states — and is fatter better?"**
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

- [x] **Interactive / slideshow facts page.** Current page is a flat list of
  31 facts. Options, cheapest first: card deck with keyboard and swipe
  navigation; filter by surprise rating; "random fact" button; a "did you
  know" that cycles. Recommend the card deck — it suits the existing
  surprise-ranked data with no new data model.

- [x] **ASCII chicken and project logo.** Wanted explicitly. ASCII art is
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

- [ ] **Voice and wordmark.** *In the note from the start, never captured until
  the 2026-07-29 re-read.* He wrote down a list of jokes: *"What the cluck?",
  "Chicken shit", "the whole clucking thing", "I'm just a cluck away from…"*.

  That is a tone decision, and it is worth treating as one rather than
  sprinkling puns wherever they fit. The project's credibility rests on
  sounding careful about numbers, so the pun budget should be spent in places
  where nobody could mistake it for a claim:
  - **Yes:** page title / tagline, the 404, the CLI banner, section headings on
    the facts deck, the manure piece (where "chicken shit" is also literally
    the subject).
  - **No:** anywhere a figure, a confidence grade, a conflict note, or a source
    citation is being read. A joke next to an `estimate` grade reads as not
    taking the grade seriously.

  "The whole clucking thing" is the best fit for the exports / full-corpus
  download, since that is exactly what it is. Pick one tagline and use it
  consistently rather than rotating them.

---

## M4 — v1.0 release

- [x] **Define and cut v1.0.** Gate: M1 data complete or explicitly bounded,
  M2 analysis pieces live, M3 identity done. Tag `v1.0.0`, write release
  notes, update README status.

- [x] **Deployment hardening.** Currently ~23s cold start on Render free tier.
  Options: accept it and add a loading state so it doesn't look broken;
  external ping to keep warm; or paid tier. Recommend a loading state first —
  cheapest, and honest about what is happening.

- [x] **Plotly is loaded from CDN.** Works, but a public deployment now depends
  on `cdn.plot.ly` staying up and on the client having network access to it.
  Decide: vendor it locally, or accept the dependency and document it.

- [x] **Data exports as .txt / .csv.** From the note: emit the fact sheets and
  data tables into the repo as plain text and CSV, chunked small, so local
  models can read them fast. This is genuinely useful beyond the AI use case —
  it makes the dataset citable and reusable by anyone. Add `wings export`
  writing to `data/exports/`.

- [~] **Messy-table parser.** A reusable version of the ad-hoc NASS PDF parser
  already written, generalised to turn agricultural PDF and HTML tables into
  small clean fragments. Would have saved real time on the NASS work and will
  pay off again on every new state and country source.

  Partly built by accident: `tools/parse_eggs.py` and
  `tools/parse_production_value.py` are the second and third instances of the
  same pattern, and COOPER's fetch stage now has a PDF path with a `pypdf`
  fallback that saved the saffron batch when `pdftotext` failed. Generalising is
  now a consolidation job, not a new build.

- [ ] **Source adapter layer.** *From the note, missing on first capture:*
  > "We need to consider we connect to a lot of API data, we should build an
  > adapter type structure like some saas vendors that connect to a lot of
  > api's have, so we don't have to figure it out each [time]"

  He is right, and the Israel work is the evidence — an hour went into
  discovering that FAOSTAT's API wants an auth header, its bulk host 403s, and
  CBS serves data fine but cannot be browsed for series IDs. None of that
  survived anywhere a second attempt would find it until it was written into
  `docs/ISRAEL-PLAN.md` by hand.

  The shape that fits this project, in order of value:
  1. **A uniform adapter interface** — `discover / fetch / parse / cite` per
     source, so a new country or agency is a new adapter file rather than a new
     one-off script in `tools/`. `fetch_census_states.py`,
     `parse_production_value.py`, `parse_eggs.py` and `parse_nass.py` are four
     adapters written four different ways; they are the migration set.
  2. **Access findings recorded as data, not prose.** Whether a source is
     reachable, and how, is exactly what gets rediscovered. `SOURCE-LIBRARY.md`
     already argues that coverage rather than existence is what a source entry
     is worth — the same argument applies to reachability.
  3. **Retrieval metadata that feeds the audit.** An adapter knows the URL, the
     retrieval date, and the series ID it pulled. Those are the fields
     `sources.yaml` wants anyway, so the adapter should emit them rather than a
     human transcribing them.

  Do **not** let this become a framework before there is a second country. Two
  real adapters (NASS and CBS) is the point at which the shared interface is
  discoverable rather than guessed. Until then, consolidate `tools/`.

---

## M4.5 — Eggs

> *"How many chickens to make this dozen eggs! Commercial, small farm, free
> range etc, this is deep!"* — from the note, missing on first capture.

**Shipped in v1.1.0, and corrected in v1.2.0.** He was right that it is deep,
and it turned out deeper than the capture assumed: the prediction below about
the floor was **wrong in an interesting way**, and finding out why is the best
thing in the milestone.

- [x] **The floor does not become 1 — it becomes 12, and the answer inverts.**
  *The original note-capture reasoning, kept because it was the wrong answer for
  the right reason.* One hen can indeed lay a dozen eggs, so a dozen eggs
  *can* come from one bird. But a hen lays at most about one egg a day, so a
  **same-day** dozen came from exactly **12 different hens** — the floor rises
  to meet the ceiling and mixing has nothing left to move. Wings are the
  opposite: a floor of 6 that mixing pushes *up* toward 12.

  So eggs are not "wings with a lower floor". They are the case where the
  constraint moves from anatomy to *time*, and both floors get reported: 12 is
  physiology, 15.2 is what you actually need, because hens do not lay daily.
  One hen and 15 days also reaches the floor, which wings can never do.

- [x] **`units_per_individual` became a RATE.** Option 1 was taken —
  `yield_mode: 'recurring'` with `yield_period_days: 365` on `table_egg`, so
  "about 300 eggs per hen" carries its window instead of implying one. The
  cheaper option would have hidden exactly the assumption that makes the answer
  interesting.

- [x] **Layers are not broilers.** `layer_hen` is its own `species` row — same
  animal biologically, entirely different industry and sources. The state
  spread proves the point rather than decorating it: Alabama 224 eggs/layer to
  Montana 327 is mostly table-egg versus **hatching-egg mix**, not husbandry
  quality, so the low states are the broiler states.

- [x] **Egg supply chains, after shipping the wrong ones.** v1.1.0 gave eggs no
  mixing stages and no routes, so an egg query fell through to the **wing**
  cascade and walked the cut-up line, wing chiller, size grading and fryer
  basket. The count was right (the per-day cap dominates), the audit trail was
  fiction. v1.2.0 added the real cascade — nest and belt, on-farm cooler,
  washing, candling and grading, carton pack, distributor, retail case, fridge —
  plus three routes, of which only `backyard_eggs` can reach the one-hen floor.

  Also settled a modelling judgement in public: **egg grading is `random`, not
  `separating`.** Weighing wings pulls a bird's pair apart because a bird has
  exactly two; each egg arrives at the grader already alone, so there is no pair
  to break and calling it separating would invent a mechanism.

- [x] **Production system is the headline variable, and it was already named in
  the note.** Commercial cage / cage-free / free range / pasture-raised /
  backyard, all five seeded. Unlike wings, where the interesting variable is
  *mixing*, for eggs the interesting variable is *flock size*:
  - Commercial house: 100,000+ hens, eggs onto belts, graded by weight, packed
    by machine. A dozen eggs is plausibly **12 different hens** — the same
    near-ceiling result as commodity wings, by the same mechanism.
  - Backyard flock of six: a dozen eggs gathered over a week comes from
    **about six hens**, and you could name them.
  So the 1-to-12 band maps onto production system almost perfectly.

- [x] **Data availability was good.** NASS **Chickens and Eggs 2025 Summary**
  parsed by `tools/parse_eggs.py` into `data/stats_states_eggs.yaml`, covering
  34 states as a union across two years — Maryland, South Dakota and Virginia
  are suppressed for 2025 and present for 2024, the same suppression pattern as
  the slaughter summary. `(NA)` becomes an omitted year, never a zero.

- [x] **Egg-specific loss chain.** Five factors, distinct from anything in the
  wing chain. The one worth knowing: breakers-plant diversion is a loss for
  "how many hens for a dozen eggs in a carton" even though nothing is destroyed
  — the egg simply leaves the shell-egg stream.

- [ ] **Remaining egg work.** Monthly cadence is loaded but only annual figures
  are surfaced, exactly as with broiler live weights (see M1 seasonality). USDA
  AMS on shell-egg grading and the marketing claims behind "cage-free" and
  "free range" is still unmined, and it is the part a reader is most likely to
  have an opinion about.

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

- [~] **International: country selector, top 50 max.** Israel is the first
  foreign country with data (v1.3.0) and it already reshapes this item: the
  selector cannot be a plain dropdown, because a country may have production
  without a head count, and switching the calculator's country would then either
  hide the answer or compute it from US assumptions. `/api/countries` returns
  what each country can answer for exactly this reason. Only countries with
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

## M6 — Beyond chicken: the "how many X" generalisation

**Not from the note — this arrived after it.** Recorded here because it landed
on 2026-07-29 in `dabd472` and nothing else in this file mentioned it.

The question generalises: *how many individuals does one unit of a finished
product represent?* Wings answer it with anatomy, eggs with a rate over time,
and **saffron** with neither — which is why saffron went first.

- [x] **Saffron, the first non-animal subject.** Two products, because the
  species answers two different questions: `saffron_stigma` is countable on a
  hard anatomical constant (*Crocus sativus* has exactly three stigmas, the
  direct twin of two wings per chicken), and `saffron_gram` is continuous on a
  ~150-flowers-per-gram ratio. First batch to go the whole way from a COOPER run
  to a live answer, which was the reason to do one subject before scaling to
  more.

- [x] **`yield_mode: continuous` needed real model work, and it exposed a bug.**
  The pooling maths assumed every contributing individual gives at least one
  *whole* unit — true of every poultry product, false of a gram of saffron. For
  a countable product the unit count *is* the ceiling; for a continuous one it
  says nothing, mass being fungible, so the ceiling collapses onto the floor.
  Before this was modelled, one gram returned "about 1 different flower" against
  a floor of 150 in the same output. `Result.distinct_ceiling` now reports it
  rather than each caller recomputing it, and `aggregate_units` is threaded from
  `yield_mode` through CLI and API.

- [x] **"Anatomical floor" is not always anatomical.** Two wings per chicken and
  three stigmas per flower are anatomy, and the trace may fairly grade them
  `measured`. "About 150 flowers per gram" is an extension service's rule of
  thumb; labelling it *Anatomical floor / measured* would claim a grade the
  corpus does not hold. The floor label and confidence now vary, and the floor
  carries its own `source_slug`.

- [ ] **Show the reader that saffron's evidence is weaker — the grades know, the
  page does not.** Wings rest on NASS: national, annual,
  enumerated. Saffron rests on three university extension factsheets, none of
  which surveys anything — there is no NASS for saffron because the US grows
  almost none commercially. Graded `trade_body` rather than `government`
  deliberately, so a 1994 gardening factsheet does not sit in the same tier as
  an enumerated national survey.

  Two unresolved items are stored **as conflicts rather than reconciled**:
  Penn State's ~3 lb/acre against HS661's 8–10 lb/acre "in an established
  planting" (a three-fold spread between two extension services is the most
  honest thing we know about saffron yields), and a teaspoon-to-gram conversion
  that is not loaded because the assumption would be ours, not the source's.

- [ ] **Vanilla, wagyu and honey are drafted, not run.** `batch-02-vanilla`
  (archetype `how-many`), `batch-03-wagyu` (`comparison`) and `batch-04-honey`
  (`how-many` plus a new `provenance-audit`) exist under
  `docs/research/batches/` with **candidate URLs deliberately blank** — COOPER
  fetches exactly what is listed and never searches, so an invented URL fails
  silently and the batch returns empty for a reason nobody can see. Fill them
  from a real search pass before sending.

  Honey is the most interesting of the three and the most dangerous: its
  question is partly *"does anybody actually know?"*, its own draft says two
  items should probably not ship, and a hive is a colony rather than a set of
  countable individuals — so it will test the `continuous` mode the way eggs
  tested `recurring`. Do it after vanilla, which is the plain case.

- [ ] **Decide what this project is called when it is not about chickens.**
  Three domains in and the repo, the CLI (`wings`), the database
  (`chickens.db`) and the deployed hostname all say chicken. Not urgent, and
  renaming for its own sake is not worth it — but decide before a fourth
  domain, and decide *before* the localization work below, since a name is the
  first string anyone translates.

---

## M7 — Localization: EN / FR / HE

> *"Add localization for EN/FR/IL for now, and plan more for future. Mainly
> languages."* — from the note, missing on first capture.

**This supersedes `docs/ISRAEL-PLAN.md`'s "do not translate the UI".** That was
right for a demo and is wrong now that he has asked for it; the plan document
has been updated to point here.

- [ ] **Extract strings before translating anything.** The blocker is not
  translation, it is that user-facing prose is currently hardcoded in
  `cli.py` and `static/index.html` — the egg "why not exactly the floor" prose
  had to be fixed in both places in v1.2.0, which is the same lesson in
  miniature. Nothing can be localized until the strings live in one place.

- [ ] **Distinguish UI chrome from corpus prose, and do not conflate them.**
  This is the decision that makes or breaks the work:
  - **UI chrome** (labels, buttons, tab names, units) — translate freely.
  - **Corpus prose** (`notes:`, fact bodies, conflict explanations, source
    titles) — these are *evidence*, and a translated quotation is no longer a
    quotation. Recommend: translate the surrounding explanation, keep verbatim
    quotes and source titles in their original language with the original
    beside any translation. A figure that traces to a French document should
    show the French.
  - Source titles are already mixed — the Israeli Poultry Board is
    *מועצת הלול* and there is no English publication to cite instead.

- [ ] **"IL" means Hebrew, and Hebrew means RTL.** The note says IL, which is a
  country code; the language is `he`. Hebrew is right-to-left, and that is a
  layout change, not a string swap — Plotly axes, the state choropleth, the
  card deck's swipe direction and every table with a numeric column are all
  affected. Budget for RTL separately from translation, and if only one of the
  two can ship, ship the language without claiming RTL support.

- [ ] **Numbers and units are the real risk.** French uses a comma decimal
  separator and a space thousands separator; a figure rendered `6,62` where a
  reader expects `6.62` is a hundredfold error that looks like a typo. The US
  reports pounds and both other locales expect kilograms, which the Israel
  comparison work already flagged as a 2.2× error that still looks plausible.
  Locale formatting must go through one function, tested.

- [ ] **Plan for more languages without pretending to have them.** Spanish and
  Portuguese are the obvious next two, and Portuguese is genuinely useful —
  Brazil is the import source in M1. But a language selector listing options
  that fall back to English is worse than a short list. Ship what is complete.

---

## Environment notes

- PyCharm is now available on the machine for working on this project.
- Local models and additional hardware are being added; the `.txt`/`.csv`
  export task in M4 is the enabling piece for that.

---

## Housekeeping

- [x] **README corpus figures are generated, after drifting three times.** It had
  said "7 of 12 are unsourced estimates" against an actual **11 of 21** — an
  error in the direction that matters, claiming the data was *better* sourced
  than it is.

  `audit --stats` now emits the block, `tools/update_readme.py` writes it between
  markers, `tests/test_readme.py` fails on drift, and CI runs
  `update_readme.py --check`. Two decisions worth keeping:
  - **The test count is no longer quoted.** It is not a fact about the data, it
    changes almost every commit, and it was most of why the section went stale.
  - **A second test forbids re-quoting the counts outside the block**, because
    the Status section had come to contradict the section two screens above it.

  While there: the Scope section still said "broiler chickens only" three
  subjects in, and now documents all three yield modes.

- [ ] **Unreachable data has no route to the user.** `nutrition`,
  `resource_footprint`, and `economic_stat` are built and cited but exposed by
  neither the API nor the UI. Either surface them or mark them explicitly
  deferred — cited data nobody can see is cost without benefit.

- [~] **Sources cited by nothing: down from five to one.** The audit names
  `psu-extension-saffron`, and that one is deliberate — it is held for a yield
  figure stored as an unresolved conflict, so nothing cites it and nothing
  should. Worth teaching the audit to distinguish "orphaned" from "held as
  evidence of a conflict", since the second will keep happening.

---

## Sequencing recommendation

The pre-1.0 sequence ran as written: identity, then "is fatter better", then
channel-aware loss stages, then the 1.0 cut — with eggs promoted ahead of
turkey, which was the right call for the reason given (eggs forced a real
schema improvement; turkey re-runs the wing analysis on a bigger bird).

**Revised for post-1.2, 2026-07-29.**

1. **Surface the saffron evidence gap in the UI (M6).** Saffron landed in
   `dabd472`, and the corpus now mixes an enumerated federal survey with 1994
   gardening factsheets. The grades already record that; the *page* does not show
   it. A reader who sees a saffron figure rendered exactly like a NASS figure has
   been misled by the presentation, not the data — and that is the one failure
   this project exists to prevent.
2. ~~**README generated from `audit.py`**~~ — done 2026-07-29, see Housekeeping.
3. **M1 seasonality.** Still the cheapest unexploited data in the project, and
   now doubly so — the monthly series is loaded and unused for *both* broiler
   live weights and eggs per layer.
4. **M1.5 fresh vs frozen.** Promoted for the same reason as last time and it
   did not get done: it is the only item that moves the *distinct* number, which
   is the headline answer. Everything else refines birds-required.
5. **M7 string extraction** — the extraction half only, not translation. It is
   the prerequisite for localization *and* it fixes the duplicated-prose problem
   that made the v1.2.0 egg fix touch two files. Do it as cleanup, and
   localization becomes a data task later.
6. **M1 data long pole** — regions and producers, both unblocked. Treat the
   suppressed states as bounded rather than open.
7. **M6 vanilla, then M5 turkey.** Vanilla is now cheaper than turkey: the
   `continuous` machinery will already exist, whereas turkey needs its own
   husbandry sourcing and must not inherit chicken loss factors.
8. **Israel's remaining half is now a UI job, not a data job.** v1.3.0 loaded
   CBS output, inventory and 47 districts; v1.4.0 added the head count at
   `industry` grade, the derived 2.31 kg bird, and six facts including the
   mangal hook. Both readings are queryable — `min_confidence=measured` for the
   government-only picture, the default for the industry one. What is left:
   render the two side by side, and take `batch-05-israel-hebrew.md` to COOPER
   for a *government* head count, a bedikah rejection rate, and a per-capita
   series. Do not ship a per-capita figure until that lands; five sources give
   five numbers 20% apart.
9. **M7 translation and RTL**, then the Discord bot.

Three judgement calls worth revisiting:

**The adapter layer (M4) should wait for the second country, not lead it.** It
is the right idea and the Israel access findings prove the cost of not having
it, but one real adapter is not enough to discover a shared interface. Build
CBS as a one-off, then extract the interface from two working examples.

**Localization and the project's name are entangled.** A name is the first
string anyone translates, and the project is three domains past being about
chickens. Decide the name before paying for translation twice.

**The estimate ratio is going the wrong way** — 11 of 21 loss factors are
unsourced, against 8 of 14 before eggs and saffron. That is the predictable
price of new domains with no federal survey behind them, and it is fine as long
as it is stated. But if it keeps rising, sourcing existing estimates outranks
adding a fourth subject.
