"""Command line interface.

    wings 12                    answer, then offer the reasoning
    wings 12 --explain          skip the prompt, show everything
    wings 12 --chain local_butcher
    wings 12 --pieces           twelve SEGMENTS, the restaurant convention
    wings facts                 learning-centre facts
    wings states                average bird size by state
    wings sources               every citation
    wings gui                   launch the web interface

The answer comes first in plain language. The reasoning hides behind a
prompt, so a casual user gets one sentence and a curious one gets the whole
audit trail.
"""

from __future__ import annotations

import argparse
import math
import sys
import textwrap

from . import __version__
from . import db as dbm
from . import seasonality as seas
from .brand import banner
from .model import run

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
GREEN, BLUE, AMBER, CYAN = ("\033[32m", "\033[34m", "\033[33m", "\033[36m")

CONFIDENCE_COLOUR = {
    "measured": GREEN, "derived": GREEN, "study": BLUE,
    "industry": CYAN, "estimate": AMBER,
}


def colour(enabled: bool):
    """Return a colouriser, and blank the raw constants when disabled.

    DIM and RESET are interpolated directly in a lot of format strings, so
    disabling colour has to neutralise them too or escape codes leak into
    piped output.
    """
    global BOLD, DIM, RESET, GREEN, BLUE, AMBER, CYAN
    if not enabled:
        BOLD = DIM = RESET = GREEN = BLUE = AMBER = CYAN = ""
        CONFIDENCE_COLOUR.update({k: "" for k in CONFIDENCE_COLOUR})
        return lambda s, c: s
    return lambda s, c: f"{c}{s}{RESET}"


def fmt_count(value: float) -> str:
    """Format an individual count without inventing precision.

    A boneless-wing floor of 12/34.5 is 0.34782608..., and printing all of
    that implies the portion size is known to seven figures when it is the
    least certain input in the model. Two significant figures is honest.
    """
    if value >= 100:
        return f"{value:,.0f}"
    if value >= 10:
        return f"{value:.1f}"
    if value >= 1:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:.2g}"


def fmt_rate(value: float) -> str:
    """Format a per-day production rate without rounding it out of existence.

    Two decimals is right for a hen at 0.79 eggs a day and wrong for a maple
    at 0.00518 gallons, which printed as "0.01 gallon/tree/day" -- a figure
    twice the real one, in the line that exists to show the working.
    """
    return f"{value:.2f}" if value >= 0.1 else f"{value:.3g}"


def fmt_distinct(value: float, ceiling: float) -> str:
    """Format the distinct count without hiding how close to the ceiling it is.

    A commodity chain lands at 11.99997, and rounding that to "12.00" quietly
    destroys the point: the ceiling is a limit the supply chain approaches,
    never a value it reaches. Show enough digits to keep it below the bound.
    """
    gap = ceiling - value
    # Same-day eggs actually REACH the ceiling: a hen lays at most one a day,
    # so twelve eggs in a day is exactly twelve hens. Printing "12.000000"
    # there implies a limit being approached when it has been hit, which is
    # the opposite of the truth. Wings approach and never arrive; eggs arrive.
    if gap <= 5e-7:
        return f"{value:g}"
    for places in (2, 3, 4, 5, 6):
        s = f"{value:.{places}f}"
        if float(s) < ceiling:
            return s
    return f"{value:.6f}"


