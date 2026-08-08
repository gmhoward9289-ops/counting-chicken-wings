# AGENTS.md

Project overview, architecture, versioning and deploy rules live in `CLAUDE.md` and
`README.md` — read those first. This file only adds cloud-agent operating notes.

## Cursor Cloud specific instructions

The environment is Python 3.12 (matches CI's pinned interpreter). The update script
already runs `pip install -e ".[dev,gui]"`, so dependencies are in place at session
start. Non-obvious caveats:

- **`python` is not on PATH — use `python3`.** Only `python3` / `python3.12` exist.
  All `python -m ...` commands in `CLAUDE.md`/`README.md` must be run as `python3 -m ...`.
- **The `wings` console script installs to `~/.local/bin`, which is not on PATH by
  default.** Either add it (`export PATH="$HOME/.local/bin:$PATH"`) or invoke the CLI as
  `python3 -m counting_chicken_wings.cli ...` (equivalent entrypoint).
- **Build before serving, but it also self-builds.** `python3 -m counting_chicken_wings.build`
  compiles `data/*.yaml` → `chickens.db`. `db.connect()` lazily builds the DB if it is
  missing, so the CLI/API self-build on first use; an explicit build is still the
  documented step and is fast. `chickens.db` is gitignored.
- **Run the web GUI with `wings gui` (dev) — do not use `pip install` (non-editable).**
  It serves FastAPI via uvicorn on `http://127.0.0.1:8000` (`--host`/`--port` to change).
  The DB path derives from `__file__` and only lands at the repo root under the editable
  install the update script performs, so a plain install would write the DB somewhere
  unexpected. `WINGS_DB=<path>` overrides the DB location if needed.
- **Lint here means the citation audit, not a style linter.** `python3 -m counting_chicken_wings.audit`
  is the project's gate: it fails if any statistic cites a source missing from
  `data/sources.yaml`. Do not weaken it to make a build pass. The `codespell` CI workflow
  is separate and not part of the `dev` extras.
- **Tests:** `python3 -m pytest -q` (the suite imports the FastAPI app, which is why the
  `gui` extra is required for `dev`).
- **Do not hand-edit `pyproject.toml` version or write version numbers on a branch.**
  Versioning/tagging/releasing is automatic — see the "Versioning and deploys" section of
  `CLAUDE.md`. Record changelog intent via a file under `.changes/` instead.
