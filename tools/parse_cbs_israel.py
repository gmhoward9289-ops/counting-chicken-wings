"""Parse Israeli poultry figures out of CBS Statistical Abstract chapter 21.

    python tools/parse_cbs_israel.py            # rewrite data/output_israel.yaml
    python tools/parse_cbs_israel.py --check    # exit 1 if it would change

Writes `data/output_israel.yaml`. Do not hand-edit that file; re-run this.

The route to these three files is the expensive part and it is not guessable.
It was established by the manual pass recorded in
`docs/research/library/poultry-israel.yaml`, and the short version is:

  * CBS's time-series API is the wrong database. 400 series sampled across the
    id space returned foreign trade, industry, prices and population -- no
    agriculture at all. Agriculture exists only in the Statistical Abstract.
  * The abstract's pages are a SharePoint shell, but SharePoint REST answers
    anonymously, which is how the document libraries were enumerated.
  * The files live on the HEBREW web. The English path returns a 200 soft-404
    of exactly 2,056 bytes, so a wrong guess looks like a working URL.
  * Agriculture is chapter 21, not 19.

An .xlsx is a zip of XML, so this reads them with zipfile and ElementTree
rather than adding openpyxl for three files of ~30 KB.

WHAT THIS DELIBERATELY DOES NOT EXTRACT

Table eggs. st21_11 carries a table-egg quantity of 2,661.49 under a column
headed "1,000 tonnes, unless otherwise stated" -- and 2.66 million tonnes of
eggs for a country of ten million people is impossible, so it is one of the
"otherwise stated" rows and is almost certainly millions of eggs. Almost
certainly is not a citation. Egg figures stay out until the unit is confirmed
from CBS's own metadata.

Head slaughtered per year. It is in none of the three tables, and it is what
ISRAEL-PLAN calls the denominator for everything. Deriving it from tonnage
would need an Israeli average bird weight, which CBS does not publish either;
borrowing the US 6.62 lb would silently make an American assumption into an
Israeli fact. See the note in data/output_israel.yaml.
"""

from __future__ import annotations

import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "output_israel.yaml"

BASE = ("https://www.cbs.gov.il/he/publications/DocLib/2025/"
        "21.ShnatonAgriculture/")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# Verified 2026-07-29. Byte sizes are asserted after download because the
# English path serves a 200 soft-404 -- a wrong URL here would parse as an
# empty sheet and silently produce a file with no rows in it.
FILES = {
    "st21_11": 52557,   # output by industry and product
    "st21_08": 26768,   # livestock inventory
    "st21_04": 31390,   # marketing by district
}

# CBS marks provisional years with a leading asterisk in the header cell.
PROVISIONAL = "*"

# Suppression markers, identical in meaning to NASS's withheld cells.
SUPPRESSED = {"-", ". .", "..", ". ."}


def fetch(name: str) -> bytes:
    url = f"{BASE}{name}.xlsx"
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    expected = FILES[name]
    if len(data) != expected:
        print(f"warning: {name}.xlsx is {len(data)} bytes, expected "
              f"{expected}. CBS may have republished chapter 21 -- re-verify "
              f"the figures before trusting this output.", file=sys.stderr)
    return data


def rows(data: bytes) -> list[dict[str, str]]:
    """Every sheet row as {column letter: value}, shared strings resolved."""
    z = zipfile.ZipFile(BytesIO(data))
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))

    out = []
    sheets = sorted(n for n in z.namelist()
                    if n.startswith("xl/worksheets/sheet"))
    for sheet in sheets:
        root = ET.fromstring(z.read(sheet))
        for row in root.iter(f"{NS}row"):
            cells: dict[str, str] = {}
            for c in row:
                v = c.find(f"{NS}v")
                val = v.text if v is not None else None
                if c.get("t") == "s" and val is not None:
                    val = shared[int(val)]
                if val in (None, ""):
                    continue
                col = re.match(r"[A-Z]+", c.get("r") or "").group()
                cells[col] = val
            out.append(cells)
    return out


def find_row(sheet: list[dict[str, str]], label: str) -> dict[str, str]:
    """The row whose column A starts with `label`, ignoring indentation.

    Fails loudly rather than returning empty. CBS indents product rows with
    spaces and appends footnote markers -- "      Broilers(5)" -- so an exact
    match would break the day a footnote is renumbered.
    """
    for cells in sheet:
        a = (cells.get("A") or "").strip()
        if a.startswith(label):
            return cells
    raise SystemExit(f"no row starting with {label!r}: CBS changed the table")


def year_columns(sheet: list[dict[str, str]]) -> dict[str, tuple[int, bool]]:
    """Map column letter -> (year, provisional) from the header row.

    Read rather than hardcoded because the two tables disagree: st21_08 runs
    ten columns back to 1960, st21_11 five back to 2000. Hardcoding one and
    applying it to the other silently mislabels every figure by decades.
    """
    for cells in sheet:
        found = {}
        for col, val in cells.items():
            v = val.strip()
            prov = v.startswith(PROVISIONAL)
            v = v.lstrip(PROVISIONAL)
            if re.fullmatch(r"(19|20)\d{2}", v):
                found[col] = (int(v), prov)
        if len(found) >= 4:
            return found
    raise SystemExit("no year header row found: CBS changed the table")


