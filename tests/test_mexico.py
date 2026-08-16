"""Mexico: the figures, and the limits on what they can be used to claim.

Mirrors tests/test_israel.py. The half that matters here is different from
Israel's: Israel's gap was "CBS measures scale but not count." Mexico's gap
is "SIAP measures a great deal but this project could not reach it", so
national tonnage arrived secondhand (a USDA attaché report, a peer-reviewed
citation) and is graded accordingly - never 'measured' for the secondhand
figures, and a genuine, documented conflict on state ranking that must not
be silently resolved by loading one side of it.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from counting_chicken_wings.build import build

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("mexico") / "t.db"
    build(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def mex(conn) -> int:
    return conn.execute("SELECT id FROM country WHERE iso3='MEX'").fetchone()[0]


# -- the country row ----------------------------------------------------------

def test_mexico_country_row_uses_native_units(conn):
    row = conn.execute(
        "SELECT native_mass_unit, native_currency FROM country WHERE iso3='MEX'"
    ).fetchone()
    assert row["native_mass_unit"] == "kg"
    assert row["native_currency"] == "MXN"


def test_population_is_null_so_no_per_capita_claim_can_be_made(conn):
    """Mexico's per-capita trap is the same shape as Israel's, in reverse.

    Israel's per-capita RANK was contested. Mexico's per-capita LEVEL is
    contested - five sources, a ~70% spread - and neither is safe to build a
    claim on, so population stays NULL for every country in the corpus.
    """
    rows = conn.execute(
        "SELECT iso3, population FROM country ORDER BY iso3"
    ).fetchall()
    # The one exact-roster assertion in the suite (the country tests
    # elsewhere use supersets): adding a country means updating this line
    # and no other.
    assert {r["iso3"] for r in rows} == {"CAN", "DEU", "GBR", "ISR", "MEX", "USA"}
    assert all(r["population"] is None for r in rows)


# -- the figures ---------------------------------------------------------------

def test_national_output_is_loaded_in_tonnes_not_pounds(conn):
    units = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT unit FROM output_stat_year WHERE country_id=?",
            (mex(conn),),
        )
    }
    assert units == {"tonnes"}
    assert not any("lb" in u or "usd" in u.lower() for u in units)


def test_2019_figure_is_measured_via_peer_reviewed_citation(conn):
    row = conn.execute(
        """SELECT value, confidence, unit FROM output_stat_year
           WHERE country_id=? AND measure='meat_output' AND year=2019""",
        (mex(conn),),
    ).fetchone()
    assert row["value"] == pytest.approx(3_447_600)
    assert row["unit"] == "tonnes"
    assert row["confidence"] == "measured"


def test_2023_2024_figures_are_industry_grade_not_measured(conn):
    """The USDA attaché report is government-published but self-disclaimed.

    Its own PSD table is annotated "Not official USDA data", and it quotes
    SIAP secondhand rather than being SIAP's own publication - one step
    further removed than Israel's CBS tables ever were. 'industry' is the
    honest grade even though source_type is 'government'.
    """
    rows = {
        r["year"]: (r["value"], r["confidence"], r["provisional"])
        for r in conn.execute(
            """SELECT year, value, confidence, provisional FROM output_stat_year
               WHERE country_id=? AND measure='meat_output' AND year IN (2023, 2024)""",
            (mex(conn),),
        )
    }
    assert rows[2023] == (pytest.approx(3_888_000), "industry", 0)
    assert rows[2024] == (pytest.approx(3_985_000), "industry", 1)


def test_2025_forecast_is_not_loaded(conn):
    """This project loads reported/estimated actuals, never a forecast year."""
    n = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND measure='meat_output' AND year=2025""",
        (mex(conn),),
    ).fetchone()[0]
    assert n == 0


# -- what Mexico cannot answer, and must not silently claim to -----------------

