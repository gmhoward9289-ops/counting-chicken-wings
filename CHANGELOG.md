# Changelog

## v1.12.3 — 2026-08-01
### The release job approves the run GitHub parks for it

v1.12.1 published only because a human approved a workflow run at the right
moment. `release.yml` opens its version PR with the default `GITHUB_TOKEN`, and
the file already documented that this raises no `pull_request` event — which is
true, and incomplete. GitHub still **creates** the `pull_request` run and parks
it at `action_required`. That parked run holds the four required contexts, so
the PR sat at `BLOCKED` while the dispatched run passed green beside it, and the
job waited out its deadline for a merge that could never happen.

The symptom is deliberately hard to read: `gh pr checks` reports *"no checks
reported on the branch"* while the check-runs API shows every check successful.

- **`approve_stalled_runs` in the wait loop** approves any `pull_request` run on
  the release branch sitting at `action_required`. Not a bypass — approving is
  what makes the required checks actually run, and they still have to pass.
- **It lives in the poll loop, not in a step after the dispatch**, because the
  parked run can appear after the dispatch returns, and `gh pr update-branch` in
  the `BEHIND` case creates a fresh one needing the same treatment.
- **It cannot abort a release.** Every failure path is guarded; a lookup or
  approval that fails warns and lets the loop carry on to its own deadline.
- The dispatch step's comment claimed the run is never created. Corrected in
  place rather than left to mislead the next reader.

Considered and rejected: loosening `fork-pr-contributor-approval` repo-wide.
It would work, but this repo is public and that setting also gates first-time
human contributors — a real cost to fix a bot problem.

## v1.12.2 — 2026-08-01
### Seasonality: fixed crash and restricted concordance to full-year data

Two defects in the seasonality module and its concordance test.

- **Crash when analyzing regions with no published months.** The `_classify()`
  function signature changed to include `wrap` and `months_present` arguments,
  but one call site (line 238, triggered when all 12 months are suppressed) was
  not updated. This was a two-character fix but the real defect is the missing
  test — the new test suite covers regions with exactly one published month, all
  identical months, and no published months.
- **Partial-year regions silently entered concordance tests with the wrong null
  hypothesis.** The concordance test's null is that each region's peak lands
  anywhere in a chosen three-month window (p=0.25, or 3/12). For a partial-year
  region publishing k months, the probability depends on which months survived
  suppression — ranging from 0 to 1 with no single scalar null — which is why
  excluding partial regions is correct rather than reweighting them. The fix
  changes no published figures: 2025 broiler monthly data contains **22 states,
  all 22 with a complete 12-month series, 0 partial.** Peak concordance
  p_corrected = 0.00841 ("strong agreement"), trough p_corrected = 0.03445
  ("agreement") — both unchanged. This is a guard against future corpora where
  NASS suppression may leave a state partial. The exclusion count appears on the
  API surface and is disclosed in caveats.

### The release now asks for its own deploy

`deploy.yml` triggers on `push` to master, and `release.yml` merges its version
PR with the default `GITHUB_TOKEN` — which raises no workflow-triggering event.
So the one push to master that lands a release is the one push that never
deploys. v1.12.1 merged at 23:41 and the newest Deploy run was still the human
push at 23:38; the site went on serving v1.12.0 with nothing red anywhere,
because no run existed to fail. Human pushes deploy fine, which is what made
this invisible for as long as it was.

- **`release.yml` dispatches `deploy.yml` on master after the merge.** The
  restriction is on the event *cascade*, not on the dispatch API — a
  `workflow_dispatch` made with `GITHUB_TOKEN` does start the target workflow.
  `actions: write` was already granted for the ci.yml dispatch.
- **On `master`, not on the tag**, because deploys track the branch and the tag
  may already be behind. Deploy's own "verify what is actually serving" step
  catches a wrong commit; its precondition was a run existing at all.
- **A failed dispatch warns rather than failing the release.** The tag is cut
  and the release published by that point, so retracting them to report an
  undeployed site would be worse than an annotation saying "released, not
  deployed" next to a one-click manual dispatch.