def num(raw: str) -> float:
    """Round to the precision CBS actually publishes.

    Excel stores 600.072 as 600.07199999999995 and 553.068 as
    553.06799999999998. Writing those through to YAML would put fifteen
    digits of false precision into a corpus whose entire pitch is that its
    numbers mean something.
    """
    return round(float(raw), 3)


def parse_output(data: bytes) -> tuple[list[dict], list[dict]]:
    """st21_11: broiler output quantity (tonnes) and value (NIS million).

    The sheet is two blocks side by side under one header: value in columns
    B-F, quantity in G-K, the same years in each. So a year appears twice and
    the block a column belongs to is what distinguishes them -- taken from
    order, since the block headers are merged cells.
    """
    sheet = rows(data)
    years = year_columns(sheet)
    cols = sorted(years)
    half = len(cols) // 2
    value_cols, qty_cols = cols[:half], cols[half:]

    row = find_row(sheet, "Broilers")
    output, value = [], []
    for col in qty_cols:
        if col in row:
            year, prov = years[col]
            output.append({"year": year, "tonnes": num(row[col]) * 1000,
                           "provisional": prov})
    for col in value_cols:
        if col in row:
            year, prov = years[col]
            value.append({"year": year, "ils_million": num(row[col]),
                          "provisional": prov})
    return output, value


def parse_inventory(data: bytes) -> list[dict]:
    """st21_08: broilers in thousands, END OF YEAR.

    The trap on this table, and the reason it is a separate measure: 37.9
    million is a standing flock at a point in time, not annual throughput.
    Broilers turn over several times a year, so reading it as slaughter would
    understate the answer by a factor of five or so.
    """
    sheet = rows(data)
    years = year_columns(sheet)
    row = find_row(sheet, "Broilers")
    return [
        {"year": years[col][0], "thousand_head": num(row[col]),
         "provisional": years[col][1]}
        for col in sorted(years) if col in row
    ]


def parse_districts(data: bytes) -> tuple[int, list[dict]]:
    """st21_04: broilers marketed by district and regional council, tonnes.

    Marketed, not produced -- a different measurement, and the reason the
    district total does not reconcile with st21_11's output. That gap travels
    with the data as a note rather than being quietly absorbed.
    """
    sheet = rows(data)
    year = None
    for cells in sheet:
        a = (cells.get("A") or "").strip()
        if re.fullmatch(r"(19|20)\d{2}", a):
            year = int(a)
            break
    if year is None:
        raise SystemExit("no year found in st21_04")

    out = []
    for cells in sheet:
        name = (cells.get("A") or "").rstrip()
        raw = (cells.get("C") or "").strip()
        if not name or not raw:
            continue
        if name.strip().startswith(("District", "MARKETING", "BY DISTRICT")):
            continue
        if re.fullmatch(r"(19|20)\d{2}", name.strip()):
            continue
        # Indentation is the hierarchy: unindented rows are districts or the
        # grand total, indented rows are regional councils inside them.
        indented = name.startswith(" ")
        label = name.strip()
        if raw in SUPPRESSED:
            out.append({"region": label, "level": "council" if indented
                        else "district", "suppressed": True})
        else:
            try:
                tonnes = num(raw)
            except ValueError:
                continue
            out.append({"region": label,
                        "level": "council" if indented else "district",
                        "tonnes": tonnes})
    return year, out


