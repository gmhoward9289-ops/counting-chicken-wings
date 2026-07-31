"""Maple: the third domain, and the first individual that survives harvest.

Eggs grew `yield_period_days` on a 365-day cycle. Maple is the first subject
to use that field for a period that is NOT a year -- a sugar maple runs for
about six weeks, once, in late winter -- and reading its season as a year
would overstate a tree's output roughly eightfold.

So the invariants under test are shapes, not figures. The season length, the
sap-to-syrup band and the per-tree yields will all get refined the day USDA
NASS's maple report is loaded; none of that may break these:

  * the period is read from the data, never assumed to be a year
  * boiling is a mass stage, so it cannot make trees fewer -- the 40:1 is
    already priced into a figure quoted in gallons of syrup
  * the concentration is stored as UVM's rule and its Brix range, not as the
    single folk constant that rule happens to produce at 2 Brix
  * nothing maple claims a grade above `industry`, because nothing here is
    measured
"""

import pytest

from counting_chicken_wings import db as dbm
from counting_chicken_wings.model import (
    MixingStage,
    RecurringYield,
    recurring_floor,
    run,
)

# Gallons of SYRUP per tree per season, boil already priced in.
SYRUP_LO = 0.116
SYRUP_MODE = 0.233
SYRUP_HI = 0.500

# Roughly six weeks of run, against a hen's year.
SEASON_DAYS = 45
YEAR_DAYS = 365

# UVM's Jones Rule of 86: gallons of sap per gallon of syrup = 86 / degrees
# Brix, with sap running 1% to 5%.
JONES = 86.0
BRIX = (1.0, 2.0, 5.0)

# Trees represented. Sap is mixed the moment it is collected, so this cascade
# starts wide and only ever widens.
STAND = [
    MixingStage("tank", "Collection tank", 800, "random"),
    MixingStage("evaporator", "Evaporator batch", 800, "random"),
    MixingStage("barrel", "Bulk barrel", 3000, "random"),
    MixingStage("packer", "Packer blend", 100000, "random"),
]


def _syrup(window_days):
    return RecurringYield(
        units_per_period=SYRUP_MODE,
        period_days=SEASON_DAYS,
        window_days=window_days,
    )


# ---------------------------------------------------------------------------
# The period is data, not an assumption
# ---------------------------------------------------------------------------

def test_the_season_is_not_a_year():
    """The whole reason maple was worth landing after eggs."""
    conn = dbm.connect()
    try:
        maple = dbm.get_product(conn, "maple_syrup_gallon")
        egg = dbm.get_product(conn, "table_egg")
        assert maple["yield_period_days"] == pytest.approx(SEASON_DAYS)
        assert egg["yield_period_days"] == pytest.approx(YEAR_DAYS)
        assert maple["yield_period_days"] != egg["yield_period_days"]
    finally:
        conn.close()


def test_reading_the_season_as_a_year_overstates_the_tree_eightfold():
    """The regression this subject exists to catch.

    Same rate, same window, one wrong denominator: 0.233 gallons per 45 days
    read as 0.233 per 365 days makes a tree look 365/45 times less productive
    and demands that many more trees.
    """
    honest = _syrup(SEASON_DAYS)
    misread = RecurringYield(
        units_per_period=SYRUP_MODE, period_days=YEAR_DAYS,
        window_days=SEASON_DAYS,
    )
    ratio = honest.units_per_individual / misread.units_per_individual
    assert ratio == pytest.approx(YEAR_DAYS / SEASON_DAYS, rel=1e-9)
    assert 8.0 < ratio < 8.2

    trees_honest = recurring_floor(1, honest)[1]
    trees_misread = recurring_floor(1, misread)[1]
    assert trees_misread / trees_honest == pytest.approx(ratio, rel=1e-9)


def test_a_gallon_over_one_season_is_a_handful_of_trees():
    """About a quart a tree, so a gallon is a few trees' whole spring."""
    assert recurring_floor(1, _syrup(SEASON_DAYS))[1] == pytest.approx(
        1 / SYRUP_MODE, rel=1e-9)