def cmd_count(args) -> int:
    c = colour(sys.stdout.isatty() and not args.no_colour)
    conn = dbm.connect(args.db)

    product = dbm.get_product(conn, args.product)
    noun = product["individual_noun"]
    plural = product["individual_plural"]
    upi = product["units_per_individual_mode"]

    units = args.count
    basis = "unit"

    # A restaurant "dozen wings" is normally twelve SEGMENTS. Each whole
    # wing yields two sellable segments (drumette + flat; the tip is
    # diverted), so twelve pieces is six whole wings.
    if args.pieces:
        sellable = conn.execute(
            """SELECT COUNT(*) FROM product_segment
               WHERE product_id = ? AND sold_as_product = 1""",
            (product["id"],),
        ).fetchone()[0] or 1
        units = args.count / sellable
        basis = "segment"

    chain = args.chain or dbm.default_supply_chain(
        conn, product["species_slug"])
    loss = dbm.load_loss_stages(
        conn, product["species_slug"], product["slug"],
        include_optional=args.include_mortality,
        chain_slug=chain,
    )
    mixing = dbm.load_mixing_stages(conn, chain)
    correlated = dbm.load_correlated_groups(conn, product["species_slug"])

    # None for wings; a rate-and-window for eggs. run() derives the effective
    # per-individual yield from it, because 288 eggs a year is 0.79 in a day.
    recurring = dbm.make_recurring(product, args.window_days)

    res = run(
        units_requested=int(units) if float(units).is_integer() else units,
        units_per_individual=upi,
        loss_stages=loss,
        mixing_stages=mixing,
        iterations=args.iterations,
        seed=args.seed,
        recurring=recurring,
        correlated_groups=correlated,
        # No aggregate_units here on purpose. Whether a unit is a blend is
        # derived from the figures inside run(); this was one of three copies
        # of `yield_mode == "continuous"`, and copies drift. See run().
        anatomical=bool(product["is_anatomical_constant"]),
        floor_source=dbm.product_source_slug(conn, product["slug"]),
        # From the corpus, never from a module constant. Omitting this turns
        # every mixing mechanism off -- see model.MixingParams.
        params=dbm.load_mixing_params(conn),
    )

    # ---- the answer ----------------------------------------------------
    # Wording follows the product, not the word "wing". A boneless wing is
    # breast meat, so calling it a wing here would repeat the very error the
    # program exists to correct.
    unit_word = product["unit_name"]
    units_word = unit_word if units == 1 else f"{unit_word}s"
    contains_none = (product["named_part_content"] or 0) == 0

    print()
    if args.pieces:
        print(f"  {args.count:g} wing pieces is {units:g} whole wings.")
    if contains_none:
        # "contains no wing meat" -- singular, and about CONTENT rather than
        # a count of objects. Saying "no wings" invites the reading that we
        # are counting items, when the claim is that not one gram of the
        # named part is present.
        named = product["named_part"] or unit_word
        print(f"  {c(f'A {product['label'].lower()} contains no {named} meat.',
                     BOLD)}"
              f"  It is {product['source_part']} meat.")
        print()

    shown = fmt_distinct(res.distinct_mean, res.distinct_ceiling)

    # What this product's rate is CALLED, out of the row. Hardcoding "laying
    # rate" here made the program tell people about a tree's laying rate.
    rate_label = product["rate_label"] or "production rate"
    w = res.window_days
    window_word = (None if w is None else
                   "in a single day" if w == 1 else f"over {w:g} days")

    if res.hard_floor is not None:
        # Recurring products have TWO floors and quoting only one misleads.
        # hard_floor is physiology -- the fewest individuals capable of it.
        # floor is what you actually need, always higher, because a hen does
        # not lay every single day.
        #
        # Ceil for the count claim. A hard floor of 0.8 means one hen could
        # cover it with room to spare -- but "at least 0.8 hens" is not a
        # sentence about animals. The unrounded value stays in the detail
        # line below, where it reads as a ratio rather than a headcount.
        birds = math.ceil(res.hard_floor - 1e-9)
        noun_word = plural if birds != 1 else noun
        headline = (f"Gathered {window_word}, {units:g} {units_word} took at "
                    f"least {birds:g} {noun_word}.")
        print(f"  {c(headline, BOLD)}")
        if res.floor >= 1.0:
            # Above one individual the expected figure is a headcount, and
            # it is the number that actually matters: physiology says 12 hens
            # could do it, but hens do not lay every day, so you need ~15.
            need = f"{fmt_count(res.floor)} {plural}"
            print(f"  At the real {rate_label} you would need about "
                  f"{c(need, BOLD)} to count on it.")
        else:
            # Below one individual it is a ratio, not a headcount. "You would
            # need 0.042 hens" is not a sentence; one hen covering it many
            # times over is the same fact stated usefully.
            share = res.floor * 100
            print(f"  That is about {c(f'{share:.0f}% of one {noun}', BOLD)}"
                  f"'s output over that window.")
    elif window_word is not None:
        # Recurring, but with no per-day ceiling recorded -- a maple. There
        # is exactly ONE floor to quote here, and it is a yield floor: what
        # the average tree turns out, not what physiology forbids. Naming the
        # window is what keeps it from reading as the harder claim, since the
        # same tree answers differently for one season and for ten.
        floor_line = (f"Gathered {window_word}, {units:g} {units_word} took "
                      f"at least {fmt_count(res.floor)} {plural}.")
        print(f"  {c(floor_line, BOLD)}")
        print(f"  {DIM}That is a {rate_label} floor, not a physiological "
              f"one: no per-day ceiling is recorded for a "
              f"{noun}.{RESET}")
    else:
        floor_line = f"It took at least {fmt_count(res.floor)} {plural}."
        print(f"  {c(floor_line, BOLD)}")

    print(f"  The {units_word} on your plate came from about "
          f"{c(f'{shown} different {plural}', BOLD)}.")
    print()

    if res.hard_floor is not None:
        print(f"  {DIM}hard floor {fmt_count(res.hard_floor)}  ...  "
              f"ceiling {units:g}   window {res.window_days:g}d, "
              f"{fmt_rate(res.rate_per_day)} {unit_word}/{noun}/day   "
              f"(supply chain: {chain}){RESET}")
    elif res.window_days is not None:
        # No hard floor to print, because none exists. Saying "hard floor"
        # over the expected count is the claim this fix removed.
        print(f"  {DIM}floor {fmt_count(res.floor)}  ...  ceiling "
              f"{res.distinct_ceiling:g}   window {res.window_days:g}d, "
              f"{fmt_rate(res.rate_per_day)} {unit_word}/{noun}/day   "
              f"(supply chain: {chain}){RESET}")
    else:
        print(f"  {DIM}floor {fmt_count(res.floor)}  ...  ceiling "
              f"{res.distinct_ceiling:g}   "
              f"(supply chain: {chain}){RESET}")

    if res.required > res.floor + 1e-9:
        print(f"  {DIM}{fmt_count(res.required)} {plural} had to enter the "
              f"system to yield {units:g} sellable {units_word}.{RESET}")

    if args.include_mortality:
        print(f"  {DIM}includes grow-out mortality{RESET}")

    # ---- the reasoning -------------------------------------------------
    show = args.explain
    if not show and sys.stdin.isatty() and not args.quiet:
        print()
        try:
            show = input("  Show the reasoning? [y/N] ").strip().lower() \
                in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            show = False

    if show:
        explain(conn, res, c, plural,
                dbm.chain_floor_note(conn, chain))

    if not args.no_facts:
        facts = dbm.get_facts(conn, "result", limit=1)
        if facts:
            f = facts[0]
            print()
            print(f"  {c('Did you know?', BOLD)} {f['headline']}")
            print(f"  {DIM}{f['body'][:220]}{RESET}")
            print(f"  {DIM}source: {f['publisher']}{RESET}")

    print()
    conn.close()
    return 0


