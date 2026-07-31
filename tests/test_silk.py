"""Silk: the fifth domain, and the first product measured in garments.

Three things here are worth a test rather than a comment.

1. THE HARD FLOOR. One silkworm spins one cocoon. Every per-garment figure in
   the subject is a cocoon count, and a cocoon count is only an animal count
   because that constant holds -- so it is the single load-bearing number, and
   it is also the only figure in the corpus that no automated extraction could
   produce. It was withdrawn from the COOPER batch and recorded as a human
   judgement. A test pins it so a later edit cannot quietly soften it.

2. THE RECIPROCAL ROUNDING. Every garment yield is 1/n for a whole number n of
   cocoons, and the answer divides back through ceil(). Round 1/n the wrong way
   and the headline integer comes out one too high -- 1/1850 written to ten
   digits returns a dress of 1851 silkworms. That is not hypothetical; it
   happened twice while landing this file, at two different figures. The
   arithmetic is pinned at every bound of every product.

3. THE CONTROL. Silk adds a domain, three mixing stages and one loss stage, all
   of which merge into the same tables poultry uses. The wing answer must not
   move by a hair.
"""

import math

import pytest

from counting_chicken_wings import db as dbm
from counting_chicken_wings.model import MixingStage, run

# Cocoons per garment, as the sources state them. The corpus stores the
# reciprocals; these are what they must divide back to.
COCOONS_PER = {
    "silk_necktie": (150, 150, 150),
    "silk_shirt": (1000, 1000, 1000),
    # lo/hi invert: the source's LOW cocoon count is the HIGH yield.
    "silk_dress": (2000, 1850, 1700),
    "silk_pound_raw": (3000, 2500, 2000),
}

BOUNDS = ("units_per_individual_lo", "units_per_individual_mode",
          "units_per_individual_hi")


def silk_mixing(conn, chain="commodity_silk"):
    return dbm.load_mixing_stages(conn, chain)


# ---------------------------------------------------------------------------
# 1. The hard floor
# ---------------------------------------------------------------------------

def test_one_cocoon_per_silkworm_is_a_hard_constant():
    """The anatomical constant, and the whole reason silk is in the corpus.

    The twin of two wings per chicken and three stigmas per flower, in its
    degenerate one-to-one form. If this stops being exactly 1, every garment
    figure in the subject stops being a headcount."""
    conn = dbm.connect()
    prod = dbm.get_product(conn, "silkworm_cocoon")
    assert prod["units_per_individual_lo"] == 1
    assert prod["units_per_individual_mode"] == 1
    assert prod["units_per_individual_hi"] == 1
    assert prod["is_anatomical_constant"] == 1
    assert prod["yield_mode"] == "countable"


def test_twelve_cocoons_came_from_twelve_silkworms():
    """The constant expressed as the answer it produces. One-to-one leaves no
    room between floor and ceiling at all -- unlike wings, where the whole
    interesting result is the six-to-twelve band."""
    conn = dbm.connect()
    res = run(12, 1.0, [], silk_mixing(conn))
    assert res.floor == 12
    assert res.distinct_ceiling == 12
    assert res.distinct_mean == pytest.approx(12)


def test_no_garment_figure_claims_to_be_a_constant():
    """Cocoons per tie is trade lore with no survey behind it. Only the
    one-cocoon-per-worm relation may carry is_anatomical_constant, and letting
    a garment figure claim it would launder the softest numbers in the corpus
    into the strongest guarantee it makes."""
    conn = dbm.connect()
    for slug in COCOONS_PER:
        prod = dbm.get_product(conn, slug)
        assert prod["is_anatomical_constant"] == 0, slug
        assert prod["yield_mode"] == "continuous", slug


