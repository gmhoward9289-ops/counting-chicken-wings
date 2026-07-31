"""Event store for the frontend A/B test.

Deliberately its own SQLite file, never `chickens.db`. `build.py` recreates
the corpus database from YAML on every build, so anything observational
written there is destroyed by the next deploy -- and the corpus database is
also the thing the audit reasons about. Measurements are not the corpus.
They are not cited, they are not sourced, and they must not be able to
appear anywhere the citation guarantee applies.

Nothing here is on the request path for an answer. If the metrics database
cannot be opened, collection fails and the page still works: an experiment
that can take the site down is not worth running.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from pathlib import Path

from .build import DEFAULT_DB

# The events we accept. A closed set, because this endpoint is unauthenticated
# on a public deployment and an open one is a free write-anything sink.
EVENTS = frozenset({
    "pageview",     # value = ms from navigation start to load event
    "view",         # meta.view = which tab; how much of the UI gets found
    "interact",     # value = ms from load to the first real input change
    "api",          # value = ms for one API call; meta.path, meta.status
    "error",        # meta.message; JS errors and failed fetches
    "dwell",        # value = ms on page, sent on pagehide
})

SESSION_RE = re.compile(r"\A[a-z0-9]{8,64}\Z")

MAX_BATCH = 50          # events per POST
MAX_META = 500          # characters of JSON meta per event
MAX_SUMMARY_ROWS = 200_000

_ENV_METRICS_DB = os.environ.get("WINGS_METRICS_DB")
DEFAULT_METRICS_DB = (
    Path(_ENV_METRICS_DB).expanduser() if _ENV_METRICS_DB
    else DEFAULT_DB.parent / "metrics.db"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS event (
  id      INTEGER PRIMARY KEY,
  ts      REAL NOT NULL,
  session TEXT NOT NULL,
  variant TEXT NOT NULL,
  name    TEXT NOT NULL,
  value   REAL,
  meta    TEXT
);
CREATE INDEX IF NOT EXISTS event_variant_name ON event(variant, name);
CREATE INDEX IF NOT EXISTS event_session ON event(session);
CREATE INDEX IF NOT EXISTS event_ts ON event(ts);
"""


def metrics_db() -> Path:
    """Resolved path of the metrics database.

    Read through a function rather than captured at import, so a test that
    sets `WINGS_METRICS_DB` after import still gets its own file instead of
    writing into the developer's.
    """
    env = os.environ.get("WINGS_METRICS_DB")
    return Path(env).expanduser() if env else DEFAULT_METRICS_DB


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = Path(path) if path else metrics_db()
    if p.resolve() == DEFAULT_DB.resolve():
        raise ValueError(
            "refusing to write metrics into the corpus database: "
            "`build` recreates it and the measurements would be lost"
        )
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    # Concurrent readers during a write matter here: the summary endpoint is
    # read while visitors are still posting events.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def _clean_meta(meta) -> str | None:
    if meta is None:
        return None
    if not isinstance(meta, dict):
        return None
    out = json.dumps({str(k): meta[k] for k in sorted(meta)},
                     separators=(",", ":"), default=str)
    return out[:MAX_META]


def record(session: str, variant: str, events: list[dict],
           path: Path | None = None) -> int:
    """Store a batch. Returns how many rows were accepted.

    Anything malformed is dropped rather than raising: a client sending one
    bad event should not lose the good ones alongside it, and the browser has
    no way to act on the error anyway.
    """
    if not SESSION_RE.match(session or ""):
        return 0
    rows = []
    now = time.time()          # server clock; client clocks are not trusted
    for e in events[:MAX_BATCH]:
        if not isinstance(e, dict):
            continue
        name = e.get("name")
        if name not in EVENTS:
            continue
        value = e.get("value")
        if value is not None:
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = None
            else:
                # A negative or absurd duration is a broken clock, not data.
                if value < 0 or value > 86_400_000:
                    value = None
        rows.append((now, session, variant, name, value,
                     _clean_meta(e.get("meta"))))
    if not rows:
        return 0
    conn = connect(path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO event (ts, session, variant, name, value, meta) "
                "VALUES (?, ?, ?, ?, ?, ?)", rows)
    finally:
        conn.close()
    return len(rows)


