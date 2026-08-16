"""Database access: load model inputs out of SQLite.

Kept deliberately thin. The maths lives in model.py with no database
dependency; this module's only job is turning rows into those dataclasses.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .build import DEFAULT_DB, build
from .model import (CorrelatedGroup, LossStage, MixingParams, MixingStage,
                    RecurringYield)

# A recurring product needs a window before it means anything, and the right
# default is a property of the PRODUCT, not of the module. It lived here as a
# flat 1.0 while eggs were the only recurring subject, and maple inherited it:
# a tree whose sap runs for six weeks a year was asked how many of it fit into
# one day, and answered 194. The default now comes from the row --
# `default_window_days`, falling back to the product's own season.


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

    # An unasked window falls to the product's own default, and from there to
    # its production period. A season is the honest answer for anything
    # seasonal: asking a maple for one day's worth is asking a question the
    # tree does not answer.
    default = _row_get(product, "default_window_days") or period

    return RecurringYield(
        units_per_period=product["units_per_individual_mode"],
        period_days=period,
        window_days=window_days or default,
        max_units_per_day=product["max_units_per_day"],
    )


def _row_get(row, key, default=None):
    """Column value, or `default` if the row does not carry that column.

    Rows reach the model from several queries, not all of which select every
    column. Tolerating that here beats each caller guarding it.
    """
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


def list_products(conn) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT p.slug, p.label, p.label_plural, p.display_name,
                  p.unit_name, p.yield_mode,
                  p.yield_period_days, p.max_units_per_day,
                  s.common_name AS species, s.slug AS species_slug,
                  s.individual_plural, s.active
           FROM product p JOIN species s ON s.id = p.species_id
           ORDER BY s.active DESC,
                    COALESCE(p.display_name, p.label) COLLATE NOCASE,
                    p.slug"""
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


def load_correlated_groups(
    conn, species_slug: str = "broiler",
) -> list[CorrelatedGroup]:
    """Which loss stages are NOT independent of one another (#77).

    Restricted to stages the given species actually has -- a group
    referencing a stage id that exists for a species with no factor row
    would otherwise leak in as an empty, meaningless group.
    """
    rows = conn.execute(
        """
        SELECT g.slug, g.label, g.rho, g.confidence, src.slug AS source_slug,
               ls.slug AS stage_slug
        FROM loss_correlation_group g
        JOIN loss_correlation_group_stage gs ON gs.group_id = g.id
        JOIN loss_stage ls ON ls.id = gs.loss_stage_id
        JOIN source src ON src.id = g.source_id
        JOIN loss_factor lf ON lf.loss_stage_id = ls.id
        JOIN species sp ON sp.id = lf.species_id
        WHERE sp.slug = ?
        """,
        (species_slug,),
    ).fetchall()

    groups: dict[str, CorrelatedGroup] = {}
    for r in rows:
        g = groups.get(r["slug"])
        if g is None:
            g = CorrelatedGroup(
                slug=r["slug"], label=r["label"], rho=r["rho"],
                confidence=r["confidence"], source_slug=r["source_slug"],
                stage_slugs=[],
            )
            groups[r["slug"]] = g
        if r["stage_slug"] not in g.stage_slugs:
            g.stage_slugs.append(r["stage_slug"])

    # A group naming only one (or zero) stages for this species has nothing
    # left to correlate, so it is dropped rather than sampled as a no-op.
    return [g for g in groups.values() if len(g.stage_slugs) > 1]


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
    """Every route, WITH the species it belongs to.

    `species_slug` is not decoration. `is_default` is per-species by design --
    the unique index enforces exactly that -- so three species means three rows
    with is_default = 1, and any caller that renders them as one flat list and
    marks each default `selected` ends up with whichever sorts last. That is
    precisely what happened when saffron landed: the wing calculator opened on
    "Commodity spice trade", and a chicken question was about to be narrated
    through a saffron picking tray.

    A caller cannot filter by species without being told the species, so it is
    returned here rather than left to be inferred from a label.
    """
    return conn.execute(
        "SELECT sc.slug, sc.label, sc.description, sc.is_default, "
        "       s.slug AS species_slug "
        "FROM supply_chain sc "
        "LEFT JOIN species s ON s.id = sc.species_id "
        "ORDER BY sc.is_default DESC, sc.slug"
    ).fetchall()


def load_mixing_params(conn) -> MixingParams:
    """The mixing model's scalar parameters, from the corpus.

    This function is the ONLY way the shipped values reach the model. There
    is deliberately no Python default carrying them -- `MixingParams()` turns
    every mechanism off -- because a second copy of an audited figure is the
    bug this table exists to fix.

    A missing row falls back to the inert default rather than to a guess, so
    the failure mode of a half-loaded corpus is "the model assumes nothing",
    which is visible in the answer and is the honest direction to fail in.
    """
    rows = conn.execute(
        "SELECT slug, value_mode FROM model_parameter"
    ).fetchall()
    have = {r["slug"]: r["value_mode"] for r in rows}
    inert = MixingParams()

    def pick(slug: str, fallback: float) -> float:
        v = have.get(slug)
        return fallback if v is None else float(v)

    return MixingParams(
        separation_efficiency=pick(
            "separation_efficiency", inert.separation_efficiency),
        draw_cluster_size=pick(
            "draw_cluster_size", inert.draw_cluster_size),
        adjacency_retention_random=pick(
            "adjacency_retention_random", inert.adjacency_retention_random),
        adjacency_retention_passthrough=pick(
            "adjacency_retention_passthrough",
            inert.adjacency_retention_passthrough),
    )