def explain(conn, res, c, plural: str,
            floor_note: str | None = None) -> None:
    slugs = [s.source_slug for s in res.trace if s.source_slug]
    sources = dbm.get_sources(conn, list({s for s in slugs if s}))

    print()
    print(f"  {c('HOW WE GOT THERE', BOLD)}")
    print(f"  {DIM}{'-' * 68}{RESET}")

    for step in res.trace:
        conf = step.confidence or ""
        col = CONFIDENCE_COLOUR.get(conf, "")
        badge = f"{c(conf, col)}" if conf else ""
        print()
        print(f"  {step.sequence:>2}. {c(step.stage_label, BOLD)}  {badge}")
        print(f"      {step.explanation}")
        if step.source_slug and step.source_slug in sources:
            s = sources[step.source_slug]
            print(f"      {DIM}source: {s['title']} - {s['publisher']}{RESET}")
            if s["url"]:
                print(f"      {DIM}{s['url']}{RESET}")

    if res.mixing_notes:
        print()
        print(f"  {c('WHY NOT EXACTLY THE FLOOR', BOLD)}")
        print(f"  {DIM}{'-' * 68}{RESET}")
        for n in res.mixing_notes:
            print(f"    - {n}")
        # Comes from the chain's own floor_note. It was hardcoded wing prose
        # here, which meant an egg question was answered with an explanation
        # about cut-up lines and deboning -- confident, detailed, and about
        # the wrong animal.
        if floor_note:
            print()
            for line in textwrap.wrap(floor_note.strip(), width=66):
                print(f"    {line}")

    if res.iterations:
        print()
        print(f"  {c('UNCERTAINTY', BOLD)}")
        print(f"  {DIM}{'-' * 68}{RESET}")
        print(f"    {res.iterations:,} Monte Carlo runs over the recorded")
        print(f"    lo/mode/hi band of every stage:")
        print(f"    {plural} required, 5th-95th percentile: "
              f"{res.required_lo:.2f} to {res.required_hi:.2f}")


def cmd_facts(args) -> int:
    c = colour(sys.stdout.isatty() and not args.no_colour)
    conn = dbm.connect(args.db)
    print()
    for f in dbm.get_facts(conn, "learning", limit=args.limit):
        stars = "*" * f["surprise"]
        print(f"  {c(f['headline'], BOLD)}  {DIM}{stars}{RESET}")
        print(f"  {f['body']}")
        print(f"  {DIM}source: {f['source_title']} - {f['publisher']}{RESET}")
        print()
    conn.close()
    return 0