def _pct(sorted_vals: list[float], q: float) -> float | None:
    """Nearest-rank percentile. No numpy dependency for six numbers."""
    if not sorted_vals:
        return None
    i = min(len(sorted_vals) - 1, max(0, round(q * (len(sorted_vals) - 1))))
    return round(sorted_vals[i], 1)


def summary(path: Path | None = None, since: float | None = None) -> dict:
    """Per-variant aggregates.

    Aggregates only, and deliberately so -- this endpoint is reachable on a
    public deployment. There is no per-session output, and nothing stored is
    identifying to begin with: a random cookie id, and durations.
    """
    conn = connect(path)
    try:
        where, args = "", []
        if since is not None:
            where, args = "WHERE ts >= ?", [since]
        rows = conn.execute(
            f"SELECT session, variant, name, value, meta FROM event {where} "
            f"ORDER BY id LIMIT {MAX_SUMMARY_ROWS}", args).fetchall()
    finally:
        conn.close()

    per: dict[str, dict] = {}
    for r in rows:
        v = per.setdefault(r["variant"], {
            "sessions": set(), "counts": {}, "load_ms": [], "dwell_ms": [],
            "ttfi_ms": [], "api_ms": [], "views": set(),
            "interacted": set(), "errored": set(),
        })
        v["sessions"].add(r["session"])
        v["counts"][r["name"]] = v["counts"].get(r["name"], 0) + 1
        val = r["value"]
        if r["name"] == "pageview" and val is not None:
            v["load_ms"].append(val)
        elif r["name"] == "dwell" and val is not None:
            v["dwell_ms"].append(val)
        elif r["name"] == "interact":
            v["interacted"].add(r["session"])
            if val is not None:
                v["ttfi_ms"].append(val)
        elif r["name"] == "api" and val is not None:
            v["api_ms"].append(val)
        elif r["name"] == "view":
            try:
                v["views"].add(json.loads(r["meta"] or "{}").get("view"))
            except (ValueError, AttributeError):
                pass
        elif r["name"] == "error":
            v["errored"].add(r["session"])

    out = {}
    for name, v in sorted(per.items()):
        n = len(v["sessions"]) or 1
        load = sorted(v["load_ms"])
        dwell = sorted(v["dwell_ms"])
        ttfi = sorted(v["ttfi_ms"])
        api = sorted(v["api_ms"])
        out[name] = {
            "sessions": len(v["sessions"]),
            "events": sum(v["counts"].values()),
            "event_counts": dict(sorted(v["counts"].items())),
            "load_ms": {"p50": _pct(load, .5), "p95": _pct(load, .95),
                        "n": len(load)},
            "api_ms": {"p50": _pct(api, .5), "p95": _pct(api, .95),
                       "n": len(api)},
            "dwell_ms": {"p50": _pct(dwell, .5), "n": len(dwell)},
            "time_to_first_interaction_ms": {"p50": _pct(ttfi, .5),
                                             "n": len(ttfi)},
            # The two rates worth comparing between designs: did they touch
            # it at all, and did it break while they did.
            "interaction_rate": round(len(v["interacted"]) / n, 3),
            "error_rate": round(len(v["errored"]) / n, 3),
            "views_per_session": round(v["counts"].get("view", 0) / n, 2),
            "distinct_views_found": len([x for x in v["views"] if x]),
        }
    return {
        "database": str(metrics_db() if path is None else path),
        "since": since,
        "variants": out,
        # Stated rather than implied: these counts are not evidence of a
        # difference until there are enough of them, and the page reporting
        # them is not going to do the statistics for you.
        "note": ("Descriptive only. No significance testing is performed; "
                 "small session counts will differ by chance alone."),
    }


def reset(path: Path | None = None) -> None:
    """Drop every recorded event. For starting a clean comparison."""
    conn = connect(path)
    try:
        with conn:
            conn.execute("DELETE FROM event")
    finally:
        conn.close()
