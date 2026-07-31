"""Does the version bump match what actually changed?

    python tools/release_check.py                 # HEAD against the latest tag
    python tools/release_check.py --base v1.6.0
    python tools/release_check.py --explain       # show the comparison, never fail

docs/VERSIONING.md says to version by CAPABILITY, not by volume. That rule is
correct and completely unenforced: CI checks only that a tag matches
pyproject.toml, so nothing notices when a release adds a domain and moves only
the third digit, or renames a comment and moves the second.

VOCABULARY. The scheme is MAJOR.MINOR.MINOR, not SemVer, so the verdicts here
are "second" and "third" after the digit that moves -- not "minor" and "patch",
which would import the SemVer meaning the project deliberately dropped.
"major" keeps its name because MAJOR did not change.

An unenforced convention drifts fastest when several people are cutting
releases, which is exactly this project's situation. So this executes the rule
instead of asking anyone to remember it.

WHAT IT COMPARES, and why these three

  1. STRUCTURE -- tables, and the domain/species/product rows. A new KIND of
     thing is the definition of new capability: you can ask a question that
     did not exist before. SECOND digit required.

  2. VOLUME -- row counts of tables that already existed. More rows of a kind
     we already had answers nothing new, however many rows. THIRD is enough.
     This is the case the old rule got wrong and inflated 1.0.0 to 1.7.0 in
     two days.

  3. THE PUBLISHED ANSWER -- `wings count 12` for EVERY active product, run
     against both corpora. If floor, required or distinct moved for any of
     them, someone's existing citation is now wrong, and that is the whole
     reason data is versioned here at all. SECOND digit required regardless
     of how small the diff was.

The third is the one worth having, because it is the rule's own criterion
rather than a proxy for it: it fires on a code change as readily as a data
one, which neither of the others can do.

WHAT IT DOES NOT COVER, because this was twice over-claimed before it was
measured. It runs the CLI, so an API-only regression is invisible to it. The
saffron ceiling bug is the worked example and it fails on both counts: the
faulty ceiling was served by /api/calculate while the CLI printed the right
number, AND saffron was a brand-new product with no previous answer to differ
from. That bug is caught by tests/test_api.py, not by this. Cite it as the
motivation for watching published answers, never as something this would have
caught.

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
# the world a second-digit bump and a changelog line, however it moved.
HEADLINE = ["count", "12"]


def sh(*args: str, cwd: Path | None = None, env: dict | None = None) -> str:
    return subprocess.run(
        args, cwd=cwd, env=env, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def latest_tag() -> str:
    # The highest RELEASED version, by version order.
    #
    # Two things are being avoided, and they are separate. `--tags` alone takes
    # the newest tag of ANY shape, so a marker tag (`snapshot/...`) after the
    # last release would become the base and the diff would be measured from a
    # commit nobody released. Hence the `v[0-9]*` filter and the dash exclusion.
    #
    # `git describe` is avoided for a second reason: it answers "the nearest tag
    # REACHABLE from HEAD", and release tags are no longer reachable from
    # `master`. release.yml commits the version bump and tags THAT commit
    # without pushing it to the branch, because `protect-master` rejects the
    # push. `describe` on master would keep naming the last tag that predates
    # the scheme, so every bump check would measure from a base several releases
    # stale. Version order does not care what is reachable.
    tags = sh("git", "tag", "--list", "v[0-9]*", "--sort=-v:refname", cwd=ROOT)
    for line in tags.splitlines():
        tag = line.strip()
        if tag and "-" not in tag:
            return tag
    raise SystemExit(
        "no version tags in this clone. `actions/checkout` needs "
        "`fetch-depth: 0` (or `fetch-tags: true`) for this check to mean "
        "anything -- see the note in ci.yml about the bump check that passed "
        "on every tag it ever ran on because the tags were not there.")


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


def products_in(db: Path) -> list[str]:
    conn = sqlite3.connect(db)
    try:
        return sorted(r[0] for r in conn.execute(
            "SELECT slug FROM product WHERE EXISTS ("
            "  SELECT 1 FROM species s WHERE s.id = product.species_id"
            "    AND s.active = 1)"))
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def headline(tree: Path, db: Path) -> dict[str, str]:
    """Every active product's answer at this ref, keyed by slug.

    ONE PRODUCT WAS NOT ENOUGH. The first version ran only `wings count 12`,
    so a regression confined to eggs, boneless wings or either saffron product
    would not have registered at all -- on a project whose entire direction is
    adding subjects, watching one of them is watching the shrinking majority
    of nothing.

    Asking every active product means a corpus that gains products gains
    coverage automatically, with no list to maintain.

    Missing keys are not failures: a product that does not exist at the base
    ref is already reported by the new-kind check, and an older CLI that
    rejects these flags simply yields nothing for that product.
    """
    env = dict(os.environ, PYTHONPATH=str(tree / "src"))
    out: dict[str, str] = {}
    for slug in products_in(db):
        try:
            text = subprocess.run(
                [sys.executable, "-m", "counting_chicken_wings.cli",
                 *HEADLINE, "--product", slug, "--db", str(db),
                 "--quiet", "--no-facts", "--no-colour"],
                cwd=tree, env=env, check=True,
                capture_output=True, text=True, timeout=120,
            ).stdout
        except Exception:                           # noqa: BLE001
            continue
        # Keep only the numbers. Prose gets reworded constantly, and a
        # reworded sentence is not a changed answer.
        nums = re.findall(r"\d+\.?\d*", text)
        if nums:
            out[slug] = " ".join(nums)
    return out


def answers_moved(base: dict[str, str], head: dict[str, str]) -> list[str]:
    """Products whose answer differs, compared only where both sides have one."""
    return sorted(s for s in set(base) & set(head) if base[s] != head[s])


def required_bump(base: dict, head: dict,
                  base_answers: dict[str, str],
                  head_answers: dict[str, str]) -> tuple[str, list[str]]:
    """The smallest bump this diff justifies, with the reasons."""
    reasons: list[str] = []

    new_tables = sorted(set(head["tables"]) - set(base["tables"]))
    if new_tables:
        reasons.append(f"new table(s): {', '.join(new_tables)}")

    for t in KIND_TABLES:
        added = sorted(set(head["kinds"].get(t, [])) - set(base["kinds"].get(t, [])))
        if added:
            reasons.append(f"new {t}(s): {', '.join(added)}")

    for slug in answers_moved(base_answers, head_answers):
        reasons.append(
            f"the published answer moved for {slug}: "
            f"[{base_answers[slug]}] -> [{head_answers[slug]}]")

    # Removal is checked BEFORE volume, and the order is load-bearing. Written
    # the other way round, a release that dropped a table AND changed rows
    # anywhere else returned "third" and never mentioned the removal -- the
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
        return "second", reasons

    # Volume only.
    grew = {t: (base["counts"].get(t, 0), head["counts"][t])
            for t in head["tables"]
            if head["counts"][t] != base["counts"].get(t, 0)}
    if grew:
        detail = ", ".join(f"{t} {a}->{b}" for t, (a, b) in sorted(grew.items()))
        return "third", [f"rows changed, no new kind: {detail}"]

    return "none", ["corpus identical"]


def actual_bump(old: str, new: str) -> str:
    o = [int(x) for x in old.split(".")[:3]]
    n = [int(x) for x in new.split(".")[:3]]
    if n[0] != o[0]:
        return "major"
    if n[1] != o[1]:
        return "second"
    if n[2] != o[2]:
        return "third"
    return "none"


RANK = {"none": 0, "third": 1, "second": 2, "major": 3}


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

        moved = answers_moved(base_ans, head_ans)
        if a.json:
            print(json.dumps({
                "base": base_ref, "required": need, "actual": got,
                "ok": ok, "reasons": reasons, "answers_moved": moved,
                "products_compared": sorted(set(base_ans) & set(head_ans)),
                "base_version": version_of(base_ref),
                "head_version": version_of(),
            }, indent=1))
        else:
            print(f"release-check: {base_ref} -> working tree\n")
            print(f"  tables      {len(base_snap['tables'])} -> "
                  f"{len(head_snap['tables'])}")
            shared = sorted(set(base_ans) & set(head_ans))
            if shared:
                print(f"  answers     {len(shared)} product(s) compared, "
                      f"{len(moved) or 'none'} moved")
            else:
                print("  answers     not comparable at this base "
                      "(CLI differs); structure and volume only")
            print()
            for r in reasons:
                print(f"  - {r}")
            print(f"\n  => {need.upper()} required. "
                  f"{version_of(base_ref)} -> {version_of()} is {got.upper()}.")

        # The published answer moving is worth surfacing on its own, whatever
        # the bump verdict is. A PR that moves it is not doing anything wrong
        # -- a better loss factor SHOULD move the number, that is the job --
        # but it must not move silently, because every citation someone has
        # already made against the old value is now stale.
        #
        # Warning rather than failure, deliberately. Failing would train people
        # to route around the check; a visible annotation makes a human decide
        # whether the changelog owes the world an old -> new line. (The bump
        # verdict below may still fail on its own -- these are separate.)
        if moved:
            detail = "; ".join(
                f"{s}: [{base_ans[s]}] -> [{head_ans[s]}]" for s in moved)
            note = (f"published answer moved between {base_ref} and this tree "
                    f"for {len(moved)} product(s) -- {detail}. If intended, "
                    f"the changelog owes an old -> new line.")
            if os.environ.get("GITHUB_ACTIONS"):
                print(f"::warning::{note}")
            else:
                print(f"\nNOTE: {note}")

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
