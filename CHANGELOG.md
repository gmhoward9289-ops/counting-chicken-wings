# Changelog

## Unreleased

### A/B harness for the frontend

Two frontends can now be served from one URL, with measurement attached, so a
redesign can be argued about with numbers instead of taste.

- `experiment.py` assigns a variant per visitor and makes it **stick**. The
  choice is deterministic from a random cookie id rather than a coin flip per
  request, because a page that changes under the person being measured
  measures nothing. `?ui=a` / `?ui=b` forces and pins a variant by hand.
- **The split defaults to 0%** — everyone gets the shipped page until
  `WINGS_AB_SPLIT` deliberately turns the experiment on. Deploying this
  branch does not change what a visitor sees.
- `metrics.py` stores events in **its own SQLite file** (`metrics.db`,
  `WINGS_METRICS_DB`), and refuses to open `chickens.db`. `build` recreates
  the corpus database, which would destroy the measurements; the corpus is
  also what the citation audit reasons about, and an observation is not a
  cited figure.
- `static/ab.js` is shared verbatim by both variants — an instrument that
  differs between the arms measures itself. It attaches from outside the page
  (delegated listener, fetch wrapper), so neither design has to be edited to
  be measured and the redesign cannot forget to instrument anything.
- `GET /api/metrics/summary` compares the arms: load time, API latency,
  dwell, time to first interaction, interaction rate, error rate, how much of
  the UI got found. It reports no significance test, and says so.
- `static/v2/index.html` is seeded as an **exact copy** of the shipped page,
  so the first run is an A/A test that measures the noise floor. A later
  difference smaller than that one is not a difference.
- `test_static.py`'s structural invariants now run against **both** pages.
  The redesign is a second page, not a second standard.

### Which arm an event belongs to is signed

Found by exercising it in a browser rather than only in tests: the `dwell`
beacon fires during unload, so deriving the variant from the cookie at POST
time credited 32 seconds of variant b to variant a — silently, on the event
the comparison most depends on.

The page now carries a signed token naming its own variant, issued when it
was served. A cookie describes the browser *now*; a token describes the page
that earned the measurement. It is bound to the session cookie so it cannot
be replayed under another id, and it expires after 12 hours. Letting the page
simply assert its variant would have fixed the attribution and opened a
different hole, since `/api/metrics` is public and unauthenticated.

Consequences worth knowing:

- **`WINGS_AB_SECRET` must be set** for anything that restarts, and must be
  one value across processes. Otherwise tokens are signed with a per-process
  key and refused after a restart, losing those events as what looks like
  light traffic rather than as a misconfiguration. `render.yaml` now
  generates one; a warning is logged if the experiment is on without it.
- `/` is rendered rather than served as a file, to substitute the token.
  Cached on mtime, so editing a variant is still picked up without a restart.
- One session can contribute at most 2,000 events. A signature proves which
  arm a page is; it does not stop that page reporting a million times, and
  every rate in the summary is per-session.

### The Render deployment cannot store what it collects

Noted rather than fixed, because fixing it costs money. That service has no
disk — deliberately, it is read-only at runtime — so `metrics.db` sits on the
container filesystem and is lost on every deploy and every wake from the free
tier's idle spin-down. `WINGS_AB_SPLIT` is pinned to `0` there.

`/api/metrics/summary` now reports `collecting_since` and `window_hours`, so
an emptied store reads as a window that keeps resetting rather than as a
quiet week.

## v1.9.1 — 2026-07-30

Wording only: the Israel-facing copy now leads with what Israel's sources
are, not with what they lack. No figure, citation, grade, or behaviour
changed — the government-only view still carries no slaughter count, and the
corpus still refuses to derive one.

The learning-centre fact `israel-head-count-is-not-measured` (slug unchanged)
now opens with the strength of the coverage — CBS's poultry series reaching
back to 1960, and the industry bodies' detailed public sector tables — and
presents the missing heads-slaughtered series as a definitional choice many
national statistical systems make, with the US enumeration as the exception.
The no-derivation stance is stated as this corpus's own discipline rather
than as an Israeli gap. The country view's intro, its coverage notes, and the
`/api/countries` and `/api/output` docstrings got the same reframe.

No test assertions changed: they pin identifiers and data, not prose, which
is exactly why a copy edit of this size touches nothing else.

## v1.9.0 — 2026-07-30

Maple syrup: the third domain, and the first individual that survives being
harvested.

### A tree is not consumed, and that is the point

A chicken is killed, a flower is picked, a hen at least stays put. A sugar
maple is tapped, runs for about six weeks, and does it again next spring for
upwards of a century — the longest-lived individual in this corpus by two
orders of magnitude.

That made it the right subject to be the first real use of `yield_period_days`
for a period that is **not a year**. Eggs grew the field; maple proves the
period is data rather than an assumption, because reading maple's season as a
year would overstate a tree's output about eightfold.

**About a quart of syrup per tree per season**, so one gallon represents
roughly 2 to 9 tapped trees working through a spring — and about 430 gallons of
sap boiled away.

### The band is the sugar content, not measurement error

The famous "40 gallons of sap to a gallon of syrup" is a special case, and
storing it alone would have hidden the variable that produces it. UVM's Jones
Rule of 86 gives the real relationship: gallons of sap = 86 ÷ the sap's sugar
concentration in °Brix. Sap runs anywhere from 1% to 5%:

```
1 Brix -> 86 gal sap per gal syrup     5 Brix -> 17 gal sap per gal syrup
2 Brix -> 43 gal  (this is the "40")
```

