# counting-chicken-wings

Answers "how many chickens does it take to make a dozen chicken wings?" from a cited
data corpus. **The data is the product**, and its credibility rests on one guarantee:
every published number traces to a real source.

## Commands

```bash
pip install -e ".[dev,gui]"          # gui extras are required — the API tests import the FastAPI app
python -m counting_chicken_wings.build   # compile the YAML corpus into SQLite
python -m counting_chicken_wings.audit   # every statistic must cite a source in sources.yaml
pytest -q                            # 368 tests
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

## The frontend A/B test

Two pages, one URL. `static/index.html` is variant `a` (shipped, the control);
`static/v2/index.html` is variant `b` (the redesign). **Do the redesign work in
`v2/`** — editing `index.html` destroys the control.

```bash
WINGS_AB_SPLIT=50 wings gui          # 50% of new visitors get the redesign
open 'http://localhost:8000/?ui=b'   # force a variant by hand, and pin it
curl localhost:8000/api/experiment   # which am I on, and why
curl localhost:8000/api/metrics/summary?hours=24
```

- **The split defaults to 0.** Deploying does not silently start serving a
  second site; the experiment is on only when `WINGS_AB_SPLIT` says so.
- Assignment is deterministic from a random visitor cookie, so a reload does
  not reassign. A design cannot be measured through a page that flickers.
- **Metrics live in `metrics.db`, never `chickens.db`** (`WINGS_METRICS_DB`
  overrides; `metrics.connect()` refuses the corpus path outright). `build`
  recreates the corpus DB, and the citation audit reasons about it — a
  measurement is not a cited figure and must not be able to look like one.
- `static/ab.js` is included **identically** by both pages and hooks the page
  from outside. Do not fork it per variant: an instrument that differs
  between the arms is measuring itself.
- `v2/index.html` starts as an exact copy of `index.html`. That first run is an
  **A/A test** — it tells you the noise floor, and any later difference
  smaller than it is not a difference.
- `test_static.py` runs every structural invariant against both pages. The
  redesign has to clear the same bar (dark mode, no hardcoded corpus prose,
  focus visibility, headline scaling), or it wins the test for a reason that
  has nothing to do with design.
- The summary is descriptive. It computes no significance test, and a few
  dozen sessions will differ by chance alone.

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
- **Do not bump `pyproject.toml` when you start a branch.** Write the changelog under
  `## Unreleased` and set the number in one commit right before merging, after
  `git fetch` and a look at `git log origin/master` for a `(vX.Y.Z)` subject. Several
  branches are open at once and they release the same day — a number claimed early gets
  taken while you are in review, and each renumber costs a rebase plus a sweep of the
  version string through three files.

Render tracks `branch: master`, not tags, so the deployed site is normally *ahead* of the
latest release. "Is v1.0 running?" is the wrong question — ask `GET /api/version` for the
commit SHA.

## Docs

`docs/ROADMAP.md` (milestones, with `[!]` marking data-blocked items) ·
`docs/RESEARCH.md` (source findings) · `docs/ISRAEL-PLAN.md` (post-1.0 international,
scoped for handoff) · `docs/VERSIONING.md`.
