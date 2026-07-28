"""Tests for scientific mode: intervals, evidence filtering, sensitivity.

Same principle as test_model.py -- these pin invariants rather than exact
figures, because the underlying estimates will keep moving as research
replaces placeholders. What must never break is the *shape*: a wider
confidence level always yields a wider interval, excluding weak evidence
always lowers the answer, and a stage that cannot move a count must never
show up as a source of uncertainty about one.
"""

import pytest

from counting_chicken_wings.model import (
    CONFIDENCE_RANK,
    LossStage,
    MixingStage,
    _percentile,
    meets_confidence,
    run,
    sensitivity,
)


def stage(slug, applies_to, lo, mode, hi, confidence="estimate", seq=10):
    return LossStage(
        slug=slug, label=slug.replace("_", " ").title(), sequence=seq,
        phase="test", applies_to=applies_to,
        survive_lo=lo, survive_mode=mode, survive_hi=hi,
        confidence=confidence,
    )


# A miniature version of the real chain, one stage per evidence grade so the
# filter has something meaningful to cut at every level.
GRADED = [
    stage("condemnation", "individual", 0.9954, 0.9955, 0.9955,
          "measured", seq=10),
    stage("wing_damage", "product", 0.900, 0.943, 0.980, "study", seq=20),
    stage("kitchen_loss", "product", 0.900, 0.958, 0.970, "industry", seq=30),
    stage("grading", "product", 0.950, 0.980, 0.995, "estimate", seq=40),
    stage("cook_loss", "mass", 0.700, 0.780, 0.850, "estimate", seq=50),
]

COMMODITY = [
    MixingStage("sep", "Cut-up", 5000, "random", pool_lo=500, pool_hi=20000),
    MixingStage("grade", "Grading", 20000, "separating",
                pool_lo=2000, pool_hi=60000),
    MixingStage("bin", "Freezer", 2000, "random", pool_lo=300, pool_hi=10000),
]


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------

def test_percentile_at_boundaries():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _percentile(xs, 0.0) == 1.0
    assert _percentile(xs, 1.0) == 5.0
    assert _percentile(xs, 0.5) == 3.0


def test_percentile_interpolates_between_samples():
    # Halfway between the 1st and 2nd of two points.
    assert _percentile([10.0, 20.0], 0.5) == pytest.approx(15.0)


def test_percentile_handles_degenerate_input():
    assert _percentile([], 0.5) == 0.0
    assert _percentile([7.0], 0.9) == 7.0


# ---------------------------------------------------------------------------
# Evidence grading
# ---------------------------------------------------------------------------

def test_confidence_rank_is_ordered_best_first():
    assert (CONFIDENCE_RANK["measured"] < CONFIDENCE_RANK["derived"]
            < CONFIDENCE_RANK["study"] < CONFIDENCE_RANK["industry"]
            < CONFIDENCE_RANK["estimate"])


def test_no_minimum_accepts_everything():
    for level in CONFIDENCE_RANK:
        assert meets_confidence(level, None)


def test_minimum_admits_equal_and_better_only():
    assert meets_confidence("measured", "study")
    assert meets_confidence("study", "study")
    assert not meets_confidence("industry", "study")
    assert not meets_confidence("estimate", "study")


def test_unknown_grade_is_treated_as_worst():
    """An unrecognised grade must never sneak past a filter."""
    assert not meets_confidence("vibes", "estimate")


# ---------------------------------------------------------------------------
# Confidence intervals
# ---------------------------------------------------------------------------

def test_wider_confidence_gives_wider_interval():
    """50% must sit inside 90%, which must sit inside 99%.

    Same seed and iteration count means the underlying draws are identical,
    so the only thing changing is where the percentiles are cut.
    """
    kw = dict(loss_stages=GRADED, mixing_stages=COMMODITY,
              iterations=4000, seed=99)
    r50 = run(12, 2.0, confidence_level=0.50, **kw)
    r90 = run(12, 2.0, confidence_level=0.90, **kw)
    r99 = run(12, 2.0, confidence_level=0.99, **kw)

    assert r99.required_lo < r90.required_lo < r50.required_lo
    assert r50.required_hi < r90.required_hi < r99.required_hi


def test_interval_brackets_the_mean():
    res = run(12, 2.0, GRADED, COMMODITY, iterations=4000, seed=1,
              confidence_level=0.90)
    assert res.required_lo <= res.required <= res.required_hi
    assert res.distinct_lo <= res.distinct_mean <= res.distinct_hi


def test_confidence_level_is_recorded_on_the_result():
    """A chart must never be able to mislabel its own axis."""
    res = run(12, 2.0, GRADED, COMMODITY, iterations=500, seed=1,
              confidence_level=0.80)
    assert res.confidence_level == 0.80


def test_interval_collapses_when_every_band_is_a_point():
    """No input uncertainty must mean no output uncertainty."""
    fixed = [stage("certain", "product", 0.95, 0.95, 0.95, "measured")]
    tight = [MixingStage("bin", "Bin", 2000, "random",
                         pool_lo=2000, pool_hi=2000)]
    res = run(12, 2.0, fixed, tight, iterations=800, seed=3)
    assert res.required_hi - res.required_lo == pytest.approx(0.0, abs=1e-9)


def test_without_iterations_the_band_degenerates_to_the_point():
    """Callers render a band unconditionally, so it must always be sane."""
    res = run(12, 2.0, GRADED, COMMODITY, iterations=0)
    assert res.required_lo == res.required == res.required_hi
    assert res.distinct_lo == res.distinct_mean == res.distinct_hi


