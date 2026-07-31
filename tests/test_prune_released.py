"""`## Unreleased` must not republish what a tag already carried.

The release job no longer pushes its version bump to `master` -- `protect-master`
rejects it -- so nothing ever rewrites `## Unreleased` on the branch. Left
alone, every release would carry its predecessor's entries as well as its own,
and the duplication would compound: twelve backlogged commits on 2026-07-31
would have gone out again under the next number, and again under the one after.

These tests cover the pruning rule itself. The git-backed ones use a throwaway
repo rather than this one, so they stay honest when the real changelog moves.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import prune_released as pr  # noqa: E402


def changelog(*blocks: str, released: str = "") -> str:
    body = "\n\n".join(blocks)
    return f"# Changelog\n\n## Unreleased\n\n{body}\n\n{released}"


BLOCK_A = "### Silk: a fifth domain\n\nSilk lands, with a garment-level product."
BLOCK_B = "### Ground beef has no anatomical floor\n\nOne patty is many cattle."


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------

def test_a_block_the_tag_already_published_is_dropped():
    text = changelog(BLOCK_A, BLOCK_B)
    new, dropped = pr.prune(text, {pr.normalise("Silk: a fifth domain")})

    assert dropped == ["Silk: a fifth domain"]
    assert "Silk: a fifth domain" not in new
    assert BLOCK_B in new


def test_a_block_the_tag_never_saw_is_kept():
    text = changelog(BLOCK_A, BLOCK_B)
    new, dropped = pr.prune(text, {pr.normalise("Something else entirely")})

    assert dropped == []
    assert new == text, "an untouched section must not be rewritten at all"


def test_pruning_everything_leaves_nothing_to_release():
    """The correct outcome when no new PR has merged since the last release."""
    text = changelog(BLOCK_A, BLOCK_B)
    seen = {pr.normalise("Silk: a fifth domain"),
            pr.normalise("Ground beef has no anatomical floor")}
    new, dropped = pr.prune(text, seen)

    assert len(dropped) == 2
    span = pr.unreleased_span(new)
    assert new[span[0]:span[1]].strip() == ""


def test_released_sections_below_unreleased_are_untouched():
    """Only the `## Unreleased` body is in scope. History is not rewritten."""
    history = "## v1.11.0 — 2026-07-30\n\n### Silk: a fifth domain\n\nold copy."
    text = changelog(BLOCK_A, BLOCK_B, released=history)
    new, _ = pr.prune(text, {pr.normalise("Silk: a fifth domain")})

    assert history in new


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("written, published", [
    ("### Syrup is a blend — not one tree", "Syrup is a blend -- not one tree"),
    ("###   Extra   spacing  here", "Extra spacing here"),
    ("### Case Does Not Matter", "case does not matter"),
])
def test_headings_match_across_spelling_differences(written, published):
    """A hard-wrapped changelog carries both dash spellings. Same entry."""
    text = changelog(f"{written}\n\nbody.", BLOCK_B)
    _, dropped = pr.prune(text, {pr.normalise(published)})
    assert len(dropped) == 1


def test_a_deeper_heading_is_not_a_block_boundary():
    """`####` is structure inside an entry; splitting there would halve it."""
    block = "### Silk: a fifth domain\n\n#### Sourcing\n\nDetail.\n\n#### Yield\n\nMore."
    text = changelog(block)
    new, dropped = pr.prune(text, {pr.normalise("Silk: a fifth domain")})

    assert dropped == ["Silk: a fifth domain"]
    assert "Sourcing" not in new and "Yield" not in new


def test_a_body_with_no_headings_is_left_alone():
    """An unseen shape is preserved, not guessed at. Losing notes is worse."""
    text = changelog("Just prose, with no `###` heading anywhere.")
    new, dropped = pr.prune(text, {pr.normalise("Silk: a fifth domain")})

    assert dropped == []
    assert new == text


def test_no_unreleased_section_is_not_an_error():
    text = "# Changelog\n\n## v1.11.0 — 2026-07-30\n\n### Silk\n\nbody."
    new, dropped = pr.prune(text, {pr.normalise("Silk")})

    assert (new, dropped) == (text, [])


# ---------------------------------------------------------------------------
# Reading the previous tag out of git
# ---------------------------------------------------------------------------

def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", ".")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## v1.11.0 — 2026-07-30\n\n" + BLOCK_A + "\n",
        encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "release")
    _git(tmp_path, "tag", "-a", "v1.11.0", "-m", "release")
    return tmp_path


def test_published_reads_the_tag_not_the_working_tree(repo, monkeypatch):
    """The working tree is the thing being pruned. Asking it what was already
    released would answer "all of it" and empty the section."""
    (repo / "CHANGELOG.md").write_text(
        changelog(BLOCK_A, BLOCK_B), encoding="utf-8")

    monkeypatch.setattr(pr, "ROOT", repo)
    monkeypatch.setattr(pr, "CHANGELOG", repo / "CHANGELOG.md")

    seen = pr.published("v1.11.0")
    assert pr.normalise("Silk: a fifth domain") in seen
    assert pr.normalise("Ground beef has no anatomical floor") not in seen


def test_a_missing_tag_fails_loudly(repo, monkeypatch):
    monkeypatch.setattr(pr, "ROOT", repo)
    with pytest.raises(SystemExit):
        pr.published("v9.9.9")
