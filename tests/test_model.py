"""Tests for the maths.

The invariants matter more than the exact figures here: estimates will get
refined as research continues, but "never fewer than the floor" and "never
more than the units drawn" must hold for every input, forever.
"""

import pytest

from counting_chicken_wings.model import (
    LossStage,
    MixingParams,
    MixingStage,
    cascade_retention,
    design_effect,
    draw_from_cascade,
    expected_distinct,
    expected_distinct_general,
    floor_individuals,
    required_individuals,
    resolve_pool,
    run,
    saturation_threshold,
)

# The mechanisms are parameters now, not module constants, and the model
# applies none of them unless told to -- see MixingParams. Tests that want a
# mechanism must ask for it, which is the point: it makes each test say what
# it is testing instead of inheriting a hidden global.
GRADED = MixingParams(separation_efficiency=0.90)


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
    c1, d1, _ = resolve_pool(random_only, 12, 2.0, GRADED)
    c2, d2, _ = resolve_pool(with_grading, 12, 2.0, GRADED)
    # resolve_pool returns DISTINCT individuals represented in the container.
    # Grading splits pairs, so the same number of units in the container comes
    # from more separate birds.
    assert d2 > d1
    assert (expected_distinct_general(12, c2, d2)
            >= expected_distinct_general(12, c1, d1))


def test_separation_does_nothing_unless_it_is_asked_for():
    """The mechanism is a parameter, and the default is no mechanism.

    Guards the fix for the hardcoded SEPARATION_EFFICIENCY: if a default
    carrying the corpus's value ever creeps back into MixingParams, this
    fails. The honest failure direction is towards the assumption-free
    answer, never towards a stale constant nobody is auditing.
    """
    stages = [MixingStage("g", "Grading", 20000, "separating")]
    _, inert, _ = resolve_pool(stages, 12, 2.0)
    _, graded, _ = resolve_pool(stages, 12, 2.0, GRADED)
    assert graded > inert
    assert MixingParams().separation_efficiency == 0.0
    assert MixingParams() == MixingParams.inert()


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


# ---------------------------------------------------------------------------
# Clustering in the draw
# ---------------------------------------------------------------------------
#
# A fryer scoop is a grab of contiguous units, not twelve independent picks.
# Positive intra-cluster correlation is the only force in the whole model
# that pushes the distinct count DOWN, so these tests pin its sign and its
# degenerate cases hard. Getting the null wrong invents an effect.

def test_grouping_an_exchangeable_draw_changes_nothing():
    """THE null. Cluster size alone must be an exact no-op.

    This is the easiest thing here to get wrong, and getting it wrong
    manufactures an effect out of nothing. A pair at exchangeable positions
    lands in one cluster with probability (c-1)/(W-1) and is then taken with
    that cluster; adding that to the both-clusters-drawn case reproduces the
    unclustered answer exactly. Equality, not approximation.
    """
    base = expected_distinct_general(12, 80, 40)
    for c in (1, 2, 3, 4, 6, 12):
        assert expected_distinct_general(
            12, 80, 40, cluster_size=c, retention=0.0
        ) == pytest.approx(base, abs=1e-12), c


def test_retention_is_inert_without_a_cluster_to_retain_into():
    """A one-unit grab cannot hold an adjacent pair, so c=1 kills retention."""
    base = expected_distinct_general(12, 80, 40)
    for r in (0.0, 0.5, 1.0):
        assert expected_distinct_general(
            12, 80, 40, cluster_size=1, retention=r
        ) == pytest.approx(base, abs=1e-12), r


def test_clustering_only_ever_lowers_the_count():
    """The sign of the effect, which is the whole reason to model it."""
    base = expected_distinct_general(12, 80, 40)
    prev = base
    for r in (0.2, 0.4, 0.6, 0.8, 1.0):
        got = expected_distinct_general(12, 80, 40, cluster_size=4, retention=r)
        assert got <= prev + 1e-12, r
        prev = got
    assert prev < base


def test_clustering_never_breaches_the_floor():
    """Six or more. Never fewer -- clustering included."""
    for c in (1, 2, 4, 12):
        for r in (0.0, 0.5, 1.0):
            got = expected_distinct_general(
                12, 80, 40, cluster_size=c, retention=r)
            assert got >= 6.0 - 1e-9, (c, r)
            assert got <= 12.0 + 1e-9, (c, r)


def test_design_effect_is_kish():
    """deff = 1 + (c-1)*ICC, borrowed from survey sampling, not invented."""
    assert design_effect(1, 0.9) == pytest.approx(1.0)
    assert design_effect(4, 0.0) == pytest.approx(1.0)
    assert design_effect(4, 1.0) == pytest.approx(4.0)
    assert design_effect(4, 0.5) == pytest.approx(2.5)


