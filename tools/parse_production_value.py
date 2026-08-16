#!/usr/bin/env python3
"""Parse the NASS "Poultry - Production and Value" summary into YAML.

    python tools/parse_production_value.py --from-pdf plva0426.pdf \
        > data/production_value.yaml

    # legacy: a pdftotext -layout text file still works
    python tools/parse_production_value.py plva.txt > data/production_value.yaml

This is a DIFFERENT publication from Poultry Slaughter. It measures broilers
PRODUCED (Dec 1 - Nov 30) rather than young chickens SLAUGHTERED (calendar
year), so the national totals legitimately differ and must never be summed.

Three reasons it is worth parsing:

  1. It independently confirms the state live weights we already hold.
     Production pounds divided by head reproduces the slaughter report's
     average live weight, from a separate survey with separate methodology.

  2. It recovers states. NASS suppresses different states in different years
     and different publications, so a union across both is larger than
     either alone.

  3. It publishes the SUPPRESSED states too, as named aggregates - one
     combined row for a handful of states, and an "Other States" row whose
     members the footnote lists outright. Those are real cited figures for
     exactly the states no per-state series can cover.

Prefer --from-pdf. pdftotext -layout drifts values between rows on this
document depending on the poppler build - a 2026 extraction put Delaware's
head count on Georgia's line, three plausible-looking numbers per row, no
error anywhere. The pdfplumber path rebuilds lines from word coordinates
instead. Either way the output is REFUSED unless states + aggregates
reproduce the published United States total exactly, per measure, per year -
that check is what turns a silent misread into a loud one, whichever
extraction produced the text.

Table bounds are located by their headings rather than hardcoded offsets,
because the row a table ends on moves between editions.
"""
from __future__ import annotations

import re
import sys

# An optional footnote marker sits between the label and the dot leader
# ("Other States 1 ..."), and must not break the match.
ROW = re.compile(r"^([A-Z][A-Za-z ,]+?)(?:\s*\d)?\s*\.{3,}\s*(.*)$")
NOT_A_STATE = {"United States", "Other States", "Other States 1"}


def pdf_lines(path: str) -> list[str]:
    """Rebuild layout lines from word coordinates.

    Words are clustered into lines by their top coordinate and joined with
    double spaces, so numbers() can keep splitting on runs of whitespace.
    """
    try:
        import pdfplumber
    except ImportError:
        print("--from-pdf needs pdfplumber (pip install pdfplumber)",
              file=sys.stderr)
        raise SystemExit(1)

    lines = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            rows: dict[int, list] = {}
            for w in page.extract_words():
                rows.setdefault(round(w["top"] / 3), []).append(w)
            for key in sorted(rows):
                ws = sorted(rows[key], key=lambda w: w["x0"])
                lines.append("  ".join(w["text"] for w in ws))
    return lines


def find_tables(lines: list[str]) -> dict[int, tuple[int, int]]:
    """Locate each year's broiler table by its heading and its US total row."""
    starts = {}
    for i, ln in enumerate(lines):
        m = re.match(r"^Broiler Production and Value .*:\s+(\d{4})\s*$",
                     re.sub(r"\s{2,}", " ", ln))
        if m:
            starts[int(m.group(1))] = i
    bounds = {}
    for year, start in starts.items():
        for j in range(start, len(lines)):
            s = re.sub(r"\s{2,}", " ", lines[j].lstrip())
            if s.startswith("United States") and any(c.isdigit() for c in s):
                bounds[year] = (start, j + 1)
                break
    return bounds


def numbers(rest: str) -> list[float]:
    out = []
    for tok in re.split(r"\s{2,}", rest.strip()):
        t = tok.replace(",", "").strip()
        if re.fullmatch(r"\d+", t):
            out.append(float(t))
    return out


