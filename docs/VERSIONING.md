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
  a new **kind** of data.
- **PATCH** — fixes, and **more of a kind of data we already had**.

### Data changes are versioned changes — but not all of them are MINOR

Unusually for a library, **this project's data is part of its public
interface**. Someone citing "6.90 chickens required for a dozen wings" is
citing a number that moves when we source a better loss factor. That is why
data is versioned at all, and it stays true.

What was wrong was treating *every* data addition as new capability. The rule
used to read "adding sources, states, or facts → MINOR", and under it the
project went **1.0.0 to 1.7.0 in about two days**, almost entirely on data.
A minor number that increments whenever anyone adds rows stops telling you
anything: it cannot distinguish "eggs are now a product" from "twenty more
Israeli rows landed in a table that already existed".

The test is **capability, not volume**:

| Change | Bump | Why |
|---|---|---|
| New domain, species, product, or table | **MINOR** | you can ask a question you could not ask before |
| New view, endpoint, CLI flag, or output | **MINOR** | same reason |
| More rows of a kind already present — states, sources, facts, another year, another country's series | **PATCH** | nothing new is answerable; the corpus is denser, not wider |
| A figure moves such that a **published headline answer changes** | **MINOR** | a citation someone already made is now wrong, which is exactly the case data-versioning exists for. Changelog states old → new |
| Typo, note, comment, formatting | **PATCH** | |

Two consequences worth stating plainly, because both look wrong at a glance:

- **Adding a whole country's statistics can be a PATCH** if it lands in tables
  that already exist and answers questions the schema already answered. Israel
  arriving in `output_stat_year` is more rows. Israel forcing the `country`
  dimension into existence was the MINOR.
- **A one-line data fix can be a MINOR** if it moves a number the front page
  publishes. Size is not the criterion.

Past releases are **not renumbered**. v1.0.0 through v1.7.0 stand as tagged —
retagging would break the release links and the deploy history for no gain.
This applies from the next release onward.

`GET /api/version` returns row counts alongside the version for exactly this
reason: under this rule a PATCH can move thousands of rows, so the version
alone cannot tell you whether the corpus grew. The counts can.

### The rule is checked, not remembered

```bash
python tools/release_check.py              # this tree against the latest tag
python tools/release_check.py --base v1.6.0
```

It builds the corpus at both refs and reports the smallest bump the diff
justifies. Three signals:

| signal | verdict |
|---|---|
| new table, or new `domain` / `species` / `product` row | MINOR |
| a table or kind **removed** | MINOR — retraction breaks an existing citation |
| row counts of existing tables changed, nothing else | PATCH |
| **`wings count 12` returns different numbers for any product** | MINOR, whatever else did or did not change |

The last one is the reason this exists. It is the rule's own criterion rather
than a proxy for it, and unlike the other two it fires on a *code* change as
readily as a data one — with the schema and every row count untouched. It also
prints a warning naming each product whose answer moved, so the changelog can
be given its old → new line.

It asks **every active product**, not just wings. The first version asked only
`whole_wing`, which on a project whose direction is adding subjects meant
watching a shrinking fraction of the corpus.

**What it does not cover**, stated because it was over-claimed twice before
being measured: it runs the CLI, so an **API-only regression is invisible to
it**. The saffron ceiling bug is the worked example and it fails on both
counts — the wrong ceiling was served by `/api/calculate` while the CLI printed
the right number, and saffron was a brand-new product with no previous answer
to differ from. That one is caught by `tests/test_api.py`. Treat this check as
the motivation for watching published answers, not as a net that would have
caught it.

**Over-bumping passes, under-bumping fails.** Shipping a bigger number than
required is a judgement call; shipping a smaller one silently breaks the
promise that the number means something.

The base tag is materialised with `git archive` into a temp directory rather
than checked out, so the check never touches the working tree — which matters
here, because more than one session is usually live in it.

CI runs it **advisory on pushes and PRs** and **enforcing on tags**, where it
compares against the previous tag rather than the one being cut.

#### What it cannot see, stated plainly

It diffs the **corpus and the published answer**. A new view, endpoint or CLI
flag is MINOR under the rule and invisible to it, because nothing about the
data changed. Run it against v1.6.0 and it reports "PATCH required" for a
release that added `seasonality.py`, a view and an endpoint — and v1.7.0 was
correctly MINOR.

That under-detection is deliberately the safe direction. The check only fails
on **under**-bumping, so a human who bumps MINOR for new capability passes
regardless. It is a floor on the required bump, never a ceiling, and "PATCH
required" means *at least* patch — not *only* patch.

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
