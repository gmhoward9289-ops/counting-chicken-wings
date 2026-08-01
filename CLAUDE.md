# counting-chicken-wings

Answers "how many chickens does it take to make a dozen chicken wings?" from a cited
data corpus. **The data is the product**, and its credibility rests on one guarantee:
every published number traces to a real source.

## Commands

```bash
pip install -e ".[dev,gui]"          # gui extras are required — the API tests import the FastAPI app
python -m counting_chicken_wings.build   # compile the YAML corpus into SQLite
python -m counting_chicken_wings.audit   # every statistic must cite a source in sources.yaml
pytest -q                            # 721 tests
wings 12                             # CLI: a dozen wings
wings gui                            # serve the web UI
```

`build` must run before the API or CLI will serve anything. CI runs `build`, `pytest`,
and `audit` as separate jobs so "is every number cited?" is visible as its own check.

`WINGS_DB=<path>` overrides where `chickens.db` is built and read. It is the API's only
override (`wings` also has `--db`). Without it the path derives from `__file__`, which
lands in the repo root **only under an editable install** — which is why the Dockerfile
and render.yaml both use `pip install -e`.

**CI pins Python 3.12.** Create a 3.12 venv for this project before trusting a local test
result — a different interpreter is a different result.

## The invariant that matters

`audit.py` fails the build if any statistic cites a source that does not exist in
`data/sources.yaml`. Do not weaken this to make a build pass. If a number has no source,
the number does not ship — that is the whole point of the project, and it is exactly the
guard that makes machine-extracted data safe to accept.

## Architecture

Data lives in **YAML under `data/`**; code reads it and never hardcodes figures.
`build.py` compiles YAML → SQLite (`schema.sql`), and everything downstream — `cli.py`,
`api.py`, `export.py` — reads the database, not the YAML.

So: **to change an answer, change YAML, not Python.** A figure hardcoded in a module is
a bug, because it bypasses the citation audit.

- `model.py` — the calculation, including scientific mode (variable confidence, tornado,
  distributions)
- `seasonality.py` — the month-by-month statistics and, more to the point, the
  three tests that decide whether a swing is a season at all. No database
  dependency, like `model.py`. Its thresholds are ours rather than a source's,
  so anything it concludes is graded `estimate`
- `export.py` — corpus as `.txt` / `.csv` into `data/exports/`
- `brand.py` — the ASCII chicken, shared by CLI and web so they cannot drift
- `tools/` — one-off source fetchers (`fetch_census_states.py`,
  `parse_production_value.py`). Extend these rather than writing new scrapers.

## The frontend

One page, three files: `static/index.html` (markup), `static/app.css`,
`static/app.js`. **The element ids are the contract between the markup and
`app.js`** — rename one in the HTML without renaming it in the script and the
section simply never fills in, silently.

`GET /` sends `index.html` as a file. It used to be rendered per request,
because two designs shared the URL and each needed a signed token naming
which one it was; there is nothing per-visitor left to substitute.

`test_static.py` runs the structural invariants — dark mode, no hardcoded
corpus prose, focus visibility, headline scaling. Its fixtures **follow
`/static/` links**, so a rule that lives in `app.css` rather than inline is
still checked; reading only the document would pass the page by finding no
rules to object to.

There was an A/B test here: `static/index.html` was a frozen control and
`static/v2/` the redesign, with a metrics store, a signed variant token and
`wings ab` / `wings ab-clean`. It was retired without a result. The A/A
noise floor was never collected before the arms diverged, so nothing it
reported had a baseline to be measured against, and the frozen control meant
no UI work could touch the shipped page. The redesign survives on design
merit, not on data.

## Two questions, never conflated

1. **How many birds' worth of wing did this consume?** A supply-chain question — 6 plus
   every loss walking backwards up the funnel.
2. **How many individual chickens are physically on the plate?** A pooling question,
   bounded hard at 6 below and 12 above.

Answer is always ≥ 6, usually near 12. Keep these separate in code, tests, and prose.

## Data constraints worth knowing before you "fix" them

- **State coverage.** NASS reports broilers slaughtered in 40 states but publishes only
  22 individually — the rest are suppressed under disclosure rules. That was a hard
  ceiling on the primary source and was broken by cross-validating against Census and
  NASS Production & Value (see `data/census_states.yaml`,
  `data/production_value.yaml`). Suppression is a real constraint, not a gap to fill by
  estimating.
- **Some states will only ever have presence, not volume.** Render them differently
  rather than leaving them blank or inventing a figure.
- Small and independent producers are the hardest ask in the roadmap — NASS disclosure
  rules exist specifically to protect them. Expect qualitative coverage.

## Versioning and deploys

Read `docs/VERSIONING.md` before touching a version. The two rules that catch people:

- **Version lives only in `pyproject.toml`.** Everything else derives it from installed
  package metadata. An editable install can report a stale version until reinstalled.