A five-fold spread in which every value is correct, for a different tree on a
different day. So the corpus cites the rule, not the constant.

### Boiling cannot make trees fewer

`maple_syrup_gallon` already states gallons of **syrup**, so the boil is priced
in; applying the 40:1 concentration again would divide the answer a second
time. Boiling is therefore recorded as `applies_to: mass`, and
`affects_count()` refuses to let a mass stage move a count.

This is the third unrelated process — frying a wing, drying a stigma, boiling
sap — caught by one rule that has never needed modifying. Saffron's own file
warns about the identical trap in its own terms.

### Honest about the grade

Every figure is `industry` and the combination is our arithmetic; nothing here
is measured. The per-tap yields disagree between two extension services (UMaine
5–15 gal, NY State Maple 10–20) and that disagreement is kept as a range rather
than averaged away. The whole subject rests on one modal assumption — NY State
Maple's "most trees today have only one tap" — which is what lets a per-tap
figure stand as a per-tree figure without an invented multiplier. If that
sentence stops being true these numbers need redoing, not adjusting.

USDA NASS does publish a Maple Syrup report with state production and tap
counts. Loading it is the obvious way to put a measured floor under this, and
is the single most valuable next source for the subject.

Provenance: `docs/research/accepted/batch-07-maple-REVIEW.md`. Note that COOPER
returned the folk 40:1 with the Rule of 86 retrieved and in front of it — the
preference for the round number was the model's, not a retrieval failure, and
the promotion here deliberately reverses that choice.

### Also in this release

- `WINGS_DB` environment variable overrides where the SQLite database is built
  and read. Previously the path derived from `__file__`, which is correct only
  under an editable install, and the API — unlike the CLI with `--db` — had no
  way to point at a different database at all. No published number moves.

## v1.8.0 — 2026-07-30

A rollup: thirteen commits, six of them merged without a release. Every active
product's published answer was compared against v1.7.0 and **none moved** — no
existing citation goes stale. The second digit moves for new capability: a
`quality_axis` table, an Israeli head-count measure, and a version-bump
checker wired into CI.

### The web UI is a statistical bulletin now, and it comes in slate

The restyle: paper ground, ink numerals, and one accent — the violet of USDA
inspection-stamp ink. Evidence grades render as stamps, and an estimate is
dashed and hatched, so an unsourced figure is visibly different from a sourced
one everywhere it appears. Dark mode is the same bulletin printed on slate:
theme follows the system, a header toggle stores an explicit choice, and every
colour — UI and charts — is defined once, so the toggle re-colours the charts
too.

**Each species now gets its own size question.** "Is a fatter chicken a better
chicken?" was asked of the whole corpus and answered from a verdict hardcoded
in `api.py`. A laying hen is graded on egg size and saffron on ISO colouring
strength, so the question, its axis, and the three-part verdict now live in a
`quality_axis` row per species — the new table that makes this release a
second-digit bump. A null verdict leg renders as an open question in estimate
ink, not as a no.

`tests/test_static.py` is the first coverage the web UI has ever had, and it
immediately caught a live bug: the page still printed hardcoded wing prose —
"the instant the wings leave the bird", a cut-up line — to anyone asking about
eggs. `/api/calculate` now returns `supply_chain.floor_note` and the page
renders it. Also fixed: the floor..ceiling band no longer shows "floor 0.03
hens" above prose that rounds the same number to "at least 1 hen".

### Israel gets a head count after all — in placements, not slaughter

CBS publishes no poultry head-slaughtered series, and that held. But the
quarterly series publishes **chick placements**: heavy breeds, 275,427.9
thousand head for 2024 and 262,848.753 thousand for 2023. Loaded as its own
measure, `chicks_placed`, in CBS's own thousands — placements differ from
slaughter by farm mortality, and substituting one for the other is exactly the
conflation this corpus exists to prevent. This retires the unverified "~260
million broilers a year" trade-press figure: it was essentially the 2023
placement number, and it now has a government citation instead of a 404ing
article.

The open tonnage-basis question gained evidence, not an answer: USDA PSD's
ready-to-cook figure against CBS's 2000 output is 72.2%, dressing-yield-shaped
against the project's own derived 75.67%. Recorded as a conflict on the source,
per `docs/research/README.md` — promoting it to a stated basis is a human
judgement about provenance.

### The version bump is checked, not remembered

`tools/release_check.py` builds the corpus at the base ref and at the working
tree, then reports the smallest bump the diff justifies: a new table or kind
demands the second digit, more rows of an existing kind the third, and **every
active product's published answer is compared** — a corpus that gains products
gains coverage with no list to maintain. An answer that moves emits a warning
naming the product and old → new values; a better loss factor *should* move
the number, it just must not move silently.

CI runs it advisory on pull requests — against the PR's own base, so the
signal is that branch's contribution alone — and enforcing at tag push,
against the previous tag. It fails only on under-bumping: a floor on the
required bump, never a ceiling. Honest about its blind spot, learned by
pointing it at the actual saffron-ceiling commit: an API-only regression is
invisible to a check that runs the CLI. That claim was wrong in the docs and
is now corrected.

### The third digit is a minor, not a patch

Versioning is now **MAJOR.MINOR.MINOR** and no longer claims to be SemVer. The
thresholds are unchanged from the capability-not-volume rule — second digit for
a new *kind* of thing, third for more of what we already had — but SemVer's
third component means "fixes only, no new capability", and ours routinely ships
thousands of rows of corpus data. Naming it PATCH was a promise the project
does not keep.

