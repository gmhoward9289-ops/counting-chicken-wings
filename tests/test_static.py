"""Structural invariants of the web UI.

There is no browser in CI, so these do not test behaviour -- they test the
properties of the served page that have actually broken before and that a
reader cannot check by eye across three files.

The project's own history is the argument for each one. Floor prose was
hardcoded in both `cli.py` and the page, so fixing the data fixed neither. A
country's coverage claim was written into the page, was true when written,
and was false hours later. Both were caught by a human noticing, which does
not scale.
"""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / \
    "src" / "counting_chicken_wings" / "static"


def _linked(doc, ext):
    """Same-origin assets the page pulls, resolved to files on disk.

    Anchored on `/static/` so a CDN stays out of it: Plotly is not ours and
    its minified bundle would swamp every check below in false positives.
    """
    return [STATIC / rel for rel in
            re.findall(rf'(?:href|src)="/static/([^"]+\.{ext})"', doc)]


@pytest.fixture(scope="module")
def doc():
    """The page itself, exactly as served."""
    return (STATIC / "index.html").read_text()


@pytest.fixture(scope="module")
def html(doc):
    """Everything the page is made of: its markup plus its linked assets.

    Markup, style and behaviour are three files (`index.html`, `app.css`,
    `app.js`). Every invariant here is about what reaches the browser, not
    about which file it was typed into, so the fixture follows the links
    rather than reading only the document.

    Getting this wrong is silent in the worst direction: a `.headline` rule
    living in the stylesheet would read as a page with no headline rule at
    all, and the tests would pass by finding nothing to object to.
    """
    return "\n".join([doc] + [p.read_text() for p in
                              _linked(doc, "css") + _linked(doc, "js")])


@pytest.fixture(scope="module")
def script(doc):
    """Executable JS only.

    Non-greedy per block, because a greedy match spans from the first
    <script> to the last and swallows the entire markup in between -- which
    made these tests flag the HTML comments that document the very bugs they
    check for. JS comments are stripped for the same reason: a comment
    saying "this used to be hardcoded" is the opposite of a violation.
    """
    blocks = re.findall(r"<script>(.*?)</script>", doc, re.S)
    blocks += [p.read_text() for p in _linked(doc, "js")]
    assert blocks, "could not find any script"
    js = "\n".join(blocks)
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)     # block comments
    js = re.sub(r"^\s*//.*$", "", js, flags=re.M)     # whole-line comments
    return js


# ---------------------------------------------------------------------------
# Colour lives in exactly one place
# ---------------------------------------------------------------------------


def test_no_raw_hex_colours_in_the_script(script):
    """Dark mode works because charts read CSS variables at draw time.

    A literal hex in the JS is invisible in one theme or the other, and the
    failure is silent: the chart still renders, just illegibly.
    """
    # Deliberately narrow: 3- and 6-digit hex in a string literal.
    hexes = re.findall(r"""['"]\#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})['"]""",
                       script)
    assert not hexes, f"hard-coded colours in JS: {sorted(set(hexes))}"


def test_both_themes_define_the_same_custom_properties(html):
    """A variable missing from the dark block silently inherits the light one."""
    def props(block):
        return set(re.findall(r"(--[a-z0-9-]+)\s*:", block))

    light = re.search(r":root\s*\{(.*?)\}", html, re.S)
    dark = re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\}', html, re.S)
    assert light and dark, "missing a theme block"

    # The dark block overrides; it need not restate fonts, which carry no
    # colour. Every colour-bearing property must appear in both.
    fonts = {"--mono", "--display"}
    missing = (props(light.group(1)) - fonts) - props(dark.group(1))
    assert not missing, f"not themed for dark: {sorted(missing)}"