def test_the_band_puts_a_gallon_between_two_and_nine_trees():
    lo_trees = 1 / SYRUP_HI      # the most productive tree in the band
    hi_trees = 1 / SYRUP_LO      # the least
    assert lo_trees == pytest.approx(2.0)
    assert 8.0 < hi_trees < 9.0


@pytest.mark.parametrize("window", [1, 7, 45, 365, 3650])
def test_a_longer_window_never_needs_more_trees(window):
    """Monotone in the window, exactly as for hens -- and a maple keeps
    answering for a century, so long windows are not hypothetical here."""
    shorter = recurring_floor(1, _syrup(window))[1]
    longer = recurring_floor(1, _syrup(window * 2))[1]
    assert longer <= shorter + 1e-12


def test_a_tree_has_no_daily_ceiling_so_the_two_floors_coincide():
    """A hen's floor is hard because ovulation caps her at one egg a day.
    Sap flow is weather: there is no physiological per-day cap to record, so
    the corpus records none and the hard floor collapses onto the expected
    one rather than being invented."""
    ry = _syrup(SEASON_DAYS)
    assert ry.max_units_per_day is None
    assert ry.cap_per_individual is None
    hard, expected = recurring_floor(1, ry)
    assert hard == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("window", [0, -1])
def test_an_incoherent_window_is_rejected(window):
    with pytest.raises(ValueError):
        _syrup(window)


def test_make_recurring_reads_the_period_off_the_row():
    conn = dbm.connect()
    try:
        maple = dbm.get_product(conn, "maple_syrup_gallon")
        ry = dbm.make_recurring(maple, SEASON_DAYS)
        assert ry is not None
        assert ry.period_days == pytest.approx(SEASON_DAYS)
        assert ry.units_per_period == pytest.approx(SYRUP_MODE)
        assert ry.max_units_per_day is None
        assert ry.window_days == SEASON_DAYS
    finally:
        conn.close()


def test_run_derives_the_yield_from_the_season_not_the_year():
    ry = _syrup(SEASON_DAYS)
    res = run(1, SYRUP_MODE, [], STAND, recurring=ry)
    assert res.window_days == SEASON_DAYS
    assert res.units_per_individual == pytest.approx(SYRUP_MODE, rel=1e-9)
    assert res.floor == pytest.approx(1 / SYRUP_MODE, rel=1e-9)


# ---------------------------------------------------------------------------
# applies_to discipline: boiling cannot make trees fewer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("chain", ["commodity_syrup", "sugarhouse_direct"])
def test_boiling_is_mass_only_so_it_cannot_move_a_count(chain):
    """The biggest number in the subject, and it must change nothing.

    Two reasons compound, as with saffron's drying: mass stages never touch
    counts, and `maple_syrup_gallon` is already a syrup-basis figure, so
    applying the concentration would divide the answer a second time.
    """
    conn = dbm.connect()
    try:
        stages = dbm.load_loss_stages(conn, "sugar_maple",
                                      "maple_syrup_gallon", chain_slug=chain)
        boiling = [s for s in stages if s.slug == "maple_boiling"]
        assert boiling, "the boiling stage should load for maple"
        assert boiling[0].applies_to == "mass"
        assert not boiling[0].affects_count()

        ry = _syrup(SEASON_DAYS)
        res = run(1, SYRUP_MODE, stages, STAND, recurring=ry)
        assert res.required == pytest.approx(res.floor, rel=1e-9)
    finally:
        conn.close()


