"""The release notes tool, which is what makes releasing happen at all.

These matter more than their size suggests. The tag push is what triggers
`version-consistency`, the only CI job that compares the released number
against `pyproject.toml` -- so if this tool declines to release, that check
never runs, and the versioning rules go back to being enforced by memory.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "release_notes", ROOT / "tools" / "release_notes.py")
rn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rn)


CHANGELOG = """# Changelog

## v2.0.0 — 2026-08-01

### A subheading first

Body text here.

## v1.9.0 — 2026-07-30

Maple syrup: the third domain, and the first individual that survives
being harvested.

More prose that is not the title.

## v1.8.0 — 2026-07-30

Only one line.

## v1.7.0 — 2026-07-30
"""


# ---------------------------------------------------------------------------
# Finding the section
# ---------------------------------------------------------------------------


def test_section_stops_at_the_next_version():
    body = rn.section("1.9.0", CHANGELOG)
    assert body.startswith("Maple syrup")
    assert "v1.8.0" not in body and "Only one line" not in body


def test_the_last_section_runs_to_the_end_of_the_file():
    """The oldest release has no following heading to stop at."""
    text = CHANGELOG.replace("## v1.7.0 — 2026-07-30\n", "")
    assert rn.section("1.8.0", text) == "Only one line."


def test_a_missing_section_refuses_rather_than_publishing_nothing():
    """An empty release looks exactly like one nobody bothered to describe."""
    with pytest.raises(SystemExit):
        rn.section("3.0.0", CHANGELOG)


def test_an_empty_section_refuses_too():
    with pytest.raises(SystemExit):
        rn.section("1.7.0", CHANGELOG)


def test_the_date_in_the_heading_is_not_matched():
    """Correcting a release date must not orphan its notes."""
    assert rn.section("1.8.0", CHANGELOG.replace("v1.8.0 — 2026-07-30",
                                                 "v1.8.0 — 2026-07-31"))


def test_a_version_is_not_matched_by_a_longer_one():
    """`1.1.0` must not match the `## v1.10.0` heading."""
    text = "## v1.10.0 — 2026-07-30\n\nThe A/B harness.\n"
    with pytest.raises(SystemExit):
        rn.section("1.1.0", text)


# ---------------------------------------------------------------------------
# The title
# ---------------------------------------------------------------------------


def test_a_wrapped_paragraph_is_joined_before_the_sentence_is_taken():
    """CHANGELOG.md hard-wraps at ~76 columns.

    Reading a single line produced "...the first individual that survives
    being", which stops mid-clause and reads as a truncation bug.
    """
    t = rn.title("1.9.0", rn.section("1.9.0", CHANGELOG))
    assert t == ("v1.9.0 — Maple syrup: the third domain, and the first "
                 "individual that survives being harvested")


def test_only_the_first_sentence_becomes_the_title():
    t = rn.title("1.9.0", rn.section("1.9.0", CHANGELOG))
    assert "More prose" not in t


def test_a_leading_subheading_is_used_verbatim():
    """A section opening with `###` has no summary line to borrow, and
    inventing one would put words in the changelog's mouth."""
    assert rn.title("2.0.0", rn.section("2.0.0", CHANGELOG)) == \
        "v2.0.0 — A subheading first"


def test_the_title_is_not_left_ending_in_a_full_stop():
    assert not rn.title("1.8.0", rn.section("1.8.0", CHANGELOG)).endswith(".")


# ---------------------------------------------------------------------------
# The version itself
# ---------------------------------------------------------------------------


def test_version_comes_from_the_file_not_from_installed_metadata():
    """An editable install reports whatever it was last installed at, which
    is the stale answer that lands a release under the wrong number."""
    assert rn.project_version('name = "x"\nversion = "4.5.6"\n') == "4.5.6"


def test_every_released_version_in_the_real_changelog_has_a_usable_title():
    """Regression net for the actual file: every heading must resolve."""
    import re
    text = rn.CHANGELOG.read_text(encoding="utf-8")
    versions = re.findall(r"^## v(\d+\.\d+\.\d+)\b", text, re.M)
    assert versions, "no version headings found"
    for v in versions:
        t = rn.title(v, rn.section(v, text))
        assert t.startswith(f"v{v} — "), f"{v} produced {t!r}"
        assert len(t) > len(f"v{v} — ") + 5, f"{v} title is too short: {t!r}"
