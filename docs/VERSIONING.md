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

## MAJOR.MINOR.MINOR

Three numeric components, `v`-prefixed tags, still ordered the obvious way —
but **not** SemVer, and the third component is not a patch level:

- **MAJOR** — breaking change to the CLI contract, the API response shapes,
  or the meaning of a published figure.
- **Second** — new capability. A new *kind* of data — a domain, a species, a
  product, a table, a dimension — or a new view, endpoint, CLI flag or output.
  You can ask a question you could not ask before.
- **Third** — everything else that ships. More rows of a kind already present,
  corrections, small features, fixes. Routine forward movement.

The third component is **not a patch level**, and calling it one was the thing
that had to go. It carries real data — sometimes thousands of rows of it.
Neither minor is "breaking-safe" in the SemVer sense either, because for this
project that guarantee was never the interesting one. Both are additive; they
differ in *size*, not in *risk*.

### Why not SemVer, and why not all data changes are second-digit

SemVer's third component means "fixes only, no new capability", and this
project cannot honour that, because **the data is part of the public
interface**. Someone citing "6.90 chickens required for a dozen wings" is
citing a number that moves when we source a better loss factor. That is why
data is versioned at all, and it stays true.

What was wrong was treating *every* data addition as new capability. The rule
used to read "adding sources, states, or facts → MINOR", and under it the
project went **1.0.0 to 1.7.0 in about two days**, almost entirely on data.
A second digit that increments whenever anyone adds rows stops telling you
anything: it cannot distinguish "eggs are now a product" from "twenty more
Israeli rows landed in a table that already existed".

The test is **capability, not volume**:

| Change | Bump | Why |
|---|---|---|
| New domain, species, product, or table | **second** | you can ask a question you could not ask before |
| New view, endpoint, CLI flag, or output | **second** | same reason |
| More rows of a kind already present — states, sources, facts, another year, another country's series | **third** | nothing new is answerable; the corpus is denser, not wider |
| A figure moves such that a **published headline answer changes** | **second** | a citation someone already made is now wrong, which is exactly the case data-versioning exists for. Changelog states old → new |
| Typo, note, comment, formatting | **third** | |

If the *meaning* of a published figure changed rather than its value, that is
a MAJOR, not a second-digit bump.

Two consequences worth stating plainly, because both look wrong at a glance:

- **Adding a whole country's statistics can be a third-digit bump** if it lands
  in tables that already exist and answers questions the schema already
  answered. Israel arriving in `output_stat_year` is more rows. Israel forcing
  the `country` dimension into existence was the second.
- **A one-line data fix can be a second-digit bump** if it moves a number the
  front page publishes. Size is not the criterion.

Past releases are **not renumbered**. v1.0.0 through v1.7.0 stand as tagged —
retagging would break the release links and the deploy history for no gain.
This applies from the next release onward, and the numbers themselves do not
change shape: three components, `v`-prefixed tags, same CI gate.

`GET /api/version` returns row counts alongside the version for exactly this
reason: under this rule a third-digit release can move thousands of rows, so
the version alone cannot tell you whether the corpus grew. The counts can.

### The rule is checked, not remembered

```bash
python tools/release_check.py              # this tree against the latest tag
python tools/release_check.py --base v1.6.0
```

It builds the corpus at both refs and reports the smallest bump the diff
justifies. Three signals:

| signal | verdict |
|---|---|
| new table, or new `domain` / `species` / `product` row | **second** |
| a table or kind **removed** | **second** — retraction breaks an existing citation |
| row counts of existing tables changed, nothing else | **third** |
| **`wings count 12` returns different numbers for any product** | **second**, whatever else did or did not change |

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
flag takes the **second** digit under the rule and is invisible to it, because
nothing about the data changed. Run it against v1.6.0 and it reports "THIRD
required" for a release that added `seasonality.py`, a view and an endpoint —
and v1.7.0 was correctly a second-digit bump.

That under-detection is deliberately the safe direction. The check only fails
on **under**-bumping, so a human who moves the second digit for new capability
passes regardless. It is a floor on the required bump, never a ceiling, and
"THIRD required" means *at least* third — not *only* third.