Considered and rejected: merging with a PAT or GitHub App token, which would
make the whole cascade work. It fixes more, and it puts a long-lived credential
with write access into a public repo's workflow for a problem one API call
solves.

## v1.12.1 — 2026-07-31
### The fetcher now says when it was handed a doorman

`scout` already refuses a bot wall it can see from either host, and `verify`
already fails a walled document that reaches the inbox. The fetcher itself
said nothing: in batch-05-milk it printed `fetched pmc-….txt (167 chars)` for
167 characters of reCAPTCHA and the run reported **zero** fetch failures while
having suffered one. That silently removed Gross 2023 (*Animal Frontiers*), the
strongest source in the batch, and made two spec items unanswerable.

- **`runner.fetch_url` checks body plausibility on every fetch**, HTML and
  extracted PDF alike, and prints `[WALLED]` naming the URL and the marker. The
  fetch phase then reports the walls together before any model is called, so a
  wall cannot scroll past under two hundred chunk messages.
- **The document is kept, not discarded.** The artifact is the evidence
  `verify` re-checks quotes against; deleting it would move the silence one
  layer down. A wall is a warning at fetch time and a failure at gate time,
  because the wall is per-request — COOPER got reCAPTCHA from PMC in batch-05
  and 82,331 characters of the same article in batch-06.
- **The marker list has exactly one home.** It moved into `tools/cooper/`, the
  only half of the pipeline that exists on COOPER, and `research_batch.py`
  imports it. A scout disagreeing with the runner about what counts as a
  document would be pre-flighting a fetcher it does not match.
- The certifi trust-store warning now fires at the first fetch rather than at
  import, so `verify` and `accept` — which never open a socket — stay quiet.

## v1.12.0 — 2026-07-31
### A gallon of syrup is not one tree — a correctness fix to shipped output

`wings count 1 --product maple_syrup_gallon` published a self-contradiction:

```
Gathered in a single day, 1 gallon took at least 194 trees.
At the real laying rate you would need about 193 trees to count on it.
The gallon on your plate came from about 1 different trees.
```

A floor of 194 above a ceiling of 1, plus a laying rate for a tree, plus a
"hard floor" over a figure that is two extension services disagreeing about sap
flow. Four defects in five lines, and every published maple figure moves.

- **Whether a unit is a blend is now read off the figures, not off the yield
  mode.** The rule is physical: if one individual's entire natural output is
  less than one whole unit, that unit must be several individuals blended. A
  tree makes about a quart of syrup a season, so a gallon is several trees, in
  exactly the way a gram of saffron is 150 flowers. The old condition asked
  `yield_mode == "continuous"`; maple is `recurring`, so its gallon was read as
  one tree's discrete part and the pooling formula collapsed it to 1.
- **The condition is derived inside `run()` and the three call sites no longer
  hold it.** `cli.py` and both API routes each carried their own copy, all three
  said the same wrong thing, and no test could see the disagreement because
  there was none — they were wrong in unison.
- **Default windows come from the product**, `default_window_days` falling back
  to the product's own season. A flat one-day default in `db.py` asked how many
  maples could be tapped, boiled and bottled between breakfast and supper.
  Eggs keep one day, and every egg figure is unchanged.
- **`recurring_floor` returns `None` where no per-day ceiling is recorded**,
  instead of returning the expected count under the hard floor's name. A hard
  floor claims that no supply-chain arrangement can beat it; an average yield
  cannot support that. Maple reports one floor now, and says it is a yield
  floor. `hard_floor` in `/api/calculate` is null for maple.
- **`rate_label` and `cap_note` join `floor_note` in the corpus.** "At the real
  laying rate" and "a hen lays at most one egg a day" were hardcoded in
  `cli.py` and both web pages, so a maple was narrated as a bird.
- **Found in passing and fixed:** the Monte Carlo pass had its own copy of the
  draw and skipped the aggregate re-expression, so `--iterations` and
  `/api/scientific` reported 12 flowers for 12 grams of saffron against a floor
  of 1,800. Shipped since saffron landed, unrelated to maple, same shape.

