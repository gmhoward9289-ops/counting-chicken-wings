"""Saffron: the second domain, and the first product that is not an animal part.

These tests exist because landing saffron broke something real. The pooling
maths had a buried assumption -- that every contributing individual gives at
least one WHOLE unit -- which is true of every poultry product and false of a
gram of saffron, where about 150 flowers each contribute a sliver of mass.

Asking for one gram therefore returned "came from about 1 different flower"
while the floor in the same run said 150. Two numbers from one calculation
contradicting each other, in the project's headline output.

So the invariant under test is not a figure, it is a shape: the distinct count
can never fall below the floor, for any product in any domain, whatever the
yield mode. The saffron figures will get refined; that must not.
"""

import pytest

from counting_chicken_wings import db as dbm
from counting_chicken_wings.model import MixingStage, run

# 1/150 grams of dried spice per flower, per UC ANR.
GRAMS_PER_FLOWER = 0.0066666667
STIGMAS_PER_FLOWER = 3.0

LOT = [
    MixingStage("tray", "Picking tray", 5000, "random"),
    MixingStage("pack", "Lot packing", 150000, "random"),
]


# ---------------------------------------------------------------------------
# The bug, stated as an invariant
# ---------------------------------------------------------------------------

def test_a_gram_of_saffron_came_from_at_least_its_floor():
    """The regression. Before aggregate_units this returned 1.0."""
    res = run(1, GRAMS_PER_FLOWER, [], LOT, aggregate_units=True)
    assert res.floor == pytest.approx(150, rel=1e-6)
    assert res.distinct_mean >= res.floor - 1e-6


@pytest.mark.parametrize("grams", [1, 2, 5, 28])
def test_distinct_never_below_floor_for_any_order(grams):
    res = run(grams, GRAMS_PER_FLOWER, [], LOT, aggregate_units=True)
    assert res.distinct_mean >= res.floor - 1e-6


def test_countable_products_are_untouched_by_the_fix():
    """A wing belongs to exactly one bird, so its draw count is its unit
    count. The fix must not reach products that were already right."""
    wings = run(12, 2.0, [], LOT)
    assert 6.0 <= wings.distinct_mean <= 12.0
    assert wings.distinct_ceiling == 12.0


# ---------------------------------------------------------------------------
# The ceiling, which was printing as 1 against a floor of 150
# ---------------------------------------------------------------------------

def test_continuous_ceiling_is_the_floor_not_the_unit_count():
    """Mass is fungible: every contributing flower supplies one share and
    there are exactly `floor` shares, so floor and ceiling coincide. The unit
    count (1 gram) is not a headcount and must never be read as one."""
    res = run(1, GRAMS_PER_FLOWER, [], LOT, aggregate_units=True)
    assert res.distinct_ceiling == 150
    assert res.distinct_ceiling != 1


def test_countable_ceiling_is_still_the_unit_count():
    res = run(12, STIGMAS_PER_FLOWER, [], LOT)
    assert res.distinct_ceiling == 12.0


# ---------------------------------------------------------------------------
# applies_to discipline, in a domain it was not designed for
# ---------------------------------------------------------------------------

def test_drying_is_mass_only_so_it_cannot_move_a_count():
    """The 80% drying loss is the biggest number in the subject and it must
    change nothing. Two independent reasons compound: mass stages never touch
    counts, and the 150-flowers figure is already a dried-basis figure, so
    applying it would double-count to 750 flowers per gram."""
    conn = dbm.connect()
    stages = dbm.load_loss_stages(conn, "saffron_crocus", "saffron_gram",
                                  chain_slug="commodity_spice")
    drying = [s for s in stages if s.slug == "saffron_drying"]
    assert drying, "the drying stage should be loaded for saffron"
    assert drying[0].applies_to == "mass"
    assert not drying[0].affects_count()

    res = run(1, GRAMS_PER_FLOWER, stages, LOT, aggregate_units=True)
    # required == floor: nothing in the default chain removes a flower.
    assert res.required == pytest.approx(res.floor, rel=1e-9)


def test_field_loss_is_off_by_default_so_the_answer_stays_sourced():
    """The one unsourced saffron stage is the one that would move the count,
    so it is default-off. The default answer rests only on cited figures."""
    conn = dbm.connect()
    default = dbm.load_loss_stages(conn, "saffron_crocus", "saffron_gram",
                                   chain_slug="commodity_spice")
    assert not any(s.slug == "saffron_field_loss" for s in default)

    opt = dbm.load_loss_stages(conn, "saffron_crocus", "saffron_gram",
                               include_optional=True)
    assert any(s.slug == "saffron_field_loss" for s in opt)


# ---------------------------------------------------------------------------
# The floor's honesty about its own grade
# ---------------------------------------------------------------------------

def test_anatomical_floor_is_not_claimed_for_a_reported_average():
    """Three stigmas per flower is anatomy and may be called measured. About
    150 flowers per gram is an extension service's rule of thumb, and saying
    "Anatomical floor / measured" over it would launder a grade -- in the one
    project where grades are the product."""
    soft = run(1, GRAMS_PER_FLOWER, [], LOT, aggregate_units=True,
               anatomical=False, floor_source="ucanr-mg-saffron")
    step = soft.trace[0]
    assert step.stage_label == "Yield floor"
    assert step.confidence == "industry"
    assert step.source_slug == "ucanr-mg-saffron"

    hard = run(12, STIGMAS_PER_FLOWER, [], LOT, anatomical=True)
    assert hard.trace[0].stage_label == "Anatomical floor"
    assert hard.trace[0].confidence == "measured"


# ---------------------------------------------------------------------------
# The corpus wires up
# ---------------------------------------------------------------------------

def test_saffron_has_its_own_supply_chain():
    """default_supply_chain has no cross-species fallback by design, so a
    species without a chain of its own raises rather than inheriting the wing
    cascade -- the bug that walked eggs through a fryer basket."""
    conn = dbm.connect()
    assert dbm.default_supply_chain(conn, "saffron_crocus") == "commodity_spice"


def test_three_stigmas_per_flower_is_a_hard_constant():
    conn = dbm.connect()
    prod = dbm.get_product(conn, "saffron_stigma")
    assert prod["units_per_individual_mode"] == 3
    assert prod["units_per_individual_lo"] == 3
    assert prod["units_per_individual_hi"] == 3
    assert prod["is_anatomical_constant"] == 1


def test_the_gram_figure_is_not_claimed_as_a_constant():
    conn = dbm.connect()
    prod = dbm.get_product(conn, "saffron_gram")
    assert prod["is_anatomical_constant"] == 0
    assert prod["yield_mode"] == "continuous"


def test_two_sources_agree_on_flowers_per_gram_within_five_percent():
    """The cross-check that makes this subject trustworthy at all. UC ANR
    states 150 flowers per gram outright. HS661 says 210,000 stigmas per
    pound, which at three stigmas per flower is 154.3 flowers per gram by a
    completely different route -- and its own wording is "Supposedly"."""
    stated = 150.0
    implied = (210_000 / 3) / 453.59237
    assert abs(implied - stated) / stated < 0.05


def test_saffron_is_a_second_domain():
    conn = dbm.connect()
    row = conn.execute(
        """SELECT d.slug FROM species s JOIN domain d ON d.id = s.domain_id
           WHERE s.slug = 'saffron_crocus'"""
    ).fetchone()
    assert row["slug"] == "horticulture"