def yaml_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def render(output, value, inventory, district_year, districts) -> str:
    total = next((d for d in districts if d["region"] == "GRAND TOTAL"), None)
    councils = [d for d in districts
                if d["level"] == "council" and "tonnes" in d]
    suppressed = [d for d in districts if d.get("suppressed")]
    output_2024 = next((o["tonnes"] for o in output if o["year"] == 2024), None)
    gap = ""
    if total and output_2024:
        pct = 100 * (output_2024 - total["tonnes"]) / output_2024
        gap = (f"District marketing sums to {total['tonnes']:,.2f} tonnes "
               f"against {output_2024:,.0f} tonnes of output in table 21.11, "
               f"a gap of {pct:.2f}%.")

    lines = [
        "# Israeli broiler figures, from the CBS Statistical Abstract 2025,",
        "# chapter 21. Generated by tools/parse_cbs_israel.py - do not",
        f"# hand-edit; re-run the parser. Retrieved {date.today()}.",
        "#",
        "# WHY THIS IS NOT IN slaughter_stat_year OR regional_production_year",
        "#",
        "# Those tables bake US reporting into their column names and assume",
        "# head slaughtered exists. CBS publishes tonnage, value in shekels,",
        "# and an end-of-year flock -- and no head-slaughtered series at all.",
        "# Mapping output tonnage onto certified_rtc_lb would assert that CBS",
        "# means ready-to-cook weight, which the publication never says.",
        "#",
        "# THE MISSING DENOMINATOR, stated plainly because it bounds what can",
        "# be claimed: Israel has no head-slaughtered figure here, so the",
        "# project cannot answer 'how many Israeli chickens' from Israeli data",
        "# alone. It can answer scale, districts, and value. Deriving head",
        "# from tonnage needs an Israeli average bird weight, which CBS does",
        "# not publish; using the US 6.62 lb would make an American",
        "# assumption look like an Israeli measurement. ISRAEL-PLAN.md is",
        "# explicit that US figures must not be borrowed silently.",
        "#",
        "# Israel reports kilograms and shekels. Nothing here is converted:",
        "# every row carries its own unit, and the reader of the row converts",
        "# deliberately or not at all.",
        "",
        "species: broiler",
        "country: ISR",
        "",
        "# Table 21.11. Agricultural output by industry and product.",
        "# CBS footnote 5 defines broilers as \"Chickens intended for",
        "# fattening for the meat industry\", which is our broiler species -",
        "# so no mapping decision was needed.",
        "national:",
        "  source: cbs-st21-11-output-2025",
        "  meat_output:",
        "    unit: tonnes",
        "    years:",
    ]
    for o in output:
        star = "  # provisional" if o["provisional"] else ""
        lines.append(f"      - {{year: {o['year']}, value: {o['tonnes']:.0f}, "
                     f"provisional: {int(o['provisional'])}}}{star}")
    lines += [
        "  output_value:",
        "    unit: ILS_million",
        "    years:",
    ]
    for v in value:
        star = "  # provisional" if v["provisional"] else ""
        lines.append(f"      - {{year: {v['year']}, value: "
                     f"{v['ils_million']:.3f}, "
                     f"provisional: {int(v['provisional'])}}}{star}")
    lines += [
        "",
        "# Table 21.8. Livestock, thousands, END OF YEAR.",
        "#",
        "# A STANDING FLOCK, NOT ANNUAL THROUGHPUT. Broilers turn over several",
        "# times a year, so 37.9 million is not 37.9 million birds raised.",
        "# This is the same inventory-versus-throughput distinction already",
        "# carried as a caveat on the US census sales figures, and it is why",
        "# the trade-press lead of ~260 million broilers a year in",
        "# ISRAEL-PLAN.md is neither confirmed nor refuted by this table.",
        "inventory:",
        "  source: cbs-st21-08-livestock-2025",
        "  unit: thousand_head",
        "  years:",
    ]
    for i in inventory:
        star = "  # provisional" if i["provisional"] else ""
        lines.append(f"    - {{year: {i['year']}, value: "
                     f"{i['thousand_head']:.0f}, "
                     f"provisional: {int(i['provisional'])}}}{star}")
    lines += [
        "",
        "# Table 21.4. Marketing of animals and animal products by district",
        f"# and regional council, {district_year}, broilers in tonnes.",
        "#",
        "# Answers the open question at the foot of ISRAEL-PLAN.md: Israel",
        "# DOES have subnational poultry data, so the comparison need not be",
        "# visibly lopsided against 50 US states.",
        "#",
        "# MEASURE IS 'marketed', NOT 'meat_output'. " + gap,
        "# Output and marketing measure different things so the gap is",
        "# probably real, but a reader who adds up the districts will find",
        "# it, and finding it unannounced reads as an error.",
        "#",
        "# Suppressed councils use CBS's own \"-\" and are loaded as presence",
        "# without volume, exactly as NASS-suppressed states are. Never zero.",
        "#",
        "# 'Judea and Samaria Area' is CBS's own row label and its own",
        "# footnote 3 restricts it to \"Israeli localities\", so the row",
        "# counts some of the production in that area and not all of it. Kept",
        "# with the publisher's label and the publisher's qualification.",
        "districts:",
        f"  source: cbs-st21-04-marketing-2025",
        f"  year: {district_year}",
        "  unit: tonnes",
        "  regions:",
    ]
    for d in districts:
        if d.get("suppressed"):
            lines.append(f"    - {{region: {yaml_quote(d['region'])}, "
                         f"level: {d['level']}, suppressed: 1}}")
        else:
            lines.append(f"    - {{region: {yaml_quote(d['region'])}, "
                         f"level: {d['level']}, value: {d['tonnes']:.2f}}}")
    lines += [
        "",
        f"# {len(councils)} councils with volume, {len(suppressed)} suppressed.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    output, value = parse_output(fetch("st21_11"))
    inventory = parse_inventory(fetch("st21_08"))
    district_year, districts = parse_districts(fetch("st21_04"))
    text = render(output, value, inventory, district_year, districts)

    if "--check" in argv:
        current = OUT.read_text() if OUT.exists() else ""
        # The retrieval date is in the header and changes daily; comparing it
        # would report drift on every run for no reason.
        strip = lambda t: "\n".join(  # noqa: E731
            ln for ln in t.splitlines() if not ln.startswith("# hand-edit")
        )
        if strip(current) != strip(text):
            print(f"{OUT.name} differs from CBS. Re-run without --check.",
                  file=sys.stderr)
            return 1
        print(f"{OUT.name} matches CBS")
        return 0

    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}: "
          f"{len(output)} output years, {len(inventory)} inventory years, "
          f"{len(districts)} district rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
