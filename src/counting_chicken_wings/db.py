"""Database access: load model inputs out of SQLite.

Kept deliberately thin. The maths lives in model.py with no database
dependency; this module's only job is turning rows into those dataclasses.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .build import DEFAULT_DB, build
from .model import LossStage, MixingStage


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open the database, building it first if it is missing."""
    p = Path(db_path) if db_path else DEFAULT_DB
    if not p.exists():
        build(p)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_product(conn, slug: str = "whole_wing") -> sqlite3.Row:
    row = conn.execute(
        """SELECT p.*, s.slug AS species_slug, s.individual_noun,
                  s.individual_plural
           FROM product p JOIN species s ON s.id = p.species_id
           WHERE p.slug = ?""",
        (slug,),
    ).fetchone()
    if row is None:
        raise KeyError(f"unknown product: {slug}")
    return row


def list_products(conn) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT p.slug, p.label, p.unit_name, p.yield_mode,
                  s.common_name AS species, s.active
           FROM product p JOIN species s ON s.id = p.species_id
           ORDER BY s.active DESC, p.slug"""
    ).fetchall()


def load_loss_stages(
    conn,
    species_slug: str = "broiler",
    product_slug: str | None = "whole_wing",
    include_optional: bool = False,
) -> list[LossStage]:
    """Load the loss chain.

    Factor resolution is by specificity: a factor naming this product beats
    a general one for the same stage. Optional stages (grow-out mortality)
    are excluded unless asked for.
    """
    rows = conn.execute(
        """
        SELECT ls.slug, ls.label, ls.sequence, ls.phase, ls.applies_to,
               ls.optional, ls.default_enabled, ls.description, ls.notes,
               lf.survive_lo, lf.survive_mode, lf.survive_hi, lf.confidence,
               src.slug AS source_slug,
               (lf.product_id IS NOT NULL) AS specific
        FROM loss_stage ls
        JOIN loss_factor lf ON lf.loss_stage_id = ls.id
        JOIN species sp     ON sp.id = lf.species_id
        JOIN source src     ON src.id = lf.source_id
        LEFT JOIN product p ON p.id = lf.product_id
        WHERE sp.slug = ?
          AND lf.valid_to IS NULL
          AND (lf.product_id IS NULL OR p.slug = ?)
        ORDER BY ls.sequence, specific DESC
        """,
        (species_slug, product_slug),
    ).fetchall()

    out: list[LossStage] = []
    seen: set[str] = set()
    for r in rows:
        if r["slug"] in seen:
            continue          # first row wins: most specific factor
        seen.add(r["slug"])
        if r["optional"] and not include_optional:
            continue
        if not r["default_enabled"] and not include_optional:
            continue
        out.append(LossStage(
            slug=r["slug"], label=r["label"], sequence=r["sequence"],
            phase=r["phase"], applies_to=r["applies_to"],
            survive_lo=r["survive_lo"], survive_mode=r["survive_mode"],
            survive_hi=r["survive_hi"], confidence=r["confidence"],
            description=r["description"] or "", notes=r["notes"] or "",
            optional=bool(r["optional"]),
            default_enabled=bool(r["default_enabled"]),
            source_slug=r["source_slug"],
        ))
    return out


def default_supply_chain(conn) -> str:
    row = conn.execute(
        "SELECT slug FROM supply_chain WHERE is_default = 1 LIMIT 1"
    ).fetchone()
    return row["slug"] if row else "commodity_foodservice"


def list_supply_chains(conn) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT slug, label, description, is_default FROM supply_chain "
        "ORDER BY is_default DESC, slug"
    ).fetchall()


def load_mixing_stages(conn, chain_slug: str) -> list[MixingStage]:
    rows = conn.execute(
        """
        SELECT ms.slug, ms.label, ms.mixing_kind, ms.description,
               ms.confidence, src.slug AS source_slug,
               COALESCE(scs.pool_override, ms.pool_mode) AS pool,
               ms.pool_lo, ms.pool_hi, scs.pool_override
        FROM supply_chain sc
        JOIN supply_chain_stage scs ON scs.supply_chain_id = sc.id
        JOIN mixing_stage ms        ON ms.id = scs.mixing_stage_id
        JOIN source src             ON src.id = ms.source_id
        WHERE sc.slug = ?
        ORDER BY ms.sequence
        """,
        (chain_slug,),
    ).fetchall()
    out = []
    for r in rows:
        # A per-chain override replaces the point value, so its band has to
        # be rescaled rather than inherited -- otherwise a butcher's 40-bird
        # tray would sample against the plant-scale 2,000-60,000 range.
        if r["pool_override"] is not None:
            scale = r["pool"] / max(1, r["pool_lo"] or r["pool"])
            lo = max(1, int(r["pool"] / max(scale, 1.0)))
            hi = r["pool"]
            lo, hi = min(lo, r["pool"]), max(hi, r["pool"])
        else:
            lo, hi = r["pool_lo"], r["pool_hi"]
        out.append(MixingStage(
            slug=r["slug"], label=r["label"], pool=r["pool"],
            mixing_kind=r["mixing_kind"], description=r["description"],
            confidence=r["confidence"], source_slug=r["source_slug"],
            pool_lo=lo, pool_hi=hi,
        ))
    return out


def get_sources(conn, slugs: list[str]) -> dict[str, sqlite3.Row]:
    if not slugs:
        return {}
    marks = ",".join("?" * len(slugs))
    rows = conn.execute(
        f"SELECT * FROM source WHERE slug IN ({marks})", slugs
    ).fetchall()
    return {r["slug"]: r for r in rows}


def get_facts(conn, placement: str = "both", limit: int = 5):
    where = ("placement IN ('result','both')" if placement == "result"
             else "placement IN ('learning','both')" if placement == "learning"
             else "1=1")
    return conn.execute(
        f"""SELECT f.slug, f.headline, f.body, f.surprise,
                   s.slug AS source_slug, s.title AS source_title,
                   s.publisher, s.url
            FROM fact f JOIN source s ON s.id = f.source_id
            WHERE {where}
            ORDER BY f.surprise DESC, f.slug
            LIMIT ?""",
        (limit,),
    ).fetchall()