Nothing about the numbers changes shape: three components, `v`-prefixed tags,
same CI gate, and v1.0.0 through v1.7.0 stand as tagged. `release_check.py`
still prints `MINOR` / `PATCH` for *second* / *third* — same thresholds, older
vocabulary, retermed separately.

### Three new "how many X" subjects, scouted and ready to run

Ground beef, maple syrup, and silk are drafted as research work-orders under
`docs/research/batches/` (06, 07, 08). Every candidate URL has been fetched,
confirmed 200, and pinned to the verbatim sentence that carries its figure — so
the quote-gate has a real target before COOPER ever runs. Nothing is in `data/`
yet: these are specs, not corpus, so the version does not move until COOPER runs
them and a human accepts. The batches were the surviving third of a larger idea
(saffron already shipped; honey and milk were already drafted as 04 and 05).

Each was chosen to exercise something the poultry corpus does not:

- **Ground beef** is the mixing model with **no anatomical floor** — the count is
  set by grinding, not biology, so it is the purest test of pooling standing
  alone. The floor is 1 (ground at home by hand); a documented contamination
  traceback puts one patty's trimmings at **four separate sources** (Nebraska,
  Texas, Uruguay, and a South Dakota trim plant).
- **Maple syrup** stacks a concentration ratio (~40 gal sap to 1 gal syrup, by
  the Jones Rule of 86) on a `recurring` per-tap rate over a **~6-week season** —
  a shorter period than eggs' year, and a test that the period is data rather
  than a hardcoded assumption.
- **Silk** adds a **garment-level** product (tie, shirt, dress) on a
  one-cocoon-per-worm constant, with a small honest reeling step (~5 cocoons per
  thread) that is real mixing but does not dominate the count.

Honest about grade: none rises above `industry`. Ground beef's headline "100+
cattle" is a corporate statement, the per-garment silk counts are craft-site
lore, and the sourced silk filament (**300–900 m**) is deliberately the cited
figure over the higher number that circulates. Said here so that proximity to
the NASS-backed poultry rows lends them no credibility they have not earned.

### Three of those batches ran. One was accepted; the negatives were kept.

**Maple was accepted**: 5 figures, with the 40:1 sap-to-syrup ratio at 2/2
model consensus and the other four flagged `needs_human` rather than averaged.
`season_length` came back with a quote and no number, which is right — the
source gives calendar windows, not a duration, and subtracting them would be
our arithmetic rather than the source's. Findings live in
`docs/research/accepted/`, not `data/`: promotion is a human call, so nothing
here moves the version.

**Ground beef and silk both failed verification, and the runs were worth more
as bug reports than the figures would have been.** Silk's best row — reeling,
2/2 consensus — was rejected because `fetch_url()` never decoded HTML
entities, so a model that read the prose correctly produced a quote that could
never match the inbox: manufactured false guilt that reads exactly like an
invented citation. Ground beef stored the hedged ceiling "more than 100
cattle" as lo=mode=hi=100 and verified a lab's test-patty mold size as a
market standard. And an egg-breakage run named a new failure class the gate
cannot see: a **pie-chart label** — verbatim quote, right document, right
words — that is a share of calorie loss, not a loss rate, wrong by a factor of
twenty with every check passing. A figure whose basis cannot be read off its
own quote is not usable however well it verifies.

### The research pipeline earned four fixes from those failures

- **Colliding filenames silently deleted fetched documents.** Three govinfo
  URLs shared their first 47 characters and the filename was `slug[:48]`, so
  two documents were downloaded, logged as "fetched + extracted", and
  overwritten by the third — a 693 KB CFR text never reached the extractor and
  the run's "0 of 8 figures" read as source scarcity. Fixed with a URL-hash
  suffix and a regression test.
- **HTML entities are now decoded** before the inbox is written, per above.
- **The extractor finally sees the trap the spec named.** Every spec item
  carries a "Watch for" paragraph, and `parse_spec` used to throw it away.
  Measured on ground beef after the fix: the flattened "more than 100" ceiling
  became `null/100/null`, and the mold-size figure withdrew. Three figures
  became two — precision bought with recall, the right trade for a corpus
  whose value is that every number traces to a source.
- **Verification runs on Windows now**: explicit UTF-8 in `build.py`, and a
  temp-dir teardown failure no longer discards an audit verdict already
  correctly arrived at.

### Licensed: MIT for code, CC BY 4.0 for the words and the data

The code is MIT. `docs/` and `data/` are CC BY 4.0 — attribution is the one
condition, which is fitting for a corpus whose entire point is citation.

### Housekeeping

`.ccwork` is committed, so a fresh worktree comes up with its venv built and a
port assigned instead of being rebuilt by hand.

## v1.7.0 — 2026-07-30
Seasonality. The corpus has held twelve months of live weight for every state
NASS names since the state work landed, and only the annual average was ever
surfaced — the roadmap called it the cheapest unexploited data in the project.
It is now exploited, and the answer is more interesting than "chickens are
heavier in winter".

### No state is seasonal. The states agree on the season anyway.

Broiler live weight moves **2.7% across the year nationally**, 6.55 lb in March
to 6.73 lb in September. Judged on its own that swing cannot be told apart from
twelve noisy numbers — and neither can any of the 22 states' individually.

