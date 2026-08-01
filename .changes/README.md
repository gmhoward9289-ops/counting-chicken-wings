# `.changes/`

One file per branch, holding that branch's changelog entry and — optionally —
the size of bump it needs. The release job merges every file here into one
`## vX.Y.Z` section and deletes them.

```markdown
---
bump: second
---
### What changed, in the changelog's own voice

Prose. This lands in CHANGELOG.md verbatim.
```

Name the file after the branch (`say-which-species.md`). The name never
appears in the changelog; it exists so two branches cannot collide.

## Write a level, never a number

`bump:` is one of **`third`**, **`second`**, **`major`**. It is not a version
number, and a number here is an error rather than a shortcut.

The distinction is the entire point. A branch that names `v1.16.0` has to hope
nobody else takes that number during review — v1.5.0 and v1.6.0 were both taken
out from under a branch in review on 2026-07-30, each costing a rebase and a
sweep of the version string through three files. A *level* is relative, so two
branches may both declare `second` and neither collides; the number is resolved
at merge, against the tag that exists then.

## When to declare, and when not to

Usually don't. `tools/release_check.py` diffs the corpus and the published
answer and gets it right on its own: new tables and new domain/species/product
rows take the second digit, more rows of an existing kind take the third, and a
moved published answer takes the second whatever else changed.

Declare when the capability is one the corpus diff **cannot see**, which
`docs/VERSIONING.md` lists as a new view, endpoint or CLI flag. v1.15.1 shipped
a new endpoint and a new database view under a third-digit bump because there
was no way to say so. Also declare `major`, which is otherwise unreachable —
`release_check` never returns it, by design, because no diff can detect the
*meaning* of a published figure changing.

## It may only raise

The resolved level is `max(what release_check requires, what the branches
declared)`. A declaration below the computed floor is a warning, not an error,
and the floor still wins. Over-bumping has always been allowed here and
under-bumping has never been, because shipping a smaller number silently breaks
the promise that the number means something.

## The old way still works

A `## Unreleased` section in `CHANGELOG.md` is still read, and a release that
finds both it and files here merges them into one section. Nothing needs
migrating in a hurry; new work should use a file, because a single shared
section is a guaranteed rebase conflict for every second branch open at once.

Check what you wrote before you push:

```bash
python tools/next_version.py --lint
python tools/next_version.py --explain
```