The invariant is now enforced across the whole corpus rather than for saffron
alone: `tests/test_aggregate_units.py` asserts floor ≤ distinct ≤ ceiling for
every product on every route, deterministic and resampled.

### The frontend A/B test is retired with no result

**No winner was measured, and none is claimed.** The A/A run that would have
established the noise floor never happened, and the two arms have since
diverged, so every number the experiment could report has nothing to be
compared against. A difference with no baseline is not a finding. This is the
project's own standard applied to its own instrumentation: an unsourced figure
does not ship.

**The surviving page was chosen on design merit, not on data.** Variant B is
kept. It is three files split by concern — `index.html` (530 lines),
`app.css` (408), `app.js` (1,316) — against variant A's single 2,116-line file
with its CSS and JS interleaved, and its readout treats the floor..ceiling band
as part of the answer rather than as decoration below it. That is an argument
about how the page is built and what it says, and it is the only kind of
argument available here.

What retiring it buys: `static/index.html` was the frozen control, so **no UI
work could touch the shipped page**, and a change of wording meant editing four
files to keep the arms comparable. Both constraints are gone.

Removed: `experiment.py`, `metrics.py`, `abcheck.py`, `static/ab.js`, the
`wings ab` and `wings ab-clean` subcommands, `GET /api/experiment`,
`POST /api/metrics`, `GET /api/metrics/summary`, and `WINGS_AB_SPLIT` /
`WINGS_AB_SECRET` from `render.yaml` and `compose.yml` (with the metrics volume
and the `/data` mount point in the Dockerfile, now that nothing writes state).
`static/v2/` is promoted to `static/`.

`GET /` sends one file. No token substitution, no `ccw_sid` / `ccw_ui` cookies,
and no `Vary: Cookie` — that header existed because two pages shared one URL.

`test_static.py` keeps every structural invariant and now runs them once
instead of per arm; its fixtures still follow `/static/` links, so a rule that
lives in `app.css` is still checked. Only the two A/B-specific tests are gone —
the token placeholder and the shared-instrument check — along with
`test_experiment.py` and `test_abcheck.py`, 60 tests in all. The suite is
green.

No collected event data was deleted. There is none in the repo; any
`metrics.db` on the deployed host is untouched, and its Docker volume is now
simply unreferenced rather than removed.

### A walled fetch now fails where the document arrives, not only in pre-flight

batch-05-milk lost its best source to a reCAPTCHA page served to COOPER with an
HTTP 200 and 167 characters, logged as a successful fetch of a 41,579-character
journal article. The scout's docstring claimed reachability was a property of
the fetcher rather than the host, "so this is faithful from either machine".
That sentence is gone; it was measured and it is false.

**The primary defence is `document_is_a_wall`, applied by `verify` to the
documents that actually arrived**, and printed by `fetch` as they land. A body
under 1,500 characters carrying reCAPTCHA, Cloudflare or "enable JavaScript"
wording is an interstitial and fails the row, naming the wall rather than
blaming the model for a quote that could never have matched. `fetch` reports
the same list because a walled document usually explains an item that returned
*nothing*, and a row that returned nothing never reaches the gate — batch-05
read as "the models declined" when one of them had been handed a doorman.

It is deliberately not a pre-flight check, because a pre-flight check cannot
hold. **The wall is per-request, not per-host:** batch-06 fetched that same PMC
URL from COOPER and got 82,331 characters of the real article, hours after
batch-05 got 167 characters of reCAPTCHA from the same machine with the same
fetcher. Anything promising a clean run from a clean pre-flight would be the
same kind of claim as the sentence deleted above.

`scout` does now fetch every URL on COOPER as well as here, through the same
`runner.fetch_once` the run uses, and fails a URL whose remote body falls under
a quarter of the local one. It is documented as a **smoke test for a persistent
wall, not a guarantee** — one sample of an intermittent behaviour. The
threshold is loose because the evidence is: eleven of twelve measured
cross-host pairs agreed exactly or within five characters, and the one wall
collapsed to 0.4%. Characters, not bytes — COOPER writes CRLF, so a byte
comparison flags every document. `scout` exits `2` when COOPER cannot be
reached and says the remote half did not run; it is deliberately not `0`,
because batch-05 was cleared to send by a Mac-only scout that printed "Safe to
send".