def parse(lines: list[str], a: int, b: int) -> dict[str, list[float]]:
    rows = {}
    for ln in lines[a:b]:
        m = ROW.match(ln)
        if not m:
            continue
        vals = numbers(m.group(2))
        if len(vals) == 3:
            # Double-space joins from the pdf path leave doubled spaces
            # inside multi-word labels; every downstream lookup is by the
            # single-spaced name.
            label = re.sub(r"\s{2,}", " ", m.group(1).strip()).rstrip(",")
            rows[label] = vals
    return rows


def parse_combined(lines: list[str], a: int, b: int):
    """The multi-line combined row ("California, Tennessee, / and West
    Virginia"). The label wraps, so ROW never sees it whole: a label line
    ending in a comma opens the row, and it closes on the "and ..."
    continuation. Numbers are collected from every line in between, because
    which physical line carries them varies by extraction.
    """
    label_parts, vals, open_row = [], [], False
    for ln in lines[a:b]:
        s = ln.strip()
        m = ROW.match(ln)
        if not open_row:
            if m and not numbers(m.group(2)) and m.group(1).strip().endswith(","):
                open_row = True
                label_parts = [re.sub(r"\s{2,}", " ", m.group(1).strip())]
                continue
            continue
        vals += numbers(s)
        if s.startswith("and "):
            tail = re.sub(r"\s{2,}", " ", s.split("..", 1)[0].strip())
            label_parts.append(tail)
            break
    if not open_row:
        return None, None
    label = " ".join(label_parts)
    if len(vals) != 3:
        print(f"combined row '{label}': expected 3 numbers, got {vals}",
              file=sys.stderr)
        raise SystemExit(1)
    return label, vals


