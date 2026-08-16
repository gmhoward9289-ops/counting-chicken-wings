# Germany data — research plan

**Status, 2026-08-16: Germany answers the count question at `measured`
grade, on the first pass, from Destatis's own headline release.** Unlike
Mexico (no head count at all) or the UK (a genuine government count, but
requiring a separate hatcheries survey to cross-check), Destatis isolates
Jungmasthuhn (broiler) from Suppenhuhn (spent/stewing hen) directly in the
same sentence of its annual "Fleischproduktion" press release: "626,7
Millionen Jungmast- und 27,1 Millionen Suppenhühner geschlachtet" (2024).
That is the species split this project needs, delivered without requiring a
second finer table (Canada) or a secondhand USDA GAIN quote (Mexico). Loaded
at `GET /api/output/DEU`: head slaughtered and meat output, four consecutive
years (2022-2025), both `measured` grade, both Destatis.

**What did not make it in, and why, up front:** no districts: table (not an
access failure -- Destatis's own poultry-slaughter tables genuinely carry no
Bundesland dimension, confirmed directly from the publication's own table of
contents), no output value in euros (not found in the sources checked this
pass), and no per-capita consumption or self-sufficiency figure (both exist,
both are government-published, and both are for "Geflügelfleisch" -- all
poultry meat, not chicken specifically -- the same taxonomy trap Mexico's
carne-de-ave/carne-de-pollo distinction already documents for this project).

This document follows `docs/MEXICO-PLAN.md`'s and `docs/UK-PLAN.md`'s shape:
a priority-1 table stating what is loaded and at what grade, the taxonomy
traps resolved in writing, and a "what NOT to do" section.

---

## Priority 1 — Core production figures

