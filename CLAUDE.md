# counting-chicken-wings

Answers "how many chickens does it take to make a dozen chicken wings?" from a cited
data corpus. **The data is the product**, and its credibility rests on one guarantee:
every published number traces to a real source.

## Commands

```bash
pip install -e ".[dev,gui]"          # gui extras are required — the API tests import the FastAPI app
python -m counting_chicken_wings.build   # compile the YAML corpus into SQLite
python -m counting_chicken_wings.audit   # every statistic must cite a source in sources.yaml
pytest -q                            # 158 tests
wings 12                             # CLI: a dozen wings
wings gui                            # serve the web UI
```

`build` must run before the API or CLI will serve anything. CI runs `build`, `pytest`,
and `audit` as separate jobs so "is every number cited?" is visible as its own check.

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
- `export.py` — corpus as `.txt` / `.csv` into `data/exports/`
- `brand.py` — the ASCII chicken, shared by CLI and web so they cannot drift
- `tools/` — one-off source fetchers (`fetch_census_states.py`,
  `parse_production_value.py`). Extend these rather than writing new scrapers.

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
- **Data changes are MINOR version changes.** The data is part of the public interface —
  someone citing a figure is citing something that moves. If a headline number changes,
  the changelog states old and new.

Render tracks `branch: master`, not tags, so the deployed site is normally *ahead* of the
latest release. "Is v1.0 running?" is the wrong question — ask `GET /api/version` for the
commit SHA.

## Docs

`docs/ROADMAP.md` (milestones, with `[!]` marking data-blocked items) ·
`docs/RESEARCH.md` (source findings) · `docs/ISRAEL-PLAN.md` (post-1.0 international,
scoped for handoff) · `docs/VERSIONING.md`.