Then stop looking at one series and look across them. **13 of 22 states peak in
August–October**, where about 5.5 would be expected if the peak month were
random (p=0.0084 after correcting for having chosen the window from the data),
and 12 trough in February–April. Agreement between series that were surveyed
separately is a different and stronger kind of evidence than the size of any one
series' range, and it is the same instinct as `tests/test_cross_validation.py`.

Both results ship, and the weaker one is not dressed up as the stronger. A test
asserts both halves, so a NASS revision breaks it.

### Three ways to be wrong about a season, two of them found the hard way

A range over twelve numbers is trivial to compute and thoroughly misleading, so
the classifier applies three tests and a region must pass all of them:

| Test | Catches | Clean cycle scores | The failure scores |
|---|---|---|---|
| Swing ÷ month-to-month jitter | random noise | 6.0× | 3.0× |
| Swing surviving 3-month smoothing | one odd month | 91% | 33% |
| Movement spent crossing Dec→Jan | a trend with a January reset | ≤13% | 50% |

The second and third tests exist because the first draft shipped without them:

- **Texas was published as the one seasonal state on the strength of one June.**
  A year that is flat for eleven months and dips once scores *exactly* the
  ideal-cycle score on swing ÷ jitter. It is now classified `spike`, and its
  entry says the swing is real and the pattern is not.
- **A series that climbs all year and resets in January passes the first two
  tests.** Broiler weight does trend — about 1% a year — and a trend read as a
  season puts the peak in whichever month the year happens to end on.

Kentucky's 12.3% swing, the largest of any serious broiler state, is one August:
53% of it survives smoothing. Alabama's 3.6% is spread across the year and keeps
82%. **Shape beats range**, which is why the table sorts by verdict and not by
swing — sorting by size puts the least trustworthy states first.

These thresholds are **ours, not a source's**. Nothing in NASS says a swing must
clear 4.0× to be a season, so the classification is graded `estimate` even
though the weights it reads are `measured`, and the synthetic series whose right
answer is known by construction are tested alongside the corpus.

### The Super Bowl does not show up in the birds

February is the **third-lightest month** of the national year, five months off
the September peak. That is a lead time, not a mystery: a bird slaughtered in
early February was placed as a chick before Christmas. Whatever absorbs the
demand spike — frozen inventory, imports, grade mix — is not bird size, and none
of those three series is in the corpus, so the page says the weight does not
move and declines to say what does.

### Seasonality is deliberately NOT wired into the count

`affects_count: false`, stated in the payload rather than left in a comment.
Monthly condemnation and dead-on-arrival rates would be the count-affecting
ones and the corpus holds annual figures only; monthly head slaughtered is not
loaded either. A chicken has two wings in every month of the year.

### Added

- `seasonality.py` — `analyse`, `concordance`, `smooth`, `sparkline`. No
  database dependency, like `model.py`.
- `GET /api/seasonality` — national and per-state series, verdicts with their
  reasoning, both concordance tests with caveats, citations, and
  `not_modelled`. The verdict prose is generated from the rows; the hardcoded
  first draft claimed no state was seasonal while reporting one that was.
- `wings seasonality` — the whole year per state as a block sparkline, which is
  what makes the recurring autumn peak visible at a glance.
- A **Seasons** tab: the national line beside a peak-month histogram against
  what chance would give. The line alone understates the finding; the histogram
  alone overstates it.
- Three facts, and 21 tests including regressions for Texas and for the summary
  outrunning its own data.
- `db.monthly_size_series()`, reading the per-species view — the shared table
  holds broiler pounds and layer eggs-per-year in one column, and the existing
  convention test caught the first version doing it wrong.

### Not changed

No figure any previous release published moves. Nothing here touches the
calculator: this release adds a view of data already in the corpus, and the
count for a dozen wings is what it was in v1.6.0.

## v1.6.0 — 2026-07-30
Israel's head count stops being a single-source figure.

### Two figures promoted, from a document COOPER downloaded and could not read

The growers' organisation summary for 2021 carries a sector table that the
batch-05 extraction missed entirely and a human found by reading the returned
artifact. Both figures are now in the corpus at `industry` grade, from a new
`trade_body` source:

- **604 broiler growers** (2021), against the Times of Israel's "about 600 large
  chicken farms" from the Poultry Breeders Association. Two industry bodies, two
  publications, one number.
- **244 million chicks placed** (2021), against 260 million birds a year
  reported for 2025 by the other body — a ~6% gap over four years, which is
  roughly what growth looks like.

**Chicks placed is NOT birds slaughtered**, and it has its own measure for that
reason: grow-out mortality sits between the two, and the model already carries a
factor for it, so merging them would overstate throughput and then double-count
the mortality downstream. A test asserts the two measures stay distinct.

**The corroboration itself is now tested**, not just asserted in a note: the
chick and head figures must stay within 25% of each other and the grower count
within 550–650. If a future edit breaks the agreement that justified promoting
these, the suite says so rather than the claim quietly becoming false.

The learning-centre fact "Nobody officially counts Israel's chickens" now
carries both checks; it previously described only the kg-per-bird one.

### Hebrew questions work, and that was the experiment

`batch-05b` re-ran six of the same documents with the questions rewritten in
Hebrew. English questions had returned **0 figures from 12 calls**; Hebrew
questions returned **2 from 12**, both with quotes matching the source
character-for-character, both through `verify` with the audit clean — and they
were the same two figures the human read had found, which is what makes it a
reproduction rather than an anecdote.

