"""Tests for the variance decomposition of `distinct`.

Two halves, and the split matters.

The first half tests the ESTIMATOR against functions whose Sobol indices are
known in closed form. That is the only way to find out whether the arithmetic
is right, because the thing it is pointed at in production has a variance of
2e-5 and no analytic answer -- a broken estimator and a saturated model both
return "approximately nothing", and only a toy function can tell them apart.

The second half tests the WIRING against the real corpus, and pins the two
findings: the commodity cascade has almost no variance to decompose, and the
butcher does. Neither is asserted anywhere in prose that these tests do not
also check, which is the point of computing them.
"""

import math
import random

import pytest

from counting_chicken_wings import db as dbm
from counting_chicken_wings.model import (
    CONFIDENCE_RANK,
    MixingParams,
    MixingStage,
    _centre,
    _sobol_pair,
    variance_decomposition,
)


@pytest.fixture(scope="module")
def conn():
    c = dbm.connect()
    yield c
    c.close()


@pytest.fixture(scope="module")
def bands(conn):
    return dbm.load_mixing_param_bands(conn)


@pytest.fixture(scope="module")
def base(conn):
    return dbm.load_mixing_params(conn)


# ---------------------------------------------------------------------------
# The estimator, against closed-form answers
# ---------------------------------------------------------------------------

def sobol_toy(f, n_in, samples, seed=7):
    """Saltelli design over an arbitrary f, using the shipped estimators.

    Deliberately re-implements only the SAMPLING, and calls the same
    `_centre` and `_sobol_pair` that `variance_decomposition` calls. A test
    that reimplemented the estimators would be checking its own arithmetic.
    """
    rng = random.Random(seed)
    a_m = [[rng.random() for _ in range(n_in)] for _ in range(samples)]
    b_m = [[rng.random() for _ in range(n_in)] for _ in range(samples)]
    fa = [f(r) for r in a_m]
    fb = [f(r) for r in b_m]
    a, b, mu, var = _centre(fa, fb)
    out = []
    for i in range(n_in):
        fab = []
        for k in range(samples):
            row = list(a_m[k])
            row[i] = b_m[k][i]
            fab.append(f(row))
        out.append(_sobol_pair(a, b, [x - mu for x in fab], var))
    return out


def test_ishigami_matches_the_published_indices():
    """The one test that proves the method rather than the plumbing.

    Ishigami is the standard sensitivity-analysis benchmark precisely
    because it is nastily non-additive and its indices are known exactly:
    x3 has NO first-order effect at all and yet a substantial total-order
    one, so a method that cannot see interaction scores it zero and looks
    fine. If this passes, the estimator can see what OAT cannot.
    """
    a_c, b_c = 7.0, 0.1

    def f(u):
        x = [-math.pi + 2 * math.pi * v for v in u]
        return (math.sin(x[0])
                + a_c * math.sin(x[1]) ** 2
                + b_c * x[2] ** 4 * math.sin(x[0]))

    got = sobol_toy(f, 3, 16384, seed=11)
    want_s1 = (0.3139, 0.4424, 0.0)
    want_st = (0.5576, 0.4424, 0.2437)
    for i in range(3):
        assert got[i][0] == pytest.approx(want_s1[i], abs=0.03), f"S1 x{i+1}"
        assert got[i][1] == pytest.approx(want_st[i], abs=0.03), f"ST x{i+1}"

    # The property that makes x3 the interesting one, stated on its own.
    assert got[2][0] < 0.03 < got[2][1]


def test_a_purely_additive_function_has_no_interaction():
    got = sobol_toy(lambda u: u[0] + 2 * u[1] + 3 * u[2], 3, 8192)
    for s1, st in got:
        assert s1 == pytest.approx(st, abs=0.02)
    total = sum(s1 for s1, _ in got)
    assert total == pytest.approx(1.0, abs=0.03)
    # Variances go as the square of the coefficient: 1 : 4 : 9.
    assert got[1][0] / got[0][0] == pytest.approx(4.0, rel=0.15)
    assert got[2][0] / got[0][0] == pytest.approx(9.0, rel=0.15)


