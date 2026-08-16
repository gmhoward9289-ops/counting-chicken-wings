"""Tests for the data-access layer.

Most of this module is straightforward SQL, with one exception worth real
scrutiny: load_loss_stages resolves competing factors by specificity, and
silently picking the wrong one would change every answer the program gives
without failing anything.
"""

import pytest

from counting_chicken_wings import db as dbm


@pytest.fixture(scope="module")
def conn():
    c = dbm.connect()
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def test_get_product_returns_species_wording(conn):
    """The CLI and API build prose from these, so they must be present."""
    p = dbm.get_product(conn, "whole_wing")
    assert p["individual_noun"] == "chicken"
    assert p["individual_plural"] == "chickens"
    assert p["units_per_individual_mode"] == 2


def test_unknown_product_raises_keyerror(conn):
    with pytest.raises(KeyError):
        dbm.get_product(conn, "griffin_wing")


def test_list_products_puts_active_species_first(conn):
    rows = dbm.list_products(conn)
    actives = [r["active"] for r in rows]
    assert actives == sorted(actives, reverse=True)


def test_list_products_sorts_by_display_name_within_activity(conn):
    """Pickers render this list verbatim, so the source prefixes must group:
    'Chicken: Bone-in wing' next to 'Chicken: Egg', not scattered by slug."""
    rows = dbm.list_products(conn)
    for chunk in (True, False):
        names = [(r["display_name"] or r["label"]).lower()
                 for r in rows if bool(r["active"]) is chunk]
        assert names == sorted(names)


def test_active_products_carry_a_prefixed_display_name(conn):
    """Every picker entry leads with its source: 'Chicken: Bone-in wing'.

    The pickers mix species, so an unprefixed option ('Egg') gives no hint
    of what is being counted. `label` stays bare because prose composes it
    mid-sentence; `display_name` is the picker-only form, and the 'Source: '
    shape is the convention this test keeps new products honest about.
    """
    for r in dbm.list_products(conn):
        if not r["active"]:
            continue
        assert r["display_name"], f"{r['slug']} has no display_name"
        assert ": " in r["display_name"], (
            f"{r['slug']} display_name '{r['display_name']}' lacks the "
            "'Source: product' prefix")


# ---------------------------------------------------------------------------
# Loss stage resolution
# ---------------------------------------------------------------------------

def test_each_stage_appears_at_most_once(conn):
    """A stage with one factor per product must not load twice.

    Note this passes trivially against the current corpus: the query filters
    to a single product, so per-product factors already collapse to one row.
    The case that actually exercises the dedupe is built explicitly in
    test_specific_factor_beats_general_when_both_exist below.
    """
    stages = dbm.load_loss_stages(conn, "broiler", "whole_wing")
    slugs = [s.slug for s in stages]
    assert len(slugs) == len(set(slugs))


def test_specific_factor_beats_general_when_both_exist(tmp_path):
    """The ambiguous case: one stage, a general factor AND a specific one.

    No current data hits this, so it has to be constructed. Without the
    dedupe the stage loads twice and its loss is applied twice, silently
    changing every answer the program gives. Resolution must be by
    specificity -- the product-specific factor wins.
    """
    c = dbm.connect(tmp_path / "ambiguous.db")
    try:
        stage_id, species_id, source_id = c.execute("""
            SELECT ls.id, lf.species_id, lf.source_id
            FROM loss_stage ls JOIN loss_factor lf ON lf.loss_stage_id = ls.id
            WHERE ls.slug = 'wing_damage' LIMIT 1
        """).fetchone()

        specific = c.execute(
            "SELECT survive_mode FROM loss_factor "
            "WHERE loss_stage_id = ? AND product_id IS NOT NULL",
            (stage_id,),
        ).fetchone()[0]

        # A general factor for the same stage, deliberately different.
        c.execute("""
            INSERT INTO loss_factor
              (loss_stage_id, species_id, product_id, survive_lo,
               survive_mode, survive_hi, confidence, source_id)
            VALUES (?, ?, NULL, 0.5, 0.5, 0.5, 'estimate', ?)
        """, (stage_id, species_id, source_id))
        c.commit()

        loaded = dbm.load_loss_stages(c, "broiler", "whole_wing")
        hits = [s for s in loaded if s.slug == "wing_damage"]

        assert len(hits) == 1, "stage loaded twice; its loss would double-apply"
        assert hits[0].survive_mode == pytest.approx(specific), \
            "the general factor won; resolution is not by specificity"
    finally:
        c.close()


