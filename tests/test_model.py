"""Tests for the maths.

The invariants matter more than the exact figures here: estimates will get
refined as research continues, but "never fewer than the floor" and "never
more than the units drawn" must hold for every input, forever.
"""

import pytest

from counting_chicken_wings.model import (
    LossStage,
    MixingStage,
    expected_distinct,
    expected_distinct_general,
    floor_individuals,
    required_individuals,
    resolve_pool,
    run,
)


# ---------------------------------------------------------------------------
# Floor
# ---------------------------------------------------------------------------

def test_floor_is_wings_over_two():
    assert floor_individuals(12, 2) == 6
    assert floor_individuals(1, 2) == 0.5
    assert floor_individuals(100, 2) == 50


def test_floor_rejects_nonsense():
    with pytest.raises(ValueError):
        floor_individuals(12, 0)


# ---------------------------------------------------------------------------
# Pooling
# ---------------------------------------------------------------------------

def test_six_birds_cut_up_by_hand_gives_exactly_six():
    """The one case where a dozen wings really is six chickens."""
    assert expected_distinct(12, 12, 6) == pytest.approx(6.0)


def test_fully_separated_pool_gives_exactly_n():
    """If no individual has two units in the container, every unit is a
    different individual -- distinct must equal the draw exactly."""
    assert expected_distinct(12, 4000, 0) == pytest.approx(12.0)


def test_distinct_rises_with_pool_size():
    vals = [expected_distinct(12, 2 * b, b) for b in (6, 10, 25, 50, 100, 1000)]
    assert vals == sorted(vals)
    assert vals[0] == pytest.approx(6.0)
    assert vals[-1] > 11.9


def test_distinct_never_exceeds_units_drawn():
    for b in (6, 7, 12, 50, 1000, 40000):
        assert expected_distinct(12, 2 * b, b) <= 12.0 + 1e-9


def test_distinct_never_below_floor():
    for b in (6, 7, 12, 50, 1000, 40000):
        assert expected_distinct(12, 2 * b, b) >= 6.0 - 1e-9


def test_known_pooling_values():
    """Values verified independently against B*(1 - C(2B-2,n)/C(2B,n))."""
    assert expected_distinct(12, 12, 6) == pytest.approx(6.0000, abs=1e-4)
    assert expected_distinct(12, 20, 10) == pytest.approx(8.5263, abs=1e-4)
    assert expected_distinct(12, 100, 50) == pytest.approx(11.3333, abs=1e-4)
    assert expected_distinct(12, 2000, 1000) == pytest.approx(11.9670, abs=1e-4)


def test_cannot_draw_more_than_the_container_holds():
    with pytest.raises(ValueError):
        expected_distinct(12, 8, 4)


# ---------------------------------------------------------------------------
# Mixing cascade
# ---------------------------------------------------------------------------

def test_no_mixing_means_the_answer_is_the_floor():
    container, distinct_in_container, _ = resolve_pool([], 12, 2.0)
    got = expected_distinct_general(12, container, distinct_in_container)
    assert got == pytest.approx(6.0)


def test_boneless_wings_take_a_fraction_of_a_bird():
    """A boneless wing is breast meat; a bird yields tens of pieces.

    The general formula has to cope with ~34.5 units per individual, not
    just the bone-in case of exactly two.
    """
    floor = floor_individuals(12, 34.5)
    assert floor < 1.0
    container, distinct_in_container, _ = resolve_pool([], 12, 34.5)
    got = expected_distinct_general(12, container, distinct_in_container)
    assert got == pytest.approx(floor, rel=1e-6)


def test_separating_stage_pushes_toward_the_ceiling():
    random_only = [
        MixingStage("a", "Chiller", 20000, "random"),
        MixingStage("b", "Bin", 2000, "random"),
    ]
    with_grading = [
        MixingStage("a", "Chiller", 20000, "random"),
        MixingStage("g", "Grading", 20000, "separating"),
        MixingStage("b", "Bin", 2000, "random"),
    ]
    c1, d1, _ = resolve_pool(random_only, 12, 2.0)
    c2, d2, _ = resolve_pool(with_grading, 12, 2.0)
    # resolve_pool returns DISTINCT individuals represented in the container.
    # Grading splits pairs, so the same number of units in the container comes
    # from more separate birds.
    assert d2 > d1
    assert (expected_distinct_general(12, c2, d2)
            >= expected_distinct_general(12, c1, d1))


# ---------------------------------------------------------------------------
# Loss chain
# ---------------------------------------------------------------------------

def _stage(slug, applies_to, survive, seq=10):
    return LossStage(
        slug=slug, label=slug, sequence=seq, phase="test",
        applies_to=applies_to, survive_lo=survive, survive_mode=survive,
        survive_hi=survive, confidence="estimate",
    )


def test_mass_only_losses_never_change_the_count():
    """Frying a wing makes it lighter, not fractional."""
    base, _ = required_individuals(12, 2, [])
    with_cook, _ = required_individuals(
        12, 2, [_stage("cook_loss", "mass", 0.78)]
    )
    assert with_cook == pytest.approx(base)


