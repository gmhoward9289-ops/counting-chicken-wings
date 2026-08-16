"""Canada: the first non-US country with a government head count and tonnage.

Israel's tests exist mostly to assert what CBS cannot answer. Canada's are the
opposite shape: StatCan publishes head slaughtered AND meat output, by
province, same year, same survey, at 'measured' grade -- so these tests assert
that the strongest claim survives loading intact, and that the two traps the
research documented (the live-vs-eviscerated weight basis, the Atlantic
aggregate masquerading as an eleventh province) cannot re-enter silently.
"""

from __future__ import annotations

import sqlite3

import pytest

from counting_chicken_wings.build import build


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("canada") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def can(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='CAN'").fetchone()[0]


# -- the figures -------------------------------------------------------------

def test_national_head_count_is_measured_grade(conn):
    """The figure Israel never had: a government-enumerated slaughter count."""
    row = conn.execute(
        """SELECT value, unit, confidence FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered'
             AND year=2025 AND region IS NULL""",
        (can(conn),),
    ).fetchone()
    assert row["value"] == pytest.approx(806_000)      # thousand head
    assert row["unit"] == "thousand_head"
    # 'measured', not 'industry': registered-plant slaughter reports, per
    # StatCan's survey methodology. This is the grade Israel's head count
    # could not earn, and the whole reason Canada leads with it.
    assert row["confidence"] == "measured"


def test_national_output_is_loaded_in_tonnes(conn):
    row = conn.execute(
        """SELECT value, unit, confidence FROM output_stat_year
           WHERE country_id=? AND measure='meat_output'
             AND year=2025 AND region IS NULL""",
        (can(conn),),
    ).fetchone()
    assert row["value"] == pytest.approx(1_416_554)
    assert row["unit"] == "tonnes"
    assert row["confidence"] == "measured"


def test_value_is_in_canadian_dollars_not_us(conn):
    row = conn.execute(
        """SELECT value, unit FROM output_stat_year
           WHERE country_id=? AND measure='output_value'
             AND year=2025 AND region IS NULL""",
        (can(conn),),
    ).fetchone()
    assert row["unit"] == "CAD_million"
    assert row["value"] == pytest.approx(4060.369, abs=0.001)


def test_no_canadian_row_is_stored_in_us_units(conn):
    """StatCan reports kilograms and Canadian dollars; nothing converts."""
    units = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT unit FROM output_stat_year WHERE country_id=?",
            (can(conn),),
        )
    }
    assert units == {"thousand_head", "tonnes", "CAD_million"}
    assert not any("lb" in u or "usd" in u.lower() for u in units)


def test_five_year_series_for_all_three_measures(conn):
    """2021-2025, no gaps, for head count, tonnage and value alike."""
    for measure in ("head_slaughtered", "meat_output", "output_value"):
        years = [
            r[0] for r in conn.execute(
                """SELECT year FROM output_stat_year
                   WHERE country_id=? AND measure=? AND region IS NULL
                   ORDER BY year""", (can(conn), measure))
        ]
        assert years == [2021, 2022, 2023, 2024, 2025], measure


def test_the_head_series_rises_every_year(conn):
    """The Daily's "fifth consecutive year-over-year increase", asserted."""
    values = [
        r[0] for r in conn.execute(
            """SELECT value FROM output_stat_year
               WHERE country_id=? AND measure='head_slaughtered'
                 AND region IS NULL ORDER BY year""", (can(conn),))
    ]
    assert values == sorted(values)
    assert len(values) == 5


# -- the contrast with Israel, kept honest -----------------------------------

