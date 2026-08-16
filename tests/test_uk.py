"""United Kingdom: the figures, and why this country's data looks different.

Israel's tests (test_israel.py) spend most of their weight asserting what
Israel *cannot* answer, because CBS publishes no head-slaughtered series.
The UK is close to the opposite case: DEFRA publishes head_slaughtered
directly, at government grade, so the interesting assertions here are about
what DID land cleanly (a real head count, a real cross-check against
FAOSTAT) and what was deliberately left out despite being available in the
source data (a GB/NI split, a UK-wide weight-per-bird) rather than about an
absence forced by the source.
"""

from __future__ import annotations

import sqlite3

import pytest

from counting_chicken_wings.build import build

ROOT = __file__


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("uk") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def gbr(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='GBR'").fetchone()[0]


# -- the country row itself --------------------------------------------------

def test_uk_country_row_uses_native_units(conn):
    row = conn.execute(
        "SELECT native_mass_unit, native_currency, population "
        "FROM country WHERE iso3='GBR'"
    ).fetchone()
    assert row is not None, "GBR row missing from countries.yaml"
    assert row["native_mass_unit"] == "kg"
    assert row["native_currency"] == "GBP"
    # Deliberately NULL. See docs/UK-PLAN.md: ONS has an uncontested UK
    # population figure, but no per-capita CONSUMPTION figure was sourced,
    # so population stays out until both land together.
    assert row["population"] is None


# -- the figures --------------------------------------------------------------

def test_head_slaughtered_is_measured_grade_government(conn):
    """Unlike Israel, the UK's head count comes straight from DEFRA.

    Israel's equivalent figure lives at 'industry' grade because nobody
    enumerated it -- it came from a named official's press interview. The
    UK's is a government survey result, so it must be 'measured', and this
    is the contrast worth asserting rather than assuming.
    """
    row = conn.execute(
        """SELECT value, unit, confidence FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered' AND year=2024""",
        (gbr(conn),),
    ).fetchone()
    assert row is not None
    assert row["value"] == pytest.approx(1131.6)
    assert row["unit"] == "million_head"
    assert row["confidence"] == "measured"


def test_meat_output_is_in_tonnes_not_pounds(conn):
    row = conn.execute(
        """SELECT value, unit FROM output_stat_year
           WHERE country_id=? AND measure='meat_output' AND year=2024""",
        (gbr(conn),),
    ).fetchone()
    assert row["unit"] == "thousand_tonnes_carcase_weight"
    assert row["value"] == pytest.approx(1832.7)


def test_no_uk_row_is_stored_in_us_or_israeli_units(conn):
    """The same 2.2x-and-still-plausible trap the Israel tests guard against.

    Nothing here is converted or re-scaled at load, so a pound, a dollar, a
    shekel, or an expanded (x1,000 or x1,000,000) figure appearing on a UK
    row means a loader silently converted or rescaled -- exactly the bug
    that produces a wrong comparison rather than a visible one.
    """
    units = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT unit FROM output_stat_year WHERE country_id=?",
            (gbr(conn),),
        )
    }
    assert units == {
        "million_head", "thousand_tonnes_carcase_weight", "percent",
    }
    assert not any(
        "lb" in u or "usd" in u.lower() or "ils" in u.lower() for u in units
    )


def test_self_sufficiency_ratio_is_loaded_and_volume_based(conn):
    """DEFRA's own answer to the question ISRAEL-PLAN.md left as 'not attempted'."""
    rows = dict(conn.execute(
        """SELECT year, value FROM output_stat_year
           WHERE country_id=? AND measure='self_sufficiency_ratio'""",
        (gbr(conn),),
    ))
    assert rows[2024] == pytest.approx(83)
    assert rows[2023] == pytest.approx(82)
    assert rows[2022] == pytest.approx(84)

    prov = conn.execute(
        """SELECT provisional FROM output_stat_year
           WHERE country_id=? AND measure='self_sufficiency_ratio'
             AND year=2024""",
        (gbr(conn),),
    ).fetchone()[0]
    assert prov == 1


# -- inventory-vs-throughput, and stock-vs-flow more generally --------------

