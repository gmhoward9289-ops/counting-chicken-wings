"""Drop from `## Unreleased` the blocks a previous tag already published.

    python tools/prune_released.py --base v1.12.0            # rewrite in place
    python tools/prune_released.py --base v1.12.0 --explain  # say what goes

WHY THIS EXISTS. The release job used to push its version bump straight back
to `master`, and that push is what CONSUMED the `## Unreleased` section: the
number and the date replaced the heading, so the next merge started from an
empty section. A `protect-master` ruleset with no bypass actors now rejects
that push -- twelve commits went unreleased across five failed runs on
2026-07-31 -- so the bump lives only on the commit the tag names, and `master`
never learns that anything was released.

That is survivable for the NUMBER, which `next_version.py` derives from the
latest tag rather than from `pyproject.toml`. It is not survivable for the
NOTES. `## Unreleased` on `master` still holds everything v1.12.0 shipped, so
the next release would republish v1.12.0's entries under v1.13.0, and the
release after that would carry both. The duplication compounds.

So the section is pruned against the previous tag before the number is applied:
whatever that tag's changelog already describes is dropped, and what remains is
genuinely new. The previous tag's changelog is the authority because it is the
artefact the release was actually cut from.

MATCHING IS BY `###` HEADING, not by line. Prose repeats -- this changelog runs
to paragraphs, and "The invariant is now enforced across the whole corpus"
could honestly appear twice. A heading names one change, and one change is
released once. Line-level differencing would also shred a paragraph whose
middle sentence happened to recur, turning a considered entry into rubble;
dropping whole blocks either keeps an entry intact or removes it entirely.

A body with no `###` headings at all is left alone rather than guessed at. That
shape has not appeared in this changelog, and inventing a rule for it here
would mean the first time it does appear, notes go missing silently.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"

UNRELEASED = "## Unreleased"

# `### <heading>`, and nothing under a deeper level: `####` is structure WITHIN
# an entry, not a separate entry, and treating one as a block boundary would
# let half an entry be pruned while the other half stayed.
HEADING = re.compile(r"^###(?!#)\s*(.+?)\s*$", re.M)


def unreleased_span(text: str) -> tuple[int, int] | None:
    """Where the `## Unreleased` body starts and ends, or None if absent."""
    m = re.search(rf"^{re.escape(UNRELEASED)}\s*$(.*?)(?=^## |\Z)",
                  text, re.M | re.S)
    return (m.start(1), m.end(1)) if m else None


def normalise(heading: str) -> str:
    """A heading reduced to what makes it the same heading.

    Case and whitespace are noise. An em dash typed as `--` on one branch and
    as `—` on another is the SAME entry, and this project hard-wraps its
    changelog, so the two spellings genuinely coexist.
    """
    h = heading.lower().replace("—", "--").replace("–", "--")
    return re.sub(r"\s+", " ", h).strip()


def blocks(body: str) -> list[tuple[str | None, str]]:
    """The body split into `(heading, text)`, preamble first with no heading."""
    marks = list(HEADING.finditer(body))
    if not marks:
        return [(None, body)]

    out: list[tuple[str | None, str]] = []
    if body[:marks[0].start()].strip():
        out.append((None, body[:marks[0].start()]))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        out.append((m.group(1), body[m.start():end]))
    return out


def published(base: str) -> set[str]:
    """Every `###` heading the changelog carried at tag `base`.

    Read out of git rather than off disk: the working tree's changelog is the
    one being pruned, so asking it what was already released would answer
    "everything" and prune the section to nothing.
    """
    out = subprocess.run(["git", "show", f"{base}:CHANGELOG.md"],
                         capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit(
            f"cannot read CHANGELOG.md at {base}: {out.stderr.strip()[:200]}")
    return {normalise(h) for h in HEADING.findall(out.stdout)}


def prune(text: str, seen: set[str]) -> tuple[str, list[str]]:
    """The changelog with already-published blocks removed, and their names."""
    span = unreleased_span(text)
    if span is None:
        return text, []

    start, end = span
    kept, dropped = [], []
    for heading, block in blocks(text[start:end]):
        if heading is not None and normalise(heading) in seen:
            dropped.append(heading)
        else:
            kept.append(block.rstrip())

    if not dropped:
        return text, []

    body = "\n\n".join(b for b in kept if b.strip())
    return text[:start] + ("\n\n" + body + "\n\n" if body else "\n\n") + text[end:], dropped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True,
                    help="the tag whose changelog is already published")
    ap.add_argument("--explain", action="store_true",
                    help="report what would go, without writing")
    args = ap.parse_args()

    # Explicit UTF-8 both ways. The changelog is full of em dashes and the
    # platform default is not UTF-8 everywhere; a silent transcode here would
    # corrupt the file this whole pipeline reads.
    text = CHANGELOG.read_text(encoding="utf-8")
    if unreleased_span(text) is None:
        print("no '## Unreleased' section; nothing to prune")
        return 0

    new, dropped = prune(text, published(args.base))
    for h in dropped:
        print(f"already in {args.base}: {h}")
    if not dropped:
        print(f"nothing in '## Unreleased' was published in {args.base}")

    if not args.explain and new != text:
        CHANGELOG.write_text(new, encoding="utf-8")
        print(f"pruned {len(dropped)} block(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
