"""Tests for the builder and the guarantees it is supposed to enforce.

The build is the only thing standing between a typo in a YAML file and a
number appearing on a public website with no citation behind it. These tests
exist to make sure that gate actually holds, rather than trusting that it
does because it did once.
"""

import sqlite3

import pytest

from counting_chicken_wings import build as buildmod
from counting_chicken_wings.build import BuildError, Builder, build


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    """Build the real corpus once and share it across the read-only tests."""
    path = tmp_path_factory.mktemp("build") / "chickens.db"
    build(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# The build produces a coherent database
# ---------------------------------------------------------------------------

def test_build_creates_the_file(tmp_path):
    path = tmp_path / "out.db"
    assert build(path) == path
    assert path.exists() and path.stat().st_size > 0


def test_build_is_idempotent(tmp_path):
    """Rebuilding must replace, never append."""
    path = tmp_path / "out.db"
    build(path)
    first = sqlite3.connect(path).execute(
        "SELECT COUNT(*) FROM source").fetchone()[0]
    build(path)
    second = sqlite3.connect(path).execute(
        "SELECT COUNT(*) FROM source").fetchone()[0]
    assert first == second


def test_core_tables_are_populated(db):
    for table in ("source", "species", "product", "loss_stage",
                  "loss_factor", "mixing_stage", "supply_chain", "fact",
                  "slaughter_stat_year", "regional_size_stat"):
        n = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert n > 0, f"{table} is empty"


def test_foreign_keys_are_intact(db):
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_every_supply_chain_resolves_to_real_stages(db):
    orphans = db.execute("""
        SELECT COUNT(*) FROM supply_chain_stage scs
        LEFT JOIN mixing_stage ms ON ms.id = scs.mixing_stage_id
        WHERE ms.id IS NULL
    """).fetchone()[0]
    assert orphans == 0


def test_exactly_one_default_supply_chain_per_species(db):
    """Defaults are per species now, not global.

    A single global default was the bug: eggs had no chain of their own, so
    they inherited the wing cascade and the audit trail described a cut-up
    line to anyone asking about a carton. Every species that has routes must
    name exactly one default, and no route may be left unscoped.
    """
    rows = db.execute("""
        SELECT COALESCE(s.slug, '(unscoped)') AS species, COUNT(*) AS n
        FROM supply_chain sc
        LEFT JOIN species s ON s.id = sc.species_id
        WHERE sc.is_default = 1
        GROUP BY species
    """).fetchall()
    per_species = {r["species"]: r["n"] for r in rows}

    assert per_species, "no default supply chain anywhere"
    for species, n in per_species.items():
        assert n == 1, f"{species} has {n} defaults"
    assert "(unscoped)" not in per_species, (
        "an unscoped default lets one species borrow another's route"
    )

    # Every species with any route at all needs a default, or a lookup for it
    # raises rather than silently falling through to someone else's chain.
    with_routes = db.execute("""
        SELECT DISTINCT s.slug FROM supply_chain sc
        JOIN species s ON s.id = sc.species_id
    """).fetchall()
    for (slug,) in [tuple(r) for r in with_routes]:
        assert slug in per_species, f"{slug} has routes but no default"


# ---------------------------------------------------------------------------
# The citation guarantee
# ---------------------------------------------------------------------------

def test_no_statistic_lacks_a_citation(db):
    for table in ("product", "product_segment", "producer", "loss_factor",
                  "mixing_stage", "slaughter_stat_year", "regional_size_stat",
                  "husbandry_stat_year", "fact", "production_program"):
        n = db.execute(
            f"SELECT COUNT(*) FROM {table} WHERE source_id IS NULL"
        ).fetchone()[0]
        assert n == 0, f"{table} has uncited rows"


def test_unknown_source_slug_is_rejected(tmp_path):
    """A typo'd citation must fail the build, not silently pass."""
    conn = sqlite3.connect(tmp_path / "t.db")
    conn.executescript(buildmod.SCHEMA.read_text())
    b = Builder(conn)
    b.source["real-source"] = 1
    with pytest.raises(BuildError, match="unknown source"):
        b.src("typo-source", "somewhere")


def test_known_source_slug_resolves(tmp_path):
    conn = sqlite3.connect(tmp_path / "t.db")
    conn.executescript(buildmod.SCHEMA.read_text())
    b = Builder(conn)
    b.source["real-source"] = 7
    assert b.src("real-source", "ctx") == 7


def test_missing_source_is_passed_through_as_none(tmp_path):
    """Optional citations stay optional; NOT NULL columns catch the rest."""
    conn = sqlite3.connect(tmp_path / "t.db")
    conn.executescript(buildmod.SCHEMA.read_text())
    assert Builder(conn).src(None, "ctx") is None


def test_a_failed_build_leaves_no_database_behind(tmp_path, monkeypatch):
    """A half-built database is worse than none -- it would look valid."""
    path = tmp_path / "broken.db"

    def explode(self):
        raise BuildError("simulated failure")

    monkeypatch.setattr(Builder, "taxonomy", explode)
    with pytest.raises(BuildError):
        build(path)
    assert not path.exists()


def test_missing_data_file_is_reported_clearly(monkeypatch, tmp_path):
    monkeypatch.setattr(buildmod, "DATA", tmp_path)
    with pytest.raises(BuildError, match="missing data file"):
        buildmod.load("nope.yaml")


# ---------------------------------------------------------------------------
# Schema constraints actually bite
# ---------------------------------------------------------------------------

def test_loss_factor_rejects_inverted_band(db):
    """lo <= mode <= hi is a CHECK, not a convention."""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO loss_factor
              (loss_stage_id, species_id, survive_lo, survive_mode,
               survive_hi, confidence, source_id)
            VALUES (1, 1, 0.9, 0.5, 0.8, 'estimate', 1)
        """)
    db.rollback()


def test_loss_factor_rejects_nonpositive_survival(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO loss_factor
              (loss_stage_id, species_id, survive_lo, survive_mode,
               survive_hi, confidence, source_id)
            VALUES (1, 1, 0.0, 0.0, 0.0, 'estimate', 1)
        """)
    db.rollback()


