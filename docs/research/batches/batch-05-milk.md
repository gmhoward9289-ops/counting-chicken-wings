# Batch 05 — dairy milk

**Archetype:** `how-many`

**Question in one sentence:** How many cows does it take to fill a gallon of
milk — and how many are in the carton you actually bought?

**Expected confidence ceiling:** **`measured`, item by item.** This is the first
non-poultry subject that can reach it. Items 1, 3 and 5 rest on NASS or ERS
measurements with clean verbatim sentences. Others cannot get near it, and the
table at the bottom of this spec says which is which.

---

## Read this before running the batch

Scouted by a human first. Four findings changed what this spec asks.

**1. There is no published per-day yield, and no physiological ceiling.** NASS
publishes per cow per *month* and per *year*, never per day. Worse for the
model: the best peer-reviewed source states outright that *"It is not still
possible to define the maximum capacity for milk production in dairy cows."*

That matters more than it sounds. `max_units_per_day` is what makes a recurring
product's floor a real floor — a hen lays at most one egg a day, so twelve
same-day eggs need twelve hens, necessarily. **Milk has no equivalent.** Any
ceiling we use will be an *observed record*, not a physiological limit, and it
must be graded and labelled as such. Do not let a derived per-day average
masquerade as a ceiling.

**2. The 2% farm shrink is not a loss.** It is a *price-classification
allowance* under 7 CFR 1000.43(b) — the maximum a handler may assign to the
lowest-priced class before the excess is charged at Class I. A model will read
"2 percent" as spillage. **This is the milk analogue of the saffron drying
trap**: a real number, in a real government document, that must not enter the
count.

**3. Mean and midpoint herd size differ by 4.6× and both are correct.** ERS says
the mean is 283 cows; ERS also says the *midpoint* is 1,300, meaning half of all
US dairy cows live in herds larger than that. Neither is wrong. A single
"average herd size" in this corpus must name which statistic it is.

**4. Two famous conversion ratios have no primary source.** "21.2 pounds of milk
per pound of butter" and "12 pounds of milk per gallon of ice cream" circulate
everywhere and trace to nothing — marketing pages, a state Farm Bureau article,
content farms. USDA publishes *component* yields instead (per pound of
butterfat, per pound of protein). Item 4 is phrased around what actually exists.

---

## Why this subject

Milk is the first product where **the pooling question has real consequences and
a real answer path.** A tanker collects from several farms, a plant silo
commingles many tankers, and the carton is drawn from that. So "how many cows
are in your gallon" is genuinely the wing question at industrial scale.

It also fills a schema gap honestly. Milk is `recurring` like eggs — a rate over
a window — but unlike eggs it has no daily ceiling, so it tests whether the
recurring machinery works when its most load-bearing input is *absent*.

---

## Fetch-reliability notes — read before queueing

| Hazard | What to do |
|---|---|
| `usda.library.cornell.edu` is **dead** | 301s cross-host to `esmis.nal.usda.gov`. Any Cornell URL in this repo's older docs is stale. |
| `ecfr.gov` is **fully bot-walled** | Returns 200 for an unblock interstitial. Use `govinfo.gov` CFR PDFs instead — verified working. |
| `ams.usda.gov` **HTML** needs a User-Agent | 403 without, 200 with. AMS **PDFs** are fine as-is. |
| ESMIS `.txt` variants **hard-wrap at ~70 chars** | Quotes span line breaks and **fail character-for-character matching**. Prefer the PDF path here — the opposite of the honey batch, where the `.txt` was better. |
| NASS `Charts_and_Maps/*.php`, ERS chart-detail pages | Figures exist **only inside PNG images**. Unusable. Not listed below. |
| `holsteinusa.com`, `farmanddairy.com`, `farmprogress.com` | Cloudflare 403 / HTTP 500 / 403. Not listed below. |

**A `.gov` host is not a `.gov` document.** Several
`ams.usda.gov/sites/default/files/media/FMMO_*.pdf` files are **hearing exhibits
submitted by industry parties** — NMPF, IDFA, CDFA — and one is a reprinted
*Dairy Foods* magazine article. Do not let the URL promote these to `measured`.

---

## Items

### Item 1 — milk_yield_per_cow_year

| | |
|---|---|
| `target_table` | `product` (`units_per_individual`), `husbandry_stat_year` |
| `unit` | **pounds** per cow per year |
| `archetype` | `how-many` |
| `expected confidence` | **`measured`** |

**Question:** What is the average annual milk production per cow in the US, for
the most recent year available?

