"""The validator: what it flags, and more importantly what it refuses to.

A cleaner that quietly deletes the interesting cases is worse than no
cleaner, because the store then looks tidy and is wrong. Most of these tests
are about restraint.
"""

import pytest

from counting_chicken_wings import abcheck, metrics


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("WINGS_METRICS_DB", str(tmp_path / "metrics.db"))


def sid(n: int) -> str:
    return f"{n:032x}"


def found(findings, name):
    return next((f for f in findings if f.check == name), None)


def a_normal_session(n: int, variant: str = "a") -> str:
    s = sid(n)
    metrics.record(s, variant, [
        {"name": "pageview", "value": 800},
        {"name": "api", "value": 20},
        {"name": "interact", "value": 3000},
        {"name": "dwell", "value": 45000},
    ])
    return s


def test_a_clean_store_is_flagged_for_nothing():
    a_normal_session(1, "a")
    a_normal_session(2, "b")
    assert abcheck.check() == []


# ---------------------------------------------------------------------------
# What it catches
# ---------------------------------------------------------------------------


def test_a_session_that_saw_both_arms_is_flagged():
    """Our own `?ui=` flipping, and it inflates both arms at once."""
    both = sid(3)
    metrics.record(both, "a", [{"name": "pageview", "value": 800}])
    metrics.record(both, "b", [{"name": "pageview", "value": 800}])

    f = found(abcheck.check(), "cross_variant_session")
    assert f and f.sessions == {both}


def test_events_with_no_pageview_are_flagged():
    """A beacon from a tab that was open before the store was emptied."""
    metrics.record(sid(4), "a", [{"name": "dwell", "value": 5000}])
    f = found(abcheck.check(), "no_pageview")
    assert f and f.sessions == {sid(4)}


def test_an_impossible_load_time_is_flagged_as_one_event():
    """The session is fine; one number in it is not."""
    s = a_normal_session(5)
    metrics.record(s, "a", [{"name": "pageview", "value": 300_000}])

    f = found(abcheck.check(), "impossible_load_time")
    assert f and f.scope == "event" and len(f.event_ids) == 1


def test_a_tab_left_open_is_flagged():
    s = a_normal_session(6)
    metrics.record(s, "a", [{"name": "dwell", "value": 9 * 3600 * 1000}])
    assert found(abcheck.check(), "dwell_beyond_ceiling")


def test_a_flooded_session_is_flagged():
    s = sid(7)
    for _ in range(metrics.MAX_EVENTS_PER_SESSION // metrics.MAX_BATCH + 1):
        metrics.record(s, "b", [{"name": "view", "meta": {"view": "calc"}}
                                for _ in range(metrics.MAX_BATCH)])
    assert found(abcheck.check(), "flooded_session")


def test_a_variant_that_no_longer_exists_is_flagged():
    metrics.record(sid(8), "legacy-c", [{"name": "pageview", "value": 1}])
    assert found(abcheck.check(), "unknown_variant")


def test_retention_is_opt_in():
    import time as t
    s = a_normal_session(9)
    conn = metrics.connect()
    with conn:
        conn.execute("UPDATE event SET ts = ? WHERE session = ?",
                     (t.time() - 40 * 86400, s))
    conn.close()

    assert found(abcheck.check(), "older_than_retention") is None
    assert found(abcheck.check(older_than_days=30), "older_than_retention")


# ---------------------------------------------------------------------------
# What it refuses to delete
# ---------------------------------------------------------------------------


def test_a_load_with_no_api_calls_is_reported_but_never_cleaned():
    """The most important restraint in this module.

    It looks like a crawler and it looks identical to a variant failing on
    somebody's browser -- which is the single most valuable thing this
    experiment could surface. Tidying it away would delete the answer.
    """
    metrics.record(sid(10), "b", [{"name": "pageview", "value": 300}])

    f = found(abcheck.check(), "pageview_without_api_calls")
    assert f and not f.cleanable

    abcheck.clean(abcheck.check())
    assert metrics.summary()["variants"]["b"]["sessions"] == 1, \
        "a possible variant failure was cleaned away"


def test_cleaning_leaves_the_real_sessions_alone():
    good_a = a_normal_session(11, "a")
    good_b = a_normal_session(12, "b")
    metrics.record(sid(13), "a", [{"name": "dwell", "value": 1}])  # orphan

    abcheck.clean(abcheck.check())

    conn = metrics.connect()
    try:
        left = {r[0] for r in conn.execute("SELECT DISTINCT session FROM event")}
    finally:
        conn.close()
    assert left == {good_a, good_b}


def test_the_report_is_read_only():
    """`check` must never be the thing that changes the store."""
    a_normal_session(14)
    metrics.record(sid(15), "a", [{"name": "dwell", "value": 1}])
    before = metrics.summary()

    abcheck.check()
    abcheck.check(older_than_days=1)

    assert metrics.summary() == before


def test_cleaning_a_cross_variant_session_removes_it_from_both_arms():
    """Dropping half of it would leave the half that is still wrong."""
    a_normal_session(16, "a")
    both = sid(17)
    metrics.record(both, "a", [{"name": "pageview", "value": 1}])
    metrics.record(both, "b", [{"name": "pageview", "value": 1}])

    abcheck.clean(abcheck.check())

    s = metrics.summary()["variants"]
    assert s["a"]["sessions"] == 1
    assert "b" not in s


def test_the_report_names_the_starred_checks_as_never_cleaned():
    metrics.record(sid(18), "b", [{"name": "pageview", "value": 300}])
    text = abcheck.format_report(abcheck.check())
    assert "* pageview_without_api_calls" in text
    assert "never cleaned" in text