def test_theme_is_applied_before_first_paint(doc):
    """Otherwise a dark reload flashes light.

    Deliberately reads the document rather than the resolved bundle: the
    point is that the theme attribute is set by a script the parser runs on
    its way through <head>, before anything paints. A linked file cannot do
    this job, so following the links here would defeat the check.

    Checked against the mechanism (`dataset.theme` / `data-theme` set from
    `localStorage`) rather than the mere presence of the string. The page
    this replaced passed the older, looser version for the wrong reason --
    its entire stylesheet was inline, so `:root[data-theme="dark"]` put the
    substring in <head> whether or not any script ever set it.
    """
    head = doc.split("</head>")[0]
    m = re.search(r"<script>(.*?)</script>", head, re.S)
    assert m, "no inline script in <head> to set the theme"
    boot = m.group(1)
    assert "dataset.theme" in boot or "data-theme" in boot, \
        "the <head> script does not set the theme attribute"
    assert "localStorage" in boot, "stored theme not read before paint"


# ---------------------------------------------------------------------------
# Prose that belongs to the data must not be retyped in the page
# ---------------------------------------------------------------------------


def test_the_page_does_not_hardcode_a_supply_chain_floor_note(script):
    """`supply_chain.floor_note` exists because this was wing text in the HTML.

    A hardcoded cut-up-line description shipped to anyone asking about eggs.
    """
    for phrase in ("cut-up line", "fryer basket", "cut up six chickens yourself"):
        assert phrase not in script, (
            f"floor prose {phrase!r} is hardcoded; it belongs in "
            "supply_chain.floor_note")


def test_country_coverage_claims_are_not_written_into_the_page(script):
    """Coverage changes; prose about coverage rots.

    An earlier draft stated "Israel cannot answer how many chickens", which
    was true when written and false once a figure was sourced.
    """
    claims = re.findall(r"(?:Israel|the United States|USA)[^\n]{0,60}"
                        r"cannot (?:answer|tell)", script)
    assert not claims, f"hardcoded coverage claim: {claims}"


def test_the_size_verdict_is_not_hardcoded(script):
    """Each species' verdict comes from quality_axis, not from the client."""
    assert "Heavier birds give more meat" not in script, \
        "broiler verdict summary is hardcoded in the page"
    assert "/api/quality-axes" in script, "size view is not axis-driven"


# ---------------------------------------------------------------------------
# Evidence grading is the product, so it has to reach the page
# ---------------------------------------------------------------------------


def test_every_evidence_grade_has_a_badge_style(html):
    """A grade with no style renders as an unlabelled pill."""
    from counting_chicken_wings import db as dbm

    conn = dbm.connect()
    try:
        grades = {r["confidence"] for r in conn.execute(
            "SELECT DISTINCT confidence FROM loss_factor "
            "WHERE confidence IS NOT NULL")}
    finally:
        conn.close()

    for g in grades:
        assert f".b-{g}" in html, f"no badge style for evidence grade {g!r}"


def test_estimates_are_visually_distinct_from_sourced_figures(html):
    """The whole design argument: an unsourced figure must look unsourced."""
    m = re.search(r"\.b-estimate\s*\{(.*?)\}", html, re.S)
    assert m, "no .b-estimate rule"
    rule = m.group(1)
    assert "dashed" in rule or "repeating-linear-gradient" in rule, \
        "estimate badge is not visually distinguished from sourced grades"


# ---------------------------------------------------------------------------
# Accessibility floor
# ---------------------------------------------------------------------------


def test_focus_is_visible(html):
    """A focusable card with outline:none is a keyboard trap you cannot see."""
    assert ":focus-visible" in html, "no visible focus style"
    card = re.search(r"\.card\s*\{(.*?)\}", html, re.S)
    assert card and "outline: none" not in card.group(1), \
        ".card suppresses its own focus ring"


def test_motion_respects_the_reduced_motion_preference(html):
    assert "prefers-reduced-motion" in html


def test_headline_figures_scale_on_small_screens(html):
    """A fixed 58px headline overflowed a phone at seven significant digits."""
    headline = re.search(r"\.headline\s*\{(.*?)\}", html, re.S)
    assert headline and "clamp(" in headline.group(1), \
        "headline font-size does not scale"
