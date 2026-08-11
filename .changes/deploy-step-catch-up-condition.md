### `release.yml`'s Deploy step now fires on any release work, not just a same-run merge

The second version of a bug this file's own comments already described once:
`Deploy the release` was gated on `steps.landed.outputs.sha != ''`, which is
only set when the SAME run opened and waited on a version PR. A run that
finds the version already on master — because an earlier run's PR merged,
but GitHub never raised a `push` event for that merge (the exact
`GITHUB_TOKEN` limitation this file already routes around for the PR-open
step) — has `computed=no` and `landed.sha` empty, but can still have
`go=yes` and correctly tag and release. That run then skipped Deploy
silently. Observed on v1.19.0: the release was tagged and published, and
the live site kept serving v1.18.0 for roughly 50 minutes with nothing
anywhere reporting a failure.

`Deploy the release` now runs on `steps.need.outputs.go == 'yes'`, the same
condition `Tag` and `Release` already use, since by the time this step's
condition is evaluated those two have either succeeded or the job has
already failed and skipped everything after.