def test_a_purely_multiplicative_function_has_interaction():
    """The control that stops the near-zero commodity result reading as a
    null instrument. If the estimator could not detect interaction anywhere,
    "no interaction found" would mean nothing."""
    got = sobol_toy(lambda u: u[0] * u[1] * u[2], 3, 8192)
    assert sum(s1 for s1, _ in got) < 1.0
    assert sum(st for _, st in got) > 1.0


def test_an_ignored_input_scores_zero():
    got = sobol_toy(lambda u: u[0], 3, 4096)
    assert got[0][0] == pytest.approx(1.0, abs=0.03)
    for i in (1, 2):
        assert abs(got[i][0]) < 0.02
        assert abs(got[i][1]) < 0.02


def test_centring_is_what_makes_the_estimator_usable_here():
    """Pins the failure the `_centre` docstring describes, because it is
    silent: uncentred products at this ratio are floating-point noise, and
    the result looks like a number rather than like an error."""
    tiny = [12.0 + 1e-6 * math.sin(k) for k in range(512)]
    other = [12.0 + 1e-6 * math.cos(k) for k in range(512)]
    _, _, mu, var = _centre(tiny, other)
    assert mu == pytest.approx(12.0, abs=1e-5)
    assert 0.0 < var < 1e-11


# ---------------------------------------------------------------------------
# The wiring, against the real corpus
# ---------------------------------------------------------------------------

def _run(conn, bands, base, chain, samples=512, bootstrap=40, seed=3):
    stages = dbm.load_mixing_stages(conn, chain)
    return variance_decomposition(
        stages, bands, 12, 2.0, samples=samples, seed=seed,
        bootstrap=bootstrap, base_params=base,
    )


def test_every_mixing_parameter_slug_is_a_MixingParams_field(bands):
    """The identity mapping `variance_decomposition` relies on to turn a
    corpus row into a keyword argument. Pinned rather than trusted: a
    renamed slug would otherwise silently stop being swept, and an input
    that is not swept scores zero exactly like one that does not matter."""
    from dataclasses import fields
    names = {f.name for f in fields(MixingParams)}
    assert set(bands) == names


def test_the_bands_reaching_the_model_are_the_corpus_bands(bands):
    for slug, (label, lo, mode, hi, conf) in bands.items():
        assert lo <= mode <= hi, slug
        assert label and conf in CONFIDENCE_RANK, slug
        assert lo < hi, f"{slug} has no band to sweep"


def test_every_decomposed_input_carries_an_evidence_grade(conn, bands, base):
    """The honesty machinery has to reach the new output too. An index is a
    statement about a corpus figure, and this project does not publish one
    of those without saying how well evidenced it is."""
    dec = _run(conn, bands, base, "commodity_foodservice")
    assert dec.shares
    for s in dec.shares:
        assert s.confidence in CONFIDENCE_RANK, s.slug
        assert s.kind in ("pool", "parameter"), s.slug


def test_first_order_sums_below_one_and_total_above(conn, bands, base):
    dec = _run(conn, bands, base, "commodity_foodservice")
    assert dec.sum_first_order <= 1.0 + 0.05
    assert dec.sum_total_order >= 1.0 - 0.05
    assert dec.sum_total_order >= dec.sum_first_order


def test_every_index_lies_within_its_bootstrap_band(conn, bands, base):
    dec = _run(conn, bands, base, "commodity_foodservice")
    for s in dec.shares:
        assert s.first_lo - 1e-9 <= s.first_order <= s.first_hi + 1e-9, s.slug
        assert s.total_lo - 1e-9 <= s.total_order <= s.total_hi + 1e-9, s.slug


def test_the_decomposition_is_deterministic_under_a_seed(conn, bands, base):
    a = _run(conn, bands, base, "commodity_foodservice", seed=42)
    b = _run(conn, bands, base, "commodity_foodservice", seed=42)
    assert [(s.slug, s.first_order, s.total_order) for s in a.shares] == \
           [(s.slug, s.first_order, s.total_order) for s in b.shares]

    # And a different seed must actually differ, or the seed is not reaching
    # the rng and every "reproducible" figure above is a coincidence.
    c = _run(conn, bands, base, "commodity_foodservice", seed=43)
    assert [s.first_order for s in a.shares] != [s.first_order for s in c.shares]


