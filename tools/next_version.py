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

WHICH DIGIT MOVES is answered by `release_check.py`, which diffs the corpus --
new tables and domains take the second digit, more rows of an existing kind
take the third -- and by the branch, which may RAISE that verdict and may not
lower it. The scheme is MAJOR.MINOR.MINOR, not SemVer: the third digit is not
a patch level and routinely carries data.

WHY A BRANCH GETS A SAY AT ALL. `release_check` diffs the corpus and the
published answer, and `docs/VERSIONING.md` says outright that a new view,
endpoint or CLI flag "takes the second digit under the rule and is invisible
to it". So the automated verdict is a FLOOR, not an answer, and until now
nothing could raise it: v1.15.1 shipped an endpoint and a database view under
a third-digit bump because there was no way to say otherwise. MAJOR was worse
than under-reported -- it was unreachable, since `release_check` never returns
it and this had no other input.

The declaration is a LEVEL, never a number, and that distinction is the whole
design. A number on a branch has to hope nobody takes it during review, which
is how v1.5.0 and v1.6.0 were both taken out from under a branch on
2026-07-30. Two branches may both declare `second` and neither collides,
because a level is relative and gets resolved against the tag that exists at
merge. This is the same rule changesets and release-please follow.

WHERE IT IS WRITTEN. One file per branch under `.changes/`, carrying its own
changelog prose and an optional `bump:`. Branches used to append to a single
`## Unreleased` section, which meant every second branch open at once rebased
through a conflict in the same paragraph -- on a repo where eight sessions are
routinely live. A file per branch cannot conflict with another branch's file.

`## Unreleased` is still read, so the two mechanisms overlap rather than
switching over: a branch already in flight keeps working, and a release that
finds both merges both.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
PYPROJECT = ROOT / "pyproject.toml"
CHANGES = ROOT / ".changes"

UNRELEASED = "## Unreleased"

# release_check's verdicts, weakest first. A merge that is worth a changelog
# entry is worth a release, so `none` is floored to `third` when there is one:
# the corpus can be untouched while the code, the docs or the frontend all
# moved, and "the numbers did not change" is not the same as "nothing shipped".
LEVELS = ("none", "third", "second", "major")
RANK = {level: i for i, level in enumerate(LEVELS)}

# What a branch may declare. `none` is deliberately absent: a changeset file
# exists because something shipped, and declaring that nothing did would be a
# way to talk the floor DOWN, which no declaration is allowed to do.
DECLARABLE = ("third", "second", "major")


class Change:
    """One branch's changelog entry, and the level it claims."""

    def __init__(self, path: Path, level: str | None, body: str):
        self.path, self.level, self.body = path, level, body

    @property
    def name(self) -> str:
        return self.path.name


