"""Russia: thin by design, and the thinness is the assertion.

Two tonnage rows from one dated attache report, nothing at 'measured', and
a research trail full of figures that were found and refused -- Rosstat
unreachable (TLS trust), and three recent "chicken" totals that turned out
to be all-poultry (птица) wearing a chicken label. These tests pin the
loaded pair and, more importantly, guard the refusals.
"""

from __future__ import annotations

import sqlite3

import pytest

from counting_chicken_wings.build import build


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("russia") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def rus(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='RUS'").fetchone()[0]


# -- the country row ----------------------------------------------------------

def test_russia_country_row_uses_native_units(conn):
    row = conn.execute(
        "SELECT native_mass_unit, native_currency, population "
        "FROM country WHERE iso3='RUS'"
    ).fetchone()
    assert row["native_mass_unit"] == "kg"
    assert row["native_currency"] == "RUB"
    assert row["population"] is None


# -- the figures ---------------------------------------------------------------

def test_the_two_loaded_rows_and_their_grades(conn):
    rows = {
        r["year"]: (r["value"], r["confidence"], r["provisional"])
        for r in conn.execute(
            """SELECT year, value, confidence, provisional
               FROM output_stat_year
               WHERE country_id=? AND measure='meat_output'""",
            (rus(conn),),
        )
    }
    assert rows[2019] == (pytest.approx(4_668_000), "industry", 0)
    assert rows[2020] == (pytest.approx(4_715_000), "industry", 1)
    assert set(rows) == {2019, 2020}


def test_nothing_russian_is_measured_grade(conn):
    """No Russian figure traces to a government enumeration this project
    could actually read -- Rosstat was unreachable -- so nothing may sit
    above 'industry'. A 'measured' Russian row means someone upgraded a
    grade without upgrading the provenance."""
    hits = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND confidence IN ('measured', 'derived')""",
        (rus(conn),),
    ).fetchone()[0]
    assert hits == 0


def test_the_all_poultry_totals_stayed_out(conn):
    """5.16-5.46 Mt figures are птица (all poultry), not chicken.

    Three published totals for 2023-2024 carry chicken labels over
    all-poultry scopes; the 2021 GAIN forecast (4,725) was a forecast.
    None may appear as a loaded value.
    """
    values = [
        r[0] for r in conn.execute(
            """SELECT value FROM output_stat_year WHERE country_id=?""",
            (rus(conn),),
        )
    ]
    for banned in (4_725_000, 5_156_000, 5_340_000, 5_420_000, 5_460_000):
        assert not any(v == pytest.approx(banned) for v in values), banned


def test_only_meat_output_no_regions(conn):
    measures = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT measure FROM output_stat_year WHERE country_id=?",
            (rus(conn),),
        )
    }
    assert measures == {"meat_output"}
    assert conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND region IS NOT NULL""",
        (rus(conn),),
    ).fetchone()[0] == 0


# -- the facts -----------------------------------------------------------------

@pytest.mark.parametrize("slug", [
    "russia-poultry-not-broken-out-by-species",
    "russia-2023-poultry-meat-three-way-conflict",
    "russia-poultry-union-reports-all-poultry-not-broiler",
])
def test_russia_facts_are_loaded_and_cited(conn, slug):
    row = conn.execute(
        """SELECT f.headline, s.slug AS src FROM fact f
           JOIN source s ON s.id = f.source_id WHERE f.slug=?""", (slug,)
    ).fetchone()
    assert row is not None, f"{slug} missing"
    assert row["src"], f"{slug} has no citation"
