### `release_check` can see the public surface now

The fourth signal, and the one this script's own docstring has been admitting
it needed. Structure, volume and the published answer are all facts about the
**corpus**, so a release that adds an endpoint or a CLI flag moves none of them
— which is why v1.15.1 shipped `/api/scope` and a new database view under a
third-digit bump when the rule wanted the second.

It now diffs the routes and the CLI at both refs, in both directions:

```
  tables      35 -> 35
  answers     12 product(s) compared, none moved
  endpoints   19 -> 20
  CLI surface 69 -> 69

  - new endpoint(s): GET /api/scope

  => SECOND required. 1.15.0 -> 1.15.1 is THIRD.
```

A removed endpoint, subcommand or flag is also the second digit — the same
argument the removed-table rule already makes, one layer up from the data.

**Routes are read from the source, not by importing the app.** The check runs
where `pip install -e .` was used, which has no `gui` extra and therefore no
FastAPI; an import-based probe would raise there, degrade to "not comparable",
and silently never fire in the one place it matters. Reading the decorators
also works at any base ref regardless of what is installed. The CLI is
introspected by importing `build_parser()` in the base tree, which needs only
argparse.

Both probes report `None` rather than an empty list when they cannot read a
ref, because "I could not compare" and "everything was deleted" must not be the
same answer — the trap `answers_moved` already avoids for a product missing at
the base. The human output says which of the two it is, since an empty reasons
list looks identical either way and only one of them is reassuring.

This complements `bump:` rather than replacing it: the surface signal catches
what it can automatically, so a declaration is for the residue — a new page
view, a changed response shape, anything whose capability lives in prose.
