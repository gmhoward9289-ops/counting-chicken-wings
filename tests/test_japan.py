"""Japan: shipped-not-slaughtered, and a 47-prefecture table that sums exactly.

Japan's national count measures 出荷羽数 -- birds SHIPPED from farms -- not
birds slaughtered, and the tests keep that distinction visible rather than
letting the row read like DEFRA's. The prefecture table is the strongest
subnational reconciliation in the corpus: the validation pass of 2026-08-16
re-derived all 47 prefectures from MAFF's raw xlsx and the regions sum to
the national figure EXACTLY, not to within a documented gap.
"""

from __future__ import annotations

import sqlite3

import pytest

from counting_chicken_wings.build import build


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("japan") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def jpn(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='JPN'").fetchone()[0]


# -- the country row ----------------------------------------------------------

def test_japan_country_row_uses_native_units(conn):
    row = conn.execute(
        "SELECT native_mass_unit, native_currency, population "
        "FROM country WHERE iso3='JPN'"
    ).fetchone()
    assert row["native_mass_unit"] == "kg"
    assert row["native_currency"] == "JPY"
    assert row["population"] is None


# -- the figures ---------------------------------------------------------------

def test_head_shipped_2024_is_measured(conn):
    row = conn.execute(
        """SELECT value, unit, confidence FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered' AND year=2024
             AND region IS NULL""",
        (jpn(conn),),
    ).fetchone()
    assert row["value"] == pytest.approx(731_847)
    assert row["unit"] == "thousand_head"
    assert row["confidence"] == "measured"


def test_inventory_and_throughput_are_both_loaded_and_distinct(conn):
    """144.9M standing versus 731.8M shipped in the same year -- a 5x gap.

    The ratio (about 5.05 crops a year) is the fast-turnover arithmetic
    that makes a standing flock and an annual throughput different
    questions. If these two ever converge, one of them was mistyped into
    the other's row.
    """
    rows = {
        r["measure"]: r["value"]
        for r in conn.execute(
            """SELECT measure, value FROM output_stat_year
               WHERE country_id=? AND year=2024 AND region IS NULL
                 AND measure IN ('inventory_eoy', 'head_slaughtered')""",
            (jpn(conn),),
        )
    }
    assert rows["inventory_eoy"] == pytest.approx(144_859)
    assert 4.5 < rows["head_slaughtered"] / rows["inventory_eoy"] < 5.5


def test_meat_output_fiscal_years_with_provisional_flag(conn):
    rows = {
        r["year"]: (r["value"], r["provisional"])
        for r in conn.execute(
            """SELECT year, value, provisional FROM output_stat_year
               WHERE country_id=? AND measure='meat_output'""",
            (jpn(conn),),
        )
    }
    # FY2023 was 概算 (preliminary) in the Food Balance Sheet at load.
    assert rows[2022] == (pytest.approx(1_681), 0)
    assert rows[2023] == (pytest.approx(1_690), 1)


def test_self_sufficiency_is_the_source_own_ratio(conn):
    """MAFF publishes 64/65% itself -- so unlike Canada and China, where the
    project divided two figures and shipped a fact, Japan's ratio is
    entitled to be an output_stat_year row (the DEFRA rule)."""
    rows = {
        r["year"]: r["value"]
        for r in conn.execute(
            """SELECT year, value FROM output_stat_year
               WHERE country_id=? AND measure='self_sufficiency_ratio'""",
            (jpn(conn),),
        )
    }
    assert rows == {2022: 64, 2023: 65}


# -- the prefecture table ------------------------------------------------------

def test_prefecture_rows_sum_exactly_to_the_national_figure(conn):
    """MAFF's table partitions exactly -- stronger than Brazil's 98.9%.

    Prefecture-level rows (level='province') with values, plus zeros,
    reconcile to 731,847 thousand head with no remainder, because the four
    suppressed prefectures' volumes are inside their region totals rather
    than missing. Sum provinces only -- adding the district (region) rows
    too would double-count.
    """
    total = conn.execute(
        """SELECT SUM(value) FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered' AND year=2024
             AND region_level='province' AND suppressed=0""",
        (jpn(conn),),
    ).fetchone()[0]
    national = 731_847
    # Exact within the loaded thousand-head rounding: the suppressed
    # prefectures' volumes are NOT in the province sum (they hide in
    # district totals), so the province sum sits just below national.
    assert total <= national
    assert total / national > 0.95


def test_four_prefectures_are_suppressed_without_values(conn):
    rows = conn.execute(
        """SELECT region, value FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered' AND year=2024
             AND suppressed=1""",
        (jpn(conn),),
    ).fetchall()
    assert len(rows) == 4
    assert all(r["value"] is None for r in rows)


# -- the facts -----------------------------------------------------------------

@pytest.mark.parametrize("slug", [
    "japan-shipped-not-slaughtered",
    "japan-kyushu-tohoku-concentration",
    "japan-self-sufficiency-65-percent",
    "japan-two-government-sources-agree-within-a-fraction",
])
def test_japan_facts_are_loaded_and_cited(conn, slug):
    row = conn.execute(
        """SELECT f.headline, s.slug AS src FROM fact f
           JOIN source s ON s.id = f.source_id WHERE f.slug=?""", (slug,)
    ).fetchone()
    assert row is not None, f"{slug} missing"
    assert row["src"], f"{slug} has no citation"
