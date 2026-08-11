### Tests and tools now state their encoding instead of inheriting the platform default

`pytest` could not complete on Windows: several test fixtures and tools called
`Path.read_text()` / `.write_text()` / `open()` with no `encoding` argument, so
Windows fell back to the locale codepage (cp1252 on COOPER) and choked on the
UTF-8 bytes the corpus deliberately carries — sparkline block characters,
Hebrew research documents, and em dashes throughout the data files.

Every bare call site across `tools/`, `src/`, and `tests/` now passes
`encoding="utf-8"` explicitly. The corpus was always UTF-8 by design; relying
on the platform to guess it was the bug, not the content.

Also fixed in passing: `test_build_is_idempotent` left its first `sqlite3`
connection open across the rebuild, which is silently fine on Linux but raises
`PermissionError` on Windows when `build()` tries to unlink the still-open
file. Both connections are now closed explicitly.

No published figure changes; this is test and tooling infrastructure only.