def cmd_states(args) -> int:
    c = colour(sys.stdout.isatty() and not args.no_colour)
    conn = dbm.connect(args.db)
    rows = conn.execute(
        """SELECT region, avg_size, volume FROM v_broiler_size_stat
           WHERE year = 2025 AND month IS NULL AND region != 'United States'
           ORDER BY avg_size DESC"""
    ).fetchall()
    us = conn.execute(
        """SELECT avg_size FROM v_broiler_size_stat
           WHERE year = 2025 AND month IS NULL AND region = 'United States'"""
    ).fetchone()

    print()
    print(f"  {c('AVERAGE BROILER LIVE WEIGHT BY STATE, 2025', BOLD)}")
    print(f"  {DIM}USDA NASS. National average "
          f"{us['avg_size'] if us else 6.62} lb{RESET}")
    print()
    widest = max(r["avg_size"] for r in rows)
    for r in rows:
        bar = "#" * round(34 * r["avg_size"] / widest)
        print(f"  {r['region']:<16} {r['avg_size']:>5.2f} lb  {DIM}{bar}{RESET}")
    print()
    print(f"  {DIM}Ohio's birds are about half the weight of North "
          f"Carolina's. Small-bird{RESET}")
    print(f"  {DIM}programs feed fast food and tray pack; big-bird programs "
          f"feed deboning.{RESET}")
    print()
    conn.close()
    return 0


def cmd_seasonality(args) -> int:
    c = colour(sys.stdout.isatty() and not args.no_colour)
    conn = dbm.connect(args.db)
    raw = dbm.monthly_size_series(conn, year=args.year)
    if not raw:
        print(f"  no monthly data for {args.year}")
        conn.close()
        return 1

    national_raw = raw.pop("United States", None)
    national = (
        seas.analyse("United States", args.year, national_raw["values"],
                     unit=national_raw["unit"])
        if national_raw else None
    )
    regions = [
        seas.analyse(n, args.year, v["values"], unit=v["unit"])
        for n, v in raw.items()
    ]

    print()
    print(f"  {c(f'BROILER LIVE WEIGHT BY MONTH, {args.year}', BOLD)}")
    print(f"  {DIM}USDA NASS. J F M A M J J A S O N D{RESET}")
    print()
    if national:
        print(f"  {c('United States'.ljust(16), BOLD)} "
              f"{seas.sparkline(national.values)}  "
              f"{national.lo:.2f}-{national.hi:.2f} lb  "
              f"{national.swing_pct:>4.1f}%  {national.verdict}")
        print()
    for s in seas.rank(regions):
        mark = "*" if s.is_seasonal else " "
        print(f"  {s.region:<16} {seas.sparkline(s.values)}  "
              f"{s.lo:.2f}-{s.hi:.2f} lb  {s.swing_pct:>4.1f}%  "
              f"{DIM}{s.verdict:<12}{RESET}{mark}")
    print()

    for kind in ("peak", "trough"):
        co = seas.concordance(regions, kind)
        print(f"  {c(kind.upper() + ' AGREEMENT', BOLD)}  {co.verdict}")
        for line in textwrap.wrap(co.explanation, 68):
            print(f"  {line}")
        print()

    print(f"  {DIM}A swing is only a season if it is large next to the "
          f"month-to-month{RESET}")
    print(f"  {DIM}jitter. Most of these are not, and the count does not "
          f"move either way:{RESET}")
    print(f"  {DIM}a chicken has two wings in every month of the year."
          f"{RESET}")
    print()
    conn.close()
    return 0


def cmd_sources(args) -> int:
    c = colour(sys.stdout.isatty() and not args.no_colour)
    conn = dbm.connect(args.db)
    rows = conn.execute(
        "SELECT * FROM source ORDER BY source_type, slug"
    ).fetchall()
    print()
    for r in rows:
        print(f"  {c(r['title'], BOLD)}")
        print(f"    {r['publisher']}  {DIM}[{r['source_type']}]{RESET}")
        if r["url"]:
            print(f"    {DIM}{r['url']}{RESET}")
        print()
    conn.close()
    return 0


def cmd_chains(args) -> int:
    c = colour(sys.stdout.isatty() and not args.no_colour)
    conn = dbm.connect(args.db)
    print()
    for r in dbm.list_supply_chains(conn):
        mark = " (default)" if r["is_default"] else ""
        print(f"  {c(r['slug'], BOLD)}{mark}")
        print(f"    {r['description']}")
        print()
    conn.close()
    return 0


