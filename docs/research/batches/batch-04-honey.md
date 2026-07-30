# Batch 04 — honey and honeybees

**Archetype:** `how-many` + a new one, `provenance-audit`

**Question in one sentence:** How many bees does it take to make a jar of
honey — and does anybody actually know?

**Expected confidence ceiling:** `measured` for Item 5 only. Everything else
tops out at `industry`, and two items should probably not ship at all.

---

## Read this before running the batch

A human scouted this subject before the spec was written, and the scouting
changed what the batch asks. **The two most famous numbers in this subject
appear to be folklore.**

**"A bee makes 1/12 of a teaspoon of honey in her lifetime."** Three land-grant
extension services state it. None cites a study. University of Arkansas hedges
it as "It has been estimated" — passive, no agent. Iowa State attributes it
outright to *"National Honey Board trivia."* The National Honey Board's own site
returns 403 and cannot be fetched, so the origin is attested only secondhand.
Meanwhile the Canadian Honey Council, a national trade body, says **1½
teaspoons** — eighteen times more.

**"Two million flowers per pound of honey."** UF/IFAS is the only extension
publication that attaches a citation, and the citation is *Jaganathan and Mandal
2009* — a **cancer-biology review of honey polyphenols**, where the sentence
sits in the introduction **with no reference attached to it at all**. Verified in
PubMed Central. An extension service is laundering an uncited factoid out of an
oncology paper, and UW–Madison and Missouri Extension repeat the same 2 M /
55,000 mi pairing. Those are not three sources. They are one claim with three
repeaters.

So this batch is **partly a provenance audit**, and that is the interesting
work. The project's whole claim is that every number traces to a real source.
Honey is the first subject where the famous numbers appear not to, and
documenting that is worth more than shipping them.

**A figure with no traceable origin does not ship. Reporting that it has no
origin IS the deliverable.**

---

## Why this subject

Honey is the most extreme ratio available to the project, and it has the same
shape as wings for a reason worth stating: **a hive is a pooling machine.**
Every drop is blended by the colony before anyone opens a jar, so the
distinct-versus-required gap is total rather than partial. Where a wing
sometimes stays with its pair, no bee's honey ever stays separate.

It also settles a modelling question without new schema. The **bee** is the
individual, with a lifetime yield (`continuous`). The **hive** is a
`mixing_stage` with `mixing_kind: random` and a very large pool — not a new tier
above species. Colony, herd, and plant-bearing-many-flowers all look like they
need a group level in the schema, and this one does not.

---

## Fetch-reliability notes — read before queueing

Confirmed **403/404, do not queue**: `honey.com` (both pages), 
`extension.oregonstate.edu/catalog/...` (PNW 623), `royalsocietypublishing.org`,
`onlinelibrary.wiley.com`, `openknowledge.fao.org`,
`beeculture.com/thermal-efficiency/`.

Cross-host redirects that **silently return nothing** — point the fetcher at the
destination: `usda.library.cornell.edu` → `esmis.nal.usda.gov`, and
`www.ncbi.nlm.nih.gov/pmc/articles/...` → `pmc.ncbi.nlm.nih.gov/articles/...`.

One document will look like a model failure and is not: Mississippi State P2941
fetches fine and contains **no population figures at all**. Search engines
misattribute figures to it. It is deliberately not listed below.

---

## Items

### Item 1 — honey_per_bee_lifetime

| | |
|---|---|
| `target_table` | `product` |
| `required_fields` | `value_lo/mode/hi`, `unit` |
| `unit` | mass or volume of honey per bee — **whatever unit the source uses** |
| `archetype` | `provenance-audit` |

**Question:** How much honey does one worker bee produce in her lifetime, and
**who measured it?**

**Candidate URLs:**

- https://www.uaex.uada.edu/farm-ranch/special-programs/beekeeping/documents/Basic%20Beekeeping%20-%204%20-%20Bee%20Biology.pdf — U. Arkansas extension, PDF, clean text layer. **Best-value document in the batch: also answers Items 3 and 6.**
- https://extension.missouri.edu/publications/m403 — U. Missouri Extension M403, HTML
- https://blogs.extension.iastate.edu/answerline/2022/09/20/september-is-national-honey-month/ — Iowa State. **Use this dated permalink, not the paginated index.** Carries the provenance admission.
- https://honeycouncil.ca/how-to-make-a-pound-of-honey/ — Canadian Honey Council. **Included deliberately because it conflicts.**

**Done means:** the figure, its unit, AND an explicit statement of whether the
source cites anyone. Report the hedging language verbatim — "It has been
estimated" and "National Honey Board trivia" are the most valuable strings in
this batch.

**Watch for:** the **lifetime basis differs between sources and they are not
answering the same question.** Missouri says a "six-week lifetime" (total adult
life). Arkansas says the foraging career is "usually less than a couple of
weeks". A bee spends most of her adult life as a nurse, not a forager. Do not
merge these.

**Do not resolve the 1/12 vs 1½ teaspoon conflict.** Report both.

---

