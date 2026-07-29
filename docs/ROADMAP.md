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
| Cold start | ~23s (Render free tier spins down; see M4) |
| Tests | 59 passing |
| Facts | 31 |
| Sources | 30 |
| States with data | 22 |
| Products | whole wing, boneless wing |

---

## M1 — Data completeness (US)

The biggest single lever on the project's credibility. Everything here is
data, not code.

- [!] **Remaining US states.** NASS reports broilers slaughtered in **40
  states** but publishes only **22** individually — the rest are suppressed
  under disclosure rules precisely because too few companies operate there.
  *This is a hard ceiling on the primary source.* Routes worth trying, in
  order of promise:
  1. NASS QuickStats API — may expose series the PDF summary aggregates away
  2. FSIS Meat, Poultry and Egg Inspection Directory — gives which states
     have plants, and plant counts, even where volume is suppressed
  3. State departments of agriculture for the larger missing states
  Accept that some states may only ever have presence, not volume, and
  render them differently on the map rather than leaving them blank.

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

## M5 — After 1.0

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

## Sequencing recommendation

1. **M3 identity first** — ASCII logo and the facts card deck are fast, visible,
   and make every subsequent demo better.
2. **M2 "is fatter better"** — highest payoff per unit effort, since the data
   is already in the database.
3. **M1 data** — the long pole. Start with regions and producers, which are
   unblocked; treat the suppressed states as bounded rather than open.
4. **M4 cut 1.0.**
5. **M5** once 1.0 is stable.
