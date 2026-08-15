"""Eggs: recurring yield, the time window, and the physiological floor.

Eggs are the project's first product where production happens over time, so
these tests guard a different set of invariants from the wing tests. The
central one: a hen lays at most about one egg a day, therefore a dozen eggs
gathered in a single day came from at least twelve different hens, and no
supply chain arrangement can reduce that.
"""

import sqlite3

import pytest

from counting_chicken_wings import db as dbm
from counting_chicken_wings.build import SCHEMA
from counting_chicken_wings.model import (
    MixingStage,
    RecurringYield,
    expected_distinct_general,
    recurring_floor,
    resolve_pool,
)

# US 2025, NASS Chickens and Eggs.
EGGS_PER_YEAR = 288
LAY_CEILING = 1.0


# ---------------------------------------------------------------------------
# The rate itself
# ---------------------------------------------------------------------------

def test_rate_per_day_matches_the_independently_reported_figure():
    """288 eggs/year must reproduce NASS's separately surveyed daily rate.

    The monthly releases report 78.7-79.9 eggs per 100 layers per day from a
    different survey than the annual summary. Agreement between the two is
    the strongest validation in the project, so it is pinned here.
    """
    ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=1)
    per_100 = ry.rate_per_day * 100
    assert 78.0 <= per_100 <= 80.0, per_100


def test_period_is_mandatory_and_validated():
    with pytest.raises(ValueError):
        RecurringYield(EGGS_PER_YEAR, 0, window_days=1)
    with pytest.raises(ValueError):
        RecurringYield(EGGS_PER_YEAR, 365, window_days=0)
    with pytest.raises(ValueError):
        RecurringYield(0, 365, window_days=1)


def test_a_hen_cannot_beat_her_own_physiology():
    """Expected yield is capped by the per-day ceiling, never above it."""
    ry = RecurringYield(500, 365, window_days=1, max_units_per_day=LAY_CEILING)
    # 500/year would imply 1.37 eggs/day, which is not possible.
    assert ry.units_per_individual == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# The floor moves with the window -- the whole point of eggs
# ---------------------------------------------------------------------------

def test_same_day_dozen_needs_at_least_twelve_hens():
    """The headline result, and it is a hard floor rather than an estimate."""
    ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=1,
                        max_units_per_day=LAY_CEILING)
    hard, expected = recurring_floor(12, ry)
    assert hard == pytest.approx(12.0)
    # And you need MORE than twelve hens present, because hens do not lay
    # every day: 12 / 0.789 = 15.2.
    assert expected == pytest.approx(15.2, abs=0.1)
    assert expected > hard


def test_one_hen_can_make_a_dozen_given_fifteen_days():
    """Unlike wings, the floor here is genuinely reachable."""
    ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=15,
                        max_units_per_day=LAY_CEILING)
    hard, expected = recurring_floor(12, ry)
    assert hard < 1.0
    assert expected == pytest.approx(1.01, abs=0.05)


def test_floor_falls_monotonically_as_the_window_widens():
    floors = []
    for w in (1, 2, 7, 15, 30, 365):
        ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=w,
                            max_units_per_day=LAY_CEILING)
        floors.append(recurring_floor(12, ry)[0])
    assert floors == sorted(floors, reverse=True)
    assert floors[0] == pytest.approx(12.0)


def test_without_a_ceiling_there_is_no_hard_floor_to_report():
    """No physiological cap means no hard floor -- say so, don't invent one.

    This test used to assert `hard == expected`, which is the docstring's own
    rule broken by its own assertion: a hard floor is the claim that no
    arrangement of the supply chain can beat it, and an average production
    rate cannot support that claim. Reporting the average under the hard
    floor's name is inventing one. Maple is the product where it showed --
    the CLI printed "hard floor 193" for a figure derived from two extension
    services disagreeing about sap flow -- and it was wrong here first.
    """
    ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=1)
    hard, expected = recurring_floor(12, ry)
    assert hard is None
    assert expected == pytest.approx(12 / (EGGS_PER_YEAR / 365))


# ---------------------------------------------------------------------------
# Pooling: the ceiling is pinned, unlike wings
# ---------------------------------------------------------------------------

COMMERCIAL = [
    MixingStage("house", "Layer house", 250000, "random"),
    MixingStage("grade", "Grading", 250000, "random"),
    MixingStage("carton", "Carton", 250000, "none"),
]


def test_commercial_same_day_dozen_is_exactly_twelve_hens():
    """Floor meets ceiling. There is no room for the supply chain to move it.

    This is the structural inverse of wings, where the floor sits at 6 and
    mixing pushes the answer up toward 12.
    """
    ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=1,
                        max_units_per_day=LAY_CEILING)
    container, distinct, _ = resolve_pool(COMMERCIAL, 12,
                                          ry.units_per_individual)
    assert expected_distinct_general(12, container, distinct) == \
        pytest.approx(12.0, abs=1e-3)


