# Roadmap

Captured from the "Chicken Scratch" note, 2026-07-28, and organised into
milestones around a **v1.0** release. **Re-read against the note 2026-07-29**,
after v1.0 through v1.2 shipped, and **re-verified against the working tree
2026-07-31** at v1.11.0 — this file had been left at v1.8.0 and gone four
releases stale, which is the failure the README's generated corpus block
already exists to prevent.

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

Verified 2026-07-31 against the working tree at `e5187ea`, not carried forward
from the last edit of this file — which was the v1.8.0 rollup, four releases
ago. Every count below came from the code or the corpus rather than from the
previous version of this table.

| | |
|---|---|
| Released | **v1.11.0**, 2026-07-31 — variant B of the frontend stops being a byte-copy of the shipped page and becomes a design worth measuring. Since v1.8.0: **v1.9.0** promoted maple, opening the `forestry` domain, **v1.9.1** was a copy edit that moved no figure, **v1.10.0** built the A/B harness. `master` also carries unreleased work on the tag and release pipeline. See [CHANGELOG](../CHANGELOG.md) |
| Deployed | **https://wings.swamplink.com** — moved off Render in `5695099`. A Hetzner CPX11 behind the Caddy that already serves swamplink.com, container bound to `127.0.0.1:8101` and never exposed directly. Still tracks `master`, so the site is normally *ahead* of the latest tag. Ask `GET /api/version` |
| Cold start | **Not a problem any more.** The box is always on, so the 12–23s free-tier spin-up — which no client-side loading state could hide, because the browser had no document yet — and the keep-warm cron it needed are both gone. `/healthz` survives as the deploy gate: `deploy.yml` polls `/api/version` until the pushed SHA is the one serving. `render.yaml` is still in the tree as a provider-agnostic fallback and is **not** what serves |
| Monte Carlo default | Still 2,000 iterations in scientific mode. The reason was Render's CPU — 11–13× slower than the laptop, and not architecture, since the app boots in 0.28s — and that reason left with Render. Worth re-measuring on the CPX11 before treating 2,000 as a constraint rather than a leftover |
| Tests | 490 collected |
| Corpus counts | **Do not hand-maintain these.** `python -m counting_chicken_wings.audit --stats` prints sources, facts, products and the estimate ratio; the README block is generated from it and `tests/test_readme.py` fails on drift. As of v1.11.0: **54 sources**, 55 facts, 6 products across 4 active species, 31 tables |
| Loss factors | **22**, of which **11 are unsourced estimates (50%)** and **8 of those affect the count**, spread across 7 stages. Still worse than the 8-of-14 this file claimed before eggs and saffron, but it has now held at roughly half for three releases — maple arrived without making it worse |
| Mixing stages | 25 |
| States with data | 23 broiler (22 from the slaughter summary + Florida from Production and Value); 34 egg (union across two years) |
| Species | broiler, layer hen, saffron crocus and **sugar maple**, all active. Turkey still seeded `active: 0`, waiting on figures |
| Products | whole wing, boneless wing, table egg, **maple syrup gallon**, saffron stigma, saffron gram — `countable`, `recurring` and `continuous` all represented, and maple is the first `recurring` product whose period is not a year |
| Countries | USA and **Israel**, both with data. Israel: CBS output, value, a flock series to 1960, a `measured` chick-placement series for 2023–24, and 50 regional councils inside 4 districts (**not** 47 districts — `region_level` was added in v1.5.0 precisely so the hierarchy stops being counted as one flat list). The head count itself is `industry`-grade, so `min_confidence=measured` still returns no Israeli slaughter figure, deliberately |
| GUI views | 11, including scientific mode, By country and Seasons — and there are now **two** front ends carrying them |
| Frontend A/B | Two pages on one URL: `static/index.html` is the control, `static/v2/` the redesign, and the element ids are identical across both. **The split defaults to 0**, so deploying does not start the experiment. It runs on swamplink rather than Render, because Render's service has no disk and would lose `metrics.db` on every deploy. The A/A noise floor was never collected before the arms diverged, so anything this reports has no measured baseline |
| Exports | `wings export` → .txt/.csv into `data/exports/` |
| Research pipeline | COOPER work-orders under `docs/research/`: **eleven specs written, eight run.** Two went into the corpus on their own (saffron, maple); a third put figures there only because a human read documents the extractor returned and could not use (Israel, v1.6.0); **four accepted nothing at all** (honey, ground beef, silk, own-loss-factors). Every run has a review record in `docs/research/accepted/`, negatives included — see M6 for the per-batch picture. Source library at `docs/research/library/`, with `docs/research/SOURCE-LIBRARY.md` on top of it |

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
    figures that look wrong. This is genuinely valuable here, because 11 of 22
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
and **saffron** with neither — which is why saffron went first. **Maple** then
answered it with a rate over a period that is not a year, which is what proved
the period was data rather than an assumption.

