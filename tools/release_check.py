"""Does the version bump match what actually changed?

    python tools/release_check.py                 # HEAD against the latest tag
    python tools/release_check.py --base v1.6.0
    python tools/release_check.py --explain       # show the comparison, never fail

docs/VERSIONING.md says to version by CAPABILITY, not by volume. That rule is
correct and completely unenforced: CI checks only that a tag matches
pyproject.toml, so nothing notices when a release adds a domain and calls it a
patch, or renames a comment and calls it a minor.

An unenforced convention drifts fastest when several people are cutting
releases, which is exactly this project's situation. So this executes the rule
instead of asking anyone to remember it.

WHAT IT COMPARES, and why these three

  1. STRUCTURE -- tables, and the domain/species/product rows. A new KIND of
     thing is the definition of new capability: you can ask a question that
     did not exist before. MINOR required.

  2. VOLUME -- row counts of tables that already existed. More rows of a kind
     we already had answers nothing new, however many rows. PATCH is enough.
     This is the case the old rule got wrong and inflated 1.0.0 to 1.7.0 in
     two days.

  3. THE PUBLISHED ANSWER -- `wings count 12`, run against BOTH corpora. If
     floor, required or distinct moved, someone's existing citation is now
     wrong, and that is the whole reason data is versioned here at all. MINOR
     required regardless of how small the diff was.

The third is the one worth having. It is the rule's own criterion, and it
catches things the other two cannot: the saffron ceiling bug changed a
published answer through a pure code change and shipped under no bump at all.

HOW THE OLD CORPUS IS BUILT

`git archive` the base tag into a temp directory and build there with
PYTHONPATH pointed at that tree, rather than checking anything out. The
working tree is never touched -- which matters because other sessions are
usually live in it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Tables whose rows ARE the taxonomy: a new row here is a new kind of thing,
# not more of an existing thing. Everything else is volume.
KIND_TABLES = ("domain", "species", "product")

# The question the project exists to answer. Any release that moves this owes
# the world a MINOR and a changelog line, however it moved.
HEADLINE = ["count", "12"]


def sh(*args: str, cwd: Path | None = None, env: dict | None = None) -> str:
    return subprocess.run(
        args, cwd=cwd, env=env, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def latest_tag() -> str:
    return sh("git", "describe", "--tags", "--abbrev=0", cwd=ROOT)


def version_of(ref: str | None = None) -> str:
    """The version pyproject declares, at a ref or in the working tree."""
    text = (sh("git", "show", f"{ref}:pyproject.toml", cwd=ROOT) if ref
            else (ROOT / "pyproject.toml").read_text())
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit(f"no version in pyproject.toml at {ref or 'HEAD'}")
    return m.group(1)


def build_corpus(ref: str | None, work: Path) -> tuple[Path, Path]:
    """Materialise a ref and build its database. Returns (tree, db).

    ref=None means the current working tree, used as-is so that uncommitted
    changes are what gets checked -- the point is to answer "may I release
    THIS", not "may I release what I last committed".
    """
    if ref is None:
        tree = ROOT
    else:
        tree = work / "base"
        tree.mkdir(parents=True)
        # git archive rather than checkout/worktree: no lock on the repo, and
        # nothing that another live session could collide with.
        tar = subprocess.run(["git", "archive", ref], cwd=ROOT,
                             check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", str(tree)], input=tar, check=True)

    db = work / f"{'head' if ref is None else 'base'}.db"
    env = dict(os.environ, PYTHONPATH=str(tree / "src"))
    subprocess.run(
        [sys.executable, "-m", "counting_chicken_wings.build", str(db)],
        cwd=tree, env=env, check=True, capture_output=True, text=True,
    )
    return tree, db


def snapshot(db: Path) -> dict:
    conn = sqlite3.connect(db)
    try:
        tables = sorted(
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")
        )
        counts, kinds = {}, {}
        for t in tables:
            counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            if t in KIND_TABLES:
                kinds[t] = sorted(
                    r[0] for r in conn.execute(f"SELECT slug FROM {t}"))
        return {"tables": tables, "counts": counts, "kinds": kinds}
    finally:
        conn.close()


def headline(tree: Path, db: Path) -> str | None:
    """`wings count 12` at this ref, as a comparable string.

    Returns None if it cannot be run -- an older tag whose CLI took different
    arguments is not a failure, it just means this signal is unavailable and
    the check falls back to structure and volume.
    """
    env = dict(os.environ, PYTHONPATH=str(tree / "src"))
    try:
        out = subprocess.run(
            [sys.executable, "-m", "counting_chicken_wings.cli",
             *HEADLINE, "--db", str(db), "--quiet", "--no-facts",
             "--no-colour"],
            cwd=tree, env=env, check=True,
            capture_output=True, text=True, timeout=120,
        ).stdout
    except Exception:                               # noqa: BLE001
        return None
    # Keep only the numbers. Prose gets reworded constantly and a reworded
    # sentence is not a changed answer.
    nums = re.findall(r"\d+\.?\d*", out)
    return " ".join(nums) if nums else None


def required_bump(base: dict, head: dict,
                  base_answer: str | None, head_answer: str | None) -> tuple[str, list[str]]:
    """The smallest bump this diff justifies, with the reasons."""
    reasons: list[str] = []

    new_tables = sorted(set(head["tables"]) - set(base["tables"]))
    if new_tables:
        reasons.append(f"new table(s): {', '.join(new_tables)}")

    for t in KIND_TABLES:
        added = sorted(set(head["kinds"].get(t, [])) - set(base["kinds"].get(t, [])))
        if added:
            reasons.append(f"new {t}(s): {', '.join(added)}")

    if base_answer and head_answer and base_answer != head_answer:
        reasons.append(
            f"the published answer moved: `wings {' '.join(HEADLINE)}` "
            f"gave [{base_answer}], now gives [{head_answer}]")

    # Removal is checked BEFORE volume, and the order is load-bearing. Written
    # the other way round, a release that dropped a table AND changed rows
    # anywhere else returned "patch" and never mentioned the removal -- the
    # volume branch matched first and won. Retraction breaks a citation
    # somebody already made, which is the exact harm this versioning exists to
    # signal, so it must not be reachable only when nothing else moved.
    gone = sorted(set(base["tables"]) - set(head["tables"]))
    if gone:
        reasons.append(f"table(s) REMOVED: {', '.join(gone)}")

    for t in KIND_TABLES:
        dropped = sorted(set(base["kinds"].get(t, [])) - set(head["kinds"].get(t, [])))
        if dropped:
            reasons.append(f"{t}(s) REMOVED: {', '.join(dropped)}")

    if reasons:
        return "minor", reasons

    # Volume only.
    grew = {t: (base["counts"].get(t, 0), head["counts"][t])
            for t in head["tables"]
            if head["counts"][t] != base["counts"].get(t, 0)}
    if grew:
        detail = ", ".join(f"{t} {a}->{b}" for t, (a, b) in sorted(grew.items()))
        return "patch", [f"rows changed, no new kind: {detail}"]

    return "none", ["corpus identical"]


def actual_bump(old: str, new: str) -> str:
    o = [int(x) for x in old.split(".")[:3]]
    n = [int(x) for x in new.split(".")[:3]]
    if n[0] != o[0]:
        return "major"
    if n[1] != o[1]:
        return "minor"
    if n[2] != o[2]:
        return "patch"
    return "none"


RANK = {"none": 0, "patch": 1, "minor": 2, "major": 3}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="release_check")
    p.add_argument("--base", help="tag or ref to compare against "
                                  "(default: latest tag)")
    p.add_argument("--explain", action="store_true",
                   help="report and always exit 0")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv if argv is not None else sys.argv[1:])

    base_ref = a.base or latest_tag()
    work = Path(tempfile.mkdtemp(prefix="release-check-"))
    try:
        base_tree, base_db = build_corpus(base_ref, work)
        head_tree, head_db = build_corpus(None, work)

        base_snap, head_snap = snapshot(base_db), snapshot(head_db)
        base_ans = headline(base_tree, base_db)
        head_ans = headline(head_tree, head_db)

        need, reasons = required_bump(base_snap, head_snap, base_ans, head_ans)
        got = actual_bump(version_of(base_ref), version_of())
        ok = RANK[got] >= RANK[need]

        if a.json:
            print(json.dumps({
                "base": base_ref, "required": need, "actual": got,
                "ok": ok, "reasons": reasons,
                "base_version": version_of(base_ref),
                "head_version": version_of(),
            }, indent=1))
        else:
            print(f"release-check: {base_ref} -> working tree\n")
            print(f"  tables      {len(base_snap['tables'])} -> "
                  f"{len(head_snap['tables'])}")
            if base_ans and head_ans:
                same = "unchanged" if base_ans == head_ans else "CHANGED"
                print(f"  wings {' '.join(HEADLINE):<6} {head_ans}  ({same})")
            else:
                print("  wings        not comparable at this base "
                      "(CLI differs); structure and volume only")
            print()
            for r in reasons:
                print(f"  - {r}")
            print(f"\n  => {need.upper()} required. "
                  f"{version_of(base_ref)} -> {version_of()} is {got.upper()}.")

        if ok:
            print("\nOK" if not a.json else "")
            return 0
        msg = (f"version bump is {got}, but this diff requires {need}")
        print(f"\nFAIL: {msg}")
        # GitHub renders this as an annotation on the run.
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error::{msg}. See docs/VERSIONING.md.")
        return 0 if a.explain else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
