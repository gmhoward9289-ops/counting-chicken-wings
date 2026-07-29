"""The country dimension.

These exist because of a specific hazard. Before `country` was added,
`region` was a bare TEXT column: loading an Israeli figure would have sat
next to "Alabama" with nothing to distinguish it, and every query that sums
regions would have quietly returned a US-plus-Israel total while still
being labelled United States.

Nobody would have noticed. The number would just have been wrong.

So these tests assert the structural guarantees rather than any value:
every country-scoped row is attributed, the attribution is discovered from
the schema rather than a list someone has to remember to update, and a
national total is only correct when it filters by country.
"""

import sqlite3

import pytest

from counting_chicken_wings.build import build


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("country") / "chickens.db"
    build(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def country_scoped_tables(conn):
    """Tables carrying country_id, discovered from the schema.

    Same reasoning as the audit's cited_tables: a hand-kept list of tables
    goes stale the first time someone adds one, and the failure is silent.
    """
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return [t for t in names
            if "country_id" in {c[1] for c in conn.execute(
                f"PRAGMA table_info({t})")}]


def test_country_scoped_tables_exist(db):
    """Guard the guard: an empty list would pass every test below."""
    assert len(country_scoped_tables(db)) >= 5


def test_every_country_scoped_row_is_attributed(db):
    unattributed = {
        t: n for t in country_scoped_tables(db)
        if (n := db.execute(
            f"SELECT COUNT(*) FROM {t} WHERE country_id IS NULL"
        ).fetchone()[0])
    }
    assert not unattributed, f"rows with no country: {unattributed}"


def test_every_country_id_resolves(db):
    """A dangling country_id is worse than a NULL -- it joins to nothing and
    silently drops rows from an inner join."""
    for t in country_scoped_tables(db):
        orphans = db.execute(
            f"SELECT COUNT(*) FROM {t} x "
            f"LEFT JOIN country c ON c.id = x.country_id "
            f"WHERE c.id IS NULL"
        ).fetchone()[0]
        assert orphans == 0, f"{t} has {orphans} rows with a dangling country"


def test_the_existing_corpus_is_all_american(db):
    """Every figure loaded so far is US. If this starts failing, a second
    country has data and every national aggregate needs re-checking for a
    missing country filter."""
    usa = db.execute("SELECT id FROM country WHERE iso3='USA'").fetchone()[0]
    for t in country_scoped_tables(db):
        other = db.execute(
            f"SELECT COUNT(*) FROM {t} WHERE country_id != ?", (usa,)
        ).fetchone()[0]
        assert other == 0, (
            f"{t} now holds non-US rows -- audit every query that aggregates "
            f"it for a missing country filter before relaxing this test"
        )


def test_israel_is_stubbed_with_no_data(db):
    """Israel exists as a dimension row before any statistic arrives, so the
    schema and loaders are exercised by a second country first."""
    isr = db.execute("SELECT * FROM country WHERE iso3='ISR'").fetchone()
    assert isr is not None, "Israel stub missing"
    assert isr["native_mass_unit"] == "kg"
    assert isr["population"] is None, (
        "population is a statistic and needs a citation before it is set"
    )


def test_reporting_units_are_recorded_not_assumed(db):
    """The likeliest silent error in a cross-country comparison is unit mix.

    The US reports pounds and Israel kilograms; a comparison that forgets is
    off by 2.2x and still looks plausible. Recording the native unit is what
    lets a loader convert deliberately.
    """
    units = dict(db.execute("SELECT iso3, native_mass_unit FROM country"))
    assert units["USA"] == "lb"
    assert units["ISR"] == "kg"
    assert units["USA"] != units["ISR"], (
        "if these ever match, check it is real and not a copy-paste"
    )


def test_national_totals_must_filter_by_country(db):
    """Demonstrates the bug the dimension prevents.

    An unfiltered SUM over a country-scoped table is only right while the
    corpus has one country in it. This asserts the filtered and unfiltered
    answers agree TODAY, and names what changes when they stop agreeing.
    """
    usa = db.execute("SELECT id FROM country WHERE iso3='USA'").fetchone()[0]
    unfiltered = db.execute(
        "SELECT SUM(head_slaughtered) FROM slaughter_stat_year"
    ).fetchone()[0]
    filtered = db.execute(
        "SELECT SUM(head_slaughtered) FROM slaughter_stat_year "
        "WHERE country_id = ?", (usa,)
    ).fetchone()[0]
    assert unfiltered == filtered
