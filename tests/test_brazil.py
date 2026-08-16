"""Brazil: two real national head counts, and the discipline of loading one.

Canada's tests assert a clean government pairing; Israel's assert a forced
absence. Brazil's assert a CHOICE: IBGE's census-type survey (federal +
state + municipal inspection) outranks ABPA's real-but-narrower
federal-inspection-only figure, so IBGE holds every cell where the two
overlap and ABPA appears only where IBGE has nothing (value) or a different
year (2024 tonnage). Every figure below was re-derived from IBGE's SIDRA
API and ABPA's actual PDF by the validation pass of 2026-08-16.
"""

from __future__ import annotations

import sqlite3

import pytest

from counting_chicken_wings.build import build


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("brazil") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def bra(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='BRA'").fetchone()[0]


# -- the country row ----------------------------------------------------------

def test_brazil_country_row_uses_native_units(conn):
    row = conn.execute(
        "SELECT native_mass_unit, native_currency, population "
        "FROM country WHERE iso3='BRA'"
    ).fetchone()
    assert row["native_mass_unit"] == "kg"
    assert row["native_currency"] == "BRL"
    # ABPA publishes 46.7 kg/person as its own ratio, loaded as a fact --
    # so no denominator ships here, same discipline as every non-US country.
    assert row["population"] is None


# -- the national figures ------------------------------------------------------

def test_head_slaughtered_is_ibge_not_abpa(conn):
    """6.695 billion (IBGE, all inspection tiers), not 5.706 billion (ABPA/MAPA).

    Both are real; they differ by 17% because ABPA's chart cites federal
    inspection only. The schema allows one row per cell, and the census-type
    survey outranks the trade body's citation of a narrower figure. If this
    value ever becomes ~5,706,000, someone has silently swapped the loser in.
    """
    row = conn.execute(
        """SELECT value, unit, confidence FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered' AND year=2025
             AND region IS NULL""",
        (bra(conn),),
    ).fetchone()
    assert row["value"] == pytest.approx(6_695_465)
    assert row["unit"] == "thousand_head"
    assert row["confidence"] == "measured"


def test_meat_output_2025_is_ibge_carcass_tonnes(conn):
    row = conn.execute(
        """SELECT value, unit, confidence FROM output_stat_year
           WHERE country_id=? AND measure='meat_output' AND year=2025
             AND region IS NULL""",
        (bra(conn),),
    ).fetchone()
    assert row["value"] == pytest.approx(14_304_261)
    assert row["unit"] == "tonnes"
    assert row["confidence"] == "measured"


def test_abpa_rows_are_industry_grade_and_do_not_collide_with_ibge(conn):
    """ABPA appears only in cells IBGE does not hold.

    2024 tonnage (IBGE's 2025 row leaves 2024 open) and 2025 output value
    (IBGE's table has no value column at all). Neither may be 'measured' --
    a trade body's own series is 'industry' however good it is.
    """
    rows = {
        (r["measure"], r["year"]): (r["value"], r["confidence"])
        for r in conn.execute(
            """SELECT measure, year, value, confidence FROM output_stat_year
               WHERE country_id=? AND region IS NULL
                 AND confidence='industry'""",
            (bra(conn),),
        )
    }
    assert rows[("meat_output", 2024)] == (pytest.approx(14_972_000), "industry")
    assert rows[("output_value", 2025)] == (pytest.approx(112_600), "industry")
    # And the collision guard itself: exactly one meat_output row per year.
    counts = conn.execute(
        """SELECT year, COUNT(*) AS n FROM output_stat_year
           WHERE country_id=? AND measure='meat_output' AND region IS NULL
           GROUP BY year""",
        (bra(conn),),
    ).fetchall()
    assert all(r["n"] == 1 for r in counts)


def test_implied_carcass_weight_is_plausible(conn):
    """14.30 Mt over 6.695 billion head is ~2.14 kg carcass per bird.

    ABPA's narrower pairing implies 2.68 kg -- the gap between the two is
    the inspection-scope difference wearing a weight, which is why the two
    sources must never be mixed within one calculation.
    """
    rows = {
        r["measure"]: r["value"]
        for r in conn.execute(
            """SELECT measure, value FROM output_stat_year
               WHERE country_id=? AND year=2025 AND region IS NULL
                 AND measure IN ('head_slaughtered', 'meat_output')""",
            (bra(conn),),
        )
    }
    kg = rows["meat_output"] * 1000 / (rows["head_slaughtered"] * 1000)
    assert 1.9 < kg < 2.4, kg


# -- the state breakdown -------------------------------------------------------

def test_state_rows_reconcile_to_within_the_documented_gap(conn):
    """19 published states capture 98.9% of the national total, per measure.

    The ~1.1% remainder is the eight suppressed states -- if this ratio
    drifts far from 0.989, either a state row was mistyped or a suppressed
    state silently gained a value.
    """
    for measure, national in (("head_slaughtered", 6_695_465),
                              ("meat_output", 14_304_261)):
        total = conn.execute(
            """SELECT SUM(value) FROM output_stat_year
               WHERE country_id=? AND measure=? AND year=2025
                 AND region IS NOT NULL AND region_level='province'
                 AND suppressed=0""",
            (bra(conn), measure),
        ).fetchone()[0]
        assert 0.985 < total / national < 0.992, (measure, total)


def test_eight_states_are_suppressed_with_no_value(conn):
    """Suppression is presence-without-volume, never an invented number.

    Seven confidential ("X") plus Amapa ("...", data not available) -- and a
    suppressed row carrying a value would mean someone filled a cell IBGE
    deliberately left empty.
    """
    for measure in ("head_slaughtered", "meat_output"):
        rows = conn.execute(
            """SELECT region, value FROM output_stat_year
               WHERE country_id=? AND measure=? AND year=2025
                 AND suppressed=1""",
            (bra(conn), measure),
        ).fetchall()
        assert len(rows) == 8, measure
        assert all(r["value"] is None for r in rows)
        assert {r["region"] for r in rows} == {
            "Acre", "Amazonas", "Roraima", "Amapa",
            "Rio Grande do Norte", "Alagoas", "Sergipe", "Distrito Federal",
        }


# -- the facts -----------------------------------------------------------------

@pytest.mark.parametrize("slug", [
    "brazil-two-national-headcounts-disagree",
    "brazil-south-exports-more-than-it-produces-share-of",
    "brazil-largest-exporter-not-largest-producer",
    "brazil-breeder-stock-not-broiler-flock",
    "brazil-per-capita-consumption",
])
def test_brazil_facts_are_loaded_and_cited(conn, slug):
    row = conn.execute(
        """SELECT f.headline, s.slug AS src FROM fact f
           JOIN source s ON s.id = f.source_id WHERE f.slug=?""", (slug,)
    ).fetchone()
    assert row is not None, f"{slug} missing"
    assert row["src"], f"{slug} has no citation"
