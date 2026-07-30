"""Audit the database's citation coverage.

    python -m counting_chicken_wings.audit
    python -m counting_chicken_wings.audit --stats   # the README's own block

Exits non-zero if any statistic lacks a citation. Runs as its own CI job so
"is every number sourced?" is a visible check rather than a line buried in
a test log.

It also prints, without failing, how much of the model currently rests on
unsourced estimates. That number should go down over time; printing it
every build is what keeps it honest.

`--stats` exists because that honesty was being undermined by the README.
Its "Honesty about the data" section is the project's single most important
claim and it was hand-maintained, so it drifted three times -- most recently
to "7 of 12 are unsourced estimates" when the true figure was 11 of 21. The
direction of the error is what makes it serious: the README claimed the corpus
was *better sourced* than it is. Every figure it quotes is one the audit
already computes, so the README now generates that block from here and
`tests/test_readme.py` fails if the two disagree.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from .build import DEFAULT_DB, build

# Friendlier names for the report. Any table not listed falls back to its
# own name, so this is presentation only -- never a gate on what gets checked.
TABLE_LABELS = {
    "product": "products",
    "product_segment": "wing segments",
    "production_program": "production programs",
    "product_grade": "product grades",
    "producer": "producers",
    "loss_factor": "loss factors",
    "mixing_stage": "mixing stages",
    "slaughter_stat_year": "national slaughter stats",
    "regional_size_stat": "regional stats",
    "regional_production_year": "regional production stats",
    "regional_census_stat": "census state stats",
    "husbandry_stat_year": "husbandry stats",
    "quality_defect": "quality defects",
    "nutrition": "nutrition rows",
    "resource_footprint": "resource footprint",
    "economic_stat": "economic stats",
    "fact": "learning-centre facts",
}


def cited_tables(conn: sqlite3.Connection) -> list[tuple[str, str, bool]]:
    """Every table carrying a source_id, discovered from the schema.

    Returns (table, label, required). `required` comes from the schema's own
    NOT NULL declaration on source_id, because that is where the intent
    already lives:

      source_id INTEGER NOT NULL   a statistic. citation mandatory, and
                                   SQLite enforces it at insert time.
      source_id INTEGER            a dimension. "The United States exists"
                                   is not a claim and needs no citation.

    Deriving this rather than asserting it fixes a real failure. `country` is
    a dimension with a deliberately nullable source_id, but the audit
    demanded a citation anyway, exited 1, and took the Render build down --
    buildCommand runs the audit. Two parts of the codebase disagreed about
    the same contract, so now only one of them defines it.

    This list was hand-maintained twice and went stale twice, hence asking
    the database instead.
    """
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    out = []
    for t in tables:
        # run_step records which source a saved calculation used. It is a
        # runtime artifact, not curated data, so auditing it says nothing
        # about the corpus and reports an empty 0/0 on a fresh database.
        if t in {"run", "run_step"}:
            continue
        for c in conn.execute(f"PRAGMA table_info({t})"):
            if c[1] == "source_id":
                required = bool(c[3])          # PRAGMA column 3 is notnull
                out.append(
                    (t, TABLE_LABELS.get(t, t.replace("_", " ")), required)
                )
                break
    return out

CONFIDENCE_ORDER = ["measured", "derived", "study", "industry", "estimate"]

# The README delimits its generated block with these. Kept here rather than in
# the tool that writes them, because the test that checks for drift and the
# writer both need them and a second copy is a second thing to get wrong.
STATS_BEGIN = "<!-- BEGIN GENERATED: audit --stats -->"
STATS_END = "<!-- END GENERATED -->"


def corpus_stats(conn: sqlite3.Connection) -> dict:
    """Every figure the README quotes about the corpus, from the corpus.

    Deliberately excludes the test count. It is not a fact about the data, it
    changes on almost every commit, and quoting it was most of why the README
    went stale -- a number nobody can verify from the artifact it describes.
    """
    def scalar(sql: str) -> int:
        return conn.execute(sql).fetchone()[0]

    tables = cited_tables(conn)
    clauses = " ".join(
        f"AND NOT EXISTS (SELECT 1 FROM {t} WHERE source_id = s.id)"
        for t, _, _ in tables
    )

    confidence = dict(conn.execute(
        "SELECT confidence, COUNT(*) FROM loss_factor GROUP BY confidence"
    ).fetchall())
    factors = sum(confidence.values())
    estimates = confidence.get("estimate", 0)

    # Count-affecting is the distinction that matters and the one the README
    # has always drawn: a mass-only factor cannot move the answer however
    # uncertain it is. Same predicate as the report below -- if these two ever
    # disagree the README is wrong again, so they share one query shape.
    count_affecting = scalar("""
        SELECT COUNT(*) FROM loss_factor lf
        JOIN loss_stage ls ON ls.id = lf.loss_stage_id
        WHERE lf.confidence = 'estimate'
          AND ls.applies_to IN ('individual','product')
    """)

    return {
        "sources": scalar("SELECT COUNT(*) FROM source"),
        "orphan_sources": scalar(
            f"SELECT COUNT(*) FROM source s WHERE 1=1 {clauses}"
        ),
        "facts": scalar("SELECT COUNT(*) FROM fact"),
        "tables": scalar(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        ),
        "products": scalar("SELECT COUNT(*) FROM product"),
        "species_active": scalar("SELECT COUNT(*) FROM species WHERE active=1"),
        "loss_factors": factors,
        "estimates": estimates,
        "estimate_pct": round(100 * estimates / factors) if factors else 0,
        "count_affecting_estimates": count_affecting,
    }


def render_stats(stats: dict) -> str:
    """The README block, between its markers.

    Prose rather than a table, because this section is an argument and not a
    dashboard: the point is that *most* of the uncertainty cannot move the
    answer, which a bare percentage does not say.
    """
    s = stats
    mass_only = s["estimates"] - s["count_affecting_estimates"]
    lines = [
        STATS_BEGIN,
        "",
        f"Of the {s['loss_factors']} loss factors in the model, "
        f"**{s['estimates']} are unsourced estimates "
        f"({s['estimate_pct']}%)**. Only "
        f"{s['count_affecting_estimates']} of those affect the **count** "
        f"answer; the other {mass_only} are mass-only and cannot move it. "
        "That distinction is tracked and reported by the audit rather than "
        "glossed over.",
        "",
        f"Corpus: **{s['sources']} sources**, {s['facts']} facts, "
        f"{s['products']} products across {s['species_active']} active "
        f"species, {s['tables']} tables. Every statistic is cited and the "
        "build fails if one is not.",
        "",
        "*Generated by `python -m counting_chicken_wings.audit --stats`. "
        "Do not hand-edit — `tests/test_readme.py` fails on drift.*",
        "",
        STATS_END,
    ]
    return "\n".join(lines)


def stats_block(db_path: Path = DEFAULT_DB) -> str:
    """The generated block for a database path, building it if absent."""
    if not db_path.exists():
        build(db_path)
    conn = sqlite3.connect(db_path)
    try:
        return render_stats(corpus_stats(conn))
    finally:
        conn.close()


def audit(db_path: Path) -> int:
    if not db_path.exists():
        build(db_path)

    conn = sqlite3.connect(db_path)
    failures = 0

    tables = cited_tables(conn)

    print("citation coverage")
    for table, label, required in tables:
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        missing = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE source_id IS NULL"
        ).fetchone()[0]
        if missing == 0:
            mark = "ok  "
        elif required:
            mark = "FAIL"
        else:
            # Dimension table: uncited rows are expected, not a defect.
            mark = "dim "
        print(f"  [{mark}] {label:<28} {total - missing:>5}/{total:<5} cited")
        if required:
            failures += missing

    # Orphaned sources are not an error, but they usually mean a fact was
    # dropped and its citation was left behind.
    clauses = " ".join(
        f"AND NOT EXISTS (SELECT 1 FROM {t} WHERE source_id = s.id)"
        for t, _, _ in tables
    )
    orphans = conn.execute(
        f"SELECT s.slug FROM source s WHERE 1=1 {clauses} ORDER BY s.slug"
    ).fetchall()
    if orphans:
        print(f"\n  {len(orphans)} source(s) cited by nothing:")
        for (slug,) in orphans:
            print(f"    - {slug}")

    print("\nconfidence mix across loss factors")
    rows = conn.execute(
        "SELECT confidence, COUNT(*) FROM loss_factor GROUP BY confidence"
    ).fetchall()
    counts = dict(rows)
    total = sum(counts.values()) or 1
    for level in CONFIDENCE_ORDER:
        n = counts.get(level, 0)
        bar = "#" * round(30 * n / total)
        print(f"  {level:<10} {n:>3}  {bar}")

    est = counts.get("estimate", 0)
    print(f"\n  {est}/{total} loss factors rest on unsourced estimates "
          f"({est / total:.0%}).")
    if est:
        print("  These are listed as open items in docs/RESEARCH.md.")

    # Factors whose stage can move a count matter far more than mass-only
    # ones, which cannot shift the answer however uncertain they are.
    #
    # A stage legitimately holds several factors -- typically one per product
    # -- so name the product alongside the stage. Listing bare stage labels
    # made product-specific factors read as duplicates, which looked like a
    # data bug and inflated the apparent number of unsourced stages.
    critical = conn.execute("""
        SELECT ls.label, COALESCE(p.label, 'all products')
        FROM loss_factor lf
        JOIN loss_stage ls ON ls.id = lf.loss_stage_id
        LEFT JOIN product p ON p.id = lf.product_id
        WHERE lf.confidence = 'estimate'
          AND ls.applies_to IN ('individual','product')
        ORDER BY ls.sequence, p.label
    """).fetchall()
    if critical:
        stages = {label for label, _ in critical}
        print(f"\n  {len(critical)} of those affect the COUNT answer, "
              f"across {len(stages)} stage(s):")
        for label, prod in critical:
            print(f"    - {label}  [{prod}]")
    else:
        print("\n  None of them affect the count answer.")

    conn.close()

    if failures:
        print(f"\nFAILED: {failures} uncited statistic(s)", file=sys.stderr)
        return 1
    print("\nevery statistic is cited")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--stats" in argv:
        rest = [a for a in argv if a != "--stats"]
        print(stats_block(Path(rest[0]) if rest else DEFAULT_DB))
        return 0
    return audit(Path(argv[0]) if argv else DEFAULT_DB)


if __name__ == "__main__":
    raise SystemExit(main())
