"""The version-bump rule, executed rather than remembered.

docs/VERSIONING.md versions by CAPABILITY, not volume, and until now nothing
enforced it -- CI checked only that a tag matched pyproject.toml. These tests
cover the decision logic directly, without the ~90s corpus builds the real
script does, so the rule itself is cheap to keep honest.
"""

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
    need, why = rc.required_bump(BASE, head, "6 12", "6 12")
    assert need == "minor"
    assert "new table" in why[0]


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
    need, why = rc.required_bump(BASE, head, "6 12", "6 12")
    assert need == "minor"
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
    need, why = rc.required_bump(BASE, head, "6 12", "6 12")
    assert need == "patch"
    assert "no new kind" in why[0]


def test_an_identical_corpus_needs_nothing():
    need, _ = rc.required_bump(BASE, BASE, "6 12", "6 12")
    assert need == "none"


# ---------------------------------------------------------------------------
# The published answer moving -> minor, whatever else did or did not change
# ---------------------------------------------------------------------------

def test_a_moved_answer_is_minor_even_with_an_identical_corpus():
    """The signal the other two cannot see. The saffron ceiling bug changed a
    published answer through a pure CODE change and shipped under no bump at
    all -- structure and row counts were untouched."""
    need, why = rc.required_bump(BASE, BASE, "6 11.99997", "6 150")
    assert need == "minor"
    assert "published answer moved" in why[0]


def test_an_unavailable_answer_does_not_invent_a_reason():
    """An old tag whose CLI took different flags yields None, which must read
    as "signal unavailable", never as "the answer changed"."""
    need, _ = rc.required_bump(BASE, BASE, None, "6 12")
    assert need == "none"


# ---------------------------------------------------------------------------
# Comparing required against actual
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("old,new,expect", [
    ("1.7.0", "1.7.0", "none"),
    ("1.7.0", "1.7.1", "patch"),
    ("1.7.0", "1.8.0", "minor"),
    ("1.7.0", "2.0.0", "major"),
])
def test_actual_bump_reads_the_version_pair(old, new, expect):
    assert rc.actual_bump(old, new) == expect


def test_over_bumping_is_allowed_and_under_bumping_is_not():
    """Deliberate asymmetry. Shipping a bigger bump than required is a
    judgement call; shipping a smaller one silently breaks the promise that
    the number means something."""
    assert rc.RANK["minor"] >= rc.RANK["patch"]      # minor covers a patch need
    assert not rc.RANK["patch"] >= rc.RANK["minor"]  # patch cannot cover minor


def test_a_removed_table_is_not_silently_a_patch():
    """Retraction breaks an existing citation, which is the exact harm data
    versioning exists to signal."""
    head = snap([t for t in BASE["tables"] if t != "source"],
                kinds=BASE["kinds"],
                counts={k: v for k, v in BASE["counts"].items()
                        if k != "source"})
    need, why = rc.required_bump(BASE, head, "6 12", "6 12")
    assert need == "minor"
    assert "REMOVED" in why[0]


def test_removal_is_seen_even_when_rows_changed_elsewhere():
    """Ordering regression. With the volume branch checked first, a release
    that dropped a table AND changed rows anywhere else returned "patch" and
    never mentioned the removal -- the row-count branch matched and won."""
    head = snap([t for t in BASE["tables"] if t != "source"],
                kinds=BASE["kinds"],
                counts={"domain": 1, "species": 1, "product": 9})
    need, why = rc.required_bump(BASE, head, "6 12", "6 12")
    assert need == "minor"
    assert any("REMOVED" in r for r in why), why


def test_a_removed_species_is_minor():
    kinds = {**BASE["kinds"], "species": []}
    head = snap(BASE["tables"], kinds=kinds,
                counts={**BASE["counts"], "species": 0})
    need, why = rc.required_bump(BASE, head, "6 12", "6 12")
    assert need == "minor"
    assert any("REMOVED" in r for r in why), why