None of this replaces the verbatim quote check, and the docstring now says why.
A bot wall is short; batch-08's JS-truncated page was 7,195 characters on both
hosts, ending mid-word at "The average wor" with the cited figure absent —
identical everywhere, invisible to any host comparison, and caught only by
looking for the quote.

Two new `[needs_human]` warnings for a figure whose basis cannot be read off
its own quote, which has now cost three batches. A **bare table row** — at
least two numbers against no more than two words, or numbers with no words at
all: `"Eggs, 5.1, 1.3%"` (batch-09, a share of total food-loss calories read as
an egg loss rate, wrong by ~20×), `"Fluid milk 109 13 12 22 20 35 32"`
(batch-05, severed from its header) and `"150 -185"` (batch-06). And a quote
that is **not a sentence**: `quote_looks_truncated` tested only the final
character, so `"(60 pounds versus 2,000 pounds)"` read as complete because it
ended in a bracket. Closers are now stripped before the sentence underneath is
judged, and a quote that is entirely a parenthetical aside is flagged on its
own account.

### batch-05-milk: a negative result, and the scout's promise disproved

Milk ran on COOPER and `verify` failed. Nothing was promoted; the review record
is `docs/research/accepted/batch-05-milk-REVIEW.md`. Four rows came back across
seven items, one failed the gate on a non-numeric value, and all three that
passed are unusable — an annual per-herd figure from a fictional worked example
stored in a per-day field, a Guinness record aimed at `max_units_per_day`, and a
loss table row stripped of the header that said which column was retail and
which was consumer.

The finding worth carrying forward is about the pipeline, not the dairy. `scout`
claims in its docstring that reachability "is a property of the fetcher and its
user agent, not of the host running it, so this is faithful from either machine".
It is not. Scouted from the Mac, PMC returned 41,579 characters of Gross 2023;
fetched from COOPER minutes later, the same URL returned 167 characters of
reCAPTCHA interstitial, logged as a successful fetch. Bot-walling keys on address
and reputation, which the host owns and the fetcher does not. Six of the seven
HTML fetches matched between the two machines to within five characters, so this
is one host-dependent source rather than general flakiness — and it was the
source the spec called the strongest in the batch, carrying the one sentence that
declines to define a maximum daily yield. Its absence left the record standing
without the counterweight that existed to stop it being read as a ceiling.

Also the second batch running to ground on a figure whose basis cannot be read
off its own quote — `"Fluid milk 109 13 12 22 20 35 32"`, after batch-09's
`"Eggs, 5.1, 1.3%"`. Both verbatim, both from the right document, both
meaningless without the header. On two instances that rule should stop being
advice in a spec and become a check.

### Ground beef: the subject with no anatomical floor

A third domain, `livestock`, and the first product this project has ever
described that hands the model **no floor at all**. A chicken has two wings, a
crocus flower has three stigmas; a hamburger patty has nothing. One animal can
supply the whole patty, so the floor is 1, and every number above it is
industrial commingling and nothing else. `is_anatomical_constant: 0`, and that
is the point rather than a gap.

- **The first mixing pool in this corpus that anybody measured.** Every other
  cascade — poultry, eggs, saffron, maple — cites `project-estimate-mixing`,
  because pool size is not something those trades measure. Hu et al. (*PLoS ONE*,
  2012) profiled DNA markers in six commercial grind batches and counted **411
  to 1,367 distinct animals** in them. That is the strongest evidence the model
  has that commingling describes something real, and it is the one mixing stage
  in the project resting on a study rather than on our own reasoning. A test
  pins it, because a silent revert to `estimate` would lose exactly that.
- **The engine's limit, stated rather than papered over.** Ask for one patty and
  the answer is about one animal, and that is honest: the pooling formula counts
  distinct individuals among N *draws*, and a patty is not draws — it is a
  sample of a homogenate. The count of cattle in it is the number of
  distinguishable parcels of trim it happens to contain, which nobody publishes.
  Inventing that number would make the headline figure as large as we liked. The
  evidence bounds the **batch**, so the batch is where it is recorded.