def test_backyard_flock_lands_near_its_own_size():
    """Six hens over two weeks really is about six hens."""
    ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=14,
                        max_units_per_day=LAY_CEILING)
    stages = [MixingStage("flock", "Backyard flock", 6, "random")]
    container, distinct, _ = resolve_pool(stages, 12, ry.units_per_individual)
    got = expected_distinct_general(12, container, distinct)
    assert 5.0 <= got <= 6.5, got


def test_a_single_hen_over_time_reports_one():
    """One hen, fifteen days, twelve eggs -- the answer is her."""
    ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=15,
                        max_units_per_day=LAY_CEILING)
    stages = [MixingStage("flock", "One hen", 1, "random")]
    container, distinct, _ = resolve_pool(stages, 12, ry.units_per_individual)
    got = expected_distinct_general(12, container, distinct)
    assert got == pytest.approx(1.0, abs=0.1)


def test_distinct_never_exceeds_the_dozen_at_any_flock_size():
    ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=1,
                        max_units_per_day=LAY_CEILING)
    for flock in (12, 100, 5000, 250000, 2000000):
        stages = [MixingStage("f", "Flock", flock, "random")]
        c, d, _ = resolve_pool(stages, 12, ry.units_per_individual)
        assert expected_distinct_general(12, c, d) <= 12.0 + 1e-9, flock


def test_eggs_invert_the_wing_relationship():
    """Wings: floor 6, answer ~12. Same-day eggs: floor 12, answer 12."""
    egg_ry = RecurringYield(EGGS_PER_YEAR, 365, window_days=1,
                            max_units_per_day=LAY_CEILING)
    egg_floor, _ = recurring_floor(12, egg_ry)
    ec, ed, _ = resolve_pool(COMMERCIAL, 12, egg_ry.units_per_individual)
    egg_answer = expected_distinct_general(12, ec, ed)

    wc, wd, _ = resolve_pool(COMMERCIAL, 12, 2.0)
    wing_answer = expected_distinct_general(12, wc, wd)

    assert egg_floor == pytest.approx(12.0)        # floor at the ceiling
    assert egg_answer == pytest.approx(egg_floor, abs=1e-3)
    assert 6.0 < wing_answer                       # pushed up from 6
    assert wing_answer < 12.0


# ---------------------------------------------------------------------------
# Schema constraints
# ---------------------------------------------------------------------------

def _fresh_db(tmp_path):
    p = tmp_path / "t.db"
    c = sqlite3.connect(p)
    c.executescript(SCHEMA.read_text(encoding="utf-8"))
    c.execute("INSERT INTO source (slug,title,publisher,retrieved_on,"
              "source_type) VALUES ('s','t','p','2026-01-01','government')")
    c.execute("INSERT INTO domain (slug,label) VALUES ('d','D')")
    c.execute("INSERT INTO species (domain_id,slug,common_name,"
              "individual_noun,individual_plural) VALUES (1,'sp','S','x','xs')")
    return c


def _insert_product(conn, slug, **kw):
    cols = dict(species_id=1, slug=slug, label="L", label_plural="Ls",
                units_per_individual_lo=1, units_per_individual_mode=1,
                units_per_individual_hi=1, unit_name="u", source_id=1, **kw)
    names = ",".join(cols)
    marks = ",".join("?" * len(cols))
    conn.execute(f"INSERT INTO product ({names}) VALUES ({marks})",
                 list(cols.values()))