def test_product_losses_raise_the_requirement():
    r, _ = required_individuals(12, 2, [_stage("damage", "product", 0.943)])
    assert r > 6.0
    assert r == pytest.approx(6.0 / 0.943)


def test_losses_compound_in_order():
    stages = [
        _stage("a", "individual", 0.9955, seq=10),
        _stage("b", "product", 0.943, seq=20),
    ]
    r, trace = required_individuals(12, 2, stages)
    assert r == pytest.approx(6.0 / 0.9955 / 0.943)
    assert [t.sequence for t in trace] == [0, 1, 2]


def test_required_never_below_floor():
    stages = [_stage("x", "product", 0.9)]
    r, _ = required_individuals(12, 2, stages)
    assert r >= floor_individuals(12, 2)


def test_zero_survival_is_rejected():
    with pytest.raises(ValueError):
        required_individuals(12, 2, [_stage("dead", "product", 0.0)])


# ---------------------------------------------------------------------------
# Full run
# ---------------------------------------------------------------------------

COMMODITY = [
    MixingStage("sep", "Cut-up", 5000, "random"),
    MixingStage("grade", "Grading", 20000, "separating"),
    MixingStage("dist", "Distributor", 100000, "random"),
    MixingStage("bin", "Freezer", 2000, "random"),
]


def test_run_produces_the_three_answers():
    res = run(12, 2.0, [_stage("damage", "product", 0.943)], COMMODITY)
    assert res.floor == 6.0
    assert res.required > res.floor
    assert 6.0 <= res.distinct_mean <= 12.0


def test_commodity_chain_lands_just_under_the_ceiling():
    res = run(12, 2.0, [], COMMODITY)
    assert res.distinct_mean > 11.99
    # Strictly below: the ceiling is approached, never reached.
    assert res.distinct_mean < 12.0


def test_the_central_claim_holds_across_every_chain():
    """Six or more. Never fewer. That is the whole project."""
    chains = [
        [],
        [MixingStage("s", "Small", 40, "random")],
        COMMODITY,
    ]
    for chain in chains:
        res = run(12, 2.0, [], chain)
        assert res.distinct_mean >= 6.0 - 1e-9, chain
        assert res.distinct_mean <= 12.0 + 1e-9, chain


def test_monte_carlo_band_brackets_the_point_estimate():
    stages = [
        LossStage("d", "damage", 10, "cutup", "product",
                  0.90, 0.943, 0.98, "study"),
    ]
    res = run(12, 2.0, stages, COMMODITY, iterations=2000, seed=7)
    assert res.iterations == 2000
    assert res.required_lo < res.required < res.required_hi


def test_monte_carlo_is_reproducible_with_a_seed():
    stages = [LossStage("d", "d", 10, "p", "product",
                        0.90, 0.943, 0.98, "study")]
    a = run(12, 2.0, stages, COMMODITY, iterations=500, seed=42)
    b = run(12, 2.0, stages, COMMODITY, iterations=500, seed=42)
    assert a.required == pytest.approx(b.required)


# ---------------------------------------------------------------------------
# Boneless wings -- many units per individual
# ---------------------------------------------------------------------------

BONELESS_PER_BIRD = 34.5


def test_boneless_floor_is_a_fraction_of_a_chicken():
    """A dozen boneless wings is well under one bird's worth of breast."""
    floor = floor_individuals(12, BONELESS_PER_BIRD)
    assert floor == pytest.approx(0.348, abs=0.01)
    assert floor < 1.0


def test_boneless_and_bone_in_differ_by_more_than_an_order_of_magnitude():
    bone_in = floor_individuals(12, 2)
    boneless = floor_individuals(12, BONELESS_PER_BIRD)
    assert bone_in / boneless > 15


def test_many_units_per_individual_still_bounded_by_the_draw():
    """The generalized formula must never exceed the number drawn."""
    for upi in (2.0, 5.0, 34.5, 100.0):
        c, d, _ = resolve_pool(COMMODITY, 12, upi)
        got = expected_distinct_general(12, c, d)
        assert got <= 12.0 + 1e-9, upi
        assert got > 0


def test_general_formula_matches_the_two_unit_case():
    """expected_distinct is the upi=2 special case of the general formula."""
    for container, paired in ((12, 6), (100, 50), (2000, 1000), (4000, 0)):
        distinct = container - paired
        assert expected_distinct_general(12, container, distinct) == \
            pytest.approx(expected_distinct(12, container, paired), abs=1e-9)


def test_a_single_individual_supplying_everything_gives_one():
    """One bird yielding all 12 pieces must report exactly one bird."""
    assert expected_distinct_general(12, 12, 1) == pytest.approx(1.0)


def test_boneless_run_floor_below_one_but_distinct_near_twelve():
    """The headline contrast: a third of a chicken, a dozen chickens."""
    res = run(12, BONELESS_PER_BIRD, [], COMMODITY)
    assert res.floor < 1.0
    assert res.distinct_mean > 11.9
    # Distinct is bounded by the draw, never by the floor.
    assert res.distinct_mean <= 12.0 + 1e-9
