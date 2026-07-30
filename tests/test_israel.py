"""Israel: the figures, and the limits on what they can be used to claim.

The data half of these tests is ordinary. The half that matters asserts what
Israel *cannot* answer, because that is the failure available here: CBS
publishes no head-slaughtered series, so any code path that produces an Israeli
bird count is producing it from an American assumption.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from counting_chicken_wings.build import build

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from parse_cbs_israel import (  # noqa: E402
    num,
    parse_districts,
    parse_inventory,
    parse_output,
)


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("israel") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def isr(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='ISR'").fetchone()[0]


# -- the figures -------------------------------------------------------------

def test_national_output_is_loaded_in_tonnes(conn):
    row = conn.execute(
        """SELECT value, unit, provisional FROM output_stat_year
           WHERE country_id=? AND measure='meat_output' AND year=2024""",
        (isr(conn),),
    ).fetchone()
    assert row["value"] == pytest.approx(600_072)
    assert row["unit"] == "tonnes"
    # CBS's own asterisk. A provisional figure must not be quoted as final.
    assert row["provisional"] == 1


def test_value_is_in_shekels_not_dollars(conn):
    row = conn.execute(
        """SELECT value, unit FROM output_stat_year
           WHERE country_id=? AND measure='output_value' AND year=2024""",
        (isr(conn),),
    ).fetchone()
    assert row["unit"] == "ILS_million"
    assert row["value"] == pytest.approx(5367.618, abs=0.001)


def test_no_israeli_row_is_stored_in_us_units(conn):
    """The 2.2x error that still looks plausible.

    Israel reports kilograms and shekels. Nothing is converted at load, so a
    pound or a dollar appearing on an Israeli row means a loader converted
    silently -- which is the bug that produces a wrong comparison rather than
    a visible one.
    """
    units = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT unit FROM output_stat_year WHERE country_id=?",
            (isr(conn),),
        )
    }
    assert units == {"tonnes", "ILS_million", "thousand_head"}
    assert not any("lb" in u or "usd" in u.lower() for u in units)


def test_inventory_is_end_of_year_not_throughput(conn):
    """37.9 million is a standing flock, and the measure name says so.

    Broilers turn over several times a year. Reading the inventory as annual
    slaughter understates the answer several times over, so the distinction
    lives in the measure rather than only in a comment.
    """
    row = conn.execute(
        """SELECT value, unit FROM output_stat_year
           WHERE country_id=? AND measure='inventory_eoy' AND year=2024""",
        (isr(conn),),
    ).fetchone()
    assert row["value"] == pytest.approx(37_895)
    assert row["unit"] == "thousand_head"

    measures = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT measure FROM output_stat_year WHERE country_id=?",
            (isr(conn),),
        )
    }
    assert "head_slaughtered" not in measures


def test_long_series_reaches_1960(conn):
    years = [
        r[0] for r in conn.execute(
            """SELECT year FROM output_stat_year
               WHERE country_id=? AND measure='inventory_eoy'
               ORDER BY year""", (isr(conn),))
    ]
    assert years[0] == 1960 and years[-1] == 2024
    assert len(years) == 10


# -- what Israel cannot answer ----------------------------------------------

def test_israel_has_no_head_slaughtered_anywhere(conn):
    """The missing denominator, asserted so nothing quietly fills it.

    If a future loader derives head from tonnage using a US bird weight, this
    fails -- which is the point. Deriving it is allowed only with an Israeli
    weight and a citation, and then this test should be updated deliberately.
    """
    assert conn.execute(
        """SELECT COUNT(*) FROM slaughter_stat_year
           WHERE country_id=? AND head_slaughtered IS NOT NULL""",
        (isr(conn),),
    ).fetchone()[0] == 0


def test_population_is_null_so_no_per_capita_claim_can_be_made(conn):
    """The headline the demo wanted to lead with has no reachable source.

    The Euromeatnews article behind "Israel is the world's highest per-capita
    chicken consumer" now 404s and the WATTAgNet ranking 403s, so population
    stays NULL for both countries rather than being filled with a plausible
    number that would make the claim renderable.
    """
    rows = conn.execute(
        "SELECT iso3, population FROM country ORDER BY iso3"
    ).fetchall()
    assert {r["iso3"] for r in rows} == {"ISR", "USA"}
    assert all(r["population"] is None for r in rows)


# -- districts ---------------------------------------------------------------

def test_districts_exist_so_the_comparison_is_not_lopsided(conn):
    """Israel does have subnational data, which was an open question."""
    n = conn.execute(
        """SELECT COUNT(DISTINCT region) FROM output_stat_year
           WHERE country_id=? AND region IS NOT NULL""", (isr(conn),)
    ).fetchone()[0]
    assert n > 40


def test_suppressed_councils_carry_no_value_and_are_not_zero(conn):
    """Presence without volume, exactly as NASS suppression is handled."""
    rows = conn.execute(
        """SELECT region, value FROM output_stat_year
           WHERE country_id=? AND suppressed=1""", (isr(conn),)
    ).fetchall()
    assert rows, "CBS suppresses several councils; none were loaded"
    assert all(r["value"] is None for r in rows)


def test_district_sum_falls_short_of_national_output_by_about_5pct(conn):
    """The cross-check that fails, asserted so it cannot be quietly absorbed.

    Marketing excludes self-consumption and private sale by CBS's own footnote,
    so the gap is probably real. It is asserted because a reader who adds up
    the districts will find it, and a silent 4.76% discrepancy reads as our
    error rather than as two different measurements.
    """
    country = isr(conn)
    # Districts, not councils. Councils sum lower still because six of them
    # are suppressed, so a council-level sum understates by an unknown amount
    # and is not a cross-check at all -- which is itself worth knowing.
    districts = conn.execute(
        """SELECT COALESCE(SUM(value), 0) FROM output_stat_year
           WHERE country_id=? AND measure='marketed'
             AND notes LIKE 'district%'""", (country,)
    ).fetchone()[0]
    total = conn.execute(
        """SELECT value FROM output_stat_year
           WHERE country_id=? AND measure='marketed'
             AND notes = 'total'""", (country,)
    ).fetchone()[0]
    # The districts do reconcile with the source's own grand total.
    assert districts == pytest.approx(total, abs=0.05)

    output = conn.execute(
        """SELECT value FROM output_stat_year
           WHERE country_id=? AND measure='meat_output' AND year=2024""",
        (country,),
    ).fetchone()[0]
    gap = (output - total) / output
    assert 0.04 < gap < 0.06


def test_the_gap_is_documented_in_the_citation(conn):
    """A discrepancy that lives only in a test is invisible to a reader."""
    notes = conn.execute(
        "SELECT notes FROM source WHERE slug='cbs-st21-04-marketing-2025'"
    ).fetchone()[0]
    assert "4.76" in notes
    assert "self-consumption" in notes


def test_judea_and_samaria_keeps_the_publishers_label_and_caveat(conn):
    """Reported as CBS reports it, with CBS's own restriction recorded.

    The row exists in the source, so dropping it would understate the total;
    renaming it would attribute a label to CBS that CBS did not use. Its
    footnote restricts it to Israeli localities, which is a real limit on what
    the figure covers and belongs with the citation.
    """
    row = conn.execute(
        """SELECT region FROM output_stat_year
           WHERE country_id=? AND region LIKE 'JUDEA%'""", (isr(conn),)
    ).fetchone()
    assert row is not None
    # Footnote markers belong in prose, not in a region identity.
    assert "(" not in row["region"]

    notes = conn.execute(
        "SELECT notes FROM source WHERE slug='cbs-st21-04-marketing-2025'"
    ).fetchone()[0]
    assert "Israeli localities" in notes


def test_outside_regional_councils_is_disambiguated(conn):
    """The same label appears once per district and must not collide."""
    rows = [
        r[0] for r in conn.execute(
            """SELECT region FROM output_stat_year
               WHERE country_id=? AND region LIKE 'Outside regional%'""",
            (isr(conn),))
    ]
    assert len(rows) == 3
    assert len(set(rows)) == 3


def test_national_and_regional_rows_cannot_be_confused(conn):
    """region IS NULL is the national figure; a total is not a region."""
    national = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND region IS NULL""", (isr(conn),)
    ).fetchone()[0]
    assert national == 20        # 5 output + 5 value + 10 inventory years


