"""The A/B harness: assignment, stickiness, collection, and aggregation.

These test the properties that make a measurement trustworthy rather than
the plumbing. An experiment that reassigns a visitor on reload, or that lets
a client name its own arm, produces numbers that look fine and mean nothing.
"""

import json

import pytest
from fastapi.testclient import TestClient

from counting_chicken_wings import experiment as exp
from counting_chicken_wings import metrics
from counting_chicken_wings.api import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Every test gets its own metrics database.

    Not the developer's, and never `chickens.db`.
    """
    db = tmp_path / "metrics.db"
    monkeypatch.setenv("WINGS_METRICS_DB", str(db))
    return db


@pytest.fixture
def split_50(monkeypatch):
    monkeypatch.setenv("WINGS_AB_SPLIT", "50")


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------


def test_the_split_defaults_to_everyone_on_the_control(monkeypatch):
    """Deploying the branch must not silently start serving a second site."""
    monkeypatch.delenv("WINGS_AB_SPLIT", raising=False)
    assert exp.split_percent() == 0
    assert all(exp.bucket(exp.new_session_id()) == "a" for _ in range(50))


def test_a_visitor_keeps_the_same_variant_across_reloads(client, split_50):
    """The whole experiment rests on this.

    A page that changes under the person being measured measures nothing.
    """
    # The client's own cookie jar, so this is what a browser actually does.
    first = client.get("/")
    assigned = first.cookies[exp.UI_COOKIE]
    marker = 'data-variant="b"' in first.text
    assert (assigned == "b") == marker, "cookie and page disagree"

    for _ in range(5):
        again = client.get("/")
        assert client.cookies[exp.UI_COOKIE] == assigned
        assert ('data-variant="b"' in again.text) == marker


def test_bucketing_is_deterministic_for_an_id(split_50):
    sid = exp.new_session_id()
    assert len({exp.bucket(sid) for _ in range(20)}) == 1


def test_a_fifty_percent_split_actually_splits(split_50):
    """A hash that clumps is not a split. Loose bounds; this is a smoke test."""
    ids = [exp.new_session_id() for _ in range(2000)]
    b = sum(exp.bucket(i) == "b" for i in ids)
    assert 800 < b < 1200, f"{b}/2000 to b -- assignment is not balanced"


def test_the_ui_parameter_forces_a_variant_and_pins_it(client):
    r = client.get("/?ui=b")
    assert r.cookies[exp.UI_COOKIE] == "b"
    assert 'data-variant="b"' in r.text

    r = client.get("/?ui=a")
    assert r.cookies[exp.UI_COOKIE] == "a"
    assert 'data-variant="b"' not in r.text


def test_an_unknown_variant_falls_back_to_the_control(client):
    r = client.get("/?ui=nonsense")
    assert r.status_code == 200
    assert r.cookies[exp.UI_COOKIE] == exp.CONTROL


def test_a_missing_variant_file_does_not_take_the_site_down(monkeypatch):
    """The redesign must be deletable, and must be safe to not exist yet."""
    monkeypatch.setitem(exp.VARIANTS, "b", "does-not-exist.html")
    assert exp.path_for("b").name == "index.html"


def test_the_response_varies_on_cookie(client, split_50):
    """Two pages behind one URL. Without this a cache serves the wrong arm."""
    r = client.get("/")
    assert "cookie" in r.headers.get("vary", "").lower()


def test_experiment_state_explains_the_assignment(client, split_50):
    r = client.get("/api/experiment")
    body = r.json()
    assert body["variant"] in exp.VARIANTS
    assert body["split_percent_to_b"] == 50
    assert body["reason"]
    # The id itself is never handed back out.
    assert "session_id" not in body
    assert exp.SID_COOKIE not in json.dumps(body)


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def test_events_are_recorded_against_the_cookie_variant(client, store):
    client.get("/?ui=b")
    r = client.post("/api/metrics", json={"events": [
        {"name": "pageview", "value": 812, "meta": {"w": 390}},
        {"name": "view", "meta": {"view": "season"}},
    ]})
    assert r.json()["accepted"] == 2
    assert metrics.summary()["variants"]["b"]["sessions"] == 1


def test_a_late_beacon_is_credited_to_the_page_that_sent_it(client, store):
    """The regression that made the body authoritative over the cookie.

    `dwell` is sent by `sendBeacon` during unload, so on a variant switch it
    lands *after* the next page's cookie is set. Deriving the variant from
    the cookie at POST time recorded variant b's 32 seconds against variant
    a -- silently, and on the one event the comparison most depends on.
    """
    client.get("/?ui=b")
    client.get("/?ui=a")          # cookie is now `a`; the beacon is still b's
    client.post("/api/metrics", json={
        "variant": "b", "events": [{"name": "dwell", "value": 31824}]})

    v = metrics.summary()["variants"]
    assert v["b"]["dwell_ms"]["p50"] == 31824, "dwell lost from its own arm"
    assert v.get("a", {}).get("dwell_ms", {}).get("n", 0) == 0, \
        "dwell was credited to the wrong variant"


def test_a_body_naming_an_unknown_variant_falls_back_to_the_cookie(
        client, store):
    """The body is trusted only to name one of the arms that exist."""
    client.get("/?ui=a")
    client.post("/api/metrics", json={
        "variant": "../../etc/passwd",
        "events": [{"name": "pageview", "value": 1}]})
    v = metrics.summary()["variants"]
    assert set(v) == {"a"}


def test_a_session_id_cannot_be_chosen_by_the_client(client, store):
    """Session still comes from the cookie: it is what bounds a rate."""
    client.get("/?ui=a")
    real = client.cookies[exp.SID_COOKIE]
    client.post("/api/metrics", json={
        "session": "f" * 32, "events": [{"name": "pageview", "value": 1}]})
    conn = metrics.connect()
    try:
        got = {r[0] for r in conn.execute("SELECT session FROM event")}
    finally:
        conn.close()
    assert got == {real}


def test_unknown_event_names_are_dropped(client, store):
    client.get("/?ui=a")
    r = client.post("/api/metrics", json={"events": [
        {"name": "pageview", "value": 100},
        {"name": "rm -rf", "value": 1},
        {"name": "purchase", "value": 999},
    ]})
    assert r.json()["accepted"] == 1


def test_collection_without_cookies_is_a_no_op(client, store):
    r = client.post("/api/metrics", json={
        "events": [{"name": "pageview", "value": 1}]})
    assert r.status_code == 200
    assert r.json()["accepted"] == 0


def test_malformed_bodies_never_fail_the_caller(client, store):
    """A rejected metric must not surface as a console error on a live page."""
    client.get("/?ui=a")
    for body in (b"not json", b"[]", b'{"events": "nope"}'):
        r = client.post("/api/metrics", content=body,
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        assert r.json()["accepted"] == 0


def test_the_batch_is_capped(client, store):
    client.get("/?ui=a")
    r = client.post("/api/metrics", json={"events": [
        {"name": "view", "meta": {"view": "calc"}} for _ in range(500)]})
    assert r.json()["accepted"] == metrics.MAX_BATCH


def test_impossible_durations_are_discarded_not_stored(store):
    metrics.record("a" * 16, "a", [
        {"name": "dwell", "value": -5},
        {"name": "dwell", "value": 10 ** 12},
        {"name": "dwell", "value": 4000},
    ])
    dwell = metrics.summary()["variants"]["a"]["dwell_ms"]
    assert dwell["n"] == 1 and dwell["p50"] == 4000


def test_a_bad_session_id_is_refused(store):
    for sid in ("", "short", "not hex or alnum!!", "A" * 16):
        assert metrics.record(sid, "a",
                              [{"name": "pageview", "value": 1}]) == 0


# ---------------------------------------------------------------------------
# The corpus database is not a metrics database
# ---------------------------------------------------------------------------


def test_metrics_refuse_to_share_the_corpus_database(monkeypatch):
    """`build` recreates chickens.db, which would destroy the measurements.

    It is also the database the citation audit reasons about, and an
    observation is not a cited figure.
    """
    from counting_chicken_wings.build import DEFAULT_DB

    monkeypatch.setenv("WINGS_METRICS_DB", str(DEFAULT_DB))
    with pytest.raises(ValueError, match="corpus database"):
        metrics.connect()


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def test_the_summary_compares_the_two_arms(store):
    for sid, variant, load in (("a" * 16, "a", 900), ("b" * 16, "a", 1100),
                               ("c" * 16, "b", 400), ("d" * 16, "b", 600)):
        metrics.record(sid, variant, [
            {"name": "pageview", "value": load},
            {"name": "view", "meta": {"view": "season"}},
            {"name": "interact", "value": load + 500},
        ])
    s = metrics.summary()["variants"]
    assert s["a"]["sessions"] == 2 and s["b"]["sessions"] == 2
    assert s["a"]["load_ms"]["p50"] > s["b"]["load_ms"]["p50"]
    assert s["a"]["interaction_rate"] == 1.0
    assert s["b"]["distinct_views_found"] == 1


def test_the_summary_reports_no_significance_it_did_not_compute(store):
    """Two numbers side by side invite a conclusion the data cannot support."""
    metrics.record("a" * 16, "a", [{"name": "pageview", "value": 1}])
    s = metrics.summary()
    assert "significance" in s["note"].lower()
    blob = json.dumps(s)
    for word in ("p_value", "p-value", "significant", "winner", "confidence"):
        assert word not in blob.replace(s["note"], "")


def test_error_rate_is_per_session_not_per_event(store):
    """One session throwing fifty errors is one broken session, not fifty."""
    metrics.record("a" * 16, "b", [
        {"name": "error", "meta": {"message": "boom"}} for _ in range(50)])
    metrics.record("b" * 16, "b", [{"name": "pageview", "value": 1}])
    assert metrics.summary()["variants"]["b"]["error_rate"] == 0.5


def test_summary_of_an_empty_store_is_not_an_error(store):
    assert metrics.summary()["variants"] == {}


def test_reset_clears_the_comparison(store):
    metrics.record("a" * 16, "a", [{"name": "pageview", "value": 1}])
    metrics.reset()
    assert metrics.summary()["variants"] == {}
