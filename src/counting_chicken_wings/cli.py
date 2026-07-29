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
import sys

from . import db as dbm
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


def fmt_distinct(value: float, ceiling: float) -> str:
    """Format the distinct count without hiding how close to the ceiling it is.

    A commodity chain lands at 11.99997, and rounding that to "12.00" quietly
    destroys the point: the ceiling is a limit the supply chain approaches,
    never a value it reaches. Show enough digits to keep it below the bound.
    """
    gap = ceiling - value
    if gap <= 0:
        return f"{value:.2f}"
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

    chain = args.chain or dbm.default_supply_chain(conn)
    loss = dbm.load_loss_stages(
        conn, product["species_slug"], product["slug"],
        include_optional=args.include_mortality,
    )
    mixing = dbm.load_mixing_stages(conn, chain)

    res = run(
        units_requested=int(units) if float(units).is_integer() else units,
        units_per_individual=upi,
        loss_stages=loss,
        mixing_stages=mixing,
        iterations=args.iterations,
        seed=args.seed,
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

    shown = fmt_distinct(res.distinct_mean, units)
    print(f"  {c(f'It took at least {fmt_count(res.floor)} {plural}.', BOLD)}")
    print(f"  The {units_word} on your plate came from about "
          f"{c(f'{shown} different {plural}', BOLD)}.")
    print()
    print(f"  {DIM}floor {fmt_count(res.floor)}  ...  ceiling {units:g}   "
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
        explain(conn, res, c, plural)

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


def explain(conn, res, c, plural: str) -> None:
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
        print()
        print(f"    Mixing starts the instant the wings leave the bird. On")
        print(f"    the cut-up line a bird's two wings drop onto the same")
        print(f"    conveyor and part company, then size grading actively")
        print(f"    splits any pair that survived. That is why the answer")
        print(f"    sits near the ceiling rather than at the floor of "
              f"{res.floor:g}.")

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
        """SELECT region, avg_size, volume FROM regional_size_stat
           WHERE year = 2025 AND month IS NULL AND region != 'United States'
           ORDER BY avg_size DESC"""
    ).fetchall()
    us = conn.execute(
        """SELECT avg_size FROM regional_size_stat
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
