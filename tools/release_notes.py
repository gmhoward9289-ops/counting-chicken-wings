"""The release notes for a version, taken from the changelog that already has them.

    python tools/release_notes.py                  # notes for pyproject's version
    python tools/release_notes.py --version 1.9.0
    python tools/release_notes.py --title          # just the release title
    python tools/release_notes.py --check          # is this version tagged?

WHY THIS EXISTS. Releasing was the one step of this project's pipeline with no
automation, and it silently became the step that does not happen. v1.2.0
through v1.7.0 sat untagged until someone backfilled six releases in one batch;
v1.9.0 was tagged by hand three hours after it merged; v1.9.1 and v1.10.0 were
both merged, both version-bumped, and neither tagged at all.

That is worse than untidy. `ci.yml`'s `version-consistency` job is gated on
`refs/tags/v*`, so it is the tag push that runs the ONLY check comparing the
released number against `pyproject.toml`. No tag means that check never runs,
which means `docs/VERSIONING.md`'s rules -- version by capability, set the
number at merge -- are enforced by nothing but memory, on a repo where several
sessions cut releases the same day.

So: notes come from `CHANGELOG.md` rather than from generated commit subjects.
The changelog is written deliberately, explains WHY a number moved, and is
already the artefact a reader is pointed at. Generating notes from commit
titles would replace something considered with something mechanical, and would
also make the release disagree with the changelog it duplicates.

FAILING LOUDLY IS THE POINT. If a version has no changelog section this exits
non-zero rather than publishing an empty release. A release with no notes is
indistinguishable from a release nobody bothered to describe, and the whole
argument for this project is that unsourced things must look unsourced.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
PYPROJECT = ROOT / "pyproject.toml"


def project_version(text: str | None = None) -> str:
    """The version `pyproject.toml` declares.

    Read from the file rather than from installed metadata: an editable
    install reports whatever it was last installed at, which is exactly the
    stale answer that makes a release land under the wrong number.
    """
    text = PYPROJECT.read_text() if text is None else text
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("no version in pyproject.toml")
    return m.group(1)


def section(version: str, text: str | None = None) -> str:
    """The changelog body for `version`, without its heading.

    Headings look like `## v1.10.0 — 2026-07-30`; the date is not matched, so
    a correction to a release date does not break the lookup.
    """
    text = CHANGELOG.read_text() if text is None else text
    pattern = rf"^## v{re.escape(version)}\b.*?$(.*?)(?=^## |\Z)"
    m = re.search(pattern, text, re.M | re.S)
    if not m:
        raise SystemExit(
            f"no CHANGELOG section for v{version}. Write the section before "
            "releasing -- an empty release is worse than a late one.")
    body = m.group(1).strip()
    if not body:
        raise SystemExit(f"CHANGELOG section for v{version} is empty")
    return body


def title(version: str, body: str) -> str:
    """`vX.Y.Z — what changed`, matching the titles already on the releases page.

    Two shapes appear in this changelog and both are honest, so both are
    handled rather than one being reformatted to suit the parser:

      * a summary paragraph (v1.9.0 opens "Maple syrup: the third domain...")
      * a `###` subheading first (v1.10.0 opens "### A/B harness for the frontend")

    A release whose body starts with a subheading has no one-line summary to
    borrow, and inventing one here would put words in the changelog's mouth.

    The prose case joins the whole paragraph before splitting on sentences.
    CHANGELOG.md is hard-wrapped at ~76 columns, so reading one LINE gets a
    title chopped wherever the wrap happened to fall -- v1.9.0 came out as
    "Maple syrup: the third domain, and the first individual that survives
    being", which stops mid-clause and reads as a truncation bug on the
    releases page.
    """
    para: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            if para:
                break          # end of the first paragraph
            continue           # leading blank lines
        if line.startswith("#"):
            if para:
                break
            return f"v{version} — {line.lstrip('#').strip()}"
        para.append(line)

    if not para:
        return f"v{version}"
    # Keep the first sentence, and drop a trailing full stop so it reads as a
    # title rather than as a sentence that lost its paragraph.
    first = re.split(r"(?<=[.!?])\s", " ".join(para))[0].strip()
    return f"v{version} — {first.rstrip('.')}"


def tag_exists(version: str) -> bool:
    """Does `vX.Y.Z` already exist on the remote?

    Asks the remote, not the local clone. A CI runner's checkout may not have
    fetched tags, and a local clone can hold a tag that was never pushed --
    which is precisely the state this whole tool exists to stop happening.
    """
    out = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", f"refs/tags/v{version}"],
        capture_output=True, text=True, cwd=ROOT)
    return bool(out.stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", help="default: whatever pyproject declares")
    ap.add_argument("--title", action="store_true", help="print the title only")
    ap.add_argument("--check", action="store_true",
                    help="exit 0 if the version still needs a tag, 1 if tagged")
    args = ap.parse_args()

    version = args.version or project_version()

    if args.check:
        if tag_exists(version):
            print(f"v{version} already tagged")
            return 1
        # Resolve the notes even though they are not printed: a version that
        # cannot be described should fail here, in the check, rather than
        # halfway through a release.
        section(version)
        print(f"v{version} needs a tag")
        return 0

    body = section(version)
    print(title(version, body) if args.title else body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