**The retrieval detail makes the result stronger, not weaker.** The embedder was
unavailable for that run, so it fell back to keyword overlap: English question
with real embeddings scored 0, Hebrew question with crude keyword matching
scored 2. Matching the question's language to the document's is what mattered,
so **a multilingual embedder is no longer the diagnosis** and should not be
built on this evidence.

Written up in `docs/research/accepted/batch-05b-israel-hebrew-questions-REVIEW.md`.

### COOPER could not print Hebrew, and it cost a completed run

`runner.py` now reconfigures stdout and stderr to UTF-8 at startup. COOPER is
Windows, its console is cp1252, and any non-Latin character reaching stdout
killed the run — **after** the work was done, which is the worst possible place.
The first Hebrew-question batch extracted two figures and then died printing the
item's name, taking `findings.yaml` with it.

## v1.5.0 — 2026-07-30

The Israeli data gets a page, and the reader chooses how much of it to believe.

### The evidence toggle, on the "By country" view

The view itself arrived in a concurrent commit; this adds the choice it was
missing. Two radio buttons — **All evidence** and **Government figures only** —
re-query `/api/output/{iso3}` with `min_confidence` and re-render:

| | Birds/year | Implied average bird |
|---|---|---|
| All evidence | 260M `industry` | 2.31 kg `industry` |
| Government figures only | — | — |

Under the filter both cards disappear, because the figure they rest on does, and
the page names what it dropped: *"Hidden by this filter: Birds slaughtered per
year (industry, toi-poultry-imports-2025)."* A filtered answer that does not say
what it filtered is just a different number.

The choice **survives a country change** rather than resetting: a reader who
asked for government figures only should not have that quietly undone by
clicking a different country.

### region_level, so counting regions does not double-count

Israel nests 50 regional councils inside 4 districts inside a grand total.
Counting every row as a "region" claimed **55 Israeli regions against 23 US
states** — more granularity than exists. `output_stat_year.region_level` records
the publisher's hierarchy as a column rather than as a prefix inside a prose
note; the coverage count reads leaves only (50), the district cross-check reads
the column instead of matching a string, and a test pins the level counts.

### Batch 05 ran, and returned nothing — which is the finding

Three items, ten Hebrew documents, two models, twelve extraction calls, **zero
figures**. The fetch worked (including a 40-page State Comptroller PDF) and the
Hebrew survived chunking intact, so the failure is retrieval and extraction:
English questions scored against Hebrew chunks with an English-centric embedder.

A human read of the same returned artifacts found figures in minutes — the
second time the artifacts have been worth more than the extraction. Written up
in `docs/research/accepted/batch-05-israel-hebrew-REVIEW.md`, with **604 broiler
growers** and **244 million chicks placed (2021)** proposed for promotion. The
chick figure corroborates the 260-million head count from a second industry body
four years earlier, and the review is explicit that chicks placed must not be
loaded as birds slaughtered.

Nothing from the batch is in `data/`. The verify gate exists precisely so a zero
is allowed to be a zero.

## v1.4.0 — 2026-07-29

Israel gets the sources CBS is not, and the reader gets to choose how much to
believe.

### Both readings of Israel, and neither is hidden

CBS answers scale and nothing else, so with government data alone Israel cannot
answer "how many chickens" at all. A named industry official — Moti Elkabetz,
secretary of the Poultry Breeders Association, in the Times of Israel — puts
throughput at **260 million broilers a year**. That figure is loaded at
`industry` grade, and the government-only picture stays reachable rather than
being overwritten:

```
GET /api/output/ISR                          260 million birds, industry grade
GET /api/output/ISR?min_confidence=measured  no bird count, and it says which
                                             row it dropped and why
```

`output_stat_year` gained a `confidence` column to make that possible. The table
stopped being government-only the day this row arrived, and "government figures
only" is now a WHERE clause instead of a promise in a comment. `/api/countries`
reports `head_slaughtered_grade` and `head_slaughtered_measured` alongside the
boolean, so a caller cannot render "we have a bird count" without also knowing
who counted.

### The cross-check that makes it believable

600,072 tonnes (CBS, measured) over 260 million birds (industry) is **2.31 kg a
bird** — what a 40-day broiler weighs. Two sources that were not derived from
each other, agreeing.

It is a view, `v_output_derived_weight`, never a stored row, so it cannot drift
from its parents. Its confidence is the **weaker** parent's, never the better
one, and it reports `year_gap` because the years genuinely do not line up: CBS
has no 2025 output figure and the interview named no year. A same-year pairing
would have been tidier and would have required pretending otherwise.

### A hole in the government data, now explained

CBS output for 2023 is **553,068 tonnes — below its own 2020 figure** and 8%
below 2024. Poultry World reports 16 million head lost to Newcastle disease
outbreaks in Q4 2023, wartime closures in the north and south, and a labour
shortage that pushed slaughterhouses to a six-day week. The standing flock
agrees: 34,121 thousand at end-2023 against 38,239 thousand at end-2020.

The dip was already in the corpus. The explanation came from a trade
publication. Neither meant much alone, and a test asserts the fact's prose still
matches the rows it describes.

### Six Israeli facts, including the demo hook

- **Chicken wings are on the Yom Ha'atzmaut grill**, alongside pargiyot, with
  falafel and shawarma barely featuring. The project's exact product is part of
  an Israeli national holiday.
- **"Pargiyot" means "baby chickens"** and no longer does — the same name drift
  that makes "a dozen wings" ambiguous.
- An Israeli chicken goes from **NIS 6.5/kg at the farm to ~NIS 20/kg at
  retail**.
