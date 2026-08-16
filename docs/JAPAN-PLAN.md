# Japan data — research plan

**Status, 2026-08-16: Japan answers the question at `measured` grade on
every dimension the project asks for, including a full prefecture
breakdown of the head count — the strongest single research pass this
project has produced.** Mexico's plan exists mostly to document what SIAP
could not be reached to publish. Japan is closer to Canada's shape: MAFF's
own e-Stat portal answered directly, for two separate national head counts
(a standing-flock inventory and an annual shipment/throughput figure) with
a genuine 47-prefecture breakdown on the throughput side, plus a
production-tonnage and self-sufficiency-ratio series pulled from MAFF's
Food Balance Sheet. Every number below was read from a raw MAFF `.xlsx` or
`.pdf` fetched directly and parsed programmatically — not typed from a
rendered page, and not taken secondhand from the USDA FAS GAIN report,
which is loaded here only as an independent cross-check.

Loaded at `GET /api/output/JPN`, alongside `GET /api/countries`.

## The one caveat that matters more than any single number

MAFF's national annual bird count is **出荷羽数 ("shipment number")** — birds
shipped off the farm within the past year — not a post-mortem count taken
at a processing plant the way Statistics Canada's registered-plant
slaughter reports are, or the way DEFRA's Food Standards Agency
slaughterhouse survey is for the UK. This project loads it as
`head_slaughtered` anyway, on the working assumption that a broiler
shipped from a Japanese farm has no destination other than immediate
slaughter. **That assumption was not independently verified against a
separate post-mortem count** — no such Japanese national figure was found
in this research pass. Named explicitly, per the project brief's own
instruction not to conflate shipment with slaughter silently. See
`docs/research/library/poultry-japan.yaml` and the `maff-chikusan-toukei-
broiler-2024` source notes for the full reasoning.

## Priority 1 — Core production figures

| Field | Why the model needs it | Status 2026-08-16 |
|---|---|---|
| Broilers shipped per year (head) | The denominator for everything | **LOADED at `measured`.** 731,847 thousand birds for the year ending 2024-02-01, from MAFF's Livestock Statistics Survey table 5(4) — read directly from the raw e-Stat `.xlsx`. See the shipped-vs-slaughtered caveat above. |
| Standing flock (head) | Not throughput, but a real government figure elsewhere | **LOADED at `measured`.** 144,859 thousand birds as of 2024-02-01, across 2,050 farms, up 2.4% year on year — table 5(1) of the same survey. Independently corroborates the USDA FAS GAIN report's own secondhand citation of this exact MAFF figure ("approximately 145 million... up two percent"), which is a genuine cross-check: the primary table and a US attaché's paraphrase of it agree. |
| Average live weight (kg) | Drives wing size | **NOT LOADED.** No source found reporting it directly, and — as with Mexico — nothing in this pass derives one, because the two head counts available (inventory, shipment) are not on the same basis as the tonnage figure (bone-in-equivalent) closely enough to divide safely without manufacturing a number. |
| Total chicken meat production (tonnes) | Cross-check against head × weight | **LOADED at `measured`.** 1,690 thousand tonnes FY2023 (provisional, MAFF's own 概算値), 1,681 thousand tonnes FY2022 (confirmed), bone-in-equivalent basis — MAFF's Food Balance Sheet. Cross-validates within 0.2% against the USDA FAS GAIN report's independent 2023 estimate (1,686 thousand MT). |
| Output value (JPY) | Scale in the local currency | **NOT LOADED.** No aggregate yen figure for chicken meat output specifically was found in this pass — the same gap Mexico's plan recorded for pesos, for the same reason: value figures found were for the whole livestock sector or for feed spend, not chicken meat output alone. |
| Subnational breakdown | Gives the choropleth a Japanese counterpart | **LOADED**, and it reconciles exactly — see below. |
| Per-capita consumption (kg) | The headline candidate | **LOADED as a fact.** 14.4 kg/person, FY2023 (down 0.7% from 14.6 kg FY2022) — MAFF's own Food Balance Sheet net-food-supply figure, the same "disappearance"-style supply proxy Canada's AAFC figure is, not a measured intake survey. |
| Self-sufficiency / import share | How much of its own chicken Japan grows | **LOADED at `measured`.** 65% FY2023 (up from 64% FY2022), weight basis, chicken meat specifically — a genuinely different statistic from Japan's much more widely quoted overall calorie-basis food self-sufficiency rate (38%, covering every food category at once). |

### The prefecture reconciliation is exact, like Canada's regional total and unlike its provincial rounding gap

MAFF's own nine regional-agricultural-bureau subtotals (covering all
forty-seven prefectures between them, with Hokkaido and Okinawa each
standing alone as a single-prefecture region) sum to **precisely** the
national total: 731,847 thousand birds, to the exact thousand, with no
rounding gap at all — unlike Canada's ±1-thousand-kilogram StatCan gap on
the equivalent weight reconciliation. This is worth stating for the same
reason Canada's near-exact reconciliation was: a partition that closes
exactly means the regional figures and the national figure are the same
underlying count, not two surveys that happen to agree.

