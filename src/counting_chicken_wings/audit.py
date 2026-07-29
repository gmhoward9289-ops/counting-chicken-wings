"""Audit the database's citation coverage.

    python -m counting_chicken_wings.audit

Exits non-zero if any statistic lacks a citation. Runs as its own CI job so
"is every number sourced?" is a visible check rather than a line buried in
a test log.

It also prints, without failing, how much of the model currently rests on
unsourced estimates. That number should go down over time; printing it
every build is what keeps it honest.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from .build import DEFAULT_DB, build

# (table, human label) for everything that must carry a source.
CITED_TABLES = [
    ("product", "products"),
    ("product_segment", "wing segments"),
    ("production_program", "production programs"),
    ("product_grade", "product grades"),
    ("producer", "producers"),
    ("loss_factor", "loss factors"),
    ("mixing_stage", "mixing stages"),
    ("slaughter_stat_year", "national slaughter stats"),
    ("regional_size_stat", "regional stats"),
    ("husbandry_stat_year", "husbandry stats"),
    ("fact", "learning-centre facts"),
]

CONFIDENCE_ORDER = ["measured", "derived", "study", "industry", "estimate"]


def audit(db_path: Path) -> int:
    if not db_path.exists():
        build(db_path)

    conn = sqlite3.connect(db_path)
    failures = 0

    print("citation coverage")
    for table, label in CITED_TABLES:
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        missing = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE source_id IS NULL"
        ).fetchone()[0]
        mark = "ok " if missing == 0 else "FAIL"
        print(f"  [{mark}] {label:<28} {total - missing:>5}/{total:<5} cited")
        failures += missing

    # Orphaned sources are not an error, but they usually mean a fact was
    # dropped and its citation was left behind.
    orphans = conn.execute("""
        SELECT s.slug FROM source s
        WHERE NOT EXISTS (SELECT 1 FROM loss_factor      WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM fact             WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM product          WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM product_segment  WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM producer         WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM mixing_stage     WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM slaughter_stat_year   WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM regional_size_stat    WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM husbandry_stat_year   WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM production_program    WHERE source_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM product_grade         WHERE source_id = s.id)
        ORDER BY s.slug
    """).fetchall()
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
    return audit(Path(argv[0]) if argv else DEFAULT_DB)


if __name__ == "__main__":
    raise SystemExit(main())