# ---------------------------------------------------------------------------
# Evidence filtering
# ---------------------------------------------------------------------------

def test_evidence_filter_excludes_weaker_stages():
    res = run(12, 2.0, GRADED, COMMODITY, min_confidence="study")
    assert set(res.excluded_stages) == {"kitchen_loss", "grading", "cook_loss"}


def test_excluding_losses_lowers_the_requirement():
    """Dropping unsourced losses makes the answer an underestimate."""
    everything = run(12, 2.0, GRADED, COMMODITY)
    study_only = run(12, 2.0, GRADED, COMMODITY, min_confidence="study")
    assert study_only.required < everything.required
    assert study_only.required >= study_only.floor


def test_measured_only_keeps_just_the_measured_stage():
    res = run(12, 2.0, GRADED, COMMODITY, min_confidence="measured")
    assert set(res.excluded_stages) == {
        "wing_damage", "kitchen_loss", "grading", "cook_loss"
    }
    assert res.required == pytest.approx(6.0 / 0.9955)


def test_filtering_never_breaches_the_floor():
    for level in [None, "industry", "study", "derived", "measured"]:
        res = run(12, 2.0, GRADED, COMMODITY, min_confidence=level)
        assert res.required >= res.floor - 1e-9, level


def test_no_filter_excludes_nothing():
    assert run(12, 2.0, GRADED, COMMODITY).excluded_stages == []


def test_filter_does_not_change_the_mixing_answer():
    """Evidence grade applies to losses; mixing drives distinct separately."""
    a = run(12, 2.0, GRADED, COMMODITY)
    b = run(12, 2.0, GRADED, COMMODITY, min_confidence="measured")
    assert a.distinct_mean == pytest.approx(b.distinct_mean)


# ---------------------------------------------------------------------------
# Mixing pool resampling
# ---------------------------------------------------------------------------

def test_pool_band_defaults_to_the_point_value():
    m = MixingStage("x", "X", 500, "random")
    assert m.band() == (500, 500, 500)


def test_pool_band_orders_its_bounds():
    m = MixingStage("x", "X", 500, "random", pool_lo=100, pool_hi=900)
    assert m.band() == (100, 500, 900)


def test_resampling_pools_widens_the_distinct_band():
    """Holding pool sizes fixed understates uncertainty on the headline.

    Small pools are used deliberately: the distinct curve is steep there, so
    the effect is measurable. At commodity scale it flattens against the
    ceiling and any band is invisible.
    """
    varied = [MixingStage("bin", "Bin", 50, "random",
                          pool_lo=10, pool_hi=400)]
    fixed = [MixingStage("bin", "Bin", 50, "random",
                         pool_lo=50, pool_hi=50)]
    v = run(12, 2.0, [], varied, iterations=3000, seed=5)
    f = run(12, 2.0, [], fixed, iterations=3000, seed=5)

    assert (v.distinct_hi - v.distinct_lo) > (f.distinct_hi - f.distinct_lo)
    assert f.distinct_hi - f.distinct_lo == pytest.approx(0.0, abs=1e-9)


def test_resampled_distinct_stays_inside_floor_and_ceiling():
    res = run(12, 2.0, [], COMMODITY, iterations=2000, seed=8)
    assert res.distinct_lo >= 6.0 - 1e-9
    assert res.distinct_hi <= 12.0 + 1e-9


# ---------------------------------------------------------------------------
# Samples
# ---------------------------------------------------------------------------

def test_samples_withheld_unless_requested():
    res = run(12, 2.0, GRADED, COMMODITY, iterations=500, seed=2)
    assert res.required_samples == []
    assert res.distinct_samples == []


def test_samples_returned_sorted_and_complete():
    res = run(12, 2.0, GRADED, COMMODITY, iterations=500, seed=2,
              keep_samples=True)
    assert len(res.required_samples) == 500
    assert len(res.distinct_samples) == 500
    assert res.required_samples == sorted(res.required_samples)


# ---------------------------------------------------------------------------
# Sensitivity
# ---------------------------------------------------------------------------

def test_mass_only_stages_have_no_swing():
    """Cook loss is wildly uncertain and completely irrelevant to a count."""
    by_slug = {s.slug: s for s in sensitivity(12, 2.0, GRADED)}
    assert by_slug["cook_loss"].swing == pytest.approx(0.0)
    assert by_slug["cook_loss"].share == pytest.approx(0.0)


def test_widest_band_on_a_count_stage_dominates():
    ranked = sensitivity(12, 2.0, GRADED)
    assert ranked[0].slug == "wing_damage"
    assert ranked[0].swing > 0


def test_sensitivity_is_sorted_by_swing_descending():
    swings = [s.swing for s in sensitivity(12, 2.0, GRADED)]
    assert swings == sorted(swings, reverse=True)


def test_shares_sum_to_one():
    total = sum(s.share for s in sensitivity(12, 2.0, GRADED))
    assert total == pytest.approx(1.0)


def test_tight_band_contributes_almost_nothing():
    """The best-sourced figure should barely register as a source of doubt."""
    by_slug = {s.slug: s for s in sensitivity(12, 2.0, GRADED)}
    assert by_slug["condemnation"].share < 0.01


def test_high_result_exceeds_low_result():
    """survive_lo means more loss, so it must need more individuals."""
    for s in sensitivity(12, 2.0, GRADED):
        assert s.high_result >= s.low_result


def test_sensitivity_of_an_empty_chain_is_empty():
    assert sensitivity(12, 2.0, []) == []