### Item 2 — flowers_per_pound_honey

| | |
|---|---|
| `target_table` | `loss_stage` / narrative |
| `unit` | flowers per pound or per kilogram — **as the source states it** |
| `archetype` | `provenance-audit` |

**Question:** How many flowers must be visited per pound of honey, and does the
figure derive from anything?

**Candidate URLs:**

- https://honeycouncil.ca/how-to-make-a-pound-of-honey/ — **the best source for this item, because it shows its arithmetic** and lands on 2.6 million rather than 2 million. States its assumptions (32 mg nectar load, 45% sugar, 17 mg honey per load) and names the primary literature (Park 1922/1925, Lundie 1925, Ribbands 1949).
- https://ask.ifas.ufl.edu/publication/UW546 — UF/IFAS WEC477. The only extension source that attaches a citation to the 2 M claim.
- https://pmc.ncbi.nlm.nih.gov/articles/PMC2712839/ — Jaganathan & Mandal 2009, the cited paper. **Check whether the sentence carries a reference. It does not.**
- https://blogs.ifas.ufl.edu/duvalco/2026/06/26/its-honey-season/ — introduces a bees-per-pound figure (500–600)

**Done means:** both the 2 M and 2.6 M figures, with the CHC assumptions
recorded, and a plain statement of whether Jaganathan & Mandal cite a source for
their sentence.

**Watch for:** **do not grade Jaganathan & Mandal as `study`.** It is a
peer-reviewed article, but the figure inside it is uncited scene-setting in a
paper about cancer cells. Document type and claim support point in opposite
directions here, and the grade must follow the support.

---

### Item 3 — colony_size

| | |
|---|---|
| `target_table` | `mixing_stage` pool |
| `unit` | bees per colony |
| `archetype` | `how-many` |

**Question:** How many bees are in a productive colony at peak season?

> **Field names must be single identifiers.** This item and the next were one
> item until the spec was checked. Batch-01 had a heading reading
> `stigmas_per_pound cross-check`, and COOPER faithfully emitted a finding whose
> `field` was `stigmas_per_pound cross-check` — a field name with spaces in it,
> which is not a field name. The spec caused that, not the model.

**Candidate URLs:**

- https://canr.udel.edu/maarec/honey-bee-biology/the-colony-and-its-organization/ — MAAREC, the seven-state extension consortium. Gives colony size; **gives no forager fraction, do not expect one.**
- https://ucanr.edu/blog/bug-squad/article/foraging-force-honey-bee-colony — **the only source found with an explicit forager fraction** ("usually consists of one-third of the total population"), quoting Eric Mussen, UC Davis extension apiculturist. A blog on a university domain: institutional voice, weak format. Grade accordingly.
- https://www.uaex.uada.edu/farm-ranch/special-programs/beekeeping/documents/Basic%20Beekeeping%20-%204%20-%20Bee%20Biology.pdf — colony range, and the foraging-career sentence that makes Item 1's basis separable
- https://extension.missouri.edu/publications/m403 — distinguishes **feral** (14,000–25,000) from **managed** (up to 60,000), which nothing else does

**Done means:** a colony-size band with its definition attached.

**Watch for:** most of the apparent disagreement here is **definition drift, not
conflict** — peak season vs annual average, feral vs managed. 60,000 max,
20,000–60,000, 40,000–50,000 at peak, and 14,000–25,000 feral are largely the
same claim under different definitions. Record which definition each figure
uses, and do not average them.

---

### Item 4 — forager_fraction

| | |
|---|---|
| `target_table` | `mixing_stage` pool |
| `unit` | fraction of colony population that forages |
| `archetype` | `how-many` |

**Question:** What fraction of a colony's bees are foragers rather than nurses
or house bees?

**Candidate URLs:** as Item 3.

**Done means:** the fraction, flagged as **single-sourced**. One-third comes from
exactly one source (UC ANR, quoting Mussen) and must not be presented as
consolidated. If no second source states it, say so.

**Watch for:** this fraction is what turns colony size into a bee count for a
jar of honey, so it carries more weight in the final answer than its evidence
supports. That asymmetry should be stated in the corpus notes, not smoothed over.

---

### Item 5 — honey_yield_per_colony_year

| | |
|---|---|
| `target_table` | `husbandry_stat_year` |
| `unit` | **pounds** per colony per year |
| `archetype` | `how-many` |
| `expected confidence` | **`measured`** — the only item here that can reach it |

**Question:** What is the average US honey yield per colony per year?

**Candidate URLs:**

- https://esmis.nal.usda.gov/sites/default/release-files/795818/hony0326.txt — **USDA NASS *Honey*, released 2026-03-13, PLAIN TEXT. Best fetch target in the whole batch — no PDF path, no layout ambiguity.**
- https://www.nass.usda.gov/Publications/Todays_Reports/reports/hony0326.pdf — same release as PDF, with per-state tables
- https://esmis.nal.usda.gov/concern/publications/hd76s004z — the series archive, for a time series
- https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/Bee_and_Honey/ — methodology, which is what licenses a `measured` grade

