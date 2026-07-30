"""Database access: load model inputs out of SQLite.

Kept deliberately thin. The maths lives in model.py with no database
dependency; this module's only job is turning rows into those dataclasses.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .build import DEFAULT_DB, build
from .model import LossStage, MixingStage, RecurringYield

# A recurring product needs a window before it means anything, and one day is
# the honest default: "a dozen eggs" colloquially means a carton gathered
# together, not a dozen accumulated over a fortnight. It is also the case
# where the answer is hardest -- a hen lays at most one egg a day, so twelve
# same-day eggs came from twelve different hens and no arrangement of the
# supply chain can reduce it.
DEFAULT_WINDOW_DAYS = 1.0


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


def make_recurring(
    product: sqlite3.Row,
    window_days: float | None = None,
) -> RecurringYield | None:
    """Build a RecurringYield for a product, or None if it is timeless.

    Returns None for countable and continuous products so callers can pass
    the result straight through to `run()` without branching -- a chicken has
    two wings and that needs no clock.
    """
    if product["yield_mode"] != "recurring":
        return None

    period = product["yield_period_days"]
    if not period:
        # yield_mode='recurring' without a period is incoherent: the rate has
        # no denominator. Better to say so than to silently assume a year.
        raise ValueError(
            f"product {product['slug']!r} is recurring but has no "
            f"yield_period_days, so its rate has no meaning"
        )

    return RecurringYield(
        units_per_period=product["units_per_individual_mode"],
        period_days=period,
        window_days=window_days or DEFAULT_WINDOW_DAYS,
        max_units_per_day=product["max_units_per_day"],
    )


def list_products(conn) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT p.slug, p.label, p.label_plural, p.unit_name, p.yield_mode,
                  p.yield_period_days, p.max_units_per_day,
                  s.common_name AS species, s.individual_plural, s.active
           FROM product p JOIN species s ON s.id = p.species_id
           ORDER BY s.active DESC, p.slug"""
    ).fetchall()


def _loss_stage_from_row(r) -> LossStage:
    """Row to LossStage. Shared by the declared-chain and default paths so the
    two cannot drift apart."""
    return LossStage(
        slug=r["slug"], label=r["label"], sequence=r["sequence"],
        phase=r["phase"], applies_to=r["applies_to"],
        survive_lo=r["survive_lo"], survive_mode=r["survive_mode"],
        survive_hi=r["survive_hi"], confidence=r["confidence"],
        description=r["description"] or "", notes=r["notes"] or "",
        optional=bool(r["optional"]),
        default_enabled=bool(r["default_enabled"]),
        source_slug=r["source_slug"],
    )


def chain_loss_stages(conn, chain_slug: str) -> set[str] | None:
    """The loss stages a chain declares, or None if it declares none.

    None means "use the species defaults", which is how every route behaved
    before chains could select losses. A chain that lists stages gets exactly
    those.
    """
    rows = conn.execute(
        """SELECT ls.slug FROM supply_chain sc
           JOIN supply_chain_loss_stage scls ON scls.supply_chain_id = sc.id
           JOIN loss_stage ls ON ls.id = scls.loss_stage_id
           WHERE sc.slug = ?""",
        (chain_slug,),
    ).fetchall()
    return {r["slug"] for r in rows} or None


def load_loss_stages(
    conn,
    species_slug: str = "broiler",
    product_slug: str | None = "whole_wing",
    include_optional: bool = False,
    chain_slug: str | None = None,
) -> list[LossStage]:
    """Load the loss chain.

    Factor resolution is by specificity: a factor naming this product beats
    a general one for the same stage. Optional stages (grow-out mortality)
    are excluded unless asked for.

    `chain_slug` lets a route declare its own losses. Without it, every chain
    got every stage, which is why `retail_shrink` had to be parked
    default-off: a restaurant route would otherwise have charged supermarket
    shrink on top of restaurant kitchen loss and double-counted. A grocery
    route can now claim retail shrink and skip the kitchen without either
    being globally disabled.
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

    declared = chain_loss_stages(conn, chain_slug) if chain_slug else None

    out: list[LossStage] = []
    seen: set[str] = set()
    for r in rows:
        if r["slug"] in seen:
            continue          # first row wins: most specific factor
        seen.add(r["slug"])

        if declared is not None:
            # The chain is explicit, so it decides -- including claiming a
            # stage that is optional or default-off for everyone else. That is
            # the point: retail shrink belongs to the grocery route and to no
            # other, and listing it here is how a route says so.
            if r["slug"] not in declared:
                continue
            out.append(_loss_stage_from_row(r))
            continue

        if r["optional"] and not include_optional:
            continue
        if not r["default_enabled"] and not include_optional:
            continue
        out.append(_loss_stage_from_row(r))
    return out


def default_supply_chain(conn, species_slug: str) -> str:
    """The default route for a species.

    `species_slug` is REQUIRED, deliberately. "What is the default supply
    chain?" is not a meaningful question without saying for what, and the fact
    that it used to be answerable is precisely how an egg query ended up
    walking the wing cascade -- a cut-up line, a wing chiller, size grading,
    a fryer basket -- and narrating all of it as though it had happened.

    There is no cross-species fallback for the same reason. Returning some
    other animal's route is worse than failing, because it fails silently and
    the audit trail then reads as confident and detailed fiction.
    """
    if not species_slug:
        raise ValueError(
            "species_slug is required; a species-less default chain is what "
            "let eggs inherit the wing cascade"
        )

    row = conn.execute(
        """SELECT sc.slug FROM supply_chain sc
           JOIN species s ON s.id = sc.species_id
           WHERE s.slug = ? AND sc.is_default = 1
           LIMIT 1""",
        (species_slug,),
    ).fetchone()
    if row:
        return row["slug"]

    raise LookupError(
        f"no default supply chain for species '{species_slug}'; mark one "
        f"is_default in a data/mixing*.yaml rather than borrowing another "
        f"species' route"
    )


def chain_floor_note(conn, chain_slug: str) -> str | None:
    """Prose explaining why the answer is not exactly the floor.

    Stored per chain because it used to be hardcoded wing text in both the CLI
    and the HTML, which meant anyone asking about eggs was told about deboning.
    """
    row = conn.execute(
        "SELECT floor_note FROM supply_chain WHERE slug = ?", (chain_slug,)
    ).fetchone()
    return row["floor_note"] if row else None


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
