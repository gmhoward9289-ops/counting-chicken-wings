"""Deciding the release number at merge time.

The rule these enforce is `docs/VERSIONING.md`'s: pick the number last. It was
written as an instruction to humans and lost the moment two sessions merged
minutes apart -- v1.5.0 and v1.6.0 were both taken out from under a branch in
review on 2026-07-30, and v1.9.1 and v1.10.0 were both skipped entirely on
2026-07-31 because the release job read a `pyproject.toml` that had already
moved on. Executing the rule is the only version of it that holds.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "next_version", ROOT / "tools" / "next_version.py")
nv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nv)


CHANGELOG = """# Changelog

## Unreleased

### Something shipped

Body.

## v1.11.0 — 2026-07-31

Older.
"""


# ---------------------------------------------------------------------------
# Is there anything to release?
# ---------------------------------------------------------------------------


def test_an_unreleased_section_with_content_is_a_release():
    assert "Something shipped" in nv.unreleased(CHANGELOG)


def test_the_section_stops_at_the_next_heading():
    assert "Older" not in nv.unreleased(CHANGELOG)


def test_no_unreleased_section_means_nothing_to_release():
    assert nv.unreleased("# Changelog\n\n## v1.11.0 — 2026-07-31\n\nx\n") is None


def test_an_empty_unreleased_section_is_not_a_release():
    """A merge that left the heading behind has not written a changelog."""
    assert nv.unreleased("# Changelog\n\n## Unreleased\n\n## v1.1.0 — x\n\ny\n") is None


# ---------------------------------------------------------------------------
# MAJOR.MINOR.MINOR, which is not SemVer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version,level,want", [
    ("1.11.0", "third",  "1.11.1"),
    ("1.11.0", "second", "1.12.0"),
    ("1.11.0", "major",  "2.0.0"),
    ("1.9.1",  "third",  "1.9.2"),
    ("1.9.1",  "second", "1.10.0"),
])
def test_bump(version, level, want):
    assert nv.bump(version, want and level) == want


def test_a_second_digit_bump_resets_the_third():
    """1.9.1 -> 1.10.0, not 1.10.1."""
    assert nv.bump("1.9.1", "second") == "1.10.0"


def test_a_major_bump_resets_both():
    assert nv.bump("3.4.5", "major") == "4.0.0"


def test_bumping_nothing_is_an_error_rather_than_a_silent_no_op():
    with pytest.raises(ValueError):
        nv.bump("1.0.0", "none")


def test_the_third_digit_is_not_treated_as_a_patch_level():
    """Guards the scheme itself.

    The old rule called this a patch and took the project 1.0.0 -> 1.7.0 in
    two days. If someone 'fixes' bump() into SemVer, second-digit moves stop
    resetting the third and this fails.
    """
    assert nv.bump("1.7.3", "second") == "1.8.0"


# ---------------------------------------------------------------------------
# Writing the number in
# ---------------------------------------------------------------------------


def test_rewrite_gives_the_section_its_number_and_date():
    out = nv.rewrite("1.12.0", CHANGELOG, "2026-08-01")
    assert "## v1.12.0 — 2026-08-01" in out
    assert "## Unreleased" not in out


def test_rewrite_leaves_older_releases_alone():
    out = nv.rewrite("1.12.0", CHANGELOG, "2026-08-01")
    assert "## v1.11.0 — 2026-07-31" in out


def test_rewrite_touches_only_the_first_heading():
    """Two Unreleased headings would mean a bad merge; do not paper over it."""
    doubled = CHANGELOG + "\n## Unreleased\n\nstray\n"
    assert nv.rewrite("1.12.0", doubled, "2026-08-01").count("## Unreleased") == 1


# ---------------------------------------------------------------------------
# The real file
# ---------------------------------------------------------------------------


def test_the_levels_are_ordered_weakest_first():
    """`none` must sort below `third`; the floor rule depends on it."""
    assert nv.LEVELS.index("none") < nv.LEVELS.index("third") \
        < nv.LEVELS.index("second") < nv.LEVELS.index("major")


def test_every_version_in_the_real_changelog_parses_as_three_digits():
    import re
    text = nv.CHANGELOG.read_text()
    for v in re.findall(r"^## v(\S+)", text, re.M):
        assert len(v.split(".")) == 3, f"{v} is not MAJOR.MINOR.MINOR"