def test_product_specific_factor_wins_over_general(conn):
    """transit_rejection carries a different figure per product."""
    whole = {s.slug: s for s in
             dbm.load_loss_stages(conn, "broiler", "whole_wing")}
    boneless = {s.slug: s for s in
                dbm.load_loss_stages(conn, "broiler", "boneless_wing")}
    assert (whole["transit_rejection"].survive_mode
            != boneless["transit_rejection"].survive_mode)


def test_optional_stages_are_excluded_by_default(conn):
    slugs = {s.slug for s in dbm.load_loss_stages(conn, "broiler",
                                                  "whole_wing")}
    assert "farm_mortality" not in slugs
    assert "plate_waste" not in slugs


def test_optional_stages_appear_when_requested(conn):
    slugs = {s.slug for s in dbm.load_loss_stages(
        conn, "broiler", "whole_wing", include_optional=True)}
    assert "farm_mortality" in slugs


def test_stages_come_back_in_pipeline_order(conn):
    stages = dbm.load_loss_stages(conn, "broiler", "whole_wing")
    seqs = [s.sequence for s in stages]
    assert seqs == sorted(seqs)


def test_every_loaded_stage_carries_its_citation(conn):
    for s in dbm.load_loss_stages(conn, "broiler", "whole_wing"):
        assert s.source_slug, s.slug
        assert s.confidence, s.slug


def test_bands_are_ordered_on_load(conn):
    for s in dbm.load_loss_stages(conn, "broiler", "whole_wing"):
        assert s.survive_lo <= s.survive_mode <= s.survive_hi, s.slug


def test_mass_stages_are_flagged_as_not_affecting_count(conn):
    by_slug = {s.slug: s for s in
               dbm.load_loss_stages(conn, "broiler", "whole_wing")}
    assert not by_slug["cook_loss"].affects_count()
    assert by_slug["wing_damage"].affects_count()


# ---------------------------------------------------------------------------
# Supply chains and mixing
# ---------------------------------------------------------------------------

def test_default_supply_chain_exists_and_is_listed(conn):
    for species in ("broiler", "layer_hen"):
        default = dbm.default_supply_chain(conn, species)
        assert default in {c["slug"] for c in dbm.list_supply_chains(conn)}


def test_default_supply_chain_is_species_specific(conn):
    """Eggs and wings must not resolve to the same route.

    They did, which is the bug this argument exists to prevent: eggs took the
    wing chain and were explained via a cut-up line and a fryer basket.
    """
    assert (dbm.default_supply_chain(conn, "broiler")
            != dbm.default_supply_chain(conn, "layer_hen"))


def test_default_supply_chain_refuses_to_guess(conn):
    """No species, no answer -- and no borrowing another animal's chain."""
    with pytest.raises(ValueError):
        dbm.default_supply_chain(conn, "")
    with pytest.raises(LookupError):
        dbm.default_supply_chain(conn, "turkey")   # stubbed, has no routes


def test_an_egg_query_never_touches_a_wing_stage(conn):
    """The regression guard for the whole v1.2.0 fix.

    An egg has no cut-up line, no wing chiller, no size grading, no IQF
    freezer and no fryer basket. If any of those appear in an egg cascade the
    audit trail is lying, however right the number looks.
    """
    wing_only = {"separation", "wing_chiller", "size_grading", "combo_bin",
                 "iqf_freezer", "case_pack", "distributor",
                 "restaurant_freezer", "fryer_basket"}
    chain = dbm.default_supply_chain(conn, "layer_hen")
    stages = {s.slug for s in dbm.load_mixing_stages(conn, chain)}
    assert stages, "egg chain has no stages"
    assert not (stages & wing_only), sorted(stages & wing_only)


