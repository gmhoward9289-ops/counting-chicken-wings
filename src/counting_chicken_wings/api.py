"""FastAPI backend for the web interface.

Every endpoint returning a statistic also returns its citation. That is a
deliberate constraint: it makes it impossible to render a number in the UI
without having the source available to render beside it.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import audit
from . import db as dbm
from . import seasonality as seas
from .model import (
    CONFIDENCE_RANK,
    expected_distinct_general,
    floor_individuals,
    meets_confidence,
    mixing_draw_scale,
    run,
    sensitivity,
    variance_decomposition,
)

STATIC = Path(__file__).parent / "static"

app = FastAPI(
    title="counting-chicken-wings",
    description="How many chickens does it take to make a dozen wings?",
)


def _source_payload(row) -> dict:
    return {
        "slug": row["slug"],
        "title": row["title"],
        "publisher": row["publisher"],
        "url": row["url"],
        "published_on": row["published_on"],
        "source_type": row["source_type"],
        # Why a source with no loaded figure is kept: 'corroboration',
        # 'context', or null. Lets the Sources view say "held" instead of
        # reporting "0 figures" as if it were an accident.
        "held_reason": row["held_reason"],
        "notes": row["notes"],
    }


# ---------------------------------------------------------------------------
# Scope: which species a view is actually about
#
# Twelve products sit in one dropdown as equals, and eight of the eleven views
# answer for exactly one of them. Picking "Silk dress" and opening Trends used
# to show broiler chickens with nothing saying so.
#
# The fix has to survive the corpus growing, so no view names a species. Each
# scoped endpoint reports the species ITS OWN QUERY reached, built from the
# same rows it is returning -- the day /api/trends carries a second species,
# its scope says two without anyone remembering to update it. This is the same
# rule that put `coverage` on /api/footprint: prose about coverage rots, so
# coverage is data.
# ---------------------------------------------------------------------------


def _scope(conn, species_slugs, *, label: str | None = None) -> dict:
    """A view's scope, named from the `species` table rather than in prose.

    `label` overrides the printed name where the scope is genuinely broader
    than one species -- the fact deck is per DOMAIN, and "Poultry" is what it
    covers, even though the species behind it are a broiler and a laying hen.
    Callers still get `species` for the mismatch check either way.
    """
    slugs = [s for s in species_slugs if s]
    rows = []
    if slugs:
        marks = ",".join("?" * len(slugs))
        rows = conn.execute(
            f"""SELECT slug, common_name, individual_noun, individual_plural
                FROM species WHERE slug IN ({marks}) ORDER BY id""",
            tuple(slugs),
        ).fetchall()
    names = [r["common_name"] for r in rows]
    return {
        "species": [dict(r) for r in rows],
        # Ready to print. `label` when the caller has a truer word for the
        # scope; otherwise the species' own names out of the corpus.
        "label": label or (" and ".join(names) if names else None),
    }


# What each `v_species_coverage` flag is called in English. The columns are
# the source of truth for WHICH dimensions exist -- this only names them, and
# a column with no entry here is a schema change that forgot its label, which
# is what test_scope_labels_every_dimension_the_view_carries checks.
_DIMENSION_LABELS = {
    "loss_chain": "a sourced supply chain",
    "products": "products in the calculator",
    "size_axis": "a size question",
    "regional_weight": "region-by-region weights",
    "seasonality": "a month-by-month series",
    "trends": "a year-over-year series",
    "footprint": "a resource footprint",
    "nutrition": "nutrition figures",
}

# Columns of `v_species_coverage` that name the species rather than measure it.
_SPECIES_COLUMNS = ("id", "slug", "common_name", "individual_noun",
                    "individual_plural", "domain")


def _borrow_note(product_label: str, product_species: str,
                 scope_species: str) -> str:
    """What a view scoped to one species owes a reader who asked about another.

    Composed HERE rather than in the page, and the reason is the constraint
    issue #110 states outright: scope copy must be app copy or come from the
    API. This is the second, and it is the better one -- every noun is the
    corpus' own, so a renamed species renames the sentence.

    The pattern is deliberately the one `/api/footprint.allocation_note`
    already uses for the same situation one panel down ("...they are not this
    product's to borrow"). Reusing the pattern rather than that string itself
    is the one liberty taken, and it is forced: the footprint sentence is
    written for its own panel -- "there is nothing HERE to allocate", "the
    economic figures BELOW" -- and panel-relative deixis is exactly what does
    not survive being hoisted to the tab level.
    """
    return (f"{product_label} is a {product_species} product, and nothing "
            f"measured on {scope_species} is its to borrow.")


@app.get("/api/scope")
def scope(product: str | None = None):
    """Which species the corpus answers, in how many dimensions, and the anchor.

    The page's strapline needs to say that one species is the anchor dataset
    and the rest are extensions. Written into the page, that sentence is a
    coverage claim, and coverage claims rot -- an earlier draft of this project
    hardcoded "Israel cannot answer how many chickens", which was true when
    typed and false hours later.

    So the anchor is COMPUTED, from `v_species_coverage`: the active species
    present in the most dimensions. A tie returns `anchor: null` and the page
    prints nothing rather than picking one -- the day a second species reaches
    parity, the claim retires itself instead of becoming a lie.

    `product` asks the second question the page has: given that this product is
    selected, what should a view scoped to some OTHER species say? One
    pre-composed sentence per species comes back in `selected.borrow_notes`, so
    switching tabs costs no request and the page never composes the sentence
    itself. See `_borrow_note`.
    """
    conn = dbm.connect()
    try:
        rows = conn.execute(
            "SELECT * FROM v_species_coverage ORDER BY id"
        ).fetchall()
        keys = [k for k in (rows[0].keys() if rows else [])
                if k not in _SPECIES_COLUMNS]

        species = []
        for r in rows:
            dims = {k: bool(r[k]) for k in keys}
            species.append({
                "slug": r["slug"],
                "common_name": r["common_name"],
                "individual_noun": r["individual_noun"],
                "individual_plural": r["individual_plural"],
                "domain": r["domain"],
                "dimensions": dims,
                "depth": sum(dims.values()),
            })

        anchor = None
        if species:
            depths = sorted((s["depth"] for s in species), reverse=True)
            # Strictly deepest, or nothing. Two species at the same depth is
            # not an anchor, and a tie-break would invent one.
            if len(depths) == 1 or depths[0] > depths[1]:
                anchor = max(species, key=lambda s: s["depth"])

        selected = None
        if product is not None:
            try:
                prod = dbm.get_product(conn, product)
            except KeyError:
                raise HTTPException(404, f"unknown product: {product}")
            mine = next((s for s in species
                         if s["slug"] == prod["species_slug"]), None)
            selected = {
                "slug": prod["slug"],
                "label": prod["label"],
                "species": prod["species_slug"],
                "common_name": mine["common_name"] if mine else None,
                # One sentence per species this product is NOT. Keyed by slug
                # so a client holding a view's scope can look its own up
                # without asking again on every tab switch, and so a species
                # that gains a view needs no new field.
                "borrow_notes": {
                    s["slug"]: _borrow_note(
                        prod["label"],
                        mine["common_name"] if mine else prod["species_slug"],
                        s["common_name"])
                    for s in species if s["slug"] != prod["species_slug"]
                },
            }

        return {
            "anchor": anchor,
            "species": species,
            "selected": selected,
            "dimensions": [
                {"key": k, "label": _DIMENSION_LABELS.get(k, k),
                 "species": [s["slug"] for s in species if s["dimensions"][k]]}
                for k in keys
            ],
        }
    finally:
        conn.close()


@app.get("/healthz")
def healthz():
    """Liveness check, deliberately cheap: no database, no imports.

    Exists to be pinged. Render's free tier spins the service down after
    idling, and the next visitor then waits ~20s for a cold start on the
    HTML document itself -- which no amount of client-side loading UI can
    disguise, because the browser has no page yet. An external cron hitting
    this endpoint every few minutes is the only thing that actually fixes it
    short of paying for an always-on instance.
    """
    return {"ok": True}


@app.get("/api/version")
def version():
    """What is actually deployed here.

    Exists because this was not answerable from outside. Recent commits added
    schema and data without new endpoints, so feature-probing could not
    distinguish a current build from one several commits stale -- and the
    deploy tracks `master` rather than a tag, so the deployed code is whatever
    master last was, not necessarily a release.

    THE COMMIT IS READ FROM A HOST-NEUTRAL VARIABLE FIRST. It used to read
    only RENDER_GIT_COMMIT, which Render injects at build time. Moving to a
    self-hosted box made that variable nobody's job to set, so the endpoint
    answered `null` to the exact question it was built to answer -- and
    "what am I looking at?" is not a question this project should shrug at.

    GIT_COMMIT is what the deploy sets now. RENDER_GIT_COMMIT stays as a
    fallback rather than being deleted, because the Dockerfile is deliberately
    provider-agnostic and someone may still run this on Render.

    Absent both, the value is None, which is itself informative: it means
    nobody told this process what it is, so it is almost certainly local.
    """
    import os
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as pkg_version

    try:
        pkg = pkg_version("counting-chicken-wings")
    except PackageNotFoundError:          # running from source, not installed
        pkg = None

    sha = os.environ.get("GIT_COMMIT") or os.environ.get("RENDER_GIT_COMMIT")
    conn = dbm.connect()
    try:
        counts = {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("source", "fact", "loss_factor", "product",
                      "quality_defect", "regional_size_stat")
        }
        # Row counts are the practical way to tell a data-only change apart
        # from a code change, since data ships in the same push.
        tables = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "package_version": pkg,
        "git_commit": sha,
        "git_commit_short": sha[:7] if sha else None,
        # Which host is serving this. Named `service` rather than
        # `render_service` since 2026-07-30, when the deploy moved to a
        # self-hosted box -- a field called `render_service` reporting a
        # Hetzner container is the sort of quiet wrongness this project
        # spends its time removing. The old key is kept alongside so any
        # existing caller keeps working.
        "service": (os.environ.get("SERVICE_NAME")
                    or os.environ.get("RENDER_SERVICE_NAME")),
        "render_service": os.environ.get("RENDER_SERVICE_NAME"),
        "branch": (os.environ.get("GIT_BRANCH")
                   or os.environ.get("RENDER_GIT_BRANCH")),
        "table_count": tables,
        "row_counts": counts,
    }


@app.get("/api/brand")
def brand():
    """ASCII identity, served rather than duplicated in the HTML.

    The CLI banner and the web header render the same art from the same
    module, so the two surfaces cannot drift apart.
    """
    from .brand import CHICKEN, TAGLINE, TITLE, WING, art
    return {
        "title": TITLE,
        "tagline": TAGLINE,
        "chicken": art("chicken"),
        "wing": art("wing"),
        "chicken_raw": CHICKEN,
        "wing_raw": WING,
    }


def _resolve_chain(conn, prod, chain: str | None) -> str:
    """The route to run this product through, checked against its species.

    Every endpoint that takes a `chain` needs the same three answers, and they
    were previously spelled out once, loosely, in `/api/calculate` and not at
    all in `/api/scientific`: `?chain=total_nonsense` came back 200 with
    `distinct: 6.0` -- the floor, because no mixing stages were found and none
    were expected to be. A silently unmixed answer is the worst shape this
    project's failures can take, since the number looks like a result.

    1. No chain named: the species' own default. Never a global one --
       `default_supply_chain` refuses that outright, for the reason its
       docstring gives.
    2. A chain that does not exist: 404.
    3. A chain belonging to ANOTHER species: 422, not a silent answer. A wing
       question routed through `commodity_syrup` moved the answer by up to six
       chickens and produced a confident trace of a maple sugarhouse. The
       schema already records which species a route belongs to, precisely so
       this is answerable; nothing was asking.

    A route with a NULL species applies to any of them, which is what the
    column means, so it passes.
    """
    if not chain:
        return dbm.default_supply_chain(conn, prod["species_slug"])

    row = conn.execute(
        """SELECT sc.slug, s.slug AS species_slug
           FROM supply_chain sc
           LEFT JOIN species s ON s.id = sc.species_id
           WHERE sc.slug = ?""",
        (chain,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"unknown supply chain: {chain}")
    if row["species_slug"] and row["species_slug"] != prod["species_slug"]:
        raise HTTPException(
            422,
            f"supply chain '{chain}' belongs to {row['species_slug']}, "
            f"and {prod['label']} comes from {prod['species_slug']}",
        )
    return chain


@app.get("/api/calculate")
def calculate(
    count: float = Query(12, gt=0, le=100000),
    product: str = "whole_wing",
    chain: str | None = None,
    pieces: bool = False,
    include_mortality: bool = False,
    iterations: int = Query(0, ge=0, le=200000),
    window_days: float | None = Query(None, gt=0, le=3650),
):
    """The main calculation, with a full per-stage audit trail.

    `window_days` applies only to recurring products such as eggs, where the
    per-individual yield is a rate and means nothing without a window. Left
    unset it comes from the product: one day for eggs, because a hen lays at
    most one egg a day and twelve same-day eggs came from twelve different
    hens; a whole 45-day season for maple syrup, because a tree is tapped for
    a spring rather than an afternoon. Ignored for wings, which need no clock.

    Payload is built by ``tools.wings_calculate`` so HTTP and MCP cannot drift.
    """
    from . import tools as tools_mod

    body = tools_mod.wings_calculate(
        count=count,
        product=product,
        chain=chain,
        pieces=pieces,
        include_mortality=include_mortality,
        iterations=iterations,
        window_days=window_days,
    )
    err = body.get("error")
    if err:
        # Match prior status codes: unknown product / chain → 404; cross-species
        # chain → 422; bad window / other ValueError → 400.
        lower = err.lower()
        if lower.startswith("unknown product") or lower.startswith(
            "unknown supply chain"
        ):
            raise HTTPException(404, err)
        if "belongs to" in lower and "comes from" in lower:
            raise HTTPException(422, err)
        raise HTTPException(400, err)
    body.pop("package_version", None)
    return body


def _histogram(values: list[float], bins: int = 40) -> dict:
    """Bin samples for a chart. Returned as counts plus bin centres."""
    if not values:
        return {"centres": [], "counts": [], "width": 0.0}
    lo, hi = values[0], values[-1]
    if hi <= lo:
        return {"centres": [lo], "counts": [len(values)], "width": 0.0}
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        i = min(bins - 1, int((v - lo) / width))
        counts[i] += 1
    centres = [lo + width * (i + 0.5) for i in range(bins)]
    return {"centres": centres, "counts": counts, "width": width}


@app.get("/api/scientific")
def scientific(
    count: float = Query(12, gt=0, le=100000),
    product: str = "whole_wing",
    chain: str | None = None,
    pieces: bool = False,
    include_mortality: bool = False,
    iterations: int = Query(20000, ge=100, le=200000),
    confidence_level: float = Query(0.90, gt=0.0, lt=1.0),
    min_confidence: str | None = None,
    seed: int | None = 12345,
):
    """Full uncertainty analysis: Monte Carlo, tornado, and evidence mix.

    `confidence_level` sets the reported interval width. `min_confidence`
    drops loss stages weaker than the given evidence grade, so you can see
    how much of the answer depends on figures we could not source.
    """
    if min_confidence and min_confidence not in CONFIDENCE_RANK:
        raise HTTPException(
            422, f"min_confidence must be one of {list(CONFIDENCE_RANK)}"
        )

    conn = dbm.connect()
    try:
        try:
            prod = dbm.get_product(conn, product)
        except KeyError:
            raise HTTPException(404, f"unknown product: {product}")

        units = count
        if pieces:
            seg = conn.execute(
                """SELECT COUNT(*) FROM product_segment
                   WHERE product_id = ? AND sold_as_product = 1""",
                (prod["id"],),
            ).fetchone()[0] or 1
            units = count / seg

        chain = _resolve_chain(conn, prod, chain)
        upi = prod["units_per_individual_mode"]
        loss = dbm.load_loss_stages(
            conn, prod["species_slug"], prod["slug"],
            include_optional=include_mortality,
            chain_slug=chain,
        )
        mixing = dbm.load_mixing_stages(conn, chain)

        res = run(
            units_requested=units, units_per_individual=upi,
            loss_stages=loss, mixing_stages=mixing,
            iterations=iterations, seed=seed,
            confidence_level=confidence_level,
            min_confidence=min_confidence, keep_samples=True,
            # Derived inside run() from the figures -- see unit_is_aggregate.
            anatomical=bool(prod["is_anatomical_constant"]),
            floor_source=dbm.product_source_slug(conn, prod["slug"]),
            # From the corpus -- see model.MixingParams.
            params=dbm.load_mixing_params(conn),
            # Lets the Monte Carlo loop resample these too (#98), not just
            # pool sizes.
            param_bands=dbm.load_mixing_param_bands(conn),
            correlated_groups=dbm.load_correlated_groups(
                conn, prod["species_slug"]),
            mixing_subunits_per_unit=prod["mixing_subunits_per_unit"],
        )

        kept = [s for s in loss
                if meets_confidence(s.confidence, min_confidence)]
        tornado = sensitivity(units, upi, kept)

        # How much of the answer rests on each evidence grade. Counted over
        # stages that can actually move the count -- mass-only stages are
        # excluded because their evidence quality is irrelevant to it.
        mix: dict[str, int] = {}
        for s in kept:
            if s.applies_to in ("individual", "product"):
                mix[s.confidence] = mix.get(s.confidence, 0) + 1

        # Waterfall: floor, then each count-affecting stage's contribution.
        waterfall, running = [], res.floor
        for s in sorted(kept, key=lambda x: x.sequence):
            if s.applies_to not in ("individual", "product"):
                continue
            after = running / s.survive_mode
            waterfall.append({
                "label": s.label, "slug": s.slug,
                "from": running, "to": after, "delta": after - running,
                "confidence": s.confidence,
            })
            running = after

        return {
            "question": {
                "count": count, "units": units, "chain": chain,
                "product": prod["label"],
                "individual_plural": prod["individual_plural"],
                "iterations": iterations,
                "confidence_level": confidence_level,
                "min_confidence": min_confidence,
                "seed": seed,
            },
            "answer": {
                "floor": res.floor,
                "ceiling": res.distinct_ceiling,   # see /api/calculate
                "required": res.required,
                "required_estimator": res.required_estimator,
                "required_lo": res.required_lo,
                "required_hi": res.required_hi,
                "distinct": res.distinct_mean,
                "distinct_lo": res.distinct_lo,
                "distinct_hi": res.distinct_hi,
                "excluded_stages": res.excluded_stages,
            },
            "required_hist": _histogram(res.required_samples),
            "distinct_hist": _histogram(res.distinct_samples),
            "tornado": [
                {
                    "slug": t.slug, "label": t.label,
                    "applies_to": t.applies_to, "confidence": t.confidence,
                    "low": t.low_result, "high": t.high_result,
                    "swing": t.swing, "share": t.share,
                }
                for t in tornado
            ],
            "waterfall": waterfall,
            "evidence_mix": mix,
        }
    finally:
        conn.close()


@app.get("/api/variance")
def variance(
    count: float = Query(12, gt=0, le=100000),
    product: str = "whole_wing",
    chain: str | None = None,
    pieces: bool = False,
    include_mortality: bool = False,
    samples: int = Query(1024, ge=64, le=16384),
    bootstrap: int = Query(200, ge=0, le=2000),
    confidence_level: float = Query(0.90, gt=0.0, lt=1.0),
    seed: int | None = 12345,
):
    """Which mixing input drives the uncertainty in `distinct`?

    A DIFFERENT QUESTION FROM `/api/scientific`'s TORNADO, and served
    separately for two reasons. It is about `distinct` rather than
    `required`, by a variance-based method rather than one-at-a-time -- see
    `model.sensitivity`'s docstring for why the two outputs need different
    methods. And it costs a couple of seconds of its own, so bolting it onto
    an endpoint that already runs 20,000 Monte Carlo iterations would make
    every scientific-mode load pay for both in series. Fetched alongside,
    the wall clock is the slower of the two rather than the sum.

    Read `sd` before the shares. On a saturated cascade the indices still
    sum to about one while the variance they are dividing is 2e-5 of an
    individual; the shares say who owns what little is left, not that the
    answer is uncertain. `notes` says which case you are in.
    """
    conn = dbm.connect()
    try:
        try:
            prod = dbm.get_product(conn, product)
        except KeyError:
            raise HTTPException(404, f"unknown product: {product}")

        units = count
        if pieces:
            seg = conn.execute(
                """SELECT COUNT(*) FROM product_segment
                   WHERE product_id = ? AND sold_as_product = 1""",
                (prod["id"],),
            ).fetchone()[0] or 1
            units = count / seg

        chain = _resolve_chain(conn, prod, chain)
        upi = prod["units_per_individual_mode"]
        loss = dbm.load_loss_stages(
            conn, prod["species_slug"], prod["slug"],
            include_optional=include_mortality,
            chain_slug=chain,
        )
        mixing = dbm.load_mixing_stages(conn, chain)
        params = dbm.load_mixing_params(conn)

        # A deterministic pass purely to resolve the question. For an
        # aggregate unit -- a gram of saffron -- the cascade is asked in
        # individual-shares rather than in grams, and the decomposition has
        # to be asked in the same currency or it silently analyses a
        # different question than the histogram it is rendered beside.
        # `run` owns that derivation and reports what it used;
        # `test_aggregate_units.py` forbids this module deciding it again.
        res = run(
            units_requested=units, units_per_individual=upi,
            loss_stages=loss, mixing_stages=mixing,
            anatomical=bool(prod["is_anatomical_constant"]),
            floor_source=dbm.product_source_slug(conn, prod["slug"]),
            params=params,
            mixing_subunits_per_unit=prod["mixing_subunits_per_unit"],
        )

        dec = variance_decomposition(
            mixing_stages=mixing,
            param_bands=dbm.load_mixing_param_bands(conn),
            units_requested=int(res.draw_units),
            units_per_individual=res.draw_upi,
            samples=samples, seed=seed, bootstrap=bootstrap,
            confidence_level=confidence_level,
            base_params=params,
        )

        return {
            "question": {
                "count": count, "units": units, "chain": chain,
                "product": prod["label"],
                "individual_plural": prod["individual_plural"],
                "drawn_units": res.draw_units,
                "drawn_upi": res.draw_upi,
            },
            "output": dec.output,
            "mean": dec.mean,
            "variance": dec.variance,
            "sd": dec.sd,
            "sample_lo": dec.sample_lo,
            "sample_hi": dec.sample_hi,
            "samples": dec.samples,
            "evaluations": dec.evaluations,
            "bootstrap": dec.bootstrap,
            "confidence_level": dec.confidence_level,
            "seed": dec.seed,
            "sum_first_order": dec.sum_first_order,
            "sum_total_order": dec.sum_total_order,
            "notes": dec.notes,
            "shares": [
                {
                    "slug": s.slug, "label": s.label, "kind": s.kind,
                    "confidence": s.confidence,
                    "first_order": s.first_order,
                    "first_lo": s.first_lo, "first_hi": s.first_hi,
                    "total_order": s.total_order,
                    "total_lo": s.total_lo, "total_hi": s.total_hi,
                    "degenerate": s.degenerate, "inert": s.inert,
                }
                for s in dec.shares
            ],
        }
    finally:
        conn.close()


@app.get("/api/mixing-curve")
def mixing_curve(
    count: float = Query(12, gt=0, le=100000),
    product: str = "whole_wing",
    window_days: float | None = Query(None, gt=0, le=3650),
):
    """The distinct-individuals curve as the pool grows, for any product.

    Powers the simulator: drag the pool from a handful of individuals to
    200,000 and watch the count climb from the floor toward the ceiling.

    The curve itself stays the bare hypergeometric shape it has always
    been -- no separation efficiency, no clustering, none of the mixing
    cascade's other stages -- because the shape is the finding: it flattens
    above a few hundred individuals and never recovers. What varies by
    product is the SCALE the draw happens at, and that has to match the
    real headline answer or the two disagree in front of the same reader.
    `mixing_draw_scale` is the same re-expression `run()` uses for the
    headline figure (individual-shares for a blended unit like a gram of
    saffron, mixing sub-units for a homogenate like a ground beef patty) --
    duplicating that logic here once produced exactly the mismatch this
    fixes -- see .changes/beef-patty-mixing-granularity.md: a patty's curve
    implied "about 1 animal" while its headline answer said "most of the
    batch".
    """
    conn = dbm.connect()
    try:
        try:
            prod = dbm.get_product(conn, product)
        except KeyError:
            raise HTTPException(404, f"unknown product: {product}")

        try:
            recurring = dbm.make_recurring(prod, window_days)
        except ValueError as e:
            raise HTTPException(400, str(e))

        units_per_individual = (
            recurring.units_per_individual if recurring is not None
            else prod["units_per_individual_mode"]
        )
        floor = floor_individuals(count, units_per_individual)
        # Whether the unit is an aggregate is derived inside the model, from
        # `recurring` -- `test_aggregate_units.py` forbids this module
        # deciding it again.
        draw, upi, drawn_label = mixing_draw_scale(
            count, units_per_individual, floor,
            recurring=recurring,
            mixing_subunits_per_unit=prod["mixing_subunits_per_unit"],
        )

        pools = []
        b = max(1, int(draw / upi))
        while b <= 200000:
            pools.append(b)
            b = int(b * 1.35) + 1
        if 200000 not in pools:
            pools.append(200000)

        points = []
        for pool in pools:
            container = int(pool * upi)
            if container < draw:
                continue
            points.append({
                "pool": pool,
                # The general formula, not the wings-only two-per-individual
                # special case: `pool` individuals contributed `container`
                # units between them, whatever this product's anatomy says
                # that ratio is.
                "distinct": expected_distinct_general(
                    int(draw), container, pool),
            })

        return {
            "product": prod["label"],
            "individual_noun": prod["individual_noun"],
            "individual_plural": prod["individual_plural"],
            "count": count,
            "unit_name": prod["unit_name"],
            "drawn_label": drawn_label,
            "draw": draw,
            "floor": draw / upi,
            "ceiling": draw,
            "points": points,
            "note": (
                "Each individual contributes all of its units to the pool, "
                "so this is the most conservative case. Note how fast the "
                "curve flattens: past a few hundred individuals the answer "
                "stops depending on the pool size at all, which is why "
                "every commodity-scale route lands in the same place."
            ),
        }
    finally:
        conn.close()


@app.get("/api/states")
def states(year: int | None = None):
    """Average live weight by state, with production volume where reported.

    `year` defaults to the most recent year with data rather than a literal
    constant -- a hardcoded year renders an empty map and a header-only table
    with no explanation the moment the corpus rolls past it. Absent any data
    at all, or given an explicit year with none, the response says so in
    `message` rather than leaving the caller to infer it from an empty list.
    """
    conn = dbm.connect()
    try:
        explicit_year = year is not None
        if year is None:
            year = dbm.latest_broiler_size_year(conn)

        programs = conn.execute(
            """SELECT slug, label, size_lo, size_hi, typical_market
               FROM production_program ORDER BY size_lo"""
        ).fetchall()

        def program_for(w):
            for p in programs:
                if p["size_lo"] <= w <= p["size_hi"]:
                    return p["label"]
            return None

        rows = []
        if year is not None:
            rows = conn.execute(
                """SELECT r.region, r.avg_size, r.size_unit, r.volume,
                          r.volume_unit, s.slug AS source_slug
                   FROM v_broiler_size_stat r
                   JOIN source s ON s.id = r.source_id
                   WHERE r.year = ? AND r.month IS NULL
                   ORDER BY r.avg_size DESC""",
                (year,),
            ).fetchall()

        message = None
        if year is None:
            message = "No state-level size data is loaded yet."
        elif not rows:
            message = (
                f"No state-level size data for {year}."
                if explicit_year else
                f"No state-level size data for {year}, the most recent year "
                "loaded."
            )

        # Read back off the rows this call is returning, not asserted. The
        # underlying view is broilers today; the day it widens, so does this,
        # with nobody having to remember.
        scoped = conn.execute(
            """SELECT DISTINCT sp.slug
               FROM v_broiler_size_stat r
               JOIN species sp ON sp.id = r.species_id
               WHERE r.year = ? AND r.month IS NULL""",
            (year,),
        ).fetchall() if year is not None else []

        # Census of Agriculture: every state, five-yearly, sales rather than
        # slaughter. Reported alongside the annual survey, never merged into
        # it -- regional_census_stat.sales_head and v_broiler_size_stat.volume
        # are different USDA programmes measuring different things, and
        # summing or averaging them together would claim a false equivalence
        # (see the comment above regional_census_stat in schema.sql).
        census_rows = conn.execute(
            """SELECT c.region, c.census_year, c.sales_head, c.operations,
                      c.inventory, s.slug AS source_slug
               FROM v_broiler_census_stat c
               JOIN source s ON s.id = c.source_id
               ORDER BY c.region"""
        ).fetchall()

        census_scoped = conn.execute(
            """SELECT DISTINCT sp.slug
               FROM v_broiler_census_stat c
               JOIN species sp ON sp.id = c.species_id"""
        ).fetchall()

        # A state the census enumerates but the requested year's survey does
        # not -- presence, with no comparable weight or volume figure to show
        # for it. Computed against the SURVEY YEAR actually being served, not
        # against every year the survey has ever covered, so this stays right
        # if a caller asks for an older `year`.
        survey_regions = {r["region"] for r in rows}
        census_year = census_rows[0]["census_year"] if census_rows else None

        # The Production and Value summary's own multi-state aggregates: real
        # published figures for exactly the states the survey will not name.
        # Served at the aggregate table's own latest year rather than the
        # survey year requested, because the two publications cover different
        # periods and forcing them to share a year would silently drop these
        # rows the moment their editions drift apart.
        agg_year = conn.execute(
            "SELECT MAX(year) FROM regional_production_aggregate"
        ).fetchone()[0]
        agg_rows = conn.execute(
            """SELECT a.label, a.year, a.members, a.head_thousands,
                      a.live_weight_klb, a.value_kusd,
                      a.derived_live_weight_lb, s.slug AS source_slug
               FROM regional_production_aggregate a
               JOIN source s ON s.id = a.source_id
               WHERE a.year = ?
               ORDER BY a.label""",
            (agg_year,),
        ).fetchall() if agg_year is not None else []

        return {
            "year": year,
            "message": message,
            "scope": _scope(conn, [r["slug"] for r in scoped]),
            "regions": [
                {
                    "region": r["region"],
                    "avg_size": r["avg_size"],
                    "size_unit": r["size_unit"],
                    "volume": r["volume"],
                    "volume_unit": r["volume_unit"],
                    "program": program_for(r["avg_size"]),
                    "source": r["source_slug"],
                }
                for r in rows
            ],
            "programs": [dict(p) for p in programs],
            # `derived_live_weight_lb` is arithmetic on the published head
            # and pounds -- a weight the source itself never printed, so it
            # travels at `derived` grade and the page must say so.
            "production_aggregates": {
                "year": agg_year,
                "grade": "derived",
                "rows": [
                    {
                        "label": a["label"],
                        "members": a["members"].split(", "),
                        "head_thousands": a["head_thousands"],
                        "live_weight_klb": a["live_weight_klb"],
                        "value_kusd": a["value_kusd"],
                        "derived_live_weight_lb": a["derived_live_weight_lb"],
                        "source": a["source_slug"],
                    }
                    for a in agg_rows
                ],
            },
            "census": {
                "census_year": census_year,
                "scope": _scope(conn, [r["slug"] for r in census_scoped]),
                "regions": [
                    {
                        "region": c["region"],
                        "sales_head": c["sales_head"],
                        "operations": c["operations"],
                        "inventory": c["inventory"],
                        "source": c["source_slug"],
                        "presence_only": c["region"] not in survey_regions,
                    }
                    for c in census_rows
                ],
            },
        }
    finally:
        conn.close()


@app.get("/api/countries")
def countries():
    """What each country can actually answer, not just which countries exist.

    Deliberately shaped as coverage rather than as a list of names. A selector
    built from names alone invites the comparison this project must not make:
    the US has enumerated head slaughtered, 50 states and a sourced loss
    chain, and Israel has one of the longest output series anywhere -- CBS
    tonnage, value and districts -- with its bird count carried at industry
    grade rather than as a government enumeration. A caller that can see
    `answers` cannot accidentally imply parity, and one that only saw ISO
    codes would have to guess.
    """
    conn = dbm.connect()
    try:
        rows = conn.execute(
            """SELECT c.iso3, c.name, c.native_mass_unit, c.native_currency,
                      c.population, c.population_year,
                      (SELECT COUNT(*) FROM slaughter_stat_year s
                        WHERE s.country_id = c.id
                          AND s.head_slaughtered IS NOT NULL) AS head_years,
                      -- A head count may also arrive as an output_stat_year
                      -- row at a weaker grade, which is how Israel has one at
                      -- all. Report the best grade available, never a bare
                      -- yes: "we have a bird count" means something different
                      -- when a federal agency enumerated it than when a trade
                      -- association secretary said it in an interview.
                      (SELECT o.confidence FROM output_stat_year o
                        WHERE o.country_id = c.id
                          AND o.measure = 'head_slaughtered'
                        ORDER BY CASE o.confidence
                                   WHEN 'measured' THEN 1 WHEN 'derived' THEN 2
                                   WHEN 'study' THEN 3 WHEN 'industry' THEN 4
                                   ELSE 5 END
                        LIMIT 1) AS head_grade,
                      -- The view, not the shared table: regional_size_stat
                      -- holds broiler and layer rows together, and reading it
                      -- raw is what the egg work forbade for that reason.
                      (SELECT COUNT(DISTINCT region) FROM v_broiler_size_stat r
                        WHERE r.country_id = c.id) AS size_regions,
                      -- Leaves only. Israel nests councils inside districts
                      -- inside a grand total, and counting every level would
                      -- claim 55 Israeli regions against 23 US states.
                      (SELECT COUNT(DISTINCT region) FROM output_stat_year o
                        WHERE o.country_id = c.id
                          AND o.region IS NOT NULL
                          AND COALESCE(o.region_level, 'council')
                              NOT IN ('total','district')) AS output_regions,
                      (SELECT COUNT(*) FROM output_stat_year o
                        WHERE o.country_id = c.id
                          AND o.region IS NULL) AS national_rows
               FROM country c ORDER BY c.iso3"""
        ).fetchall()

        out = []
        for r in rows:
            subnational = max(r["size_regions"], r["output_regions"])
            out.append({
                "iso3": r["iso3"],
                "name": r["name"],
                "native_mass_unit": r["native_mass_unit"],
                "native_currency": r["native_currency"],
                # NULL until sourced. Per-capita is the comparison an audience
                # asks for first and it is the one figure here with no
                # citation, so the API says absent rather than guessing.
                "population": r["population"],
                "population_year": r["population_year"],
                "answers": {
                    # The count question needs birds, not tonnes.
                    "head_slaughtered": bool(
                        r["head_years"] or r["head_grade"]
                    ),
                    # ...and the grade is what a caller needs to decide whether
                    # to show the count answer, so it travels with the boolean
                    # rather than being looked up separately.
                    "head_slaughtered_grade": (
                        "measured" if r["head_years"] else r["head_grade"]
                    ),
                    # True only if the count survives a government-only view.
                    # This is the "both options" split made queryable: Israel
                    # answers the count question on industry evidence and not
                    # on measured evidence, and a caller can render either.
                    "head_slaughtered_measured": bool(
                        r["head_years"]
                        or r["head_grade"] in ("measured", "derived")
                    ),
                    "subnational": subnational > 0,
                    "national_output": r["national_rows"] > 0,
                    "per_capita": r["population"] is not None,
                },
                "subnational_regions": subnational,
                "has_data": bool(
                    r["head_years"] or subnational or r["national_rows"]
                ),
            })

        # Every `answers` flag above is counted off three tables, and all three
        # are per-species. The view compares countries, so the species it is
        # comparing them ON is the thing a reader cannot see and has to be
        # told -- a maple-syrup question opened here got broiler coverage with
        # nothing marking it. Read off the same rows rather than asserted.
        scoped = conn.execute(
            """SELECT sp.slug FROM species sp
               WHERE sp.id IN (SELECT species_id FROM slaughter_stat_year
                               UNION SELECT species_id FROM output_stat_year
                               UNION SELECT species_id FROM v_broiler_size_stat)
               ORDER BY sp.id"""
        ).fetchall()
        return {
            "scope": _scope(conn, [r["slug"] for r in scoped]),
            "countries": out,
        }
    finally:
        conn.close()


@app.get("/api/output/{iso3}")
def output(
    iso3: str,
    species: str = "broiler",
    # Anchored: an unanchored alternation only has to match SOMEWHERE in the
    # string, so "xxmeasuredxx" validated as if it were "measured".
    min_confidence: str | None = Query(
        None, pattern=f"^(?:{'|'.join(CONFIDENCE_RANK)})$"
    ),
):
    """Output, value and inventory for one country, in its own units.

    Units are returned per row and nothing is converted. Israel reports
    kilograms and shekels against the project's pounds and dollars, and a
    comparison that forgets is wrong by 2.2x while still looking plausible --
    so the conversion is the caller's explicit decision, never a default.

    `min_confidence` is how a reader chooses between the two honest pictures of
    Israel rather than having one chosen for them:

      min_confidence=measured  government figures only. Tonnage, value, a
                               year-end flock and districts -- the measures
                               CBS publishes; the industry-reported bird
                               count drops out with the filter.
      (omitted)                everything, including the industry head count
                               of ~260 million birds a year from a named trade
                               official. The count question becomes answerable
                               at industry grade.

    `excluded` names what the filter dropped, because a filtered answer that
    does not say what it filtered is just a different number.
    """
    conn = dbm.connect()
    try:
        country = conn.execute(
            "SELECT id, iso3, name, native_mass_unit, native_currency "
            "FROM country WHERE iso3 = ? COLLATE NOCASE", (iso3,)
        ).fetchone()
        if country is None:
            raise HTTPException(404, f"unknown country {iso3!r}")

        rows = conn.execute(
            """SELECT o.region, o.region_level, o.year, o.measure, o.value,
                      o.unit, o.confidence, o.provisional, o.suppressed,
                      o.notes,
                      s.slug AS source_slug
               FROM output_stat_year o
               JOIN source s ON s.id = o.source_id
               JOIN species sp ON sp.id = o.species_id
               WHERE o.country_id = ? AND sp.slug = ?
               ORDER BY o.measure, o.year DESC, o.value DESC""",
            (country["id"], species),
        ).fetchall()
        if not rows:
            raise HTTPException(
                404, f"no output data for {country['iso3']} / {species}"
            )

        kept, excluded = [], []
        for r in rows:
            (kept if meets_confidence(r["confidence"], min_confidence)
             else excluded).append(dict(r))

        national = [r for r in kept if r["region"] is None]
        regional = [r for r in kept if r["region"] is not None]

        # The cross-check that makes the industry head count believable, and
        # the reason it is a view: derived from the two figures, never stored,
        # so it cannot drift from them. Dropped when the filter drops its
        # weaker parent, which is the correct behaviour rather than a gap.
        weight = conn.execute(
            """SELECT head_year, output_year, year_gap, output_tonnes,
                      head_thousands, kg_per_head, confidence
               FROM v_output_derived_weight
               WHERE iso3 = ? AND species = ?""",
            (country["iso3"].upper(), species),
        ).fetchall()
        weight = [dict(w) for w in weight
                  if meets_confidence(w["confidence"], min_confidence)]

        return {
            "country": {
                "iso3": country["iso3"],
                "name": country["name"],
                "native_mass_unit": country["native_mass_unit"],
                "native_currency": country["native_currency"],
            },
            "species": species,
            "min_confidence": min_confidence,
            "national": national,
            "regional": regional,
            "derived_weight": weight,
            "excluded": [
                {"measure": r["measure"], "year": r["year"],
                 "confidence": r["confidence"], "source": r["source_slug"]}
                for r in excluded
            ],
            # Stated rather than left for the caller to notice. A suppressed
            # row is presence without volume and must not be read as zero.
            "suppressed_regions": sum(
                1 for r in regional if r["suppressed"]
            ),
        }
    finally:
        conn.close()


def _harmonic_payload(h: seas.HarmonicFit | None) -> dict | None:
    if h is None:
        return None
    return {
        "amplitude": h.amplitude,
        "phase_month": h.phase_month,
        "p_value": h.p_value,
        "ci_lo": h.ci_lo,
        "ci_hi": h.ci_hi,
        "confidence_level": h.confidence_level,
        "bootstrap": h.bootstrap,
        "notes": h.notes,
    }


def _seasonality_payload(s: seas.Seasonality) -> dict:
    return {
        "region": s.region,
        "year": s.year,
        "unit": s.unit,
        "values": s.values,
        "months_present": s.months_present,
        "lo": s.lo,
        "hi": s.hi,
        "mean": s.mean,
        "swing": s.swing,
        "swing_pct": s.swing_pct,
        "peak_month": s.peak_month,
        "peak_month_name": s.peak_month_name,
        "trough_month": s.trough_month,
        "trough_month_name": s.trough_month_name,
        "jitter": s.jitter,
        "signal_ratio": s.signal_ratio,
        "persistence": s.persistence,
        "wrap_share": s.wrap_share,
        "verdict": s.verdict,
        # The weights are surveyed; this verdict about them is ours.
        "confidence": s.confidence,
        "explanation": s.explanation,
        "sparkline": seas.sparkline(s.values),
        "source_slug": s.source_slug,
        "notes": s.notes,
        # A second lens on the same twelve points, not a second series --
        # see "identification_limit" at the top level of this payload.
        "harmonic": _harmonic_payload(s.harmonic),
    }


def _concordance_payload(c: seas.Concordance) -> dict:
    return {
        "kind": c.kind,
        "regions_counted": c.regions_counted,
        "regions_excluded": c.regions_excluded,
        "window": list(c.window),
        "window_names": c.window_names,
        "in_window": c.in_window,
        "expected": c.expected,
        "p_value": c.p_value,
        "p_corrected": c.p_corrected,
        "verdict": c.verdict,
        "confidence": c.confidence,
        "explanation": c.explanation,
        "caveats": c.caveats,
    }


_ORDINALS = {
    1: "", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
    7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh",
    12: "twelfth",
}


def _ordinal(n: int) -> str:
    return _ORDINALS.get(n, f"{n}th")


def _seasonality_summary(
    national: seas.Seasonality | None,
    regions: list[seas.Seasonality],
    peak: seas.Concordance,
) -> str:
    """Assemble the verdict from the rows, never from memory.

    Written this way after the hardcoded first draft claimed that no single
    state's series was a clean cycle. One is.
    """
    cycles = [s.region for s in regions if s.is_seasonal]
    if cycles:
        single = (
            f"{len(cycles)} of {len(regions)} states "
            f"({', '.join(sorted(cycles))}) "
            f"{'has' if len(cycles) == 1 else 'have'} a swing clean enough to "
            f"call seasonal on its own. Every other state, and the national "
            f"series itself, does not."
        )
    else:
        single = (
            f"Not one of the {len(regions)} states has a swing clean enough to "
            f"call seasonal on its own, and neither does the national series."
        )

    size = (
        f"Broiler live weight moves {national.swing_pct:.1f}% across the year "
        f"nationally, from {national.lo:g} {national.unit} in "
        f"{national.trough_month_name} to {national.hi:g} in "
        f"{national.peak_month_name}. "
        if national else ""
    )
    together = (
        f"What the states cannot show alone they show together: {peak.explanation} "
        if peak.verdict != "no agreement" else
        "The states do not agree on when the year peaks either, so there is no "
        "second-order evidence to fall back on. "
    )
    return (
        size + single + " " + together
        + "So the season is real, it is small, and no single series is "
        "evidence for it. None of it moves the count: a chicken has two wings "
        "in every month of the year."
    )


@app.get("/api/seasonality")
def seasonality(year: int | None = None, species: str = "broiler"):
    """Does bird weight have a season, and does the answer change with it?

    The finding this endpoint exists to carry: **no single series is seasonal
    and the states agree anyway.** Per region the swing is indistinguishable
    from twelve noisy points, including nationally. But the peak months cluster
    in one quarter far more than chance allows, and agreement between series
    that were surveyed separately is stronger evidence than any one series'
    range. Both results are returned, neither is hidden, and the weaker one is
    not dressed up as the stronger.

    `year` defaults to the most recent year with a full monthly series rather
    than a literal constant -- a hardcoded year turned this endpoint into a
    404 the frontend silently swallowed the moment the corpus rolled past it.
    """
    conn = dbm.connect()
    try:
        explicit_year = year is not None
        if year is None:
            year = dbm.latest_monthly_size_year(conn, species_slug=species)
            if year is None:
                raise HTTPException(
                    404, f"no monthly {species} data is loaded at all")

        try:
            raw = dbm.monthly_size_series(conn, year=year, species_slug=species)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not raw:
            detail = (
                f"no monthly {species} data for {year}" if explicit_year else
                f"no monthly {species} data for {year}, the most recent "
                "year loaded"
            )
            raise HTTPException(404, detail)

        national_raw = raw.pop("United States", None)
        national = (
            seas.analyse(
                "United States", year, national_raw["values"],
                unit=national_raw["unit"],
                source_slug=national_raw["source_slug"],
            ) if national_raw else None
        )
        regions = [
            seas.analyse(
                name, year, v["values"], unit=v["unit"],
                source_slug=v["source_slug"],
            )
            for name, v in raw.items()
        ]
        # States only. The national row is the sum of these and would be
        # counted as an extra independent witness to its own evidence.
        peak = seas.concordance(regions, "peak")
        trough = seas.concordance(regions, "trough")

        slugs = sorted({
            s.source_slug for s in regions + ([national] if national else [])
            if s.source_slug
        })
        sources = dbm.get_sources(conn, slugs)

        cycles = [s.region for s in regions if s.is_seasonal]

        month_ranks = None
        feb_from_bottom = None
        if national and national.months_present == 12:
            order = sorted(
                range(12), key=lambda i: national.values[i], reverse=True)
            month_ranks = {
                seas.MONTH_NAMES[i]: order.index(i) + 1 for i in range(12)
            }
            feb_from_bottom = 12 - month_ranks["February"] + 1

        return {
            "year": year,
            "species": species,
            # `species` above is the requested slug and has been in the payload
            # since this endpoint existed; `scope` is the same fact in the
            # shape every scoped view reads, so the page has one code path.
            "scope": _scope(conn, [species]),
            "unit": national.unit if national else "lb",
            "measure": "average live weight at slaughter",
            "national": _seasonality_payload(national) if national else None,
            "regions": [
                _seasonality_payload(s) for s in seas.rank(regions)
            ],
            "concordance": {
                "peak": _concordance_payload(peak),
                "trough": _concordance_payload(trough),
            },
            "national_month_ranks": month_ranks,
            # Stated outright rather than left to be inferred from the
            # verdict text (#80): one year of twelve monthly points cannot
            # separate a season from a trend. `verdict` and `harmonic` above
            # are two lenses on that same single short series, not
            # independent confirmations of each other -- see the module
            # docstring in seasonality.py for the full reasoning.
            "identification_limit": (
                "One year of monthly data cannot separate a season from a "
                "trend -- any twelve points are consistent with infinitely "
                "many season/trend decompositions. The verdict above and "
                "the harmonic-regression p-value on each region are two "
                "different statistical lenses on the same single, "
                "unreplicated year, not independent evidence for each "
                "other. This becomes a genuinely identified question with "
                "3+ years of monthly data, which the corpus does not yet "
                "hold."
            ),
            "sources": [
                _source_payload(sources[s]) for s in slugs if s in sources
            ],
            "verdict": {
                "single_series": national.verdict if national else "unknown",
                "across_series": peak.verdict,
                "affects_count": False,
                # Counted from the rows rather than typed, because the first
                # draft of this sentence said no state was seasonal and one is.
                "cycles": cycles,
                "summary": _seasonality_summary(national, regions, peak),
            },
            # Stated in the payload, not just in a comment, so a caller cannot
            # render a seasonal count without seeing why there isn't one.
            "not_modelled": [
                "Monthly head slaughtered. Only the annual total is loaded, so "
                "the corpus cannot say whether more birds are processed in "
                "February.",
                "Monthly condemnation and dead-on-arrival rates. Summer heat "
                "plausibly raises both, and both are count-affecting losses -- "
                "but the corpus holds annual figures only, so seasonality is "
                "deliberately NOT wired into the calculator.",
                (
                    "Demand, imports and frozen inventory. "
                    + (
                        f"February is the {_ordinal(feb_from_bottom)}-lightest "
                        f"month of the national year"
                        if feb_from_bottom else
                        "February sits low in the national year"
                    )
                    + ", which is the opposite of what a supply response to "
                    "Super Bowl demand would look like. The corpus cannot "
                    "explain it, so it does not try."
                ),
            ],
        }
    finally:
        conn.close()


@app.get("/api/trends")
def trends():
    """Year-over-year husbandry and slaughter series."""
    conn = dbm.connect()
    try:
        hus = conn.execute(
            """SELECT h.year, h.cycle_days, h.end_size, h.feed_conversion,
                      h.mortality_pct, s.slug AS source_slug
               FROM husbandry_stat_year h
               JOIN source s ON s.id = h.source_id
               ORDER BY h.year"""
        ).fetchall()
        sla = conn.execute(
            """SELECT y.year, y.head_slaughtered, y.live_weight_lb,
                      y.certified_rtc_lb, y.avg_live_weight_lb,
                      y.postmortem_condemn_pct, s.slug AS source_slug
               FROM slaughter_stat_year y
               JOIN source s ON s.id = y.source_id
               ORDER BY y.year"""
        ).fetchall()
        yields = conn.execute(
            "SELECT year, dressing_yield FROM v_dressing_yield ORDER BY year"
        ).fetchall()
        # Neither series above filters by species -- they return whatever the
        # corpus holds -- so the scope is whatever they just reached.
        scoped = conn.execute(
            """SELECT sp.slug FROM species sp
               WHERE sp.id IN (SELECT species_id FROM husbandry_stat_year
                               UNION SELECT species_id FROM slaughter_stat_year)
               ORDER BY sp.id"""
        ).fetchall()
        return {
            "scope": _scope(conn, [r["slug"] for r in scoped]),
            "husbandry": [dict(r) for r in hus],
            "slaughter": [dict(r) for r in sla],
            "dressing_yield": [dict(r) for r in yields],
        }
    finally:
        conn.close()


@app.get("/api/quality-axes")
def quality_axes():
    """Every species' size question, and whether the corpus can answer it.

    The view is built from this rather than from a hardcoded list, so a
    species with an axis row appears the moment its YAML lands.

    LEFT JOIN, not an inner one, and the difference is the whole point of this
    endpoint. Inner-joined, three of six active species vanished from the
    picker: a silkworm, a beef cow and a sugar maple simply were not offered,
    and nothing said why. A reader counted three chips and had no way to know
    the corpus holds six species. An unanswered question is a finding about
    the data -- omitting it misrepresents the corpus as more complete than it
    is, which is the same bug the null verdict legs already exist to avoid,
    one level up.
    """
    conn = dbm.connect()
    try:
        rows = conn.execute(
            """SELECT sp.slug, sp.common_name, sp.individual_noun,
                      a.question, a.x_label, a.x_unit, a.x_kind,
                      a.verdict_yield, a.verdict_quality, a.verdict_count,
                      (SELECT COUNT(*) FROM quality_defect q
                        WHERE q.species_id = sp.id) AS defects,
                      (SELECT COUNT(*) FROM production_program p
                        WHERE p.species_id = sp.id) AS programs,
                      (SELECT COUNT(*) FROM product_grade g
                        JOIN product pr ON pr.id = g.product_id
                       WHERE pr.species_id = sp.id) AS grades
               FROM species sp
               LEFT JOIN quality_axis a ON a.species_id = sp.id
               WHERE sp.active = 1
               ORDER BY sp.id"""
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            # No axis row at all: the species is offered, its question is
            # stated as unasked, and every downstream field stays null rather
            # than borrowing the neighbouring species' answer.
            d["has_axis"] = d["question"] is not None
            if not d["has_axis"]:
                d["axis_rows"] = 0
                d["has_figures"] = False
                out.append(d)
                continue
            # Which table backs the x-axis depends on the kind of axis, and
            # getting this wrong is subtle: a laying hen HAS production_program
            # rows, but they measure hens per house, not egg size. Counting
            # them here would put a flock-size taxonomy behind the question
            # "is a bigger egg a better egg?" and report a chart we cannot
            # draw. Continuous axes are backed by weight bands, graded ladders
            # by product grades, and neither borrows the other's rows.
            on_axis = d["programs"] if d["x_kind"] == "continuous" \
                else d["grades"]
            d["axis_rows"] = on_axis
            d["has_figures"] = bool(on_axis or d["defects"])
            out.append(d)
        return {"axes": out}
    finally:
        conn.close()


@app.get("/api/bird-size")
def bird_size(year: int = 2025, species: str = "broiler"):
    """One species' size question, and everything needed to answer it.

    Composes state weights, production programs, and quality defects so the
    trade-off is visible in one payload. The question, the x-axis and the
    verdict all come from `quality_axis` -- a species whose answer differs
    (or does not exist) is a YAML change, not a code change.

    TWO 404s, and they are not the same failure. This endpoint serves a size
    QUESTION, so a species with no `quality_axis` row has no resource here to
    return -- but that is a fact about the corpus, not a caller mistake, and
    the caller has to be able to tell which it hit. Both used to be one bare
    string, so the picker could only avoid them by not offering those species
    at all: a silkworm, a beef cow and a sugar maple were silently absent from
    a view claiming to grade "every species".

    So `detail` is an object rather than a sentence, carrying a machine-
    readable `error` and -- for `no_size_question` -- the species itself, which
    is what lets a client render the gap honestly instead of blanking. The
    corpus names the species; the page does not.

      unknown_species    the slug is not in the corpus at all. A bug.
      no_size_question   the species exists and nobody has asked yet.
    """
    conn = dbm.connect()
    try:
        axis = conn.execute(
            """SELECT sp.slug AS species_slug, sp.common_name,
                      sp.individual_noun, sp.individual_plural,
                      a.question, a.x_label, a.x_unit, a.x_kind,
                      a.verdict_yield, a.verdict_quality, a.verdict_count,
                      a.summary
               FROM species sp
               LEFT JOIN quality_axis a ON a.species_id = sp.id
               WHERE sp.slug = ?""",
            (species,),
        ).fetchone()
        if axis is None:
            raise HTTPException(404, detail={
                "error": "unknown_species",
                "message": f"unknown species: '{species}'",
            })
        if axis["question"] is None:
            raise HTTPException(404, detail={
                "error": "no_size_question",
                # Ready to print, and built from the corpus' own name for the
                # species so the page never types one.
                "message": "No size question has been recorded for "
                           f"{axis['common_name'].lower()} yet",
                "species": {
                    "slug": axis["species_slug"],
                    "common_name": axis["common_name"],
                    "individual_noun": axis["individual_noun"],
                    "individual_plural": axis["individual_plural"],
                },
            })
        # v_broiler_size_stat is, as its name says, broilers only. Other
        # species have no regional weight series, and inheriting the broiler
        # one would put chicken pounds on a turkey's axis.
        if species == "broiler":
            regions = conn.execute(
                """SELECT region, avg_size, size_unit, volume
                   FROM v_broiler_size_stat
                   WHERE year = ? AND month IS NULL
                     AND region != 'United States'
                   ORDER BY avg_size DESC""",
                (year,),
            ).fetchall()
            national = conn.execute(
                """SELECT avg_size FROM v_broiler_size_stat
                   WHERE year = ? AND month IS NULL
                     AND region = 'United States'""",
                (year,),
            ).fetchone()
        else:
            regions, national = [], None
        programs = conn.execute(
            """SELECT p.slug, p.label, p.size_lo, p.size_mode, p.size_hi,
                      p.size_unit, p.typical_market, p.notes,
                      s.slug AS source_slug
               FROM production_program p
               JOIN source s ON s.id = p.source_id
               JOIN species sp ON sp.id = p.species_id
               WHERE sp.slug = ?
               ORDER BY p.size_lo""",
            (species,),
        ).fetchall()
        defects = conn.execute(
            """SELECT q.slug, q.label, q.affected_part, q.severity,
                      q.prevalence_pct_lo, q.prevalence_pct_mode,
                      q.prevalence_pct_hi, q.weight_association,
                      q.first_year, q.first_year_pct, q.notes,
                      s.slug AS source_slug, s.title AS source_title,
                      s.publisher, s.url
               FROM quality_defect q
               JOIN source s ON s.id = q.source_id
               JOIN species sp ON sp.id = q.species_id
               WHERE sp.slug = ?
               ORDER BY q.prevalence_pct_mode DESC""",
            (species,),
        ).fetchall()
        # Graded ladders are the classes-axis analogue of production programs:
        # for eggs the x-axis IS the grade, so it has to come back as data.
        grades = conn.execute(
            """SELECT g.slug, g.label, g.units_per_lb_lo, g.units_per_lb_hi,
                      pr.slug AS product_slug, pr.label AS product_label,
                      pr.unit_name, s.slug AS source_slug
               FROM product_grade g
               JOIN product pr ON pr.id = g.product_id
               JOIN species sp ON sp.id = pr.species_id
               JOIN source s ON s.id = g.source_id
               WHERE sp.slug = ?
               ORDER BY g.units_per_lb_lo""",
            (species,),
        ).fetchall()

        rows = [dict(r) for r in regions]
        if rows:
            lightest, heaviest = rows[-1], rows[0]
            ratio = heaviest["avg_size"] / lightest["avg_size"]
        else:
            lightest = heaviest = None
            ratio = None

        ax = dict(axis)
        # Same rule as /api/quality-axes: only the table that actually carries
        # this axis is returned as the axis. A laying hen's production_program
        # rows are flock sizes and belong to a different question entirely, so
        # they are not handed to a view that would chart them as egg sizes.
        on_axis = programs if ax["x_kind"] == "continuous" else grades
        return {
            "year": year,
            "species": {
                "slug": ax["species_slug"],
                "common_name": ax["common_name"],
                "individual_noun": ax["individual_noun"],
                "individual_plural": ax["individual_plural"],
            },
            "axis": {
                "question": ax["question"],
                "x_label": ax["x_label"],
                "x_unit": ax["x_unit"],
                "x_kind": ax["x_kind"],
            },
            "national_avg": national["avg_size"] if national else None,
            "regions": rows,
            "axis_bands": [dict(b) for b in on_axis],
            "defects": [dict(d) for d in defects],
            "has_figures": bool(on_axis or defects),
            "spread": {
                "lightest": lightest,
                "heaviest": heaviest,
                "ratio": ratio,
            },
            # The verdict comes from quality_axis. A null is an open question
            # -- the corpus cannot support that leg yet -- and the client is
            # expected to render it as such rather than as a "no".
            "verdict": {
                "yield_per_individual": ax["verdict_yield"],
                "quality": ax["verdict_quality"],
                "count_floor": ax["verdict_count"],
                "summary": ax["summary"],
            },
        }
    finally:
        conn.close()


@app.get("/api/nutrition")
def nutrition(product: str | None = None):
    """Nutrition per product and preparation, with citations."""
    conn = dbm.connect()
    try:
        sql = """SELECT n.preparation, n.label, n.kcal, n.protein_g, n.fat_g,
                        n.saturated_fat_g, n.carbohydrate_g, n.sodium_mg,
                        n.cholesterol_mg, n.edible_g_per_unit, n.fdc_id,
                        n.notes, p.slug AS product, p.label AS product_label,
                        p.unit_name, s.slug AS source_slug,
                        s.title AS source_title, s.publisher, s.url
                 FROM nutrition n
                 JOIN product p ON p.id = n.product_id
                 JOIN source s  ON s.id = n.source_id"""
        params: tuple = ()
        if product:
            sql += " WHERE p.slug = ?"
            params = (product,)
        sql += " ORDER BY p.slug, n.preparation"
        rows = [dict(r) for r in conn.execute(sql, params)]

        # Per-piece values are derived here rather than stored, so they can
        # never drift out of sync with the per-100 g figures.
        for r in rows:
            g = r.get("edible_g_per_unit")
            if not g:
                continue
            scale = g / 100.0
            r["per_unit"] = {
                k: (r[k] * scale if r.get(k) is not None else None)
                for k in ("kcal", "protein_g", "fat_g", "saturated_fat_g",
                          "carbohydrate_g", "sodium_mg", "cholesterol_mg")
            }
        return {"nutrition": rows}
    finally:
        conn.close()


@app.get("/api/footprint")
def footprint(
    # `le` mirrors /api/calculate and /api/scientific, which both cap here --
    # this one did not, so count=999999999 returned 200 with half a billion
    # birds' worth of footprint.
    count: float = Query(12, gt=0, le=100000),
    product: str = "whole_wing",
):
    """Resource and economic footprint, where the corpus has one.

    A dozen wings does NOT carry six birds' worth of anything. Wings are about
    7.3% of live weight and the rest of the bird fed other people, so every
    figure here is scaled by the product's mass share. Both the raw
    per-individual number and the allocated share are returned, because the gap
    between them is the whole point.

    WHAT THIS ENDPOINT USED TO DO, because the shape of the fix follows from
    it. Three figures were hardcoded rather than looked up:

      mass_share = 0.073 if slug == 'whole_wing' else 0.23
      avg_lw     = ... else 6.62
      grower_pay = computed unconditionally, for every product

    `0.23` is the chicken-BREAST share, so it was applied to all eleven
    non-wing products. A gallon of maple syrup was narrated as 51.50 birds at
    6.62 lb each and $14.32 of broiler grower pay; a silk dress as 22,200
    birds and $6,172.49; a pound of raw silk as 30,000 birds and $8,341.20.
    The resource chart multiplied broiler feed and water by those counts, and
    the allocation note told a reader of a silk dress that "the rest of the
    bird was eaten by someone else."

    So every figure now has to be found rather than assumed, and each of the
    three has its own scope, which is why they can be absent independently:

      - resource_footprint is per SPECIES. Only the broiler has one.
      - economic_stat is per DOMAIN. Poultry has its own, and `livestock`
        (beef cattle) picked up five wagyu figures in v2.1.0 -- reachable
        through any beef product, since wagyu has no product of its own.
      - the mass share is per PRODUCT, and lives in the corpus (see
        `product_mass_share`), so it is subject to the citation audit like
        everything else. Two products have one.

    Nothing is substituted for a missing one. `metrics` comes back empty,
    `mass_share` null, `grower_pay` null, and `coverage` says which -- so the
    page can print "no figures for this product" instead of a chicken's.
    """
    conn = dbm.connect()
    try:
        try:
            prod = dbm.get_product(conn, product)
        except KeyError:
            raise HTTPException(404, f"unknown product: {product}")

        # Scoped to THIS product's species. Unscoped, this handed broiler LCA
        # figures to a silkworm and multiplied them by a silkworm count.
        metrics = conn.execute(
            """SELECT r.metric, r.label, r.unit, r.per_individual,
                      r.per_kg_liveweight, r.reference_lw_lb, r.year,
                      r.pct_change_decade, r.notes, s.slug AS source_slug,
                      s.title AS source_title, s.publisher, s.url
               FROM resource_footprint r
               JOIN source s   ON s.id = r.source_id
               JOIN species sp ON sp.id = r.species_id
               WHERE sp.slug = ?
               ORDER BY r.metric""",
            (prod["species_slug"],),
        ).fetchall()

        # Economic stats are per DOMAIN -- "355,000 industry workers" is a
        # poultry figure, not a broiler one, and it is equally true of eggs.
        econ = conn.execute(
            """SELECT e.slug, e.label, e.value_lo, e.value_mode, e.value_hi,
                      e.unit, e.basis, e.confidence, e.notes,
                      s.slug AS source_slug, s.title AS source_title,
                      s.publisher, s.url
               FROM economic_stat e
               JOIN source s  ON s.id = e.source_id
               JOIN domain d  ON d.id = e.domain_id
               JOIN species sp ON sp.domain_id = d.id
               WHERE sp.slug = ?
               ORDER BY e.slug""",
            (prod["species_slug"],),
        ).fetchall()

        upi = prod["units_per_individual_mode"]
        individuals = count / upi

        share_row = conn.execute(
            """SELECT m.mass_share, m.basis, m.notes, s.slug AS source_slug,
                      s.title AS source_title, s.publisher, s.url
               FROM product_mass_share m
               JOIN source s ON s.id = m.source_id
               WHERE m.product_id = ?""",
            (prod["id"],),
        ).fetchone()
        mass_share = share_row["mass_share"] if share_row else None

        out = []
        for m in metrics:
            d = dict(m)
            per_one = d["per_individual"]
            d["individuals"] = individuals
            d["naive_total"] = (per_one * individuals) if per_one else None
            # Null, not the naive total, when there is no share to allocate
            # by. An unallocated figure presented as an allocated one is the
            # bug this endpoint had, one order of magnitude smaller.
            d["allocated_total"] = (
                per_one * individuals * mass_share
                if per_one and mass_share else None
            )
            out.append(d)

        # Grower pay needs three things to be true at once, and each of them
        # was previously assumed. A layer hen is in the poultry domain, so she
        # inherits the ERS *broiler* grower fee -- and has no slaughter live
        # weight to multiply it by, which is the check that catches it.
        grower = next((dict(e) for e in econ
                       if e["slug"] == "grower_pay_per_lb"), None)
        lw = conn.execute(
            """SELECT sy.avg_live_weight_lb FROM slaughter_stat_year sy
               JOIN species sp ON sp.id = sy.species_id
               WHERE sp.slug = ? AND sy.avg_live_weight_lb IS NOT NULL
               ORDER BY sy.year DESC LIMIT 1""",
            (prod["species_slug"],),
        ).fetchone()

        grower_pay = None
        if grower and grower["value_mode"] and lw and mass_share:
            avg_lw = lw["avg_live_weight_lb"]
            total_lb = individuals * avg_lw
            grower_pay = {
                "live_weight_lb": total_lb,
                "avg_live_weight_lb": avg_lw,
                "paid_for_individuals": total_lb * grower["value_mode"],
                "allocated_to_product":
                    total_lb * grower["value_mode"] * mass_share,
                "rate": grower["value_mode"],
                "source": grower["source_slug"],
            }

        if mass_share:
            allocation_note = (
                "Scaled by mass share. Charging a whole "
                f"{prod['individual_noun']} to this product would overstate "
                f"it by about {1 / mass_share:.0f}x, since the rest of it "
                "went to someone else. Economic allocation would give a "
                "higher figure, because wings sell at a premium per pound."
            )
        elif out:
            allocation_note = (
                f"These are per-{prod['individual_noun']} figures, not this "
                "product's share of them. No published mass share exists for "
                f"{prod['label']}, so allocating them would mean inventing "
                "the multiplier rather than citing it."
            )
        elif econ:
            allocation_note = (
                f"No resource footprint has been sourced for the "
                f"{prod['individual_noun']} yet, so there is nothing here to "
                "allocate. The economic figures below describe the whole "
                "industry rather than this product."
            )
        else:
            allocation_note = (
                "Nothing in the corpus measures the footprint of "
                f"{prod['label']}. The resource and payment figures this "
                "project holds are for broiler chickens, and they are not "
                "this product's to borrow."
            )

        return {
            "product": prod["label"],
            "product_slug": prod["slug"],
            "species": prod["species_slug"],
            "individual_noun": prod["individual_noun"],
            "individual_plural": prod["individual_plural"],
            "count": count,
            "individuals": individuals,
            "mass_share": mass_share,
            "mass_share_basis": share_row["basis"] if share_row else None,
            "mass_share_note": share_row["notes"] if share_row else None,
            "mass_share_source": ({
                "slug": share_row["source_slug"],
                "title": share_row["source_title"],
                "publisher": share_row["publisher"],
                "url": share_row["url"],
            } if share_row else None),
            "allocation_note": allocation_note,
            # What the corpus actually holds for this product, stated rather
            # than left for a client to infer from three empty fields -- and
            # inferring it wrongly is how the page came to narrate a silk
            # dress as a chicken.
            "coverage": {
                "footprint": bool(out),
                "economics": bool(econ),
                "mass_share": mass_share is not None,
                "grower_pay": grower_pay is not None,
            },
            "metrics": out,
            "economics": [dict(e) for e in econ],
            "grower_pay": grower_pay,
        }
    finally:
        conn.close()


@app.get("/api/facts")
def facts(
    placement: str = "learning",
    # Unbounded before this: `limit` was a plain int, and SQLite reads a
    # negative LIMIT as "no limit at all" -- so `?limit=-1` returned every
    # fact in the corpus. The fact deck's own "everything" fetch asks for
    # 500 (app.js initFacts), so the ceiling has to clear that.
    limit: int = Query(20, ge=1, le=1000),
):
    conn = dbm.connect()
    try:
        rows = dbm.get_facts(conn, placement, limit)
        # Facts hang off a DOMAIN, not a species, so the domain's own label is
        # the truer name for what the deck covers -- "Poultry" rather than
        # "Broiler chicken and Laying hen". The species list comes back too,
        # because that is what a caller compares a selected product against.
        doms = conn.execute(
            """SELECT DISTINCT d.slug, d.label FROM fact f
               JOIN domain d ON d.id = f.domain_id
               WHERE f.slug IN (%s) ORDER BY d.id"""
            % (",".join("?" * len(rows)) or "NULL"),
            tuple(r["slug"] for r in rows),
        ).fetchall()
        spp = conn.execute(
            """SELECT sp.slug FROM species sp
               WHERE sp.active = 1 AND sp.domain_id IN
                 (SELECT id FROM domain WHERE slug IN (%s))
               ORDER BY sp.id"""
            % (",".join("?" * len(doms)) or "NULL"),
            tuple(d["slug"] for d in doms),
        ).fetchall()
        return {
            "scope": _scope(conn, [r["slug"] for r in spp],
                            label=" and ".join(d["label"] for d in doms)
                            or None),
            "facts": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@app.get("/api/sources")
def sources():
    """Every source, with a count of how many figures depend on it.

    The tables are discovered from the schema rather than listed here. A
    hand-written list is a third copy of a contract the database already
    states, and it went stale exactly as `audit.cited_tables` warns: every
    country added after the list was written landed in `output_stat_year`
    and `regional_production_year`, neither of which was counted, so 39 of
    111 sources reported "0 figures" -- including every source behind the
    international data. A source that carries the corpus reading as unused
    is worse than no count at all.
    """
    conn = dbm.connect()
    try:
        tables = [t for t, _label, _req in audit.cited_tables(conn)]
        rows = conn.execute("SELECT * FROM source ORDER BY source_type, slug")
        out = []
        for r in rows:
            uses = 0
            for table in tables:
                uses += conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE source_id = ?",
                    (r["id"],),
                ).fetchone()[0]
            d = _source_payload(r)
            d["used_by"] = uses
            out.append(d)
        return {"sources": out}
    finally:
        conn.close()


@app.get("/api/conflicts")
def conflicts():
    """Disagreements the corpus records rather than resolves.

    The point of the endpoint is that these were already in the corpus, held
    as prose in a source's `notes:` where no reader reached them. Each conflict
    comes back with its positions, and every position ships its citation --
    the same rule every other endpoint obeys, so a disagreement cannot be
    rendered without the sources on both sides available to render beside it.

    Neither figure is loaded into the model for any of these (`loaded` is
    almost always false); the disagreement itself is the datum.
    """
    conn = dbm.connect()
    try:
        rows = conn.execute(
            """SELECT c.id, c.slug, c.subject, c.question, c.summary,
                      c.status, c.loaded, c.notes,
                      d.slug AS domain, d.label AS domain_label
               FROM conflict c
               LEFT JOIN domain d ON d.id = c.domain_id
               ORDER BY c.id"""
        ).fetchall()
        out = []
        for c in rows:
            positions = conn.execute(
                """SELECT p.label, p.claim, p.value_text, p.notes,
                          s.slug AS source_slug, s.title AS source_title,
                          s.publisher, s.url, s.source_type
                   FROM conflict_position p
                   JOIN source s ON s.id = p.source_id
                   WHERE p.conflict_id = ?
                   ORDER BY p.id""",
                (c["id"],),
            ).fetchall()
            out.append({
                "slug": c["slug"],
                "subject": c["subject"],
                "question": c["question"],
                "summary": c["summary"],
                "status": c["status"],
                "loaded": bool(c["loaded"]),
                "domain": c["domain"],
                "domain_label": c["domain_label"],
                "notes": c["notes"],
                "positions": [dict(p) for p in positions],
            })
        return {"conflicts": out}
    finally:
        conn.close()


@app.get("/api/meta")
def meta():
    """Supply chains, products, and the loss chain, for populating controls."""
    conn = dbm.connect()
    try:
        chains = [dict(r) for r in dbm.list_supply_chains(conn)]
        products = [dict(r) for r in dbm.list_products(conn)]
        stages = conn.execute(
            """SELECT ls.slug, ls.label, ls.sequence, ls.phase,
                      ls.applies_to, ls.optional, ls.description, ls.notes,
                      lf.survive_lo, lf.survive_mode, lf.survive_hi,
                      lf.confidence, s.slug AS source_slug
               FROM loss_stage ls
               JOIN loss_factor lf ON lf.loss_stage_id = ls.id
               JOIN source s ON s.id = lf.source_id
               ORDER BY ls.sequence"""
        ).fetchall()
        mixing = conn.execute(
            """SELECT ms.slug, ms.label, ms.sequence, ms.pool_lo,
                      ms.pool_mode, ms.pool_hi, ms.mixing_kind,
                      ms.description, ms.confidence
               FROM mixing_stage ms ORDER BY ms.sequence"""
        ).fetchall()
        industry = conn.execute(
            """SELECT p.slug, p.name, p.market_share_pct,
                      p.throughput_per_week, p.facility_count,
                      s.slug AS source_slug
               FROM producer p JOIN source s ON s.id = p.source_id
               ORDER BY p.market_share_pct DESC"""
        ).fetchall()
        segments = conn.execute(
            """SELECT ps.slug, ps.label, ps.mass_grams, ps.edible_yield_pct,
                      ps.sold_as_product, ps.notes, s.slug AS source_slug
               FROM product_segment ps JOIN source s ON s.id = ps.source_id"""
        ).fetchall()
        return {
            "chains": chains,
            "products": products,
            "loss_stages": [dict(r) for r in stages],
            "mixing_stages": [dict(r) for r in mixing],
            "producers": [dict(r) for r in industry],
            "segments": [dict(r) for r in segments],
        }
    finally:
        conn.close()


@app.get("/")
def index():
    """Serve the frontend.

    One page, sent as a file. It was rendered per request while two designs
    shared this URL and each needed a signed token naming which one it was;
    with a single page there is nothing per-visitor left to substitute.

    `no-cache` keeps a deploy visible without a hard reload -- the markup is
    small and the assets under `/static` carry the weight.
    """
    return FileResponse(STATIC / "index.html",
                        headers={"Cache-Control": "no-cache"})


if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
