"""The A/B harness: assignment, stickiness, collection, and aggregation.

These test the properties that make a measurement trustworthy rather than
the plumbing. An experiment that reassigns a visitor on reload, or that lets
a client name its own arm, produces numbers that look fine and mean nothing.
"""

import json
import re
import time

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


@pytest.fixture(autouse=True)
def fixed_secret(monkeypatch):
    """A stable signing key, so tests do not depend on process identity."""
    monkeypatch.setenv("WINGS_AB_SECRET", "test-secret-not-a-real-one")


def token_from(response) -> str:
    """The signed variant token the server baked into the page."""
    m = re.search(r'name="ccw-ab-token" content="([^"]+)"', response.text)
    assert m, "page carries no A/B token"
    return m.group(1)


def send(client, response, events):
    """Post a batch the way the page would: with its own page's token."""
    return client.post("/api/metrics",
                       json={"token": token_from(response), "events": events})


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


def test_events_are_recorded_against_the_variant_in_the_token(client, store):
    page = client.get("/?ui=b")
    r = send(client, page, [
        {"name": "pageview", "value": 812, "meta": {"w": 390}},
        {"name": "view", "meta": {"view": "season"}},
    ])
    assert r.json()["accepted"] == 2
    assert metrics.summary()["variants"]["b"]["sessions"] == 1


def test_a_late_beacon_is_credited_to_the_page_that_sent_it(client, store):
    """The regression the token exists for.

    `dwell` is sent by `sendBeacon` during unload, so on a variant switch it
    lands *after* the next page's cookie is set. Deriving the variant from
    the cookie at POST time recorded variant b's 32 seconds against variant
    a -- silently, and on the event the comparison most depends on.
    """
    page_b = client.get("/?ui=b")
    client.get("/?ui=a")          # cookie is now `a`; the beacon is still b's
    send(client, page_b, [{"name": "dwell", "value": 31824}])

    v = metrics.summary()["variants"]
    assert v["b"]["dwell_ms"]["p50"] == 31824, "dwell lost from its own arm"
    assert v.get("a", {}).get("dwell_ms", {}).get("n", 0) == 0, \
        "dwell was credited to the wrong variant"


def test_an_unsigned_claim_is_refused(client, store):
    """Asserting a variant without the signature must not work.

    This endpoint is public. If naming an arm were enough, anyone could
    decide which design won.
    """
    client.get("/?ui=a")
    r = client.post("/api/metrics", json={
        "variant": "b", "events": [{"name": "interact", "value": 1}]})
    assert r.json()["accepted"] == 0
    assert metrics.summary()["variants"] == {}


def test_a_forged_token_is_refused(client, store):
    """Right shape, wrong signature."""
    page = client.get("/?ui=a")
    sid, variant, ts, sig = token_from(page).split(".")
    for bad in (f"{sid}.b.{ts}.{sig}",              # variant swapped
                f"{sid}.{variant}.{ts}.{'0' * 32}",  # signature invented
                f"{'f' * 32}.{variant}.{ts}.{sig}"):  # someone else's session
        r = client.post("/api/metrics",
                        json={"token": bad,
                              "events": [{"name": "pageview", "value": 1}]})
        assert r.json()["accepted"] == 0, f"forged token accepted: {bad}"


def test_a_token_from_another_session_cannot_be_replayed(client, store):
    """Lifting a token out of a page must not let another browser use it."""
    victim = TestClient(app)
    stolen = token_from(victim.get("/?ui=b"))

    attacker = TestClient(app)
    attacker.get("/?ui=a")
    r = attacker.post("/api/metrics", json={
        "token": stolen, "events": [{"name": "interact", "value": 1}]})
    assert r.json()["accepted"] == 0


def test_an_expired_token_is_refused(store):
    sid = "a" * 32
    old = exp.issue_token(sid, "b", now=time.time() - exp.TOKEN_TTL - 60)
    assert exp.read_token(old, sid) is None
    fresh = exp.issue_token(sid, "b")
    assert exp.read_token(fresh, sid) == "b"


def test_a_token_signed_with_another_key_is_refused(monkeypatch, store):
    """What a restart without WINGS_AB_SECRET looks like: dropped, not wrong."""
    sid = "a" * 32
    tok = exp.issue_token(sid, "b")
    monkeypatch.setenv("WINGS_AB_SECRET", "a-different-key")
    assert exp.read_token(tok, sid) is None


def test_unknown_event_names_are_dropped(client, store):
    page = client.get("/?ui=a")
    r = send(client, page, [
        {"name": "pageview", "value": 100},
        {"name": "rm -rf", "value": 1},
        {"name": "purchase", "value": 999},
    ])
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
    page = client.get("/?ui=a")
    r = send(client, page, [
        {"name": "view", "meta": {"view": "calc"}} for _ in range(500)])
    assert r.json()["accepted"] == metrics.MAX_BATCH


def test_one_session_cannot_flood_an_arm(client, store):
    """Every rate in the summary is per-session, so one runaway drags an arm."""
    page = client.get("/?ui=b")
    for _ in range(50):
        send(client, page, [{"name": "view", "meta": {"view": "calc"}}
                            for _ in range(metrics.MAX_BATCH)])
    assert (metrics.summary()["variants"]["b"]["events"]
            == metrics.MAX_EVENTS_PER_SESSION)


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


def test_the_summary_states_how_long_it_has_been_collecting(store):
    """An emptied store must be visible, not inferred.

    The Render container has no disk, so a deploy or a wake from the free
    tier's spin-down restarts collection. A window that keeps resetting to
    minutes is that -- not a quiet week.
    """
    metrics.record("a" * 16, "a", [{"name": "pageview", "value": 1}])
    s = metrics.summary()
    assert s["collecting_since"] and s["latest_event"]
    assert s["window_hours"] >= 0

    metrics.reset()
    assert metrics.summary()["collecting_since"] is None


def test_the_served_page_never_leaks_the_placeholder(client):
    """A page serving the literal placeholder collects nothing, silently."""
    for url in ("/?ui=a", "/?ui=b"):
        assert exp.TOKEN_PLACEHOLDER not in client.get(url).text


def test_editing_a_variant_is_picked_up_without_a_restart(client, tmp_path):
    """`wings gui` must not serve a stale page to whoever is redesigning it."""
    page = exp.path_for("b")
    original = page.read_text()
    try:
        page.write_text(original.replace("</title>", " EDITED</title>", 1))
        assert "EDITED" in client.get("/?ui=b").text
    finally:
        page.write_text(original)


def test_reset_clears_the_comparison(store):
    metrics.record("a" * 16, "a", [{"name": "pageview", "value": 1}])
    metrics.reset()
    assert metrics.summary()["variants"] == {}