- `home_ground_beef` is the `whole_bird_home` analogue: no mixing stages at all,
  and the one route where the answer is the floor.
- Two mass-only loss stages, dressing (60–64%) and carcass-to-packaged (65–75%),
  neither of which can move a head count — the same guard written so that frying
  could not change a chicken count, now holding on a slaughter floor with no code
  change.
- A conflict recorded rather than resolved: MSU Extension's take-home yield is
  given two ways in one sentence and the two do not reconcile with each other.
  SDSU's does. Both bounds kept, neither averaged away.

### batch-06-ground-beef passes on the second attempt

The first run failed `verify` with nothing accepted. Two of its three failures
could not be fixed by trying harder, and the fixes are worth naming:

- An item whose answer had to be **counted out of prose** was deleted, not
  reworded. The gate was right to refuse it and no warning makes it extractable.
- A row that took a **laboratory patty-mould size** (112 g, one gram from the
  real quarter-pound) was fixed by removing that document from the batch
  entirely — `runner.run()` pools chunks across every document, so a document
  cited by one item is reachable by all of them.
- A hedged ceiling stored as a point value was fixed by **renaming the field to
  what the sentence supports**. A field name travels with the row into the
  corpus; a `Watch for` does not, and this was the second time one failed to
  stop the thing it named.

`fsis.usda.gov` still 403s the fetcher site-wide, and the lot/commingling
figures were found anyway — in the National Academies' 2002 *review* of the FSIS
draft risk assessment, which quotes the definitions at length and hosts
somewhere reachable. **When an agency document is unfetchable, look for the body
that reviewed it.**

Three quotes were corrected by hand and the values left untouched: one true
quote that failed the gate on tidied punctuation, and two that passed the gate
while being unreviewable — a bare parenthetical and a bare numeric span. Short
and verbatim is not the same as checkable.
### Silk: a fifth domain, and a garment-level product

`batch-08-silk` had failed `verify` twice and was recorded as a negative
result. The headline cause was ours, not the models': `fetch_url()` never
called `html.unescape()`, so `&nbsp;` survived into the inbox that `verify`
matches quotes against, and an honest quote spanning one could never match.
That fix landed separately; this is the re-run it enables.

Five figures verified and promoted, plus one recorded as a human judgement.

- **A third hard anatomical constant.** One silkworm spins one cocoon — the
  degenerate one-to-one form of two wings per chicken. It is load-bearing:
  every per-garment figure in the subject is a cocoon count, and a cocoon count
  is only an animal count because the constant holds.
- **The corpus's first garment-level product.** A necktie is about 150
  silkworms, a shirt about 1,000, a dress 1,700–2,000. Measured in garments,
  not in pieces or mass, and the first product here that is worn rather than
  eaten.
- **The first sourced mixing pool in the project.** Every other mixing stage in
  the corpus cites our own estimate, because nobody in any trade measures pool
  size. Reeling is the exception: five cocoons are combined into one thread,
  stated outright and returned independently by both models.

Three things this run got right by being told about them, and they are worth
recording because each was a prior failure:

- **The semantic hole the gate cannot see.** The previous run stored the
  *dress* numbers in the *shirt* row, from a sentence answering two questions
  at once. Every figure was genuinely in the quote, so no automatic check could
  object. The spec now names the trap; the row now reads 1,000.
- **A source that only exists in a browser.** The cited necktie page serves its
  article body through JavaScript, so to this project's fetcher it contains
  neither of its own figures — two runs read as model weakness for a week. It
  is replaced by two sources that survive a no-JS fetch, and they disagree
  (150 against 120–130), which is reported on the product row rather than
  averaged away.
- **A figure no machine could produce.** Cocoons-per-worm was withdrawn from
  the batch rather than coerced. No fetchable source states it numerically, and
  reading `1` out of "spun by a single silkworm larva" is a judgement about
  what a source means. It is recorded as a human judgement, with the paper's
  own "usually" and its multi-larva counterexample intact, and graded
  `industry` rather than `study` even though the paper is peer-reviewed —
  the sentence is uncited scene-setting, not the finding.