Four subjects are live — wings, eggs, saffron, maple — across three `domain`
rows (`poultry`, `horticulture`, `forestry`), six products and all three yield
modes. The rest of this milestone is the research pipeline that feeds it, and
most of what that pipeline has produced so far is **negative results** — kept
rather than discarded, because a batch that accepted nothing still cost a run
or two and still says something true about the subject or about us.

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

  **Superseded.** Threading it from `yield_mode` was the wrong condition and it
  shipped: maple is `recurring`, so all three call sites read a gallon of syrup
  as one tree's discrete part and printed a floor of 194 against a ceiling of 1.
  Whether a unit is a blend is a fact about the figures — one individual's whole
  natural output against one whole unit — and it is now derived inside `run()`
  where no caller can hold a copy of it. The lesson generalises past this flag:
  a condition duplicated across CLI, API and analysis route cannot be caught by
  disagreement, because all three copies are wrong together.

- [x] **"Anatomical floor" is not always anatomical.** Two wings per chicken and
  three stigmas per flower are anatomy, and the trace may fairly grade them
  `measured`. "About 150 flowers per gram" is an extension service's rule of
  thumb; labelling it *Anatomical floor / measured* would claim a grade the
  corpus does not hold. The floor label and confidence now vary, and the floor
  carries its own `source_slug`.

- [~] **Show the reader that saffron's evidence is weaker — the grades know, the
  page half does.** Wings rest on NASS: national, annual,
  enumerated. Saffron rests on three university extension factsheets, none of
  which surveys anything — there is no NASS for saffron because the US grows
  almost none commercially. Graded `trade_body` rather than `government`
  deliberately, so a 1994 gardening factsheet does not sit in the same tier as
  an enumerated national survey.

  **v1.8.0 shipped the first half.** Evidence grades render as stamps and an
  estimate is dashed and hatched, so an unsourced figure now looks different
  from a sourced one everywhere it appears, in both themes.

  **The conflicts are still invisible.** The word "conflict" appears zero times
  in either front end — variant A's page, variant B's markup, and `v2/app.js`
  all return 0. Two saffron items are stored **as conflicts rather than
  reconciled** with no route to a reader: Penn State's ~3 lb/acre against
  HS661's 8–10 lb/acre "in an established planting" (a three-fold spread
  between two extension services is the most honest thing we know about saffron
  yields), and a teaspoon-to-gram conversion that is not loaded because the
  assumption would be ours, not the source's. Israel's live-versus-carcass
  tonnage basis from v1.8.0 is in the same position. A stored conflict nobody
  can see is the orphaned-source problem wearing a different hat.

- [x] **Maple, the fourth subject and the third domain.** *Shipped in v1.9.0
  from `batch-07-maple` — the second batch, after saffron, whose figures went
  straight into the corpus, and so far the last.* A sugar maple is the first
  individual here that survives being harvested: tapped for about six weeks,
  then tapped again next spring for upwards of a century. That made it the
  first real use of `yield_period_days` for a period that is **not** a year,
  and reading the season as a year would have overstated a tree's output
  roughly eightfold.

  Two things worth carrying forward. The famous 40:1 sap-to-syrup ratio is
  stored as UVM's Jones Rule of 86 rather than as the constant, because the
  spread is the sap's sugar content and every value in it is correct for a
  different tree on a different day. And boiling is `applies_to: mass`, so it
  cannot make trees fewer — the third unrelated process (frying a wing, drying a
  stigma, boiling sap) caught by one rule that has never needed modifying.

  NASS publishes a Maple Syrup report with state production and tap counts.
  Loading it is the single most valuable next source for the subject, and would
  put a `measured` floor under figures that are currently all `industry`.

