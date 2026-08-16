# Russia data — research plan

Fifth country. Mirrors `docs/MEXICO-PLAN.md`'s structure and discipline
deliberately: a headline this document does not lead with, a priority-1
table stating what is loaded and at what grade, and access findings written
down rather than papered over.

**Status, 2026-08-16: Russia answers the scale question at `industry`
grade, for 2019-2020 only, and nothing else.** One national chicken-meat
production series is loaded — 4,668,000 tonnes (2019, final) and 4,715,000
tonnes (2020, in-year estimate), both ready-to-cook weight, from a 2020
USDA FAS GAIN report that is the only source this pass found which isolates
chicken from Russia's blended poultry total. No head count, no standing
flock, no output value in rubles, no subnational breakdown, and — the
sharpest gap — **no current (2023-2024) chicken-specific figure at all**,
because every current-year number this pass found for "мясо бройлеров"
(broiler meat) is either unconfirmed against a primary Rosstat table or
directly contradicted by another source describing the same year. Served at
`GET /api/output/RUS` once built.

---

## The headline this demo should NOT lead with

Every Russian broiler figure found in trade press for 2023 or 2024 turned
out to be exactly the kind of trap Mexico's per-capita and world-rank claims
were — and, on inspection, a level worse: Mexico's traps were *contested*
numbers; Russia's is a number that may not be measuring what it claims to
measure at all.

**Claim: "Russia produced 5.34 million tonnes of broiler meat in 2023."**
Three publishers, three numbers, describing the same year, none of them
confirmed chicken-only:

| Figure | Publisher | Label used | Basis |
|---|---|---|---|
| 5,339,467 t | Rosstat's own national workbook (per independent verification — see below) | "птицы" (poultry, ALL species) | slaughter weight |
| 5.34 million t | agromics.ru (trade press) | "мясо бройлеров" (broiler meat) | slaughter weight, claimed |
| 5.156 million t | Tsenovik / ИАА "ИМИТ" (industry analytics) | "мясо птицы" (poultry meat) | slaughter weight |

The first and second numbers are numerically indistinguishable to three
significant figures — which is the opposite of reassuring. If agromics.ru
had genuinely isolated broiler-only production from Rosstat's all-poultry
total, the two numbers should differ by roughly the turkey/duck/goose
share of Russian poultry (a USDA GAIN report elsewhere in this research put
chicken at ~94-96% of Russian poultry meat/inventory in 2019-2020, meaning
a genuine broiler-only figure should read a few percent *below* the
all-poultry total, not identical to it). The most likely explanation is
that agromics.ru's "мясо бройлеров" label is describing Rosstat's
all-poultry aggregate, not a species-isolated one — the same species trap
Mexico's "carne de ave" almost created, except here nothing in the
secondary source's own text resolves it the way bmeditores's explicit
carne-de-ave/carne-de-pollo definition did for Mexico. The third number
(5.156 million t) disagrees with both, for the same year, under the
explicit label "мясо птицы" (poultry, not broiler-specific) — proof that
even industry analysts publishing on the same subject in the same year do
not converge.

**Do not publish any 2023 or 2024 Russian broiler-meat tonnage.** All three
numbers above are recorded in `data/facts.yaml` as an explicit, unresolved
conflict (`russia-2023-poultry-meat-three-way-conflict`) rather than loaded
as a corpus figure or adjudicated by picking the "most authoritative-
sounding" one.

**What the demo can lead with instead:** Rosstat does not publish a
chicken-only national total at all — not "publishes one this project
couldn't reach" the way Mexico's SIAP or Israel's Ministry of Agriculture
did, but genuinely does not break "птица" out by species at the national
level. That is a stronger and more interesting finding than any tonnage
figure this pass could respectably load, and it is checkable independent of
which secondary source is trusted.

---

## Priority 1 — Core production figures