| Field | Why the model needs it | Status 2026-08-16 |
|---|---|---|
| Broilers slaughtered per year (head) | The denominator for everything | **LOADED at `measured`.** 626.7 million (2024), 640.3 million (2025) from Destatis's annual press release, isolating Jungmasthuhn from Suppenhuhn directly; 631,132.8 thousand (2022) and 631,476.2 thousand (2023) at full decimal precision from Destatis's own data table. Four consecutive years, one government survey (mandatory reporting by EU-hygiene-licensed poultry abattoirs, small operations estimated via Marktinfo Eier & Geflügel per the survey's stated methodology) |
| Average live weight (kg) | Drives wing size | **NOT LOADED, and not derivable as live weight.** No live-weight figure was found in any source this pass reached. A derived carcass-weight-per-bird figure IS possible from head_slaughtered ÷ meat_output (≈1.72-1.76 kg/bird across the series) but that would be whole-carcass (skin-on, eviscerated) weight, not live weight -- see the weight-basis section below |
| Total chicken meat production (tonnes) | Cross-check against head × weight | **LOADED.** 1,074,500 t (2022) and 1,086,100 t (2023) at exact precision from Destatis's data table; 1,100,000 t for both 2024 and 2025 -- Destatis's OWN rounded press-release figure, loaded verbatim rather than back-solved to a false precision from the stated percentage growth |
| Standing flock (head) | Not throughput, but a real head figure elsewhere | **NOT LOADED.** No end-of-year standing-flock series for broilers was found; Destatis's poultry statistics are throughput-oriented (slaughter counts), matching the UK's finding rather than Israel's or the US's inventory tables |
| Output value (EUR) | Scale in local currency | **NOT LOADED.** No aggregate euro figure for broiler meat output specifically was found in the sources this pass checked; worth a dedicated search of BMEL's farm-income series before concluding it does not exist, exactly the caveat the UK plan carries for GBP |
| Subnational breakdown | Choropleth counterpart | **NOT AVAILABLE, and Destatis's own publication structure says so.** See "Why there is no subnational broiler table" below -- a genuine, confirmed absence, not a research gap |
| Per-capita consumption (kg) | A demo hook, if sourceable | **DELIBERATELY UNSOURCED as a chicken-specific figure.** See the taxonomy trap below. A poultry-wide figure (13.6 kg, 2024) exists and is NOT loaded as chicken |
| Self-sufficiency / import share | Scale contrast with the UK (net importer) and Israel (net exporter) | **DELIBERATELY UNSOURCED as a chicken-specific figure.** A poultry-wide ratio (100.4%, 2024) exists and is NOT loaded, same reasoning |

**Two figures a demo can use honestly today:** 640.3 million broilers
slaughtered and 1.1 million tonnes of broiler meat produced in Germany in
2025, both Destatis-measured from a mandatory abattoir survey -- alongside
Canada, this is the strongest data position (both a head count AND a
tonnage, from one government source, at `measured` grade, for a multi-year
run) any non-US country in this corpus has reached.

---

## The weight-basis question, resolved directly rather than left open

BMEL's own supply-balance documentation states the definition plainly:
*"Schlachtkörper bei Geflügel bezeichnet den gerupften und ausgenommenen
Körper, ohne Kopf und Ständer und ohne Hals, Herz, Leber und Muskelmagen"* --
the plucked and eviscerated body, without head, feet, neck, heart, liver or
gizzard. Skin and subcutaneous fat stay ON: poultry and pigs are the two
exceptions to Destatis's general rule that Schlachtgewicht excludes skin.
That means Germany's meat_output figure is whole-carcass weight, closest in
concept to the UK's "whole-bird-equivalent carcase weight net of offal," and
is a different basis from a ready-to-cook-minus-skin retail figure. Loaded
as `tonnes` with this basis stated in the file's own notes rather than left
implicit the way Israel's CBS tonnage originally was.

**Not applied:** the Warmgewicht/Kaltgewicht (factor 0.98) conversion that
governs cattle, pig, sheep and horse slaughter statistics does NOT apply to
poultry, which Destatis measures through an entirely separate survey (the
Geflügelstatistik, not the Schlachtungs- und Schlachtgewichtsstatistik).
Confirmed directly from a Niedersachsen state-statistics document that
states this explicitly while describing the cattle/pig conversion factor in
the same paragraph -- worth stating because it would be an easy trap to
walk into by assuming one Schlachtgewicht convention governs every species
in one country's statistics.

---

## Why there is no subnational broiler table

This is Germany's version of the question every country plan in this
project has had to answer for itself. Unlike Mexico (SIAP genuinely
publishes state data, but its portals were unreachable) or Canada's
suppressed Atlantic provinces (published, but confidentiality-withheld),
**Germany's answer is structural: Destatis's own poultry-slaughter Fachserie
(3/4.2.3) has no Bundesland dimension in its table of contents at all.**
Sections 3.1 through 3.5 -- the entire "Geflügelschlachtungen in
Deutschland" chapter -- break the data out by species, month, and
presentation form, and never by state.

A genuine Land-level poultry breakdown DOES exist in the very same
publication -- but in sections 4 and 5, covering farms with **laying-hen**
housing (Legehennenhaltung), not broiler slaughter. That is a different bird
category (egg layers) and a different concept (a housing/farm census, not an
abattoir-throughput survey). A second, independent document -- Niedersachsen's
own 1994-2014 state comparison -- explains the structural reason directly:
*"Die Schlachtdaten von Geflügel werden über die Geflügelstatistik beim
Statistischen Bundesamt in Tonnen erhoben und können daher in der Regel nur
deutschlandweit oder auf der Ebene Niedersachsens ausgewiesen werden"* --
poultry slaughter data is collected nationally and can generally only be
reported Germany-wide or at the Niedersachsen level specifically, because a
bird raised in one state is routinely slaughtered in a plant in another, so
an abattoir-based survey does not naturally partition by state the way a
farm census does.

**So the honest state to ship is the same one the UK plan reached: there
isn't a broiler-specific choropleth table for Germany, and that is a
confirmed structural fact about how Destatis's own two poultry surveys
diverge, not a gap this project failed to fill.**

What IS available, and is carried as facts rather than forced into a
`districts:` block:

- **2020 census, all chicken housing, all sixteen states:** "Die
  Geflügelhaltung ist mit 50 % der gesamten Haltungsplätze besonders auf
  Niedersachsen konzentriert" -- half of Germany's chicken housing capacity
  sits in one state. A housing-capacity (stock) concept, not throughput, and
  not broiler-isolated (covers laying hens too).
- **2014, Niedersachsen's own state statistics office, broiler-isolated:**
  53.0% of Jungmasthühner (broiler) SLAUGHTER by head, 59.1% of poultry
  slaughter by weight, both attributed to Niedersachsen alone. The right
  concept (throughput, broiler-specific) but a decade stale relative to the
  national head-count series this project otherwise loads for 2022-2025 --
  kept explicitly dated as a 2014 figure rather than presented as current.

Both point the same direction (Lower Saxony's dominance of German poultry),
from two different vintages and two different measurement concepts, which is
itself worth stating rather than picking whichever one sounds more current.

---

## The two taxonomy traps, both resolved the same way: don't load them

**Trap 1 — per-capita consumption and self-sufficiency are Geflügel figures,
not Hühner figures.** BLE's 2025 Versorgungsbilanz release states, for 2024:
13.6 kg per-capita consumption and 100.4% self-sufficiency, both for
"Geflügelfleisch" (poultry meat: chicken, turkey, duck, goose combined).
Neither figure is ever narrowed to "Hühnerfleisch" (chicken specifically)
anywhere this pass reached, even though the release's own prose credits the
year's growth to chicken "insbesondere" (particularly). This is the same
species-aggregation shape as Mexico's carne-de-ave/carne-de-pollo trap, and
this project answers it the same way: **neither figure is loaded as a
chicken statistic.** A fact documents the trap itself (see
`germany-selfsufficiency-hides-which-bird`) rather than silently promoting
the poultry-wide number to a chicken-specific one, or silently omitting the
issue.

**Trap 2 — Geflügel (poultry, all birds) vs Jungmasthuhn/Hähnchen (broiler
specifically), checked on every row loaded.** Every figure loaded into
`data/output_germany.yaml` traces to a source sentence that names
Jungmasthuhn (or, for the total-poultry rows that were explicitly NOT
loaded, Geflügel) -- never a silent promotion from the broader aggregate.
The Destatis data table states both figures side by side (Jungmasthühner:
631,476.2 thousand animals, 1,086.1 thousand tonnes, 2023; Geflügel total:
1,563.8 thousand tonnes, 2023) precisely so this check is auditable rather
than assumed.

---

## Sources, in order of preference

1. **Destatis (Statistisches Bundesamt)** — the NASS-equivalent, and this
   pass's headline finding: its own annual press release isolates broiler
   from spent-hen slaughter directly, without requiring a second table the
   way Canada's national release did. Two access routes worked: the annual
   press releases (rounded, current) and a data table (exact, one year
   behind).
2. **BMEL / BLE (Bundesanstalt für Landwirtschaft und Ernährung)** — the
   ministry and its subordinate agency; BMEL's own methodology page settles
   the weight-basis question directly (a rare case of the *definition*
   being easier to find than the *figure*), and BLE's Versorgungsbilanz
   release is the source of the per-capita/self-sufficiency taxonomy trap.
3. **Landesamt für Statistik Niedersachsen** — the one German state that
   publishes its own poultry-specific comparison against the national
   total, and the source of both the broiler-isolated 2014 regional-
   concentration figure and the structural explanation for why no current
   Bundesland table exists.
4. **ZDG (Zentralverband der Deutschen Geflügelwirtschaft)** — Germany's
   poultry trade body, the equivalent of the National Chicken Council or
   Mexico's UNA. Searched for a state-level broiler production breakdown
   that might have corroborated or updated the 2014 Niedersachsen figure;
   no citable statistical publication was reached this pass (general search
   results only, no page actually read) — a genuine gap for a future pass,
   not a claim this plan makes on the trade body's behalf.
5. **GENESIS-Online** — Destatis's queryable database, the equivalent of
   Statistics Canada's WDS. **Not reached this pass** — see "Access
   findings" below. This is the single highest-value target for a future
   pass with real browser tooling rather than a bare fetch.

### Access findings

**Read `docs/research/library/poultry-germany.yaml` first** — it is the
machine-readable version of this section, with every URL tried, its HTTP
status, and what it does and does not cover.

| Source | Result |
|---|---|
| **Destatis annual "Fleischproduktion" press releases (2024, 2025)** | **Work, and isolate broiler directly.** Rounded to one decimal of a million tonnes for meat output; head counts given to 0.1 million. |
| **Destatis "gewerbliche Schlachtung" data table** | **Works.** Exact decimal-precision figures for 2022-2023 (Jungmasthühner: head count and tonnage both), extracted cleanly via the page's own rendered table. Had not yet rolled forward to 2024-2025 at the time of this pass. |
| **Destatis Fachserie 3, Reihe 4.2.3 (Geflügel, 2018 PDF)** | **Works, once fetched as a binary and run through `pdftotext -layout`** — WebFetch's own summarizer initially called it corrupted. Settles the "does a Bundesland table exist for broiler slaughter" question directly and negatively, from the publication's own table of contents. |
| **BMEL Versorgungsbilanz Fleisch documentation** | **Works.** Direct, quotable government definition of poultry Schlachtgewicht — the rare case where the methodology page was easier to reach than the underlying figure. |
| **BLE Fleischbilanz 2025 press release** | **Works.** Source of the per-capita/self-sufficiency taxonomy trap. |
| **Destatis 2020 Agricultural Census livestock press release** | **Works.** Niedersachsen's 50%-of-housing-capacity figure. |
| **Landesamt für Statistik Niedersachsen, 1994-2014 comparison PDF** | **Works, same PDF-extraction route as the Fachserie above** — another WebFetch-summarizer refusal that `pdftotext -layout` resolved cleanly. The single most useful document in this pass for the regional-concentration question, and the only source in this batch of countries that gives a broiler-ISOLATED state share. |
| **GENESIS-Online (`genesis.destatis.de`)** | **Not reached.** Real API/database (the tables the press releases themselves cite, 41331-0004 and 41322-0002, live here), but a plain fetch returns only a JavaScript page shell — no data in the initial HTML, unlike Canada's WDS (a real REST endpoint once a TLS flag was found) or StatCan's TLS-handshake fix. This is a genuine "needs a browser, not a bare fetch" gap, flagged for the next pass. |
| **Marktinfo Eier & Geflügel (MEG) census summary article** | **403 Forbidden.** Not used as a citation — never actually read. |
| **Niedersachsen's own cattle/pig/sheep slaughter-statistics page** | **Works, and confirms an absence.** Explicitly scoped to non-poultry species; corroborates the structural finding that poultry runs through a wholly separate national survey. |
| **ZDG (trade body) statistics** | **Not reached.** General search results only; no statistical publication page was actually opened and read this pass. |

---

## Priority 2 — What makes the comparison land

- **Five-country scale comparison, updated.** Germany's 640.3 million
  broilers (2025) sits below the UK's 1.13 billion and well below the US's
  9.58 billion or Canada's 806 million, but above Israel's ~260-275 million
  and comparable in order of magnitude to Mexico's unenumerated-but-implied
  scale (UNA's ~39.3 million/week ≈ 2 billion/year if it were annualized,
  which this project deliberately does not do). Germany sits roughly at
  Canada's scale, a genuinely useful mid-sized-economy data point alongside
  the UK's larger and Israel's smaller examples.
- **The skin-on weight basis is a strong, standalone fact.** Unlike the
  UK's carcase-weight-net-of-offal (a basis shared conceptually with most
  other countries once stated) or Canada's live-vs-eviscerated conflict
  (a genuine cross-publisher disagreement), Germany's skin-INCLUDED
  convention is a genuinely counterintuitive, government-stated exception
  that most readers will not expect — a strong candidate for a
  high-surprise learning-centre fact, loaded as
  `germany-poultry-skin-included`.
- **Two independently-dated regional-concentration figures, same direction,
  different vintages.** The 2014 broiler-specific 53% and the 2020
  all-chicken-housing 50% agree in substance (Lower Saxony's dominance)
  without being the same measurement — worth stating together rather than
  picking the more recent or the more specific one and discarding the other.
- **Wings specifically.** Not researched in this pass, matching every other
  country plan's finding so far — no source reached broke out wings as a
  separate cut for Germany. A genuine gap, not a "no."

---

## What "done" looks like for this pass

1. [x] National head-slaughtered loaded at `measured` grade, broiler
   isolated from spent hen directly at the source, for four consecutive
   years — Destatis did this without a second finer table, unlike Canada.
2. [x] National meat_output loaded, `measured`, with the precision gap
   between 2022-2023 (exact) and 2024-2025 (Destatis's own rounded
   press-release figures) stated explicitly rather than smoothed over.
3. [x] Weight basis resolved directly from a government methodology page,
   including the genuinely surprising skin-on convention.
4. [x] Explicit, source-confirmed statement of why no subnational broiler
   table ships — a structural absence in Destatis's own publication
   design, not an access failure or a suppression.
5. [x] Both taxonomy traps (per-capita/self-sufficiency as poultry-wide;
   Geflügel vs Jungmasthuhn generally) documented and deliberately not
   shipped as chicken-specific figures.
6. [ ] Output value in EUR — not found in the sources checked this pass;
   worth a dedicated look at BMEL's farm-income series, mirroring the
   UK plan's identical open item.
7. [ ] A live GENESIS-Online pull — blocked on tooling (a JS single-page
   app, not a dead source), not on the data not existing. The highest-value
   next step for a future pass with real browser access.
8. [ ] Wings as a separately-reported cut — not investigated this pass.

## What to explicitly NOT do

- **Do not load the 13.6 kg per-capita or 100.4% self-sufficiency figures
  as chicken-specific statistics.** Both are stated for "Geflügelfleisch"
  (all poultry) in every source this pass reached; loading either as a
  Hühner/broiler figure would silently promote a broader aggregate, the
  exact trap Mexico's carne-de-ave/carne-de-pollo discipline exists to
  catch.
- **Do not build a `districts:` table from the 2020 census housing-capacity
  figure.** It covers "Hühner" generally (broilers and laying hens
  together), only names one state's share (Niedersachsen), and measures
  housing capacity, not slaughter throughput or meat output — none of
  which matches this project's `output_stat_year` measure vocabulary or
  its species definition.
- **Do not present the 2014 Niedersachsen broiler share as current.** It is
  the most recent BROILER-SPECIFIC regional figure this pass could source,
  but it is over a decade old relative to the 2022-2025 national series —
  keep it dated in every fact and every reference to it.
- **Do not apply the Warmgewicht/Kaltgewicht (factor 0.98) conversion to
  any German poultry figure.** That conversion is documented for cattle,
  pigs, sheep, goats and horses specifically; poultry runs through an
  entirely separate survey with its own (skin-on, eviscerated) weight
  definition.
- **Do not back-solve a falsely precise 2024 or 2025 tonnage from the
  stated percentage-growth figures.** Destatis's own press releases round
  meat_output to one decimal of a million tonnes; computing "1,105,650" or
  similar from the percentage change would invent precision the source
  itself does not publish, the same discipline this project already
  applies to Mexico's UNA weekly-throughput figure (not annualized by
  multiplying by 52).
- **Do not reuse US, UK or Canadian loss factors on German data without
  grading the result `estimate` and saying so.** Nothing in this pass
  investigated Germany's own slaughter/inspection loss chain.