- [x] **Vanilla and wagyu were run and landed in `v2.1.0`.** Both batches'
  candidate URLs were filled from a real search pass and both cleared the
  citation audit; see `docs/research/accepted/batch-03-wagyu-REVIEW.md` and
  `-round2.md` for the record of what was fetched and accepted.

  Neither is a full subject yet, and that gap is real, not documentation lag:

  - **Vanilla** got a species row (*Vanilla planifolia*, horticulture) and the
    curing-loss stage, but no product row — no source states a per-vine yield
    as a numeral, and the schema refuses a product without one. Still the
    cleanest test of a large concentration ratio, once that number turns up.
  - **Wagyu** got five `economic_stat` rows (30-month finishing period,
    three carcass/retail yield figures on three different denominators) and
    two grading facts, reachable today via `/api/footprint?product=ground_beef_patty`
    (wagyu shares beef cattle's `livestock` domain) and the facts feed — but
    no species or product row of its own, so it has no calculator answer and
    no BMS-marbling quality axis. It is still the only specced subject that
    tests quality-as-a-dimension (BMS marbling, which should reuse the
    `quality_defect` pattern and must not change a count), and would be the
    first subject where the individual is a large animal and the product is
    most of it.

  `batch-05-milk` was drafted and human-scouted ahead of both and has not been
  run either. It is the first non-poultry subject that could reach `measured`
  item by item, and its scout already found the thing that makes it hard: NASS
  publishes per cow per month and per year but never per day, so a recurring
  product's floor has no physiological ceiling to rest on.

- [x] **Honey was run, twice, and returned nothing — that is the result.**
  *Not "drafted, not run", which is what this file used to say.*
  `batch-04-honey` went to COOPER twice; run 2 fetched **17 of 17** documents
  into 59 chunks and still accepted **zero** figures. The full record is
  `docs/research/accepted/batch-04-honey-REVIEW.md`, written precisely because
  `outbox/` is gitignored and the only other trace would have been a missing
  findings file.

  Two independent causes, and the review is careful to separate them. **The
  subject genuinely lacks sourced numbers** — "1/12 teaspoon per bee" is
  attributed by Iowa State to National Honey Board *trivia*, and "two million
  flowers per pound" traces to a cancer-biology review whose sentence carries no
  reference at all. And **the extractor answered from proximity rather than
  meaning**: one number, 2670588, came back as the answer to three unrelated
  questions. Asking a model for a figure no document states yields a refusal or
  a fabrication, never a citation.

  The honest reading is that honey's real question was always *"does anybody
  actually know?"*, and the pipeline answered it. Do not re-run it hoping for a
  different number; re-run it only if a genuinely sourced figure turns up.

- [x] **Ground beef, silk and our own loss factors: three more negatives, kept
  as bug reports.** All three ran, all three were reviewed, and **none of them
  put a figure in the corpus** — which is why the version never moved for any
  of them.
  - `batch-06-ground-beef` — verify FAILED. `fsis.usda.gov` returns 403 to
    COOPER site-wide (it renders no JavaScript and sends no browser UA), so one
    item was excluded before any model time was spent. Of the two figures that
    passed the gate, one flattened the hedged ceiling *"more than 100 cows can
    be used"* into `lo = mode = hi = 100`, and the other took a USDA ARS
    methods section's 112 g test-patty mold for a market standard — about one
    gram from the real quarter-pound, which is what makes it dangerous.
  - `batch-08-silk` — verify FAILED twice, and paid for itself anyway:
    `fetch_url()` never called `html.unescape()`, so `&nbsp;` survived into the
    inbox and a model that read the prose correctly produced a quote that could
    **never** match. That cost the run's best row (reeling, 2/2 consensus) and
    manufactured false guilt that reads exactly like an invented citation.
    Chunking was cleared as a suspect in the same run.
  - `batch-09-own-loss-factors` — the most instructive of the lot. One figure
    returned, the gate **passed** it, and it was wrong by a factor of twenty:
    a verbatim pie-chart label from the right document, reporting a share of
    *calorie* loss as a loss *rate*. A figure whose basis cannot be read off its
    own quote is not usable however well it verifies.

  Four fixes came out of these runs — colliding filenames silently deleting
  fetched documents, HTML entities, the extractor finally being shown the
  spec's own "Watch for" paragraph, and verification running on Windows. **The
  pipeline is getting more trustworthy while shipping nothing, which is the
  right order.**

- [x] **Israel-Hebrew ran, and the language of the question was the finding.**
  *This file used to list batch 05 as merely "drafted".* `batch-05-israel-hebrew`
  put 10 Hebrew documents through 12 extraction calls and returned **0
  figures** — not a fetch failure and not a chunking failure, since a 40-page
  State Comptroller PDF extracted to 103,610 characters with the Hebrew intact.
  A human reading the same returned artifacts found real figures in minutes,
  the second time the artifacts have been worth more than the extraction.

  Two of those figures — **604 broiler growers** and **244 million chicks
  placed (2021)** — were promoted in **v1.6.0** at `industry` grade, with a
  test pinning the corroboration that justified promoting them, and with chicks
  placed held deliberately distinct from birds slaughtered so grow-out mortality
  is not double-counted.

  `batch-05b` then re-asked six of the same documents **in Hebrew** and got 2
  figures from 12 calls, both quote-matched character-for-character, both the
  same two the human had found — a reproduction rather than an anecdote. The
  detail that makes it stronger: the embedder was down for that run, so Hebrew
  questions with crude keyword matching beat English questions with real
  embeddings. **A multilingual embedder is therefore not the diagnosis** and
  should not be built on this evidence.

- [ ] **Decide what this project is called when it is not about chickens.**
  **The deadline this item set has passed.** It said decide before a fourth
  subject; maple landed in v1.9.0 and opened a third `domain` row with the
  decision unmade. The repo, the CLI (`wings`), the database (`chickens.db`)
  and the deployed hostname all still say chicken — and the hostname
  re-committed to it, since `wings.swamplink.com` was chosen during the move off
  Render, which was the natural moment to change it and did not. Renaming for
  its own sake is still not worth it, but this is now overdue rather than early,
  and it wants deciding *before* the localization work below, since a name is
  the first string anyone translates.

---

## M7 — Localization: EN / FR / HE

> *"Add localization for EN/FR/IL for now, and plan more for future. Mainly
> languages."* — from the note, missing on first capture.

**This supersedes `docs/ISRAEL-PLAN.md`'s "do not translate the UI".** That was
right for a demo and is wrong now that he has asked for it; the plan document
has been updated to point here.

- [ ] **Extract strings before translating anything.** The blocker is not
  translation, it is that user-facing prose is hardcoded in `cli.py` and in the
  front end — the egg "why not exactly the floor" prose had to be fixed in both
  places in v1.2.0, which is the same lesson in miniature. Nothing can be
  localized until the strings live in one place.

  **The A/B test made this worse before anyone fixes it.** There are now two
  front ends, and variant B is three files (`v2/index.html`, `v2/app.css`,
  `v2/app.js`) rather than one, so a prose change can need touching four places
  instead of two. There is still no strings module in
  `src/counting_chicken_wings/`. The A/B work also proves the extraction is
  doable: `static/ab.js` is already shared verbatim by both arms precisely
  because a thing that differs between the pages is a thing that drifts.

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

- [x] **Unreachable data now has a route to the user.** `nutrition`,
  `resource_footprint` and `economic_stat` were built and cited with nothing
  serving them; `810bdba` surfaced all three in the same commit that added this
  item, and the checkbox was simply never ticked. `/api/nutrition` and
  `/api/footprint` serve them today and the "Nutrition & impact" view renders
  both, mass-allocated — a dozen wings carries the product's share of the bird,
  not six whole birds' worth, and the gap between the raw and allocated figures
  is shown because it is the point.

- [~] **Sources cited by nothing: back up to five, and none of them is a
  mistake.** The audit names `jfs-independence-day-grilling`,
  `nysmaple-sap-per-tree`, `psu-extension-saffron`, `umaine-7036e-maple` and
  `usda-psd-israel-broiler-2000`. They are uncited for three different reasons:
  - **Held as an unresolved conflict** — `psu-extension-saffron` (~3 lb/acre
    against HS661's 8–10) and `usda-psd-israel-broiler-2000` (the live-versus-
    carcass weight basis, recorded on `cbs-st21-11-output-2025`). Neither figure
    is loaded, deliberately.
  - **Held as corroboration** — `jfs-independence-day-grilling` is the second
    source agreeing that Yom Ha'atzmaut grilling is near-universal, and two
    sources agreeing is why the cultural fact is loaded at all. The fact cites
    the other one.
  - **Held for context around a figure that came from elsewhere** — the two
    maple extension services, whose per-tap yields disagree and are kept as a
    range rather than averaged, and whose "most trees today have only one tap"
    is load-bearing without being a cited number.

  So the item's original prediction held — this keeps happening — but it is
  wider than "conflict". **The audit needs to distinguish "orphaned" from "held
  deliberately, and here is why",** because as it stands the check reports five
  findings and none of them wants acting on, which is how a warning stops being
  read. The `notes:` field already carries the reason in every one of the five;
  it is not exposed in a form the audit can read.

---

## Sequencing recommendation

The pre-1.0 sequence ran as written: identity, then "is fatter better", then
channel-aware loss stages, then the 1.0 cut — with eggs promoted ahead of
turkey, which was the right call for the reason given (eggs forced a real
schema improvement; turkey re-runs the wing analysis on a bigger bird).

**Revised for post-1.11, 2026-07-31.** Of the nine items in the previous
sequence, two shipped and two more were partly answered by work nobody
sequenced — the A/B harness and the move off Render both arrived from outside
this list.

1. **Finish surfacing the evidence gap (M6), which is now specifically about
   conflicts.** v1.8.0 did the grade half: stamps, dashed-and-hatched estimates,
   in both themes, so an unsourced figure looks different from a sourced one
   everywhere it appears. What no reader can reach is the disagreements held
   **as unresolved conflicts** — saffron's three-fold per-acre spread and
   Israel's live-versus-carcass tonnage basis — which are among the most honest
   things the corpus holds and are invisible in both front ends. A reader who
   sees a saffron figure rendered like a NASS figure has been misled by
   presentation rather than data, and that is the failure this project exists
   to prevent.
2. ~~**README generated from `audit.py`**~~ — done 2026-07-29, see Housekeeping.
3. ~~**M1 seasonality**~~ — done in v1.7.0 for broiler live weight, and it came
   back a negative result with a second-order positive behind it. **The half
   that matters to the count is still open**: monthly condemnation and DOA,
   which is a parser-pointing job on a document `tools/parse_nass.py` already
   reads. Eggs-per-layer monthly is in the same position.
4. **M1.5 fresh vs frozen.** Promoted for the third time and still not done: it
   is the only item that moves the *distinct* number, which is the headline
   answer. Everything else refines birds-required.
5. **M7 string extraction** — the extraction half only, not translation. There
   is still no strings module; user-facing prose lives in `cli.py` and now in
   *three* front-end files rather than two, since variant B split its markup,
   CSS and JS. The duplication this item exists to fix got worse, not better.
6. **M1 data long pole** — regions and producers, both unblocked. Treat the
   suppressed states as bounded rather than open.
7. **M6 milk or vanilla, then M5 turkey.** `batch-05-milk` is already drafted
   and human-scouted and would be the first non-poultry subject able to reach
   `measured`; vanilla still needs a URL scout before it can run at all. Turkey
   stays last of the three — it needs its own husbandry sourcing and must not
   inherit chicken loss factors.
8. **Israel's remaining half is still a UI job.** v1.3.0 loaded CBS output,
   inventory and the regional hierarchy; v1.4.0 added the head count at
   `industry` grade and the derived 2.31 kg bird; v1.6.0 promoted the grower
   count and chick placements a human read out of batch-05's documents; v1.9.1
   reframed the copy to lead with what the sources are. Both readings are
   queryable — `min_confidence=measured` for the government-only picture, the
   default for the industry one — and **rendering the two side by side is what
   is left**. A *government* head count, a bedikah rejection rate and a
   per-capita series are still unfetched; batch-05 and 05b answered the language
   question, not those. Do not ship a per-capita figure until one lands; five
   sources give five numbers 20% apart.
9. **M7 translation and RTL**, then the Discord bot.

Unsequenced but now real: **the A/B experiment has no noise floor.** The A/A
run that would have given it one never happened, and the arms have diverged, so
any difference variant B reports cannot be compared to anything. Decide whether
that is worth the cost of getting back — it is not obviously worth re-copying
the page to find out.

Three judgement calls worth revisiting:

**The adapter layer (M4) should wait for the second country, not lead it.** It
is the right idea and the Israel access findings prove the cost of not having
it, but one real adapter is not enough to discover a shared interface. Build
CBS as a one-off, then extract the interface from two working examples.

**Localization and the project's name are entangled.** A name is the first
string anyone translates, and the project is four subjects and three domains
past being about chickens — the fourth subject arrived without the naming
decision being made. Decide the name before paying for translation twice.

**The estimate ratio has stopped getting worse** — 11 of 22 loss factors are
unsourced (50%), against 11 of 21 (52%) at v1.8.0 and 8 of 14 before eggs and
saffron. Maple added a domain without adding an unsourced estimate, which is
the first time that has happened. The earlier warning stands as a threshold
rather than a trend: if it starts rising again, sourcing existing estimates
outranks adding a fifth subject.
