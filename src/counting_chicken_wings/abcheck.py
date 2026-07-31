"""Validate the A/B event store, and clean what should not be compared.

A public experiment collects more than the experiment. Crawlers, prefetches,
our own `?ui=` flipping while testing, a tab left open over a weekend, a
stale beacon arriving after the store was emptied -- each of these lands in
the same table as the real visitors and none of them belong in the answer.

Two rules shape everything here.

**Report before deleting.** Every check runs read-only by default and prints
what it would remove. `--clean` is a separate decision, and it prints the
same list before acting.

**Never delete the failure you are testing for.** A session that loaded a
page and then made no API calls looks like junk and may be variant b
breaking on someone's browser -- which is the single most valuable thing the
experiment could tell us. Checks like that are reported and never cleaned;
`CLEANABLE` is deliberately a subset of the checks that exist.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from . import metrics

# A tab left open over a weekend is not engagement. Beyond this a dwell says
# something about the browser, not the design.
DWELL_CEILING_MS = 2 * 3600 * 1000

# The page issues several API calls on load, unconditionally. A load slower
# than this is a broken network, not a design difference.
LOAD_CEILING_MS = 120_000


@dataclass
class Finding:
    check: str
    why: str
    sessions: set[str] = field(default_factory=set)
    event_ids: list[int] = field(default_factory=list)
    cleanable: bool = True
    # Whether removing this drops whole sessions or single events. Stated
    # because they are very different amounts of damage.
    scope: str = "session"

    @property
    def count(self) -> int:
        return len(self.sessions) if self.scope == "session" \
            else len(self.event_ids)


def _rows(conn, since: float | None):
    where, args = "", []
    if since is not None:
        where, args = "WHERE ts >= ?", [since]
    return conn.execute(
        f"SELECT id, ts, session, variant, name, value FROM event {where} "
        f"ORDER BY id", args).fetchall()


def check(path: Path | None = None, since: float | None = None,
          older_than_days: float | None = None) -> list[Finding]:
    """Everything wrong with the store, in the order it matters."""
    conn = metrics.connect(path)
    try:
        rows = _rows(conn, since)
    finally:
        conn.close()

    by_session: dict[str, list] = {}
    for r in rows:
        by_session.setdefault(r["session"], []).append(r)

    findings = []

    # --- a session that saw both designs belongs to neither ---------------
    #
    # Per-session rates are the summary's whole output, and a session counted
    # in both arms contributes to both. This is mostly self-inflicted: it is
    # what `?ui=` flipping looks like afterwards, and it is how our own
    # testing shows up in real data.
    cross = Finding(
        "cross_variant_session",
        "session has events in more than one variant (usually ?ui= "
        "flipping, including our own testing) -- it inflates both arms")
    for sid, evs in by_session.items():
        if len({e["variant"] for e in evs}) > 1:
            cross.sessions.add(sid)
            cross.event_ids += [e["id"] for e in evs]
    findings.append(cross)

    # --- events that cannot be attributed to a page load -------------------
    orphan = Finding(
        "no_pageview",
        "events without a pageview: a beacon from a tab open before the "
        "store was last emptied, so its load and dwell describe nothing here")
    for sid, evs in by_session.items():
        if not any(e["name"] == "pageview" for e in evs):
            orphan.sessions.add(sid)
            orphan.event_ids += [e["id"] for e in evs]
    findings.append(orphan)

    # --- looks like junk, might be the finding -----------------------------
    #
    # NOT cleanable, on purpose. The page fires API calls on load without
    # being asked, so a pageview with none means the page's script did not
    # get that far. That is either a crawler or a variant breaking on
    # somebody's browser -- and the second is the most valuable thing this
    # experiment could surface. Deleting it to tidy the numbers would delete
    # the answer.
    silent = Finding(
        "pageview_without_api_calls",
        "loaded but made no API calls: a crawler, OR a variant failing on "
        "that browser -- inspect before assuming the former",
        cleanable=False)
    for sid, evs in by_session.items():
        names = {e["name"] for e in evs}
        if "pageview" in names and "api" not in names:
            silent.sessions.add(sid)
    findings.append(silent)

    # --- a session that hit the ingest cap is not a visitor ----------------
    flooded = Finding(
        "flooded_session",
        f"at the {metrics.MAX_EVENTS_PER_SESSION}-event ceiling: whatever "
        "this is, it is not one person using the page once")
    for sid, evs in by_session.items():
        if len(evs) >= metrics.MAX_EVENTS_PER_SESSION:
            flooded.sessions.add(sid)
            flooded.event_ids += [e["id"] for e in evs]
    findings.append(flooded)

    # --- single events that are wrong, in sessions that are fine -----------
    impossible = Finding(
        "impossible_load_time",
        f"pageview over {LOAD_CEILING_MS // 1000}s or non-positive: a broken "
        "network or a broken clock, not a design difference",
        scope="event")
    stale = Finding(
        "dwell_beyond_ceiling",
        f"dwell over {DWELL_CEILING_MS // 3600000}h: a tab left open, which "
        "says something about the browser and nothing about the design",
        scope="event")
    for r in rows:
        v = r["value"]
        if r["name"] == "pageview" and v is not None and (
                v <= 0 or v > LOAD_CEILING_MS):
            impossible.event_ids.append(r["id"])
            impossible.sessions.add(r["session"])
        elif r["name"] == "dwell" and v is not None and v > DWELL_CEILING_MS:
            stale.event_ids.append(r["id"])
            stale.sessions.add(r["session"])
    findings += [impossible, stale]

    # --- arms that no longer exist -----------------------------------------
    from . import experiment as exp
    unknown = Finding(
        "unknown_variant",
        "variant is not one of the arms that currently exist -- left over "
        "from a renamed or removed variant", scope="event")
    for r in rows:
        if r["variant"] not in exp.VARIANTS:
            unknown.event_ids.append(r["id"])
            unknown.sessions.add(r["session"])
    findings.append(unknown)

    # --- retention ---------------------------------------------------------
    if older_than_days:
        cutoff = time.time() - older_than_days * 86400
        old = Finding(
            "older_than_retention",
            f"older than {older_than_days:g} days", scope="event")
        for r in rows:
            if r["ts"] < cutoff:
                old.event_ids.append(r["id"])
                old.sessions.add(r["session"])
        findings.append(old)

    return [f for f in findings if f.count]


def clean(findings: list[Finding], path: Path | None = None) -> dict:
    """Delete what the cleanable findings point at. Returns what it removed.

    Session-scoped findings remove the session entirely -- a session that
    saw both arms cannot be repaired by dropping some of its events, because
    what is wrong with it is the session.
    """
    sessions, events = set(), set()
    for f in findings:
        if not f.cleanable:
            continue
        if f.scope == "session":
            sessions |= f.sessions
        else:
            events |= set(f.event_ids)

    conn = metrics.connect(path)
    try:
        with conn:
            removed_sessions = 0
            if sessions:
                cur = conn.executemany(
                    "DELETE FROM event WHERE session = ?",
                    [(s,) for s in sessions])
                removed_sessions = cur.rowcount
            removed_events = 0
            if events:
                cur = conn.execute(
                    "DELETE FROM event WHERE id IN (%s)"
                    % ",".join("?" * len(events)), list(events))
                removed_events = cur.rowcount
        # Reclaim the pages: this store is small and lives on a box shared
        # with every other app.
        conn.execute("VACUUM")
    finally:
        conn.close()
    return {
        "sessions_dropped": len(sessions),
        "events_from_dropped_sessions": removed_sessions,
        "individual_events_dropped": removed_events,
    }


def format_report(findings: list[Finding], cleaned: dict | None = None) -> str:
    out = []
    if not findings and cleaned is None:
        out.append("nothing to flag — every session looks like a visitor")
    for f in findings:
        mark = " " if f.cleanable else "*"
        unit = "session" if f.scope == "session" else "event"
        s = "s" if f.count != 1 else ""
        out.append(f"{mark} {f.check}: {f.count} {unit}{s}")
        out.append(f"    {f.why}")
    if any(not f.cleanable for f in findings):
        out.append("")
        out.append("* reported, never cleaned: removing it could delete the "
                   "failure the experiment exists to find")
    if cleaned is not None:
        out.append("")
        out.append(f"removed {cleaned['sessions_dropped']} session(s) "
                   f"({cleaned['events_from_dropped_sessions']} events) and "
                   f"{cleaned['individual_events_dropped']} individual event(s)")
    return "\n".join(out)