def test_applying_the_concentration_twice_is_the_wrong_answer():
    """Pin the number the bug would produce, so it cannot creep back in.

    Dividing the floor by the surviving fraction again turns four trees into
    roughly two hundred -- a tree made to look forty times less productive
    than it is.
    """
    conn = dbm.connect()
    try:
        stages = dbm.load_loss_stages(conn, "sugar_maple",
                                      "maple_syrup_gallon",
                                      chain_slug="commodity_syrup")
        boiling = next(s for s in stages if s.slug == "maple_boiling")
        res = run(1, SYRUP_MODE, stages, STAND, recurring=_syrup(SEASON_DAYS))
        double_counted = res.floor / boiling.survive_mode
        assert double_counted > 180.0
        assert res.required != pytest.approx(double_counted, rel=1e-3)
        assert res.required == pytest.approx(res.floor, rel=1e-9)
    finally:
        conn.close()


def test_every_maple_loss_stage_in_the_default_chain_is_mass():
    """Nothing in maple's default chain removes a tree. If a count stage is
    ever added the answer moves, which is fine -- but it must be a deliberate
    edit, not something that arrives sideways with a mass figure."""
    conn = dbm.connect()
    try:
        stages = dbm.load_loss_stages(conn, "sugar_maple",
                                      "maple_syrup_gallon",
                                      chain_slug="commodity_syrup")
        assert stages
        assert all(s.applies_to == "mass" for s in stages)
        assert not any(s.affects_count() for s in stages)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# The band is sugar content, not measurement error
# ---------------------------------------------------------------------------

def test_the_concentration_is_stored_as_a_band_not_a_constant():
    conn = dbm.connect()
    try:
        boiling = next(
            s for s in dbm.load_loss_stages(conn, "sugar_maple",
                                            "maple_syrup_gallon",
                                            chain_slug="commodity_syrup")
            if s.slug == "maple_boiling")
        assert boiling.survive_lo < boiling.survive_mode < boiling.survive_hi
        # 1 Brix to 5 Brix is a five-fold spread in which every value is right.
        assert boiling.survive_hi / boiling.survive_lo == pytest.approx(
            5.0, rel=0.02)
    finally:
        conn.close()


@pytest.mark.parametrize("brix,attr", [
    (1.0, "survive_lo"),     # thinnest sap: 86 gallons boiled to one
    (2.0, "survive_mode"),   # typical: 43, which is the famous "40"
    (5.0, "survive_hi"),     # sweetest sap survives best: 17
])
def test_the_stored_band_reproduces_the_jones_rule(brix, attr):
    """gallons of sap per gallon of syrup = 86 / Brix, at each end and in
    the middle. Stored as surviving fractions, so invert to compare."""
    conn = dbm.connect()
    try:
        boiling = next(
            s for s in dbm.load_loss_stages(conn, "sugar_maple",
                                            "maple_syrup_gallon",
                                            chain_slug="commodity_syrup")
            if s.slug == "maple_boiling")
        surviving = {
            "survive_lo": boiling.survive_lo,
            "survive_mode": boiling.survive_mode,
            "survive_hi": boiling.survive_hi,
        }[attr]
        sap_per_syrup = 1 / surviving
        assert sap_per_syrup == pytest.approx(JONES / brix, rel=0.01)
    finally:
        conn.close()


def test_the_folk_forty_to_one_sits_inside_the_band_rather_than_replacing_it():
    """40:1 is the 2 Brix case rounded. Storing it alone would have hidden
    the variable that produces it, so it must be inside the range, not the
    range itself."""
    conn = dbm.connect()
    try:
        boiling = next(
            s for s in dbm.load_loss_stages(conn, "sugar_maple",
                                            "maple_syrup_gallon",
                                            chain_slug="commodity_syrup")
            if s.slug == "maple_boiling")
        folk = 1 / 40.0
        assert boiling.survive_lo < folk < boiling.survive_hi
        assert 1 / boiling.survive_mode == pytest.approx(JONES / 2.0, rel=0.01)
        assert 1 / boiling.survive_mode != pytest.approx(40.0, rel=1e-3)
    finally:
        conn.close()


