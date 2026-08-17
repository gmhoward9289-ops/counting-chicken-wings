"""Export the dataset as plain .txt and .csv.

    wings export [--dir data/exports]

Two audiences, one mechanism. Local models read small plain-text fragments
far faster than they parse a SQLite file, and humans citing the data need
something that opens in a spreadsheet. Both get the same provenance header,
so a fragment lifted out of context still says where its numbers came from.

Deliberately chunked: one file per topic rather than one big dump, and every
file carries its own header. A model handed `facts.txt` alone should be able
to work with it without the rest of the repo.
"""

from __future__ import annotations

import csv
import io
import sys
from datetime import date
from pathlib import Path

from . import db as dbm
from .brand import export_header

# One entry per exported table. Kept declarative so adding a topic is a row
# here rather than a new function.
EXPORTS: list[dict] = [
    {
        "name": "facts",
        "title": "chicken facts",
        "sql": """SELECT f.slug, f.headline, f.body, f.surprise,
                         f.placement, s.title AS source, s.publisher, s.url
                  FROM fact f JOIN source s ON s.id = f.source_id
                  ORDER BY f.surprise DESC, f.slug""",
        "note": "surprise is 1-5; higher means more counterintuitive",
    },
    {
        "name": "sources",
        "title": "citations",
        "sql": """SELECT slug, title, publisher, source_type, published_on,
                         retrieved_on, url, notes
                  FROM source ORDER BY source_type, slug""",
        "note": "every statistic in this dataset cites one of these",
    },
    {
        "name": "loss_chain",
        "title": "loss chain",
        "sql": """SELECT ls.sequence, ls.slug, ls.label, ls.phase,
                         ls.applies_to, ls.optional, ls.default_enabled,
                         COALESCE(p.slug, 'all') AS product,
                         lf.survive_lo, lf.survive_mode, lf.survive_hi,
                         lf.confidence, s.slug AS source
                  FROM loss_factor lf
                  JOIN loss_stage ls ON ls.id = lf.loss_stage_id
                  JOIN source s ON s.id = lf.source_id
                  LEFT JOIN product p ON p.id = lf.product_id
                  WHERE lf.valid_to IS NULL
                  ORDER BY ls.sequence, p.slug""",
        "note": ("survive_* are SURVIVING fractions, not loss fractions. "
                 "applies_to='mass' stages cannot change a unit count"),
    },
    {
        "name": "mixing_cascade",
        "title": "mixing cascade",
        "sql": """SELECT ms.sequence, ms.slug, ms.label, ms.mixing_kind,
                         ms.pool_lo, ms.pool_mode, ms.pool_hi,
                         ms.confidence, ms.description, s.slug AS source
                  FROM mixing_stage ms JOIN source s ON s.id = ms.source_id
                  ORDER BY ms.sequence""",
        "note": ("pool sizes are in INDIVIDUALS. mixing_kind='separating' "
                 "actively splits one bird's units into different streams"),
    },
    {
        "name": "states",
        "title": "average live weight by state",
        "sql": """SELECT region, year, avg_size AS avg_live_weight_lb,
                         volume AS certified_klb
                  FROM v_broiler_size_stat
                  WHERE month IS NULL ORDER BY year DESC, avg_size DESC""",
        "note": "USDA NASS. Only states NASS publishes individually appear",
    },
    {
        "name": "states_census",
        "title": "broiler presence by state, Census of Agriculture",
        "sql": """SELECT region, census_year, sales_head, operations,
                         inventory
                  FROM v_broiler_census_stat ORDER BY region""",
        "note": ("USDA Census of Agriculture, five-yearly, ALL 50 states -- "
                 "no state is suppressed here. sales_head is a sales count, "
                 "not the head_slaughtered/certified_klb in states.csv; the "
                 "two are different USDA programmes and must not be summed "
                 "or averaged together"),
    },
    {
        "name": "states_monthly",
        "title": "average live weight by state and month",
        "sql": """SELECT region, year, month, avg_size AS avg_live_weight_lb
                  FROM v_broiler_size_stat
                  WHERE month IS NOT NULL
                  ORDER BY region, year DESC, month""",
        "note": ("USDA NASS. A month NASS suppresses is an ABSENT ROW, never a "
                 "zero. The swing across these months is not a season on its "
                 "own for any state -- see GET /api/seasonality"),
    },
    {
        "name": "national",
        "title": "national slaughter totals",
        "sql": """SELECT year, head_slaughtered, live_weight_lb,
                         certified_rtc_lb, avg_live_weight_lb,
                         postmortem_condemn_pct,
                         ROUND(CAST(certified_rtc_lb AS REAL)
                               / live_weight_lb, 5) AS dressing_yield
                  FROM slaughter_stat_year ORDER BY year DESC""",
        "note": "dressing_yield is derived, not reported: RTC / live weight",
    },
    {
        "name": "husbandry",
        "title": "grow-out performance by year",
        "sql": """SELECT year, cycle_days AS market_age_days,
                         end_size AS market_weight_lb, feed_conversion,
                         mortality_pct
                  FROM husbandry_stat_year ORDER BY year DESC""",
        "note": "National Chicken Council series",
    },
    {
        "name": "quality_defects",
        "title": "meat quality defects",
        "sql": """SELECT q.slug, q.label, q.affected_part, q.severity,
                         q.prevalence_pct_mode, q.weight_association,
                         q.first_year, q.first_year_pct, s.slug AS source
                  FROM quality_defect q JOIN source s ON s.id = q.source_id
                  ORDER BY q.prevalence_pct_mode DESC""",
        "note": ("these degrade quality without removing product, so they "
                 "are NOT part of the loss chain"),
    },
    {
        "name": "nutrition",
        "title": "nutrition per 100g",
        "sql": """SELECT p.slug AS product, n.preparation, n.label, n.kcal,
                         n.protein_g, n.fat_g, n.carbohydrate_g,
                         n.edible_g_per_unit, n.fdc_id, s.slug AS source
                  FROM nutrition n
                  JOIN product p ON p.id = n.product_id
                  JOIN source s ON s.id = n.source_id
                  ORDER BY p.slug, n.preparation""",
        "note": "USDA FoodData Central. Per 100 g edible portion",
    },
    {
        "name": "footprint",
        "title": "resource footprint per bird",
        "sql": """SELECT r.metric, r.label, r.unit, r.per_individual,
                         r.per_kg_liveweight, r.reference_lw_lb, r.year,
                         r.pct_change_decade, r.notes, s.slug AS source
                  FROM resource_footprint r JOIN source s ON s.id = r.source_id
                  ORDER BY r.metric""",
        "note": ("PER BIRD. Allocate by mass share before charging to one "
                 "cut -- wings are ~7.3% of live weight. Metrics are not "
                 "like-for-like: read notes per row, scope differs (e.g. "
                 "electricity is on-farm growout only, the rest are "
                 "whole-lifecycle blended-bird figures)"),
    },
    {
        "name": "economics",
        "title": "economic measures",
        "sql": """SELECT e.slug, e.label, e.value_lo, e.value_mode,
                         e.value_hi, e.unit, e.basis, e.confidence,
                         s.slug AS source
                  FROM economic_stat e JOIN source s ON s.id = e.source_id
                  ORDER BY e.slug""",
        "note": "",
    },
    {
        "name": "producers",
        "title": "producers",
        "sql": """SELECT p.slug, p.name, p.headquarters, p.market_share_pct,
                         p.throughput_per_week, p.facility_count,
                         p.as_of_year, s.slug AS source
                  FROM producer p JOIN source s ON s.id = p.source_id
                  ORDER BY p.market_share_pct DESC""",
        "note": "",
    },
]