# ---------------------------------------------------------------------------
# 2. The reciprocal rounding
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slug", sorted(COCOONS_PER))
def test_every_garment_bound_divides_back_to_a_whole_cocoon_count(slug):
    """The regression, and it fired twice for real while landing this file.

    floor = quantity / yield, then ceil(). A reciprocal rounded DOWN lands the
    division just above n and ceil() pushes it to n+1: 1/1850 at ten digits
    gave 1851, and 1/1700 at eighteen digits gave 1701. Both are one worm of
    pure arithmetic noise sitting in a headline figure."""
    conn = dbm.connect()
    prod = dbm.get_product(conn, slug)
    mix = silk_mixing(conn)
    for key, expected in zip(BOUNDS, COCOONS_PER[slug]):
        res = run(1, prod[key], [], mix, aggregate_units=True)
        assert res.distinct_ceiling == expected, f"{slug}.{key}"
        # And the floor must READ as the integer too, not as 149.2537 -- a
        # bound can ceil correctly while still printing false precision into
        # the audit trail, which is the half of this bug that is easy to miss.
        assert res.floor == pytest.approx(expected, abs=1e-6), f"{slug}.{key}"


@pytest.mark.parametrize("slug", sorted(COCOONS_PER))
def test_reciprocals_are_rounded_up_not_down(slug):
    """States the rule directly, so a future editor who 'tidies' a long decimal
    is told which direction is safe rather than left to rediscover it."""
    conn = dbm.connect()
    prod = dbm.get_product(conn, slug)
    for key, n in zip(BOUNDS, COCOONS_PER[slug]):
        v = prod[key]
        assert v >= 1 / n, f"{slug}.{key} rounded down; ceil() will overshoot"
        assert math.ceil(1 / v) == n, f"{slug}.{key}"


def test_the_bands_invert_because_they_are_reciprocals():
    """A dress is 1700-2000 cocoons, so its LO yield is 1/2000. Getting this
    backwards would silently swap a subject's error bars end for end, and the
    schema's lo <= mode <= hi CHECK would not notice, since both orderings
    satisfy it."""
    conn = dbm.connect()
    dress = dbm.get_product(conn, "silk_dress")
    assert dress["units_per_individual_lo"] < dress["units_per_individual_hi"]
    # Fewest cocoons (1700) is the most generous yield, hence `hi`.
    assert 1 / dress["units_per_individual_hi"] == pytest.approx(1700, abs=1e-6)
    assert 1 / dress["units_per_individual_lo"] == pytest.approx(2000, abs=1e-6)


# ---------------------------------------------------------------------------
# The garment shape: floor and ceiling coincide
# ---------------------------------------------------------------------------

def test_a_necktie_pins_to_its_floor_with_no_band():
    """Silk thread is a blend from the first operation onward -- five cocoons
    are combined before the material is even a thread -- so no two shares of a
    woven cloth plausibly come from the same worm. Floor and ceiling therefore
    meet, and the answer is 150 rather than 'between 150 and something'.

    This is the saffron shape, and the opposite of wings."""
    conn = dbm.connect()
    prod = dbm.get_product(conn, "silk_necktie")
    res = run(1, prod["units_per_individual_mode"], [], silk_mixing(conn),
              aggregate_units=True)
    assert res.floor == pytest.approx(150, abs=1e-6)
    assert res.distinct_ceiling == 150
    assert res.distinct_mean >= res.floor - 1e-6
    # The unit count is 1 necktie and is not a headcount. Reading it as one is
    # the bug saffron's aggregate_units fix exists to prevent.
    assert res.distinct_mean != 1


# ---------------------------------------------------------------------------
# Corpus wiring
# ---------------------------------------------------------------------------

def test_silk_has_its_own_supply_chain():
    """default_supply_chain has no cross-species fallback by design, so a
    species without a chain of its own raises rather than inheriting the wing
    cascade -- the bug that walked eggs through a fryer basket."""
    conn = dbm.connect()
    assert dbm.default_supply_chain(conn, "silkworm") == "commodity_silk"


def test_silk_is_its_own_domain():
    conn = dbm.connect()
    row = conn.execute(
        """SELECT d.slug FROM species s JOIN domain d ON d.id = s.domain_id
           WHERE s.slug = 'silkworm'"""
    ).fetchone()
    assert row["slug"] == "sericulture"


