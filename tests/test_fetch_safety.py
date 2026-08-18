"""Tests for the robots.txt / throttle / audit-log safety net around fetches.

tools/cooper/runner.py is the one place documents get pulled off the web for
citation verification, so this is where "safe scraping" either holds or does
not: robots.txt is honoured, requests to one host are throttled, the User-
Agent identifies the project and a contact, and every fetch is logged for
provenance. See tools/research_batch.py's own docstring for the trust model
these fetches feed into.

All network calls are faked -- these tests must never touch the real
network, both because CI has no business phoning outbound hosts and because a
real robots.txt could change out from under the test.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "cooper"))

import runner  # noqa: E402


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


@pytest.fixture(autouse=True)
def _clean_runner_state(monkeypatch):
    """Fresh per-host caches for every test.

    They are module-level dicts in runner.py because the real script runs
    once per batch and wants them to persist for that whole run -- but a test
    session is many independent "runs" sharing one process, so leaking state
    between tests would make later tests depend on earlier ones by accident.
    """
    monkeypatch.setattr(runner, "_ROBOTS_CACHE", {})
    monkeypatch.setattr(runner, "_LAST_FETCH", {})


def _allow_robots(url: str) -> bool:
    return "robots.txt" in url


def test_robots_disallow_skips_the_fetch_without_requesting_the_page(
        monkeypatch, tmp_path):
    """A Disallow must skip the page, not raise -- and the disallowed page
    itself must never be requested."""
    requested = []

    def fake_urlopen(req, timeout=None, context=None):
        requested.append(req.full_url)
        if _allow_robots(req.full_url):
            return _FakeResponse(b"User-agent: *\nDisallow: /private/\n")
        raise AssertionError("must not fetch a disallowed page")

    monkeypatch.setattr(runner.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)

    result = runner.fetch_url("https://example.com/private/page.html",
                              tmp_path / "doc")

    assert result is None
    assert any(_allow_robots(u) for u in requested)
    assert not any("private/page.html" in u for u in requested)


def test_robots_allow_permits_the_fetch(monkeypatch, tmp_path):
    def fake_urlopen(req, timeout=None, context=None):
        if _allow_robots(req.full_url):
            return _FakeResponse(b"User-agent: *\nAllow: /\n")
        return _FakeResponse(b"some page text with a figure: 12")

    monkeypatch.setattr(runner.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)

    result = runner.fetch_url("https://example.com/page.html",
                              tmp_path / "doc")

    assert result is not None
    assert "figure: 12" in result.read_text(encoding="utf-8")


def test_missing_robots_txt_does_not_block_the_fetch(monkeypatch, tmp_path):
    """A host with no robots.txt (a 404, a timeout, a dead host) must be
    treated as allowed. The file exists to restrict what would otherwise be
    unrestricted, not to require its own presence before anything can be
    fetched -- a broken robots.txt fetch must never masquerade as a Disallow."""
    def fake_urlopen(req, timeout=None, context=None):
        if _allow_robots(req.full_url):
            raise OSError("404 Not Found")
        return _FakeResponse(b"page body")

    monkeypatch.setattr(runner.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)

    result = runner.fetch_url("https://example.com/page.html",
                              tmp_path / "doc")
    assert result is not None


def test_throttle_only_delays_the_same_host(monkeypatch, tmp_path):
    """Two different hosts never wait on each other; the same host hit again
    immediately afterward must."""
    clock = {"t": 0.0}

    def fake_monotonic():
        return clock["t"]

    sleeps = []

    def fake_sleep(s):
        sleeps.append(s)
        clock["t"] += s

    def fake_urlopen(req, timeout=None, context=None):
        if _allow_robots(req.full_url):
            return _FakeResponse(b"User-agent: *\nAllow: /\n")
        return _FakeResponse(b"body")

    monkeypatch.setattr(runner.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(runner.time, "sleep", fake_sleep)
    monkeypatch.setattr(runner.urllib.request, "urlopen", fake_urlopen)

    runner.fetch_url("https://example.com/one.html", tmp_path / "one")
    assert sleeps == []                      # first-ever fetch: nothing to wait on

    runner.fetch_url("https://other.org/two.html", tmp_path / "two")
    assert sleeps == []                      # a different host: unaffected

    runner.fetch_url("https://example.com/three.html", tmp_path / "three")
    assert sleeps and sleeps[-1] > 0          # same host again, immediately: throttled


def test_user_agent_identifies_the_project_and_a_contact():
    """The single highest-value courtesy for an unattended fetcher: give a
    host operator someone to email before they reach for a block."""
    assert "counting-chicken-wings" in runner.FETCH_UA
    assert "@" in runner.FETCH_UA or "contact" in runner.FETCH_UA.lower()


def test_fetch_writes_an_audit_log_entry(monkeypatch, tmp_path):
    """What was fetched, from where, and when is the product of a citation
    pipeline, not an afterthought -- see tools/research_batch.py's `verify`,
    which re-checks every quote against exactly what landed here."""
    def fake_urlopen(req, timeout=None, context=None):
        if _allow_robots(req.full_url):
            return _FakeResponse(b"User-agent: *\nAllow: /\n")
        return _FakeResponse(b"body text")

    monkeypatch.setattr(runner.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)

    dest = tmp_path / "doc"
    runner.fetch_url("https://example.com/page.html", dest)

    log = dest.parent / "_fetch_log.jsonl"
    assert log.exists()
    entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert entry["url"] == "https://example.com/page.html"
    assert entry["status"] == "ok"
    assert entry["sha256"]


def test_robots_disallow_is_logged_too(monkeypatch, tmp_path):
    def fake_urlopen(req, timeout=None, context=None):
        if _allow_robots(req.full_url):
            return _FakeResponse(b"User-agent: *\nDisallow: /\n")
        raise AssertionError("must not fetch a disallowed page")

    monkeypatch.setattr(runner.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)

    dest = tmp_path / "doc"
    runner.fetch_url("https://example.com/page.html", dest)

    log = dest.parent / "_fetch_log.jsonl"
    entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert entry["status"] == "robots-disallow"
