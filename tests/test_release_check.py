"""The version-bump rule, executed rather than remembered.

docs/VERSIONING.md versions by CAPABILITY, not volume, and until now nothing
enforced it -- CI checked only that a tag matched pyproject.toml. These tests
cover the decision logic directly, without the ~90s corpus builds the real
script does, so the rule itself is cheap to keep honest.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import release_check as rc  # noqa: E402


def snap(tables, kinds=None, counts=None):
    kinds = kinds or {}
    counts = counts or {t: 1 for t in tables}
    return {"tables": list(tables), "kinds": kinds, "counts": counts}


BASE = snap(
    ["source", "domain", "species", "product"],
    kinds={"domain": ["poultry"], "species": ["broiler"],
           "product": ["whole_wing"]},
    counts={"source": 40, "domain": 1, "species": 1, "product": 1},
)


# ---------------------------------------------------------------------------
# New KIND -> minor
# ---------------------------------------------------------------------------

def test_a_new_table_is_minor():
    head = snap(
        BASE["tables"] + ["output_stat_year"],
        kinds=BASE["kinds"],
        counts={**BASE["counts"], "output_stat_year": 75},
    )
    need, why = rc.required_bump(BASE, head, {"whole_wing": "6 12"}, {"whole_wing": "6 12"})
    assert need == "second"
    assert "output_stat_year" in why[0]  # names the table


@pytest.mark.parametrize("table,slug", [
    ("domain", "horticulture"),
    ("species", "saffron_crocus"),
    ("product", "saffron_gram"),
])
def test_a_new_kind_row_is_minor(table, slug):
    """A new domain, species or product is a question you could not ask
    before. That is the definition of new capability here."""
    kinds = {k: list(v) for k, v in BASE["kinds"].items()}
    kinds[table] = kinds[table] + [slug]
    head = snap(BASE["tables"], kinds=kinds,
                counts={**BASE["counts"], table: 2})
    need, why = rc.required_bump(BASE, head, {"whole_wing": "6 12"}, {"whole_wing": "6 12"})
    assert need == "second"
    assert slug in why[0]


# ---------------------------------------------------------------------------
# More of the same -> patch. The case the old rule got wrong.
# ---------------------------------------------------------------------------

def test_more_rows_of_an_existing_kind_is_only_patch():
    """Another country's series landing in a table that already exists
    answers nothing new, however many rows it is. This is what took the
    project 1.0.0 -> 1.7.0 in two days under the old rule."""
    head = snap(BASE["tables"], kinds=BASE["kinds"],
                counts={**BASE["counts"], "source": 49})
    need, why = rc.required_bump(BASE, head, {"whole_wing": "6 12"}, {"whole_wing": "6 12"})
    assert need == "third"
    assert "source" in why[0]  # names the table whose count moved


def test_an_identical_corpus_needs_nothing():
    need, _ = rc.required_bump(BASE, BASE, {"whole_wing": "6 12"}, {"whole_wing": "6 12"})
    assert need == "none"


# ---------------------------------------------------------------------------
# The published answer moving -> minor, whatever else did or did not change
# ---------------------------------------------------------------------------

def test_a_moved_answer_is_minor_even_with_an_identical_corpus():
    """The signal the other two cannot see: it fires on a code change as
    readily as a data one, with the schema and every row count untouched.

    Uses saffron_gram because a per-product answer is exactly what the
    single-product first version could not have seen."""
    need, why = rc.required_bump(BASE, BASE, {"saffron_gram": "150 150"}, {"saffron_gram": "150 1"})
    assert need == "second"
    assert "saffron_gram" in why[0]  # names the product whose answer moved


def test_an_unavailable_answer_does_not_invent_a_reason():
    """A product absent from the base -- an older tag, or one added by this
    very diff -- must read as "not comparable", never as "the answer changed".
    New products are already reported by the new-kind check."""
    need, _ = rc.required_bump(BASE, BASE, {}, {"whole_wing": "6 12"})
    assert need == "none"


# ---------------------------------------------------------------------------
# Comparing required against actual
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("old,new,expect", [
    ("1.7.0", "1.7.0", "none"),
    ("1.7.0", "1.7.1", "third"),
    ("1.7.0", "1.8.0", "second"),
    ("1.7.0", "2.0.0", "major"),
])
def test_actual_bump_reads_the_version_pair(old, new, expect):
    assert rc.actual_bump(old, new) == expect


def test_the_vocabulary_matches_the_documented_scheme():
    """The scheme is MAJOR.MINOR.MINOR, not SemVer, so the verdicts name the
    DIGIT that moves. "patch" and "minor" would import the SemVer meanings the
    project deliberately dropped -- SemVer's third component promises "fixes
    only, no new capability", and ours routinely ships thousands of rows.

    Pinned as a test because a doc and a tool that disagree on vocabulary is
    how the last mismatch survived three commits."""
    assert set(rc.RANK) == {"none", "third", "second", "major"}
    assert rc.RANK["none"] < rc.RANK["third"] < rc.RANK["second"] < rc.RANK["major"]


def test_major_is_rankable_but_never_returned():
    """`required_bump` can return none/third/second and never "major", because
    the MAJOR criterion -- the MEANING of a published figure changing rather
    than its value -- is not mechanically detectable.

    It stays in RANK so that a human who bumps MAJOR still satisfies
    RANK[got] >= RANK[need]. Over-bumping must always pass."""
    import inspect
    src = inspect.getsource(rc.required_bump)
    assert '"major"' not in src
    assert rc.RANK["major"] > rc.RANK["second"]


def test_over_bumping_is_allowed_and_under_bumping_is_not():
    """Deliberate asymmetry. Shipping a bigger bump than required is a
    judgement call; shipping a smaller one silently breaks the promise that
    the number means something."""
    assert rc.RANK["second"] >= rc.RANK["third"]      # second covers a third-digit need
    assert not rc.RANK["third"] >= rc.RANK["second"]  # third cannot cover second


def test_a_removed_table_is_not_silently_a_patch():
    """Retraction breaks an existing citation, which is the exact harm data
    versioning exists to signal."""
    head = snap([t for t in BASE["tables"] if t != "source"],
                kinds=BASE["kinds"],
                counts={k: v for k, v in BASE["counts"].items()
                        if k != "source"})
    need, why = rc.required_bump(BASE, head, {"whole_wing": "6 12"}, {"whole_wing": "6 12"})
    assert need == "second"
    assert "REMOVED" in why[0]


def test_removal_is_seen_even_when_rows_changed_elsewhere():
    """Ordering regression. With the volume branch checked first, a release
    that dropped a table AND changed rows anywhere else returned "third" and
    never mentioned the removal -- the row-count branch matched and won."""
    head = snap([t for t in BASE["tables"] if t != "source"],
                kinds=BASE["kinds"],
                counts={"domain": 1, "species": 1, "product": 9})
    need, why = rc.required_bump(BASE, head, {"whole_wing": "6 12"}, {"whole_wing": "6 12"})
    assert need == "second"
    assert any("REMOVED" in r for r in why), why


def test_a_removed_species_is_minor():
    kinds = {**BASE["kinds"], "species": []}
    head = snap(BASE["tables"], kinds=kinds,
                counts={**BASE["counts"], "species": 0})
    need, why = rc.required_bump(BASE, head, {"whole_wing": "6 12"}, {"whole_wing": "6 12"})
    assert need == "second"
    assert any("REMOVED" in r for r in why), why


def test_a_move_in_any_product_counts_not_just_wings():
    """The single-product first version watched `whole_wing` alone, so a
    regression confined to eggs or saffron registered as nothing at all."""
    for slug in ("table_egg", "saffron_gram", "boneless_wing"):
        need, why = rc.required_bump(
            BASE, BASE, {slug: "1 2 3"}, {slug: "1 2 4"})
        assert need == "second", slug
        assert slug in why[0]


def test_products_are_compared_only_where_both_sides_have_one():
    """Intersection, not union. A product added by this very diff has no base
    answer to differ from, and is already reported as a new kind."""
    moved = rc.answers_moved(
        {"whole_wing": "6 12"},
        {"whole_wing": "6 12", "saffron_gram": "150 150"})
    assert moved == []


def test_every_moved_product_is_named():
    moved = rc.answers_moved(
        {"a": "1", "b": "2", "c": "3"},
        {"a": "1", "b": "9", "c": "8"})
    assert moved == ["b", "c"]


# ---------------------------------------------------------------------------
# latest_tag() must see releases only
#
# `git describe --tags` returns the newest tag of ANY shape. Marker tags
# (`snapshot/...`) are deliberately cheap and expected to accumulate, and one
# sitting after the last release used to become the base for the whole bump
# check -- measuring the diff from a commit nobody released, and saying
# nothing about having done so.
# ---------------------------------------------------------------------------

def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", ".")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "f").write_text("one")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "one")
    _git(tmp_path, "tag", "-a", "v1.11.0", "-m", "release")
    return tmp_path


def test_latest_tag_ignores_a_marker_tag(repo, monkeypatch):
    (repo / "f").write_text("two")
    _git(repo, "commit", "-qam", "work after the release")
    _git(repo, "tag", "snapshot/demo")          # newer than v1.11.0

    monkeypatch.setattr(rc, "ROOT", repo)
    assert rc.latest_tag() == "v1.11.0"


def test_latest_tag_finds_a_tag_that_is_not_reachable_from_head(repo, monkeypatch):
    """The shape release.yml now produces, and the one `describe` cannot see.

    The release job commits the version bump and tags THAT commit without
    pushing it to the branch -- `protect-master` rejects the push. So the tag
    hangs off master rather than sitting on it. `git describe` answers "nearest
    tag reachable from HEAD" and would say v1.11.0 here forever, which would
    make every future release recompute the same number.
    """
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          capture_output=True, text=True, check=True).stdout.strip()
    (repo / "f").write_text("release commit, never merged")
    _git(repo, "commit", "-qam", "Release v1.12.0")
    _git(repo, "tag", "-a", "v1.12.0", "-m", "release")
    _git(repo, "reset", "-q", "--hard", head)   # the branch never took it

    unreachable = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "v1.12.0^{commit}", "HEAD"],
        cwd=repo).returncode != 0
    assert unreachable, "the fixture must reproduce an off-branch tag"

    monkeypatch.setattr(rc, "ROOT", repo)
    assert rc.latest_tag() == "v1.12.0"


def test_latest_tag_orders_by_version_not_by_string(repo, monkeypatch):
    """v1.9.0 must not outrank v1.11.0. Plain sorting says it does."""
    for tag in ("v1.10.0", "v1.9.1"):       # v1.11.0 comes from the fixture
        _git(repo, "tag", "-a", tag, "-m", "release")

    monkeypatch.setattr(rc, "ROOT", repo)
    assert rc.latest_tag() == "v1.11.0"


def test_latest_tag_ignores_a_prerelease_tag(repo, monkeypatch):
    (repo / "f").write_text("three")
    _git(repo, "commit", "-qam", "more work")
    _git(repo, "tag", "-a", "v1.12.0-rc.1", "-m", "preview")

    monkeypatch.setattr(rc, "ROOT", repo)
    assert rc.latest_tag() == "v1.11.0"