def test_us_tables_did_not_gain_israeli_rows(conn):
    """The country dimension exists so a total cannot silently double-count."""
    for table in ("regional_size_stat", "regional_production_year",
                  "regional_census_stat", "slaughter_stat_year"):
        n = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE country_id=?", (isr(conn),)
        ).fetchone()[0]
        assert n == 0, f"{table} unexpectedly holds Israeli rows"


# -- parser ------------------------------------------------------------------
#
# Fed synthetic sheets rather than the network, so the suppression and
# duplicate-label handling is testable in CI without CBS being reachable.

def test_num_drops_excel_float_noise():
    assert num("600.07199999999995") == 600.072
    assert num("553.06799999999998") == 553.068


def test_parse_output_splits_value_from_quantity():
    sheet = [
        {"B": "*2024", "C": "2023", "G": "*2024", "H": "2023"},
        {"A": "      Broilers(5)", "B": "5367.6", "C": "5303.8",
         "G": "600.072", "H": "553.068"},
    ]
    output, value = parse_output(sheet)
    assert output[0] == {"year": 2024, "tonnes": 600072.0,
                         "provisional": True}
    assert value[0]["ils_million"] == 5367.6


def test_parse_inventory_reads_ten_year_columns():
    sheet = [
        {"B": "*2024", "C": "2023", "D": "2020", "E": "2015", "F": "2010"},
        {"A": "Broilers(2)", "B": "37895", "C": "34121", "D": "38239",
         "E": "34680", "F": "33594"},
    ]
    rows = parse_inventory(sheet)
    assert [r["year"] for r in rows] == [2024, 2023, 2020, 2015, 2010]
    assert rows[0]["provisional"] is True


def test_parse_districts_marks_suppression_and_hierarchy():
    sheet = [
        {"A": "2024"},
        {"A": "       GRAND TOTAL", "C": "571499.95"},
        {"A": "NORTHERN AND HAIFA DISTRICTS", "C": "236340.64"},
        {"A": "    Al Batof", "C": "-"},
        {"A": "    Golan", "C": "24602.43"},
        {"A": "    Outside regional councils", "C": "8515.94"},
        {"A": "JUDEA AND SAMARIA AREA(3)", "C": "13818.8"},
    ]
    year, rows = parse_districts(sheet)
    assert year == 2024
    by = {r["region"]: r for r in rows}

    assert by["GRAND TOTAL"]["level"] == "total"
    assert by["Al Batof"]["suppressed"] is True
    assert "tonnes" not in by["Al Batof"]
    assert by["Golan"]["parent"] == "NORTHERN AND HAIFA DISTRICTS"
    assert "JUDEA AND SAMARIA AREA" in by        # footnote marker stripped
    assert any(r["region"].startswith("Outside regional councils (")
               for r in rows)
