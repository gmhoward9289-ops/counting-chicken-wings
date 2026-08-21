"""Pure sync tool surface for the MCP server (and tests).

No ``mcp`` import here — keep the core free of the optional extra. Every
answer reuses the same DB loaders and ``model.run`` path as the HTTP API so
CLI / API / MCP cannot drift on citations or the required-vs-distinct split.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__, audit
from . import db as dbm
from .model import run

DIMENSION_LABELS = {
    "loss_chain": "a sourced supply chain",
    "products": "products in the calculator",
    "size_axis": "a size question",
    "regional_weight": "region-by-region weights",
    "seasonality": "a month-by-month series",
    "trends": "a year-over-year series",
    "footprint": "a resource footprint",
    "nutrition": "nutrition figures",
}

_SPECIES_COLUMNS = (
    "id",
    "slug",
    "common_name",
    "individual_noun",
    "individual_plural",
    "domain",
)


class ToolError(Exception):
    """User-facing tool failure — returned as ``{"error": ...}`` to agents."""


def _conn(db: str | Path | None = None):
    return dbm.connect(Path(db) if db else None)


def source_payload(row) -> dict:
    return {
        "slug": row["slug"],
        "title": row["title"],
        "publisher": row["publisher"],
        "url": row["url"],
        "published_on": row["published_on"],
        "source_type": row["source_type"],
        "notes": row["notes"],
    }


def _stamp() -> dict[str, str]:
    return {"package_version": __version__}


def _scope(conn, species_slugs, *, label: str | None = None) -> dict:
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
        "label": label or (" and ".join(names) if names else None),
    }


def _borrow_note(
    product_label: str, product_species: str, scope_species: str
) -> str:
    return (
        f"{product_label} is a {product_species} product, and nothing "
        f"measured on {scope_species} is its to borrow."
    )


def resolve_chain(conn, prod, chain: str | None) -> str:
    """Return the supply-chain slug, or raise ToolError."""
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
        raise ToolError(f"unknown supply chain: {chain}")
    if row["species_slug"] and row["species_slug"] != prod["species_slug"]:
        raise ToolError(
            f"supply chain '{chain}' belongs to {row['species_slug']}, "
            f"and {prod['label']} comes from {prod['species_slug']}"
        )
    return chain


def wings_meta(db: str | Path | None = None) -> dict[str, Any]:
    """Supply chains, products, loss/mixing stages — discovery before calculate."""
    conn = _conn(db)
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
            **_stamp(),
            "chains": chains,
            "products": products,
            "loss_stages": [dict(r) for r in stages],
            "mixing_stages": [dict(r) for r in mixing],
            "producers": [dict(r) for r in industry],
            "segments": [dict(r) for r in segments],
        }
    finally:
        conn.close()


def wings_scope(
    product: str | None = None, db: str | Path | None = None
) -> dict[str, Any]:
    """Species coverage depth, corpus anchor, and borrow notes for a product."""
    conn = _conn(db)
    try:
        rows = conn.execute(
            "SELECT * FROM v_species_coverage ORDER BY id"
        ).fetchall()
        keys = [
            k
            for k in (rows[0].keys() if rows else [])
            if k not in _SPECIES_COLUMNS
        ]

        species = []
        for r in rows:
            dims = {k: bool(r[k]) for k in keys}
            species.append(
                {
                    "slug": r["slug"],
                    "common_name": r["common_name"],
                    "individual_noun": r["individual_noun"],
                    "individual_plural": r["individual_plural"],
                    "domain": r["domain"],
                    "dimensions": dims,
                    "depth": sum(dims.values()),
                }
            )

        anchor = None
        if species:
            depths = sorted((s["depth"] for s in species), reverse=True)
            if len(depths) == 1 or depths[0] > depths[1]:
                anchor = max(species, key=lambda s: s["depth"])

        selected = None
        if product is not None:
            try:
                prod = dbm.get_product(conn, product)
            except KeyError:
                return {**_stamp(), "error": f"unknown product: {product}"}
            mine = next(
                (s for s in species if s["slug"] == prod["species_slug"]),
                None,
            )
            selected = {
                "slug": prod["slug"],
                "label": prod["label"],
                "species": prod["species_slug"],
                "common_name": mine["common_name"] if mine else None,
                "borrow_notes": {
                    s["slug"]: _borrow_note(
                        prod["label"],
                        mine["common_name"] if mine else prod["species_slug"],
                        s["common_name"],
                    )
                    for s in species
                    if s["slug"] != prod["species_slug"]
                },
            }

        return {
            **_stamp(),
            "anchor": anchor,
            "species": species,
            "selected": selected,
            "dimensions": [
                {
                    "key": k,
                    "label": DIMENSION_LABELS.get(k, k),
                    "species": [
                        s["slug"] for s in species if s["dimensions"][k]
                    ],
                }
                for k in keys
            ],
        }
    finally:
        conn.close()


def wings_calculate(
    count: float = 12,
    product: str = "whole_wing",
    chain: str | None = None,
    pieces: bool = False,
    include_mortality: bool = False,
    iterations: int = 0,
    window_days: float | None = None,
    db: str | Path | None = None,
) -> dict[str, Any]:
    """Main answer: required (supply) vs distinct (plate), with full citations.

    Never conflate ``answer.required`` (birds' worth of wing through the funnel)
    with ``answer.distinct`` (expected individuals on the plate). Floor is ≥ 6;
    distinct is bounded hard at 6 below and 12 above for a dozen whole wings.
    """
    if count <= 0 or count > 100_000:
        return {**_stamp(), "error": "count must be in (0, 100000]"}
    if iterations < 0 or iterations > 200_000:
        return {**_stamp(), "error": "iterations must be in [0, 200000]"}
    if window_days is not None and (window_days <= 0 or window_days > 3650):
        return {**_stamp(), "error": "window_days must be in (0, 3650]"}

    conn = _conn(db)
    try:
        try:
            prod = dbm.get_product(conn, product)
        except KeyError:
            return {**_stamp(), "error": f"unknown product: {product}"}

        units = count
        segments = None
        if pieces:
            segments = (
                conn.execute(
                    """SELECT COUNT(*) FROM product_segment
                       WHERE product_id = ? AND sold_as_product = 1""",
                    (prod["id"],),
                ).fetchone()[0]
                or 1
            )
            units = count / segments

        try:
            chain = resolve_chain(conn, prod, chain)
        except ToolError as e:
            return {**_stamp(), "error": str(e)}

        loss = dbm.load_loss_stages(
            conn,
            prod["species_slug"],
            prod["slug"],
            include_optional=include_mortality,
            chain_slug=chain,
        )
        mixing = dbm.load_mixing_stages(conn, chain)

        try:
            recurring = dbm.make_recurring(prod, window_days)
        except ValueError as e:
            return {**_stamp(), "error": str(e)}

        res = run(
            units_requested=units,
            units_per_individual=prod["units_per_individual_mode"],
            loss_stages=loss,
            mixing_stages=mixing,
            iterations=iterations,
            recurring=recurring,
            anatomical=bool(prod["is_anatomical_constant"]),
            floor_source=dbm.product_source_slug(conn, prod["slug"]),
            params=dbm.load_mixing_params(conn),
            param_bands=dbm.load_mixing_param_bands(conn),
            correlated_groups=dbm.load_correlated_groups(
                conn, prod["species_slug"]
            ),
            mixing_subunits_per_unit=prod["mixing_subunits_per_unit"],
        )

        slugs = list({s.source_slug for s in res.trace if s.source_slug})
        sources = {
            k: source_payload(v) for k, v in dbm.get_sources(conn, slugs).items()
        }

        return {
            **_stamp(),
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
                "ceiling": res.distinct_ceiling,
                "required": res.required,
                "required_estimator": res.required_estimator,
                "required_lo": res.required_lo,
                "required_hi": res.required_hi,
                "distinct": res.distinct_mean,
                "iterations": res.iterations,
                "container_units": res.container_units,
                "paired_individuals": res.paired_individuals,
                "hard_floor": res.hard_floor,
                "window_days": res.window_days,
                "rate_per_day": res.rate_per_day,
                "cap_per_individual": res.cap_per_individual,
                "rate_label": prod["rate_label"],
                "cap_note": prod["cap_note"],
                "yield_mode": prod["yield_mode"],
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
            "floor_note": dbm.chain_floor_note(conn, chain),
            "sources": sources,
        }
    finally:
        conn.close()


def wings_sources(db: str | Path | None = None) -> dict[str, Any]:
    """Full citation catalog with how many figures depend on each source."""
    conn = _conn(db)
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
            d = source_payload(r)
            d["used_by"] = uses
            out.append(d)
        return {**_stamp(), "sources": out}
    finally:
        conn.close()


def wings_facts(
    placement: str = "learning",
    limit: int = 20,
    db: str | Path | None = None,
) -> dict[str, Any]:
    """Fact deck rows with embedded source fields and domain scope."""
    if limit < 1 or limit > 1000:
        return {**_stamp(), "error": "limit must be in [1, 1000]"}
    conn = _conn(db)
    try:
        rows = dbm.get_facts(conn, placement, limit)
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
            **_stamp(),
            "scope": _scope(
                conn,
                [r["slug"] for r in spp],
                label=" and ".join(d["label"] for d in doms) or None,
            ),
            "facts": [dict(r) for r in rows],
        }
    finally:
        conn.close()