def test_the_evaluation_count_is_what_it_claims(conn, bands, base):
    dec = _run(conn, bands, base, "commodity_foodservice", samples=256)
    assert dec.evaluations == 256 * (len(dec.shares) + 2)


def test_a_degenerate_band_gives_a_zero_index_and_says_so(conn, bands, base):
    """An input pinned to a point has no uncertainty to propagate, so its
    index is zero by construction. The flag is the assertion that matters --
    a bare zero here is indistinguishable from "this input does not
    matter", and those are opposite claims about the corpus."""
    stages = [
        MixingStage(slug="pinned", label="Pinned", pool=500,
                    mixing_kind="random", pool_lo=500, pool_hi=500),
        MixingStage(slug="real", label="Real", pool=900,
                    mixing_kind="random", pool_lo=200, pool_hi=4000),
    ]
    dec = variance_decomposition(stages, bands, 12, 2.0, samples=256,
                                 bootstrap=20, base_params=base)
    pinned = next(s for s in dec.shares if s.slug == "pinned")
    assert pinned.degenerate is True
    assert pinned.first_order == 0.0 and pinned.total_order == 0.0
    assert any("no band recorded" in n for n in dec.notes)


def test_an_unread_pool_is_reported_as_structurally_inert(conn, bands, base):
    """`resolve_pool` reads only the largest pool and the draw stage's. A
    middling stage is recorded, cited, and invisible -- which is a fact
    about the model worth stating, not a very short bar."""
    dec = _run(conn, bands, base, "commodity_foodservice")
    inert = [s for s in dec.shares if s.inert]
    assert inert, "expected some stages the model never reads"
    for s in inert:
        assert s.total_order == 0.0 and not s.degenerate
    assert any("never reads them" in n for n in dec.notes)


# ---------------------------------------------------------------------------
# The findings themselves
# ---------------------------------------------------------------------------

def test_the_commodity_cascade_has_almost_no_variance_to_decompose(
        conn, bands, base):
    """THE NEGATIVE RESULT, computed rather than asserted.

    Every mixing input varied simultaneously across its whole corpus band
    moves the headline answer by a few hundred-thousandths of a chicken.
    That is the saturation claim, measured on the quantity the claim is
    about, and it is the thing this analysis exists to establish.

    If saturation ever stops holding this fails loudly, which is the point.
    """
    dec = _run(conn, bands, base, "commodity_foodservice")
    assert dec.sd < 1e-3, f"sd={dec.sd:.3e}"
    assert dec.sample_hi - dec.sample_lo < 1e-2
    assert any(n.startswith("Saturated") for n in dec.notes)


def test_the_butcher_has_variance_worth_decomposing(conn, bands, base):
    """The paired control. Without it the test above could be passed by an
    estimator that returns zero for everything."""
    dec = _run(conn, bands, base, "local_butcher")
    assert dec.sd > 0.05, f"sd={dec.sd:.3e}"
    assert any(n.startswith("Not saturated") for n in dec.notes)
    assert dec.shares[0].total_order > 0.5


def test_interaction_is_present_in_the_mixing_model(conn, bands, base):
    """The empirical case against using OAT on `distinct`, in the suite
    rather than in a comment. Total-order above first-order is interaction,
    and interaction is exactly what a one-at-a-time sweep cannot see."""
    dec = _run(conn, bands, base, "commodity_foodservice")
    assert dec.sum_total_order > dec.sum_first_order + 0.05


def test_wings_are_untouched_by_the_variance_decomposition(conn, bands, base):
    """The control every domain file in this repo ends with. The new code
    only observes the model, so the published answer must be bit-identical
    either side of running it."""
    from counting_chicken_wings.model import run
    stages = dbm.load_mixing_stages(conn, "commodity_foodservice")
    before = run(12, 2.0, [], stages, params=base)
    _run(conn, bands, base, "commodity_foodservice")
    after = run(12, 2.0, [], stages, params=base)
    assert before.required == after.required
    assert before.distinct_mean == after.distinct_mean
    assert before.container_units == after.container_units
