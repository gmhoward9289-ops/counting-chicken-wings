"""The floor-versus-ceiling invariant, enforced over the WHOLE corpus.

Saffron broke the pooling maths once and got a test. Maple broke it again,
the same way, eighteen months of subjects later, because the fix was a flag
whose condition -- `yield_mode == "continuous"` -- was copied into three call
sites and described the wrong thing. Maple is `recurring`, so every copy read
a gallon of syrup as one tree's discrete part and printed:

    Gathered in a single day, 1 gallon took at least 194 trees.
    The gallon on your plate came from about 1 different trees.

A floor of 194 above a ceiling of 1, in adjacent lines of shipped output.

So this file does not test maple. It tests the SHAPE, product by product,
through every surface that can answer the question, so that the next subject
cannot reintroduce it and pass. The invariant:

    floor <= distinct <= ceiling,     for every product, on every route,

where `floor` is whichever floor the surface actually prints after the words
"at least" -- the hard one where physiology provides it, the yield one where
it does not. See `_claimed_floor`.

If a subject you are adding fails here, the answer is never to widen the
tolerance. It is that the corpus does not yet describe your product.
"""

import pytest
from fastapi.testclient import TestClient

from counting_chicken_wings import db as dbm
from counting_chicken_wings.api import app
from counting_chicken_wings.model import RecurringYield, run, unit_is_aggregate

EPS = 1e-6


@pytest.fixture(scope="module")
def conn():
    c = dbm.connect()
    yield c
    c.close()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _slugs():
    c = dbm.connect()
    try:
        return [r["slug"] for r in dbm.list_products(c)]
    finally:
        c.close()


PRODUCTS = _slugs()


def _run_product(conn, slug, count=1, window_days=None):
    """Exactly what the CLI does, minus the printing."""
    prod = dbm.get_product(conn, slug)
    chain = dbm.default_supply_chain(conn, prod["species_slug"])
    return prod, run(
        units_requested=count,
        units_per_individual=prod["units_per_individual_mode"],
        loss_stages=dbm.load_loss_stages(
            conn, prod["species_slug"], prod["slug"], chain_slug=chain),
        mixing_stages=dbm.load_mixing_stages(conn, chain),
        recurring=dbm.make_recurring(prod, window_days),
        anatomical=bool(prod["is_anatomical_constant"]),
    )


# ---------------------------------------------------------------------------
# The invariant, over the whole corpus
# ---------------------------------------------------------------------------

def _claimed_floor(res):
    """The number a surface prints after the words "at least".

    Where a hard floor exists it is that, and `floor` is a different
    quantity -- for twelve same-day eggs, twelve hens are on your plate and
    you need 15.2 hens' worth of laying to count on getting them. Those two
    do not contradict each other. Where there is no hard floor, `floor` is
    the only floor and it IS the "at least" claim.
    """
    return res.hard_floor if res.hard_floor is not None else res.floor


@pytest.mark.parametrize("slug", PRODUCTS)
@pytest.mark.parametrize("count", [1, 2, 12])
def test_distinct_is_never_below_the_floor(conn, slug, count):
    """The bug, stated once for every product there is."""
    _, res = _run_product(conn, slug, count)
    assert res.distinct_mean >= _claimed_floor(res) - EPS, (
        f"{slug}: {res.distinct_mean} individuals reported for a floor of "
        f"{_claimed_floor(res)} -- the same answer says both"
    )


@pytest.mark.parametrize("slug", PRODUCTS)
@pytest.mark.parametrize("count", [1, 12])
def test_the_invariant_survives_the_monte_carlo_pass(conn, slug, count):
    """Resampling had its own copy of the draw and skipped the aggregate
    re-expression, so `--iterations` reported 12 flowers per 12 grams
    against a floor of 1,800. Shipped, and separate from the maple bug."""
    prod = dbm.get_product(conn, slug)
    chain = dbm.default_supply_chain(conn, prod["species_slug"])
    res = run(
        units_requested=count,
        units_per_individual=prod["units_per_individual_mode"],
        loss_stages=dbm.load_loss_stages(
            conn, prod["species_slug"], prod["slug"], chain_slug=chain),
        mixing_stages=dbm.load_mixing_stages(conn, chain),
        recurring=dbm.make_recurring(prod),
        anatomical=bool(prod["is_anatomical_constant"]),
        iterations=200, seed=7,
    )
    assert res.distinct_lo >= _claimed_floor(res) - EPS, slug
    assert res.distinct_hi <= res.distinct_ceiling + EPS, slug


