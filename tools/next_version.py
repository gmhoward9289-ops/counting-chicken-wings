"""What number should this merge release, decided at merge time.

    python tools/next_version.py                 # print the number, or nothing
    python tools/next_version.py --explain
    python tools/next_version.py --apply         # write CHANGELOG + pyproject

WHY THE NUMBER IS DECIDED HERE. `docs/VERSIONING.md` already says to pick the
release number last, in one commit right before merging. That rule exists
because several branches are open at once and they release the same day: on
2026-07-30 a seasonality branch was numbered v1.5.0, another session released
v1.5.0 while it was in review, it was renumbered v1.6.0, and that was taken
too. It shipped as v1.7.0, having cost two rebases and two sweeps of the
version string through three files.

A rule that asks people to time a commit correctly is a rule that gets lost the
moment two sessions merge within a minute of each other. So the number is not
written on the branch at all. A branch writes `## Unreleased` and nothing else;
whichever merge lands first takes the next number, and the second merge
computes its own against a base that already moved. Two branches cannot claim
one number because neither branch names a number.

It also closes a gap that bit twice within an hour. A workflow that reads
`pyproject.toml` only ever releases the version master CURRENTLY declares, so
when v1.11.0 landed on top of v1.10.0 before the release job ran, v1.10.0 was
skipped for good -- as v1.9.1 had been an hour earlier. Deriving the number
from the tag that exists, at the moment of merge, means every merge that
carries an `## Unreleased` section gets its own release and none can be
overtaken.

WHICH DIGIT MOVES is not decided here. `release_check.py` already answers that
by diffing the corpus -- new tables and domains take the second digit, more
rows of an existing kind take the third -- and this only turns its verdict into
a number. The scheme is MAJOR.MINOR.MINOR, not SemVer: the third digit is not
a patch level and routinely carries data.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
PYPROJECT = ROOT / "pyproject.toml"

UNRELEASED = "## Unreleased"

# release_check's verdicts, weakest first. A merge that is worth a changelog
# entry is worth a release, so `none` is floored to `third` when there is one:
# the corpus can be untouched while the code, the docs or the frontend all
# moved, and "the numbers did not change" is not the same as "nothing shipped".
LEVELS = ("none", "third", "second", "major")


def unreleased(text: str | None = None) -> str | None:
    """The `## Unreleased` body, or None when there is nothing to release."""
    text = CHANGELOG.read_text() if text is None else text
    m = re.search(rf"^{re.escape(UNRELEASED)}\s*$(.*?)(?=^## |\Z)",
                  text, re.M | re.S)
    if not m:
        return None
    body = m.group(1).strip()
    return body or None


def bump(version: str, level: str) -> str:
    """Move one digit of MAJOR.MINOR.MINOR.

    Deliberately not SemVer arithmetic: the third digit is this project's
    second MINOR, not a patch level, and calling it one is how the old rule
    took the project 1.0.0 -> 1.7.0 in two days.
    """
    major, second, third = (int(p) for p in version.split("."))
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "second":
        return f"{major}.{second + 1}.0"
    if level == "third":
        return f"{major}.{second}.{third + 1}"
    raise ValueError(f"nothing to bump for level {level!r}")


# Version tags only. `--tags` alone takes the newest tag of ANY shape, so a
# marker tag (`snapshot/...`, `checkpoint/...`) pushed after the last release
# would become the base this counts from -- bumping against a commit nobody
# released, and saying nothing about it. docs/VERSIONING.md ("Tags that are
# not releases") states that both other call sites pass this; this is the
# third, added later, and it was the one that did not.
VERSION_TAG_MATCH = ("--match", "v[0-9]*", "--exclude", "*-*")


def latest_tag() -> str | None:
    out = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", *VERSION_TAG_MATCH],
        capture_output=True, text=True, cwd=ROOT)
    return out.stdout.strip() or None


def required_level(base: str) -> tuple[str, list[str]]:
    """What `release_check.py` says this change requires, and why."""
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "release_check.py"),
         "--json", "--base", base],
        capture_output=True, text=True, cwd=ROOT)
    if out.returncode not in (0, 1) or not out.stdout.strip():
        raise SystemExit(f"release_check failed: {out.stderr.strip()[:300]}")

    return parse_verdict(out.stdout)


def parse_verdict(stdout: str) -> tuple[str, list[str]]:
    """`required` and its reasons, out of release_check's --json stream.

    That stream is NOT a single JSON document: on a FAIL verdict the object is
    followed by a human line, so `json.loads` raises "Extra data".

    FAIL is the normal case here rather than the exception, which is worth
    stating plainly. release_check derives `actual` by diffing pyproject
    against the base tag, and under this scheme a branch never bumps pyproject
    -- so `actual` is always "none" and every verdict reads as failing. Only
    `required` is read: this runs BEFORE the number is applied and asks what
    the diff needs, not whether the tree already says so. The workflow still
    runs release_check as a real gate, after --apply, when there is an actual
    bump to compare against.
    """
    d, _ = json.JSONDecoder().raw_decode(stdout[stdout.index("{"):])
    return d.get("required", "none"), d.get("reasons", [])


def rewrite(version: str, text: str, today: str) -> str:
    """Give the `## Unreleased` section its number and its date."""
    return re.sub(rf"^{re.escape(UNRELEASED)}\s*$",
                  f"## v{version} — {today}", text, count=1, flags=re.M)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", help="tag to compare against (default: latest)")
    ap.add_argument("--explain", action="store_true")
    ap.add_argument("--apply", action="store_true",
                    help="write the number into CHANGELOG.md and pyproject.toml")
    args = ap.parse_args()

    body = unreleased()
    if not body:
        if args.explain:
            print("no '## Unreleased' section with content; nothing to release")
        return 1

    base = args.base or latest_tag()
    if not base:
        raise SystemExit("no tag to count from; tag a first release by hand")

    level, reasons = required_level(base)
    if level == "none":
        # See LEVELS: a changelog entry means something shipped.
        level = "third"
        reasons = reasons + ["corpus unchanged, but there is a changelog entry"]

    version = bump(base.lstrip("v"), level)

    if args.explain:
        print(f"base:     {base}")
        print(f"required: {level}")
        for r in reasons:
            print(f"  - {r}")
        print(f"next:     v{version}")
    else:
        print(version)

    if args.apply:
        today = dt.date.today().isoformat()
        CHANGELOG.write_text(rewrite(version, CHANGELOG.read_text(), today))
        PYPROJECT.write_text(re.sub(
            r'^version\s*=\s*"[^"]+"', f'version = "{version}"',
            PYPROJECT.read_text(), count=1, flags=re.M))
        print(f"applied v{version}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
