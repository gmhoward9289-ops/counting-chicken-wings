"""Poland: the first country to arrive through a supranational source.

The UK's tests assert what DEFRA answered cleanly; Israel's assert what CBS
could not answer at all. Poland's assert a third thing: what it means to
load a country from Eurostat rather than from its own national agency. The
figures are `measured` (an exhaustive census under Regulation (EC) No
1165/2008), the head count and tonnage come from the same table in the same
year — and the deliberate absences (no EU aggregate, no broiler-pure split,
no kg-per-head) are as load-bearing as the figures, because each one is a
place where inventing a plausible number would have been easy.
"""

from __future__ import annotations

import sqlite3

import pytest

from counting_chicken_wings.build import build


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("poland") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def pol(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='POL'").fetchone()[0]


# -- the country row itself --------------------------------------------------

def test_poland_country_row_uses_native_units(conn):
    row = conn.execute(
        "SELECT native_mass_unit, native_currency, population "
        "FROM country WHERE iso3='POL'"
    ).fetchone()
    assert row is not None, "POL row missing from countries.yaml"
    assert row["native_mass_unit"] == "kg"
    # In the EU but not the eurozone -- a future output-value figure arrives
    # in zloty, and EUR here would be exactly the kind of silently wrong
    # default the native_currency column exists to prevent.
    assert row["native_currency"] == "PLN"
    # Deliberately NULL, same discipline as every country since Israel: no
    # per-capita consumption figure was sourced, so no denominator ships.
    assert row["population"] is None


# -- the figures -------------------------------------------------------------

def test_head_slaughtered_is_measured_grade(conn):
    """Head count at government grade, from a census, via Eurostat.

    Israel's head count is 'industry' because nobody enumerated it. Poland's
    comes from an exhaustive census of slaughterhouses harmonised under
    Regulation (EC) No 1165/2008 -- it must be 'measured', and that this
    holds through a supranational republisher rather than a national agency
    is the thing this country's data exists to prove.
    """
    row = conn.execute(
        """SELECT value, unit, confidence FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered' AND year=2024""",
        (pol(conn),),
    ).fetchone()
    assert row is not None
    assert row["value"] == pytest.approx(1297913.7)
    assert row["unit"] == "thousand_head"
    assert row["confidence"] == "measured"


def test_meat_output_carries_stated_carcass_basis_unit(conn):
    """The unit name carries the basis, because Eurostat states one.

    Israel's tonnage never states live-versus-carcass and its unit says so
    by omission. Eurostat's regulation defines the poultry basis outright
    ("65% chicken", carcass), so Poland's unit is entitled to the word
    'carcass' -- and a future edit that drops it would be discarding stated
    provenance, not shortening a label.
    """
    row = conn.execute(
        """SELECT value, unit, confidence FROM output_stat_year
           WHERE country_id=? AND measure='meat_output' AND year=2024""",
        (pol(conn),),
    ).fetchone()
    assert row is not None
    assert row["value"] == pytest.approx(2433.02)
    assert row["unit"] == "thousand_tonnes_carcass_weight"
    assert row["confidence"] == "measured"


def test_head_and_tonnage_are_same_year_same_grade(conn):
    """The Canada property, from a second source family.

    Same table, same census, same year, both halves 'measured' -- for every
    loaded year, not just the newest. This is the pairing Israel never had
    and the reason the EU entry is worth a research pass.
    """
    rows = conn.execute(
        """SELECT year,
                  COUNT(DISTINCT measure) AS measures,
                  COUNT(DISTINCT confidence) AS grades,
                  MAX(confidence) AS grade
           FROM output_stat_year
           WHERE country_id=? AND measure IN ('head_slaughtered', 'meat_output')
           GROUP BY year""",
        (pol(conn),),
    ).fetchall()
    assert len(rows) == 5, "expected the 2020-2024 series, both measures"
    for r in rows:
        assert r["measures"] == 2, f"{r['year']}: one half of the pair missing"
        assert r["grades"] == 1 and r["grade"] == "measured"


def test_implied_carcass_weight_is_plausible(conn):
    """Tonnage over head count lands near 1.9 kg -- consistency, not a figure.

    Both series in thousands, so the scales cancel. A ratio near a broiler
    carcass weight says the two series share a basis; a ratio near 2.6 kg
    would say the tonnage was secretly live weight. This asserts the
    internal check that the data files describe in prose.
    """
    rows = {
        r["measure"]: r["value"]
        for r in conn.execute(
            """SELECT measure, value FROM output_stat_year
               WHERE country_id=? AND year=2024
                 AND measure IN ('head_slaughtered', 'meat_output')""",
            (pol(conn),),
        )
    }
    kg_per_bird = rows["meat_output"] * 1_000_000 / (rows["head_slaughtered"] * 1000)
    assert 1.5 < kg_per_bird < 2.2, kg_per_bird


# -- the deliberate absences -------------------------------------------------

def test_no_eu_aggregate_was_loaded(conn):
    """No 'EU' pseudo-country, because Eurostat publishes no EU aggregate.

    apro_mt_pann returns zero EU-27 poultry values in any year -- verified,
    not assumed. Summing 27 member states ourselves would be our computation
    wearing Eurostat's citation. If this test ever fails because someone
    added an EU row, that row needs a source that actually publishes an EU
    total, not a sum.
    """
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM country "
        "WHERE iso3 IN ('EU', 'EUR', 'EU27') OR name LIKE '%European Union%'"
    ).fetchone()
    assert row["n"] == 0


def test_no_regional_breakdown_pretends_to_exist(conn):
    """National rows only -- no Polish voivodeship split was sourced.

    Eurostat's table is per-member-state, and no subnational Polish source
    was attempted this pass. Unlike Israel (real 50-council table) and
    Canada (real province split), Poland ships national-only, and a
    regional row appearing here without a new source would be invented
    geography.
    """
    row = conn.execute(
        """SELECT COUNT(*) AS n FROM output_stat_year
           WHERE country_id=? AND region IS NOT NULL""",
        (pol(conn),),
    ).fetchone()
    assert row["n"] == 0