def test_reeling_is_the_only_sourced_mixing_pool_in_the_project():
    """Every other mixing stage in the corpus cites project-estimate-mixing,
    because nobody in any trade measures pool size. Reeling is the exception:
    a source states five cocoons per thread outright, and both COOPER models
    returned it independently. Worth a test because the value of that stage is
    entirely that it is NOT our estimate."""
    conn = dbm.connect()
    reeling = [m for m in silk_mixing(conn) if m.slug == "silk_reeling"]
    assert reeling, "the reeling stage should load for silk"
    assert reeling[0].pool == 5
    assert reeling[0].confidence == "industry"
    assert reeling[0].source_slug == "suekayton-silk-thread-and-cloth"


def test_reeling_does_not_dominate_the_garment_answer():
    """The batch asked for this figure as a contrast with ground beef, where
    mixing is the whole story. Here it is real and small: 150 cocoons go into a
    tie whether they were reeled five at a time or fifty. What reeling actually
    buys is the guarantee of no repeats."""
    conn = dbm.connect()
    prod = dbm.get_product(conn, "silk_necktie")
    y = prod["units_per_individual_mode"]
    with_reeling = run(1, y, [], silk_mixing(conn), aggregate_units=True)
    huge = [MixingStage("r", "Reeling", 500, "random"),
            MixingStage("w", "Warp", 500000, "random")]
    without = run(1, y, [], huge, aggregate_units=True)
    assert with_reeling.distinct_mean == pytest.approx(
        without.distinct_mean, rel=1e-9)


def test_the_one_unsourced_silk_stage_is_off_by_default():
    """Silk's only loss stage is our own reasoning, so it is default-off and
    the default silk answer rests entirely on cited figures. Same standard
    saffron set. It changes how many worms were REARED, never how many are in
    the garment."""
    conn = dbm.connect()
    default = dbm.load_loss_stages(conn, "silkworm", "silk_necktie",
                                   chain_slug="commodity_silk")
    assert default == []

    opt = dbm.load_loss_stages(conn, "silkworm", "silk_necktie",
                               include_optional=True)
    assert {s.slug for s in opt} == {"silk_breeding_stock"}


def test_rearing_mortality_is_left_out_rather_than_guessed():
    """The honest band for larval mortality is 0.70-0.97, which spans an order
    of magnitude and is not a band at all. Writing it as lo/mode/hi would make
    an admission of ignorance look like a measurement to everything downstream,
    so it is prose in the YAML header and not a row.

    Pinned because the obvious 'improvement' to this file is to add it back."""
    conn = dbm.connect()
    opt = dbm.load_loss_stages(conn, "silkworm", "silk_necktie",
                               include_optional=True)
    assert not any("mortality" in s.slug for s in opt)


def test_stifling_the_pupa_is_not_a_loss_stage():
    """Every commercial cocoon is stifled with the pupa alive inside, which is
    100% mortality and belongs nowhere in the loss chain -- because it removes
    no silk. It is the opposite: killing the pupa is what keeps the filament
    unbroken, since an emerging moth would cut it into useless lengths.

    A loss chain measures what is lost, and nothing is lost here. The fact
    belongs in facts.yaml, and this test stops it being 'corrected' into the
    model by someone reading only the mortality rate."""
    conn = dbm.connect()
    opt = dbm.load_loss_stages(conn, "silkworm", "silk_necktie",
                               include_optional=True)
    for s in opt:
        assert "stifl" not in s.slug and "pupa" not in s.slug


# ---------------------------------------------------------------------------
# 3. The control
# ---------------------------------------------------------------------------

def test_wings_are_untouched_by_silk():
    """Silk merges a domain, five products, three mixing stages and one loss
    stage into the same tables poultry uses. The founding answer must not move
    by a hair."""
    conn = dbm.connect()
    wing = dbm.get_product(conn, "whole_wing")
    assert wing["units_per_individual_mode"] == 2
    assert wing["is_anatomical_constant"] == 1
    assert dbm.default_supply_chain(conn, "broiler") != "commodity_silk"

    mix = dbm.load_mixing_stages(conn, dbm.default_supply_chain(conn, "broiler"))
    res = run(12, 2.0, [], mix)
    assert res.floor == 6
    assert 6.0 <= res.distinct_mean <= 12.0
    assert res.distinct_ceiling == 12.0
