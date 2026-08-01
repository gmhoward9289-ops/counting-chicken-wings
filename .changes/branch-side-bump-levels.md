---
bump: second
---
### A branch can say how big its change is, without naming a number

`release_check.py` diffs the corpus and the published answer, and
`docs/VERSIONING.md` has always said outright that a new view, endpoint or CLI
flag "takes the second digit under the rule and is invisible to it". Nothing
could act on that. The automated verdict was the only input `next_version.py`
had, so it was a ceiling as well as a floor — v1.15.1 shipped a new endpoint
and a new database view under a third-digit bump because there was no way to
say otherwise, and **MAJOR was unreachable entirely**, since `release_check`
never returns it by design.

A branch now writes one file under `.changes/`, carrying its changelog prose
and an optional `bump:` of `third`, `second` or `major`:

```markdown
---
bump: second
---
### What changed
```

**A level, never a number**, and that is the whole design. A number on a branch
has to hope nobody takes it during review — v1.5.0 and v1.6.0 were both taken
out from under a branch on 2026-07-30. A level is relative, so two branches may
both declare `second` and neither collides; the number is still resolved at
merge against the tag that exists then. A number in a `bump:` is refused with
that history in the error.

**It may only raise.** The resolved level is `max(computed, declared)`. A
declaration below the corpus diff's floor is a warning and the floor wins,
matching the rule `release_check` already enforced: over-bumping passes,
under-bumping fails.

### One file per branch, instead of one shared section

Every branch appended to the same `## Unreleased` section, so every second
branch open at once rebased through a conflict in the same paragraph — on a
repo where eight sessions are routinely live, and the conflict this changeset's
own PR hit an hour before it was written.

`## Unreleased` is still read. A release that finds both a section and files
merges them into one, so branches in flight keep working and nothing has to be
migrated on a deadline.
