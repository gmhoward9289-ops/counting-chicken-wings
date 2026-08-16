"""Germany: broiler-specific figures from Destatis, with the split intact.

The category trap for any EU country is loading an all-poultry aggregate
under the broiler species -- Eurostat's own harmonised table publishes
Germany at 668 million poultry head for 2024, and Destatis's broiler
(Jungmasthühner) figure is 627 million with even the Suppenhühner (boiling
hens) excluded. The validation pass of 2026-08-16 confirmed the loaded
series is the narrow one. These tests keep it that way.
"""

from __future__ import annotations

import sqlite3

import pytest

from counting_chicken_wings.build import build


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("germany") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def deu(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='DEU'").fetchone()[0]


# -- the country row ----------------------------------------------------------

def test_germany_country_row_uses_native_units(conn):
    row = conn.execute(
        "SELECT native_mass_unit, native_currency, population "
        "FROM country WHERE iso3='DEU'"
    ).fetchone()
    assert row["native_mass_unit"] == "kg"
    assert row["native_currency"] == "EUR"
    assert row["population"] is None


# -- the figures ---------------------------------------------------------------

def test_head_slaughtered_series_is_measured_and_broiler_scale(conn):
    """The Jungmasthühner series, not all-poultry.

    Every year must sit well below Eurostat's all-poultry Germany figure
    (668,210 thousand head for 2024): a value near or above it means an
    aggregate was silently promoted to "broiler".
    """
    rows = {
        r["year"]: (r["value"], r["confidence"])
        for r in conn.execute(
            """SELECT year, value, confidence FROM output_stat_year
               WHERE country_id=? AND measure='head_slaughtered'""",
            (deu(conn),),
        )
    }
    assert rows[2022] == (pytest.approx(631_132.8), "measured")
    assert rows[2023] == (pytest.approx(631_476.2), "measured")
    assert rows[2024][0] == pytest.approx(626_700)
    assert rows[2025][0] == pytest.approx(640_300)
    assert all(v < 660_000 for v, _ in rows.values())


def test_recent_years_are_provisional_settled_years_are_not(conn):
    """2024 and 2025 come from press releases that call themselves
    vorläufig; 2022-2023 come from the settled annual table."""
    rows = {
        r["year"]: r["provisional"]
        for r in conn.execute(
            """SELECT year, provisional FROM output_stat_year
               WHERE country_id=? AND measure='head_slaughtered'""",
            (deu(conn),),
        )
    }
    assert rows == {2022: 0, 2023: 0, 2024: 1, 2025: 1}


def test_meat_output_in_tonnes_with_plausible_bird_weight(conn):
    rows = {
        r["year"]: r["value"]
        for r in conn.execute(
            """SELECT year, value FROM output_stat_year
               WHERE country_id=? AND measure='meat_output'""",
            (deu(conn),),
        )
    }
    assert rows[2022] == pytest.approx(1_074_500)
    assert rows[2023] == pytest.approx(1_086_100)
    # Implied carcass weight ~1.7 kg/bird -- German broilers are slaughtered
    # lighter than Poland's chicken mix; a ratio near 2.2+ would suggest an
    # all-poultry tonnage snuck in above a broiler head count.
    kg = rows[2023] * 1000 / (631_476.2 * 1000)
    assert 1.5 < kg < 2.0, kg


def test_no_subnational_rows(conn):
    """The Niedersachsen concentration story ships as facts (with their own
    sources), not as a Länder table -- none was loaded this pass."""
    assert conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND region IS NOT NULL""",
        (deu(conn),),
    ).fetchone()[0] == 0


# -- the facts -----------------------------------------------------------------

@pytest.mark.parametrize("slug", [
    "germany-poultry-skin-included",
    "germany-niedersachsen-half-the-flock",
    "germany-niedersachsen-2014-broiler-share",
    "germany-selfsufficiency-hides-which-bird",
])
def test_germany_facts_are_loaded_and_cited(conn, slug):
    row = conn.execute(
        """SELECT f.headline, s.slug AS src FROM fact f
           JOIN source s ON s.id = f.source_id WHERE f.slug=?""", (slug,)
    ).fetchone()
    assert row is not None, f"{slug} missing"
    assert row["src"], f"{slug} has no citation"