def test_recurring_without_a_period_is_rejected(tmp_path):
    """The bug this constraint exists to stop.

    Written as a bare `yield_period_days > 0`, a NULL period made the
    comparison NULL and SQLite passed the CHECK -- silently allowing the one
    thing being forbidden. Regression-guarded because it already happened.
    """
    conn = _fresh_db(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        _insert_product(conn, "b1", yield_mode="recurring")
    with pytest.raises(sqlite3.IntegrityError):
        _insert_product(conn, "b2", yield_mode="recurring",
                        yield_period_days=None)
    with pytest.raises(sqlite3.IntegrityError):
        _insert_product(conn, "b3", yield_mode="recurring",
                        yield_period_days=0)


def test_recurring_with_a_period_is_accepted(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_product(conn, "ok", yield_mode="recurring",
                    yield_period_days=365, max_units_per_day=1.0,
                    rate_label="laying rate")


def test_a_recurring_product_must_name_its_own_rate(tmp_path):
    """Otherwise the prose borrows another species'. Every surface said "at
    the real LAYING rate" for anything recurring, so maple syrup was reported
    at a tree's laying rate. The constraint makes the omission impossible
    rather than merely embarrassing."""
    conn = _fresh_db(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        _insert_product(conn, "noname", yield_mode="recurring",
                        yield_period_days=365)


def test_a_timeless_product_cannot_claim_a_rate_or_a_window(tmp_path):
    """A wing has no rate to name and no window to default to."""
    conn = _fresh_db(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        _insert_product(conn, "r1", yield_mode="countable",
                        rate_label="laying rate")
    with pytest.raises(sqlite3.IntegrityError):
        _insert_product(conn, "r2", yield_mode="countable",
                        default_window_days=1)


def test_a_cap_note_without_a_cap_is_refused(tmp_path):
    """The note explains the ceiling. With no ceiling recorded it is the
    model asserting physiology the corpus does not hold."""
    conn = _fresh_db(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        _insert_product(conn, "c1", yield_mode="recurring",
                        yield_period_days=365, rate_label="laying rate",
                        cap_note="lays at most one a day")


def test_a_timeless_product_cannot_carry_a_per_day_cap(tmp_path):
    """A daily ceiling on something that is not produced daily is nonsense."""
    conn = _fresh_db(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        _insert_product(conn, "bad", yield_mode="countable",
                        max_units_per_day=1.0)


# ---------------------------------------------------------------------------
# Seeded data
# ---------------------------------------------------------------------------

def test_egg_product_is_seeded_as_recurring():
    conn = dbm.connect()
    try:
        row = dbm.get_product(conn, "table_egg")
        assert row["yield_mode"] == "recurring"
        assert row["yield_period_days"] == 365
        assert row["max_units_per_day"] == 1.0
        assert row["units_per_individual_mode"] == EGGS_PER_YEAR
        assert row["individual_plural"] == "hens"
        # Not an anatomical constant: 288/year moves with breed, age, light,
        # feed and moulting. The hardness lives in max_units_per_day.
        assert row["is_anatomical_constant"] == 0
    finally:
        conn.close()


def test_seeded_egg_rate_reproduces_national_totals():
    """365M layers x 288 eggs should give the reported ~105 billion."""
    conn = dbm.connect()
    try:
        row = dbm.get_product(conn, "table_egg")
        total = 365_000_000 * row["units_per_individual_mode"]
        assert 104e9 <= total <= 106e9, total
    finally:
        conn.close()


def test_layer_programs_span_backyard_to_industrial():
    conn = dbm.connect()
    try:
        rows = conn.execute(
            """SELECT p.slug, p.size_mode FROM production_program p
               JOIN species s ON s.id = p.species_id
               WHERE s.slug = 'layer_hen' ORDER BY p.size_mode"""
        ).fetchall()
        sizes = {r["slug"]: r["size_mode"] for r in rows}
        assert sizes["backyard_flock"] < 100
        assert sizes["conventional_cage"] > 100000
        # Only the backyard end can ever reach the floor of one hen.
        assert sizes["backyard_flock"] < sizes["pasture_raised"]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Unit collision between species -- a bug that actually happened
# ---------------------------------------------------------------------------

def test_species_views_keep_incompatible_units_apart():
    """regional_size_stat mixes pounds and eggs; the views must separate them.

    Adding egg data broke the cross-validation suite instantly, because its
    query read regional_size_stat without a species filter and began
    comparing Alabama's 5.6 lb broilers against its 224 eggs per layer. The
    views exist so no caller has to remember the filter.
    """
    conn = dbm.connect()
    try:
        broiler = conn.execute(
            "SELECT DISTINCT size_unit FROM v_broiler_size_stat"
        ).fetchall()
        layer = conn.execute(
            "SELECT DISTINCT size_unit FROM v_layer_egg_stat"
        ).fetchall()
        assert [r[0] for r in broiler] == ["lb live weight"]
        assert [r[0] for r in layer] == ["eggs per layer per year"]

        # Both species really do carry rows for the same state and year --
        # which is exactly why an unfiltered query is dangerous rather than
        # merely untidy.
        overlap = conn.execute("""
            SELECT COUNT(*) FROM v_broiler_size_stat b
            JOIN v_layer_egg_stat l
              ON l.region = b.region AND l.year = b.year
            WHERE b.month IS NULL AND l.month IS NULL
        """).fetchone()[0]
        assert overlap > 0, "expected states appearing in both series"
    finally:
        conn.close()


def test_no_source_file_reads_the_shared_table_directly():
    """Guard the convention rather than trusting everyone to recall it."""
    import pathlib
    pkg = pathlib.Path(__file__).parent.parent / "src" / "counting_chicken_wings"
    offenders = []
    for p in pkg.glob("*.py"):
        # build.py legitimately writes to the table; everyone else reads views.
        if p.name == "build.py":
            continue
        text = p.read_text(encoding="utf-8")
        for clause in ("FROM regional_size_stat", "JOIN regional_size_stat"):
            if clause in text:
                offenders.append(f"{p.name}: {clause}")
    assert not offenders, (
        "read v_broiler_size_stat or v_layer_egg_stat instead: "
        + "; ".join(offenders)
    )