def test_government_only_view_keeps_the_canadian_head_count(conn):
    """min_confidence=measured keeps Canada countable. Israel it does not.

    This is the entire point of the Canada pass: the same filter that strips
    Israel's head count (industry grade, a trade-press interview) leaves
    Canada's standing, because StatCan enumerated it.
    """
    n = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered'
             AND confidence IN ('measured','derived')""",
        (can(conn),),
    ).fetchone()[0]
    assert n > 0


def test_statcan_rows_are_all_measured(conn):
    grades = {
        r[0] for r in conn.execute(
            """SELECT DISTINCT o.confidence FROM output_stat_year o
               JOIN source s ON s.id = o.source_id
               WHERE o.country_id=? AND s.slug LIKE 'statcan-%'""",
            (can(conn),))
    }
    assert grades == {"measured"}


def test_population_is_null_so_the_per_capita_figure_stays_a_fact(conn):
    """35.64 kg/person ships as AAFC's published ratio, not as a division.

    Loading a population would invite deriving a per-capita figure the
    corpus already holds as a dated government-published fact -- and would
    require sourcing, dating and defending a population estimate nothing
    else in the corpus needs.
    """
    pop = conn.execute(
        "SELECT population FROM country WHERE iso3='CAN'"
    ).fetchone()[0]
    assert pop is None

    body = conn.execute(
        "SELECT body FROM fact WHERE slug='canada-per-capita-disappearance'"
    ).fetchone()[0]
    assert "35.64" in body
    # And the ratio never leaked into the statistics table as a number.
    assert conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND value = 35.64""", (can(conn),)
    ).fetchone()[0] == 0


def test_us_tables_did_not_gain_canadian_rows(conn):
    """The country dimension exists so a total cannot silently double-count."""
    for table in ("regional_size_stat", "regional_production_year",
                  "regional_census_stat", "slaughter_stat_year"):
        n = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE country_id=?", (can(conn),)
        ).fetchone()[0]
        assert n == 0, f"{table} unexpectedly holds Canadian rows"


# -- provinces ---------------------------------------------------------------

def test_provincial_partition_reconciles(conn):
    """The opposite finding from Israel's 4.76% gap, asserted per measure.

    Heads reconcile EXACTLY: six named provinces plus the Atlantic aggregate
    sum to precisely 806,000 thousand birds, because every level of table
    32-10-0118-01 partitions the same registered-plant count. The weight
    rows sum one thousand kg OVER the published national total -- StatCan
    rounds each series row to the nearest thousand kg independently, and the
    one-unit gap was confirmed against the WDS API itself, so it is asserted
    here at its exact size rather than absorbed into a tolerance: if it ever
    grows past one rounding unit, that is a real discrepancy, not rounding.
    """
    for measure, slack in (("head_slaughtered", 0), ("meat_output", 1)):
        parts = conn.execute(
            """SELECT COALESCE(SUM(value), 0) FROM output_stat_year
               WHERE country_id=? AND measure=? AND region IS NOT NULL
                 AND region_level IN ('province','district')""",
            (can(conn), measure),
        ).fetchone()[0]
        national = conn.execute(
            """SELECT value FROM output_stat_year
               WHERE country_id=? AND measure=? AND year=2025
                 AND region IS NULL""",
            (can(conn), measure),
        ).fetchone()[0]
        assert parts - national == slack, measure

        # And the source's own total row agrees with the national block.
        total_row = conn.execute(
            """SELECT value FROM output_stat_year
               WHERE country_id=? AND measure=? AND region_level='total'""",
            (can(conn), measure),
        ).fetchone()[0]
        assert total_row == national, measure


def test_region_levels_are_data_not_prose(conn):
    """Ten provinces, one aggregate, one total -- per measure, and no more.

    The Atlantic aggregate is a StatCan-defined statistical region, loaded at
    'district' precisely so a reader counting Canadian provinces gets ten,
    not eleven. Counting it as a province would be the double-counting trap
    Israel's level column exists to prevent.
    """
    levels = dict(conn.execute(
        """SELECT region_level, COUNT(*) FROM output_stat_year
           WHERE country_id=? AND region IS NOT NULL
           GROUP BY region_level""", (can(conn),)
    ).fetchall())
    # Two districts blocks (head_slaughtered and meat_output), each holding
    # 1 total + 1 Atlantic aggregate + 10 provinces (6 valued, 4 suppressed).
    assert levels == {"total": 2, "district": 2, "province": 20}

    atlantic = {
        r[0] for r in conn.execute(
            """SELECT DISTINCT region_level FROM output_stat_year
               WHERE country_id=? AND region='Atlantic'""", (can(conn),))
    }
    assert atlantic == {"district"}