- **Nobody officially counts Israel's chickens**, and the fact says so.
- **Kosher bedikah has no FSIS analogue** — and no published rejection rate, so
  it is described and deliberately not quantified.

### What is deliberately still absent

No per-capita figure. Three reachable sources give three "world's highest"
numbers — 58.2, 64.9 and 70.83 kg — a 20% spread that is almost certainly
definition drift, so `population` stays NULL and a test fails if any of those
numbers appears in a fact. `batch-05-israel-hebrew.md` is written to resolve it
from a primary series, and says not to ship one otherwise.

Also recorded as reachable-but-unused: the Ministry of Agriculture (403 to every
fetcher, an Akamai filter rather than a missing page) and the plant market shares
in Poultry World, which are third-hand.

## v1.3.0 — 2026-07-29

Israel becomes the second country with data, and the README stops claiming the
corpus is better sourced than it is.

### Israeli broiler figures, and the one they do not include

Three tables from the CBS Statistical Abstract 2025, chapter 21, cited and
audited like everything else:

- **Output** — 600,072 tonnes of broiler output for 2024 (CBS-provisional),
  with a series back to 2000, and value in NIS millions.
- **Inventory** — 37,895 thousand broilers at end of 2024, a series back to
  1960. This is a **standing flock, not annual throughput**; broilers turn over
  several times a year, so reading it as slaughter understates the answer
  several times over. Stored as `measure='inventory_eoy'` so the distinction is
  in the data rather than only in a comment.
- **Districts** — broiler marketing for 47 districts and regional councils,
  8 of them suppressed by CBS and loaded as presence without volume.

**Head slaughtered per year does not exist in any of them**, and it is the
denominator the count question needs. So Israel can answer scale and cannot
answer "how many chickens" from Israeli sources. Deriving it would need an
Israeli average bird weight, which CBS also does not publish; borrowing the US
6.62 lb would make an American assumption look like an Israeli measurement.
A test asserts no Israeli head figure exists, so nothing can quietly fill it.

Per-capita consumption is still unclaimable: the article behind the "Israel is
the world's highest per-capita chicken consumer" headline now returns 404, so
`country.population` stays NULL and `/api/countries` reports
`per_capita: false` rather than rendering a claim with no reachable source.

### New table, because the US-shaped ones would have lied

`output_stat_year` stores the measure and the unit as data instead of implying
them in column names. The alternatives were mapping CBS tonnage onto
`certified_rtc_lb` — asserting that "agricultural output" means ready-to-cook
weight, which the publication never says — or converting shekels with an
exchange rate we would have to source. Israeli rows keep tonnes, shekels and
thousands of head; a test fails if a pound or a dollar ever appears on one.

### A cross-check that fails, on purpose

District marketing sums to 571,500 tonnes against 600,072 tonnes of output, a
gap of **4.76%**. Marketing excludes self-consumption and private sale by CBS's
own footnote, so the gap is probably real — but a reader who adds up the
districts will find it, and finding it unannounced reads as our error. Both the
gap and its explanation are asserted by tests.

### New endpoints

- `GET /api/countries` — what each country can actually answer, not just its
  name. A selector built from names alone would imply a parity that does not
  exist between enumerated US head counts and Israeli tonnage.
- `GET /api/output/{iso3}` — output, value and inventory in native units, with
  suppressed regions flagged rather than zeroed.

### README figures are generated

"Honesty about the data" had drifted three times while hand-maintained, most
recently claiming **7 of 12** loss factors were unsourced estimates when the
true figure was **11 of 21** — an error in the direction that overstates the data's
quality. `audit --stats` now emits that block, `tools/update_readme.py` writes
it, and CI fails if a data change skipped the regeneration. The test count is no
longer quoted: it is not a fact about the data and it moved on every commit.

The Scope section was three subjects out of date and now documents all three
yield modes — countable, recurring, continuous.

## v1.2.0 — 2026-07-29

Eggs get their own supply chain. **This is a correctness fix**: v1.1.0 shipped
eggs with the right number and the wrong explanation.

### The bug

Eggs had zero mixing stages and zero supply chains, and
`default_supply_chain()` took no product argument — so an egg query resolved to
the single global default, which was the **wing** chain, and walked eight
stages that do not exist for an egg:

```
cut-up line → wing chiller → size grading → combo bin
  → IQF freezer → case pack → distributor → fryer basket
```

The *count* was right (12 hens), because a hen's one-egg-a-day ceiling
dominates and any large pool yields twelve. But the reasoning panel told anyone
asking about a carton that "the cut-up line a chicken's two wings drop onto the
same conveyor and part company, then size grading actively splits any pair."

For a project whose entire claim is that every number is traceable, a confident
and detailed explanation of the wrong animal is the worst defect available.

### What changed

- **Egg mixing cascade** — nest and belt collection, on-farm cooler, washing,
  candling and grading, carton pack, distributor, retail case, your fridge.
- **Three egg routes** — `commercial_carton` (default), `farmers_market`,
  `backyard_eggs`. Only the backyard route can reach the floor of one hen.
- **Egg grading is `random`, not `separating`.** Weighing wings splits a bird's
  pair because a bird has exactly two. Each egg is already a lone contribution,
  so there is no pair for grading to break; calling it separating would invent
  a mechanism.
- **Supply chains are scoped to a species**, and `species_slug` is now
  **required** on `default_supply_chain()`. A species-less default is not a
  meaningful thing to ask for, and its being answerable is exactly how this
  happened. There is deliberately no cross-species fallback — returning
  another animal's route fails silently, which is worse than failing.