**Candidate URLs:**

- https://release.nass.usda.gov/reports/mkpr0226.pdf — NASS *Milk Production*, released 2026-02-20. **The February release is the one carrying the prior-year annual revision.** Best target.
- https://esmis.nal.usda.gov/sites/default/release-files/795884/mlkpdi26.pdf — NASS *Milk Production, Disposition, and Income 2025 Summary*, released 2026-04-30
- https://www.ers.usda.gov/amber-waves/2026/february/fewer-farms-more-milk-the-changing-structure-and-costs-of-us-dairy-farming — ERS, for the long trend

**Done means:** the per-cow figure **in pounds**, with the year, plus total
production and cow numbers.

**Watch for — two traps:**

1. **Filename year is the RELEASE year, not the data year.** `mlkpdi26.pdf` is
   the 2025 Summary; `mlkpdi24.pdf` is the **2023** Summary. A model
   pattern-matching filenames for "most recent" will fetch the wrong year.
2. **`release.nass.usda.gov` and `www.nass.usda.gov/Publications/Todays_Reports`
   serve byte-identical files.** Two URLs, one document. And the Summary
   republishes the same NASS estimate. **These are not independent
   confirmations — do not report 2/2 or 3/3 agreement across them.**

---

### Item 2 — milk_yield_per_cow_day

| | |
|---|---|
| `target_table` | `product` (`yield_period_days`) |
| `unit` | **as stated by the source** — pounds, kg, or litres per day |
| `archetype` | `how-many` |
| `expected confidence` | `study` for the kg figures; the US average is `derived` |

**Question:** What daily milk yields are reported for dairy cows, and in what
units?

**Candidate URLs:**

- https://pmc.ncbi.nlm.nih.gov/articles/PMC10289513/ — Gross 2023, *Animal Frontiers*, peer-reviewed open access. **The strongest source in the batch.** States daily yields in **kg**.
- https://fieldreport.caes.uga.edu/publications/B1193/ — UGA Extension B1193. Real per-day figures in **pounds**, but they are *peak* and *benchmark* values, not national averages.
- https://release.nass.usda.gov/reports/mkpr0726.pdf — NASS monthly, June 2026. Gives per cow per **month**.

**Done means:** the daily figures each source states, **in that source's own
units**.

**Do NOT** divide a monthly figure by 30 to get a daily rate. That division is a
`derived` step for a human, and it is exactly the shape of error that produced
the saffron misattribution — answering the question asked with arithmetic on a
number that answers a different one.

---

### Item 3 — physiological_ceiling_per_day

| | |
|---|---|
| `target_table` | `product` (`max_units_per_day`) |
| `unit` | as stated — kg or litres per day |
| `archetype` | `provenance-audit` |
| `expected confidence` | `study` for the statement of absence; `industry` for the record |

**Question:** Is there a defined physiological maximum daily milk yield for a
cow, and if not, what is the highest *observed* 24-hour yield?

**Candidate URLs:**

<!-- Listed in full rather than "as Item 2, plus one". The parser only inherits
     the previous item's URLs when a block has NONE of its own, so a block
     saying "as Item 2, plus X" fetches only X -- which here would have dropped
     Gross, the one source that matters for this item. Checked before sending. -->

- https://pmc.ncbi.nlm.nih.gov/articles/PMC10289513/ — Gross 2023, *Animal Frontiers*. **The source that declines to define a maximum.** Essential to this item.
- https://www.guinnessworldrecords.com/world-records/70833-largest-milk-yield-from-a-cow-in-24-hours-mechanical-milking — the only published, adjudicated 24-hour maximum found. **Units: litres.** Guinness is a records adjudicator, not a scientific body → `industry` at best.
- https://fieldreport.caes.uga.edu/publications/B1193/ — UGA Extension B1193, peak-lactation figures in pounds per day

**Done means:** the verbatim sentence from Gross declining to define a maximum,
**and** the observed record with its units and its adjudicator.

**This item exists because the answer is "no".** For eggs, `max_units_per_day`
is a genuine physiological ceiling and it does the heavy lifting in the model.
Milk has no such figure, and a corpus that quietly substituted an observed
record for a physiological limit would be claiming something no source supports.
**Reporting the absence is the deliverable.**

**Watch for:** the US record (78,170 lb in 365 days, peak 228 lb/day) is real and
widely reported, and **every host for it is currently 403, 500, or
Cloudflare-walled.** Do not accept it without a fetchable citation.

---

### Item 4 — herd_size