| Field | Why the model needs it | Status 2026-08-16 |
|---|---|---|
| Broilers slaughtered per year (head) | The denominator for everything | **NOT LOADED.** No chicken-specific slaughter count found anywhere, government or industry. |
| Average live weight (kg) | Drives wing size | **NOT LOADED.** No source found reports it directly, and with no head count, there is nothing to derive it from. |
| Total chicken meat production (tonnes) | The scale figure | **LOADED, thin.** 4,668,000 t (2019, final) and 4,715,000 t (2020, in-year estimate), both `industry` grade, RTC weight, from a 2020 USDA FAS GAIN report — the only source in this pass that isolates chicken from Russia's poultry total. **No 2021-2026 figure loaded** — 2021 in the same report is an explicit forecast (excluded, matching Mexico's convention), and no newer Russia-specific GAIN report exists. See "The 2023-2024 conflict" below for why the numbers everyone else is citing for those years are not loaded either. |
| Standing flock (head) | Not throughput, but a real figure elsewhere | **NOT LOADED**, though a candidate exists: the same GAIN report's "Inventory (Reference)" row (523 million head, Jan 2021) is chicken-specific, but the table does not state whether each column is a beginning- or end-of-year figure for its market year, and this project will not guess a year mapping for a stock number. |
| Output value (RUB) | Scale in local currency | **NOT LOADED.** No aggregate ruble figure for chicken meat output specifically was found. |
| Subnational / regional breakdown | The choropleth's Russian counterpart | **NOT ATTEMPTED.** Rosstat does publish regional livestock bulletins by federal subject, but they inherit the same all-poultry-not-chicken taxonomy problem as the national series, and rosstat.gov.ru itself was unreachable from this environment regardless (see below) — not chased further this pass. |
| Per-capita consumption (kg) | The headline candidate | **NOT LOADED.** A single derived figure (36.49 kg/person, agromics.ru, 2024) was found, built from the same unconfirmed production number as the tonnage trap above — not independently corroborated, not loaded. Population NULL. |
| Self-sufficiency / import share | Russia is reportedly a net exporter, unlike Mexico | **NOT LOADED.** Trade-press research (not a primary source) describes Russia as self-sufficient well above 100% for meat generally and a net poultry exporter (roughly 300-410 thousand tonnes of poultry meat and offal exported in 2023-2024, mainly to China, Saudi Arabia, and Kazakhstan), but no single citable source gives a chicken-specific self-sufficiency percentage the way Mexico's GAIN table did. Recorded as directional context in this plan, not as a corpus figure. |

---

## Sources, in order of what was actually reachable

