# Versioning

## Single source of truth

The version lives in **`pyproject.toml`** and nowhere else.

Everything that reports a version derives it from the installed package
metadata:

| Surface | How it gets the version |
|---|---|
| `counting_chicken_wings.__version__` | `importlib.metadata.version()` |
| `wings --version` | `__version__` |
| `GET /api/version` | `importlib.metadata.version()` + Render's commit SHA |

Nothing hardcodes a version string a second time. That rule exists because
the alternative fails quietly: two declarations drift, and a build starts
claiming a version it is not. We hit a mild form of this already — an
editable install kept reporting `0.1.0` after `pyproject.toml` said `1.0.0`,
because the metadata was stale until reinstall.

## Why not setuptools-scm

Deriving the version from git tags is tempting and would remove the manual
bump. It is the wrong call **for this project specifically**, because of the
deploy target: Render clones the repo without tags, so `setuptools-scm` would
resolve to something like `0.1.dev1+g8031a98` in production while the tag
says `v1.0.0`.

A static version plus a CI check that tag and `pyproject.toml` agree is
duller and correct. Revisit only if the deploy pipeline starts fetching tags.

## Semantic versioning

[SemVer 2.0.0](https://semver.org). Given `MAJOR.MINOR.PATCH`:

- **MAJOR** — breaking change to the CLI contract, the API response shapes,
  or the meaning of a published figure.
- **MINOR** — new capability, backwards compatible. New views, new endpoints,
  **new data**.
- **PATCH** — fixes only, no new capability.

### Data changes are versioned changes

Unusually for a library, **this project's data is part of its public
interface**. Someone citing "6.90 chickens required for a dozen wings" is
citing a number that moves when we source a better loss factor.

So:

- Adding sources, states, or facts → **MINOR**.
- Correcting a figure such that a headline answer changes → **MINOR**, and
  the changelog must state the old and new values.
- Fixing a typo in a note → **PATCH**.

`GET /api/version` returns row counts alongside the version for exactly this
reason: data ships in the same push as code, so a version number alone cannot
tell you whether the corpus moved.

## Release procedure

1. Update `version` in `pyproject.toml`.
2. Add a `CHANGELOG.md` section. State what moved, including any figure whose
   value changed.
3. Commit.
4. Tag: `git tag -a vX.Y.Z -m "..."` — the tag is `v`-prefixed, the
   `pyproject.toml` value is not.
5. `git push --follow-tags`.
6. `gh release create vX.Y.Z --notes-file CHANGELOG.md --verify-tag`

CI enforces step 1 against step 4: pushing a tag whose version disagrees with
`pyproject.toml` fails the build rather than publishing a mislabelled release.

## What is deployed is not necessarily what is tagged

`render.yaml` tracks `branch: master`, not tags. The deployed site is
therefore whatever master last was — which is normally *ahead* of the latest
release, not behind it.

This is a deliberate choice: the site is a live view of the corpus, and
holding it back to the last tag would mean newly sourced data sat unpublished.
The consequence is that "is v1.0 running?" is the wrong question to ask of the
deployment. Ask `/api/version` for the commit SHA instead.

To pin the deploy to releases instead, change `branch: master` to a tag or a
release branch in `render.yaml`.
