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

from . import db as dbm
from .model import (
    CONFIDENCE_RANK,
    expected_distinct,
    meets_confidence,
    run,
    sensitivity,
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
        "notes": row["notes"],
    }


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


@app.get("/api/calculate")
def calculate(
    count: float = Query(12, gt=0, le=100000),
    product: str = "whole_wing",
    chain: str | None = None,
    pieces: bool = False,
    include_mortality: bool = False,
    iterations: int = Query(0, ge=0, le=200000),
):
    """The main calculation, with a full per-stage audit trail."""
    conn = dbm.connect()
    try:
        try:
            prod = dbm.get_product(conn, product)
        except KeyError:
            raise HTTPException(404, f"unknown product: {product}")

        units = count
        segments = None
        if pieces:
            segments = conn.execute(
                """SELECT COUNT(*) FROM product_segment
                   WHERE product_id = ? AND sold_as_product = 1""",
                (prod["id"],),
            ).fetchone()[0] or 1
            units = count / segments

        chain = chain or dbm.default_supply_chain(conn)
        loss = dbm.load_loss_stages(
            conn, prod["species_slug"], prod["slug"],
            include_optional=include_mortality,
        )
        mixing = dbm.load_mixing_stages(conn, chain)
        if not mixing and chain != "whole_bird_home":
            existing = [c["slug"] for c in dbm.list_supply_chains(conn)]
            if chain not in existing:
                raise HTTPException(404, f"unknown supply chain: {chain}")

        res = run(
            units_requested=units,
            units_per_individual=prod["units_per_individual_mode"],
            loss_stages=loss,
            mixing_stages=mixing,
            iterations=iterations,
        )

        slugs = list({s.source_slug for s in res.trace if s.source_slug})
        sources = {k: _source_payload(v)
                   for k, v in dbm.get_sources(conn, slugs).items()}

        return {
            "question": {
                "count": count,
                "units": units,
                "basis": "segment" if pieces else "whole unit",
                "segments_per_unit": segments,
                "product": prod["label"],
                "unit_name": prod["unit_name"],
                "individual_noun": prod["individual_noun"],
                "individual_plural": prod["individual_plural"],
                "chain": chain,
                "include_mortality": include_mortality,
            },
            "answer": {
                "floor": res.floor,
                "ceiling": units,
                "required": res.required,
                "required_lo": res.required_lo,
                "required_hi": res.required_hi,
                "distinct": res.distinct_mean,
                "iterations": res.iterations,
                "container_units": res.container_units,
                "paired_individuals": res.paired_individuals,
            },
            "trace": [
                {
                    "sequence": s.sequence,
                    "kind": s.kind,
                    "slug": s.stage_slug,
                    "label": s.stage_label,
                    "value": s.value_used,
                    "running_total": s.running_total,
                    "explanation": s.explanation,
                    "confidence": s.confidence,
                    "source": s.source_slug,
                }
                for s in res.trace
            ],
            "mixing_notes": res.mixing_notes,
            "sources": sources,
        }
    finally:
        conn.close()


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

        chain = chain or dbm.default_supply_chain(conn)
        upi = prod["units_per_individual_mode"]
        loss = dbm.load_loss_stages(
            conn, prod["species_slug"], prod["slug"],
            include_optional=include_mortality,
        )
        mixing = dbm.load_mixing_stages(conn, chain)

        res = run(
            units_requested=units, units_per_individual=upi,
            loss_stages=loss, mixing_stages=mixing,
            iterations=iterations, seed=seed,
            confidence_level=confidence_level,
            min_confidence=min_confidence, keep_samples=True,
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
                "ceiling": units,
                "required": res.required,
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


@app.get("/api/mixing-curve")
def mixing_curve(
    draw: int = Query(12, gt=0, le=500),
    units_per_individual: float = Query(2.0, gt=0),
):
    """The distinct-individuals curve as the pool grows.

    Powers the simulator: drag the pool from 6 individuals to 40,000 and
    watch the count climb from the floor toward the ceiling.
    """
    pools = []
    b = max(1, int(draw / units_per_individual))
    while b <= 200000:
        pools.append(b)
        b = int(b * 1.35) + 1
    if 200000 not in pools:
        pools.append(200000)

    points = []
    for pool in pools:
        container = int(pool * units_per_individual)
        if container < draw:
            continue
        points.append({
            "pool": pool,
            "distinct": expected_distinct(draw, container, pool),
        })

    return {
        "draw": draw,
        "floor": draw / units_per_individual,
        "ceiling": draw,
        "points": points,
        "note": (
            "Each individual contributes all of its units to the pool, so "
            "this is the most conservative case. Size grading actively "
            "separates a pair, which pushes the real answer even closer to "
            "the ceiling."
        ),
    }


@app.get("/api/states")
def states(year: int = 2025):
    """Average live weight by state, with production volume where reported."""
    conn = dbm.connect()
    try:
        rows = conn.execute(
            """SELECT r.region, r.avg_size, r.size_unit, r.volume,
                      r.volume_unit, s.slug AS source_slug
               FROM regional_size_stat r
               JOIN source s ON s.id = r.source_id
               WHERE r.year = ? AND r.month IS NULL
               ORDER BY r.avg_size DESC""",
            (year,),
        ).fetchall()
        programs = conn.execute(
            """SELECT slug, label, size_lo, size_hi, typical_market
               FROM production_program ORDER BY size_lo"""
        ).fetchall()

        def program_for(w):
            for p in programs:
                if p["size_lo"] <= w <= p["size_hi"]:
                    return p["label"]
            return None

        return {
            "year": year,
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
        }
    finally:
        conn.close()


@app.get("/api/state-trend/{region}")
def state_trend(region: str, year: int = 2025):
    """Month-over-month average live weight for one state."""
    conn = dbm.connect()
    try:
        rows = conn.execute(
            """SELECT month, avg_size FROM regional_size_stat
               WHERE region = ? AND year = ? AND month IS NOT NULL
               ORDER BY month""",
            (region, year),
        ).fetchall()
        if not rows:
            raise HTTPException(404, f"no monthly data for {region}")
        return {
            "region": region,
            "year": year,
            "months": [r["month"] for r in rows],
            "values": [r["avg_size"] for r in rows],
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
        return {
            "husbandry": [dict(r) for r in hus],
            "slaughter": [dict(r) for r in sla],
            "dressing_yield": [dict(r) for r in yields],
        }
    finally:
        conn.close()


@app.get("/api/bird-size")
def bird_size(year: int = 2025):
    """Is a fatter bird better? Everything needed to answer it.

    Composes state weights, production programs, and quality defects so the
    trade-off is visible in one payload: heavier birds yield more meat per
    bird, and carry worse meat quality per pound.
    """
    conn = dbm.connect()
    try:
        regions = conn.execute(
            """SELECT region, avg_size, size_unit, volume
               FROM regional_size_stat
               WHERE year = ? AND month IS NULL AND region != 'United States'
               ORDER BY avg_size DESC""",
            (year,),
        ).fetchall()
        national = conn.execute(
            """SELECT avg_size FROM regional_size_stat
               WHERE year = ? AND month IS NULL AND region = 'United States'""",
            (year,),
        ).fetchone()
        programs = conn.execute(
            """SELECT p.slug, p.label, p.size_lo, p.size_mode, p.size_hi,
                      p.size_unit, p.typical_market, p.notes,
                      s.slug AS source_slug
               FROM production_program p JOIN source s ON s.id = p.source_id
               ORDER BY p.size_lo"""
        ).fetchall()
        defects = conn.execute(
            """SELECT q.slug, q.label, q.affected_part, q.severity,
                      q.prevalence_pct_lo, q.prevalence_pct_mode,
                      q.prevalence_pct_hi, q.weight_association,
                      q.first_year, q.first_year_pct, q.notes,
                      s.slug AS source_slug, s.title AS source_title,
                      s.publisher, s.url
               FROM quality_defect q JOIN source s ON s.id = q.source_id
               ORDER BY q.prevalence_pct_mode DESC"""
        ).fetchall()

        rows = [dict(r) for r in regions]
        if rows:
            lightest, heaviest = rows[-1], rows[0]
            ratio = heaviest["avg_size"] / lightest["avg_size"]
        else:
            lightest = heaviest = None
            ratio = None

        return {
            "year": year,
            "national_avg": national["avg_size"] if national else None,
            "regions": rows,
            "programs": [dict(p) for p in programs],
            "defects": [dict(d) for d in defects],
            "spread": {
                "lightest": lightest,
                "heaviest": heaviest,
                "ratio": ratio,
            },
            # The verdict, stated rather than left for the reader to assemble.
            "verdict": {
                "yield_per_bird": "better",
                "quality_per_pound": "worse",
                "wing_count_floor": "unchanged",
                "summary": (
                    "Heavier birds give more meat per bird and better "
                    "processing economics. They also carry worse meat "
                    "quality: every breast myopathy measured gets more "
                    "common as live weight rises, and heavier birds are "
                    "harder to handle so more wings break. The anatomical "
                    "floor does not move at all -- a chicken has two wings "
                    "whatever it weighs. So 'fatter is better' is true for "
                    "yield, false for quality, and irrelevant to the count."
                ),
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
def footprint(count: float = Query(12, gt=0), product: str = "whole_wing"):
    """Resource and economic footprint, mass-allocated to the product.

    A dozen wings does NOT carry six birds' worth of anything. Wings are
    about 7% of live weight and the rest of the bird fed other people, so
    every figure here is scaled by the product's mass share. Both the raw
    per-bird number and the allocated share are returned, because the gap
    between them is the whole point.
    """
    conn = dbm.connect()
    try:
        try:
            prod = dbm.get_product(conn, product)
        except KeyError:
            raise HTTPException(404, f"unknown product: {product}")

        metrics = conn.execute(
            """SELECT r.metric, r.label, r.unit, r.per_individual,
                      r.per_kg_liveweight, r.reference_lw_lb, r.year,
                      r.pct_change_decade, r.notes, s.slug AS source_slug,
                      s.title AS source_title, s.publisher, s.url
               FROM resource_footprint r JOIN source s ON s.id = r.source_id
               ORDER BY r.metric"""
        ).fetchall()
        econ = conn.execute(
            """SELECT e.slug, e.label, e.value_lo, e.value_mode, e.value_hi,
                      e.unit, e.basis, e.confidence, e.notes,
                      s.slug AS source_slug, s.title AS source_title,
                      s.publisher, s.url
               FROM economic_stat e JOIN source s ON s.id = e.source_id
               ORDER BY e.slug"""
        ).fetchall()

        upi = prod["units_per_individual_mode"]
        birds = count / upi

        # Mass share of the bird this product represents. Whole wings run
        # ~7.3% of live weight; boneless is breast, ~23%.
        mass_share = 0.073 if prod["slug"] == "whole_wing" else 0.23

        out = []
        for m in metrics:
            d = dict(m)
            per_bird = d["per_individual"]
            d["birds"] = birds
            d["naive_total"] = (per_bird * birds) if per_bird else None
            d["allocated_total"] = (
                per_bird * birds * mass_share if per_bird else None
            )
            out.append(d)

        grower = next((dict(e) for e in econ
                       if e["slug"] == "grower_pay_per_lb"), None)
        grower_pay = None
        if grower and grower["value_mode"]:
            lw = conn.execute(
                """SELECT avg_live_weight_lb FROM slaughter_stat_year
                   ORDER BY year DESC LIMIT 1"""
            ).fetchone()
            avg_lw = lw["avg_live_weight_lb"] if lw else 6.62
            total_lb = birds * avg_lw
            grower_pay = {
                "live_weight_lb": total_lb,
                "paid_for_birds": total_lb * grower["value_mode"],
                "allocated_to_product":
                    total_lb * grower["value_mode"] * mass_share,
                "rate": grower["value_mode"],
                "source": grower["source_slug"],
            }

        return {
            "product": prod["label"],
            "count": count,
            "birds": birds,
            "mass_share": mass_share,
            "allocation_note": (
                "Scaled by mass share. Charging the whole bird to this "
                "product would overstate it by about "
                f"{1 / mass_share:.0f}x, since the rest of the bird was "
                "eaten by someone else. Economic allocation would give a "
                "higher figure, because wings sell at a premium per pound."
            ),
            "metrics": out,
            "economics": [dict(e) for e in econ],
            "grower_pay": grower_pay,
        }
    finally:
        conn.close()


@app.get("/api/facts")
def facts(placement: str = "learning", limit: int = 20):
    conn = dbm.connect()
    try:
        return {"facts": [dict(r) for r in
                          dbm.get_facts(conn, placement, limit)]}
    finally:
        conn.close()


@app.get("/api/sources")
def sources():
    """Every source, with a count of how many figures depend on it."""
    conn = dbm.connect()
    try:
        rows = conn.execute("SELECT * FROM source ORDER BY source_type, slug")
        out = []
        for r in rows:
            uses = 0
            for table in ("loss_factor", "fact", "product", "product_segment",
                          "producer", "mixing_stage", "slaughter_stat_year",
                          "regional_size_stat", "husbandry_stat_year",
                          "production_program", "product_grade"):
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
    return FileResponse(STATIC / "index.html")


if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
