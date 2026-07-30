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


# Tables that legitimately hold more than one country, each with the reason.
# Everything else is US-only, and the test below is the alarm that fires the
# day that changes -- the whole point being that a second country's rows in a
# table nobody re-checked is how a national aggregate silently double-counts.
MULTI_COUNTRY = {
    "output_stat_year": (
        "Israel's CBS figures, 2026-07-29. Exists precisely because Israeli "
        "reporting does not fit the US-shaped tables: tonnes not pounds, "
        "shekels not dollars, and no head-slaughtered series at all."
    ),
}


def test_us_shaped_tables_stay_us_only(db):
    """The four NASS-shaped tables must not gain a second country by accident.

    Their column names bake in American reporting -- live_weight_lb,
    certified_rtc_lb, value_kusd -- so a foreign row in them is either
    converted (and the conversion is a figure needing a citation) or
    mislabelled. Israeli data goes to output_stat_year instead.

    This replaced a blanket "the whole corpus is American" assertion, which
    fired as designed when Israel landed. Relaxing it to a per-table allowlist
    keeps the alarm for the next table rather than deleting it.
    """
    usa = db.execute("SELECT id FROM country WHERE iso3='USA'").fetchone()[0]
    for t in country_scoped_tables(db):
        if t in MULTI_COUNTRY:
            continue
        other = db.execute(
            f"SELECT COUNT(*) FROM {t} WHERE country_id != ?", (usa,)
        ).fetchone()[0]
        assert other == 0, (
            f"{t} now holds non-US rows. Audit every query that aggregates it "
            f"for a missing country filter, then add it to MULTI_COUNTRY with "
            f"the reason -- do not just delete this assertion."
        )


def test_views_are_the_hazard_when_a_second_country_lands(db):
    """v_broiler_size_stat and v_layer_egg_stat do not filter by country.

    Nothing reads them for a country other than the US today, because Israel's
    rows live in output_stat_year. If Israeli figures ever reach
    regional_size_stat, every consumer of these views starts silently mixing
    countries -- so this asserts the precondition that keeps them safe rather
    than trusting that someone will remember.
    """
    usa = db.execute("SELECT id FROM country WHERE iso3='USA'").fetchone()[0]
    for view in ("v_broiler_size_stat", "v_layer_egg_stat"):
        other = db.execute(
            f"SELECT COUNT(*) FROM {view} WHERE country_id != ?", (usa,)
        ).fetchone()[0]
        assert other == 0, (
            f"{view} now spans countries and does not filter by one. Add a "
            f"country predicate to the view or to every caller."
        )


def test_israel_has_data_but_not_the_denominator(db):
    """Israel is no longer a stub, and what it still cannot answer is asserted.

    CBS publishes broiler output in tonnes, a value in shekels, and an
    end-of-year flock -- but no head slaughtered, which is the denominator the
    count question needs. Population is likewise still NULL: the per-capita
    headline's only citation now 404s.
    """
    isr = db.execute("SELECT * FROM country WHERE iso3='ISR'").fetchone()
    assert isr is not None, "Israel row missing"
    assert isr["native_mass_unit"] == "kg"
    assert isr["population"] is None, (
        "population is a statistic and needs a citation before it is set"
    )

    loaded = db.execute(
        "SELECT COUNT(*) FROM output_stat_year WHERE country_id=?",
        (isr["id"],),
    ).fetchone()[0]
    assert loaded > 0, "Israeli CBS figures are no longer pending"

    assert db.execute(
        """SELECT COUNT(*) FROM slaughter_stat_year
           WHERE country_id=? AND head_slaughtered IS NOT NULL""",
        (isr["id"],),
    ).fetchone()[0] == 0


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


# ---------------------------------------------------------------- can it hold
#
# Every test above reads. None of them wrote, which is why the corpus could
# carry country_id on five tables, pass all of them, and still be unable to
# store a second country: the UNIQUE keys omitted country_id, so an Israeli
# broiler row for a year the US already had was rejected outright. The
# dimension existed and the table could hold exactly one country.
#
# A read-only assertion cannot see that. Only an insert can.

@pytest.mark.parametrize("table, columns, values", [
    ("slaughter_stat_year",
     "(species_id, country_id, year, head_slaughtered, source_id)",
     (2025, 260_000_000)),
    ("husbandry_stat_year",
     "(species_id, country_id, year, mortality_pct, source_id)",
     (2024, 4.2)),
])
def test_a_second_country_can_hold_the_same_species_and_year(
        db, table, columns, values):
    """The key must include country_id, not merely the row.

    Written against a throwaway copy so the corpus itself is untouched.
    """
    year, measure = values
    scratch = sqlite3.connect(":memory:")
    db.backup(scratch)

    broiler = scratch.execute(
        "SELECT id FROM species WHERE slug='broiler'").fetchone()[0]
    isr = scratch.execute(
        "SELECT id FROM country WHERE iso3='ISR'").fetchone()[0]
    src = scratch.execute("SELECT id FROM source LIMIT 1").fetchone()[0]

    # The US row for this species and year already exists in the corpus.
    existing = scratch.execute(
        f"SELECT COUNT(*) FROM {table} WHERE species_id=? AND year=?",
        (broiler, year)).fetchone()[0]
    assert existing, (
        f"fixture assumption broken: no US {table} row for {year}, so this "
        f"test would pass without proving anything"
    )

    try:
        scratch.execute(
            f"INSERT INTO {table} {columns} VALUES (?,?,?,?,?)",
            (broiler, isr, year, measure, src))
    except sqlite3.IntegrityError as e:
        pytest.fail(
            f"{table} cannot hold Israel alongside the US for {year}: {e}. "
            f"country_id is missing from the UNIQUE key."
        )
    finally:
        scratch.close()