Rearing mortality is deliberately **not** modelled. The only honest band is
0.70–0.97, which spans an order of magnitude and would look like a measurement
to everything downstream.

The unsourced-estimate share of loss factors rises from 46% to 48%, and the
README says so. That is the audit working: silk is the thinnest-sourced subject
in the corpus and the thinness stays visible instead of being laundered by
proximity to well-sourced poultry figures.

### Tags that are not releases

Since #37 the merge cuts the release, so a tag is no longer how you publish one.
What was left over was a tag still firing the entire pipeline. `ci.yml` now
triggers on `v[0-9]*` instead of `v*`, and the test and citation jobs skip tag
refs: a tag names a commit that already passed on master, so re-running them
proved nothing and made tagging feel expensive enough to avoid. Only
`version-consistency` runs, and only for a tag someone typed by hand -- a tag
the workflow pushes with the default token raises no event at all.

Anything not matching `v[0-9]*` is now a marker tag -- `snapshot/...`,
`checkpoint/...` -- which starts no run and claims no number. Making those cheap
exposed a latent bug: `git describe --tags` returns the newest tag of any shape,
so a marker sitting after the last release would have become the base of the
bump check, in `release.yml` and `release_check.py` both, measuring the diff
from a commit nobody released and saying nothing about it. Both call sites now
match version tags only, with tests that fail without the fix.

The bump step inside `version-consistency` is gone rather than fixed. It checked
out without `fetch-depth: 0`, so `git describe` found no tags, and it had been
taking its "no previous tag" branch and exiting 0 on every tag it ever ran on.
`release.yml` runs the real check before the tag exists.

`docs/VERSIONING.md` still told you to tag and release by hand, which #37 had
already taken away.

### The version is decided at merge, not on the branch

A branch now writes `## Unreleased` and no number anywhere — not in the
changelog heading, not in `pyproject.toml`. `tools/next_version.py` computes
the number when the merge lands, from the latest version tag plus
`release_check.py`'s verdict on what actually changed, then writes it into
both files and lands it on master ahead of the tag (through a pull request —
see below).

This closes two failures that were the same failure.

**Releases were being skipped.** Reading `pyproject.toml` only ever released
the version master *currently* declared, so any release that another merge
landed on top of vanished. v1.9.1 and v1.10.0 were both lost to it within one
hour on 2026-07-31, and both had to be backfilled by hand. A number derived at
merge cannot be overtaken, because the merge that computes it is the one that
publishes it.

**Numbers were being raced for.** `docs/VERSIONING.md` already said to pick the
number last, but that was a rule people had to remember while several branches
were in review at once. On 2026-07-30 a seasonality branch was numbered
v1.5.0, another session released v1.5.0 during its review, it was renumbered
v1.6.0, and that was taken too — it shipped as v1.7.0 having cost two rebases
and two sweeps of the version string through three files. A branch that names
no number cannot lose a race for one.

`pyproject.toml` is now an output of the release job rather than an input to
it. Editing it on a branch only creates a conflict for the bot to resolve.

### The release job stopped being able to push, and now opens a PR instead

`release.yml` recorded the computed version by pushing straight to master. A
`protect-master` ruleset added on 2026-07-30 rejects that:

```
remote: - Changes must be made through a pull request.
remote: - 4 of 4 required status checks are expected.
 ! [remote rejected] HEAD -> master (push declined due to repository rule violations)
```

Four consecutive merges failed on it — #44, #47, #48, #49 — and **v1.12.0 was
computed by the first of them, created inside the failed job, and lost with
it**: no tag, no release, five merges sitting unreleased on top of v1.11.0.
The number was never the problem; the last step was.

The job now goes through the front door. It commits to `release/vX.Y.Z`, opens
a pull request, and waits for it to squash-merge. **No bypass actor, no PAT, no
GitHub App, no new secret** — the default `GITHUB_TOKEN` is sufficient, given
`pull-requests: write` and `actions: write` beside the existing
`contents: write`.

Four details are load-bearing:

