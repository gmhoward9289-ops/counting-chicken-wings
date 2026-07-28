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
