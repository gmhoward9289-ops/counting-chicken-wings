### `release.yml` describes the mechanism it actually runs

v1.16.0 moved branches onto `.changes/` entries with an optional `bump:`
level, and `release.yml`'s comments were the one place left describing
`## Unreleased` as the only way a branch says something shipped. On a repo
where those comments are the documentation — every one of them explains a
release that went wrong once — a stale one is worse than none.

Comments only, plus one belt-and-braces pathspec: the release commit now names
`.changes` alongside `CHANGELOG.md` and `pyproject.toml`. `--apply` already
stages its own deletions, so this changes no behaviour; it means a future edit
to that line cannot silently reintroduce the trap where the notes ship, the
changesets stay on master, and the next release publishes all of them again.