def parse_change(text: str, name: str = "<changeset>") -> tuple[str | None, str]:
    """Split a changeset into its declared level and its prose.

    Frontmatter is optional -- a file that only carries prose declares
    nothing and leaves the computed floor alone, which is the common case.

    Every failure here is LOUD, and deliberately so. A declaration that is
    silently ignored is worse than no declaration: the release ships under a
    number somebody thinks they corrected. `bumps:` for `bump:` is the typo
    this is really guarding, and it costs nothing to catch.
    """
    m = re.match(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?", text, re.S)
    if not m:
        return None, text.strip()

    level = None
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip().strip("'\"")
        if key != "bump":
            raise SystemExit(
                f"{name}: unknown frontmatter key {key!r}. "
                f"The only key is 'bump', one of {', '.join(DECLARABLE)}.")
        if re.match(r"^v?\d+(\.\d+)", value):
            # The one mistake worth its own message, because it is the whole
            # reason branches stopped naming versions in the first place.
            raise SystemExit(
                f"{name}: bump is a LEVEL, not a number -- got {value!r}. "
                f"Use one of {', '.join(DECLARABLE)}. A branch that names a "
                "number races every other branch open at the same time; "
                "v1.5.0 and v1.6.0 were both taken out from under a branch "
                "in review on 2026-07-30.")
        if value not in DECLARABLE:
            raise SystemExit(
                f"{name}: bump must be one of {', '.join(DECLARABLE)}, "
                f"got {value!r}.")
        level = value

    return level, text[m.end():].strip()


def read_changes() -> list[Change]:
    """Every changeset on disk, in a deterministic order.

    Sorted by filename so the assembled section reads the same way whoever
    runs it -- two entries landing in one release must not swap places
    between a dry run and the real one.
    """
    if not CHANGES.is_dir():
        return []
    out = []
    for path in sorted(CHANGES.glob("*.md")):
        if path.name.upper() == "README.MD":
            continue          # the convention's own documentation, not an entry
        level, body = parse_change(path.read_text(), path.name)
        out.append(Change(path, level, body))
    return out


def declared_level(changes: list[Change]) -> tuple[str | None, list[str]]:
    """The strongest level any branch in this release declared, and who said so.

    Strongest rather than first: two branches merging into one release each
    describe their own change, and the release is the union of both. A
    second-digit change does not become a third-digit one by travelling
    alongside a typo fix.
    """
    reasons, best = [], None
    for c in changes:
        if not c.level:
            continue
        reasons.append(f"{c.name} declares {c.level}")
        if best is None or RANK[c.level] > RANK[best]:
            best = c.level
    return best, reasons


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


def stage_consumed(changes: list[Change]) -> None:
    """Stage the changesets `--apply` just deleted.

    A deletion has to be committed or it did not happen, and the release
    commit stages explicit pathspecs -- deliberately, so a stray file cannot
    be swept into a commit nobody reviews. That leaves a trap: the notes ship,
    the files stay on master, and the NEXT release publishes every one of them
    a second time.

    Rather than depend on the workflow naming a path that a future edit could
    drop, `--apply` stages its own deletions. The tool's contract becomes
    "after this, the tree is ready to commit", which is the property the
    caller actually wants.

    Best-effort: this also runs on a developer's machine, where the changesets
    may not be tracked yet and there may be no repository at all. A failure to
    stage is not a failure to apply -- the files really are gone either way.
    """
    for c in changes:
        subprocess.run(["git", "add", "--", str(c.path)],
                       cwd=ROOT, capture_output=True)


def resolve_level(computed: str, reasons: list[str],
                  changes: list[Change]) -> tuple[str, list[str], str | None]:
    """The level this release actually moves, after the branches have spoken.

    A branch may RAISE the computed floor and may never lower it, which is the
    property that makes the declaration safe to trust. `release_check` diffs
    the corpus and the published answer; a declaration is a claim about the
    part it is BLIND to -- a new view, endpoint or CLI flag -- and not a veto
    over the part it is not. Somebody who writes `third` on a branch that
    added a species has misread their own change, and the corpus diff is
    right.

    That direction is not new here either: `release_check` has always passed
    over-bumping and failed under-bumping, for the same reason. Shipping a
    bigger number than required is a judgement call; shipping a smaller one
    silently breaks the promise that the number means something.

    Returns the level, the reasons for `--explain`, and a warning to print
    when a declaration was overruled.
    """
    declared, why = declared_level(changes)
    if not declared:
        return computed, reasons, None
    if RANK[declared] > RANK[computed]:
        return declared, reasons + why, None
    if RANK[declared] < RANK[computed]:
        note = (f"declared {declared}, but the corpus diff requires "
                f"{computed}; releasing as {computed}")
        return computed, reasons + why + [note], note
    return computed, reasons + why, None


def rewrite(version: str, text: str, today: str) -> str:
    """Give the `## Unreleased` section its number and its date."""
    return re.sub(rf"^{re.escape(UNRELEASED)}\s*$",
                  f"## v{version} — {today}", text, count=1, flags=re.M)


def splice(version: str, text: str, today: str, bodies: list[str]) -> str:
    """Write a release section carrying every changeset's prose.

    Two shapes, because both can be true at once during the overlap:

      * a `## Unreleased` section exists -- replace it wholesale, so a branch
        still using the old mechanism and a branch using `.changes/` land in
        ONE section rather than two claiming the same number.
      * no such section -- insert a new one directly under `# Changelog`.

    `rewrite` above still handles the legacy-only case untouched, so a release
    with no changesets produces byte-identical output to before this existed.
    """
    body = "\n\n".join(b.strip() for b in bodies if b.strip()).strip()
    section = f"## v{version} — {today}\n\n{body}\n"

    pattern = rf"^{re.escape(UNRELEASED)}\s*$(.*?)(?=^## |\Z)"
    if re.search(pattern, text, re.M | re.S):
        return re.sub(pattern, section + "\n", text, count=1, flags=re.M | re.S)

    m = re.search(r"\A(#\s+\S[^\n]*\n)", text)
    if not m:
        raise SystemExit("CHANGELOG.md has no '# ' title to insert under")
    return text[:m.end()] + "\n" + section + "\n" + text[m.end():].lstrip("\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", help="tag to compare against (default: latest)")
    ap.add_argument("--explain", action="store_true")
    ap.add_argument("--apply", action="store_true",
                    help="write the number into CHANGELOG.md and pyproject.toml")
    ap.add_argument("--lint", action="store_true",
                    help="validate .changes/ declarations and exit")
    args = ap.parse_args()

    # Parsing is the validation, and it raises. Doing it first means a typo in
    # a `bump:` fails on the branch that wrote it rather than three merges
    # later, in the middle of a release, where it is most expensive to find.
    changes = read_changes()
    if args.lint:
        for c in changes:
            print(f"{c.name}: {c.level or 'no declaration'}")
        print(f"{len(changes)} changeset(s) OK")
        return 0

    body = unreleased()
    if not body and not changes:
        if args.explain:
            print("no '## Unreleased' section and no .changes/ entries; "
                  "nothing to release")
        return 1

    base = args.base or latest_tag()
    if not base:
        raise SystemExit("no tag to count from; tag a first release by hand")

    level, reasons = required_level(base)
    if level == "none":
        # See LEVELS: a changelog entry means something shipped.
        level = "third"
        reasons = reasons + ["corpus unchanged, but there is a changelog entry"]

    level, reasons, warning = resolve_level(level, reasons, changes)
    if warning:
        # Visible, never fatal. The floor already protects the number, and
        # failing here would block a release over a judgement call.
        print(f"::warning::{warning}" if os.environ.get("GITHUB_ACTIONS")
              else f"NOTE: {warning}", file=sys.stderr)

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
        text = CHANGELOG.read_text()
        if changes:
            # Legacy section first: it was written before any of these files,
            # and a release holding both is one section, not two.
            CHANGELOG.write_text(splice(
                version, text, today,
                ([body] if body else []) + [c.body for c in changes]))
            for c in changes:
                c.path.unlink()
            stage_consumed(changes)
        else:
            CHANGELOG.write_text(rewrite(version, text, today))
        PYPROJECT.write_text(re.sub(
            r'^version\s*=\s*"[^"]+"', f'version = "{version}"',
            PYPROJECT.read_text(), count=1, flags=re.M))
        print(f"applied v{version}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