def test_cascade_retention_is_the_product_of_its_stages():
    """A route's mixing_kind sequence finally determines something."""
    p = MixingParams(
        separation_efficiency=0.90,
        adjacency_retention_random=0.20,
        adjacency_retention_passthrough=0.95,
    )
    assert cascade_retention([], p) == pytest.approx(1.0)
    assert cascade_retention(
        [MixingStage("a", "A", 10, "random")], p) == pytest.approx(0.20)
    assert cascade_retention(
        [MixingStage("a", "A", 10, "none")], p) == pytest.approx(0.95)
    # A separating stage needs no parameter of its own: splitting a pair IS
    # destroying its adjacency, so it derives from the efficiency.
    assert cascade_retention(
        [MixingStage("a", "A", 10, "separating")], p
    ) == pytest.approx(0.20 * 0.10)
    two = [MixingStage("a", "A", 10, "random"),
           MixingStage("b", "B", 10, "random")]
    assert cascade_retention(two, p) == pytest.approx(0.04)


def test_a_long_commodity_cascade_retains_essentially_no_adjacency():
    """The finding, pinned. Six bulk stages and a grader destroy adjacency.

    Not a tuning failure and not a placeholder. This is WHY clustering does
    not move the commodity answer, and it should fail loudly if the cascade
    or the parameters ever change enough to make it untrue, because the
    published narrative rests on it.
    """
    p = MixingParams(
        separation_efficiency=0.90,
        draw_cluster_size=4.0,
        adjacency_retention_random=0.20,
        adjacency_retention_passthrough=0.95,
    )
    long_chain = [
        MixingStage("sep", "Cut-up", 5000, "random"),
        MixingStage("chill", "Chiller", 20000, "random"),
        MixingStage("grade", "Grading", 20000, "separating"),
        MixingStage("combo", "Combo bin", 8700, "random"),
        MixingStage("iqf", "IQF", 50000, "random"),
        MixingStage("case", "Case pack", 175, "none"),
        MixingStage("dist", "Distributor", 100000, "random"),
        MixingStage("bin", "Freezer", 2000, "random"),
        MixingStage("fry", "Fryer", 2000, "none"),
    ]
    assert cascade_retention(long_chain, p) < 1e-5
    _, _, _, got = draw_from_cascade(long_chain, 12, 2.0, p)
    assert got > 11.99


def test_clustering_can_reach_the_floor_when_nothing_destroys_adjacency():
    """The mechanism has real range. It is not a rounding artifact.

    This is the necessary companion to the test above. "Clustering does not
    move the commodity answer" is only an interesting claim if clustering is
    capable of moving an answer at all -- otherwise it is a report on a
    broken formula. So take the same pool sizes, delete every stage that
    destroys adjacency, preserve it perfectly, and take the whole order in
    one grab: the answer collapses from 12 to essentially the floor.

    That is the honest shape of the finding. The commodity number survives
    because a chiller and a grader are real, not because the model cannot
    push back.
    """
    perfect = MixingParams(
        separation_efficiency=0.0,
        draw_cluster_size=12.0,
        adjacency_retention_random=1.0,
        adjacency_retention_passthrough=1.0,
    )
    chain = [
        MixingStage("sep", "Cut-up", 5000, "random"),
        MixingStage("dist", "Distributor", 100000, "random"),
        MixingStage("bin", "Freezer", 2000, "random"),
    ]
    assert cascade_retention(chain, perfect) == pytest.approx(1.0)
    _, _, _, got = draw_from_cascade(chain, 12, 2.0, perfect)
    assert got < 7.0
    # And never below the floor, however hard clustering is pushed.
    assert got >= 6.0 - 1e-9

    # Same pool, same scoop, but adjacency destroyed: back to the ceiling.
    exchangeable = MixingParams(draw_cluster_size=12.0)
    _, _, _, loose = draw_from_cascade(chain, 12, 2.0, exchangeable)
    assert loose > 11.99


def test_clustering_bites_where_the_cascade_is_short():
    """A butcher's tray keeps adjacency a plant destroys, and it shows."""
    p = MixingParams(
        separation_efficiency=0.90,
        draw_cluster_size=4.0,
        adjacency_retention_random=0.20,
        adjacency_retention_passthrough=0.95,
    )
    tray = [MixingStage("sep", "Cut-up", 40, "random"),
            MixingStage("tray", "Tray", 40, "random")]
    _, _, _, clustered = draw_from_cascade(tray, 12, 2.0, p)
    _, _, _, exchangeable = draw_from_cascade(
        tray, 12, 2.0, MixingParams(separation_efficiency=0.90))
    assert clustered < exchangeable
    assert clustered >= 6.0


# ---------------------------------------------------------------------------
# Saturation
# ---------------------------------------------------------------------------

def test_saturation_threshold_is_where_the_curve_flattens():
    """The claim made computable: above this pool, the pool stops mattering."""
    t = saturation_threshold(12, 2.0, epsilon=0.05)

    def answer(b):
        c, d, _ = resolve_pool(
            [MixingStage("p", "Pool", b, "random")], 12, 2.0)
        return expected_distinct_general(12, c, d)

    assert 12.0 - answer(t) <= 0.05
    assert 12.0 - answer(t - 1) > 0.05
    # A tighter epsilon can only ever need a bigger pool.
    assert saturation_threshold(12, 2.0, epsilon=0.01) > t


def test_a_draw_that_cannot_saturate_raises_rather_than_looping():
    """The guard is a guard, not a silent clamp."""
    with pytest.raises(ValueError):
        saturation_threshold(12, 2.0, epsilon=0.0)