It also never returns **major**. The MAJOR criterion is the *meaning* of a
published figure changing rather than its value, and no diff can detect that.
`major` stays in the ranking purely so that a human who bumps it still
satisfies the over-bumping rule.

The floor is also why this check and the "pick the number last" rule below do
not argue: the check tells you the smallest number the diff justifies, and you
claim a number after running it. It cannot tell you the claim is *big* enough —
a new endpoint is invisible to it — and it cannot tell you the number is still
free. Nobody claims one any more: `release.yml` computes it at merge, against
master's tip, so "still free" is not a question anyone has to answer.

## Release procedure

While the work is in progress:

1. Write the changelog section under `## Unreleased`. State what moved,
   including any figure whose value changed.
2. Leave `pyproject.toml` alone. Do not pick a number yet.

Then merge. **There is no step 3.** You never pick a number, never edit
`pyproject.toml`, and never write a `## vX.Y.Z` heading.

`.github/workflows/release.yml` fires on every push to master and does the rest:

1. **Syncs to the current tip of master**, not the SHA that triggered it.
2. **Computes the number** with `tools/next_version.py` — the latest *version*
   tag plus `release_check.py`'s verdict on what actually changed.
3. **Runs the gates** — the release must be describable, and the bump must
   match the diff.
4. **Records the number on master through a pull request**: it writes the
   heading and `pyproject.toml`, commits to `release/vX.Y.Z`, opens a PR,
   and waits for it to squash-merge.
5. **Tags the squash commit** and publishes the GitHub release against it.

The tag is `v`-prefixed, the `pyproject.toml` value is not — the workflow adds
the `v`.

Do not tag or release by hand. Releasing was the one manual step left and it
became the step that did not happen: v1.2.0 through v1.7.0 sat untagged until
six were backfilled in a batch, and v1.9.1 and v1.10.0 were merged, bumped and
never tagged at all. The number and the changelog are what you owe; the tag is
not yours to type.

The gates run *before* the tag exists, because a release is easier to prevent
than to retract, and because a tag the workflow pushes with the default
`GITHUB_TOKEN` raises no workflow event — checks hung on `refs/tags/v*` would
never run at all.

### Why the version commit goes through a pull request

It used to `git push origin HEAD:master` directly. The `protect-master`
ruleset, added 2026-07-30, rejects that:

```
remote: - Changes must be made through a pull request.
remote: - 4 of 4 required status checks are expected.
 ! [remote rejected] HEAD -> master (push declined due to repository rule violations)
```

Four consecutive merges failed on it — #44, #47, #48, #49 — and the v1.12.0
that #44's own run computed was created inside the failed job and lost with it.

Adding a bypass actor for the bot would have restored the push, but the
ruleset is the part that is right: nothing should reach master unchecked, and
the release commit is not an exception. So the job goes through the front door.
It needs no PAT, no GitHub App and no new secret — the default `GITHUB_TOKEN`
opens the PR, with `pull-requests: write` and `actions: write` added to the
workflow's `permissions:` alongside `contents: write`.

Three things about it are worth knowing, because each is load-bearing:

- **The checks on that PR are dispatched explicitly.** GitHub raises no
  workflow-triggering event for anything done with the default `GITHUB_TOKEN`
  — the same rule that keeps bot-pushed tags from starting CI. So `ci.yml`'s
  `pull_request` trigger does *not* fire for a PR the job opens, and its four
  required checks would sit "Expected" forever. `ci.yml` therefore also
  accepts `workflow_dispatch`, and the job asks for a run against the release
  branch. The checks genuinely run, on the exact tree being merged; nothing is
  stubbed or reported green on its behalf.
- **The tag points at the squash commit, not at the branch commit.** Squashing
  means the commit built on the release branch never becomes an ancestor of
  master, so a tag on it would sit off-history where `git describe` cannot
  reach it and `release_check --base` would resolve to a commit master never
  saw. The squash commit is the first commit *on master* whose
  `pyproject.toml` declares the version, which is exactly what a human tagging
  by hand would pick and exactly what `version-consistency` asserts. The job
  reads it back from the PR rather than taking master's tip, because another
  merge may have landed on top in the meantime, and a tag one commit too far
  forward would quietly fold somebody else's change into this release. It
  verifies the target declares the version before tagging it.