def test_chicks_placed_is_not_confused_with_head_slaughtered(conn):
    """Placements are a throughput PROXY, not throughput itself.

    Same discipline as Israel's CBS-quarterly chicks_placed rows: a chick
    placed is a bird entering the system, and some fraction never reaches
    market. The two measures must stay distinct rows with distinct values.
    """
    rows = dict(conn.execute(
        """SELECT measure, value FROM output_stat_year
           WHERE country_id=? AND year=2024
             AND measure IN ('chicks_placed', 'head_slaughtered')""",
        (gbr(conn),),
    ))
    assert set(rows) == {"chicks_placed", "head_slaughtered"}
    assert rows["chicks_placed"] != rows["head_slaughtered"]
    # Placed must exceed slaughtered -- mortality runs the other direction.
    assert rows["chicks_placed"] > rows["head_slaughtered"]
    gap = (rows["chicks_placed"] - rows["head_slaughtered"]) / rows["chicks_placed"]
    assert 0.0 < gap < 0.05, f"grow-out mortality gap looks wrong: {gap:.1%}"


def test_no_standing_flock_is_loaded_for_the_uk(conn):
    """The UK has no inventory_eoy row -- unlike Israel, which has one and
    nothing else head-shaped. Asserted so a future load does not invent a
    number DEFRA never published (see docs/UK-PLAN.md, 'standing flock').
    """
    n = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND measure='inventory_eoy'""",
        (gbr(conn),),
    ).fetchone()[0]
    assert n == 0


# -- the country must not gain a phantom subnational panel -------------------

def test_uk_has_no_subnational_rows(conn):
    """DEFRA itself stopped publishing any nation-level split in July 2025.

    Unlike Israel, which has a genuine 47-region table, the UK ships
    national figures only -- and a region row appearing here would be
    inventing a choropleth granularity the source does not currently
    support. See docs/UK-PLAN.md, 'Why there is no subnational UK
    breakdown'.
    """
    n = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND region IS NOT NULL""",
        (gbr(conn),),
    ).fetchone()[0]
    assert n == 0


def test_uk_rows_all_have_region_level_null(conn):
    """National rows carry no region_level -- region IS NULL already says so."""
    n = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND region_level IS NOT NULL""",
        (gbr(conn),),
    ).fetchone()[0]
    assert n == 0


# -- cross-country isolation --------------------------------------------------

def test_us_and_israeli_tables_did_not_gain_uk_rows(conn):
    """The country dimension exists so a total cannot silently double-count.

    Mirrors test_israel.py's test_us_tables_did_not_gain_israeli_rows.
    """
    for table in ("regional_size_stat", "regional_production_year",
                  "regional_census_stat", "slaughter_stat_year",
                  "husbandry_stat_year"):
        cols = {c[1] for c in conn.execute(f"PRAGMA table_info({table})")}
        if "country_id" not in cols:
            continue
        n = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE country_id=?", (gbr(conn),)
        ).fetchone()[0]
        assert n == 0, f"{table} unexpectedly holds UK rows"


def test_uk_row_count_is_exactly_what_was_loaded(conn):
    """Guards against a stray duplicate row from a future edit to the file.

    5 head_slaughtered years + 5 meat_output years + 3 chicks_placed years +
    3 self_sufficiency_ratio years = 16.
    """
    n = conn.execute(
        "SELECT COUNT(*) FROM output_stat_year WHERE country_id=?",
        (gbr(conn),),
    ).fetchone()[0]
    assert n == 16


# -- audit: every UK row must cite a real source -----------------------------

def test_every_uk_source_exists_and_is_government_graded(conn):
    slugs = {
        r[0] for r in conn.execute(
            """SELECT DISTINCT s.slug FROM output_stat_year o
               JOIN source s ON s.id = o.source_id
               WHERE o.country_id=?""", (gbr(conn),))
    }
    assert slugs == {
        "defra-poultry-slaughter-2026-07",
        "defra-poultry-hatcheries-2026-07",
        "defra-agriculture-uk-2024",
    }

    types = {
        r[0] for r in conn.execute(
            """SELECT DISTINCT s.source_type FROM output_stat_year o
               JOIN source s ON s.id = o.source_id
               WHERE o.country_id=?""", (gbr(conn),))
    }
    # Every UK figure loaded here is DEFRA -- a government source, unlike
    # Israel's head count, which is 'trade_press' at industry grade.
    assert types == {"government"}


def test_all_uk_rows_are_measured_confidence(conn):
    """No UK figure in this pass rests on an industry estimate.

    Contrast with Israel, where the head count is industry-grade because
    nobody enumerated it. If a future UK figure arrives at a lower grade,
    this test should be relaxed deliberately, not silently.
    """
    grades = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT confidence FROM output_stat_year WHERE country_id=?",
            (gbr(conn),),
        )
    }
    assert grades == {"measured"}