- **The scheme is MAJOR.MINOR.MINOR, not SemVer** — the third digit is not a patch
  level, and routinely carries data. **Version by capability, not by volume.** A new
  *kind* of data — a domain, a product, a table, a dimension — takes the second digit.
  **More rows of a kind we already have takes the third**, however many rows: another
  country's series landing in an existing table answers nothing new. The exception runs
  the other way — a one-line fix that moves a published headline figure takes the second,
  because someone's existing citation is now wrong, and the changelog states old and new.
  The old rule ("all data changes are MINOR") took the project 1.0.0 → 1.7.0 in two days
  and made the middle number meaningless.
- **Never write a version number on a branch — not in `pyproject.toml`, not in the
  changelog heading.** Write your entry under `## Unreleased` and stop there. The
  number is computed at merge by `tools/next_version.py`, from the tag that exists
  plus `release_check.py`'s verdict on what actually changed.

  This used to be a rule you had to remember to follow, and it did not survive
  contact with several sessions merging the same day: v1.5.0 and v1.6.0 were both
  taken out from under a branch in review on 2026-07-30, each renumber costing a
  rebase and a sweep of the version string through three files. A branch that names
  no number cannot lose a race for one.

**Versioning, tagging and releasing are all automatic — do not do any of them by
hand.** `.github/workflows/release.yml` fires on every push to master and, when
`CHANGELOG.md` carries an `## Unreleased` section with content:

1. syncs to the current tip of master, not the SHA that triggered the run;
2. computes the number from the latest version tag and `release_check.py`'s verdict;
3. rewrites `## Unreleased` to `## vX.Y.Z — <date>` and sets `pyproject.toml`;
4. **opens a pull request** with that commit and waits for it to squash-merge;
5. tags the squash commit and publishes the GitHub release against it.

So **the merge is the release**, and all you owe it is a written changelog section.
A section that cannot be described fails the job rather than publishing an empty
release.

Three consequences worth knowing:

- **`pyproject.toml` is an output now, not an input.** It is written by the release
  job. Editing it on a branch just creates a conflict for the bot to resolve.
- **The release commit goes through a PR like everyone else's.** It used to push
  straight to master; the `protect-master` ruleset added 2026-07-30 rejects that,
  and four consecutive merges failed on it before this was fixed. Expect to see a
  short-lived `release/vX.Y.Z` branch and a `Release vX.Y.Z` PR after each merge —
  they are the bot's, they auto-merge, and the branch deletes itself. If one is
  sitting open and red, the release did not happen and the job failed saying so.
- **The version checks moved earlier.** `ci.yml` gates them on tag refs, which cannot
  work for a bot-created tag: GitHub does not raise workflow-triggering events for
  pushes made with the default `GITHUB_TOKEN`, so a tag the workflow pushes starts
  nothing. `release.yml` therefore runs `release_check.py` itself, *before* tagging —
  a bad release is easier to prevent than to retract. That same rule is why `ci.yml`
  carries a `workflow_dispatch` trigger: the bot's own PR gets no `pull_request`
  event, so `release.yml` asks for its four required checks by name.
- **"No `pull_request` event" does not mean "no `pull_request` run."** GitHub still
  *creates* one for the bot's PR and parks it at `action_required`, awaiting a human.
  That parked run holds the four required contexts, so it pins the PR at `BLOCKED`
  and the dispatched run passing alongside it does not release it. The tell is
  `gh pr checks` saying **"no checks reported on the branch"** while
  `/commits/<sha>/check-runs` shows them all green — a red release PR with nothing
  visibly wrong. `release.yml` now approves the parked run itself, inside the wait
  loop (`approve_stalled_runs`), which is not a bypass: approving makes the required
  checks actually run, and they still have to pass. Loosening
  `fork-pr-contributor-approval` repo-wide would also have fixed it and was rejected —
  this repo is **public**, and that knob also gates first-time human contributors.

Deploys track `branch: master`, not tags, so the deployed site is normally *ahead* of
the latest release. "Is v1.0 running?" is the wrong question — ask `GET /api/version`
for the commit SHA.

**The release merge is the one push to master that does not deploy itself.**
`deploy.yml` triggers on `push`, and the release PR is merged with `GITHUB_TOKEN`, so
no `push` event is raised — v1.12.1 sat undeployed with nothing red anywhere, because
no Deploy run existed to be red. `release.yml` now dispatches `deploy.yml` explicitly
after its merge; the restriction is on the event *cascade*, not on the dispatch API.
If a release ever ships and the site does not change, check that the **Deploy the
release** step ran, not just that Deploy's own runs are green.

## Docs

`docs/ROADMAP.md` (milestones, with `[!]` marking data-blocked items) ·
`docs/RESEARCH.md` (source findings) · `docs/ISRAEL-PLAN.md` (post-1.0 international,
scoped for handoff) · `docs/VERSIONING.md`.