- **The PR's checks are dispatched by name.** GitHub raises no
  workflow-triggering event for anything the default `GITHUB_TOKEN` does — the
  rule this repo already knew about for bot-pushed tags. So `ci.yml`'s
  `pull_request` trigger does not fire for the bot's own PR and its four
  required checks would sit "Expected" forever. `ci.yml` now also accepts
  `workflow_dispatch`, and the release job requests a run against the release
  branch. The checks run for real, on the exact tree being merged; nothing is
  reported green on their behalf.
- **The tag moved to the squash commit.** Squashing means the commit built on
  the release branch never becomes an ancestor of master, so a tag on it would
  sit off-history where `git describe` cannot see it. The squash commit is the
  first commit *on master* declaring the version — what a human would tag, and
  what `version-consistency` asserts. It is read back from the PR rather than
  taken from master's tip, since another merge may have landed on top, and the
  job refuses to tag a commit whose `pyproject.toml` disagrees with the number.
- **The job waits, and fails loudly.** It polls until the PR merges. A
  conflict, a close, or forty minutes without a merge fails the job with the
  PR URL in the error, and no tag is cut. A release job that exits 0 having
  recorded nothing is precisely the failure this file keeps documenting.
- **`git pull --rebase` is replaced by syncing to master's tip first.** The
  run now reads master as it currently is, before computing anything, rather
  than rebasing after. That is strictly stronger: rebasing happened *after* the
  number was computed, so a run whose trigger SHA predated a landed release
  would rename an `## Unreleased` section still holding the previous release's
  prose and publish it again under a second number. Reading the tip first
  collapses concurrent runs correctly — the first releases everything
  unreleased, the second finds nothing to do and does nothing.

It needs **one repository setting**, which is the one thing here a workflow
file cannot grant itself: *Settings → Actions → General → Workflow permissions
→ "Allow GitHub Actions to create and approve pull requests"*. With it off,
`gh pr create` fails with `GitHub Actions is not permitted to create or approve
pull requests` — which is how the first live run of this mechanism died. A
leftover `release/vX.Y.Z` branch with no PR is now cleared and recreated rather
than failing the job, so one dead run does not wedge every release after it; a
leftover branch *with* an open PR still fails, because that one is in flight.

Also fixed alongside it: `next_version.py`'s `latest_tag()` called
`git describe --tags` unfiltered, so a marker tag (`snapshot/…`,
`checkpoint/…`) pushed after the last release would silently become the base
the next number counted from. `docs/VERSIONING.md` claimed every call site
passed `--match 'v[0-9]*' --exclude '*-*'`; this third one, added later, did
not. Two tests cover it.

## v1.11.0 — 2026-07-31

### Variant B becomes a real design

The harness had no design in it. `v2/index.html` was a byte-copy of the
shipped page, so there was nothing to measure — the apparatus was finished and
the thing it existed to test had never been built.

- **Three files instead of one.** Variant A keeps 2,109 lines of markup, CSS
  and JS interleaved, where changing the type scale means scrolling past the
  Monte Carlo code to find it. Variant B splits into `v2/index.html`,
  `v2/app.css` and `v2/app.js`. The element ids stay identical across both
  arms: two designs that disagree about what to call the answer field are two
  applications, and the test would measure the wrong difference.
- **A cold instrument instead of warm paper.** Variant A dresses the project
  as a bulletin — cream stock, a serif display face, violet inspection ink.
  The subject is a measuring problem, so variant B is built as an instrument:
  blue-grey stock, a condensed grotesque, and one accent taken from
  chill-tank water. The warm ambers are untouched and are now **the only warm
  thing on the page**, so colour alone tells you what is data and what is
  chrome. `industry` moves from cyan to the violet that vacated the accent
  slot, which also widens the hue gap between the four evidence grades.
- **The answer and its band are one object.** Variant A centred the figure
  and parked the floor..ceiling band below it as a thin decoration. This
  project's claim is not "12", it is "12, and here is the span it had to fall
  inside" — so the band is set beside the figure at instrument scale, ruled
  every 10%, with the reading drawn as a hard edge rather than a gradient.