@pytest.mark.parametrize("slug", PRODUCTS)
@pytest.mark.parametrize("count", [1, 2, 12])
def test_distinct_is_never_above_the_ceiling(conn, slug, count):
    """The other half. A contradiction can point either way, and clamping the
    count into range would hide both."""
    _, res = _run_product(conn, slug, count)
    assert res.distinct_mean <= res.distinct_ceiling + EPS, slug


@pytest.mark.parametrize("slug", PRODUCTS)
def test_the_floor_never_exceeds_the_ceiling(conn, slug):
    """The printed pair, checked as a pair. `hard floor 193 ... ceiling 1` was
    the line that gave the bug away, and neither number alone was wrong."""
    _, res = _run_product(conn, slug)
    assert _claimed_floor(res) <= res.distinct_ceiling + EPS, slug


@pytest.mark.parametrize("slug", PRODUCTS)
def test_the_api_holds_the_same_invariant(client, slug):
    """Through the HTTP route, which had its own copy of the condition and so
    could hold the invariant in the model and break it on the wire."""
    a = client.get("/api/calculate",
                   params={"count": 12, "product": slug}).json()["answer"]
    lo = a["hard_floor"] if a["hard_floor"] is not None else a["floor"]
    assert lo - EPS <= a["distinct"] <= a["ceiling"] + EPS, slug


@pytest.mark.parametrize("slug", PRODUCTS)
def test_the_analysis_route_holds_it_too(client, slug):
    """The third call site. It is the one nobody looks at, which is exactly
    why it needs the same test as the two that are looked at."""
    a = client.get("/api/scientific",
                   params={"count": 12, "product": slug}).json()["answer"]
    # This route never passes `recurring`, so it answers timelessly and
    # `floor` is its only floor. Noted rather than fixed here -- see the
    # report; it is a separate defect with its own blast radius.
    assert a["floor"] - EPS <= a["distinct"] <= a["ceiling"] + EPS, slug


# ---------------------------------------------------------------------------
# The rule itself, read off the data
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slug,expected", [
    ("whole_wing", False),        # 2 wings per chicken
    ("boneless_wing", False),     # 34.5 pieces per chicken
    ("saffron_stigma", False),    # exactly 3 per flower
    ("saffron_gram", True),       # 1/150th of a gram per flower
    ("table_egg", False),         # 288 a year, and an egg has one mother
    ("maple_syrup_gallon", True),  # about a quart per tree per season
    # The two domains that landed after this file was written. Beef is the
    # interesting one: a patty is emphatically a blend in the everyday sense --
    # it is the most thoroughly commingled thing in the corpus -- and this test
    # still says False, correctly. The question here is not "was it mixed", it
    # is "does one unit need more than one individual to exist at all". One
    # steer yields about 670 patties, so it does not. Mixing is the cascade's
    # business; this flag is about arithmetic, and conflating the two is the
    # bug the file exists to prevent.
    ("ground_beef_patty", False),  # ~670 patties from one animal's lean trim
    ("silkworm_cocoon", False),   # exactly 1 per worm, the hard floor
    ("silk_necktie", True),       # 1/150th of a tie per worm
])
def test_whether_a_unit_is_a_blend_is_read_off_the_figures(conn, slug,
                                                           expected):
    """One individual's WHOLE natural output against one whole unit. Not the
    yield mode: maple and eggs share a mode and differ here, saffron and
    maple differ in mode and agree."""
    prod = dbm.get_product(conn, slug)
    ry = dbm.make_recurring(prod)
    assert unit_is_aggregate(
        prod["units_per_individual_mode"], ry) is expected