def test_mexico_has_no_head_count_at_any_grade(conn):
    """UNA's weekly figure is deliberately not annualized into this table.

    Multiplying ~39.3 million/week by 52 would assert a constant weekly
    rate nobody published. The corpus has no Mexican head_slaughtered row
    at all - not even at industry grade - and that absence is the point,
    not an oversight.
    """
    assert conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND measure='head_slaughtered'""",
        (mex(conn),),
    ).fetchone()[0] == 0
    assert conn.execute(
        """SELECT COUNT(*) FROM slaughter_stat_year WHERE country_id=?""",
        (mex(conn),),
    ).fetchone()[0] == 0


def test_mexico_has_no_inventory_or_output_value(conn):
    """No standing flock and no peso-denominated output value were sourced."""
    measures = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT measure FROM output_stat_year WHERE country_id=?",
            (mex(conn),),
        )
    }
    assert measures == {"meat_output"}


def test_mexico_has_no_subnational_rows(conn):
    """The state breakdown is a documented gap, not a silently-skipped one.

    SIAP's own by-state table was unreachable from this research pass, and
    the partial pictures that ARE reachable (a 2019 peer-reviewed figure
    naming four states, a 2024 trade-press figure naming five, a
    conflicting ordinal ranking from a US attaché report) disagree with
    each other on state rank for 2023-24 and do not reconcile against a
    grand total the way Israel's district table did. No districts: block
    was built from them - see docs/MEXICO-PLAN.md.
    """
    n = conn.execute(
        """SELECT COUNT(*) FROM output_stat_year
           WHERE country_id=? AND region IS NOT NULL""", (mex(conn),)
    ).fetchone()[0]
    assert n == 0


def test_us_shaped_tables_stay_us_only(conn):
    """The country dimension exists so a total cannot silently double-count."""
    for table in ("regional_size_stat", "regional_production_year",
                  "regional_census_stat", "slaughter_stat_year"):
        n = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE country_id=?", (mex(conn),)
        ).fetchone()[0]
        assert n == 0, f"{table} unexpectedly holds Mexican rows"


def test_no_per_capita_figure_leaked_into_the_corpus(conn):
    """Five sources give five different Mexican per-capita chicken figures.

    None is safe to publish - see docs/MEXICO-PLAN.md's headline-trap
    section - so none may appear in a fact body, exactly as Israel's three
    per-capita figures may not.
    """
    for value in ("22.4", "28.7", "34.5", "35.82", "37.75"):
        hits = conn.execute(
            "SELECT COUNT(*) FROM fact WHERE body LIKE ?", (f"%{value}%",)
        ).fetchone()[0]
        assert hits == 0, f"per-capita figure {value} appears in a fact"


def test_no_world_rank_claim_leaked_into_the_corpus(conn):
    """Three sources give three different "Nth largest producer" claims.

    5th, 6th, and "1st in the world" for what reads as a narrower product
    definition all appear in the research pass; none is safe to publish as
    Mexico's rank, and the plan is explicit that no version of this claim
    should ship.
    """
    hits = conn.execute(
        "SELECT COUNT(*) FROM fact WHERE body LIKE '%largest%producer%'"
    ).fetchone()[0]
    assert hits == 0


# -- the facts ------------------------------------------------------------------

@pytest.mark.parametrize("slug", [
    "mexico-ave-vs-pollo-taxonomy",
    "mexico-self-sufficiency-eighty-percent",
    "mexico-veracruz-consistent-state-leader",
    "mexico-weekly-throughput-not-annualized",
    "mexico-tif-inspection-not-fsis-equivalent",
])
def test_mexico_facts_are_loaded_and_cited(conn, slug):
    row = conn.execute(
        """SELECT f.headline, s.slug AS src FROM fact f
           JOIN source s ON s.id = f.source_id WHERE f.slug=?""", (slug,)
    ).fetchone()
    assert row is not None, f"{slug} missing"
    assert row["src"], f"{slug} has no citation"


def test_the_taxonomy_fact_names_both_categories(conn):
    """The carne de ave / carne de pollo distinction must be spelled out.

    A fact that merely says "Mexico distinguishes poultry meat" without
    naming which category is broiler-specific would not actually resolve
    the taxonomy question the way docs/MEXICO-PLAN.md requires.
    """
    body = conn.execute(
        "SELECT body FROM fact WHERE slug='mexico-ave-vs-pollo-taxonomy'"
    ).fetchone()[0]
    assert "carne de ave" in body
    assert "carne de pollo" in body


def test_the_self_sufficiency_fact_quotes_figures_that_are_actually_loaded(conn):
    """A fact that contradicts the corpus is worse than no fact.

    The self-sufficiency fact cites the 2023 production figure in its
    prose, so that figure must match the row actually loaded.
    """
    body = conn.execute(
        "SELECT body FROM fact WHERE slug='mexico-self-sufficiency-eighty-percent'"
    ).fetchone()[0]
    stored = conn.execute(
        """SELECT value FROM output_stat_year
           WHERE country_id=? AND measure='meat_output' AND year=2023""",
        (mex(conn),),
    ).fetchone()[0]
    assert stored == pytest.approx(3_888_000)
    assert f"{3_888_000:,}" in body


def test_the_weekly_throughput_fact_does_not_state_an_annual_figure(conn):
    """The fact must carry UNA's own weekly unit, not a manufactured annual one.

    ~39.3 million/week x 52 = ~2,043,600,000/year. That number must never
    appear in this fact, because this project never computed it -- doing so
    would assert a constant weekly rate nobody published.
    """
    body = conn.execute(
        "SELECT body FROM fact WHERE slug='mexico-weekly-throughput-not-annualized'"
    ).fetchone()[0]
    assert "39.3 million" in body
    assert "per week" in body or "week" in body
    for annualized in ("2,043,600,000", "2.04 billion", "2,043,600"):
        assert annualized not in body


def test_mexico_facts_do_not_leak_into_israel_or_us_context(conn):
    """Sanity check: Mexico facts cite Mexico sources, not Israeli ones."""
    rows = conn.execute(
        """SELECT f.slug, s.slug AS src FROM fact f
           JOIN source s ON s.id = f.source_id
           WHERE f.slug LIKE 'mexico-%'"""
    ).fetchall()
    assert len(rows) == 5
    for r in rows:
        assert not r["src"].startswith("cbs-")
        assert "israel" not in r["src"] and "toi-" not in r["src"]