def test_the_concentration_cites_the_rule_and_the_rule_exists():
    conn = dbm.connect()
    try:
        boiling = next(
            s for s in dbm.load_loss_stages(conn, "sugar_maple",
                                            "maple_syrup_gallon",
                                            chain_slug="commodity_syrup")
            if s.slug == "maple_boiling")
        assert boiling.source_slug == "uvm-jones-rule-86"
        row = conn.execute("SELECT slug FROM source WHERE slug = ?",
                           (boiling.source_slug,)).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_the_per_tree_yield_is_a_range_because_two_services_disagree():
    """UMaine says 5-15 gallons of sap a taphole, NY State Maple says 10-20.
    That disagreement is kept, not averaged away, so the yield spans roughly
    four times and the figure is not claimed as a constant."""
    conn = dbm.connect()
    try:
        prod = dbm.get_product(conn, "maple_syrup_gallon")
        lo = prod["units_per_individual_lo"]
        mode = prod["units_per_individual_mode"]
        hi = prod["units_per_individual_hi"]
        assert lo < mode < hi
        assert lo == pytest.approx(SYRUP_LO)
        assert hi == pytest.approx(SYRUP_HI)
        assert 4.0 < hi / lo < 4.5
        assert prod["is_anatomical_constant"] == 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Grade honesty -- nothing maple is measured
# ---------------------------------------------------------------------------

HUMAN_ONLY_GRADES = {"measured", "derived", "study"}


def test_no_maple_loss_figure_claims_a_human_only_grade():
    """Every input is industry and the combination is our own arithmetic.
    A later commit that promotes one of these without landing a source that
    supports it should fail here."""
    conn = dbm.connect()
    try:
        rows = conn.execute(
            """SELECT ls.slug AS stage, lf.confidence AS confidence
               FROM loss_factor lf
               JOIN species sp ON sp.id = lf.species_id
               JOIN loss_stage ls ON ls.id = lf.loss_stage_id
               WHERE sp.slug = 'sugar_maple'"""
        ).fetchall()
        assert rows
        for r in rows:
            assert r["confidence"] not in HUMAN_ONLY_GRADES, r["stage"]
            assert r["confidence"] == "industry", r["stage"]
    finally:
        conn.close()


def test_maple_pool_sizes_are_estimates_like_every_other_subject():
    """Nobody in the trade measures pool sizes, so nobody may claim to."""
    conn = dbm.connect()
    try:
        rows = conn.execute(
            """SELECT ms.slug AS slug, ms.confidence AS confidence,
                      src.slug AS source
               FROM mixing_stage ms
               JOIN domain d ON d.id = ms.domain_id
               JOIN source src ON src.id = ms.source_id
               WHERE d.slug = 'forestry'"""
        ).fetchall()
        assert rows
        for r in rows:
            assert r["confidence"] == "estimate", r["slug"]
            assert r["source"] == "project-estimate-mixing", r["slug"]
    finally:
        conn.close()


def test_the_floor_is_a_yield_floor_not_an_anatomical_one():
    """A tree has no fixed number of gallons in it the way a chicken has two
    wings, so calling this floor anatomical would launder a rule of thumb
    into a biological constant."""
    soft = run(1, SYRUP_MODE, [], STAND, recurring=_syrup(SEASON_DAYS),
               anatomical=False, floor_source="uvm-jones-rule-86")
    step = soft.trace[0]
    assert step.kind == "floor"
    assert step.confidence == "industry"
    assert step.confidence not in HUMAN_ONLY_GRADES
    assert step.source_slug == "uvm-jones-rule-86"


def test_maple_declares_no_measured_output_series():
    """USDA NASS does publish a maple report; we have not loaded it. The
    honest record of that is an absent stat_category and no output rows, not
    an estimated series wearing a measured grade."""
    conn = dbm.connect()
    try:
        row = conn.execute(
            "SELECT stat_category FROM species WHERE slug = 'sugar_maple'"
        ).fetchone()
        assert row["stat_category"] is None
        n = conn.execute(
            """SELECT COUNT(*) AS n FROM output_stat_year o
               JOIN species s ON s.id = o.species_id
               WHERE s.slug = 'sugar_maple'"""
        ).fetchone()["n"]
        assert n == 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# The control: wings are untouched
