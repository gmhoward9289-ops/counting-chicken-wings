"""Build the chicken-stats database from the YAML corpus.

    python -m counting_chicken_wings.build

Rebuilds from scratch every time. The database is a build artifact and is
gitignored; the YAML under data/ is the source of truth, so git history
records what was learned and when.

The build refuses to insert a statistic whose source slug is unknown. That
is the project's central guarantee -- no number without a citation --
enforced at load time as well as by the schema's NOT NULL constraints.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import yaml

PKG = Path(__file__).parent
ROOT = PKG.parent.parent
DATA = ROOT / "data"
SCHEMA = PKG / "schema.sql"
DEFAULT_DB = ROOT / "chickens.db"


class BuildError(Exception):
    pass


def load(name: str):
    p = DATA / name
    if not p.exists():
        raise BuildError(f"missing data file: {p}")
    with p.open() as fh:
        return yaml.safe_load(fh)


class Builder:
    def __init__(self, conn: sqlite3.Connection):
        self.c = conn
        self.source: dict[str, int] = {}
        self.domain: dict[str, int] = {}
        self.species: dict[str, int] = {}
        self.product: dict[str, int] = {}
        self.program: dict[str, int] = {}
        self.producer: dict[str, int] = {}
        self.loss_stage: dict[str, int] = {}
        self.mixing_stage: dict[str, int] = {}
        self.counts: dict[str, int] = {}

    # -- helpers ----------------------------------------------------------

    def ins(self, table: str, **cols) -> int:
        cols = {k: v for k, v in cols.items() if v is not None}
        names = ",".join(cols)
        marks = ",".join("?" * len(cols))
        cur = self.c.execute(
            f"INSERT INTO {table} ({names}) VALUES ({marks})",
            list(cols.values()),
        )
        self.counts[table] = self.counts.get(table, 0) + 1
        return cur.lastrowid

    def src(self, slug: str | None, ctx: str) -> int | None:
        """Resolve a source slug, failing loudly on typos."""
        if slug is None:
            return None
        if slug not in self.source:
            raise BuildError(
                f"{ctx}: unknown source '{slug}'. "
                f"Every statistic must cite a source defined in sources.yaml."
            )
        return self.source[slug]

    # -- loaders ----------------------------------------------------------

    def sources(self):
        rows = load("sources.yaml")
        deferred = []
        for r in rows:
            sid = self.ins(
                "source",
                slug=r["slug"], title=r["title"], publisher=r["publisher"],
                url=r.get("url"), published_on=r.get("published_on"),
                retrieved_on=r["retrieved_on"], source_type=r["source_type"],
                notes=r.get("notes"),
            )
            self.source[r["slug"]] = sid
            for parent in r.get("derived_from", []):
                deferred.append((sid, parent))
        for child, parent in deferred:
            self.c.execute(
                "INSERT INTO source_derivation "
                "(derived_source_id, parent_source_id) VALUES (?,?)",
                (child, self.src(parent, "source_derivation")),
            )

    def taxonomy(self):
        t = load("taxonomy.yaml")

        for d in t["domains"]:
            self.domain[d["slug"]] = self.ins(
                "domain", slug=d["slug"], label=d["label"],
                description=d.get("description"), active=d.get("active", 1),
            )

        for s in t["species"]:
            self.species[s["slug"]] = self.ins(
                "species",
                domain_id=self.domain[s["domain"]],
                slug=s["slug"], common_name=s["common_name"],
                scientific_name=s.get("scientific_name"),
                individual_noun=s["individual_noun"],
                individual_plural=s["individual_plural"],
                stat_category=s.get("stat_category"),
                active=s.get("active", 1),
            )

        for p in t["products"]:
            self.product[p["slug"]] = self.ins(
                "product",
                species_id=self.species[p["species"]],
                slug=p["slug"], label=p["label"],
                label_plural=p["label_plural"], yield_mode=p["yield_mode"],
                units_per_individual_lo=p["units_per_individual_lo"],
                units_per_individual_mode=p["units_per_individual_mode"],
                units_per_individual_hi=p["units_per_individual_hi"],
                unit_name=p["unit_name"],
                is_anatomical_constant=p.get("is_anatomical_constant", 0),
                source_part=p.get("source_part"),
                named_part=p.get("named_part"),
                named_part_content=p.get("named_part_content", 1.0),
                source_id=self.src(p["source"], f"product {p['slug']}"),
                notes=p.get("notes"),
            )

        for s in t.get("segments", []):
            self.ins(
                "product_segment",
                product_id=self.product[s["product"]],
                slug=s["slug"], label=s["label"],
                per_product_count=s.get("per_product_count", 1),
                mass_grams=s.get("mass_grams"),
                edible_yield_pct=s.get("edible_yield_pct"),
                sold_as_product=s.get("sold_as_product", 1),
                source_id=self.src(s["source"], f"segment {s['slug']}"),
                notes=s.get("notes"),
            )

        for p in t.get("programs", []):
            self.program[p["slug"]] = self.ins(
                "production_program",
                species_id=self.species[p["species"]],
                slug=p["slug"], label=p["label"],
                size_lo=p.get("size_lo"), size_mode=p.get("size_mode"),
                size_hi=p.get("size_hi"), size_unit=p.get("size_unit"),
                typical_market=p.get("typical_market"),
                source_id=self.src(p["source"], f"program {p['slug']}"),
                notes=p.get("notes"),
            )

        for g in t.get("grades", []):
            self.ins(
                "product_grade",
                product_id=self.product[g["product"]],
                slug=g["slug"], label=g["label"],
                units_per_lb_lo=g.get("units_per_lb_lo"),
                units_per_lb_hi=g.get("units_per_lb_hi"),
                typical_program_id=self.program.get(g.get("typical_program")),
                source_id=self.src(g["source"], f"grade {g['slug']}"),
            )

    def producers(self):
        t = load("producers.yaml")
        for p in t.get("producers", []):
            self.producer[p["slug"]] = self.ins(
                "producer",
                domain_id=self.domain[p["domain"]],
                slug=p["slug"], name=p["name"],
                headquarters=p.get("headquarters"),
                market_share_pct=p.get("market_share_pct"),
                throughput_per_week=p.get("throughput_per_week"),
                facility_count=p.get("facility_count"),
                source_id=self.src(p["source"], f"producer {p['slug']}"),
                as_of_year=p.get("as_of_year"), notes=p.get("notes"),
            )

    def loss_chain(self):
        t = load("loss_chain.yaml")
        for st in t["stages"]:
            sid = self.ins(
                "loss_stage",
                domain_id=self.domain[st["domain"]],
                slug=st["slug"], label=st["label"], sequence=st["sequence"],
                phase=st["phase"], applies_to=st["applies_to"],
                optional=st.get("optional", 0),
                default_enabled=st.get("default_enabled", 1),
                description=st["description"], notes=st.get("notes"),
            )
            self.loss_stage[st["slug"]] = sid
            for f in st.get("factors", []):
                self.ins(
                    "loss_factor",
                    loss_stage_id=sid,
                    species_id=self.species[f["species"]],
                    product_id=self.product.get(f.get("product")),
                    producer_id=self.producer.get(f.get("producer")),
                    program_id=self.program.get(f.get("program")),
                    region=f.get("region"), year=f.get("year"),
                    survive_lo=f["survive_lo"],
                    survive_mode=f["survive_mode"],
                    survive_hi=f["survive_hi"],
                    confidence=f["confidence"],
                    source_id=self.src(f["source"], f"factor {st['slug']}"),
                    notes=f.get("notes"),
                )

    def mixing(self):
        t = load("mixing.yaml")
        for st in t["stages"]:
            self.mixing_stage[st["slug"]] = self.ins(
                "mixing_stage",
                domain_id=self.domain[st["domain"]],
                slug=st["slug"], label=st["label"], sequence=st["sequence"],
                pool_lo=st["pool_lo"], pool_mode=st["pool_mode"],
                pool_hi=st["pool_hi"], mixing_kind=st["mixing_kind"],
                source_id=self.src(st["source"], f"mixing {st['slug']}"),
                confidence=st["confidence"], description=st["description"],
            )

        for ch in t.get("supply_chains", []):
            cid = self.ins(
                "supply_chain",
                domain_id=self.domain[ch["domain"]],
                slug=ch["slug"], label=ch["label"],
                description=ch["description"],
                is_default=ch.get("is_default", 0),
            )
            for entry in ch.get("stages", []):
                if isinstance(entry, str):
                    slug, override = entry, None
                else:
                    slug, override = entry["slug"], entry.get("pool_override")
                if slug not in self.mixing_stage:
                    raise BuildError(
                        f"supply_chain {ch['slug']}: unknown stage '{slug}'"
                    )
                self.c.execute(
                    "INSERT INTO supply_chain_stage "
                    "(supply_chain_id, mixing_stage_id, pool_override) "
                    "VALUES (?,?,?)",
                    (cid, self.mixing_stage[slug], override),
                )

    def stats(self):
        t = load("stats_national.yaml")

        sl = t["slaughter"]
        sp = self.species[sl["species"]]
        sid = self.src(sl["source"], "slaughter stats")
        for y in sl["years"]:
            self.ins(
                "slaughter_stat_year",
                species_id=sp, year=y["year"],
                head_slaughtered=y.get("head_slaughtered"),
                live_weight_lb=y.get("live_weight_lb"),
                certified_rtc_lb=y.get("certified_rtc_lb"),
                avg_live_weight_lb=y.get("avg_live_weight_lb"),
                postmortem_condemn_pct=y.get("postmortem_condemn_pct"),
                postmortem_condemn_lb=y.get("postmortem_condemn_lb"),
                source_id=sid,
            )

        hb = t["husbandry"]
        sp = self.species[hb["species"]]
        sid = self.src(hb["source"], "husbandry stats")
        for y in hb["years"]:
            self.ins(
                "husbandry_stat_year",
                species_id=sp, year=y["year"],
                cycle_days=y.get("cycle_days"), end_size=y.get("end_size"),
                size_unit=hb.get("size_unit"),
                feed_conversion=y.get("feed_conversion"),
                mortality_pct=y.get("mortality_pct"), source_id=sid,
            )

        st = load("stats_states.yaml")
        sp = self.species[st["species"]]
        sid = self.src(st["source"], "state stats")
        unit = st.get("size_unit", "lb")
        for r in st["regions"]:
            for year, key, ckey in (
                (2025, "annual_2025_live_weight_lb",
                 "annual_2025_certified_klb"),
                (2024, "annual_2024_live_weight_lb",
                 "annual_2024_certified_klb"),
            ):
                if r.get(key) is None:
                    continue
                self.ins(
                    "regional_size_stat",
                    species_id=sp, region=r["region"], year=year, month=None,
                    avg_size=r[key], size_unit=unit,
                    volume=int(r[ckey]) if r.get(ckey) else None,
                    volume_unit="1,000 lb ready-to-cook" if r.get(ckey) else None,
                    source_id=sid,
                )
            for i, m in enumerate(
                ["jan", "feb", "mar", "apr", "may", "jun",
                 "jul", "aug", "sep", "oct", "nov", "dec"], start=1
            ):
                v = (r.get("monthly_live_weight_lb") or {}).get(m)
                if v is None:
                    continue
                self.ins(
                    "regional_size_stat",
                    species_id=sp, region=r["region"], year=2025, month=i,
                    avg_size=v, size_unit=unit, source_id=sid,
                )

    def facts(self):
        t = load("facts.yaml")
        dom = self.domain.get("poultry")
        for f in t["facts"]:
            self.ins(
                "fact",
                slug=f["slug"], domain_id=dom,
                headline=f["headline"], body=f["body"].strip(),
                placement=f["placement"], surprise=f.get("surprise", 3),
                source_id=self.src(f["source"], f"fact {f['slug']}"),
            )

    def nutrition(self):
        t = load("nutrition.yaml")
        for n in t["nutrition"]:
            self.ins(
                "nutrition",
                product_id=self.product[n["product"]],
                preparation=n["preparation"], label=n["label"],
                kcal=n.get("kcal"), protein_g=n.get("protein_g"),
                fat_g=n.get("fat_g"),
                saturated_fat_g=n.get("saturated_fat_g"),
                carbohydrate_g=n.get("carbohydrate_g"),
                sodium_mg=n.get("sodium_mg"),
                cholesterol_mg=n.get("cholesterol_mg"),
                edible_g_per_unit=n.get("edible_g_per_unit"),
                fdc_id=n.get("fdc_id"),
                source_id=self.src(n["source"],
                                   f"nutrition {n['preparation']}"),
                notes=n.get("notes"),
            )

    def resources(self):
        t = load("resources.yaml")

        fp = t["footprint"]
        sp = self.species[fp["species"]]
        sid = self.src(fp["source"], "resource footprint")
        for m in fp["metrics"]:
            self.ins(
                "resource_footprint",
                species_id=sp, metric=m["metric"], label=m["label"],
                unit=m["unit"], per_individual=m.get("per_individual"),
                per_kg_liveweight=m.get("per_kg_liveweight"),
                reference_lw_lb=fp.get("reference_lw_lb"),
                year=fp.get("year"),
                pct_change_decade=m.get("pct_change_decade"),
                source_id=sid, notes=m.get("notes"),
            )

        ec = t["economics"]
        dom = self.domain[ec["domain"]]
        for s in ec["stats"]:
            self.ins(
                "economic_stat",
                domain_id=dom, slug=s["slug"], label=s["label"],
                value_lo=s.get("value_lo"), value_mode=s.get("value_mode"),
                value_hi=s.get("value_hi"), unit=s["unit"],
                basis=s["basis"], confidence=s["confidence"],
                source_id=self.src(s["source"], f"economic {s['slug']}"),
                notes=s.get("notes"),
            )

    def run(self):
        self.sources()
        self.taxonomy()
        self.producers()
        self.loss_chain()
        self.mixing()
        self.stats()
        self.nutrition()
        self.resources()
        self.facts()


def build(db_path: Path = DEFAULT_DB) -> Path:
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text())

    b = Builder(conn)
    try:
        b.run()
    except BuildError:
        conn.close()
        db_path.unlink(missing_ok=True)
        raise

    conn.commit()

    print(f"built {db_path}")
    for table in sorted(b.counts):
        print(f"  {table:<24} {b.counts[table]:>6,}")

    dy = conn.execute(
        "SELECT year, ROUND(dressing_yield*100, 2) FROM v_dressing_yield "
        "ORDER BY year DESC"
    ).fetchall()
    print("\n  derived dressing yield:")
    for year, pct in dy:
        print(f"    {year}: {pct}%")

    uncited = conn.execute(
        "SELECT COUNT(*) FROM loss_factor WHERE source_id IS NULL"
    ).fetchone()[0]
    if uncited:
        raise BuildError(f"{uncited} loss factors have no citation")

    # A stage can legitimately hold several factors -- one per product, for
    # instance -- so name the product alongside the stage. Listing the bare
    # stage label made product-specific factors read as duplicates.
    est = conn.execute(
        "SELECT ls.label, COALESCE(p.label, 'all products') "
        "FROM loss_factor lf "
        "JOIN loss_stage ls ON ls.id = lf.loss_stage_id "
        "LEFT JOIN product p ON p.id = lf.product_id "
        "WHERE lf.confidence = 'estimate' ORDER BY ls.sequence, p.label"
    ).fetchall()
    if est:
        print(f"\n  {len(est)} factor(s) rest on unsourced estimates:")
        for label, prod in est:
            print(f"    - {label}  [{prod}]")

    conn.close()
    return db_path


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    target = Path(argv[0]) if argv else DEFAULT_DB
    try:
        build(target)
    except BuildError as e:
        print(f"build failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
