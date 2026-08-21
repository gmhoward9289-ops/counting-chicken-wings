"""Disagreements the corpus records rather than resolves.

These were in the corpus long before they were queryable -- held as prose in a
source's `notes:` field, where the roadmap counted the word "conflict" appearing
zero times in the served page. The invariant under test is not any particular
figure (the saffron numbers will be refined); it is the shape of an honest
disagreement:

  * two or more sides, never one -- a one-sided "conflict" is a single weak
    figure and belongs in that source's notes;
  * every side cited, because a disagreement rendered without both sources is
    just a different unsourced claim; and
  * neither figure loaded into the model, because the reason to record a
    conflict is usually that neither number can be trusted enough to compute
    with.

The second half of the file is about the audit: recording a conflict is what
lifts its two sources off the "cited by nothing" warning, and a `held_reason`
is what lifts the rest, so that warning goes back to meaning "a figure was
probably dropped" instead of firing on five deliberate decisions every build.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from counting_chicken_wings import audit
from counting_chicken_wings import build as buildmod
from counting_chicken_wings.build import build
from counting_chicken_wings.api import app


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    """The real corpus, built once, shared across the read-only tests."""
    path = tmp_path_factory.mktemp("conflicts") / "chickens.db"
    build(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# The shape of a disagreement
# ---------------------------------------------------------------------------

def test_the_recorded_conflicts_are_present(db):
    slugs = {r["slug"] for r in db.execute("SELECT slug FROM conflict")}
    assert {
        "saffron-yield-per-acre",
        "israel-broiler-weight-basis",
        "beef-carcass-to-packaged-yield",
    } <= slugs


def test_every_conflict_has_at_least_two_positions(db):
    """A single citable side is not a disagreement."""
    rows = db.execute(
        """SELECT c.slug, COUNT(p.id) AS n
           FROM conflict c
           JOIN conflict_position p ON p.conflict_id = c.id
           GROUP BY c.id"""
    ).fetchall()
    assert rows, "no conflicts loaded at all"
    for r in rows:
        assert r["n"] >= 2, f"{r['slug']} has only {r['n']} position(s)"


def test_every_position_cites_a_real_source(db):
    """The citation guarantee, applied to conflicts: a position without a
    resolvable source is exactly the unsourced claim this project refuses."""
    rows = db.execute(
        """SELECT p.id, s.slug, s.title
           FROM conflict_position p
           LEFT JOIN source s ON s.id = p.source_id"""
    ).fetchall()
    assert rows, "no conflict positions loaded"
    for r in rows:
        assert r["slug"] and r["title"], \
            f"conflict position {r['id']} does not resolve to a real source"


def test_no_conflict_figure_is_loaded_into_the_model(db):
    """The whole point: the disagreement is the datum, not either number."""
    loaded = db.execute(
        "SELECT slug FROM conflict WHERE loaded != 0"
    ).fetchall()
    assert not loaded, (
        "a conflict claims a loaded figure; if that is genuinely intended it "
        "needs its own test, because it is the rare case: "
        f"{[r['slug'] for r in loaded]}"
    )


def test_a_position_value_never_reaches_the_loss_or_mixing_model(db):
    """Belt-and-braces on the above: the sources held in a conflict must not
    also be quietly powering a loss factor or a mixing stage, which would mean
    the model rests on a figure the page presents as untrusted."""
    for slug in ("psu-extension-saffron", "usda-psd-israel-broiler-2000"):
        sid = db.execute(
            "SELECT id FROM source WHERE slug = ?", (slug,)
        ).fetchone()["id"]
        for table in ("loss_factor", "mixing_stage", "product",
                      "regional_size_stat"):
            n = db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE source_id = ?", (sid,)
            ).fetchone()[0]
            assert n == 0, f"{slug} unexpectedly powers {table}"


def test_build_rejects_a_one_sided_conflict(tmp_path, monkeypatch):
    """The guard the schema cannot express: it cannot count rows per parent.

    Builder and BuildError are read off `buildmod` at call time rather than
    from the module-level import, because test_build.py reloads the build
    module (DEFAULT_DB is computed at import), which rebinds BuildError to a new
    class -- and a stale `pytest.raises(BuildError)` would then let the real
    exception sail straight past.
    """
    conn = sqlite3.connect(tmp_path / "t.db")
    conn.executescript(buildmod.SCHEMA.read_text(encoding="utf-8"))
    b = buildmod.Builder(conn)
    b.source["only-one"] = 1

    monkeypatch.setattr(buildmod, "load", lambda name: {
        "conflicts": [{
            "slug": "lonely", "subject": "x", "question": "q", "summary": "s",
            "positions": [
                {"label": "a", "claim": "c", "source": "only-one"},
            ],
        }]
    })
    with pytest.raises(buildmod.BuildError, match="at least two positions"):
        b.conflicts()


# ---------------------------------------------------------------------------
# The audit stops crying wolf
# ---------------------------------------------------------------------------

def test_a_conflict_source_is_no_longer_an_orphan(db):
    """A source held as one side of a conflict is cited by its position row,
    so `conflict_position` (which carries a source_id) keeps it off the audit's
    orphan list. This is the mechanism, checked directly."""
    tables = [t for t, _l, _r in audit.cited_tables(db)]
    assert "conflict_position" in tables, (
        "conflict_position lost its source_id, so the audit no longer counts "
        "conflicts as citations"
    )
    for slug in ("psu-extension-saffron", "usda-psd-israel-broiler-2000"):
        sid = db.execute(
            "SELECT id FROM source WHERE slug = ?", (slug,)
        ).fetchone()["id"]
        cited = db.execute(
            "SELECT COUNT(*) FROM conflict_position WHERE source_id = ?",
            (sid,),
        ).fetchone()[0]
        assert cited, f"{slug} is not cited by any conflict position"


def test_held_sources_declare_a_reason(db):
    """The three sources that are uncited on purpose say so, in a vocabulary
    the audit can read rather than in prose it cannot."""
    for slug in ("jfs-independence-day-grilling", "nysmaple-sap-per-tree",
                 "umaine-7036e-maple"):
        row = db.execute(
            "SELECT held_reason FROM source WHERE slug = ?", (slug,)
        ).fetchone()
        assert row["held_reason"] in ("corroboration", "context"), \
            f"{slug} is uncited with no held_reason -- it reads as an orphan"


def test_corpus_stats_separates_held_from_orphaned(tmp_path):
    """`orphan_sources` must count only genuine orphans -- a figure that was
    probably dropped -- and not the sources kept on purpose."""
    path = tmp_path / "stats.db"
    build(path)
    conn = sqlite3.connect(path)
    try:
        stats = audit.corpus_stats(conn)
    finally:
        conn.close()

    assert stats["held_sources"] >= 3, \
        "the deliberately-held sources are not being counted as held"
    assert stats["conflicts"] >= 3, "conflicts are not counted in the stats"
    # The held count and the orphan count partition the uncited sources; a
    # source kept on purpose must never also be tallied as a probable-dropped
    # figure. Re-derive the raw "cited by nothing" total and check the split.
    conn = sqlite3.connect(path)
    try:
        clauses = " ".join(
            f"AND NOT EXISTS (SELECT 1 FROM {t} WHERE source_id = s.id)"
            for t, _l, _r in audit.cited_tables(conn)
        )
        uncited = conn.execute(
            f"SELECT COUNT(*) FROM source s WHERE 1=1 {clauses}"
        ).fetchone()[0]
    finally:
        conn.close()
    assert stats["orphan_sources"] + stats["held_sources"] == uncited, \
        "held and orphan counts do not partition the uncited sources"


def test_audit_still_passes_overall(tmp_path):
    """Nothing added here may break the central guarantee."""
    path = tmp_path / "audit.db"
    build(path)
    assert audit.audit(path) == 0


# ---------------------------------------------------------------------------
# Over HTTP
# ---------------------------------------------------------------------------

def test_api_conflicts_ships_every_source(client):
    """Same rule the calculator obeys: a disagreement cannot be rendered
    without the sources on both sides available to render beside it."""
    r = client.get("/api/conflicts")
    assert r.status_code == 200
    conflicts = r.json()["conflicts"]
    assert len(conflicts) >= 3
    for c in conflicts:
        assert len(c["positions"]) >= 2, f"{c['slug']} is one-sided over HTTP"
        assert c["loaded"] is False
        for p in c["positions"]:
            assert p["source_slug"] and p["source_title"], \
                f"{c['slug']} ships a position with no source"
