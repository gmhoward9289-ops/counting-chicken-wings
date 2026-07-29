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
    "/api/states", "/api/trends", "/api/facts", "/api/sources",
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
# mixing curve
# ---------------------------------------------------------------------------

def test_mixing_curve_rises_from_floor_to_ceiling(client):
    d = get(client, "/api/mixing-curve", draw=12)
    ys = [p["distinct"] for p in d["points"]]
    assert ys == sorted(ys)
    assert ys[0] == pytest.approx(d["floor"])
    assert ys[-1] < d["ceiling"]


def test_mixing_curve_never_leaves_its_bounds(client):
    d = get(client, "/api/mixing-curve", draw=12)
    for p in d["points"]:
        assert d["floor"] - 1e-9 <= p["distinct"] <= d["ceiling"] + 1e-9


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


def test_state_trend_returns_twelve_months(client):
    d = get(client, "/api/state-trend/Ohio")
    assert d["months"] == list(range(1, 13))
    assert len(d["values"]) == 12


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


def test_unknown_region_is_404(client):
    assert client.get("/api/state-trend/Atlantis").status_code == 404


def test_invalid_evidence_grade_is_422(client):
    r = client.get("/api/scientific", params={"min_confidence": "vibes"})
    assert r.status_code == 422


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
