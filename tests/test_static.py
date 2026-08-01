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
def markup(doc):
    """The document with its HTML comments removed.

    Every comment in that file explains a bug the page used to have, and
    several quote the offending prose verbatim -- "broiler chickens with
    nothing marking them as unrelated" is a description of the fix, not a
    violation of it. A check that reads the raw document flags its own
    documentation, which is how a guard teaches people to stop writing
    comments.
    """
    return re.sub(r"<!--.*?-->", "", doc, flags=re.S)


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


def test_no_species_is_named_anywhere_in_the_page(markup, script):
    """The class-level rule behind the scope markers.

    Eight of eleven views answer for one species, and saying WHICH in the page
    is a coverage claim: true when typed, wrong the day a second species fills
    in. Every scope label now comes from an endpoint that read it off its own
    rows, so no species' name should appear in what ships.

    This is the general form of two guards that already exist one bug each:
    the hardcoded floor prose, and the hardcoded country coverage claim. It
    caught real copy when it was written -- "the figures this project holds
    are measured on broiler chickens", in the footprint table's empty state,
    which /api/footprint's own allocation_note was already saying correctly
    one panel above.
    """
    from counting_chicken_wings import db as dbm

    conn = dbm.connect()
    try:
        names = [r["common_name"] for r in conn.execute(
            "SELECT common_name FROM species")]
    finally:
        conn.close()

    shipped = markup + "\n" + script
    offenders = [n for n in names if re.search(re.escape(n), shipped, re.I)]
    assert not offenders, (
        "species named in the page; scope copy must come from the API: "
        f"{offenders}"
    )


def test_the_scope_markers_ship_empty(markup):
    """Both are written by app.js, so both must arrive with nothing in them.

    Text typed between these tags would render before the fetch resolves and
    then be replaced -- which is a flash of a claim nobody checked, and it
    would survive a broken endpoint as the page's last word on the subject.
    """
    for el in ("scope-note", "anchor-note"):
        m = re.search(rf'id="{el}"[^>]*>(.*?)</p>', markup, re.S)
        assert m, f"#{el} is gone; the scope marker was renamed or removed"
        assert not m.group(1).strip(), f"#{el} carries copy in the markup"
        assert "hidden" in m.group(0), \
            f"#{el} is visible before it has anything to say"


def test_the_scope_marker_follows_both_the_view_and_the_product(script):
    """It has to be right on arrival, not one tab behind.

    The bug being prevented is specifically a stale marker: choosing a silk
    product and walking to Trends is the path the page used to take in
    silence, and a marker that only updated on load would be silent again for
    any view already visited (`loaded[v]` means an init does not re-run).
    So the render must be driven by BOTH the navigation and the product
    control, not by the fetch.
    """
    assert re.search(r"function\s+renderScope\s*\(", script), \
        "renderScope is gone; the marker has no writer"
    assert "#scope-note" in script, "nothing writes the scope marker"

    nav = re.search(r"querySelectorAll\('nav button'\).*?\}\);", script, re.S)
    assert nav and "renderScope" in nav.group(0), \
        "switching views does not re-render the scope marker"

    assert re.search(r"addEventListener\('(?:change|input)',\s*renderScope\)",
                     script), \
        "changing the product does not re-render the scope marker"


def test_a_renderable_error_is_actually_rendered(script):
    """The size picker must not go back to hiding what it cannot answer.

    Three of six active species have no size question, `/api/bird-size` 404s
    for them, and the picker's original fix for that was to omit them -- so a
    view claiming to grade "every species" showed three chips. The 404 now
    carries a code and the species, which only helps if the client branches on
    it: an unhandled rejection would blank the panel and leave whichever
    species was showing before, which is worse than the omission was.

    Two halves, both required. The fetch helper has to put the structured body
    on the error at all (`.message` alone collapses it to a sentence -- the
    "[object Object]" shape one bug over), and showSize has to act on it.
    """
    assert re.search(r"err\.detail\s*=", script), \
        "the fetch helper drops the error body, so no caller can act on it"
    assert "no_size_question" in script, \
        "nothing handles the one 404 this view can render"


def test_the_anchor_sentence_comes_from_the_api(script):
    """Which species is the anchor is computed, never typed.

    /api/scope derives it from v_species_coverage and returns null on a tie,
    so the page has to ask rather than assert -- that is what makes the claim
    retire itself when a second species reaches parity.
    """
    assert "/api/scope" in script, "the page does not ask which species is the anchor"
    assert "#anchor-note" in script, "nothing writes the anchor sentence"


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


def test_hidden_attribute_is_not_defeated_by_a_display_rule(html):
    """`hidden` must win over every other `display:` rule in the sheet.

    `.check` and `footer.build` both set `display: flex`, and an author rule
    beats the UA default `[hidden] { display: none }` -- so a checkbox label
    or the build footer carrying the `hidden` attribute stayed visible (the
    footer as a stray horizontal rule from its own border-top) until this
    guard existed. A future `display:` rule on some other hideable element
    would silently reintroduce the same bug without this check.
    """
    guard = re.search(r"\[hidden\]\s*\{([^}]*)\}", html)
    assert guard, "no [hidden] rule in the stylesheet"
    assert "display: none" in guard.group(1) or "display:none" in guard.group(1)
    assert "!important" in guard.group(1), \
        "[hidden] must out-specify author display rules like .check or " \
        "footer.build, or it will be silently defeated again"


