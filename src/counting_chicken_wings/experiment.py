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
import os
import secrets
from pathlib import Path

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


def path_for(variant: str) -> Path:
    """File to serve, falling back to the control if the variant is missing.

    The redesign living in a separate file means it can be deleted, or not
    yet written, without taking the site down.
    """
    p = STATIC / VARIANTS.get(variant, VARIANTS[CONTROL])
    return p if p.exists() else STATIC / VARIANTS[CONTROL]