def load_mixing_param_bands(
    conn,
) -> dict[str, tuple[str, float, float, float, str]]:
    """The same four parameters, with the bands `load_mixing_params` drops.

    Returns slug -> (label, lo, mode, hi, confidence). Deliberately a sibling
    rather than a wider return type on `load_mixing_params`, whose
    `MixingParams` result is load-bearing in `api.py`, `cli.py` and
    `test_scientific.py`.

    `schema.sql` says of these columns that they are a triangular band "so
    the Monte Carlo can resample these the same way it resamples pools", and
    until `model.variance_decomposition` nothing read them -- `run`'s
    docstring has carried that as a known open item. This is the loader that
    closes it.
    """
    return {
        r["slug"]: (r["label"], float(r["value_lo"]), float(r["value_mode"]),
                    float(r["value_hi"]), r["confidence"])
        for r in conn.execute(
            "SELECT slug, label, value_lo, value_mode, value_hi, confidence "
            "FROM model_parameter"
        ).fetchall()
    }


def load_mixing_stages(conn, chain_slug: str) -> list[MixingStage]:
    rows = conn.execute(
        """
        SELECT ms.slug, ms.label, ms.mixing_kind, ms.description,
               ms.confidence, src.slug AS source_slug,
               COALESCE(scs.pool_override, ms.pool_mode) AS pool,
               ms.pool_lo, ms.pool_mode, ms.pool_hi, scs.pool_override
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
        # Rescale proportionally so the override keeps the default band's
        # SHAPE: an override of 40 against a default 500/2,000/8,000 band
        # samples a 10-160 range, not a single point at 40.
        if r["pool_override"] is not None:
            mode = r["pool_mode"] or r["pool_override"]
            lo = max(1, round(r["pool_override"] * (r["pool_lo"] or mode) / mode))
            hi = max(lo, round(r["pool_override"] * (r["pool_hi"] or mode) / mode))
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


def product_source_slug(conn, product_slug: str) -> str | None:
    """The citation behind a product's units-per-individual figure.

    The floor step of the audit trail had no source attached, which was
    tolerable while every floor was an anatomical constant that needed none.
    A saffron gram's floor rests on one extension service's estimate, so the
    trail has to say whose.
    """
    row = conn.execute(
        """SELECT src.slug FROM product p
           JOIN source src ON src.id = p.source_id
           WHERE p.slug = ?""",
        (product_slug,),
    ).fetchone()
    return row["slug"] if row else None


# The regional stat table holds broiler pounds and layer eggs-per-year in the
# same `avg_size` column, so it is read through per-species views only. Naming
# the view per species rather than filtering on a species column means a
# species with no view fails loudly instead of returning mixed units.
SIZE_VIEW_BY_SPECIES = {
    "broiler": "v_broiler_size_stat",
    "layer_hen": "v_layer_egg_stat",
}


def latest_broiler_size_year(conn) -> int | None:
    """The most recent year with an annual (non-monthly) broiler size row.

    `/api/states` used to default its `year` query param to a literal 2025.
    The instant the corpus rolls forward past a hardcoded year, that endpoint
    would render an empty map and a header-only table with no explanation --
    this is what it should ask instead: whatever year is actually there.
    """
    row = conn.execute(
        "SELECT MAX(year) AS year FROM v_broiler_size_stat WHERE month IS NULL"
    ).fetchone()
    return row["year"] if row and row["year"] is not None else None


def latest_monthly_size_year(conn, species_slug: str = "broiler") -> int | None:
    """The most recent year with a full monthly series for `species_slug`.

    Same reasoning as `latest_broiler_size_year`: `/api/seasonality`
    hardcoded 2025 too, and rolling past it turned into a silent 404 (the
    frontend's `load()` swallows it) rather than a working default.
    """
    view = SIZE_VIEW_BY_SPECIES.get(species_slug)
    if view is None:
        return None
    row = conn.execute(
        f"SELECT MAX(year) AS year FROM {view} WHERE month IS NOT NULL"
    ).fetchone()
    return row["year"] if row and row["year"] is not None else None


def monthly_size_series(
    conn, year: int = 2025, species_slug: str = "broiler",
) -> dict[str, dict]:
    """Every region's twelve monthly figures for one year.

    Returns `{region: {"values": [12 entries, January first], "unit": str,
    "source_slug": str}}`. A month NASS does not publish stays None -- it is
    not carried forward from its neighbour, because a filled gap is a figure
    we made up.
    """
    view = SIZE_VIEW_BY_SPECIES.get(species_slug)
    if view is None:
        raise ValueError(
            f"no monthly series view for species {species_slug!r}; "
            f"known: {', '.join(sorted(SIZE_VIEW_BY_SPECIES))}"
        )
    rows = conn.execute(
        f"""SELECT r.region, r.month, r.avg_size, r.size_unit,
                   s.slug AS source_slug
            FROM {view} r
            JOIN source s ON s.id = r.source_id
            WHERE r.year = ? AND r.month IS NOT NULL
            ORDER BY r.region, r.month""",
        (year,),
    ).fetchall()

    out: dict[str, dict] = {}
    for r in rows:
        entry = out.setdefault(r["region"], {
            "values": [None] * 12,
            "unit": r["size_unit"],
            "source_slug": r["source_slug"],
        })
        entry["values"][r["month"] - 1] = r["avg_size"]
    return out


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