def cmd_export(args) -> int:
    from pathlib import Path

    from .export import export

    files = export(Path(args.dir), Path(args.db) if args.db else None)
    total = sum(f.stat().st_size for f in files)
    print(f"\n  wrote {len(files)} files to {args.dir} "
          f"({total / 1024:.1f} KB)\n")
    for f in sorted(files):
        print(f"    {f.name:<24} {f.stat().st_size:>7,} bytes")
    print()
    return 0


def cmd_gui(args) -> int:
    try:
        import uvicorn
    except ImportError:
        print("The GUI needs the optional extras:\n"
              "    pip install -e '.[gui]'", file=sys.stderr)
        return 1
    from .api import app
    print(f"\n  Chicken wing calculator: http://{args.host}:{args.port}\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def build_parser() -> argparse.ArgumentParser:
    # Shared flags, attached to every subcommand as well as the root, so
    # `wings 12 --no-colour` works as naturally as `wings --no-colour 12`.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default=None, help="path to the database")
    common.add_argument("--no-colour", "--no-color", dest="no_colour",
                        action="store_true")

    p = argparse.ArgumentParser(
        prog="wings",
        description="How many chickens does it take to make a dozen wings?",
        parents=[common],
    )
    # Root-only, not on `common`: `wings count --version` would be noise.
    p.add_argument(
        "--version", action="version",
        version=f"counting-chicken-wings {__version__}",
    )
    sub = p.add_subparsers(dest="cmd", parser_class=argparse.ArgumentParser)

    def add(name, **kw):
        return sub.add_parser(name, parents=[common], **kw)

    def add_count(sp):
        sp.add_argument("count", type=float, help="how many wings")
        sp.add_argument("--product", default="whole_wing")
        sp.add_argument("--chain", default=None,
                        help="supply chain (see: wings chains)")
        sp.add_argument("--pieces", action="store_true",
                        help="treat the count as SEGMENTS, the restaurant "
                             "convention, rather than whole wings")
        sp.add_argument("--window-days", type=float, default=None,
                        metavar="N",
                        help="for recurring products (eggs): the window the "
                             "question asks about. Defaults to 1 day, i.e. a "
                             "carton gathered together. A dozen eggs needs 12 "
                             "hens in a day but only 1 over a fortnight.")
        sp.add_argument("--include-mortality", action="store_true",
                        help="also count birds that died during grow-out")
        sp.add_argument("--explain", action="store_true",
                        help="show the reasoning without prompting")
        sp.add_argument("--quiet", action="store_true",
                        help="never prompt for the reasoning")
        sp.add_argument("--no-facts", action="store_true")
        sp.add_argument("--iterations", type=int, default=0,
                        help="Monte Carlo runs for an uncertainty band")
        sp.add_argument("--seed", type=int, default=None)
        sp.set_defaults(func=cmd_count)

    add_count(add("count", help="how many chickens for N wings"))

    f = add("facts", help="learning-centre facts")
    f.add_argument("--limit", type=int, default=20)
    f.set_defaults(func=cmd_facts)

    add("states", help="average bird size by state") \
        .set_defaults(func=cmd_states)
    se = add("seasonality", help="does bird weight have a season?")
    se.add_argument("--year", type=int, default=2025)
    se.set_defaults(func=cmd_seasonality)

    add("sources", help="every citation") \
        .set_defaults(func=cmd_sources)
    e = add("export", help="write the dataset as .txt and .csv")
    e.add_argument("--dir", default="data/exports")
    e.set_defaults(func=cmd_export)

    add("chains", help="available supply chains") \
        .set_defaults(func=cmd_chains)

    g = add("gui", help="launch the web interface")
    g.add_argument("--host", default="127.0.0.1")
    g.add_argument("--port", type=int, default=8000)
    g.set_defaults(func=cmd_gui)


    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    # `wings 12` is the headline use, so a bare number implies `count`.
    if argv and argv[0] not in {"-h", "--help"}:
        try:
            float(argv[0])
            argv.insert(0, "count")
        except ValueError:
            pass

    parser = build_parser()

    # Bare `wings` shows the identity and the help. The banner deliberately
    # does NOT appear above a count answer: the whole point of the CLI is a
    # two-line answer, and six lines of bird on top of it buries the headline.
    if not argv:
        print(banner(colour=sys.stdout.isatty()))
        print()
        parser.print_help()
        return 1

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