- **The floor explanation moved into data** as `supply_chain.floor_note`. It
  was hardcoded wing prose in both `cli.py` and `static/index.html`, so fixing
  the data alone would not have fixed the output. Per `CLAUDE.md`, a figure or
  claim hardcoded in a module is a bug.

### Also fixed

`resolve_pool()` clamped the lower bound to `container / upi` without capping
it at the container size. For wings (`upi ≥ 1`) that is always safe. For eggs
over a single day (`upi = 0.789`) it reported a 12-egg carton as "representing
roughly 15 individuals" — more contributors than units, which cannot happen.
The count was unaffected because the caller re-clamped, but the audit trail
printed the impossible figure.

### Channel-aware loss stages

A second instance of the same defect, one level down. `supply_chain` selected
which **mixing** stages applied but had no say over **losses**, so every route
got every stage. `retail_shrink` was therefore parked `optional`/default-off
purely to stop it double-counting against `kitchen_loss` — a workaround
standing in for a model, and the grocery path could not be expressed at all.

Routes now declare their own losses via `supply_chain_loss_stage`, and a new
`grocery_retail` chain demonstrates it:

| Route | `kitchen_loss` | `retail_shrink` |
|---|---|---|
| `commodity_foodservice` | yes | no |
| `grocery_retail` | no | **yes** |

A wing does not pass both a supermarket meat counter and a restaurant kitchen,
and no route may now claim both — asserted by a test over every chain. A chain
that declares nothing still gets the species defaults, so existing routes are
untouched.

### Egg grading is documented, not just decided

Modelling egg grading as ordinary mixing rather than active separation is a
judgement about mechanism, not a sourced figure, so it is now stated where
readers can find it: the stage description, and a learning-centre fact. A bird
has two wings and weighing them pulls the pair apart; an egg reaches the grader
already alone, so there is no pair to break.

### Unchanged

Wings still answer 6 → 11.99997, and still explain themselves via the cut-up
line. 261 tests pass.

## v1.1.0 — 2026-07-29

Eggs become a first-class product rather than a proof that the schema
generalises. Per [docs/VERSIONING.md](docs/VERSIONING.md) data additions are
MINOR, so this is a MINOR release.

### The recurring-yield window

`model.py` had `RecurringYield` and `recurring_floor` and nothing called them,
so `wings 12 --product table_egg` reported a floor of **0.042 hens** — the
annual rate applied to a same-day question — while the distinct count on the
same screen said 12. The two contradicted each other by 285x.

The window is now plumbed through `run()`, `db`, the CLI (`--window-days`) and
the API (`window_days`), defaulting to one day:

| Window | Hard floor | Expected | Distinct |
|---|---|---|---|
| 1 day | **12 hens** | 15.2 | 12 |
| 15 days | 1 hen | 1.01 | ~12 |

Both floors are reported, because either alone misleads: 12 is physiology,
15.2 is what you need since hens do not lay daily.

**Eggs invert the wing story.** Wings have a floor of 6 that mixing pushes up
toward 12. Same-day eggs have a floor that *rises to meet* the ceiling at 12,
leaving the supply chain nothing to move.

### Eggs get their own loss chain

Almost nothing carried over — an egg is never slaughtered, cut up, or breaded.
Five new stages in `data/loss_chain_eggs.yaml`, built on USDA's own grading
distinction:

- **Check** — shell cracked, membranes intact. A *downgrade*: it leaves the
  shell-egg stream for the breaker plant and becomes liquid egg.
- **Leaker** — contents escaping. A true loss.

Plus in-transit breakage, kitchen breakage, and layer mortality (off by
default, like grow-out mortality). A dozen eggs now needs **16.1 hens** into
the system against a 15.2 floor.

Note the contrast with wings: frozen IQF wings are robust enough that no
citable transit figure exists, while eggs are fragile enough that the industry
measures breakage closely.

### Egg data

- **Nutrition** (FDC 171287): 143 kcal, 12.56 g protein, 9.51 g fat, 372 mg
  cholesterol per 100 g. Raw only — a wing has one dominant preparation, an
  egg has none, and asserting one would invent a default.
- **National totals**: 365.1M layers, 288 eggs each, 105.2B eggs (90.1B table).
  The corpus had 34 states but no US row.
- **Three new facts**, including the companion to the bird-flu figure: layers
  fell 3% and production 4%, while broilers lost ~0.05%. Same virus, same
  country — a broiler lives 47 days and a layer lives years.

### Also

- `data/<prefix>*.yaml` globbing now applies to `loss_chain` and `nutrition`,
  not just `taxonomy`, so a new product line stays a new file.
- Fixed `fmtDistinct` printing `12.000000` for same-day eggs, in Python and
  JS. Wings approach the ceiling and never arrive; eggs arrive, and six
  decimals implied the opposite.
- Fixed the GUI band running from the expected floor, so eggs showed
  "floor 15.21" against a ceiling of 12 — above its own scale.
- The calculator had **no product selector**, so eggs were unreachable from
  the web UI entirely. Added, with the window control shown only for
  recurring products.
