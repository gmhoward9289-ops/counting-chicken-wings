"""Tests for recurring products, where the answer depends on a time window.

Eggs invert the wing story and the tests are written to pin that inversion
down. With wings the floor sits at 6 and mixing pushes the real answer up
toward 12. With same-day eggs the floor RISES TO MEET the ceiling at exactly
12, because a hen lays at most one egg a day -- so twelve eggs gathered in a
day came from twelve different hens, necessarily, and no supply chain
arrangement can reduce it.
"""

import pytest

from counting_chicken_wings import db as dbm
from counting_chicken_wings.model import (
    MixingStage,
    RecurringYield,
    recurring_floor,
    run,
)

# 288 eggs per hen per year, at most one a day.
LAYER = dict(units_per_period=288, period_days=365, max_units_per_day=1.0)

COMMODITY = [
    MixingStage("collect", "Collection", 5000, "random"),
    MixingStage("grade", "Grading", 20000, "separating"),
    MixingStage("carton", "Carton", 200, "random"),
]


# ---------------------------------------------------------------------------
# The rate needs a window
# ---------------------------------------------------------------------------

def test_rate_is_meaningless_without_a_window():
    """288 eggs per hen is not a fact until you say per what."""
    day = RecurringYield(**LAYER, window_days=1)
    year = RecurringYield(**LAYER, window_days=365)
    assert day.units_per_individual == pytest.approx(0.789, abs=1e-3)
    assert year.units_per_individual == pytest.approx(288.0)


def test_window_must_be_positive():
    with pytest.raises(ValueError):
        RecurringYield(**LAYER, window_days=0)
    with pytest.raises(ValueError):
        RecurringYield(**LAYER, window_days=-1)


def test_physiology_beats_the_long_run_average():
    """A hen cannot out-lay its own ovulation cycle in a short window.

    The annual rate is 0.79/day, which is under the 1/day ceiling, so the
    ceiling does not bind here. Raise the rate above physiology and it must.
    """
    impossible = RecurringYield(
        units_per_period=3650, period_days=365,   # 10 eggs a day on average
        window_days=1, max_units_per_day=1.0,
    )
    assert impossible.units_per_individual == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Two floors, and the gap between them
# ---------------------------------------------------------------------------

def test_a_dozen_same_day_eggs_needs_twelve_hens():
    """The headline claim. Physiology makes this a hard floor."""
    ry = RecurringYield(**LAYER, window_days=1)
    hard, expected = recurring_floor(12, ry)
    assert hard == pytest.approx(12.0)
    # Hens do not lay every day, so counting on twelve is optimistic.
    assert expected == pytest.approx(15.208, abs=1e-3)


def test_a_dozen_eggs_over_a_fortnight_needs_one_hen():
    ry = RecurringYield(**LAYER, window_days=15)
    hard, expected = recurring_floor(12, ry)
    assert hard == pytest.approx(0.8)
    assert expected == pytest.approx(1.014, abs=1e-3)


def test_hard_floor_never_exceeds_expected():
    """Physiology can never demand more individuals than the real rate does.

    expected = units / min(rate*w, cap*w) and hard = units / (cap*w), so
    expected >= hard for every window. Worth pinning: if this ever inverts,
    the two numbers have been swapped somewhere.
    """
    for w in (0.5, 1, 3, 7, 15, 90, 365, 700):
        ry = RecurringYield(**LAYER, window_days=w)
        hard, expected = recurring_floor(12, ry)
        assert hard <= expected + 1e-9, w


def test_longer_window_needs_fewer_hens():
    floors = [
        recurring_floor(12, RecurringYield(**LAYER, window_days=w))[1]
        for w in (1, 7, 15, 30, 365)
    ]
    assert floors == sorted(floors, reverse=True)


# ---------------------------------------------------------------------------
# run() integration
# ---------------------------------------------------------------------------

def test_run_derives_units_per_individual_from_the_window():
    """The bug this whole feature fixes.

    Passing the annual figure straight through gave a floor of 0.042 hens for
    a dozen same-day eggs -- understating it by roughly 285x -- while the
    distinct count said 12. run() must override units_per_individual.
    """
    ry = RecurringYield(**LAYER, window_days=1)
    res = run(12, 288.0, [], COMMODITY, recurring=ry)
    assert res.units_per_individual == pytest.approx(0.789, abs=1e-3)
    assert res.hard_floor == pytest.approx(12.0)
    assert res.floor == pytest.approx(15.208, abs=1e-3)


def test_same_day_eggs_reach_the_ceiling():
    """Unlike wings, which approach 12 and never arrive."""
    ry = RecurringYield(**LAYER, window_days=1)
    res = run(12, 288.0, [], COMMODITY, recurring=ry)
    assert res.distinct_mean == pytest.approx(12.0, abs=1e-6)


def test_wings_are_unaffected_by_the_recurring_path():
    res = run(12, 2.0, [], COMMODITY)
    assert res.hard_floor is None
    assert res.window_days is None
    assert res.floor == pytest.approx(6.0)


def test_no_mixing_collapses_eggs_to_one_hen():
    """Your own hens over a fortnight: one bird supplies the lot."""
    ry = RecurringYield(**LAYER, window_days=15)
    res = run(12, 288.0, [], [], recurring=ry)
    assert res.distinct_mean == pytest.approx(1.014, abs=1e-2)


def test_commodity_eggs_stay_near_twelve_whatever_the_window():
    """A supermarket carton is drawn from a huge flock.

    The window changes how few hens COULD have done it, not how many actually
    contributed to the carton in your hand.
    """
    for w in (1, 15, 365):
        ry = RecurringYield(**LAYER, window_days=w)
        res = run(12, 288.0, [], COMMODITY, recurring=ry)
        assert res.distinct_mean > 11.99, w


# ---------------------------------------------------------------------------
# db wiring
# ---------------------------------------------------------------------------

def test_make_recurring_returns_none_for_timeless_products():
    conn = dbm.connect()
    try:
        wing = dbm.get_product(conn, "whole_wing")
        assert dbm.make_recurring(wing, 1) is None
    finally:
        conn.close()


def test_make_recurring_builds_from_the_product_row():
    conn = dbm.connect()
    try:
        egg = dbm.get_product(conn, "table_egg")
        ry = dbm.make_recurring(egg, 1)
        assert ry is not None
        assert ry.window_days == 1
        assert ry.max_units_per_day == pytest.approx(1.0)
        assert ry.period_days == pytest.approx(365.0)
    finally:
        conn.close()


def test_make_recurring_defaults_to_one_day():
    """A carton gathered together is the colloquial reading of 'a dozen'."""
    conn = dbm.connect()
    try:
        egg = dbm.get_product(conn, "table_egg")
        assert dbm.make_recurring(egg, None).window_days == 1.0
    finally:
        conn.close()


def test_recurring_without_a_period_is_rejected():
    """A rate with no denominator is incoherent, so say so rather than
    silently assuming a year."""
    broken = {
        "yield_mode": "recurring",
        "slug": "broken",
        "yield_period_days": None,
        "units_per_individual_mode": 288,
        "max_units_per_day": 1.0,
    }
    with pytest.raises(ValueError, match="yield_period_days"):
        dbm.make_recurring(broken, 1)