def test_egg_grading_does_not_separate(conn):
    """Weighing wings splits a bird's pair. Weighing eggs splits nothing.

    A bird has exactly two wings, so grading by weight routes them to
    different boxes. Each egg is already a lone contribution -- there is no
    pair for grading to break -- so marking it 'separating' would invent a
    mechanism that does not exist.
    """
    chain = dbm.default_supply_chain(conn, "layer_hen")
    for s in dbm.load_mixing_stages(conn, chain):
        assert s.mixing_kind != "separating", s.slug


def test_commodity_chain_loads_the_full_cascade(conn):
    stages = dbm.load_mixing_stages(conn, "commodity_foodservice")
    assert len(stages) > 5
    assert any(s.mixing_kind == "separating" for s in stages)


def test_home_chain_has_no_mixing_at_all(conn):
    assert dbm.load_mixing_stages(conn, "whole_bird_home") == []


def test_mixing_stages_come_back_in_order(conn):
    stages = dbm.load_mixing_stages(conn, "commodity_foodservice")
    labels = [s.label for s in stages]
    assert labels[0].lower().startswith("cut-up")


def test_pool_override_is_respected(conn):
    """A butcher's tray must not inherit the plant-scale pool."""
    butcher = dbm.load_mixing_stages(conn, "local_butcher")
    commodity = dbm.load_mixing_stages(conn, "commodity_foodservice")
    b_sep = next(s for s in butcher if s.slug == "separation")
    c_sep = next(s for s in commodity if s.slug == "separation")
    assert b_sep.pool < c_sep.pool


def test_overridden_pool_band_is_rescaled_not_inherited(conn):
    """Inheriting the plant band would sample a 40-bird tray up to 20,000."""
    for s in dbm.load_mixing_stages(conn, "local_butcher"):
        lo, mode, hi = s.band()
        assert lo <= mode <= hi
        assert hi <= max(mode * 10, mode + 1), s.slug


def test_a_smaller_override_still_produces_a_band_not_a_point(conn):
    """The bug this regresses: clamping the rescale to 1.0 collapsed a
    below-default override to lo == mode == hi -- no band at all, on
    exactly the case an override exists to model (#116)."""
    stages = dbm.load_mixing_stages(conn, "local_butcher")
    overridden = [s for s in stages if s.pool < 500]
    assert overridden, "expected at least one overridden stage under 500"
    for s in overridden:
        lo, mode, hi = s.band()
        assert lo < hi, s.slug


def test_unknown_chain_loads_nothing(conn):
    assert dbm.load_mixing_stages(conn, "not_a_chain") == []


# ---------------------------------------------------------------------------
# Sources and facts
# ---------------------------------------------------------------------------

def test_get_sources_maps_slugs_to_records(conn):
    got = dbm.get_sources(conn, ["nass-poultry-slaughter-2025"])
    assert "nass-poultry-slaughter-2025" in got
    assert got["nass-poultry-slaughter-2025"]["publisher"]


def test_get_sources_of_nothing_is_empty(conn):
    assert dbm.get_sources(conn, []) == {}


def test_get_sources_ignores_unknown_slugs(conn):
    assert dbm.get_sources(conn, ["not-a-source"]) == {}


def test_result_facts_exclude_learning_only_ones(conn):
    for f in dbm.get_facts(conn, "result", limit=20):
        assert f["source_title"]


def test_facts_are_ordered_by_surprise(conn):
    rows = dbm.get_facts(conn, "learning", limit=10)
    surprises = [r["surprise"] for r in rows]
    assert surprises == sorted(surprises, reverse=True)


def test_fact_limit_is_honoured(conn):
    assert len(dbm.get_facts(conn, "learning", limit=3)) <= 3


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------

