"""China: three tonnage rows, and the absences that outnumber them.

The world's second-largest producer enters the corpus with LESS loaded than
Russia-sized countries a tenth its size could carry -- three meat_output
rows, all secondhand, all 'industry' -- because everything else on offer
either aggregated ducks and geese into "chicken" (NBS's 禽肉) or could not
be reconciled with its own tonnage (the 14.84-billion-bird head count).
These tests pin both halves: what was loaded, and that the tempting wrong
figures stayed out. Values re-derived from both GAIN PDFs and the PSD
Online CSVs by the validation pass of 2026-08-16.
"""

from __future__ import annotations

import sqlite3

import pytest

from counting_chicken_wings.build import build


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("china") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def chn(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='CHN'").fetchone()[0]


# -- the country row ----------------------------------------------------------

def test_china_country_row_uses_native_units(conn):
    row = conn.execute(
        "SELECT native_mass_unit, native_currency, population "
        "FROM country WHERE iso3='CHN'"
    ).fetchone()
    assert row["native_mass_unit"] == "kg"
    assert row["native_currency"] == "CNY"
    assert row["population"] is None


# -- the figures ---------------------------------------------------------------

def test_meat_output_series_is_industry_grade_throughout(conn):
    """Secondhand via USDA FAS attache reports, so never 'measured'.

    The reports' own PSD table is annotated "Not official USDA data" --
    government publisher, non-government provenance, same treatment
    Mexico's GAIN figures established. 2025 stays provisional: it was an
    in-year "New Post" estimate at load (16,200), and PSD Online has since
    moved the official figure to 16,500 -- the flag is doing its job.
    """
    rows = {
        r["year"]: (r["value"], r["confidence"], r["provisional"])
        for r in conn.execute(
            """SELECT year, value, confidence, provisional
               FROM output_stat_year
               WHERE country_id=? AND measure='meat_output'""",
            (chn(conn),),
        )
    }
    assert rows[2023] == (pytest.approx(14_800_000), "industry", 0)
    assert rows[2024] == (pytest.approx(15_350_000), "industry", 0)
    assert rows[2025] == (pytest.approx(16_200_000), "industry", 1)
    assert set(rows) == {2023, 2024, 2025}


def test_units_are_tonnes(conn):
    units = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT unit FROM output_stat_year WHERE country_id=?",
            (chn(conn),),
        )
    }
    assert units == {"tonnes"}


# -- what China must NOT answer with what it has --------------------------------

def test_no_head_count_at_any_grade(conn):
    """The 14.84-billion-bird figure exists and is deliberately not here.

    Its own report's tonnage (22.11 Mt for white+yellow alone) misses the
    loaded USDA series by 44%, and neither states a weight basis. A head
    count that cannot be squared with the tonnage beside it would imply a
    bird weight nobody measured. If this test fails, read
    docs/CHINA-PLAN.md, "The production-estimate conflict", before
    concluding the row belongs.
    """
    assert conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered'""",
        (chn(conn),),
    ).fetchone()[0] == 0


def test_only_meat_output_is_loaded(conn):
    """No inventory, no output value, no self-sufficiency ROW.

    The self-sufficiency percentages are this project's own division and
    ship as a fact (china-self-sufficiency), not as an output_stat_year
    row -- the same line Canada drew.
    """
    measures = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT measure FROM output_stat_year WHERE country_id=?",
            (chn(conn),),
        )
    }
    assert measures == {"meat_output"}


def test_no_subnational_rows(conn):
    """Provincial poultry data exists but is 家禽 (all poultry), not chicken.

    Loading it under a broiler species would repeat the exact aggregation
    error the NBS 禽肉 exclusion exists to avoid, at province scale.
    """
    assert conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND region IS NOT NULL""",
        (chn(conn),),
    ).fetchone()[0] == 0


def test_nbs_all_poultry_aggregate_did_not_leak_into_output_rows(conn):
    """26.6 Mt is 禽肉 -- chicken + duck + goose -- and must never load as chicken.

    The largest single number in China's own communique is the most
    tempting wrong figure in this country's research pass. No loaded
    output row may carry it.
    """
    hits = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND value BETWEEN 26_000_000 AND 27_000_000""",
        (chn(conn),),
    ).fetchone()[0]
    assert hits == 0


# -- the facts -----------------------------------------------------------------

@pytest.mark.parametrize("slug", [
    "china-ave-vs-pollo-taxonomy",
    "china-second-largest-producer",
    "china-production-estimate-conflict",
    "china-self-sufficiency",
    "china-broiler-headcount-not-loaded",
])
def test_china_facts_are_loaded_and_cited(conn, slug):
    row = conn.execute(
        """SELECT f.headline, s.slug AS src FROM fact f
           JOIN source s ON s.id = f.source_id WHERE f.slug=?""", (slug,)
    ).fetchone()
    assert row is not None, f"{slug} missing"
    assert row["src"], f"{slug} has no citation"