- Scientific mode now defaults to **2,000** Monte Carlo iterations rather than
  20,000. This is a hosting concession, and it does move a published band, so:
  the draws are seeded, so both figures are reproducible rather than noisy, and
  at 12 wings the 90% interval goes from 6.7833–7.3957 to 6.7794–7.3930 — a
  shift in the third decimal, or 0.01 on the upper bound as displayed. Render's
  free tier runs the CPU-bound resample 11-13x slower than a laptop, which made
  the old default a 6-second wait on every visit to the tab and 30 seconds for
  anyone choosing 100,000. Both larger counts are still in the dropdown.

### Known gaps

- Layer mortality and kitchen breakage are unsourced estimates.
- Check and leaker rates are grading *tolerances*, which are ceilings a pack
  must stay under rather than measured rates, so they overstate real loss.
- No egg mixing cascade of its own; eggs reuse the broiler chains, which is
  wrong in detail — an egg carton is not a combo bin.


## v1.0.0 — 2026-07-29

First release. Answers "how many chickens does it take to make a dozen
chicken wings?" for US broilers, with every number traced to a source.

### The answer

For a dozen whole wings through a commodity foodservice chain:

| | |
|---|---|
| Hard floor | **6 chickens** — a chicken has exactly two wings |
| Distinct chickens on the plate | **11.99997** |
| Chickens required, all losses counted | **6.90** |

The floor is arithmetic. The 11.99997 is the interesting part: mixing starts
the instant the wings leave the bird, and size grading actively splits a
bird's two wings into different grade streams, so a dozen wings from a
commodity chain is very nearly a dozen different chickens. Six is only
reachable if you cut up six birds yourself.

### Two products, and one of them is a lie

- **Whole wing** — 2 per bird, anatomical constant. A dozen is 6 chickens.
- **Boneless wing** — contains **no wing meat**. It is breast, and Tyson's own
  ingredient statement reads "boneless, skinless chicken breast chunks with
  rib meat". A dozen takes about **0.35 of a chicken** — a seventeenfold
  difference from the same menu section.

"Wings" is a regulated term: USDA requires the entire wing, muscle and skin
intact, and requires the name to disclose removed bone. "Boneless wing"
complies. The problem is the name, not the meat.

### What ships

**Three questions, never conflated** — the anatomical floor, the individuals
required after walking the loss chain backwards, and the distinct individuals
actually represented in your portion.

**A 12-stage loss chain** with 14 factors, each carrying lo/mode/hi bands.
Stages are tagged by what they affect, and the model enforces it: cook loss
makes a wing lighter, not fractional, so it cannot move a count.

**A 9-stage mixing cascade** from the cut-up line to the fryer basket, with
`separating` stages modelled distinctly from `random` ones because grading
pulls pairs apart rather than merely shuffling them.

**Scientific mode** — Monte Carlo with a selectable confidence interval
(50–99%), a tornado chart showing which unsourced figure actually moves the
answer, and an evidence floor that recomputes using only figures at or above
a chosen grade. Using measured government data alone gives 6.03 chickens
required; including our estimates gives 6.90. That gap is a more honest
statement of uncertainty than any single error bar.

**"Is fatter better?"** — Ohio runs 4.6 lb birds, North Carolina 8.4 lb, a
1.83× spread that is market segment rather than biology. The verdict: better
for yield per bird, worse for quality per pound, and irrelevant to the wing
count. White striping affects 96% of fillets and worsens with live weight;
wings develop no equivalent myopathy at all.

**Nutrition and footprint**, mass-allocated. A dozen wings carries ~1.3 kg
CO₂e, not the 17.4 kg a naive six-birds multiplication gives — wings are ~7%
of the bird. The grower was paid about **12 cents** for the wings' share.

**Nine views** in the web GUI, a CLI with progressive-disclosure reasoning,
and `wings export` writing 25 self-describing .txt/.csv files.

### Data

| | |
|---|---|
| Sources | 31, every statistic cited |
| Facts | 34, surprise-ranked |
| States | 22 (NASS publishes only these individually) |
| Tables | 26 |
| Tests | 163 |

The build **fails** if any statistic cites a source that does not exist, and
a separate CI job audits citation coverage across all 15 data tables.

### Known limits, stated rather than hidden

- **8 of 14 loss factors are unsourced estimates**, 5 of which affect the
  count. Listed in `docs/RESEARCH.md` and surfaced by `wings`' own audit.
- **Only 22 states.** NASS reports broilers slaughtered in 40 but publishes
  22 individually; the rest are suppressed to avoid disclosing individual
  companies. This is a ceiling on the source, not a gap in the work.
- **No per-producer loss factors.** Line speed (175 vs 140 birds/min) and
  chilling method (a ~10 point mass swing) demonstrably differ between
  plants, but no one publishes per-plant damage rates.
- **HPAI is deliberately not modelled.** Broilers are ~8% of the 168.62M
  birds lost since 2022 — about 0.05% of annual throughput, inside the noise
  of every other factor. It is an egg story.
- **Mixing pool sizes are our estimates.** The qualitative conclusion is
  robust to them: the curve flattens above ~1,000 birds, so any
  commodity-scale pool lands within a hair of the ceiling.
- **Boneless wings have no nutrition row yet** — the view says so rather than
  showing a blank.

### Deployment

Live at https://counting-chicken-wings.onrender.com/

Render's free tier spins down when idle, so a first visit can wait ~20s for
a cold start. A `/healthz` endpoint exists to be pinged by an external cron;
that is the only real fix short of an always-on instance. Client-side
loading UI cannot help, because the stall happens on the HTML document before
any script runs.

Plotly is loaded from a CDN. If it is unreachable the charts degrade to a
message and every figure remains available in the tables and the API.
