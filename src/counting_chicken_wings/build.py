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

import os
import sqlite3
import sys
from pathlib import Path

import yaml

PKG = Path(__file__).parent
ROOT = PKG.parent.parent
DATA = ROOT / "data"
SCHEMA = PKG / "schema.sql"
# ROOT points at the repo only under an editable install; a plain
# `pip install` puts this file in site-packages, where there is no data/ and
# nowhere sane to write. $WINGS_DB is the escape hatch, and the API's only
# override at all -- the CLI has --db, uvicorn passes nothing through.
_ENV_DB = os.environ.get("WINGS_DB")
DEFAULT_DB = Path(_ENV_DB).expanduser() if _ENV_DB else ROOT / "chickens.db"


class BuildError(Exception):
    pass


def load(name: str):
    p = DATA / name
    if not p.exists():
        raise BuildError(f"missing data file: {p}")
    # encoding is explicit because Windows defaults to cp1252, and the corpus
    # legitimately contains non-ASCII (degree signs, en dashes) in quotes.
    # YAML is UTF-8 by spec, so this is the correct read everywhere.
    with p.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def merge_files(prefix: str) -> dict[str, list]:
    """Merge every data/<prefix>*.yaml into one dict of concatenated sections.

    A new product line is a new FILE rather than an edit threaded into an
    existing one. That keeps each subject's data next to its own commentary,
    stops daily additions colliding in one growing file, and matters more than
    it sounds for eggs: an egg is never slaughtered, cut up, or breaded, so
    its loss chain has almost nothing in common with a wing's. Forcing both
    into one file would interleave two unrelated pipelines.

    Files are concatenated in filename order with the unsuffixed base file
    first, so domains and species it defines exist before a later file
    references them.
    """
    merged: dict[str, list] = {}
    base = f"{prefix}.yaml"
    paths = sorted(
        DATA.glob(f"{prefix}*.yaml"),
        key=lambda p: (p.name != base, p.name),
    )
    if not paths:
        raise BuildError(f"no {prefix}*.yaml found in {DATA}")
    for p in paths:
        part = load(p.name) or {}
        for key, rows in part.items():
            if rows:
                merged.setdefault(key, []).extend(rows)
    return merged


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
        self.country: dict[str, int] = {}
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

    def countries(self):
        """Country dimension.

        Loaded before any observation table, because every country-scoped
        statistic now carries country_id and the build should fail loudly if
        a country is missing rather than defaulting to the US.
        """
        t = load("countries.yaml")
        for c in t["countries"]:
            self.country[c["iso3"]] = self.ins(
                "country",
                iso3=c["iso3"], name=c["name"],
                native_mass_unit=c.get("native_mass_unit", "lb"),
                native_currency=c.get("native_currency"),
                population=c.get("population"),
                population_year=c.get("population_year"),
                source_id=self.src(c.get("source"), f"country {c['iso3']}"),
                notes=c.get("notes"),
            )
        # The existing corpus is US-only. Resolved once here so the
        # observation loaders stay free of country plumbing until a
        # second country actually has data.
        self.default_country = self.ctry("USA", "default country")

    def ctry(self, iso3: str | None, ctx: str) -> int:
        """Resolve a country, defaulting to the US for the existing corpus."""
        code = iso3 or "USA"
        if code not in self.country:
            raise BuildError(
                f"{ctx}: unknown country '{code}'. Add it to countries.yaml."
            )
        return self.country[code]

    def taxonomy(self):
        t = merge_files("taxonomy")

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
                yield_period_days=p.get("yield_period_days"),
                max_units_per_day=p.get("max_units_per_day"),
                default_window_days=p.get("default_window_days"),
                rate_label=p.get("rate_label"),
                cap_note=p.get("cap_note"),
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
        t = merge_files("loss_chain")
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

        # Which loss stages are not independent of one another (#77), e.g.
        # wing_damage/grading_downgrade/transport_doa all riding the same
        # per-load handling-quality variable. `rho` is an estimate like any
        # other and gets a citation, not a bare Python constant.
        for g in t.get("correlated_groups", []):
            gid = self.ins(
                "loss_correlation_group",
                slug=g["slug"], label=g["label"],
                description=g.get("description"),
                rho=g["rho"], confidence=g["confidence"],
                source_id=self.src(g["source"], f"correlation {g['slug']}"),
                notes=g.get("notes"),
            )
            for slug in g["stages"]:
                self.ins(
                    "loss_correlation_group_stage",
                    group_id=gid, loss_stage_id=self.loss_stage[slug],
                )

    def mixing(self):
        # Merged across every data/mixing*.yaml, same reasoning as taxonomy:
        # a new product's cascade is a new file. mixing.yaml is loaded first
        # so the base stages exist before anything references them.
        merged: dict[str, list] = {}
        paths = sorted(
            DATA.glob("mixing*.yaml"),
            key=lambda p: (p.name != "mixing.yaml", p.name),
        )
        if not paths:
            raise BuildError("no mixing*.yaml found in data/")
        for p in paths:
            part = load(p.name) or {}
            for key, rows in part.items():
                if rows:
                    merged.setdefault(key, []).extend(rows)
        t = merged

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

        # Scalar model parameters. Global rather than per-domain: they
        # describe how a draw behaves, not what is being drawn, and one set
        # keeps every product's cascade on the same physics. A duplicate slug
        # across two mixing*.yaml files is a real conflict, not a merge, so
        # say so rather than letting the last file win silently.
        seen: set[str] = set()
        for p in t.get("model_parameters", []):
            if p["slug"] in seen:
                raise BuildError(
                    f"model_parameter {p['slug']} defined twice"
                )
            seen.add(p["slug"])
            self.ins(
                "model_parameter",
                slug=p["slug"], label=p["label"],
                value_lo=p["value_lo"], value_mode=p["value_mode"],
                value_hi=p["value_hi"],
                source_id=self.src(p["source"], f"parameter {p['slug']}"),
                confidence=p["confidence"], description=p["description"],
            )

        for ch in t.get("supply_chains", []):
            species = ch.get("species")
            if species and species not in self.species:
                raise BuildError(
                    f"supply_chain {ch['slug']}: unknown species '{species}'"
                )
            cid = self.ins(
                "supply_chain",
                domain_id=self.domain[ch["domain"]],
                slug=ch["slug"], label=ch["label"],
                description=ch["description"],
                # NULL species means "any", which is how the wing chains
                # behaved before eggs existed. Now that a second species has
                # its own routes, leaving them unscoped is what let an egg
                # query pick up the wing cascade.
                species_id=self.species.get(species) if species else None,
                is_default=ch.get("is_default", 0),
                floor_note=ch.get("floor_note"),
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

            # Optional per-chain loss selection. Omitted means "species
            # defaults", so existing routes are unaffected.
            for slug in ch.get("loss_stages", []):
                if slug not in self.loss_stage:
                    raise BuildError(
                        f"supply_chain {ch['slug']}: unknown loss stage "
                        f"'{slug}'"
                    )
                self.c.execute(
                    "INSERT INTO supply_chain_loss_stage "
                    "(supply_chain_id, loss_stage_id) VALUES (?,?)",
                    (cid, self.loss_stage[slug]),
                )

    def stats(self):
        t = load("stats_national.yaml")

        sl = t["slaughter"]
        sp = self.species[sl["species"]]
        sid = self.src(sl["source"], "slaughter stats")
        for y in sl["years"]:
            self.ins(
                "slaughter_stat_year",
                country_id=self.default_country,
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
                country_id=self.default_country,
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
                    country_id=self.default_country,
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
                    country_id=self.default_country,
                    species_id=sp, region=r["region"], year=2025, month=i,
                    avg_size=v, size_unit=unit, source_id=sid,
                )

    def egg_states(self):
        """Eggs per layer and total production by state.

        Shares regional_size_stat with the broiler live weights. Safe because
        the table is keyed on species_id, so layer rows and broiler rows for
        the same state and year cannot collide -- and "average size of the
        thing this species yields" is the same shape of fact either way.

        A state absent for a given year was suppressed by NASS, not zero. It
        is simply omitted, so the union across years covers all 34 states even
        though only 31 have 2025 figures.
        """
        st = load("stats_states_eggs.yaml")
        sp = self.species[st["species"]]
        sid = self.src(st["source"], "egg state stats")
        unit = st["size_unit"]
        vunit = st.get("volume_unit")
        for r in st["regions"]:
            for year in (2025, 2024):
                eggs = r.get(f"eggs_per_layer_{year}")
                if eggs is None:
                    continue
                total = r.get(f"total_eggs_million_{year}")
                self.ins(
                    "regional_size_stat",
                    country_id=self.default_country,
                    species_id=sp, region=r["region"], year=year, month=None,
                    avg_size=eggs, size_unit=unit,
                    volume=int(total) if total else None,
                    volume_unit=vunit if total else None,
                    source_id=sid,
                )

    def production_value(self):
        """Broilers produced by state, from the NASS Production and Value
        summary.

        Kept apart from the slaughter series on purpose: different
        publication, different population, different reporting period. The
        national row arrives as region 'United States', exactly as the
        source presents it.
        """
        t = load("production_value.yaml")
        sp = self.species[t["species"]]
        sid = self.src(t["source"], "production and value stats")

        rows = [dict(r, region="United States") for r in t.get("national", [])]
        rows += t.get("regions", [])

        for r in rows:
            self.ins(
                "regional_production_year",
                country_id=self.default_country,
                species_id=sp,
                region=r["region"],
                year=r["year"],
                head_thousands=r.get("head_thousands"),
                live_weight_klb=r.get("live_weight_klb"),
                value_kusd=r.get("value_kusd"),
                derived_live_weight_lb=r.get("derived_live_weight_lb"),
                source_id=sid,
            )

    def census_states(self):
        """All-50-state broiler presence from the Census of Agriculture.

        Loaded separately from the survey series because it is a different
        programme: five-yearly, sales rather than slaughter, and crucially
        unsuppressed. It exists so the map can show every state instead of
        the 22 the annual survey permits.
        """
        t = load("census_states.yaml")
        sp = self.species[t["species"]]
        sid = self.src(t["source"], "census state stats")
        year = t["census_year"]

        for r in t.get("regions", []):
            self.ins(
                "regional_census_stat",
                country_id=self.default_country,
                species_id=sp,
                region=r["region"],
                census_year=year,
                sales_head=r.get("sales_head"),
                operations=r.get("operations"),
                inventory=r.get("inventory"),
                source_id=sid,
            )

    def output_stats(self):
        """Output, value and inventory as a country publishes them.

        Every data/output_*.yaml is loaded, so a second country is a new file
        rather than an edit here. Nothing is converted at load: each row keeps
        the unit its publisher used, because the alternative is deciding on a
        reader's behalf that CBS's "agricultural output" means the same thing
        as NASS's certified ready-to-cook pounds. It may not, and the
        publication does not say.

        Israel is why this exists. See the header of data/output_israel.yaml.
        """
        files = sorted(DATA.glob("output_*.yaml"))
        for path in files:
            t = load(path.name)
            sp = self.species[t["species"]]
            cid = self.ctry(t.get("country"), f"{path.name} country")

            # One shape for every national measure, each block carrying its own
            # unit, source and confidence. The confidence is per block because
            # this table stopped being government-only the day Israel's head
            # count arrived from a trade-press interview rather than from CBS.
            for block in t.get("national", []):
                measure = block["measure"]
                for r in block["years"]:
                    self.ins(
                        "output_stat_year",
                        species_id=sp, country_id=cid, region=None,
                        year=r["year"], measure=measure,
                        value=r.get("value"), unit=block["unit"],
                        confidence=block.get("confidence", "measured"),
                        provisional=r.get("provisional", 0),
                        suppressed=0,
                        source_id=self.src(block["source"],
                                           f"{path.name} {measure}"),
                        notes=block.get("notes"),
                    )

            d = t.get("districts")
            if d:
                sid = self.src(d["source"], f"{path.name} districts")
                for r in d["regions"]:
                    supp = int(bool(r.get("suppressed")))
                    self.ins(
                        "output_stat_year",
                        species_id=sp, country_id=cid, region=r["region"],
                        region_level=r.get("level"),
                        year=d["year"],
                        # Marketed, not produced. Different measurement from
                        # the national output figure, which is why the two do
                        # not reconcile and why they are not the same measure.
                        measure="marketed",
                        value=None if supp else r.get("value"),
                        unit=d["unit"],
                        confidence=d.get("confidence", "measured"),
                        provisional=0, suppressed=supp,
                        source_id=sid,
                        notes=(f"in {r['parent']}" if r.get("parent")
                               else None),
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

    def quality(self):
        t = load("quality.yaml")
        for d in t["defects"]:
            self.ins(
                "quality_defect",
                species_id=self.species[d["species"]],
                slug=d["slug"], label=d["label"],
                affected_part=d["affected_part"], severity=d["severity"],
                prevalence_pct_lo=d.get("prevalence_pct_lo"),
                prevalence_pct_mode=d["prevalence_pct_mode"],
                prevalence_pct_hi=d.get("prevalence_pct_hi"),
                weight_association=d["weight_association"],
                first_year=d.get("first_year"),
                first_year_pct=d.get("first_year_pct"),
                source_id=self.src(d["source"], f"defect {d['slug']}"),
                notes=d.get("notes"),
            )

        for a in t.get("axes", []):
            self.ins(
                "quality_axis",
                species_id=self.species[a["species"]],
                question=a["question"], x_label=a["x_label"],
                x_unit=a.get("x_unit"), x_kind=a["x_kind"],
                verdict_yield=a.get("verdict_yield"),
                verdict_quality=a.get("verdict_quality"),
                verdict_count=a.get("verdict_count"),
                summary=(a.get("summary") or "").strip() or None,
            )

    def nutrition(self):
        t = merge_files("nutrition")
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
        self.countries()
        self.taxonomy()
        self.producers()
        self.loss_chain()
        self.mixing()
        self.stats()
        self.egg_states()
        self.production_value()
        self.census_states()
        self.output_stats()
        self.quality()
        self.nutrition()
        self.resources()
        self.facts()


def build(db_path: Path = DEFAULT_DB) -> Path:
    # The default's parent is the repo root, but a $WINGS_DB path may point
    # into a directory that does not exist yet.
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))

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
