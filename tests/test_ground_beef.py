"""Ground beef: the subject with no anatomical floor.

Wings and saffron both hand the model a floor for free -- two wings per bird,
three stigmas per flower -- and the interesting work is how far commingling
pushes the answer above it. A hamburger patty hands it nothing. One animal can
supply the whole patty, so the floor is 1, and every number above 1 is
industrial mixing and nothing else.

That makes this the purest test in the corpus of the mixing engine standing on
its own, and it is also where the engine's limits become visible. These tests
pin BOTH: the floor, and the honest shape of an answer the model cannot make
bigger without inventing data.

See docs/research/accepted/batch-06-ground-beef-REVIEW.md, and the header of
data/taxonomy_ground_beef.yaml.
"""

import pytest

from counting_chicken_wings import db as dbm
from counting_chicken_wings.model import MixingStage, run

# Patties per animal, from SDSU Extension's 150-185 lb of lean trim per fed
# steer at a quarter pound of raw trim each. The reciprocal is what the model
# consumes for a continuous product.
PATTIES_PER_ANIMAL = 670.0

# The measured pool: 411-1,367 animals per commercial grind batch, Hu et al.
# 2012, by DNA marker mark-recapture.
BATCH = [
    MixingStage("bin", "Combo bin of trim", 105, "random"),
    MixingStage("grind", "Grind batch", 889, "random"),
]


# ---------------------------------------------------------------------------
# The floor, which is 1, and is the whole point
# ---------------------------------------------------------------------------

def test_one_patty_has_a_floor_of_one_animal():
    """No anatomy sets it. One animal is physically enough for one patty, so
    the floor is 1 -- the `whole_bird_home` situation, in a domain where the
    floor is an observation rather than a constant."""
    res = run(1, PATTIES_PER_ANIMAL, [], BATCH, aggregate_units=True)
    assert res.distinct_ceiling == 1
    assert res.distinct_mean >= 1.0 - 1e-9


def test_the_raw_floor_is_below_one_and_is_clamped_not_reported():
    """A steer yields hundreds of patties, so units/upi is a small fraction.
    The model clamps individual-shares at 1 rather than reporting that a patty
    came from a third of a cow, which would be arithmetically true and
    physically absurd."""
    res = run(1, PATTIES_PER_ANIMAL, [], BATCH, aggregate_units=True)
    assert res.floor < 1.0
    assert res.distinct_ceiling == 1


@pytest.mark.parametrize("patties", [1, 2, 4, 12])
def test_distinct_never_below_floor_for_any_order(patties):
    res = run(patties, PATTIES_PER_ANIMAL, [], BATCH, aggregate_units=True)
    assert res.distinct_mean >= res.floor - 1e-9
    assert res.distinct_mean >= 1.0 - 1e-9


def test_a_bigger_order_needs_more_than_one_animal_eventually():
    """Sanity on the direction of travel: enough patties and even the clamped
    floor rises above one animal. 740 patties is one steer's best case, so
    1,500 cannot come from one."""
    res = run(1500, PATTIES_PER_ANIMAL, [], BATCH, aggregate_units=True)
    assert res.distinct_ceiling >= 3


# ---------------------------------------------------------------------------
# Home-ground: the one route where the answer IS the floor
# ---------------------------------------------------------------------------

def test_home_ground_has_no_mixing_at_all():
    """The whole_bird_home analogue. A custom-exempt butcher grinding one
    animal commingles nothing, so the chain carries no stages and the answer
    is exactly the floor."""
    conn = dbm.connect()
    assert dbm.load_mixing_stages(conn, "home_ground_beef") == []


def test_home_ground_answer_is_exactly_one_animal():
    res = run(1, PATTIES_PER_ANIMAL, [], [], aggregate_units=True)
    assert res.distinct_mean == pytest.approx(1.0, rel=1e-9)
    assert res.distinct_ceiling == 1


# ---------------------------------------------------------------------------
# The control: wings are untouched
# ---------------------------------------------------------------------------

def test_wings_are_untouched_by_a_third_domain():
    """A dozen wings still comes from between six and twelve chickens. A new
    domain that moved the project's headline answer would be a bug, however
    good its data."""
    wings = run(12, 2.0, [], BATCH)
    assert 6.0 <= wings.distinct_mean <= 12.0
    assert wings.distinct_ceiling == 12.0


def test_the_poultry_corpus_still_answers_the_founding_question():
    conn = dbm.connect()
    prod = dbm.get_product(conn, "whole_wing")
    assert prod["units_per_individual_mode"] == 2
    assert prod["is_anatomical_constant"] == 1


# ---------------------------------------------------------------------------
# The corpus wires up, and says what it means
# ---------------------------------------------------------------------------

def test_the_patty_claims_no_anatomical_constant():
    """The contrast with saffron_stigma is the lesson of the subject. Three
    stigmas per flower is anatomy; there is no number of cattle a patty must
    contain."""
    conn = dbm.connect()
    prod = dbm.get_product(conn, "ground_beef_patty")
    assert prod["is_anatomical_constant"] == 0
    assert prod["yield_mode"] == "continuous"


def test_ground_beef_has_its_own_supply_chain():
    """default_supply_chain has no cross-species fallback by design, so cattle
    cannot quietly inherit the wing cascade."""
    conn = dbm.connect()
    assert dbm.default_supply_chain(conn, "beef_cattle") == "commodity_ground_beef"


def test_livestock_is_a_third_domain():
    conn = dbm.connect()
    row = conn.execute(
        """SELECT d.slug FROM species s JOIN domain d ON d.id = s.domain_id
           WHERE s.slug = 'beef_cattle'"""
    ).fetchone()
    assert row["slug"] == "livestock"


def test_the_grind_batch_pool_is_the_first_one_anybody_measured():
    """Every other mixing pool in this corpus cites project-estimate-mixing,
    because nobody in those trades measures pool size. Hu et al. counted this
    one by DNA, so it is the single mixing stage in the project resting on a
    study rather than on our own reasoning -- and if that ever silently
    reverts to an estimate, the strongest evidence the model has is gone."""
    conn = dbm.connect()
    row = conn.execute(
        """SELECT m.pool_lo, m.pool_hi, m.confidence, s.slug AS source_slug
           FROM mixing_stage m JOIN source s ON s.id = m.source_id
           WHERE m.slug = 'beef_grind_batch'"""
    ).fetchone()
    assert row["pool_lo"] == 411
    assert row["pool_hi"] == 1367
    assert row["confidence"] == "study"
    assert row["source_slug"] == "plos-hu-2012-grind-batch"


# ---------------------------------------------------------------------------
# applies_to discipline, in a domain with a mammal in it
# ---------------------------------------------------------------------------

def test_every_beef_loss_stage_is_mass_only():
    """Dressing removes 38% of a steer's weight and cannot remove any part of
    a steer. The guard written so that frying could not change a chicken count
    now stops a slaughter floor from doing it, with no code change."""
    conn = dbm.connect()
    stages = dbm.load_loss_stages(conn, "beef_cattle", "ground_beef_patty",
                                  chain_slug="commodity_ground_beef")
    assert stages, "the beef loss chain should load"
    for s in stages:
        assert s.applies_to == "mass"
        assert not s.affects_count()


def test_the_mass_chain_cannot_move_the_required_count():
    conn = dbm.connect()
    stages = dbm.load_loss_stages(conn, "beef_cattle", "ground_beef_patty",
                                  chain_slug="commodity_ground_beef")
    res = run(1, PATTIES_PER_ANIMAL, stages, BATCH, aggregate_units=True)
    assert res.required == pytest.approx(res.floor, rel=1e-9)