def test_confidence_vocabulary_is_closed(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO loss_factor
              (loss_stage_id, species_id, survive_lo, survive_mode,
               survive_hi, confidence, source_id)
            VALUES (1, 1, 0.9, 0.9, 0.9, 'pretty sure', 1)
        """)
    db.rollback()


def test_mixing_stage_rejects_inverted_pool(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO mixing_stage
              (domain_id, slug, label, sequence, pool_lo, pool_mode, pool_hi,
               mixing_kind, source_id, confidence, description)
            VALUES (1, 'bad', 'Bad', 999, 500, 100, 50, 'random', 1,
                    'estimate', 'x')
        """)
    db.rollback()


def test_applies_to_vocabulary_is_closed(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO loss_stage
              (domain_id, slug, label, sequence, phase, applies_to,
               description)
            VALUES (1, 'bad', 'Bad', 998, 'test', 'vibes', 'x')
        """)
    db.rollback()


# ---------------------------------------------------------------------------
# Derived values
# ---------------------------------------------------------------------------

def test_dressing_yield_is_derived_not_stored(db):
    """The view must recompute from the NASS totals every time.

    Storing it would let it drift away from the two figures it comes from,
    which is exactly the failure this project is trying not to have.
    """
    rows = db.execute(
        "SELECT year, certified_rtc_lb, live_weight_lb, dressing_yield "
        "FROM v_dressing_yield ORDER BY year"
    ).fetchall()
    assert rows
    for r in rows:
        assert r["dressing_yield"] == pytest.approx(
            r["certified_rtc_lb"] / r["live_weight_lb"]
        )


def test_dressing_yield_matches_the_documented_figure(db):
    """75.67% for 2025 is quoted in the README and the learning centre."""
    row = db.execute(
        "SELECT dressing_yield FROM v_dressing_yield WHERE year = 2025"
    ).fetchone()
    assert row["dressing_yield"] == pytest.approx(0.7567, abs=1e-4)


def test_cited_factors_view_only_shows_current_rows(db):
    stale = db.execute(
        "SELECT COUNT(*) FROM loss_factor WHERE valid_to IS NOT NULL"
    ).fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM loss_factor").fetchone()[0]
    shown = db.execute("SELECT COUNT(*) FROM v_cited_factors").fetchone()[0]
    assert shown == total - stale


# ---------------------------------------------------------------------------
# Anchor figures -- these are quoted verbatim in the UI
# ---------------------------------------------------------------------------

def test_nass_2025_totals_are_intact(db):
    r = db.execute(
        "SELECT * FROM slaughter_stat_year WHERE year = 2025"
    ).fetchone()
    assert r["head_slaughtered"] == 9_579_797_000
    assert r["live_weight_lb"] == 63_443_212_000
    assert r["certified_rtc_lb"] == 48_006_482_000


def test_a_chicken_has_exactly_two_wings(db):
    """The one hard constant. If this ever changes, the project is wrong."""
    r = db.execute(
        "SELECT * FROM product WHERE slug = 'whole_wing'"
    ).fetchone()
    assert r["units_per_individual_lo"] == 2
    assert r["units_per_individual_mode"] == 2
    assert r["units_per_individual_hi"] == 2
    assert r["is_anatomical_constant"] == 1


def test_state_spread_survives_the_build(db):
    """Ohio-vs-North-Carolina is the learning centre's best hook."""
    rows = dict(db.execute("""
        SELECT region, avg_size FROM v_broiler_size_stat
        WHERE year = 2025 AND month IS NULL
          AND region IN ('Ohio', 'North Carolina')
    """).fetchall())
    assert rows["Ohio"] == pytest.approx(4.6, abs=0.05)
    assert rows["North Carolina"] == pytest.approx(8.4, abs=0.05)
