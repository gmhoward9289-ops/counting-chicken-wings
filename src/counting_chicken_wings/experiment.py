"""Which frontend a visitor gets, and why.

Two pages exist: `static/index.html` (variant `a`, the one that shipped) and
`static/v2/index.html` (variant `b`, the redesign). The server chooses one
per visitor and the choice sticks, because a design cannot be measured if
the page changes under the person being measured.

Assignment is deterministic from a random visitor id rather than a coin flip
per request. That is the difference between a visitor who reloads landing on
the same design and one who sees the site flicker between two of them.

**The split defaults to 0** -- everybody gets `a` until someone deliberately
turns the experiment on with `WINGS_AB_SPLIT`. Deploying a branch should not
silently start serving a different site.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from pathlib import Path

log = logging.getLogger(__name__)

STATIC = Path(__file__).parent / "static"

# Variant -> file, relative to STATIC.
VARIANTS = {
    "a": "index.html",
    "b": "v2/index.html",
}
CONTROL = "a"

SID_COOKIE = "ccw_sid"
UI_COOKIE = "ccw_ui"
COOKIE_MAX_AGE = 60 * 60 * 24 * 90      # 90 days; long enough to finish a test

# Query parameter that forces a variant. Kept because it is what makes this
# usable by hand: `?ui=b` is how you look at the redesign, and how a
# screenshot or a bug report can name which page it is about.
UI_PARAM = "ui"


def split_percent() -> int:
    """Percentage of new visitors assigned to `b`. Clamped to 0-100."""
    raw = os.environ.get("WINGS_AB_SPLIT", "0")
    try:
        return max(0, min(100, int(raw)))
    except ValueError:
        return 0


def new_session_id() -> str:
    """Random, opaque, and carrying nothing about the visitor.

    Not derived from IP or user agent: a fingerprint would be identifying,
    and a bucket only needs to be stable, not meaningful.
    """
    return secrets.token_hex(16)


def bucket(session_id: str, percent: int | None = None) -> str:
    """Stable assignment for a visitor id."""
    pct = split_percent() if percent is None else percent
    if pct <= 0:
        return "a"
    if pct >= 100:
        return "b"
    digest = hashlib.sha256(session_id.encode()).hexdigest()
    return "b" if int(digest[:8], 16) % 100 < pct else "a"


def resolve(forced: str | None, ui_cookie: str | None,
            sid_cookie: str | None) -> tuple[str, str, str]:
    """Decide the variant for one request.

    Returns `(variant, session_id, reason)`. `reason` is returned rather than
    logged so `/api/experiment` can state plainly why this browser is seeing
    what it is seeing -- "why am I still on the old page" was otherwise only
    answerable by reading cookies by hand.
    """
    sid = sid_cookie if _valid_sid(sid_cookie) else new_session_id()

    if forced in VARIANTS:
        return forced, sid, "forced by ?ui="
    if ui_cookie in VARIANTS:
        return ui_cookie, sid, "sticky from a previous visit"
    return bucket(sid), sid, f"assigned at a {split_percent()}% split"


def _valid_sid(sid: str | None) -> bool:
    return bool(sid) and len(sid) >= 8 and all(
        c in "0123456789abcdef" for c in sid)


# ---------------------------------------------------------------------------
# Signed variant tokens
# ---------------------------------------------------------------------------
#
# The token is what a page uses to say "I am variant b" and be believed.
#
# It is baked into the HTML rather than handed over in a cookie, and that is
# the whole point: a cookie describes the browser *now*, while a token
# describes the page it was served with. The `dwell` beacon fires during
# unload, after the next page has already replaced the cookie -- which is
# exactly how variant b's time got credited to variant a before this existed.
# A token travels with the page instance that earned the measurement.
#
# It also closes the tampering hole that the cookie never really closed: the
# collection endpoint is public, so without a signature anyone could post
# events naming whichever arm they wanted to win.

TOKEN_TTL = 12 * 3600      # a page open longer than this stops reporting

_FALLBACK_SECRET = secrets.token_hex(32)


def secret() -> bytes:
    """Signing key. Set `WINGS_AB_SECRET` for anything that restarts.

    Without it each process invents its own key, so every token issued
    before a restart is refused afterwards and those visitors' events are
    dropped. On Render that is every deploy, plus every wake from the free
    tier's idle spin-down -- which is most of them.

    It is also why this must not be generated per worker: two processes with
    two keys reject each other's tokens, and the loss looks like noise rather
    than like a misconfiguration.
    """
    env = os.environ.get("WINGS_AB_SECRET")
    if env:
        return env.encode()
    if split_percent() > 0:
        log.warning(
            "WINGS_AB_SECRET is not set: A/B tokens are signed with a "
            "per-process key and will be refused after a restart. Set it "
            "before trusting collected metrics.")
    return _FALLBACK_SECRET.encode()


def issue_token(session_id: str, variant: str, now: float | None = None) -> str:
    """Bind a variant to a session and a moment, and sign the three."""
    ts = int(now if now is not None else time.time())
    payload = f"{session_id}.{variant}.{ts}"
    sig = hmac.new(secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def read_token(token: str | None, session_id: str | None,
               now: float | None = None) -> str | None:
    """Return the variant a valid token attests to, else None.

    Rejects a token whose session does not match the caller's cookie, so one
    cannot be lifted from a page and replayed under another id.
    """
    if not token or token.count(".") != 3:
        return None
    sid, variant, ts, sig = token.split(".")
    if variant not in VARIANTS or sid != session_id:
        return None
    expected = hmac.new(secret(), f"{sid}.{variant}.{ts}".encode(),
                        hashlib.sha256).hexdigest()[:32]
    # Constant time: a token check that leaks its progress through the
    # signature is forgeable one byte at a time.
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        age = (now if now is not None else time.time()) - int(ts)
    except ValueError:
        return None
    if age < -300 or age > TOKEN_TTL:
        return None
    return variant


def path_for(variant: str) -> Path:
    """File to serve, falling back to the control if the variant is missing.

    The redesign living in a separate file means it can be deleted, or not
    yet written, without taking the site down.
    """
    p = STATIC / VARIANTS.get(variant, VARIANTS[CONTROL])
    return p if p.exists() else STATIC / VARIANTS[CONTROL]


# The placeholder both pages carry, replaced per request with a fresh token.
TOKEN_PLACEHOLDER = "__CCW_AB_TOKEN__"

_page_cache: dict[Path, tuple[float, str]] = {}


def render_page(path: Path, token: str) -> str:
    """The page with its token in it.

    Cached on mtime rather than re-read per request -- these files are ~90KB
    and the only per-request difference is a 100-byte token. The mtime check
    is what keeps `wings gui` honest while someone is editing the redesign;
    serving a stale page to the person redesigning it would be its own kind
    of bug.
    """
    stamp = path.stat().st_mtime
    cached = _page_cache.get(path)
    if not cached or cached[0] != stamp:
        cached = (stamp, path.read_text())
        _page_cache[path] = cached
    return cached[1].replace(TOKEN_PLACEHOLDER, token)