1. **Rosstat** (Федеральная служба государственной статистики) — Russia's
   NASS-equivalent. **Unreachable directly**, and unreachable in a
   different way than any prior country in this project: every fetch tool
   tried (WebFetch, curl, a raw Python request) failed with a
   TLS certificate-trust error, not a DNS failure (Mexico's SIAP) or a
   handshake reset fixable by forcing an older TLS version (Canada's
   StatCan). This reads as Rosstat's certificate chain not being
   recognised by any trust store available in this environment. See "The
   TLS finding" below.
2. **Rosptitsesoyuz** (Росптицесоюз, the national poultry producers'
   union) — the task's suggested industry-detail source. **Unreachable**:
   `rosptitsesoyuz.ru` fails at the DNS level outright, the same shape of
   dead end Mexico's `infosiap.siap.gob.mx` hit. Every Rosptitsesoyuz
   figure in this research pass reaches the corpus secondhand, via press
   coverage of a spokesperson's remarks (Interfax), never from the union's
   own site.
3. **USDA FAS GAIN** — the route that actually worked, exactly as it did
   for Mexico. One report reached: `Russia: Poultry and Products Annual`,
   RS2020-0042, dated 2020-09-21, covering 2019-2021 (2021 as forecast).
   **No newer Russia-specific GAIN report exists** — searches of
   `apps.fas.usda.gov` and the FAS data pages for Russia poultry annuals
   stopped at 2018 and 2020; contrast Mexico, the UK, and Canada, which all
   have a live 2024-25 government-grade series in this project. Plausibly
   explained by reduced USDA agricultural-attaché reporting on Russia
   since 2022, though this pass found no explicit statement to that effect
   and does not assert one.
4. **Trade press and industry analytics** (agromics.ru, Tsenovik/ИМИТ,
   Interfax quoting Rosptitsesoyuz) — reachable, and the trap: three
   sources, three numbers, one year, documented above rather than
   resolved.
5. **FAOSTAT** — not independently queried this pass. A deep-research tool
   reported FAOSTAT's "Meat of chickens, fresh or chilled" production
   series for Russia (via Our World in Data's FAOSTAT mirror) matching
   Rosstat's all-poultry total almost to the exact tonne for 2020-2023
   (5,016,270 / 5,077,481 / 5,308,201 / 5,339,467) — the same numeric
   coincidence as the agromics.ru trap above, and it raises the same
   question: is FAOSTAT's Russia "chicken" line genuinely species-isolated,
   or is it ingesting Russia's reported all-poultry total under the
   "chicken" item code? This project did not verify FAOSTAT's methodology
   directly and does **not** cite a FAOSTAT figure for Russia anywhere —
   flagged here as a real, unresolved doubt for whoever picks this up next,
   not as a settled finding.

### The TLS finding is worth its own note

Every other access failure in this project so far has had a clean shape:
Mexico's SIAP either did not resolve in DNS or refused the TCP connection;
Israel's Ministry of Agriculture returned 403 to every automated fetch;
Canada's StatCan reset a plain TLS 1.3 handshake and was fixed by forcing
TLS 1.2. Rosstat is a fourth, distinct shape: the TLS handshake itself
fails on certificate trust — `curl --tlsv1.2` (Canada's fix) makes no
difference, and the failure message
(`SEC_E_UNTRUSTED_ROOT`/`unable to verify the first certificate`) is
specifically about the certificate's issuing authority, not the protocol
version. This is consistent with Rosstat's site presenting a certificate
issued by a Russian government certificate authority that is not included
in the trust stores available to this research environment — plausible
given that several Western certificate authorities stopped issuing or
renewing certificates for some Russian state domains after 2022, and
Russian sites have moved to a domestic CA (the Russian Ministry of Digital
Development's own root, colloquially "Russian Trusted CA") for some of
that gap. **Not solved this pass.** A human with a browser that already
trusts that CA (or an explicit, approved trust-store override) is the
highest-value next step — see `docs/research/library/poultry-russia.yaml`
for the full diagnostic trail, including a secondhand read of Rosstat's
actual workbook structure via a research tool that evidently reaches the
site through different infrastructure.

### Access findings

**Read `docs/research/library/poultry-russia.yaml` first** — it is the
machine-readable version of this section.

| Source | Result |
|---|---|
| **USDA FAS GAIN RS2020-0042** | **Works, and is the way in.** PDF, 200 OK, extracts cleanly with PyMuPDF once fetched — same workaround Mexico's two PDFs needed. Only source found that isolates chicken from Russia's poultry total. |
| `rosstat.gov.ru` (and regional subdomains) | **TLS certificate-trust failure**, on every tool tried. Not a DNS or connection failure — see above. |
| `rosptitsesoyuz.ru` | **DNS failure.** Does not resolve from this environment at all. |
| agromics.ru | **Reachable**, and the trap — see "The headline this demo should NOT lead with". |
| tsenovik.ru | **Reachable.** A third, conflicting 2023 figure, useful precisely because it disagrees. |
| interfax.ru | **Reachable.** The clearest direct Rosptitsesoyuz quote found, and confirms the union talks in all-poultry terms, at least via this outlet. |
| FAOSTAT | Not independently queried; a secondhand report raises a real doubt about whether its Russia "chicken" series is genuinely species-isolated — see above. Not cited. |

---

## The taxonomy question, and why it is worse than Mexico's

Mexican statistics separate "carne de ave" (poultry, including turkey) from
"carne de pollo" (chicken only) — a distinction this project's Mexico
research resolved by finding a trade-press source that states the split in
one sentence, and by checking every loaded figure against a source's own
wording. **Russia's problem is one level deeper: Rosstat's national
publications do not appear to draw that line at all.** The workbook
structure reported back from a deep-research pass shows a single "птицы"
row — poultry, all species together — with no chicken-only or
broiler-only row to select even if this project could reach the file
directly. This project cannot "check a figure against the source's own
wording" the way it did for Mexico, because Rosstat's own wording never
isolates the species in the first place at the national level.

**Consequence: this project loads only the one source that genuinely
performs that isolation** — the USDA GAIN report's own PSD table, which is
explicitly titled "Poultry, Meat, Chicken" and whose unit line states RTC
weight without ambiguity. Every other Russian figure found in this pass —
Rosstat's own aggregate, agromics.ru's "broiler" label, Tsenovik's
"poultry" figure, Rosptitsesoyuz's forecast — is poultry-wide, and none is
loaded as a chicken-specific corpus figure.

---

## The 2023-2024 conflict, stated plainly

For the single year 2023, this research pass found three published totals
for Russian poultry-meat production, none of them independently confirmed
as chicken-only:

| Figure | Source | Label |
|---|---|---|
| 5,339,467 t | Rosstat national workbook (secondhand) | "птицы" — all poultry |
| 5.34 million t | agromics.ru | "мясо бройлеров" — claimed broiler |
| 5.156 million t | Tsenovik / ИМИТ | "мясо птицы" — all poultry |

The first two are suspiciously close (within 0.01%) for numbers that claim
to describe different scopes (all-poultry vs. broiler-only); the third
disagrees with both by roughly 3.4-3.5%, for the same year, under an
explicit all-poultry label. **This project reports the conflict rather
than resolving it** — see `russia-2023-poultry-meat-three-way-conflict` in
`data/facts.yaml` — the same discipline Mexico's world-rank and per-capita
traps established: three disagreeing sources are three data points about
how hard this question is to answer cleanly, not raw material for picking
a winner.

---

## What "done" looks like for this pass

1. [x] A chicken-specific (not all-poultry) production figure loaded and
   cited, at an honestly stated grade (`industry`, 2019-2020).
2. [x] The taxonomy trap (Rosstat's poultry-wide reporting, worse than
   Mexico's ave/pollo split) resolved in writing.
3. [x] The 2023-2024 three-way conflict documented rather than
   adjudicated.
4. [x] The TLS access failure recorded precisely enough that a future pass
   does not re-diagnose it from scratch.
5. [ ] A current (2023-2026) chicken-specific figure, at any grade.
   **Blocked on the taxonomy problem, not on effort** — every current-year
   number found in this pass failed the "is this actually chicken, not
   poultry" check.
6. [ ] Direct access to Rosstat's own tables. **Blocked on the TLS
   certificate-trust failure** — the single most valuable unblock for a
   future pass, since Rosstat's regional bulletins might yet carry a
   chicken-specific line even where the national bulletin does not.
7. [ ] A head count, at any grade. Not found; no candidate source
   identified this pass, unlike Mexico's (rejected) weekly-throughput
   figure.
8. [ ] Output value in rubles. Not attempted seriously this pass.

## What to explicitly NOT do

- **Do not load any 2021-2026 Russian broiler tonnage figure** found in
  trade press without first confirming it against a primary Rosstat table
  naming the species explicitly. Every current-year figure found in this
  pass failed that check or was contradicted by another source describing
  the same year.
- **Do not treat Rosstat's "птица" aggregate as a chicken figure**, at any
  discount or adjustment factor. This project does not know Russia's
  turkey/duck/goose share precisely enough (a 2019-2020 USDA figure put
  chicken at 94-96% of poultry inventories/meat, but that ratio is
  five-plus years stale and this project will not apply it to a
  2023-2024 total as if it still holds).
- **Do not cite FAOSTAT for Russian chicken meat production** without
  first verifying, from FAOSTAT's own methodology or metadata, whether its
  Russia "chicken" item is genuinely species-isolated. A secondhand report
  found its values matching Rosstat's all-poultry total almost exactly,
  which is reason for doubt, not reassurance.
- **Do not publish a per-capita consumption figure or fill in
  `country.population` for RUS.** The one figure found (36.49 kg,
  agromics.ru) is derived from the same unconfirmed production number the
  tonnage trap above already rejects — compounding one unverified figure
  into another.
- **Do not bypass or work around the Rosstat TLS certificate failure** by
  disabling certificate verification. That is a security control, not an
  incidental obstacle, and this pass did not attempt to defeat it — the
  correct fix is a trust store that legitimately recognises Rosstat's
  issuing CA, which is outside what this research pass could authorize for
  itself.
- **Do not reuse US or Canadian loss factors for Russia without saying
  so.** Nothing in this pass investigated Russia's slaughter/inspection
  chain structure at all.