- **It waits, and it fails loudly.** The job does not fire the PR off and
  exit. It polls until the PR merges; a conflict, a close, or 40 minutes
  without a merge all fail the job with the PR URL in the error, and the tag
  is not cut. A release job that exited 0 having recorded nothing is the
  failure mode this whole file exists to prevent.

Two merges landing together still cannot take the same number, and the
mechanism is now two things rather than one. The `concurrency: release` group
serialises the runs, and syncing to master's tip means the second run reads a
tree that already contains the first run's version commit — so it finds no
`## Unreleased` section, computes nothing, and correctly does nothing. This
replaces the `git pull --rebase` the old push did, and it is strictly stronger:
rebasing happened *after* the number was computed, so a run whose trigger SHA
predated a landed release would rename an `## Unreleased` section still holding
the previous release's prose and publish it a second time under a second
number.

If `release/vX.Y.Z` already exists the push fails and the job fails with it.
That is deliberate: it means an earlier run for that number is still in flight
or died half-done, and overwriting it would hide that.

### Why the number is picked last

Several branches are usually open at once, and they ship to this repo on the
same day — seven releases across 2026-07-29 and 07-30. A version number claimed
when a branch *starts* is a claim on a number the brancher cannot hold: on
2026-07-30 a seasonality branch took v1.5.0, another session released v1.5.0
while it was in review, it renumbered to v1.6.0, and that number went too within
minutes. It shipped as v1.7.0.

Each renumber costs a rebase plus a sweep of the version string through
`CHANGELOG.md` (the heading, plus any cross-reference to it in an earlier
entry), `docs/ROADMAP.md` (the status table plus every "*Shipped in*" marker),
and `pyproject.toml`. Writing under `## Unreleased` costs nothing and cannot
collide, because the heading carries no number to collide with.

This is why there is no longer a "check which numbers are taken" step. It used
to depend on remembering to `git fetch`, and a working tree that has not
fetched cannot see the release that took its number — the collision is
invisible locally, and the gate that would catch it runs in `release.yml` on
push to master, which is to say after you have already merged. Computing the
number at merge, from master's tip, removes the question rather than making it
easier to answer.

Rebase conflicts from concurrent releases are predictable and narrow: only
`CHANGELOG.md` and the generated README stats block. Never hand-merge the README
block — take either side and re-run `python tools/update_readme.py`, which
regenerates it from the database. For `CHANGELOG.md`, if both sides used the
same heading text git auto-merges the *heading* and conflicts only the bodies,
which quietly files your prose under someone else's version. Check which body
sits under which heading after resolving.

## Tags that are not releases

A version tag is a claim: it names a number, and `release.yml` publishes a
GitHub release against it. Sometimes you want to mark a commit without claiming
anything — a demo, a checkpoint before a risky rebase, the tree a measurement
was taken on. That is a **marker tag**, and it is a different kind of object.

| pattern | means | CI |
|---|---|---|
| `vX.Y.Z` | a release. Cut by `release.yml` from `pyproject.toml` | the release flow |
| `snapshot/<slug>`, `checkpoint/<slug>`, any tag not matching `v[0-9]*` | a pointer. Publishes nothing, claims no number | **nothing** |

Markers are free. `ci.yml` triggers on `tags: ['v[0-9]*']`, so a tag that does
not start `v` followed by a digit starts no run at all. Push as many as you like.

Two things make this safe, and neither was true before:

- **`git describe --tags` takes the newest tag of any shape.** A marker sitting
  after the last release would have become the base for the bump check, in
  `release.yml` and in `release_check.py` both — measuring the diff from a
  commit nobody released, and saying nothing about it. Both call sites now pass
  `--match 'v[0-9]*' --exclude '*-*'`.
- **A hand-pushed version tag no longer re-runs the suite.** It names a commit
  that already passed on master; only `version-consistency` runs, which is the
  one check a typed tag actually needs.

There is no alpha or release-candidate tag, and adding one is not a naming
decision. `release.yml` cuts a release for whatever version master declares, so
a prerelease number on master would simply be *released*; a real prerelease
would have to be built from a branch, which the workflow does not watch. It also
needs `actual_bump()` taught to parse a suffix — today `int(x)` raises
`ValueError` on `1.12.0a1`. Worth doing only if previews are actually wanted.

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