# ---------------------------------------------------------------------------
# A view init can run more than once
# ---------------------------------------------------------------------------


def _init_bodies(script):
    """Each `init*` function body, by brace matching.

    A regex cannot find the end of a JS function, and these bodies carry
    nested braces inside template literals on nearly every line. Counting
    braces from the opening one is crude and correct enough for a source file
    we own.
    """
    bodies = {}
    for m in re.finditer(r"(?:async\s+)?function\s+(init\w+)\s*\([^)]*\)\s*\{",
                         script):
        depth, i = 1, m.end()
        while i < len(script) and depth:
            if script[i] == "{":
                depth += 1
            elif script[i] == "}":
                depth -= 1
            i += 1
        bodies[m.group(1)] = script[m.end():i]
    assert bodies, "found no init* functions to check"
    return bodies


def test_view_inits_do_not_add_listeners(script):
    """`init*` runs again on every theme toggle, so it must assign, not add.

    `redrawTheme()` clears `loaded` and rebuilds the visible view, which is
    the correct redraw: trace colours come from the same CSS variables as the
    frame, so restyling in place would leave half a chart following the theme
    and half not. The cost is that every init is re-entrant, and
    `addEventListener` has no idea it has been called before.

    Three toggles left four `change` handlers on each Scientific control, so
    one dropdown change fired four concurrent Monte Carlo runs at up to
    100,000 iterations apiece -- and four `keydown` handlers on `document`, so
    one right-arrow press moved the facts deck four cards. `initCountry` never
    had either bug, because it assigns `.onchange`.

    Listeners that genuinely cannot be assigned -- `{ passive: true }` touch
    handlers, anything on `document` -- belong in a bind-once helper behind a
    guard, which is what `bindFactsGestures` is.
    """
    offenders = sorted(name for name, body in _init_bodies(script).items()
                       if "addEventListener" in body)
    assert not offenders, (
        "these view inits add listeners instead of assigning them, so a "
        f"theme toggle leaves a duplicate behind: {offenders}"
    )


def test_a_resize_redraws_the_visible_charts(script):
    """Plotly sizes itself at draw time and never re-reads its container.

    Measured before this was fixed: at 1280px the mixing chart sat at 700px
    inside an 820px container after a viewport change, and switching tabs away
    and back did not help, because `loaded[v]` meant the view never redrew.
    `responsive: true` in CFG was not covering it on its own.

    The guard is on `Plotly.Plots`, not on `typeof Plotly`, because the
    CDN-failure stub defines `newPlot` and `relayout` and nothing else. An
    unreachable chart CDN has to stay a degraded page -- every figure is in
    the tables and the API regardless -- never a thrown error on every resize.
    """
    assert re.search(r"addEventListener\(\s*'resize'", script), \
        "nothing redraws the charts when the window changes size"
    body = _fn_body(script, "resizeCharts")
    assert "Plotly.Plots.resize" in body, \
        "the resize path does not actually resize any chart"
    assert "Plotly.Plots" in body.split("Plotly.Plots.resize")[0], \
        "resizeCharts calls into Plotly before checking the stub is not in use"


def test_the_variance_panel_ids_exist_on_both_sides_of_the_contract(
        markup, script):
    """The element ids ARE the contract between the markup and `app.js`.

    Rename one on one side and the panel silently never fills in -- no error,
    no blank chart, just a section that quietly stops being about anything.
    Every id this panel writes to is checked in both files.
    """
    for el in ("s-sobol", "s-sobol-verdict", "s-sobol-cost", "s-sobol-notes"):
        assert f'id="{el}"' in markup, f"{el} is missing from the markup"
        assert el in script, f"nothing in the script ever writes to {el}"


def test_the_variance_panel_states_its_own_spread(script):
    """Shares of a variance always fill the axis, so a saturated cascade
    renders as a chart full of confident bars over an answer that cannot
    move. The absolute spread is what stops that reading, and it has to come
    from the response -- a number typed into the markup would be a corpus
    figure bypassing the citation audit, and would go stale besides."""
    body = _fn_body(script, "renderSobol")
    for k in ("sample_lo", "sample_hi", "sd", "mean"):
        assert k in body, f"the verdict line never mentions {k}"
    assert "v.notes" in body, "the computed notes are never rendered"


def _fn_body(script, name):
    m = re.search(rf"function\s+{name}\s*\([^)]*\)\s*\{{", script)
    assert m, f"{name} is gone; the redraw path was renamed or removed"
    depth, i = 1, m.end()
    while i < len(script) and depth:
        if script[i] == "{":
            depth += 1
        elif script[i] == "}":
            depth -= 1
        i += 1
    return script[m.end():i]