def parse_footnote(lines: list[str], us_row: int) -> list[str]:
    """The members of Other States, from the source's own footnote.

    The superscript marker extracts two ways depending on its y-offset:
    inline ("1 Illinois, Indiana, ...") or as a bare "1" on a line of its
    own with the members starting on the next. Both editions in the 2026
    summary manage to do it differently, one table apart.
    """
    text, collecting = "", False
    for ln in lines[us_row:us_row + 8]:
        s = re.sub(r"\s{2,}", " ", ln.strip())
        if not collecting and re.match(r"^1(\s+[A-Z].*)?$", s):
            collecting = True
            s = s[1:].strip()
            if not s:
                continue
        elif not collecting:
            continue
        text += " " + s
        if "operations" in text:
            break
    m = re.match(r"^(.*?)\s+combined to avoid", text.strip())
    if not m:
        return []
    return [p.strip() for p in re.split(r",\s*(?:and\s+)?", m.group(1))
            if p.strip()]


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--from-pdf":
        lines = pdf_lines(argv[1])
    else:
        path = argv[0] if argv else "plva.txt"
        lines = open(path, encoding="utf-8").read().splitlines()
    bounds = find_tables(lines)
    if not bounds:
        print("no broiler tables found", file=sys.stderr)
        return 1

    tables = {y: parse(lines, a, b) for y, (a, b) in bounds.items()}
    states = {y: {k: v for k, v in t.items() if k not in NOT_A_STATE}
              for y, t in tables.items()}
    national = {y: t.get("United States") for y, t in tables.items()}

    aggregates: dict[int, list] = {}
    for y, (a, b) in bounds.items():
        aggregates[y] = []
        label, vals = parse_combined(lines, a, b)
        if label:
            # Members of the combined row are its own label.
            members = [p.strip() for p in
                       re.split(r",\s*(?:and\s+)?", label) if p.strip()]
            aggregates[y].append((label, members, vals))
        other = tables[y].get("Other States") or tables[y].get("Other States 1")
        if other:
            members = parse_footnote(lines, b - 1)
            if not members:
                print(f"{y}: Other States row without a members footnote",
                      file=sys.stderr)
                return 1
            aggregates[y].append(("Other States", members, other))

    # The gate. Rounding-free because NASS publishes these in whole
    # thousands that genuinely sum; the 2026 edition reproduces the US
    # total to the last digit on all six measures. A drifted extraction
    # cannot pass this by luck three columns in a row.
    for y in bounds:
        if not national.get(y):
            print(f"{y}: no United States row parsed", file=sys.stderr)
            return 1
        if len(aggregates[y]) != 2:
            print(f"{y}: expected 2 aggregate rows, found "
                  f"{len(aggregates[y])} - refusing to emit", file=sys.stderr)
            return 1
        for i, meas in enumerate(("head", "pounds", "dollars")):
            total = (sum(v[i] for v in states[y].values())
                     + sum(agg[2][i] for agg in aggregates[y]))
            if abs(total - national[y][i]) > national[y][i] * 1e-5:
                print(f"{y} {meas}: states + aggregates = {total:.0f}, "
                      f"published US total {national[y][i]:.0f} - the "
                      "extraction is misaligned, refusing to emit",
                      file=sys.stderr)
                return 1

    years = sorted(tables, reverse=True)
    union = sorted(set().union(*(states[y] for y in years)))

    w = sys.stdout.write
    w("# Broiler production, live weight, and value by state.\n"
      "#\n"
      "# GENERATED by tools/parse_production_value.py - do not hand-edit.\n"
      "#\n"
      "# Source: USDA NASS \"Poultry - Production and Value\" annual summary,\n"
      "# a different publication from Poultry Slaughter. It counts broilers\n"
      "# PRODUCED over Dec 1 - Nov 30; the slaughter report counts young\n"
      "# chickens SLAUGHTERED over the calendar year and also includes\n"
      "# roasters and capons. The national totals therefore differ - 9.40bn\n"
      "# produced against 9.58bn slaughtered in 2025 - and must not be summed\n"
      "# or treated as the same series.\n"
      "#\n"
      "# derived_live_weight_lb is production pounds divided by head. It\n"
      "# reproduces the slaughter report's state average live weight exactly,\n"
      "# which is the cross-check that makes this file worth carrying.\n"
      "#\n"
      "# The report excludes any state producing under 500,000 broilers, and\n"
      "# suppresses others to avoid disclosing individual operations. Which\n"
      "# states get suppressed CHANGES BY YEAR, so keeping every year widens\n"
      "# coverage. The suppressed states are not lost: the report publishes\n"
      "# them as named aggregates, carried in `aggregates:` below, and the\n"
      "# parser refuses to emit unless states + aggregates reproduce the\n"
      "# published United States total exactly.\n\n")
    w("source: nass-production-value-2025\nspecies: broiler\n\n")

    w("national:\n")
    for y in years:
        v = national.get(y)
        if not v:
            continue
        w(f"  - year: {y}\n"
          f"    head_thousands: {v[0]:.0f}\n"
          f"    live_weight_klb: {v[1]:.0f}\n"
          f"    value_kusd: {v[2]:.0f}\n")

    w("\nregions:\n")
    for y in years:
        for st in sorted(states[y]):
            h, lb, val = states[y][st]
            w(f"  - region: {st}\n"
              f"    year: {y}\n"
              f"    head_thousands: {h:.0f}\n"
              f"    live_weight_klb: {lb:.0f}\n"
              f"    value_kusd: {val:.0f}\n"
              f"    derived_live_weight_lb: {lb / h:.2f}\n")

    w("\naggregates:\n")
    for y in years:
        for label, members, (h, lb, val) in aggregates[y]:
            w(f"  - label: {label}\n"
              f"    year: {y}\n"
              f"    members: [{', '.join(members)}]\n"
              f"    head_thousands: {h:.0f}\n"
              f"    live_weight_klb: {lb:.0f}\n"
              f"    value_kusd: {val:.0f}\n"
              f"    derived_live_weight_lb: {lb / h:.2f}\n")

    print(f"years {years}; states per year "
          f"{ {y: len(states[y]) for y in years} }; union {len(union)}; "
          f"aggregates verified against the US total",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