# ---------------------------------------------------------------------------

def test_wings_are_untouched_by_the_recurring_maple_path():
    res = run(12, 2.0, [], STAND)
    assert res.window_days is None
    assert res.hard_floor is None
    assert res.floor == pytest.approx(6.0)
    assert res.distinct_ceiling == 12.0
    assert 6.0 <= res.distinct_mean <= 12.0


def test_a_wing_is_still_timeless_and_still_walks_its_own_chain():
    conn = dbm.connect()
    try:
        wing = dbm.get_product(conn, "whole_wing")
        assert dbm.make_recurring(wing, SEASON_DAYS) is None
        assert dbm.default_supply_chain(conn, "broiler") != "commodity_syrup"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# The corpus wires up
# ---------------------------------------------------------------------------

def test_maple_has_its_own_supply_chain():
    """No cross-species fallback by design: a species without a chain raises
    rather than inheriting somebody else's route."""
    conn = dbm.connect()
    try:
        assert dbm.default_supply_chain(conn, "sugar_maple") == \
            "commodity_syrup"
    finally:
        conn.close()


def test_sugar_maple_is_a_third_domain():
    conn = dbm.connect()
    try:
        row = conn.execute(
            """SELECT d.slug AS slug FROM species s
               JOIN domain d ON d.id = s.domain_id
               WHERE s.slug = 'sugar_maple'"""
        ).fetchone()
        assert row["slug"] == "forestry"
    finally:
        conn.close()


def test_syrup_is_recurring_and_measured_in_gallons_of_syrup():
    conn = dbm.connect()
    try:
        prod = dbm.get_product(conn, "maple_syrup_gallon")
        assert prod["yield_mode"] == "recurring"
        assert prod["unit_name"] == "gallon"
        assert prod["species_slug"] == "sugar_maple"
        assert prod["individual_noun"] == "tree"
    finally:
        conn.close()


@pytest.mark.parametrize("chain", ["commodity_syrup", "sugarhouse_direct"])
def test_both_routes_load_and_only_the_pool_ever_grows(chain):
    """Sap is mixed at collection and nothing downstream can unmix it, so
    every stage is at least as wide as the one before it."""
    conn = dbm.connect()
    try:
        stages = dbm.load_mixing_stages(conn, chain)
        assert stages
        pools = [s.pool for s in stages]
        assert pools == sorted(pools)
        assert all(s.mixing_kind == "random" for s in stages)
        assert dbm.chain_floor_note(conn, chain)
    finally:
        conn.close()


def test_the_sugarhouse_route_is_a_prefix_of_the_commodity_route():
    """Buying at the sugarhouse skips the packer blend and nothing else."""
    conn = dbm.connect()
    try:
        commodity = [s.slug for s in
                     dbm.load_mixing_stages(conn, "commodity_syrup")]
        direct = [s.slug for s in
                  dbm.load_mixing_stages(conn, "sugarhouse_direct")]
        assert commodity[:len(direct)] == direct
        assert len(direct) < len(commodity)
        assert "maple_packer_blend" in commodity
        assert "maple_packer_blend" not in direct
    finally:
        conn.close()


def test_exactly_one_maple_route_is_the_default():
    conn = dbm.connect()
    try:
        rows = conn.execute(
            """SELECT sc.slug AS slug, sc.is_default AS is_default
               FROM supply_chain sc
               JOIN species s ON s.id = sc.species_id
               WHERE s.slug = 'sugar_maple'"""
        ).fetchall()
        assert {r["slug"] for r in rows} == {"commodity_syrup",
                                             "sugarhouse_direct"}
        assert sum(r["is_default"] for r in rows) == 1
    finally:
        conn.close()