- **Eleven views are a list, not a tab strip.** The horizontal nav wrapped to
  three rows on a laptop and put the current view's name in a different place
  at every window width. It is a sticky index in a left rail on desktop, and
  one scrolling row on a phone, where wrapping had pushed the answer most of
  a screen down.
- `test_static.py`'s fixtures now **follow `/static/` links** rather than
  reading the document alone. Every invariant is about what reaches the
  browser, not which file it was typed into. This mattered immediately:
  `test_theme_is_applied_before_first_paint` had been passing variant A for
  the wrong reason — its inline stylesheet put `data-theme` in `<head>`
  whether or not any script set it — and it now checks the mechanism.

**Variant B was collecting nothing.** This branch was written against the
harness as first drafted, before the variant token was signed, so
`v2/index.html` carried no `__CCW_AB_TOKEN__` placeholder — and `ab.js`
returns early without one. The redesign would have served normally, looked
right, and reported not a single event, which is indistinguishable from a
variant nobody visited. Caught on rebase by
`test_every_variant_carries_the_measurement_hooks`, which exists for exactly
this.

`test_no_variant_ships_its_own_copy_of_the_instrument` moved from the `html`
fixture to `doc` for a related reason: now that the fixture follows
`/static/` links it inlines the shared `ab.js`, so the test failed on both
arms over the very file it is meant to protect. It now reads the variant's
own assets and skips `ab.js`.

The seed-identity test is deleted rather than fixed. It existed to keep the
copy in step with the control while B was a copy, and divergence is the point
now.

**The A/A noise floor was never run**, and the arms have diverged, so that
number is not available from this branch. It never collected real traffic —
only our own verification sessions, which were cleared. Any difference this
experiment now reports has no measured baseline to be compared against.

## v1.10.0 — 2026-07-30

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
- `static/v2/index.html` was seeded as an **exact copy** of the shipped page,
  so the first run would be an A/A test measuring the noise floor. A later
  difference smaller than that one is not a difference. (Superseded in
  v1.11.0 — variant B carries a real design now, and that run never happened.)
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

### The experiment runs on swamplink, because Render cannot store it

Render's service has no disk — deliberately, it is read-only at runtime — so
`metrics.db` would sit on the container filesystem and be lost on every deploy
and every wake from the free tier's idle spin-down. `WINGS_AB_SPLIT` is pinned
to `0` there, with the reasoning in `render.yaml`.

swamplink has a real disk and is always on, so that is where it runs.

- `compose.yml` mounts a named volume at `/data` — the one piece of state
  this app has. The corpus is baked into the image and never written to;
  metrics are written constantly and are worthless if they do not outlive the
  container.
- The Dockerfile creates `/data` owned by the unprivileged user. Docker seeds
  a fresh named volume from the image path, ownership included; mounting onto
  a path the image lacks yields a root-owned volume the container cannot
  write to.
- **A/B config lives at `/srv/apps/wings/ab.env`, outside the checkout.** The
  post-receive hook overwrites `src/.env` with `GIT_COMMIT` on every deploy,
  so anything put there dies at the next push. Keeping the split there also
  makes starting and stopping the experiment an operational dial rather than
  a code change.
- `/api/metrics/summary` reports `collecting_since` and `window_hours`, so an
  emptied store reads as a resetting window rather than a quiet week.

### A validator, because a public experiment collects more than the experiment

`wings ab` prints the comparison. `wings ab-clean` reports what does not
belong in it, and `--clean` removes it. Read-only by default.

It catches sessions that saw both arms (what `?ui=` flipping looks like
afterwards, including our own testing — it inflates both arms at once),
events with no pageview, sessions at the ingest ceiling, impossible load
times, tabs left open for hours, and arms that no longer exist. Retention
pruning is opt-in via `--older-than`.

**It refuses to clean everything it flags.** A session that loaded a page and
then made no API calls looks like a crawler and looks identical to a variant
failing on somebody's browser — the most valuable thing this experiment could
surface. Those are reported, starred, and never deleted. A cleaner that
quietly removes the interesting cases is worse than no cleaner, because the
store then looks tidy and is wrong.

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
