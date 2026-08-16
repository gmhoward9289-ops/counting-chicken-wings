"""Tests for the HTTP layer.

The load-bearing one here is test_every_cited_step_ships_its_source. The
whole project rests on "no number without a citation", and the API is where
that promise either survives contact with the outside world or quietly
stops being true.
"""

import pytest
from fastapi.testclient import TestClient

from counting_chicken_wings.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def get(client, path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
    return r.json()


# ---------------------------------------------------------------------------
# Smoke
# ---------------------------------------------------------------------------

def test_index_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Counting Chicken Wings" in r.text


@pytest.mark.parametrize("path", [
    "/api/meta", "/api/calculate", "/api/scientific", "/api/mixing-curve",
    "/api/states", "/api/trends", "/api/facts", "/api/sources", "/api/scope",
])
def test_every_endpoint_answers(client, path):
    assert client.get(path).status_code == 200


def test_meta_lists_the_controls_the_ui_needs(client):
    d = get(client, "/api/meta")
    for key in ("chains", "products", "loss_stages", "mixing_stages",
                "producers", "segments"):
        assert d[key], f"{key} is empty"
    assert any(c["is_default"] for c in d["chains"])


# ---------------------------------------------------------------------------
# The citation guarantee, over HTTP
# ---------------------------------------------------------------------------

def test_every_cited_step_ships_its_source(client):
    """A trace step naming a source must arrive with that source attached.

    Without this the UI could render a figure and have nothing to cite
    beside it, which is the one failure mode this project cannot have.
    """
    d = get(client, "/api/calculate", count=12)
    for step in d["trace"]:
        if step["source"]:
            assert step["source"] in d["sources"], step["slug"]


def test_shipped_sources_are_complete_records(client):
    d = get(client, "/api/calculate", count=12)
    for slug, src in d["sources"].items():
        assert src["title"] and src["publisher"] and src["source_type"]


def test_sources_endpoint_reports_usage(client):
    d = get(client, "/api/sources")
    assert d["sources"]
    assert any(s["used_by"] > 0 for s in d["sources"])


# ---------------------------------------------------------------------------
# calculate
# ---------------------------------------------------------------------------

def test_a_dozen_wings_is_six_or_more(client):
    """The project's central claim, asserted at the HTTP boundary."""
    a = get(client, "/api/calculate", count=12)["answer"]
    assert a["floor"] == 6.0
    assert a["required"] >= a["floor"]
    assert a["floor"] <= a["distinct"] <= a["ceiling"]


def test_distinct_never_reaches_the_ceiling_on_a_commodity_chain(client):
    a = get(client, "/api/calculate", count=12,
            chain="commodity_foodservice")["answer"]
    assert a["distinct"] > 11.99
    assert a["distinct"] < a["ceiling"]


def test_cutting_up_whole_birds_yourself_gives_exactly_the_floor(client):
    a = get(client, "/api/calculate", count=12,
            chain="whole_bird_home")["answer"]
    assert a["distinct"] == pytest.approx(a["floor"])


def test_supply_chain_changes_the_answer(client):
    home = get(client, "/api/calculate", count=12,
               chain="whole_bird_home")["answer"]["distinct"]
    butcher = get(client, "/api/calculate", count=12,
                  chain="local_butcher")["answer"]["distinct"]
    commodity = get(client, "/api/calculate", count=12,
                    chain="commodity_foodservice")["answer"]["distinct"]
    assert home < butcher < commodity


def test_pieces_mode_halves_the_bird_count(client):
    """A menu 'dozen wings' is twelve segments, i.e. six whole wings."""
    whole = get(client, "/api/calculate", count=12)["answer"]
    pieces = get(client, "/api/calculate", count=12, pieces=True)["answer"]
    assert pieces["floor"] == pytest.approx(whole["floor"] / 2)


def test_mortality_toggle_raises_the_requirement(client):
    off = get(client, "/api/calculate", count=12)["answer"]["required"]
    on = get(client, "/api/calculate", count=12,
             include_mortality=True)["answer"]["required"]
    assert on > off


def test_scaling_the_order_scales_the_floor(client):
    a = get(client, "/api/calculate", count=12)["answer"]
    b = get(client, "/api/calculate", count=24)["answer"]
    assert b["floor"] == pytest.approx(a["floor"] * 2)


def test_boneless_wings_take_a_fraction_of_a_bird(client):
    """A boneless wing is breast meat, so the floor is far below a real wing."""
    a = get(client, "/api/calculate", count=12,
            product="boneless_wing")["answer"]
    assert a["floor"] < 1.0


# ---------------------------------------------------------------------------
# scientific
# ---------------------------------------------------------------------------

def test_wider_confidence_widens_the_interval(client):
    def width(level):
        a = get(client, "/api/scientific", count=12, iterations=2000,
                confidence_level=level)["answer"]
        return a["required_hi"] - a["required_lo"]
    assert width(0.50) < width(0.90) < width(0.99)


def test_evidence_filter_excludes_and_lowers(client):
    everything = get(client, "/api/scientific", count=12,
                     iterations=2000)["answer"]
    filtered = get(client, "/api/scientific", count=12, iterations=2000,
                   min_confidence="study")["answer"]
    assert filtered["excluded_stages"]
    assert filtered["required"] < everything["required"]


def test_tornado_is_ranked_and_shares_sum_to_one(client):
    t = get(client, "/api/scientific", count=12, iterations=1000)["tornado"]
    assert [x["swing"] for x in t] == sorted(
        (x["swing"] for x in t), reverse=True)
    assert sum(x["share"] for x in t) == pytest.approx(1.0)


def test_mass_only_stages_contribute_no_uncertainty(client):
    t = get(client, "/api/scientific", count=12, iterations=1000)["tornado"]
    for x in t:
        if x["applies_to"] == "mass":
            assert x["swing"] == pytest.approx(0.0)


def test_histograms_account_for_every_draw(client):
    d = get(client, "/api/scientific", count=12, iterations=3000)
    assert sum(d["required_hist"]["counts"]) == 3000
    assert sum(d["distinct_hist"]["counts"]) == 3000


def test_waterfall_walks_from_the_floor(client):
    d = get(client, "/api/scientific", count=12, iterations=1000)
    w, floor = d["waterfall"], d["answer"]["floor"]
    assert w
    assert w[0]["from"] == pytest.approx(floor)
    for a, b in zip(w, w[1:]):
        assert b["from"] == pytest.approx(a["to"])


def test_waterfall_only_contains_count_affecting_stages(client):
    """Cook loss is uncertain and irrelevant; it must not appear here."""
    d = get(client, "/api/scientific", count=12, iterations=500)
    assert "cook_loss" not in {s["slug"] for s in d["waterfall"]}


def test_scientific_is_reproducible_for_a_fixed_seed(client):
    a = get(client, "/api/scientific", count=12, iterations=2000, seed=7)
    b = get(client, "/api/scientific", count=12, iterations=2000, seed=7)
    assert a["answer"]["required"] == b["answer"]["required"]


# ---------------------------------------------------------------------------
# variance decomposition
# ---------------------------------------------------------------------------

def test_variance_returns_a_share_per_mixing_input(client):
    d = get(client, "/api/variance", count=12, samples=128, bootstrap=10)
    assert d["output"] == "distinct"
    assert d["shares"]
    for s in d["shares"]:
        for k in ("slug", "label", "kind", "confidence", "first_order",
                  "total_order", "first_lo", "first_hi", "total_lo",
                  "total_hi", "degenerate", "inert"):
            assert k in s, k
    assert d["evaluations"] == 128 * (len(d["shares"]) + 2)
    assert d["notes"]


def test_variance_leads_with_a_spread_not_just_shares(client):
    """The panel's whole framing depends on these being present: shares of a
    vanishing variance are meaningless without the variance beside them."""
    d = get(client, "/api/variance", count=12, samples=128, bootstrap=0)
    assert d["sd"] >= 0.0
    assert d["sample_lo"] <= d["mean"] <= d["sample_hi"]


def test_variance_is_reproducible_for_a_fixed_seed(client):
    a = get(client, "/api/variance", count=12, samples=128, bootstrap=0, seed=7)
    b = get(client, "/api/variance", count=12, samples=128, bootstrap=0, seed=7)
    assert a["shares"] == b["shares"]


def test_variance_asks_an_aggregate_product_in_shares(client):
    """A gram of saffron is 150 flowers, so the cascade is asked in
    individual-shares. If this endpoint re-derived that for itself it would
    eventually disagree with the histogram rendered beside it."""
    d = get(client, "/api/variance", product="saffron_gram", count=12,
            samples=64, bootstrap=0)
    assert d["question"]["drawn_upi"] == 1.0
    assert d["question"]["drawn_units"] > 12


def test_variance_rejects_a_sample_count_it_cannot_estimate_from(client):
    r = client.get("/api/variance", params={"samples": 8})
    assert r.status_code == 422


def test_variance_404s_on_an_unknown_product(client):
    r = client.get("/api/variance", params={"product": "unicorn_wing"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# mixing curve
# ---------------------------------------------------------------------------

def test_mixing_curve_rises_from_floor_to_ceiling(client):
    d = get(client, "/api/mixing-curve", count=12)
    ys = [p["distinct"] for p in d["points"]]
    assert ys == sorted(ys)
    assert ys[0] == pytest.approx(d["floor"])
    assert ys[-1] < d["ceiling"]


def test_mixing_curve_never_leaves_its_bounds(client):
    d = get(client, "/api/mixing-curve", count=12)
    for p in d["points"]:
        assert d["floor"] - 1e-9 <= p["distinct"] <= d["ceiling"] + 1e-9


def test_mixing_curve_unknown_product_404s(client):
    r = client.get("/api/mixing-curve", params={"product": "not-a-product"})
    assert r.status_code == 404


@pytest.mark.parametrize("product,count", [
    ("whole_wing", 12),
    ("table_egg", 12),
    ("ground_beef_patty", 1),
    ("saffron_gram", 1),
    ("maple_syrup_gallon", 1),
])
def test_mixing_curve_covers_every_product(client, product, count):
    """Every product on the calculator's dropdown draws a real curve, not
    just the headline wing -- the mixing simulator used to be pinned to
    whole_wing regardless of which product was asked for.
    """
    d = get(client, "/api/mixing-curve", product=product, count=count)
    ys = [p["distinct"] for p in d["points"]]
    assert ys, f"{product} produced no curve points"
    # Non-decreasing up to floating-point noise: a patty's curve saturates
    # near its ~1,100 sub-unit ceiling, where the hypergeometric tail sits
    # close enough to 1 that successive points can differ in the last
    # couple of ULPs without the curve having actually turned over.
    assert all(b >= a - max(1e-6, abs(a) * 1e-8) for a, b in zip(ys, ys[1:]))
    # `d["floor"]` is the average-rate figure `run()` itself reports for this
    # product/window (recurring_floor's `expected`, not its `hard` bound), so
    # it is not a guaranteed lower bound on distinct for every recurring
    # product -- same-day eggs are the case in point, where a below-1
    # per-hen daily rate pushes the average floor above the dozen-egg
    # ceiling entirely (see test_eggs.py's own
    # test_commercial_same_day_dozen_is_exactly_twelve_hens for the sharper,
    # hard-floor version of this). What must hold for every product is the
    # ceiling: distinct can never exceed the units actually drawn.
    for p in d["points"]:
        assert p["distinct"] <= d["ceiling"] + max(1e-6, d["ceiling"] * 1e-8)
        # ... and can never exceed the pool itself: you cannot find more
        # distinct individuals in a batch than the batch contains. This is
        # the assertion that catches reaching for `expected_distinct` (the
        # wings-only two-per-individual special case) instead of
        # `expected_distinct_general` -- the special case reported ~1,100
        # distinct animals in a pool of 1 for a patty.
        assert p["distinct"] <= p["pool"] + max(1e-6, p["pool"] * 1e-8)


def test_mixing_curve_ground_beef_patty_reaches_the_batch_not_one_animal(
    client,
):
    """The regression this generalization must not reintroduce: a single
    patty's mixing curve should climb toward hundreds of distinct animals
    (the DNA-measured grind-batch pool), not flatten near 1 the way a wing
    -- or the old wing-only curve applied to a patty -- would.
    """
    d = get(client, "/api/mixing-curve", product="ground_beef_patty", count=1)
    assert d["ceiling"] > 100
    assert d["points"][-1]["distinct"] > 100


# ---------------------------------------------------------------------------
# reference data
# ---------------------------------------------------------------------------

def test_states_are_ranked_and_classified(client):
    d = get(client, "/api/states")
    sizes = [r["avg_size"] for r in d["regions"]]
    assert sizes == sorted(sizes, reverse=True)
    by_region = {r["region"]: r for r in d["regions"]}
    assert by_region["North Carolina"]["avg_size"] > \
        by_region["Ohio"]["avg_size"]


def test_states_default_year_has_rows(client):
    """Guards against the exact regression this replaced.

    `year` used to be a hardcoded 2025. The moment the corpus rolled past it,
    this endpoint would return 200 with `regions: []` and no explanation --
    silent, and only visible on `/api/states?year=2099`. Calling the endpoint
    with no `year` at all must resolve to the corpus's latest year and come
    back with real rows, not just a 200.
    """
    d = get(client, "/api/states")
    assert d["year"] is not None
    assert d["regions"], (
        f"the default year ({d['year']}) has no rows -- the endpoint is "
        "defaulting to a year the corpus does not have data for"
    )
    assert d["message"] is None


def test_states_names_the_empty_case_for_an_unloaded_year(client):
    d = get(client, "/api/states", year=2099)
    assert d["regions"] == []
    assert d["message"], "an empty result must say why, not just be empty"


def test_states_census_block_is_all_fifty_states(client):
    """The Census of Agriculture publishes every state -- the whole reason
    it exists in this project is to lift coverage past what the annual
    survey is allowed to report individually."""
    d = get(client, "/api/states")
    census = d["census"]
    assert census["census_year"] is not None
    assert len(census["regions"]) == 50
    for r in census["regions"]:
        assert r["region"]
        assert r["source"] == "nass-census-agriculture-2022"


def test_states_census_presence_only_is_exactly_the_gap(client):
    """presence_only must be true for exactly the states the requested
    year's survey has nothing to say about -- neither more (a state the
    survey DOES report, wrongly flagged) nor fewer (a census-only state
    silently reported as if it had a comparable figure)."""
    d = get(client, "/api/states")
    survey_regions = {r["region"] for r in d["regions"]}
    census = d["census"]["regions"]

    flagged = {r["region"] for r in census if r["presence_only"]}
    all_census = {r["region"] for r in census}
    assert flagged == all_census - survey_regions


def test_states_census_entries_carry_no_survey_figures(client):
    """Census rows must never be dressed up with the survey's vocabulary --
    sales_head is not head_slaughtered and must not leak into avg_size or
    volume, which is what the survey's rows carry instead."""
    d = get(client, "/api/states")
    for r in d["census"]["regions"]:
        assert "avg_size" not in r
        assert "volume" not in r


def test_trends_carry_the_full_series(client):
    d = get(client, "/api/trends")
    years = [r["year"] for r in d["husbandry"]]
    assert years == sorted(years)
    assert d["slaughter"] and d["dressing_yield"]


def test_facts_are_cited_and_ranked_by_surprise(client):
    d = get(client, "/api/facts", placement="learning", limit=10)
    assert d["facts"]
    surprises = [f["surprise"] for f in d["facts"]]
    assert surprises == sorted(surprises, reverse=True)
    for f in d["facts"]:
        assert f["source_title"] and f["publisher"]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def test_unknown_product_is_404(client):
    assert client.get("/api/calculate",
                      params={"product": "ostrich_wing"}).status_code == 404


def test_unknown_supply_chain_is_404(client):
    assert client.get("/api/calculate",
                      params={"chain": "teleportation"}).status_code == 404


def test_invalid_evidence_grade_is_422(client):
    r = client.get("/api/scientific", params={"min_confidence": "vibes"})
    assert r.status_code == 422


def test_output_min_confidence_pattern_is_anchored(client):
    """An unanchored alternation matches anywhere in the string, so
    'xxmeasuredxx' validated as if it were 'measured'."""
    r = client.get("/api/output/USA",
                    params={"min_confidence": "xxmeasuredxx"})
    assert r.status_code == 422


@pytest.mark.parametrize("limit", [-1, 0, 5000])
def test_facts_limit_is_bounded(client, limit):
    """SQLite reads a negative LIMIT as "no limit at all", so limit=-1 used
    to return the entire corpus rather than nothing."""
    assert client.get("/api/facts",
                      params={"limit": limit}).status_code == 422


@pytest.mark.parametrize("count", [0, -5, 999999999])
def test_footprint_count_is_bounded(client, count):
    """Unlike /api/calculate, count here had no `le`, so a huge count
    returned 200 with a footprint scaled to hundreds of millions of birds."""
    assert client.get("/api/footprint",
                      params={"count": count}).status_code == 422


def test_calculate_recurring_misconfiguration_is_a_4xx_not_a_500(
    client, monkeypatch,
):
    """dbm.make_recurring raising ValueError must not surface as a 500 --
    a malformed product row is a bad-request-shaped problem, not a server
    crash, and a 500 hides that distinction from whoever is looking at logs.
    """
    import counting_chicken_wings.db as dbm

    def boom(product, window_days=None):
        raise ValueError("product misconfigured for this test")

    monkeypatch.setattr(dbm, "make_recurring", boom)
    r = client.get("/api/calculate", params={"count": 12})
    assert r.status_code == 400


@pytest.mark.parametrize("count", [0, -5, 999999])
def test_out_of_range_counts_are_rejected(client, count):
    assert client.get("/api/calculate",
                      params={"count": count}).status_code == 422


@pytest.mark.parametrize("level", [0.0, 1.0, 1.5, -0.2])
def test_impossible_confidence_levels_are_rejected(client, level):
    r = client.get("/api/scientific", params={"confidence_level": level})
    assert r.status_code == 422


def test_iteration_cap_is_enforced(client):
    """An unbounded iteration count is a free denial-of-service."""
    assert client.get("/api/scientific",
                      params={"iterations": 10_000_000}).status_code == 422


# ---------------------------------------------------------------------------
# The country dimension
# ---------------------------------------------------------------------------

def test_countries_report_coverage_not_just_names(client):
    """A selector built from names alone would imply parity that is not there.

    The US has enumerated head slaughtered and a sourced loss chain; Israel has
    tonnage and districts. `answers` is what lets a caller say so.
    """
    data = get(client, "/api/countries")
    by = {c["iso3"]: c for c in data["countries"]}
    assert {"USA", "ISR"} <= set(by)

    assert by["USA"]["answers"]["head_slaughtered"] is True
    assert by["USA"]["answers"]["head_slaughtered_grade"] == "measured"

    # Israel answers the count question, but only on industry evidence: CBS
    # publishes no head figure, so the 260 million comes from a named trade
    # official via the press. Both facts have to be visible at once, which is
    # why the grade travels with the boolean.
    assert by["ISR"]["answers"]["head_slaughtered"] is True
    assert by["ISR"]["answers"]["head_slaughtered_grade"] == "industry"
    # ...and the government-only reading still cannot count birds.
    assert by["ISR"]["answers"]["head_slaughtered_measured"] is False
    assert by["USA"]["answers"]["head_slaughtered_measured"] is True

    assert by["ISR"]["answers"]["subnational"] is True
    assert by["ISR"]["native_mass_unit"] == "kg"

    # Per-capita is the comparison an audience asks for first, and it is the
    # one figure with no reachable citation. Absent, not guessed.
    assert all(c["answers"]["per_capita"] is False for c in data["countries"])


def test_output_endpoint_returns_native_units_unconverted(client):
    data = get(client, "/api/output/ISR")
    units = {r["unit"] for r in data["national"]}
    # 'growers' counts operations rather than mass, and is here because two
    # industry bodies corroborating each other is worth holding. It is still
    # not a US unit, which is what this test is actually guarding.
    assert units == {"tonnes", "ILS_million", "thousand_head", "growers"}
    assert data["country"]["native_currency"] == "ILS"
    assert every_row_cited(data["national"] + data["regional"])


def every_row_cited(rows):
    return all(r["source_slug"] for r in rows)


def test_suppressed_regions_are_flagged_rather_than_zeroed(client):
    """A withheld figure read as zero is a wrong answer that looks like data."""
    data = get(client, "/api/output/ISR")
    assert data["suppressed_regions"] > 0
    for r in data["regional"]:
        if r["suppressed"]:
            assert r["value"] is None


def test_unknown_country_is_a_404_not_an_empty_answer(client):
    assert client.get("/api/output/XXX").status_code == 404


def test_country_codes_are_case_insensitive(client):
    assert client.get("/api/output/isr").status_code == 200


# ---------------------------------------------------------------------------
# The ceiling the API reports
# ---------------------------------------------------------------------------

def test_api_ceiling_is_not_the_unit_count_for_a_continuous_product(client):
    """`ceiling` used to be the request's unit count, which is correct only
    while every product is countable. A gram of saffron is not one flower, so
    the endpoint returned ceiling=1 beside floor=150 -- the contradiction the
    CLI had already been fixed for. The field exists on Result so both surfaces
    read the same number; this test is here because one of them did not."""
    a = get(client, "/api/calculate", count=1, product="saffron_gram")["answer"]
    assert a["floor"] == pytest.approx(150, rel=1e-6)
    assert a["ceiling"] == pytest.approx(150, rel=1e-6)
    assert a["distinct"] >= a["floor"] - 1e-6


@pytest.mark.parametrize("product,count,expected", [
    ("whole_wing", 12, 12),        # a wing belongs to exactly one bird
    ("saffron_stigma", 12, 12),    # so does a stigma
    ("table_egg", 12, 12),         # and an egg to one hen
])
def test_api_ceiling_is_still_the_unit_count_for_discrete_products(
        client, product, count, expected):
    """The fix must not reach the products that were already right."""
    a = get(client, "/api/calculate", count=count, product=product)["answer"]
    assert a["ceiling"] == pytest.approx(expected)


def test_cli_and_api_agree_on_the_ceiling():
    """They read the same field. Asserted rather than assumed, since the whole
    point of putting it on Result was that they could not drift."""
    from counting_chicken_wings import db as dbm
    from counting_chicken_wings.model import run

    conn = dbm.connect()
    prod = dbm.get_product(conn, "saffron_gram")
    res = run(1, prod["units_per_individual_mode"], [],
              dbm.load_mixing_stages(conn, "commodity_spice"),
              aggregate_units=True)
    with TestClient(app) as c:
        a = c.get("/api/calculate",
                  params={"count": 1, "product": "saffron_gram"}).json()["answer"]
    assert a["ceiling"] == pytest.approx(res.distinct_ceiling)


def test_min_confidence_offers_the_government_only_reading(client):
    """Both pictures of Israel must be reachable, not one chosen for the reader.

    Without the filter, Israel answers "how many chickens" on a trade-press
    figure. With min_confidence=measured, it answers scale and admits it cannot
    count birds -- and says which row it dropped to get there.
    """
    everything = get(client, "/api/output/ISR")
    gov = get(client, "/api/output/ISR", min_confidence="measured")

    head = [r for r in everything["national"]
            if r["measure"] == "head_slaughtered"]
    assert head and head[0]["confidence"] == "industry"
    assert not [r for r in gov["national"] if r["measure"] == "head_slaughtered"]

    # A filtered answer that does not say what it filtered is just a different
    # number, so every dropped row is named -- the head count and the two
    # industry figures that corroborate it.
    dropped = {e["measure"] for e in gov["excluded"]}
    assert dropped == {"head_slaughtered", "chicks_placed", "grower_count"}
    assert {e["source"] for e in gov["excluded"]} == {
        "toi-poultry-imports-2025", "ofot-sector-summary-2021"}
    assert everything["excluded"] == []


def test_derived_weight_is_the_cross_check_and_drops_with_its_parent(client):
    """~2.3 kg a bird is what makes the industry figure believable.

    It is derived from an industry figure, so it is industry-grade and must
    disappear from a government-only view along with its parent.
    """
    everything = get(client, "/api/output/ISR")
    w = everything["derived_weight"]
    assert len(w) == 1
    assert 2.0 < w[0]["kg_per_head"] < 2.7
    assert w[0]["confidence"] == "industry"
    # The years do not line up and the payload says so rather than implying a
    # same-year measurement.
    assert w[0]["year_gap"] == 1

    gov = get(client, "/api/output/ISR", min_confidence="measured")
    assert gov["derived_weight"] == []


def test_unknown_confidence_level_is_rejected(client):
    assert client.get("/api/output/ISR",
                      params={"min_confidence": "vibes"}).status_code == 422


# ---------------------------------------------------------------------------
# Supply chains carry their species
# ---------------------------------------------------------------------------

def test_meta_chains_carry_their_species(client):
    """`is_default` is per-species by design, so three species means three rows
    flagged default. A caller that renders them flat and marks every default
    `selected` gets whichever sorts last -- which is how the wing calculator
    ended up opening on "Commodity spice trade" once saffron landed. Filtering
    is only possible if the species travels with the chain."""
    chains = get(client, "/api/meta")["chains"]
    assert chains
    for c in chains:
        assert "species_slug" in c

    defaults = [c for c in chains if c["is_default"]]
    # One default per species, not one globally.
    assert len(defaults) == len({c["species_slug"] for c in defaults})
    assert len(defaults) > 1, "the collision only exists with several species"


def test_every_product_has_at_least_one_chain_of_its_own_species(client):
    """default_supply_chain raises rather than falling back across species, so
    a product whose species has no chain is a 500 waiting to happen."""
    meta = get(client, "/api/meta")
    by_species = {}
    for c in meta["chains"]:
        by_species.setdefault(c["species_slug"], []).append(c["slug"])
    for p in meta["products"]:
        if not p["active"]:
            continue
        assert "species_slug" in p
        assert by_species.get(p["species_slug"]), (
            f"{p['slug']} has no supply chain for species {p['species_slug']}")


def test_saffron_chains_are_not_offered_for_wings(client):
    """The regression, stated as data rather than as a UI assertion."""
    chains = get(client, "/api/meta")["chains"]
    wing_chains = [c["slug"] for c in chains if c["species_slug"] == "broiler"]
    assert "commodity_spice" not in wing_chains
    assert "garden_saffron" not in wing_chains
    assert "commodity_foodservice" in wing_chains


# ---------------------------------------------------------------------------
# Quality axes
#
# "Is a fatter chicken a better chicken?" is a broiler question. These tests
# exist because the previous version answered it for every species by
# hardcoding the broiler verdict in the handler, where no YAML edit could
# reach it.
# ---------------------------------------------------------------------------


def test_every_axis_names_its_own_question_and_x_axis(client):
    """Of the species that HAVE an axis. The rest are checked below.

    This endpoint returns every active species since the picker has to offer
    every one of them, so the uniqueness check has to run over the answered
    ones -- three unasked questions are three nulls, not three collisions.
    """
    axes = [a for a in get(client, "/api/quality-axes")["axes"]
            if a["has_axis"]]
    assert len(axes) >= 2
    questions = {a["question"] for a in axes}
    assert len(questions) == len(axes), "two species share a question"
    for a in axes:
        assert a["x_label"], a["slug"]
        assert a["x_kind"] in ("continuous", "classes")


def test_the_picker_offers_every_active_species(client):
    """Three of six species used to be missing from "Does size matter?".

    They had no `quality_axis` row, the endpoint inner-joined it, and they
    dropped out of the payload entirely -- so the view claiming to grade
    "every species" showed three chips and said nothing about the other three.
    An absent answer is a finding about the corpus; an absent chip is a lie
    about it.
    """
    from counting_chicken_wings import db as dbm

    conn = dbm.connect()
    try:
        active = {r["slug"] for r in conn.execute(
            "SELECT slug FROM species WHERE active = 1")}
    finally:
        conn.close()

    axes = {a["slug"]: a for a in get(client, "/api/quality-axes")["axes"]}
    assert set(axes) == active

    unasked = [a for a in axes.values() if not a["has_axis"]]
    assert unasked, "fixture assumption: some species has no size question yet"
    for a in unasked:
        # Nothing borrowed from the species next to it in the list.
        assert a["question"] is None and a["x_label"] is None
        assert a["x_kind"] is None
        assert a["axis_rows"] == 0 and a["has_figures"] is False


def test_a_species_with_no_size_question_says_so_in_the_404(client):
    """A 404 the client can render, rather than one it can only report.

    There is genuinely no size question to serve, so this stays an error --
    but the picker's reason for omitting these species entirely was that the
    error carried nothing to act on. `detail` is an object now: a machine-
    readable code, a sentence built from the corpus' own name for the species,
    and the species itself so the view can label the gap without typing a
    species name into the page.
    """
    r = client.get("/api/bird-size", params={"species": "silkworm"})
    assert r.status_code == 404
    d = r.json()["detail"]
    assert d["error"] == "no_size_question"
    assert d["message"], "nothing for the page to print"
    for key in ("slug", "common_name", "individual_noun", "individual_plural"):
        assert d["species"][key], f"species missing {key}"
    assert d["species"]["slug"] == "silkworm"


def test_the_two_404s_are_told_apart(client):
    """An unknown slug is a bug; an unasked question is a fact about the corpus.

    Spelled the same way, a client can only treat both as failure -- which is
    exactly what made three of six species disappear from the picker.
    """
    unknown = client.get("/api/bird-size", params={"species": "nope"})
    unasked = client.get("/api/bird-size", params={"species": "sugar_maple"})
    assert unknown.status_code == unasked.status_code == 404
    assert unknown.json()["detail"]["error"] == "unknown_species"
    assert unasked.json()["detail"]["error"] == "no_size_question"
    # Only the renderable one carries a species to render.
    assert "species" not in unknown.json()["detail"]


def test_a_graded_species_does_not_borrow_weight_bands(client):
    """A laying hen has production_program rows, and they are flock sizes.

    Counting them as the egg-size axis would put "hens per house" behind
    the question "is a bigger egg a better egg?" -- a real bug that the
    first draft of this endpoint had.
    """
    axes = {a["slug"]: a for a in get(client, "/api/quality-axes")["axes"]}
    hen = axes["layer_hen"]
    assert hen["x_kind"] == "classes"
    assert hen["programs"] > 0, "fixture assumption: hens have programs"
    assert hen["axis_rows"] == hen["grades"]
    assert hen["axis_rows"] != hen["programs"]

    d = get(client, "/api/bird-size", species="layer_hen")
    units = {b.get("size_unit") for b in d["axis_bands"]}
    assert "hens per house" not in units


def test_unanswered_verdict_legs_stay_null(client):
    """An open question must not default to a settled-looking answer."""
    d = get(client, "/api/bird-size", species="turkey")
    assert d["verdict"]["yield_per_individual"] is None
    assert d["verdict"]["quality"] is None
    # Anatomy carries even where evidence does not: a turkey has two wings.
    assert d["verdict"]["count_floor"] == "unchanged"
    assert d["has_figures"] is False


def test_regional_weights_are_broiler_only(client):
    """v_broiler_size_stat is broilers; no other species may inherit it."""
    assert get(client, "/api/bird-size", species="broiler")["regions"]
    for s in ("layer_hen", "turkey", "saffron_crocus"):
        assert get(client, "/api/bird-size", species=s)["regions"] == []


def test_broiler_verdict_comes_from_data_not_code(client):
    d = get(client, "/api/bird-size", species="broiler")
    assert d["verdict"]["yield_per_individual"] == "better"
    assert d["verdict"]["quality"] == "worse"
    assert d["verdict"]["count_floor"] == "unchanged"
    assert "two wings" in d["verdict"]["summary"]


def test_unknown_species_is_404_not_an_empty_page(client):
    assert client.get("/api/bird-size", params={"species": "nope"}) \
        .status_code == 404


# ---------------------------------------------------------------------------
# Floor prose comes from the chain, in every client
#
# supply_chain.floor_note exists because this text was hardcoded as wing prose
# in the CLI and the HTML. The CLI was fixed; the web page kept its own copy
# and went on telling egg users about a cut-up line. These pin the contract
# the page depends on.
# ---------------------------------------------------------------------------


def test_calculate_returns_the_chains_own_floor_note(client):
    d = get(client, "/api/calculate", count=12, product="whole_wing",
            chain="commodity_foodservice")
    assert d["floor_note"], "no floor_note for a chain that has one"
    assert "cut-up line" in d["floor_note"]


def test_egg_floor_note_never_narrates_wing_machinery(client):
    """The exact regression: eggs walked through a wing supply chain.

    Naming wings is fine and the egg note does it deliberately -- "unlike
    wings, where mixing pushes the answer up from the floor" is a contrast
    that earns its place. What must never appear is egg prose describing
    equipment no egg passes through.
    """
    for chain in ("commercial_carton", "backyard_eggs", "farmers_market"):
        d = get(client, "/api/calculate", count=12, product="table_egg",
                chain=chain, window_days=1)
        note = (d["floor_note"] or "").lower()
        assert note, f"{chain} has no floor_note"
        for machinery in ("cut-up line", "fryer", "deboning", "chiller",
                          "wings leave the bird", "two wings drop"):
            assert machinery not in note, \
                f"{chain} floor_note narrates {machinery!r} to an egg query"


def test_every_supply_chain_has_a_floor_note(client):
    """A chain without one silently drops the explanation from the page."""
    chains = get(client, "/api/meta")["chains"]
    missing = []
    for c in chains:
        product = "table_egg" if c["slug"] in (
            "commercial_carton", "backyard_eggs", "farmers_market") \
            else "whole_wing"
        r = client.get("/api/calculate", params={
            "count": 12, "product": product, "chain": c["slug"]})
        if r.status_code != 200:
            continue          # chain belongs to another species' product
        if not r.json().get("floor_note"):
            missing.append(c["slug"])
    assert not missing, f"supply chains with no floor_note: {missing}"


# ---------------------------------------------------------------------------
# /api/version identifies the deploy, wherever it runs
# ---------------------------------------------------------------------------

def test_version_reads_a_host_neutral_commit_variable(client, monkeypatch):
    """It used to read only RENDER_GIT_COMMIT. Moving to a self-hosted box
    made that nobody's job to set, so the endpoint answered `null` to the one
    question it exists to answer."""
    monkeypatch.setenv("GIT_COMMIT", "a" * 40)
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    d = get(client, "/api/version")
    assert d["git_commit"] == "a" * 40
    assert d["git_commit_short"] == "aaaaaaa"


def test_version_still_honours_the_render_variable(client, monkeypatch):
    """The Dockerfile is deliberately provider-agnostic, so Render stays
    supported rather than being cut off."""
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "b" * 40)
    assert get(client, "/api/version")["git_commit"] == "b" * 40


def test_the_host_neutral_variable_wins(client, monkeypatch):
    monkeypatch.setenv("GIT_COMMIT", "c" * 40)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "d" * 40)
    assert get(client, "/api/version")["git_commit"] == "c" * 40


# ---------------------------------------------------------------------------
# The footprint belongs to a species, and most products do not have one
# ---------------------------------------------------------------------------
#
# `/api/footprint` hardcoded three figures: a mass share of 0.073 for whole
# wings and 0.23 -- the chicken BREAST share -- for all eleven other products,
# a 6.62 lb fallback live weight, and grower pay computed unconditionally. A
# gallon of maple syrup was narrated as 51.50 birds and $14.32 of broiler
# grower pay; a silk dress as 22,200 birds and $6,172.49.


NON_BROILER = ["table_egg", "maple_syrup_gallon", "silk_dress",
               "silk_pound_raw", "saffron_gram", "ground_beef_patty"]


@pytest.mark.parametrize("product", NON_BROILER)
def test_a_non_broiler_product_gets_no_broiler_footprint(client, product):
    """The flagship regression: 0.23 was the breast share of a chicken."""
    d = get(client, "/api/footprint", count=12, product=product)
    assert d["metrics"] == [], f"{product} was handed a broiler's footprint"
    assert d["mass_share"] is None
    assert d["coverage"]["footprint"] is False


@pytest.mark.parametrize("product", NON_BROILER)
def test_nothing_but_a_broiler_is_paid_a_broiler_grower_fee(client, product):
    """ERS broiler grower fees, at a 6.62 lb bird, for a silk dress.

    Three things have to be true before this figure exists: a grower fee in
    the product's domain, a slaughter live weight for its species, and a mass
    share to allocate by. Each of the three was previously assumed.
    """
    d = get(client, "/api/footprint", count=12, product=product)
    assert d["grower_pay"] is None
    assert d["coverage"]["grower_pay"] is False


@pytest.mark.parametrize("product", NON_BROILER)
def test_the_allocation_note_never_narrates_another_species(client, product):
    """"the rest of the bird was eaten by someone else" -- of a silk dress."""
    note = get(client, "/api/footprint", count=12,
               product=product)["allocation_note"].lower()
    assert note
    for phrase in ("the rest of the bird", "sell at a premium per pound"):
        assert phrase not in note, f"{product}: {note}"


def test_the_wing_footprint_still_answers_in_full(client):
    """The guard must not be so eager it empties the product it was built for.

    0.073 is the top of the 6.7-7.3% live-weight band in the eight-strain
    yield paper, and it now comes from `product_mass_share` rather than from
    a literal in api.py.
    """
    d = get(client, "/api/footprint", count=12, product="whole_wing")
    assert d["mass_share"] == pytest.approx(0.073)
    assert d["mass_share_basis"] == "live_weight"
    assert d["mass_share_source"]["slug"] == "wing-yield-eight-strains"
    assert all(v for v in d["coverage"].values())
    assert d["individuals"] == pytest.approx(6.0)
    for m in d["metrics"]:
        if m["per_individual"]:
            assert m["allocated_total"] == pytest.approx(
                m["naive_total"] * 0.073)


def test_boneless_wings_carry_the_breast_share_not_the_wing_one(client):
    d = get(client, "/api/footprint", count=12, product="boneless_wing")
    assert d["mass_share"] == pytest.approx(0.23)
    assert d["mass_share_source"]["slug"] == "tyson-foodservice-boneless"


def test_every_mass_share_is_cited(client):
    """The point of moving it into the corpus. A hardcoded multiplier is
    invisible to audit.py, which is why ten wrong ones went unnoticed."""
    from counting_chicken_wings import db as dbm

    conn = dbm.connect()
    try:
        rows = conn.execute(
            "SELECT product_id, source_id FROM product_mass_share").fetchall()
    finally:
        conn.close()
    assert rows, "no mass shares in the corpus at all"
    assert all(r["source_id"] for r in rows)


def test_footprint_speaks_the_species_own_noun(client):
    """"birds" was written into the page's headings, so a correct egg answer
    still read as poultry. The noun comes from the corpus now."""
    d = get(client, "/api/footprint", count=12, product="maple_syrup_gallon")
    assert d["individual_noun"] == "tree"
    assert d["individual_plural"] == "trees"


def test_no_commit_anywhere_reads_as_unknown_not_as_a_lie(client, monkeypatch):
    """Absent both, None is the honest answer: nobody told this process what
    it is, so it is almost certainly local."""
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    d = get(client, "/api/version")
    assert d["git_commit"] is None
    assert d["git_commit_short"] is None


# ---------------------------------------------------------------------------
# A route belongs to a species, and both endpoints have to know it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/api/calculate", "/api/scientific"])
def test_a_nonexistent_chain_is_refused(client, path):
    """`/api/scientific?chain=total_nonsense` returned 200 and `distinct: 6.0`.

    Six is the floor -- no mixing stages were found, so none were applied, and
    the answer came back looking like a result. A wrong number that looks like
    a result is the worst failure this project has, because nothing about it
    invites a second look.
    """
    r = client.get(path, params={"chain": "total_nonsense"})
    assert r.status_code == 404, r.text


@pytest.mark.parametrize("path", ["/api/calculate", "/api/scientific"])
def test_another_species_route_is_refused(client, path):
    """A wing question walked through a maple sugarhouse, confidently.

    `is_default` is per-species, so the Scientific tab's flat chain list left
    `commodity_syrup` selected for a chicken-wing question and every foreign
    route on offer beside it. Filtering the dropdown is half the fix; the
    other half is that the endpoint must not accept the combination however it
    arrives -- a URL, a bookmark, a stale tab.
    """
    r = client.get(path, params={"product": "whole_wing",
                                 "chain": "commodity_syrup"})
    assert r.status_code == 422, r.text
    assert "syrup" in r.text


@pytest.mark.parametrize("path", ["/api/calculate", "/api/scientific"])
def test_a_products_own_route_is_accepted(client, path):
    """The guard must not be so eager it refuses the ordinary case."""
    for product, chain in (("whole_wing", "commodity_foodservice"),
                           ("table_egg", "commercial_carton"),
                           ("maple_syrup_gallon", "commodity_syrup")):
        r = client.get(path, params={"product": product, "chain": chain})
        assert r.status_code == 200, f"{product}/{chain}: {r.text[:200]}"


def test_both_endpoints_default_to_the_same_route(client):
    """The calculator and Scientific disagreed about the default for one
    question, which is not a difference of opinion two views may hold."""
    a = get(client, "/api/calculate", product="whole_wing")
    b = get(client, "/api/scientific", product="whole_wing", iterations=100)
    assert a["question"]["chain"] == b["question"]["chain"]


# ---------------------------------------------------------------------------
# Scope: which species a view is actually about
#
# The page offers twelve products across six species in one dropdown, and
# eight of its eleven views answer for exactly one species. Picking "Silk
# dress" and opening Trends showed broiler chickens with nothing marking them
# as unrelated -- the DATA was already honest (nutrition returns an empty list
# rather than borrowing chicken figures), so the gap was entirely in framing.
#
# These pin the one property that keeps the fix from rotting: a scope is read
# off the rows the endpoint returned, never asserted. The day /api/trends
# carries a second species its scope says two, with nobody remembering to
# update a sentence.
# ---------------------------------------------------------------------------

SCOPED = ["/api/states", "/api/trends", "/api/seasonality", "/api/facts",
          "/api/countries"]


@pytest.mark.parametrize("path", SCOPED)
def test_a_scoped_view_says_what_it_is_scoped_to(client, path):
    d = get(client, path)
    scope = d["scope"]
    assert scope["species"], f"{path} reports no species"
    assert scope["label"], f"{path} has nothing to print"
    for sp in scope["species"]:
        # Enough to compare against a selected product AND to name in prose.
        for key in ("slug", "common_name", "individual_noun",
                    "individual_plural"):
            assert sp[key], f"{path}: species missing {key}"


@pytest.mark.parametrize("path", SCOPED)
def test_a_scope_names_only_species_the_corpus_has(client, path):
    """A scope is a claim about the corpus and has to be checkable against it."""
    from counting_chicken_wings import db as dbm

    conn = dbm.connect()
    try:
        known = {r["slug"]: r["common_name"] for r in conn.execute(
            "SELECT slug, common_name FROM species")}
    finally:
        conn.close()

    for sp in get(client, path)["scope"]["species"]:
        assert sp["slug"] in known
        assert sp["common_name"] == known[sp["slug"]]


def test_the_state_scope_matches_the_rows_the_state_view_draws(client):
    """Read off the same view the endpoint charts, not written beside it."""
    from counting_chicken_wings import db as dbm

    d = get(client, "/api/states")
    conn = dbm.connect()
    try:
        drawn = {r["slug"] for r in conn.execute(
            """SELECT DISTINCT sp.slug FROM v_broiler_size_stat r
               JOIN species sp ON sp.id = r.species_id
               WHERE r.year = ? AND r.month IS NULL""", (d["year"],))}
    finally:
        conn.close()
    assert {s["slug"] for s in d["scope"]["species"]} == drawn


def test_the_fact_deck_is_scoped_by_domain_not_by_species(client):
    """Facts hang off a domain, so the domain's label is the truer name.

    Its species list still comes back, because that is what a caller compares
    a selected product against -- but printing "Broiler chicken and Laying
    hen" over a poultry deck would be narrower than the deck actually is.
    """
    from counting_chicken_wings import db as dbm

    scope = get(client, "/api/facts")["scope"]
    conn = dbm.connect()
    try:
        labels = {r["label"] for r in conn.execute("SELECT label FROM domain")}
    finally:
        conn.close()
    assert scope["label"] in labels
    assert len(scope["species"]) >= 1


# ---------------------------------------------------------------------------
# The anchor is computed, never named
# ---------------------------------------------------------------------------


def test_scope_reports_every_active_species(client):
    from counting_chicken_wings import db as dbm

    conn = dbm.connect()
    try:
        active = {r["slug"] for r in conn.execute(
            "SELECT slug FROM species WHERE active = 1")}
    finally:
        conn.close()
    assert {s["slug"] for s in get(client, "/api/scope")["species"]} == active


def test_the_anchor_is_the_deepest_species_in_the_corpus(client):
    """Derived from v_species_coverage, so it follows the data.

    Written into the page instead, this claim would have been true the day it
    was typed and wrong the day a second species filled in -- the same rot
    that put "Israel cannot answer how many chickens" on the page once.
    """
    d = get(client, "/api/scope")
    depths = sorted((s["depth"] for s in d["species"]), reverse=True)
    assert d["anchor"] is not None, "fixture assumption: one species is deepest"
    assert d["anchor"]["depth"] == depths[0]
    assert depths[0] > depths[1], "no strict anchor, so none should be claimed"
    # And it is a real row, not a synthesised one.
    assert d["anchor"] in d["species"]


def test_scope_labels_every_dimension_the_view_carries(client):
    """A column added to v_species_coverage with no label is a silent gap.

    The view is the source of truth for WHICH dimensions exist; api.py only
    names them. A new column would otherwise reach the page as its own raw
    identifier.
    """
    from counting_chicken_wings.api import _DIMENSION_LABELS

    for dim in get(client, "/api/scope")["dimensions"]:
        assert dim["key"] in _DIMENSION_LABELS, \
            f"v_species_coverage.{dim['key']} has no English label"
        assert dim["label"] == _DIMENSION_LABELS[dim["key"]]
        assert isinstance(dim["species"], list)


def test_a_tie_for_deepest_claims_no_anchor(client, tmp_path, monkeypatch):
    """The property that lets the claim retire itself.

    Two species at the same depth is not an anchor, and a tie-break would
    invent one -- so the endpoint returns null and the page prints nothing.
    Exercised against a stand-in view, because the real corpus has a clear
    winner and this is exactly the case that will not stay reproducible.
    """
    import sqlite3

    from counting_chicken_wings import api as apimod

    db = tmp_path / "tie.db"
    con = sqlite3.connect(db)
    con.executescript(
        """CREATE TABLE v_species_coverage (
             id INTEGER, slug TEXT, common_name TEXT, individual_noun TEXT,
             individual_plural TEXT, domain TEXT, loss_chain INT, products INT);
           INSERT INTO v_species_coverage VALUES
             (1,'a','A','a','as','d',1,1),
             (2,'b','B','b','bs','d',1,1);"""
    )
    con.commit()
    con.close()

    def fake_connect():
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(apimod.dbm, "connect", fake_connect)
    d = apimod.scope()
    assert d["anchor"] is None
    assert [s["depth"] for s in d["species"]] == [2, 2]


# ---------------------------------------------------------------------------
# The refusal sentence belongs to the API, not to the page
#
# #110's constraint: scope copy is either app copy or comes from the API. The
# second is the better one -- every noun is the corpus' own, so renaming a
# species renames the sentence, and test_static.py can go on forbidding any
# species name in the shipped page.
# ---------------------------------------------------------------------------


def test_scope_composes_a_refusal_for_every_species_the_product_is_not(client):
    from counting_chicken_wings import db as dbm

    conn = dbm.connect()
    try:
        active = {r["slug"] for r in conn.execute(
            "SELECT slug FROM species WHERE active = 1")}
    finally:
        conn.close()

    d = get(client, "/api/scope", product="silk_dress")
    sel = d["selected"]
    assert sel["slug"] == "silk_dress"
    assert sel["label"] and sel["common_name"]

    # One per species this product does NOT belong to, and none for its own --
    # a view scoped to a product's own species is not a mismatch.
    assert set(sel["borrow_notes"]) == active - {sel["species"]}
    for slug, note in sel["borrow_notes"].items():
        assert sel["label"] in note, f"{slug}: does not name the product"
        assert note.endswith("to borrow."), \
            f"{slug}: drops the pattern the footprint note established"


def test_the_refusal_names_the_species_the_view_is_showing(client):
    """Keyed by scope species, because the sentence differs per view."""
    notes = get(client, "/api/scope",
                product="maple_syrup_gallon")["selected"]["borrow_notes"]
    assert "Broiler chicken" in notes["broiler"]
    assert "Laying hen" in notes["layer_hen"]
    assert notes["broiler"] != notes["layer_hen"]


def test_scope_without_a_product_says_nothing_about_one(client):
    """The parameter is optional and the anchor answer must not depend on it."""
    assert get(client, "/api/scope")["selected"] is None


def test_an_unknown_product_is_404_not_a_silent_null(client):
    r = client.get("/api/scope", params={"product": "nope"})
    assert r.status_code == 404