def test_the_window_cannot_change_whether_a_unit_is_a_blend():
    """The trap the old condition fell into from the other side. A hen yields
    0.79 of an egg in a day, which is below one and says nothing about
    whether an egg is a blend -- it is not."""
    for window in (1, 7, 45, 365, 3650):
        ry = RecurringYield(units_per_period=288, period_days=365,
                            window_days=window, max_units_per_day=1.0)
        assert unit_is_aggregate(288, ry) is False


def test_no_surface_keeps_its_own_copy_of_the_condition():
    """Three copies of `yield_mode == "continuous"` is why this shipped. The
    derivation lives in run(); a caller re-deriving it is the bug returning."""
    import pathlib

    import counting_chicken_wings
    root = pathlib.Path(counting_chicken_wings.__file__).parent
    for mod in ("cli.py", "api.py"):
        text = (root / mod).read_text(encoding="utf-8")
        assert "aggregate_units=" not in text, (
            f"{mod} decides aggregate_units for itself again"
        )
        assert 'yield_mode"] == "continuous"' not in text, (
            f"{mod} is testing the yield mode again, which is not the "
            f"question -- maple is recurring and its gallon is still a blend"
        )


# ---------------------------------------------------------------------------
# Maple, the product that exposed it
# ---------------------------------------------------------------------------

def test_a_gallon_of_syrup_is_several_trees_not_one(conn):
    prod, res = _run_product(conn, "maple_syrup_gallon")
    assert res.floor == pytest.approx(1 / 0.233, rel=1e-6)
    assert res.distinct_mean >= res.floor - EPS
    assert res.distinct_ceiling >= res.floor - EPS


def test_the_default_window_for_maple_is_its_season_not_a_day(conn):
    """A one-day default asked how many trees could be tapped, boiled and
    bottled between breakfast and supper, and answered 194."""
    prod = dbm.get_product(conn, "maple_syrup_gallon")
    assert prod["default_window_days"] is None
    assert dbm.make_recurring(prod).window_days == pytest.approx(45)


def test_maple_reports_no_hard_floor_because_it_has_no_daily_cap(conn):
    """A hard floor is a claim about physiology. Sap flow is weather."""
    _, res = _run_product(conn, "maple_syrup_gallon")
    assert res.hard_floor is None


def test_maple_narrates_its_own_rate(conn):
    """'At the real laying rate you would need about 193 trees' was in the
    shipped output. A tree does not lay."""
    prod = dbm.get_product(conn, "maple_syrup_gallon")
    assert prod["rate_label"] == "sap flow"
    assert prod["cap_note"] is None


# ---------------------------------------------------------------------------
# The control: nothing that was right may move
# ---------------------------------------------------------------------------

def test_wings_are_untouched(conn):
    _, res = _run_product(conn, "whole_wing", 12)
    assert res.floor == pytest.approx(6.0)
    assert res.distinct_ceiling == 12.0
    assert res.hard_floor is None
    assert res.window_days is None
    assert 6.0 <= res.distinct_mean <= 12.0


def test_eggs_are_untouched(conn):
    """Twelve same-day eggs, twelve hens, and both floors still reported."""
    prod, res = _run_product(conn, "table_egg", 12)
    assert prod["default_window_days"] == 1
    assert res.window_days == 1
    assert res.hard_floor == pytest.approx(12.0)
    assert res.floor == pytest.approx(12 / (288 / 365), rel=1e-9)
    assert res.distinct_ceiling == 12.0
    assert res.distinct_mean == pytest.approx(12.0)


def test_eggs_still_narrate_as_eggs(conn):
    prod = dbm.get_product(conn, "table_egg")
    assert prod["rate_label"] == "laying rate"
    assert "one egg a day" in prod["cap_note"]


def test_saffron_the_original_control_is_unchanged(conn):
    _, res = _run_product(conn, "saffron_gram")
    assert res.floor == pytest.approx(150, rel=1e-6)
    assert res.distinct_ceiling == 150
    assert res.distinct_mean >= res.floor - EPS
