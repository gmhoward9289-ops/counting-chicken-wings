"""Cross-source validation.

Most tests here check that the code does what it says. These check that two
INDEPENDENT government publications agree with each other, which is a
different and stronger claim: if NASS revises a series, or a parser silently
misreads a column, these fail even though every unit test still passes.

The two sources:

  regional_size_stat        Poultry Slaughter summary. Young chickens
                            slaughtered per calendar year, average live
                            weight measured at the plant.

  regional_production_year  Poultry Production and Value summary. Broilers
                            produced Dec 1 - Nov 30, from a grower survey.

Different population, different period, different methodology. Dividing
production pounds by head should still land on the slaughter report's
average live weight -- and it does, for every state both name.
"""

import sqlite3

import pytest

from counting_chicken_wings.build import DEFAULT_DB, build


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("xval") / "chickens.db"
    build(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def overlapping(conn):
    """States and years reported by both publications."""
    return conn.execute("""
        SELECT p.region, p.year,
               p.derived_live_weight_lb AS derived,
               s.avg_size               AS slaughter
        FROM regional_production_year p
        JOIN v_broiler_size_stat s
          ON s.region = p.region AND s.year = p.year AND s.month IS NULL
        WHERE p.region != 'United States'
          AND p.derived_live_weight_lb IS NOT NULL
        ORDER BY p.region, p.year
    """).fetchall()


def test_the_two_publications_actually_overlap():
    """Guard the guard: a join that matches nothing would pass everything."""
    conn = sqlite3.connect(DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        assert len(overlapping(conn)) >= 14
    finally:
        conn.close()


def test_production_reproduces_slaughter_live_weight_exactly_for_2025(db):
    """For the current year the two publications agree to the digit.

    2025 is where both series are final and cover the same birds most
    closely, and every state they both name matches within rounding. This is
    the strong form of the check and it should stay strong -- if a parser
    misread a column this is what would catch it.
    """
    rows = [r for r in overlapping(db) if r["year"] == 2025]
    assert len(rows) >= 14
    mismatches = [
        f"{r['region']}: derived {r['derived']:.2f} vs "
        f"slaughter {r['slaughter']:.2f}"
        for r in rows
        if abs(r["derived"] - r["slaughter"]) > 0.06
    ]
    assert not mismatches, "2025 disagreement: " + "; ".join(mismatches)


def test_production_tracks_slaughter_within_the_period_offset(db):
    """Across all years, allow the offset the two periods genuinely create.

    Production is surveyed December 1 to November 30; slaughter is the
    calendar year. That one-month shift means a state whose bird weight is
    trending will differ slightly between the two, and in 2024 Maryland and
    Oklahoma each sit 0.10 lb apart for exactly that reason.

    0.15 lb bounds the real offset plus one-decimal rounding in the
    slaughter series. Anything beyond it is a genuine disagreement, not an
    artefact, and should be investigated rather than accommodated.
    """
    mismatches = [
        f"{r['region']} {r['year']}: derived {r['derived']:.2f} "
        f"vs slaughter {r['slaughter']:.2f}"
        for r in overlapping(db)
        if abs(r["derived"] - r["slaughter"]) > 0.15
    ]
    assert not mismatches, "cross-source disagreement: " + "; ".join(mismatches)


def test_national_totals_differ_and_that_is_correct(db):
    """The two national figures MUST NOT match.

    Produced counts broilers Dec 1 - Nov 30; slaughtered counts young
    chickens per calendar year and also includes roasters and capons. If
    these ever became equal it would mean one series had been loaded into
    the other's table.
    """
    produced = db.execute(
        """SELECT head_thousands * 1000 FROM regional_production_year
           WHERE region = 'United States' AND year = 2025"""
    ).fetchone()[0]
    slaughtered = db.execute(
        "SELECT head_slaughtered FROM slaughter_stat_year WHERE year = 2025"
    ).fetchone()[0]

    assert produced != slaughtered
    # Same order of magnitude, though -- they describe the same industry.
    assert 0.9 < produced / slaughtered < 1.0


def test_production_report_recovers_a_state_slaughter_suppresses(db):
    """The point of carrying a second publication.

    NASS suppresses different states in different publications and years, so
    the union covers more than either alone. Florida is the current example.
    """
    only_in_production = {
        r[0] for r in db.execute("""
            SELECT region FROM regional_production_year
            WHERE region != 'United States'
            EXCEPT SELECT region FROM v_broiler_size_stat
        """).fetchall()
    }
    assert only_in_production, "second source no longer adds any state"
    assert "Florida" in only_in_production


def test_derived_live_weight_matches_its_own_inputs(db):
    """Internal consistency of the stored derivation.

    derived_live_weight_lb is stored rather than computed at query time, so
    it can drift from the columns it came from. This catches that.
    """
    bad = [
        f"{r['region']} {r['year']}"
        for r in db.execute("""
            SELECT region, year, head_thousands, live_weight_klb,
                   derived_live_weight_lb
            FROM regional_production_year
            WHERE head_thousands IS NOT NULL
              AND derived_live_weight_lb IS NOT NULL
        """).fetchall()
        if abs(r["live_weight_klb"] / r["head_thousands"]
               - r["derived_live_weight_lb"]) > 0.005
    ]
    assert not bad, "stored derivation drifted: " + ", ".join(bad)


def test_states_plus_aggregates_reproduce_the_national_total(db):
    """The aggregates' whole claim to trustworthiness, re-asserted from the
    database.

    NASS publishes the suppressed states as combined rows, and the check
    that makes those rows safe to carry is arithmetic: named states plus
    aggregates must reproduce the published United States total, per
    measure, per year. The parser refuses to emit a YAML that fails this;
    this test proves the property survived the build. If it ever fails, a
    row was edited by hand or the two tables drifted to different editions.
    """
    years = [r[0] for r in db.execute(
        "SELECT DISTINCT year FROM regional_production_aggregate")]
    assert years, "no aggregate rows built"
    for year in years:
        for col in ("head_thousands", "live_weight_klb", "value_kusd"):
            states = db.execute(
                f"""SELECT SUM({col}) FROM regional_production_year
                    WHERE year = ? AND region != 'United States'""",
                (year,),
            ).fetchone()[0]
            aggs = db.execute(
                f"SELECT SUM({col}) FROM regional_production_aggregate "
                "WHERE year = ?", (year,),
            ).fetchone()[0]
            national = db.execute(
                f"""SELECT {col} FROM regional_production_year
                    WHERE year = ? AND region = 'United States'""",
                (year,),
            ).fetchone()[0]
            assert states + aggs == national, (
                f"{year} {col}: states {states} + aggregates {aggs} "
                f"!= published national {national}"
            )


def test_aggregate_members_never_overlap_named_states(db):
    """An aggregate exists BECAUSE its members have no row of their own.

    If a member ever also appears as an individually published state in the
    same year, the sum above still catching the right total would be luck,
    and any consumer summing regions with aggregates would double-count."""
    rows = db.execute(
        """SELECT year, label, members
           FROM regional_production_aggregate"""
    ).fetchall()
    for r in rows:
        named = {x[0] for x in db.execute(
            """SELECT region FROM regional_production_year
               WHERE year = ? AND region != 'United States'""",
            (r["year"],),
        )}
        overlap = set(r["members"].split(", ")) & named
        assert not overlap, (
            f"{r['year']} '{r['label']}' members also published "
            f"individually: {sorted(overlap)}"
        )


def test_every_production_row_is_cited(db):
    assert db.execute(
        "SELECT COUNT(*) FROM regional_production_year WHERE source_id IS NULL"
    ).fetchone()[0] == 0