**Done means:** 2025 yield per colony, colonies producing honey, and total
production, from the NASS release itself.

**Watch for — two real traps:**

1. **Wrong-year table.** The PDF carries the **2024** state table *before* the
   2025 one. Any retrieval that grabs "the first yield-per-colony table" gets
   the wrong year. Prefer the `.txt`.
2. **NASS's own caveat must ride along with the figure:** *"Colonies which
   produced honey in more than one State were counted in each State where the
   honey was produced. Therefore, at the United States level yield per colony
   may be understated."* A figure this project publishes without that sentence
   is a figure it has overstated.

**Also note:** NASS measures **harvested** honey, so this figure is *already net
of extraction loss.* See Item 7.

---

### Item 6 — nectar_to_honey_ratio

| | |
|---|---|
| `target_table` | `loss_stage`, `applies_to: mass` |
| `unit` | mass nectar per mass honey; sugar % and moisture % as stated |
| `archetype` | `how-many` |
| `expected confidence` | `study` for the inputs; **the ratio itself is `derived` and COOPER may not assign it** |

**Question:** How much nectar becomes one kilogram of honey?

No source states this as a measured figure. What exists is the **mass-balance
inputs** — nectar sugar concentration and honey moisture — from which the ratio
follows. So COOPER's job is the inputs, and a human does the division. This is
the same split that worked for saffron drying: **a finding reports a source, a
corpus row models it.**

**Candidate URLs:**

- https://pmc.ncbi.nlm.nih.gov/articles/PMC9519551/ — Nicolson, Human & Pirk 2022, *Scientific Reports*, open access. **The strongest source in the batch and the only one that legitimately merits `study`** — peer-reviewed and genuinely on this topic.
- https://www.uaex.uada.edu/farm-ranch/special-programs/beekeeping/documents/Basic%20Beekeeping%20-%204%20-%20Bee%20Biology.pdf — the plain-language endpoints ("perhaps up to 80%" water in, below 20% out)
- https://honeycouncil.ca/how-to-make-a-pound-of-honey/ — the only per-load statement: 32 mg nectar at 45% sugar → 17 mg honey
- https://pmc.ncbi.nlm.nih.gov/articles/PMC5094517/ — Knopper et al. 2016, per-crop nectar sugar ranges. **This is what makes the ratio a range rather than a number.**

**Done means:** nectar sugar concentration ranges and honey moisture figures,
each with its unit as stated. **Do not compute the ratio.**

**Watch for:** a **"60 pounds of nectar per pound of honey"** claim circulates
widely. It is off by more than 10× against any mass balance — it would require
1.4% sugar nectar, which does not exist. **Reject it on sight.** Nicolson also
finds much dehydration happens *in flight*, before nectar reaches the comb,
which complicates the "bees fan it dry in the hive" story the extension sources
tell.

---

### Item 7 — extraction_recovery

| | |
|---|---|
| `target_table` | `loss_stage` |
| `archetype` | `provenance-audit` |
| `expected confidence` | **probably does not ship** |

**Question:** What fraction of honey in the comb is recovered at extraction?

**The scouting answer is that this figure may not exist, and may not be a
well-posed question.** Five search strategies returned nothing authoritative and
quantitative. Two structural reasons, both of which belong in the corpus as
prose rather than as a number:

1. Standard practice is to return "wet" supers to the colony, so residual honey
   is **re-harvested or eaten, not lost.** A one-way loss factor may be the
   wrong shape entirely.
2. NASS (Item 5) measures **harvested** honey. Applying an extraction loss on
   top of a NASS yield would **double-count** — the same trap as applying
   saffron drying loss to an already-dried-basis figure.

**Candidate URLs:**

- https://www.iahiservices.com/journal/index.php/BSPJMR/article/download/95/58 — the only quantitative source found: 92.5–96.8% recovery. **A hand-crank prototype extractor tested on three frames at 250–750 g loads.** That is a few ounces, not a commercial run, in a journal in its second volume.
- https://www.fao.org/4/w0076e/w0076e05.htm — FAO/Krell. Good on honey **moisture**; has **no recovery fraction**. Legacy path works; the `openknowledge.fao.org` path 403s.

**Done means:** either a citable recovery figure, or — more likely and equally
valuable — **a plain statement that none was found**, with the double-counting
note recorded.

**Do not** generalise the prototype-extractor figure to "the fraction of honey
recovered at extraction". If it ships at all it is `estimate`, with the basis
named as one prototype at sub-kilogram loads.

---

## Honest expectation

One item can reach `measured` (NASS yield per colony). One can reach `study`
(nectar concentration). Two are provenance audits whose likely finding is *"this
number has no traceable origin"*. One is single-sourced. One probably does not
ship.

That is a **thinner** result than saffron, and saffron was already thin. Ship it
flagged or not at all. The audit prints the confidence mix on every build, so
the thinness is visible rather than hidden — and for a subject whose famous
numbers turn out to be trivia, documenting the absence is the honest product.