def test_suppressed_atlantic_provinces_carry_no_value_and_are_not_zero(conn):
    """Presence without volume, per StatCan's own securityLevelCode."""
    rows = conn.execute(
        """SELECT region, value, region_level FROM output_stat_year
           WHERE country_id=? AND suppressed=1""", (can(conn),)
    ).fetchall()
    names = {r["region"] for r in rows}
    assert names == {"Newfoundland and Labrador", "Prince Edward Island",
                     "Nova Scotia", "New Brunswick"}
    assert all(r["value"] is None for r in rows)
    assert all(r["region_level"] == "province" for r in rows)
    # Suppressed in BOTH measures' blocks: four provinces, twice over.
    assert len(rows) == 8


def test_provincial_rows_keep_their_measure_not_marketed(conn):
    """Canada's provinces report the national concepts, not CBS's 'marketed'.

    The loader's default of 'marketed' exists for Israel's file, which never
    states a measure. Canada's blocks state theirs, and a Canadian row
    landing as 'marketed' would mean the default swallowed the declaration --
    the exact regression the multi-block districts change could introduce.
    """
    measures = {
        r[0] for r in conn.execute(
            """SELECT DISTINCT measure FROM output_stat_year
               WHERE country_id=? AND region IS NOT NULL""", (can(conn),))
    }
    assert measures == {"head_slaughtered", "meat_output"}
    assert "marketed" not in measures


# -- the weight-basis trap ---------------------------------------------------

def test_derived_weight_is_same_year_same_grade(conn):
    """1.76 kg/bird, eviscerated basis, and honestly 'derived' for once.

    Israel's derived weight is 'industry' grade with a one-year gap because
    its parents are. Canada's two parents are both StatCan, both 'measured',
    both 2025 -- so the view's own promotion rule fires and the gap is zero.
    """
    row = conn.execute(
        """SELECT * FROM v_output_derived_weight
           WHERE iso3='CAN' AND head_year=2025""",
    ).fetchone()
    assert row is not None
    # 1,416,554 tonnes over 806.0 million birds. An eviscerated-basis
    # average -- pointedly NOT a live weight, which for a broiler would run
    # roughly 30% heavier.
    assert row["kg_per_head"] == pytest.approx(1.7575, abs=0.001)
    assert row["confidence"] == "derived"
    assert row["year_gap"] == 0


def test_cfc_live_weight_figures_are_never_loaded_as_statistics(conn):
    """The 'What NOT to do' rule from the plan, enforced.

    CFC publishes farm size and producer price per kg LIVE weight; StatCan's
    figures are eviscerated. Dividing across bases would understate live
    weight by a dressing percentage while looking derived and legitimate. So
    the CFC report may ground facts, but no statistic row may cite it.
    """
    n = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year o
           JOIN source s ON s.id = o.source_id
           WHERE s.slug='cfc-annual-report-2025'"""
    ).fetchone()[0]
    assert n == 0

    # The fact channel is the right one, and it is used.
    facts = conn.execute(
        """SELECT COUNT(*) FROM fact f JOIN source s ON s.id = f.source_id
           WHERE s.slug='cfc-annual-report-2025'"""
    ).fetchone()[0]
    assert facts > 0


# -- the culture and structure facts -----------------------------------------

@pytest.mark.parametrize("slug", [
    "canada-per-capita-disappearance",
    "canada-quota-not-demand",
    "canada-two-weight-bases-one-report",
])
def test_canada_facts_are_loaded_and_cited(conn, slug):
    row = conn.execute(
        """SELECT f.headline, s.slug AS src FROM fact f
           JOIN source s ON s.id = f.source_id WHERE f.slug=?""", (slug,)
    ).fetchone()
    assert row is not None, f"{slug} missing"
    assert row["src"], f"{slug} has no citation"


def test_the_scale_comparison_holds_against_the_us(conn):
    """806 million against 9.58 billion: roughly 12x, not 35x.

    The plan states Canada is ~11.9x smaller than the US -- a claim over two
    loaded figures, so the corpus must keep supporting it or the prose rots.
    """
    can_head = conn.execute(
        """SELECT value FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered'
             AND year=2025 AND region IS NULL""", (can(conn),)
    ).fetchone()[0]                                     # thousand head
    us_head = conn.execute(
        """SELECT s.head_slaughtered FROM slaughter_stat_year s
           JOIN country c ON c.id = s.country_id
           WHERE c.iso3='USA' ORDER BY s.year DESC LIMIT 1"""
    ).fetchone()[0]                                     # head
    ratio = us_head / (can_head * 1000)
    assert 10 < ratio < 14