| | |
|---|---|
| `target_table` | `production_program`, `mixing_stage` pool |
| `unit` | cows per operation; head in the national herd |
| `archetype` | `how-many` |
| `expected confidence` | `measured` |

**Question:** How many milk cows are in the US herd, and how many per operation?

**Candidate URLs:**

- https://release.nass.usda.gov/reports/mkpr0226.pdf — national herd, 2025
- https://www.nass.usda.gov/Publications/Highlights/2024/Census22_HL_Dairy.pdf — Census of Agriculture 2022 highlights, with the size distribution
- https://www.ers.usda.gov/amber-waves/2026/february/fewer-farms-more-milk-the-changing-structure-and-costs-of-us-dairy-farming — ERS, **mean** cows per farm
- https://ers.usda.gov/sites/default/files/_laserfiche/publications/98901/ERR-274.pdf?v=11513 — ERS ERR-274, **midpoint** herd size

**Done means:** the national herd total, **and** every per-operation figure with
**the name of the statistic attached** — mean, midpoint, or derived.

**Watch for:** the mean is 283 and the midpoint is 1,300. **Both are correct and
they are 4.6× apart.** Report both with their labels; never average them, and
never report one as "average herd size" unqualified. Note also that 24,470 farms
(Census, selling milk, 2022) and 24,811 herds (ERS, licensed, 2024) nearly match
**by coincidence** across different definitions and years — that is not
corroboration.

---

### Item 5 — milk_to_product_ratios

| | |
|---|---|
| `target_table` | `product` (a second product per species) |
| `unit` | **as stated** — lb product per lb *component*, or lb milk per lb product |
| `archetype` | `how-many` |
| `expected confidence` | `measured` on the component basis |

**Question:** How much milk, or milk component, goes into a pound of cheese and
a pound of butter?

**Candidate URLs:**

- https://www.ams.usda.gov/sites/default/files/media/ClassIIIworksheetfinal.pdf — USDA AMS *Calculating Class III Price*. **The best source: USDA-authored, and it labels its units explicitly** (`lb butter/lb butterfat`).
- https://www.govinfo.gov/content/pkg/CFR-2025-title7-vol9/pdf/CFR-2025-title7-vol9-sec1000-50.pdf — 7 CFR 1000.50, the regulation behind it
- https://pubs.nmsu.edu/_e/E216/ — NMSU Extension E-216. The only clean pounds-of-milk-per-pound-of-cheese sentence found on a `.edu`.

**Done means:** the component yield factors with their labelled units, and the
plain-language cheese ratio.

**Watch for — three things:**

1. **Basis.** AMS factors are per pound of *component*, not per pound of *milk*.
   Converting needs a milk-composition assumption. That is a `derived` step and
   **not COOPER's to take.**
2. **A real discrepancy between two current USDA documents.** The CFR uses
   **1.572** and **0.9** where the AMS worksheet uses **1.589** and **0.91**.
   Report the gap; do not pick a winner. The worksheet carries no date.
3. **Ice cream and butter-per-pound-of-milk are deliberately not asked for.**
   "21.2 lb milk per lb butter" and "12 lb milk per gallon of ice cream" have no
   traceable primary source. Ask for ice cream *composition* instead (21 CFR
   135.110: minimum 4.5 lb per gallon, 1.6 lb total solids per gallon, 10%
   milkfat) and let the milk equivalent be an explicit human derivation.

---

### Item 6 — chain_loss

| | |
|---|---|
| `target_table` | `loss_stage` |
| `unit` | percent, at a named stage |
| `archetype` | `how-many` |
| `expected confidence` | `measured` for retail/consumer |

**Question:** How much milk is lost at retail and by consumers, and what does
the 2% farm figure actually measure?

**Candidate URLs:**

- https://ers.usda.gov/sites/default/files/_laserfiche/publications/43833/43680_eib121.pdf — ERS EIB-121. Fluid milk: **12%** retail, **20%** consumer.
- https://www.ers.usda.gov/data-products/food-availability-per-capita-data-system/loss-adjusted-food-availability-documentation — ERS LAFA documentation, same figures in HTML
- https://www.ams.usda.gov/sites/default/files/media/FOR%20FR%20General%20provisions%20sec.%201000%20-%201000.51.pdf — FMMO general provisions §1000.43(b). **Cleanest text of the three routes to the shrink allowance** — single column, extracts perfectly.

**Done means:** the retail and consumer loss percentages, and the verbatim
shrink-allowance text **with its regulatory context stated**.

**Watch for — the most important warning in this spec:**