Suppressed prefecture cells (`x` in MAFF's own table — too few operations
to publish without risking identifying a single farm) are loaded as
suppressed rows with no value, the same presence-without-volume pattern
CBS, NASS and StatCan all use. Cells marked `-` (genuinely no broiler
operations meeting the survey's scope) are loaded as `value: 0` — MAFF's
own table distinguishes the two explicitly, and this project preserves
that distinction rather than collapsing both into "no data."

### The regional concentration is the sharpest this project has recorded

Kyushu alone is 49.3% of national shipments; Tohoku a further 24.6%;
together 73.8% of the country's broilers come from two of Japan's ten
national-agricultural-bureau regions. Within Kyushu, Kagoshima (21.8% of
the *national* total on its own) and Miyazaki (18.7%) join Tohoku's Iwate
(16.7%) as the three prefectures — out of forty-seven — that between them
account for more than half of every broiler shipped in the country. This
is a sharper concentration than Canada's (Ontario, the largest single
province, is 32.6% of that country's head count) and matches the
concentration the project brief expected going in.

## Sources, in order of preference

1. **MAFF's Livestock Statistics Survey (畜産統計調査), via e-Stat** —
   Japan's NASS-equivalent, and — like Statistics Canada, unlike SIAP —
   genuinely reachable: the survey's own `.xlsx` tables downloaded directly
   from e-Stat's file-download endpoint and parsed with `openpyxl`, no
   scraping of a rendered page and no PDF font-encoding trap. See
   "e-Stat is worth its own note" below.
2. **MAFF's Food Balance Sheet (食料需給表)** — a second, separate MAFF
   publication (not the Livestock Statistics Survey), built to the FAO
   Food Balance Sheet handbook and covering production tonnage,
   per-capita supply, and the self-sufficiency ratio. Its own stated
   methodology (item 3 of the general estimation principles) says these
   figures are "MAFF's own survey values or estimated values" — so
   "measured" here means MAFF's official headline figure, not a raw
   slaughter census the way the Livestock Statistics Survey is.
3. **USDA FAS GAIN, `Japan: Poultry and Products Annual` (JA2024-0043)** —
   used here as a cross-check, not the primary route into Japanese
   figures the way the equivalent report was for Mexico. Its own PSD
   table's "USDA Official" and "New Post" columns disagree with each
   other (2024 production: 1,790 vs 1,720 thousand MT), so neither column
   is loaded; only its prose citation of MAFF's own broiler-population
   figure is used, purely as corroboration of a primary MAFF table this
   project also read directly.

### e-Stat is worth its own note

Statistics Canada's Web Data Service earned a note in `CANADA-PLAN.md` for
being "a real REST API... not a document to be scraped." e-Stat is not
quite that — there is no equivalent single JSON query — but its
`file-download` endpoint serves genuine raw `.xlsx` files directly, no
authentication, no JavaScript shell, and WebFetch's own PDF/binary
summarizer (which repeatedly failed to extract numbers correctly from
these files — see "Access findings" below) can be routed around entirely
by fetching the binary, saving it, and parsing it with `openpyxl` instead
of asking a text-summarization model to read compressed XML. That
combination — fetch the raw file, do not trust an AI summary of a binary
format for exact figures — is worth carrying into any future country pass
that hits a similarly binary-only government portal.

### Access findings

**Read `docs/research/library/poultry-japan.yaml` first** — it is the
machine-readable version of this section.

| Source | Result |
|---|---|
| **e-Stat file-download endpoint (`.xlsx`)** | **Works, and is the way in.** Raw Excel, no auth, parses cleanly with `openpyxl` once saved locally. WebFetch's own text summarizer cannot read it directly (reports "binary/compressed... cannot extract"), which is the correct failure mode — better than a summarizer guessing at numbers, which is exactly what happened on the first attempt at MAFF's PDF food balance sheet (see below). |
| **MAFF Food Balance Sheet PDF (`maff.go.jp/.../240808-4.pdf`)** | **Works when read directly**, but WebFetch's prompted summary of it produced a materially WRONG production figure on the first attempt (1,240,000 tonnes; the correct figure, confirmed against the PDF's own tables and against independent trade-press reporting of the same MAFF release, is 1,690,000 tonnes for FY2023). This project's PDF reader, pointed at the saved file directly rather than through a prompted summary, produced the correct figure. **Treat any WebFetch-summarized number from a binary document as unverified until read from the primary table directly** — the failure here was silent and plausible-looking, not an obvious garbage string. |
| **USDA FAS GAIN JA2024-0043 PDF** | **Works.** Extracts cleanly via this project's PDF reader, same route as Mexico's and Canada's GAIN reports. |
| **MAFF self-sufficiency press release page (`maff.go.jp/j/tokei/kekka_gaiyou/...`)** | **403 Forbidden** to WebFetch on one attempt (a different MAFF host/path than the ones that worked); not chased further since the Food Balance Sheet PDF already carried the same figures directly. |
| Trade press (keimei.ne.jp, region-case.com, jaccnet) | **Reachable, and useful for corroboration**, but never the primary citation — every trade-press figure used in this plan's prose is stated as corroboration of a MAFF or GAIN figure already loaded, never loaded on its own authority. |