def test_connect_builds_a_missing_database(tmp_path):
    path = tmp_path / "fresh.db"
    assert not path.exists()
    c = dbm.connect(path)
    try:
        assert path.exists()
        assert c.execute("SELECT COUNT(*) FROM source").fetchone()[0] > 0
    finally:
        c.close()


def test_foreign_keys_are_enforced_on_every_connection(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Channel-aware loss stages
# ---------------------------------------------------------------------------

def test_a_chain_can_declare_its_own_losses(conn):
    """The grocery route pays supermarket shrink; the restaurant route does not.

    Before chains could select losses, every chain got every stage, so
    retail_shrink had to be parked default-off to stop it double-counting
    against kitchen_loss. That was a workaround standing in for a model.
    """
    food = {s.slug for s in dbm.load_loss_stages(
        conn, "broiler", "whole_wing", chain_slug="commodity_foodservice")}
    groc = {s.slug for s in dbm.load_loss_stages(
        conn, "broiler", "whole_wing", chain_slug="grocery_retail")}

    assert "kitchen_loss" in food and "retail_shrink" not in food
    assert "retail_shrink" in groc and "kitchen_loss" not in groc


def test_no_route_pays_both_retail_and_kitchen(conn):
    """The double-count the old workaround existed to prevent.

    A wing does not pass a supermarket meat counter AND a restaurant kitchen.
    Any route claiming both is charging the same loss twice.
    """
    for ch in dbm.list_supply_chains(conn):
        stages = {s.slug for s in dbm.load_loss_stages(
            conn, "broiler", "whole_wing", chain_slug=ch["slug"])}
        assert not {"retail_shrink", "kitchen_loss"} <= stages, ch["slug"]


def test_a_declaring_chain_may_claim_a_default_off_stage(conn):
    """retail_shrink is default_enabled=0, and the grocery route still gets it.

    That is the point: the stage is not globally disabled, it belongs to one
    route. A chain being explicit overrides the global default.
    """
    row = conn.execute(
        "SELECT default_enabled, optional FROM loss_stage "
        "WHERE slug = 'retail_shrink'"
    ).fetchone()
    assert not row["default_enabled"], "precondition: stage is default-off"

    groc = {s.slug for s in dbm.load_loss_stages(
        conn, "broiler", "whole_wing", chain_slug="grocery_retail")}
    assert "retail_shrink" in groc


def test_chains_without_declared_losses_are_unaffected(conn):
    """Silence means "species defaults", so existing routes keep working."""
    assert dbm.chain_loss_stages(conn, "local_butcher") is None
    stages = dbm.load_loss_stages(
        conn, "broiler", "whole_wing", chain_slug="local_butcher")
    assert stages, "default path returned nothing"


# ---------------------------------------------------------------------------
# Correlated loss groups (#77)
# ---------------------------------------------------------------------------

def test_handling_quality_group_loads_for_broiler(conn):
    groups = dbm.load_correlated_groups(conn, "broiler")
    by_slug = {g.slug: g for g in groups}
    assert "handling_quality" in by_slug
    g = by_slug["handling_quality"]
    assert set(g.stage_slugs) == {
        "wing_damage", "grading_downgrade", "transport_doa"
    }
    assert 0.0 <= g.rho < 1.0
    assert g.confidence
    assert g.source_slug


def test_correlated_groups_carry_a_citation(conn):
    """The correlation figure is an estimate like any other in the model,
    so it must resolve to a real row in `source` -- not a dangling slug."""
    groups = dbm.load_correlated_groups(conn, "broiler")
    slugs = [g.source_slug for g in groups]
    sources = dbm.get_sources(conn, slugs)
    assert set(sources) == set(slugs)


def test_species_with_no_correlation_group_gets_an_empty_list(conn):
    """A species with no factor rows for any grouped stage must not crash
    and must not surface an empty, meaningless group."""
    groups = dbm.load_correlated_groups(conn, "layer_hen")
    assert groups == []