- **The 2% is a price-classification allowance, not a measured loss.** It caps
  what a handler may assign to the lowest-priced class. It must **not** become a
  `loss_factor` that moves a cow count.
- **LAFA publishes no farm-to-retail dairy loss figure at all.** So the two
  halves of this item are different kinds of number and must not be multiplied
  together without saying so.
- The ERS figures are **table cells, not sentences.** A verbatim-quote gate will
  struggle. Expect this item to need a human.
- EIB-121 and the LAFA documentation are **one ERS estimate published twice** —
  not independent corroboration. The underlying data is from **2010** and the
  series was last updated **2022**.
- `.5` is written in the regulation **without a leading zero**. A regex
  expecting `0.5` misses it.

---

### Item 7 — tanker_and_silo_pooling

| | |
|---|---|
| `target_table` | `mixing_stage` (`pool_lo/mode/hi`) |
| `unit` | loads per year; gallons or pounds per load |
| `archetype` | `provenance-audit` |
| `expected confidence` | `derived` at best |

**Question:** How much milk is in a tanker load, and how many loads are
collected per year?

**Note the question is NOT "how many farms' milk is commingled."** There is no
published figure for that. Sources state repeatedly *that* commingling happens;
the most precise statement found anywhere is **"many farms"**. So the item asks
for the two quantities that *are* published, from which a human can bound the
farm count.

**Candidate URLs:**

- https://www.fda.gov/media/156112/download — FDA *National Milk Drug Residue Database FY2021*. **The one quantitative handle:** every tanker load is sampled once, and it reports **3,494,330** bulk-tanker samples.
- https://farms.extension.wisc.edu/articles/policies-and-regulations-governing-milk-and-dairy-testing-a-wisconsin-overview/ — UW–Madison Extension. The clearest statement that silo milk is *"commingled from many farms"*.
- https://www.fda.gov/media/140394/download — FDA Pasteurized Milk Ordinance 2019. Defines the tanker and mandates per-load sampling. **8.6 MB — will need chunking.**
- https://www.ams.usda.gov/sites/default/files/media/FMMO_NMPF_49.pdf — tanker capacities in **gallons** (6,200 → 8,000). **NMPF testimony, not a USDA finding** → `industry`.

**Done means:** the sample/load count, the capacity figures with units, and the
"many farms" quote as the honest statement of what is not known.

**Watch for:**

- **Do not invent farms-per-tanker.** This is the project's headline question and
  the place where a plausible fabricated number would do the most damage. The
  eggs corpus once borrowed a cascade it should not have; do not repeat it.
- **Do not substitute AMS Dairy Market News's `TL = 40,000–44,000 pounds`.**
  That is **finished product** — cheese, butter, dry whey — not raw milk. Using
  it would understate a raw load by roughly a third.
- FY2021 is the most recent verifiable report. Nothing newer was found.

---

## What to explicitly NOT do

- **Do not convert units during extraction.** This subject spans four unit
  systems: NASS states pounds, Gross states kg, Guinness states litres, NMPF
  states gallons. Every conversion is a separate `derived` step.
- **Do not treat republished NASS estimates as independent agreement.**
- **Do not let the 2% shrink allowance become a loss factor.**
- **Do not report a mean herd size without saying it is the mean.**
- **Do not upgrade an `ams.usda.gov` hearing exhibit to `measured`.**
- **Do not supply a physiological ceiling.** The literature declines to.

## Expected confidence, item by item

| Item | Ceiling | Why |
|---|---|---|
| 1 — annual yield per cow | **`measured`** | NASS states it in a sentence, in pounds |
| 2 — per-day yield | `study` (kg); US average is `derived` | no source publishes a US per-day rate |
| 3 — physiological ceiling | `study` for the absence; `industry` for the record | **undefined in the literature** |
| 4 — herd totals | **`measured`** | NASS and Census |
| 4 — cows per operation | `measured` (283) or `derived` (~380) | depends which statistic |
| 5 — cheese, butter | `measured` on component basis; `derived` per lb milk | AMS labels the factors |
| 5 — ice cream | composition only | no milk ratio published anywhere |
| 6 — retail/consumer loss | **`measured`** | ERS, 2010 data, series last updated 2022 |
| 6 — farm/processing | **not a loss factor at all** | regulatory allowance |
| 7 — pooling | `derived` at best | farms-per-load is unpublished |

This is the richest subject the project has taken on since broilers, and the
first outside poultry where `measured` is reachable. It is also the one with the
most ways to be confidently wrong.