## Priority 2 — What makes the demo land

- **Two different head counts, cleanly distinguished.** Japan is the first
  country in this corpus with BOTH a genuine standing-flock inventory
  (144,859 thousand, Feb 1 snapshot) and an annual throughput proxy
  (731,847 thousand, shipped over the prior year) from the same government
  survey, at the same grade, for the same census date — Canada's plan
  noted standing flock does not exist for Canada at all under supply
  management, and this project's US data has never carried both figures
  from a single publisher this cleanly either.

- **A basis caveat worth teaching, not just noting.** The shipped-vs-
  slaughtered distinction is a genuinely different shape from Canada's
  eviscerated-vs-live weight trap and the UK's carcase-weight footnote:
  those are about how much a bird weighs once counted, and this is about
  whether a bird has actually been counted at the point this project's
  model needs (post-mortem) or one step earlier (shipped for slaughter).
  A strong learning-centre fact, not just a footnote.

- **Regional concentration, sharper than anywhere else in the corpus.**
  Two of ten regions produce three-quarters of the country's chickens, and
  three prefectures out of forty-seven produce more than half. Worth its
  own fact, and a strong choropleth story once the frontend can render it.

- **A genuine two-publisher cross-check.** MAFF's own production figure
  and USDA FAS GAIN's independent estimate land within 0.2% of each other
  for the same year, arrived at by different methodologies. Worth a fact
  in its own right — the kind of agreement that makes a number worth
  trusting, distinct from the Canada/CFC weight-basis DISagreement that
  was worth a fact for the opposite reason.

- **Wings specifically.** Neither the Livestock Statistics Survey nor the
  Food Balance Sheet reports wings as a separate cut. Not attempted
  further this round, the same honest gap Canada's plan recorded.

## What "done" looks like for this pass

1. [x] A national head count loaded at `measured` grade, with the exact
   basis (shipped, not post-mortem-slaughtered) stated rather than
   assumed — arguably the strongest single evidentiary chain this project
   has for a non-US country, precisely because the caveat is explicit
   rather than glossed over.
2. [x] A separate standing-flock inventory figure, also `measured`,
   cross-validated against an independent secondhand citation of the same
   underlying MAFF table.
3. [x] A full 47-prefecture breakdown loaded, reconciling exactly against
   the national total.
4. [x] Production tonnage and a chicken-specific self-sufficiency ratio,
   both `measured`, cross-validated within 0.2% against an independent
   USDA estimate for production.
5. [x] Per-capita figure loaded as a fact, population left `NULL`, matching
   every other country in this corpus.
6. [ ] Average live or bone-in weight per bird — not derived this pass;
   flagged for a future pass rather than manufactured from mismatched
   bases.
7. [ ] Output value in yen — not found this pass, the same gap Mexico's
   plan recorded for pesos.
8. [ ] Wings as a separate reported cut — not found, not chased further.

## What to explicitly NOT do

- **Do not silently treat Japan's head count as equivalent in kind to
  Canada's or the UK's.** MAFF's figure is a shipment count; StatCan's and
  DEFRA's are post-mortem or near-post-mortem counts. Loading Japan's
  figure as `head_slaughtered` is a judgment call, stated plainly, not a
  fact this project independently verified against a separate post-mortem
  Japanese count.
- **Do not merge the inventory figure (144,859 thousand, a snapshot) with
  the shipment figure (731,847 thousand, an annual flow) to compute a
  turnover rate or an implied grow-out cycle count** without labelling
  that derivation `derived` and explaining the two different bases —
  this project did not attempt that derivation this pass.
- **Do not divide the tonnage figure by either head count to derive an
  average bird weight.** The tonnage is bone-in-equivalent; neither head
  count is stated on a matching processed-weight basis, so a division
  would manufacture a number nobody published, the same trap Canada's
  plan explicitly avoided with CFC's live-weight table.
- **Do not conflate Japan's chicken-meat self-sufficiency ratio (65%,
  FY2023) with its overall calorie-basis food self-sufficiency rate (38%,
  same year).** They are different statistics from the same publication,
  and Japanese press coverage sometimes runs them in the same sentence
  without distinguishing them clearly.
- **`country.population` stays `NULL`.** The per-capita figure this
  project actually wants (14.4 kg/person, FY2023, MAFF) is already
  published as a ratio; loading it as a fact answers the question without
  also having to source, date, and defend a Japanese population estimate
  for a calculation nothing else in the corpus performs — the same
  discipline every prior country in this corpus follows.
- **Do not trust a WebFetch prompted summary of a binary PDF or Excel file
  for an exact number.** This pass hit exactly that failure once (a
  materially wrong production figure from a summarized PDF) and caught it
  only by reading the source document directly with this project's own
  PDF/Excel tooling. Treat any AI-summarized figure from a binary document
  as a lead to verify, not a citable number.
