"""The README must not overstate how well-sourced the corpus is.

That claim is the project's whole promise, and it drifted three times while
hand-maintained -- last landing on "7 of 12 unsourced" when the truth was 11 of
21. Drift in that direction is the one this project cannot afford, so it is a
test rather than a habit.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from counting_chicken_wings.audit import (
    STATS_BEGIN,
    STATS_END,
    corpus_stats,
    render_stats,
    stats_block,
)

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

sys.path.insert(0, str(ROOT / "tools"))
from update_readme import replace_block  # noqa: E402


def test_readme_block_matches_the_corpus(tmp_path):
    """The generated block in README.md agrees with the database."""
    text = README.read_text(encoding="utf-8")
    assert STATS_BEGIN in text, "README lost its generated markers"
    expected = replace_block(text, stats_block())
    assert text == expected, (
        "README.md corpus figures are stale. "
        "Run: python tools/update_readme.py"
    )


def test_no_stale_hand_written_counts_outside_the_block():
    """Corpus counts must live in the block, not be re-quoted around it.

    A second copy is how the Status section came to disagree with the section
    two screens above it.
    """
    text = README.read_text(encoding="utf-8")
    start = text.find(STATS_BEGIN)
    end = text.find(STATS_END) + len(STATS_END)
    outside = text[:start] + text[end:]
    assert "unsourced estimates" not in outside, (
        "the unsourced-estimate claim belongs only in the generated block"
    )


@pytest.fixture
def conn(tmp_path):
    from counting_chicken_wings.build import build

    db = tmp_path / "t.db"
    build(db)
    c = sqlite3.connect(db)
    yield c
    c.close()


def test_stats_are_internally_consistent(conn):
    """Count-affecting estimates are a subset of estimates, not a parallel tally.

    The README subtracts one from the other to report the mass-only remainder,
    so a negative remainder would print a sentence that reads as a data bug.
    """
    s = corpus_stats(conn)
    assert 0 <= s["count_affecting_estimates"] <= s["estimates"]
    assert s["estimates"] <= s["loss_factors"]
    assert 0 <= s["estimate_pct"] <= 100


def test_rendered_block_states_the_percentage(conn):
    """The percentage is the number a reader remembers; it must be present."""
    s = corpus_stats(conn)
    block = render_stats(s)
    assert f"{s['estimate_pct']}%" in block
    assert block.startswith(STATS_BEGIN)
    assert block.endswith(STATS_END)


def test_orphan_sources_are_counted_not_hidden(conn):
    """A source cited by nothing is a real state and must be countable.

    psu-extension-saffron is held deliberately -- it evidences a conflict
    rather than a loaded figure -- so the count is not asserted to be zero.
    """
    s = corpus_stats(conn)
    assert s["orphan_sources"] >= 0
    assert s["orphan_sources"] < s["sources"]