def _rows(conn, sql: str) -> tuple[list[str], list[tuple]]:
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    return cols, cur.fetchall()


def _csv(cols: list[str], rows: list[tuple]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue()


def _txt(cols: list[str], rows: list[tuple], wrap: int = 78) -> str:
    """Key: value blocks, one record per stanza.

    Chosen over aligned columns on purpose. A wide table wraps into
    unreadable soup in a plain-text window, and a model reading a fragment
    does better with explicit `key: value` than with positional columns whose
    header may have scrolled out of the chunk it was given.
    """
    out = []
    for i, r in enumerate(rows, 1):
        out.append(f"[{i}]")
        for c, v in zip(cols, r):
            if v is None or v == "":
                continue
            text = str(v).replace("\n", " ").strip()
            if len(text) <= wrap:
                out.append(f"  {c}: {text}")
            else:
                out.append(f"  {c}:")
                line = ""
                for word in text.split():
                    if len(line) + len(word) + 1 > wrap - 4:
                        out.append(f"    {line}")
                        line = word
                    else:
                        line = f"{line} {word}".strip()
                if line:
                    out.append(f"    {line}")
        out.append("")
    return "\n".join(out)


def export(out_dir: Path, db_path: Path | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = dbm.connect(db_path)
    today = date.today().isoformat()
    written: list[Path] = []
    index: list[tuple[str, int, str]] = []

    try:
        for spec in EXPORTS:
            cols, rows = _rows(conn, spec["sql"])
            header = export_header(spec["title"], today, spec.get("note", ""))

            csv_path = out_dir / f"{spec['name']}.csv"
            # No comment header in the CSV: a leading '#' line breaks every
            # spreadsheet import. Provenance lives in the .txt twin and in
            # the source column on each row.
            csv_path.write_text(_csv(cols, rows), encoding="utf-8")
            written.append(csv_path)

            txt_path = out_dir / f"{spec['name']}.txt"
            txt_path.write_text(
                f"{header}\n\n{_txt(cols, rows)}", encoding="utf-8")
            written.append(txt_path)

            index.append((spec["name"], len(rows), spec["title"]))
    finally:
        conn.close()

    readme = out_dir / "README.txt"
    lines = [
        export_header("dataset index", today,
                      "regenerate with: wings export"),
        "",
        "Every file has a .csv twin for spreadsheets and a .txt twin for",
        "reading. Files are kept small and self-describing so any one of",
        "them is usable on its own.",
        "",
    ]
    width = max(len(n) for n, _, _ in index)
    for name, n, title in index:
        lines.append(f"  {name:<{width}}  {n:>5} rows  {title}")
    lines += [
        "",
        "Numbers to read carefully:",
        "  loss_chain      survive_* are SURVIVING fractions. applies_to",
        "                  'mass' rows cannot change a unit count.",
        "  footprint       per BIRD. Allocate by mass share before charging",
        "                  to one cut.",
        "  quality_defects degrade quality without removing product, so they",
        "                  are not part of the loss chain.",
        "  states          only states USDA's annual survey publishes",
        "                  individually appear here; others are suppressed",
        "                  for disclosure. states_census has all 50, from a",
        "                  different, five-yearly programme -- do not merge",
        "                  the two: sales_head is not head_slaughtered.",
        "",
    ]
    readme.write_text("\n".join(lines), encoding="utf-8")
    written.append(readme)
    return written


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="wings export")
    p.add_argument("--dir", default="data/exports")
    p.add_argument("--db", default=None)
    a = p.parse_args(argv if argv is not None else sys.argv[1:])

    files = export(Path(a.dir), Path(a.db) if a.db else None)
    total = sum(f.stat().st_size for f in files)
    print(f"wrote {len(files)} files to {a.dir} ({total / 1024:.1f} KB)")
    for f in sorted(files):
        print(f"  {f.name:<24} {f.stat().st_size:>7,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
