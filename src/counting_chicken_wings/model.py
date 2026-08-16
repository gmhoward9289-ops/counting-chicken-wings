"""The model: floor, loss chain, and mixing cascade.

Pure functions with no database or framework dependency, so the maths can
be tested in isolation and reused by the CLI, the API, and the tests.

Three independent questions, deliberately never conflated:

  FLOOR      The hard arithmetic minimum. A chicken has exactly two wings,
             so twelve wings cannot come from fewer than six chickens.
             This is the only number here that is not an estimate.

  REQUIRED   How many individuals had to enter the system to yield the
             requested product, after walking the loss chain backwards.
             Always >= floor.

  DISTINCT   How many individuals are actually represented in the portion
             you received. Bounded below by the floor and above by the
             number of units requested. This is the interesting one.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, fields, replace
from math import ceil, comb, erf, exp, lgamma, sqrt


# ---------------------------------------------------------------------------
# Floor
# ---------------------------------------------------------------------------

def floor_individuals(units: float, units_per_individual: float) -> float:
    """Hard minimum number of individuals for a given number of units.

    For countable products with an anatomical constant (2 wings per bird)
    this is a genuine floor, not an average -- which is what licenses the
    project's central claim of "6 or more, never fewer".
    """
    if units_per_individual <= 0:
        raise ValueError("units_per_individual must be positive")
    return units / units_per_individual


# ---------------------------------------------------------------------------
# Mixing cascade
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Recurring yield -- production over time
# ---------------------------------------------------------------------------

@dataclass
class RecurringYield:
    """A rate of production, plus the window the question asks about.

    Wings are timeless: a chicken has two, and the question needs no clock.
    Eggs are not. "288 eggs per hen" is only a fact once you say per year,
    and the answer to "how many hens for a dozen eggs" then depends entirely
    on how long you are willing to wait.

    `max_units_per_day` is the physiological ceiling and it is what makes the
    floor hard. A hen's ovulation cycle runs a little over 24 hours, so she
    lays at most about one egg a day, which means twelve eggs gathered in one
    day came from twelve different hens -- no supply chain arrangement can
    reduce that.
    """
    units_per_period: float          # 288 eggs
    period_days: float               # per 365 days
    window_days: float               # the question's window
    max_units_per_day: float | None = None

    def __post_init__(self):
        if self.period_days <= 0:
            raise ValueError("period_days must be positive")
        if self.window_days <= 0:
            raise ValueError("window_days must be positive")
        if self.units_per_period <= 0:
            raise ValueError("units_per_period must be positive")

    @property
    def rate_per_day(self) -> float:
        return self.units_per_period / self.period_days

    @property
    def units_per_individual(self) -> float:
        """Expected units one individual yields inside the window."""
        expected = self.rate_per_day * self.window_days
        if self.max_units_per_day is None:
            return expected
        # An individual cannot beat its own physiology, even if a long-run
        # average would suggest otherwise.
        return min(expected, self.max_units_per_day * self.window_days)

    @property
    def cap_per_individual(self) -> float | None:
        """Most units one individual could yield in the window, at best."""
        if self.max_units_per_day is None:
            return None
        return self.max_units_per_day * self.window_days


def recurring_floor(
    units: float, ry: RecurringYield
) -> tuple[float | None, float]:
    """Return (hard_floor, expected_individuals) for a recurring product.

    Two genuinely different numbers, and conflating them is the whole trap:

      hard_floor            fewest individuals physically capable of it,
                            from the per-day ceiling. Cannot be beaten.
                            None when the product records no ceiling.
      expected_individuals  how many you actually need at the real
                            production rate, which is always more, because
                            hens do not lay every single day.

    For a dozen eggs at 288 eggs/hen/year with a 1/day ceiling:
      window 1 day   -> hard 12,  expected 15.2
      window 15 days -> hard 0.8, expected 1.01

    A HARD FLOOR IS A CLAIM, and it needs a cap to stand on. This used to
    return `expected` in place of the missing floor, which read on every
    surface as "at least N trees, and that part is physiology, not
    estimation" -- for a figure that is an average of two extension services
    disagreeing about sap flow. A maple has no daily ceiling because nothing
    in the corpus records one, so the honest return is None and the surfaces
    say nothing rather than something unsupported.
    """
    expected = units / ry.units_per_individual
    cap = ry.cap_per_individual
    hard = units / cap if cap else None
    return hard, expected


def unit_is_aggregate(
    units_per_individual: float,
    recurring: "RecurringYield | None" = None,
) -> bool:
    """Is one unit of this product a BLEND of many individuals' output?

    THE test, and it is a fact about the product, not about its yield mode.
    One individual's ENTIRE natural output -- everything it makes, over its
    whole production period -- is less than one whole unit. If a sugar maple
    turns out about a quart of syrup in a season, then a gallon of syrup is
    necessarily several trees blended, in exactly the way a gram of saffron
    is 150 flowers blended.

      whole wing      2 wings per chicken           -> False
      boneless wing   34.5 pieces per chicken       -> False
      saffron stigma  3 stigmas per flower          -> False
      saffron gram    0.0067 g per flower           -> True
      table egg       288 eggs per hen per year     -> False
      maple gallon    0.233 gallons per tree/season -> True

    Note the window is deliberately NOT consulted. A hen yields 0.79 of an
    egg in a day, which is below one and says nothing at all about whether an
    egg is a blend -- it is not, an egg comes from exactly one hen. The
    natural period is what carries the physical meaning, so a recurring
    product is judged on `units_per_period`.

    This replaced `yield_mode == "continuous"`, copied into three call sites.
    Maple is `recurring`, so all three read its gallon as one tree's discrete
    part and the mixing formula collapsed a 194-tree floor to "about 1 tree"
    in the same paragraph.
    """
    natural = (recurring.units_per_period if recurring is not None
               else units_per_individual)
    return natural < 1.0


def mixing_draw_scale(
    units_requested: float,
    units_per_individual: float,
    floor: float,
    aggregate_units: bool = False,
    mixing_subunits_per_unit: float | None = None,
) -> tuple[float, float, str]:
    """Re-express a question at the granularity the mixing draw actually
    needs, and return (draw_units, draw_upi, drawn_label).

    Extracted from `run()` so `/api/mixing-curve` can draw the same curve
    the headline answer is built from, for any product, instead of a
    wing-only approximation that ignored both re-expressions below.

      aggregate_units             one unit is a BLEND of many individuals'
                                   output (a gram of saffron) -- re-express
                                   in individual-shares, see `run()`.
      mixing_subunits_per_unit    one unit is a homogenate of many smaller
                                   already-blended particles (a ground beef
                                   patty) -- re-express at the sub-unit
                                   scale, see `run()`.
      neither                     the unit is already the atomic thing the
                                   draw assumes (a wing): unchanged.
    """
    if aggregate_units:
        shares = max(1, ceil(floor))
        return shares, 1.0, f"{shares:,} individual-shares"
    if mixing_subunits_per_unit and mixing_subunits_per_unit > 1:
        draw_units = units_requested * mixing_subunits_per_unit
        draw_upi = units_per_individual * mixing_subunits_per_unit
        return draw_units, draw_upi, f"{draw_units:,.0f} mixing sub-units"
    return units_requested, units_per_individual, f"{units_requested} units"


# Below this many factors the explicit product is as cheap as four lgamma
# calls and stays bit-for-bit what it always was -- which keeps every
# headline path (wings: removed is 1 or 2) byte-identical. Above it the
# closed form wins, and by the time `removed` is this large the ~1e-9
# relative error of a log-gamma round trip is far below the model's own
# uncertainty.
_RATIO_LOOP_MAX = 64


def _ratio_choose(total: int, removed: int, drawn: int) -> float:
    """C(total-removed, drawn) / C(total, drawn), computed without big ints.

    Equals prod_{i=0}^{removed-1} (total-drawn-i) / (total-i), which is the
    probability that none of a specific individual's `removed` units are in
    a draw of `drawn` from `total`.

    For large `removed` -- aggregate products asked at particle scale can
    put thousands of an individual's units in the container -- the product
    is evaluated in closed form as a ratio of gamma functions instead of a
    Python loop, because this sits under the Monte Carlo resample loop and
    was measured dominating entire test-suite runs (#141-adjacent perf).
    """
    if drawn > total:
        raise ValueError("cannot draw more units than the container holds")
    if removed <= _RATIO_LOOP_MAX:
        r = 1.0
        for i in range(removed):
            denom = total - i
            if denom <= 0:
                return 0.0
            r *= (total - drawn - i) / denom
            if r <= 0.0:
                return 0.0
        return r

    # prod_{i=0}^{removed-1} (total-drawn-i)/(total-i)
    #   == [G(T-n+1)/G(T-n-r+1)] / [G(T+1)/G(T-r+1)]  in log space.
    # The loop returns 0.0 as soon as a numerator factor reaches zero or
    # below, i.e. whenever total - drawn < removed; same answer here.
    if total - drawn - removed + 1.0 <= 0.0:
        return 0.0
    return exp(
        lgamma(total - drawn + 1.0) - lgamma(total - drawn - removed + 1.0)
        + lgamma(total - removed + 1.0) - lgamma(total + 1.0)
    )


def _miss_probability(
    container_units: float,
    units_held: float,
    drawn: float,
    cluster_size: float = 1.0,
    retention: float = 0.0,
) -> float:
    """P(none of one individual's `units_held` units are in the draw).

    The exchangeable case -- cluster_size 1, retention 0 -- is exactly
    C(W-k, n)/C(W, n) and nothing below changes it. Everything else is the
    cluster-sampling generalisation.

    A scoop is not an exchangeable draw. It takes `c` contiguous units at a
    time, so the draw is really g = n/c whole clusters chosen from G = W/c.
    Two branches, weighted by how much adjacency survived the cascade:

      retention        the individual's units were kept together, so they
                       occupy ceil(k/c) consecutive clusters and are taken or
                       missed as one object. When taken they spend k of the n
                       units on a single individual. This is the only term in
                       the whole model that pushes the distinct count DOWN.
      1 - retention    the units sit at exchangeable positions in the
                       container, which is the ordinary hypergeometric on
                       UNITS -- unchanged by how the draw is grouped.

    That second branch is worth being careful about, because getting it wrong
    is easy and invents an effect that is not there. Grouping an exchangeable
    draw into clusters changes nothing: a pair at random positions falls in
    one cluster with probability (c-1)/(W-1) and is then taken with
    probability g/G, and adding that to the both-clusters-drawn case
    reproduces the unclustered answer exactly. Cluster size can only matter
    through positive correlation -- through `retention` -- which is precisely
    the survey-sampling result that clustering costs you nothing when the
    intra-class correlation is zero.

    So the two degenerate cases are exact rather than approximate: c=1 makes
    the branches identical (a one-unit grab cannot hold an adjacent pair),
    and k=1 makes them identical too (a single unit is not adjacent to
    itself). Both correctly leave `retention` inert.
    """
    exchangeable = _ratio_choose(container_units, units_held, drawn)
    if retention <= 0.0 or units_held <= 1:
        return exchangeable

    c = max(1.0, min(float(cluster_size), float(drawn), float(container_units)))
    if c <= 1.0:
        return exchangeable

    g = drawn / c
    grid = container_units / c
    blocks = ceil(units_held / c)
    together = _ratio_choose(grid, blocks, g)

    r = min(1.0, retention)
    return r * together + (1.0 - r) * exchangeable


def design_effect(cluster_size: float, retention: float) -> float:
    """Kish's design effect for the draw: deff = 1 + (c - 1) * ICC.

    Standard survey sampling, borrowed rather than invented. The intra-class
    correlation is the retention -- the probability that units grabbed
    together came from the same individual rather than being an independent
    pick -- and `drawn / deff` is the effective number of independent draws.

    Reported because the loss of effective sample size should be explicit
    rather than buried in a formula. deff = 1 is an exchangeable draw.
    """
    c = max(1.0, float(cluster_size))
    return 1.0 + (c - 1.0) * max(0.0, min(1.0, retention))


def expected_distinct_general(
    drawn: int,
    container_units: int,
    distinct_in_container: float,
    cluster_size: float = 1.0,
    retention: float = 0.0,
) -> float:
    """Expected distinct individuals in a draw, for any units-per-individual.

    The container holds `container_units` units contributed by
    `distinct_in_container` individuals, so each contributes an average of
    m = container_units / distinct_in_container units.

    An individual is missed entirely with probability C(W-m, n) / C(W, n).
    m is generally fractional, so rather than rounding or interpolating the
    totals, split the population into the two adjacent integer classes that
    reproduce both D and W exactly:

        n_hi individuals contribute (lo+1) units
        n_lo individuals contribute  lo    units
        n_hi + n_lo = D          n_hi*(lo+1) + n_lo*lo = W

    That is exact and physically meaningful, where interpolating the two
    totals is neither -- it can produce a value above `drawn`, which is
    impossible.

    `cluster_size` and `retention` make the draw a clustered one rather than
    an exchangeable one; see `_miss_probability`. Their defaults are the
    exchangeable draw, so leaving them alone reproduces the old formula
    exactly.
    """
    if drawn <= 0:
        return 0.0
    if drawn > container_units:
        raise ValueError(
            f"cannot draw {drawn} units from a container of {container_units}"
        )
    if distinct_in_container <= 0:
        raise ValueError("container must represent at least one individual")

    d = min(distinct_in_container, float(container_units))
    lo = int(container_units / d)
    if lo < 1:
        lo = 1

    n_hi = container_units - d * lo      # individuals contributing lo+1
    n_lo = d - n_hi                      # individuals contributing lo
    n_hi = max(0.0, n_hi)
    n_lo = max(0.0, n_lo)

    e = n_lo * (1.0 - _miss_probability(
        container_units, lo, drawn, cluster_size, retention))
    if n_hi > 0:
        e += n_hi * (1.0 - _miss_probability(
            container_units, lo + 1, drawn, cluster_size, retention))
    return min(e, float(drawn))


def expected_distinct(
    drawn: int,
    container_units: int,
    paired_individuals: float,
    cluster_size: float = 1.0,
    retention: float = 0.0,
) -> float:
    """Two-units-per-individual case, expressed via the general formula.

    `paired_individuals` contributed 2 units each; the rest contributed one
    apiece. Kept as its own entry point because bone-in wings -- the
    project's headline question -- are exactly this case.
    """
    if drawn <= 0:
        return 0.0
    if drawn > container_units:
        raise ValueError(
            f"cannot draw {drawn} units from a container of {container_units}"
        )

    p2 = max(0.0, min(paired_individuals, container_units / 2))
    p1 = container_units - 2 * p2          # individuals contributing one unit

    miss_two = _miss_probability(
        container_units, 2, drawn, cluster_size, retention)
    miss_one = _miss_probability(
        container_units, 1, drawn, cluster_size, retention)

    return p2 * (1.0 - miss_two) + p1 * (1.0 - miss_one)


@dataclass
class MixingStage:
    slug: str
    label: str
    pool: int                     # individuals represented at this stage
    mixing_kind: str              # 'random' | 'separating' | 'none'
    description: str = ""
    confidence: str = "estimate"
    source_slug: str | None = None
    # Pool sizes are estimates with real spread. Scientific mode samples
    # these alongside the loss factors instead of pinning them at the mode,
    # so the reported band reflects mixing uncertainty too. Default to the
    # point value when a range was not supplied.
    pool_lo: int = 0
    pool_hi: int = 0

    def band(self) -> tuple[int, int, int]:
        lo = self.pool_lo or self.pool
        hi = self.pool_hi or self.pool
        return min(lo, self.pool), self.pool, max(hi, self.pool)


# Evidence grades, best first. Scientific mode can require a minimum grade
# and re-run with weaker figures excluded, which answers a question worth
# asking: how much of the result depends on numbers we could not source?
CONFIDENCE_RANK = {
    "measured": 0,
    "derived": 1,
    "study": 2,
    "industry": 3,
    "estimate": 4,
}


def meets_confidence(level: str | None, minimum: str | None) -> bool:
    """True if `level` is at least as well-evidenced as `minimum`."""
    if not minimum:
        return True
    return (CONFIDENCE_RANK.get(level or "estimate", 99)
            <= CONFIDENCE_RANK.get(minimum, 99))


@dataclass(frozen=True)
class MixingParams:
    """The scalar parameters of the mixing model.

    THESE DEFAULTS ARE NOT THE SHIPPED VALUES, and that is deliberate.

    `SEPARATION_EFFICIENCY = 0.90` used to live here as a bare module
    constant. In this project that is a bug by definition -- a figure
    hardcoded in a module bypasses the citation audit, so the question "how
    much does this number matter?" could only be answered by writing a
    one-off sweep. It sat there for months; when someone finally swept it the
    answer turned out to be 0.0003 of a bird. Harmless, but unknowable, which
    is the entire argument for the rule.

    The real figures live in `data/mixing.yaml`, carry a confidence grade and
    a citation, are audited, and reach the model through
    `db.load_mixing_params`. Putting a copy of any of them here as a default
    would recreate exactly the bug that was just removed -- two figures, one
    audited and one not, free to drift.

    So `MixingParams()` is the INERT configuration: every mechanism off, the
    exchangeable draw, no adjacency. It is what the model does when it has
    been told nothing, which is the honest thing for it to do. If a headline
    figure ever moves because a caller forgot to pass params, it moves
    towards the assumption-free answer rather than towards a stale constant.
    `test_model.py` pins the corpus values reaching the real code path.
    """
    # How thoroughly a 'separating' stage pulls an individual's units apart.
    separation_efficiency: float = 0.0
    # Units taken per contiguous grab. 1 is the exchangeable draw.
    draw_cluster_size: float = 1.0
    # Fraction of "these two units are adjacent" surviving one stage.
    adjacency_retention_random: float = 0.0
    adjacency_retention_passthrough: float = 0.0

    @classmethod
    def inert(cls) -> "MixingParams":
        """Every mechanism off. Same as `MixingParams()`, but says so."""
        return cls()


def cascade_retention(
    stages: list[MixingStage],
    params: MixingParams,
) -> float:
    """How much unit-to-unit adjacency survives the whole cascade.

    The product of the stages' retentions, which is what finally gives a
    route's `mixing_kind` sequence something to determine. Before clustering
    existed, 'random' and 'none' were nearly interchangeable in the maths --
    both only ever raised the pool.

    A 'separating' stage gets no parameter of its own. Routing a bird's two
    wings into different grade boxes IS destroying their adjacency, so its
    retention falls out of the separation efficiency already estimated:
    (1 - efficiency) of pairs survive the split, and those then take the
    ordinary bulk-commingling hit for passing through the machine.

    The number this returns for the commodity cascade is about 1e-6. Six bulk
    commingling stages and a grader do not leave two wings adjacent. That is
    the finding, not a tuning failure.
    """
    r = 1.0
    for s in stages:
        if s.mixing_kind == "separating":
            r *= (params.adjacency_retention_random
                  * (1.0 - params.separation_efficiency))
        elif s.mixing_kind == "random":
            r *= params.adjacency_retention_random
        else:
            r *= params.adjacency_retention_passthrough
    return max(0.0, min(1.0, r))


def saturation_threshold(
    drawn: int,
    units_per_individual: float,
    epsilon: float = 0.05,
    max_pool: int = 10_000_000,
) -> int:
    """Smallest commingled pool whose answer is within `epsilon` of the ceiling.

    The headline claim of the mixing model, made checkable. The
    distinct-count curve flattens hard, and above this pool size the answer
    stops depending on the pool at all -- which is the honest reason the
    commodity number is what it is. Every pool figure in `data/mixing.yaml`
    is our estimate, and this is what licenses saying the commodity answer
    does not rest on them.

    Deliberately measured on a SINGLE 'random' stage with no separation and
    no clustering: the weakest, most conservative cascade that can be built.
    A real cascade only ever mixes harder, so a threshold established here
    holds a fortiori for one with a grader in it.

    Returns the pool in individuals. `max_pool` is a guard, not a model
    parameter -- a draw that can never saturate raises rather than looping.
    """
    if drawn <= 0:
        raise ValueError("must draw at least one unit")
    ceiling = float(drawn)

    def gap(pool: int) -> float:
        stages = [MixingStage("probe", "Probe", pool, "random")]
        c, d, _ = resolve_pool(stages, drawn, units_per_individual)
        return ceiling - expected_distinct_general(drawn, c, d)

    if gap(max_pool) > epsilon:
        raise ValueError(
            f"a draw of {drawn} never comes within {epsilon} of its ceiling"
        )

    lo, hi = 1, max_pool
    while lo < hi:
        mid = (lo + hi) // 2
        if gap(mid) <= epsilon:
            hi = mid
        else:
            lo = mid + 1
    return lo


def resolve_pool(
    stages: list[MixingStage],
    units_requested: int,
    units_per_individual: float,
    params: MixingParams | None = None,
) -> tuple[int, float, list[str]]:
    """Reduce a mixing cascade to (container_units, distinct_in_container, notes).

    Two quantities drive the answer:

      stream_individuals  the largest commingled population upstream
      container_units     the size of the container actually drawn from

    An individual is represented in your container unless *none* of its
    `units_per_individual` units were drawn into it, which happens with
    probability (1 - share)^upi. Working in terms of distinct individuals
    rather than surviving pairs is what lets this handle bone-in wings
    (2 units per bird) and boneless wings (tens of pieces per bird) with
    one formula.

    `params` carries the scalar parameters, which come from the corpus.
    Omitting it applies NO mechanism at all -- see `MixingParams`.
    """
    notes: list[str] = []
    upi = units_per_individual
    params = params or MixingParams()

    if not stages:
        # No mixing anywhere: the container is exactly what you cut up, and
        # every individual contributes all of its units. Answer == floor.
        container = max(units_requested, 1)
        distinct = container / upi
        notes.append(
            "No mixing stages apply, so every unit stays with its "
            "individual and the answer is exactly the floor."
        )
        return container, distinct, notes

    stream = max(s.pool for s in stages)
    draw_stage = stages[-1]
    container = max(units_requested, int(draw_stage.pool * upi))

    if stream * upi <= 0:
        raise ValueError("stream must contain at least one unit")

    # Expected distinct individuals represented in the container: an
    # individual is absent entirely only if none of its `upi` units were
    # drawn into it from the stream.
    #
    # That is the exchangeable version, and it assumes the container is a
    # uniform random sample of the stream. It is not: a bin is filled case by
    # case and a case is packed from a contiguous belt run, so an
    # individual's units are correlated in whether they land in the SAME
    # container. `retention` is how much of that correlation survives the
    # cascade -- the product of the stages' retentions.
    #
    #   retention 0   each of the individual's units lands independently,
    #                 which is exactly 1 - (1 - share)^upi as before.
    #   retention 1   its units travel as one object, in or out together, so
    #                 the container's W units come from W/upi individuals --
    #                 precisely the floor, which is the right limit.
    #
    # Written so the r=0 branch is bit-for-bit the old expression: the
    # clustering work must not perturb the answer it is being compared to.
    share = min(1.0, container / (stream * upi))
    retention = cascade_retention(stages, params)
    if retention <= 0.0:
        distinct = stream * (1.0 - (1.0 - share) ** upi)
    else:
        distinct = stream * (
            retention * share
            + (1.0 - retention) * (1.0 - (1.0 - share) ** upi)
        )
        notes.append(
            f"About {retention:.2%} of unit-to-unit adjacency survives this "
            f"cascade, so an individual's units are that much more likely to "
            f"land in the same container than chance alone would give."
        )

    # A separating stage routes an individual's units into different
    # streams, so more individuals are represented by fewer units each --
    # which pushes distinct up toward the container size.
    eff = params.separation_efficiency
    for s in stages:
        if s.mixing_kind != "separating" or eff <= 0.0:
            continue
        distinct += (container - distinct) * eff
        notes.append(
            f"{s.label} actively separates an individual's units, so "
            f"{eff:.0%} of the units that would have "
            f"shared a source are split apart."
        )

    # Clamp to what is physically possible. The lower bound is how many
    # individuals it takes to supply the container at all, but that cannot
    # exceed the container size: you can never have more contributors than
    # units, since every contributor gave at least one.
    #
    # The min() matters only for recurring products. With upi >= 1 (wings)
    # container/upi is always below container. With upi < 1 -- eggs over a
    # single day, where a hen yields 0.789 of an egg -- container/upi is
    # 15.2 against a 12-egg carton, and reporting "12 eggs from 15
    # individuals" is not a coherent sentence. The count was right anyway
    # because the caller re-clamps, but the audit trail printed the nonsense.
    lower = min(container / upi, float(container))
    distinct = max(lower, min(distinct, float(container)))

    per = container / distinct
    notes.append(
        f"Largest commingled pool is {stream:,} individuals; the container "
        f"drawn from holds about {container:,} units representing roughly "
        f"{distinct:,.0f} individuals, or {per:.3f} units each."
    )
    return container, distinct, notes


def draw_from_cascade(
    stages: list[MixingStage],
    drawn: int,
    units_per_individual: float,
    params: MixingParams | None = None,
) -> tuple[int, float, list[str], float]:
    """One full pass: resolve the container, then take the draw from it.

    Returns (container_units, distinct_in_container, notes, expected_distinct).

    Clustering enters twice, because it is two different questions with one
    physical answer:

      container level  did an individual's units land in the same BIN? The
                       full cascade retention applies -- a case is a long
                       contiguous run, so its length imposes no discount.
      draw level       given they are in the same bin, are they in the same
                       SCOOP? Discounted by (c-1)/c, because a grab of c
                       contiguous units that contains one member of an
                       adjacent pair contains the other only if the pair does
                       not straddle the edge of the grab. At c=1 that is 0:
                       a one-unit grab is exchangeable by construction, which
                       is the model as it stood before clustering existed.
    """
    params = params or MixingParams()
    container, distinct_in_container, notes = resolve_pool(
        stages, drawn, units_per_individual, params
    )

    c = max(1.0, params.draw_cluster_size)
    retention = cascade_retention(stages, params)
    draw_retention = retention * (c - 1.0) / c if c > 1.0 else 0.0

    expected = expected_distinct_general(
        int(drawn), container, distinct_in_container,
        cluster_size=c, retention=draw_retention,
    )

    deff = design_effect(c, draw_retention)
    if deff > 1.0 + 1e-12:
        notes.append(
            f"The draw is a grab of {c:g} contiguous units at a time rather "
            f"than {drawn} independent picks, so its design effect is "
            f"{deff:.3f} -- {drawn / deff:.2f} effective draws."
        )
    return container, distinct_in_container, notes, expected


# ---------------------------------------------------------------------------
# Loss chain
# ---------------------------------------------------------------------------

@dataclass
class LossStage:
    slug: str
    label: str
    sequence: int
    phase: str
    applies_to: str               # 'individual' | 'product' | 'mass'
    survive_lo: float
    survive_mode: float
    survive_hi: float
    confidence: str
    description: str = ""
    notes: str = ""
    optional: bool = False
    default_enabled: bool = True
    source_slug: str | None = None

    def affects_count(self) -> bool:
        """Mass-only stages never change how many individuals were needed.

        Frying a wing makes it lighter, not fractional. Twelve wings go in
        and twelve come out, so cook loss cannot move a count answer. This
        is enforced here rather than trusted to whoever writes the data.
        """
        return self.applies_to in ("individual", "product")


@dataclass
class CorrelatedGroup:
    """Loss stages that are NOT independent of one another (#77).

    Sampling every stage's triangular band independently -- as the Monte
    Carlo did before this existed -- lets errors partially cancel at
    roughly sqrt(n) across stages, which understates the reported band
    whenever the underlying causes actually move together. `wing_damage`,
    `grading_downgrade`, and `transport_doa` are the clearest case here:
    all three ride the same per-load handling quality, so a bad load is bad
    on all three at once, not independently.

    `rho` is a single-factor equicorrelation applied pairwise to every
    stage listed: each stage's sampled percentile is
    sqrt(rho)*shared + sqrt(1-rho)*idiosyncratic (see `_correlated_pick`),
    which preserves each stage's own triangular lo/mode/hi band exactly and
    changes only how the stages co-move. It is itself an unmeasured
    estimate -- the point is to stop asserting zero correlation, not to
    claim this figure is calibrated -- so it carries a confidence grade and
    a source citation like any other figure in the model, recorded in
    `data/loss_chain.yaml` rather than hardcoded here.
    """
    slug: str
    label: str
    stage_slugs: list[str]
    rho: float
    confidence: str = "estimate"
    source_slug: str | None = None


@dataclass
class StepTrace:
    """One line of the audit trail the 'show reasoning' toggle unfolds."""
    sequence: int
    kind: str                     # 'floor' | 'loss' | 'mixing'
    stage_slug: str
    stage_label: str
    value_used: float
    running_total: float
    explanation: str
    confidence: str | None = None
    source_slug: str | None = None


def required_individuals(
    units_requested: float,
    units_per_individual: float,
    stages: list[LossStage],
    picks: dict[str, float] | None = None,
    anatomical: bool = True,
    floor_source: str | None = None,
) -> tuple[float, list[StepTrace]]:
    """Walk the loss chain backwards from delivered units to individuals.

    Each surviving fraction divides, because we are running the pipeline in
    reverse: to end up with 12 wings after a stage that loses 5.7%, more
    than 12 had to enter it.

    `anatomical` distinguishes a floor that rests on a hard biological
    constant from one that rests on a reported average. Two wings per chicken
    and three stigmas per flower are anatomy, and the trace may fairly call
    them measured. About 150 flowers per gram of saffron is an extension
    service's rule of thumb, and labelling it "Anatomical floor / measured"
    would claim a grade the corpus does not hold for it -- in a project whose
    whole promise is that grades mean something.
    """
    picks = picks or {}
    trace: list[StepTrace] = []
    seq = 0

    floor = floor_individuals(units_requested, units_per_individual)
    trace.append(StepTrace(
        sequence=seq,
        kind="floor",
        stage_slug="floor",
        stage_label="Anatomical floor" if anatomical else "Yield floor",
        value_used=units_per_individual,
        running_total=floor,
        explanation=(
            f"{units_requested:g} units at {units_per_individual:g} per "
            f"individual is a hard minimum of {floor:g}. No loss anywhere "
            f"in the chain can push this number down."
        ) + ("" if anatomical else
             " The ratio is a reported average rather than a biological "
             "constant, so the floor is only as firm as that figure."),
        confidence="measured" if anatomical else "industry",
        source_slug=floor_source,
    ))

    running = floor
    for st in sorted(stages, key=lambda s: s.sequence):
        seq += 1
        f = picks.get(st.slug, st.survive_mode)

        if not st.affects_count():
            trace.append(StepTrace(
                sequence=seq,
                kind="loss",
                stage_slug=st.slug,
                stage_label=st.label,
                value_used=f,
                running_total=running,
                explanation=(
                    f"{st.label} scales mass by {f:.3f} but does not change "
                    f"unit counts, so the individual count is unaffected."
                ),
                confidence=st.confidence,
                source_slug=st.source_slug,
            ))
            continue

        if f <= 0:
            raise ValueError(f"stage {st.slug} has a non-positive factor")

        before = running
        running = running / f
        trace.append(StepTrace(
            sequence=seq,
            kind="loss",
            stage_slug=st.slug,
            stage_label=st.label,
            value_used=f,
            running_total=running,
            explanation=(
                f"{st.label} lets {f:.4f} through, so {before:.4f} becomes "
                f"{running:.4f} individuals required."
            ),
            confidence=st.confidence,
            source_slug=st.source_slug,
        ))

    return running, trace


# ---------------------------------------------------------------------------
# Full run
# ---------------------------------------------------------------------------

@dataclass
class Result:
    units_requested: int
    units_per_individual: float
    floor: float
    required: float
    distinct_mean: float
    distinct_lo: float = 0.0
    distinct_hi: float = 0.0
    # Populated only when iterations > 0; equal to `required` otherwise so
    # callers can render a band unconditionally.
    required_lo: float = 0.0
    required_hi: float = 0.0
    container_units: int = 0
    paired_individuals: float = 0.0
    # The most individuals that could possibly be represented. For a
    # countable or recurring product this is the unit count -- twelve wings
    # came from at most twelve chickens, because a wing belongs to one bird.
    # For a CONTINUOUS product the unit count says nothing (one gram is not
    # one flower) and the ceiling is the floor instead: mass is fungible, so
    # every contributing individual supplies one share and there are exactly
    # `floor` shares. Reported rather than recomputed by each caller, which
    # is how "floor 150 ... ceiling 1" got printed.
    distinct_ceiling: float = 0.0
    trace: list[StepTrace] = field(default_factory=list)
    mixing_notes: list[str] = field(default_factory=list)
    iterations: int = 0
    # The interval actually reported, e.g. 0.90 for a 5th-95th percentile
    # band. Recorded on the result so a chart can never mislabel its axis.
    confidence_level: float = 0.90
    # Which statistic populates `required`. Recorded for the same reason
    # `confidence_level` is: a number that can silently swap out from under
    # its own label is a lie waiting to happen. "deterministic" means the
    # product of every stage's survive_mode -- point value, no simulation.
    # "monte_carlo_median" means the 50th percentile of the resampled
    # distribution (see `run`'s iterations > 0 branch). The two are NOT
    # interchangeable: on the real loss chain the deterministic figure sits
    # at roughly the 19th percentile of its own simulated distribution
    # (#76), because a triangular distribution's mean is (lo+mode+hi)/3, not
    # its mode, and `required_individuals` divides by each survival fraction
    # in turn -- Jensen's inequality on 1/x compounds that skew across every
    # stage. The median is reported instead of the mean because it is the
    # honest centre of the band AND is invariant under that reciprocal
    # transform (median(1/X) == 1/median(X), which is not true of the mean).
    required_estimator: str = "deterministic"
    # The units the mixing cascade was actually asked in, after the
    # aggregate-unit re-expression. For a wing these are just
    # (units_requested, units_per_individual); for a gram of saffron they are
    # (1,800 individual-shares, 1.0). Reported so that a caller wanting to
    # run a SECOND analysis over the same cascade -- `variance_decomposition`
    # is the one that exists -- can ask it the same question this run
    # answered, instead of re-deriving the condition and getting it wrong.
    # `test_aggregate_units.py` forbids that re-derivation by name.
    draw_units: float = 0.0
    draw_upi: float = 0.0
    # Raw Monte Carlo draws, kept for histograms. Empty unless requested.
    required_samples: list[float] = field(default_factory=list)
    distinct_samples: list[float] = field(default_factory=list)
    excluded_stages: list[str] = field(default_factory=list)

    # --- recurring products only (eggs, milk, honey) ---------------------
    # None for timeless products. A chicken has two wings and the question
    # needs no clock; "288 eggs per hen" means nothing until you say per what.
    window_days: float | None = None
    # The physiological floor: fewest individuals *capable* of the order in
    # the window, from the per-day ceiling. Distinct from `floor`, which is
    # what you actually need at the real production rate. For a dozen
    # same-day eggs these are 12 and 15.2 -- and reporting only one of them
    # is the trap this pair exists to avoid.
    hard_floor: float | None = None
    rate_per_day: float | None = None
    cap_per_individual: float | None = None


def _triangular(lo: float, mode: float, hi: float, rng: random.Random) -> float:
    if lo == hi:
        return mode
    return rng.triangular(lo, hi, mode)


def _norm_cdf(z: float) -> float:
    """Standard normal CDF, via the error function -- no scipy dependency."""
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def _triangular_ppf(p: float, lo: float, mode: float, hi: float) -> float:
    """Inverse CDF of a triangular(lo, mode, hi) distribution at quantile p.

    Lets a stage be sampled from a percentile handed to it -- e.g. one
    derived from a shared latent factor (`_correlated_pick`) -- rather than
    only ever from its own independent draw, while landing on exactly the
    same triangular distribution `_triangular` would have used.
    """
    if lo == hi:
        return mode
    p = 0.0 if p < 0.0 else (1.0 if p > 1.0 else p)
    span = hi - lo
    fc = (mode - lo) / span
    if p < fc:
        return lo + sqrt(p * span * (mode - lo))
    return hi - sqrt((1.0 - p) * span * (hi - mode))


def _correlated_pick(
    stage: "LossStage",
    group: "CorrelatedGroup | None",
    group_shared: dict[str, float],
    rng: random.Random,
) -> float:
    """One stage's Monte Carlo draw, honoring a shared latent factor if any.

    Ungrouped stages fall through to the plain independent draw. A grouped
    stage instead draws its OWN standard-normal deviate and blends it with
    the group's shared deviate (drawn once per iteration, before any stage
    loop, so every member of the group sees the same value that iteration),
    then converts the blend to a percentile and looks that percentile up in
    the stage's own triangular band. sqrt(rho)/sqrt(1-rho) weighting is the
    standard single-factor construction that makes the PAIRWISE Pearson
    correlation between any two members' latent deviates equal to rho.
    """
    if group is None:
        return _triangular(stage.survive_lo, stage.survive_mode,
                            stage.survive_hi, rng)
    shared = group_shared[group.slug]
    idio = rng.gauss(0.0, 1.0)
    z = sqrt(group.rho) * shared + sqrt(1.0 - group.rho) * idio
    return _triangular_ppf(_norm_cdf(z), stage.survive_lo,
                            stage.survive_mode, stage.survive_hi)


def _jitter_pools(
    stages: list[MixingStage],
    pools: list[float],
) -> list[MixingStage]:
    """Rebuild a cascade with new pool sizes, one per stage, in order.

    Shared by the Monte Carlo in `run` and by `variance_decomposition`, and
    that sharing is the point. Both need to take a resampled pool figure and
    turn it back into something `draw_from_cascade` will accept, and the two
    would eventually disagree about the clamp -- `max(1, int(...))`, which is
    a floor rather than a round, so a sampled 4.9 is four individuals -- if
    each kept its own copy. Only the sampling differs between the callers:
    `run` draws from the rng, the decomposition inverts a quantile.
    """
    return [
        MixingStage(slug=m.slug, label=m.label, pool=max(1, int(p)),
                    mixing_kind=m.mixing_kind)
        for m, p in zip(stages, pools)
    ]


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated percentile on an already-sorted list."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def run(
    units_requested: int,
    units_per_individual: float,
    loss_stages: list[LossStage],
    mixing_stages: list[MixingStage],
    iterations: int = 0,
    seed: int | None = None,
    confidence_level: float = 0.90,
    min_confidence: str | None = None,
    keep_samples: bool = False,
    recurring: RecurringYield | None = None,
    aggregate_units: bool | None = None,
    anatomical: bool = True,
    floor_source: str | None = None,
    params: MixingParams | None = None,
    param_bands: dict[str, tuple[str, float, float, float, str]] | None = None,
    correlated_groups: list[CorrelatedGroup] | None = None,
    mixing_subunits_per_unit: float | None = None,
) -> Result:
    """Compute floor, required, and distinct for one question.

    `recurring` turns a rate into an answer. Pass it for products that are
    produced over time rather than harvested once, and `units_per_individual`
    is then derived from the window instead of being taken at face value --
    288 eggs a year is 0.79 in a day, and using the annual figure for a
    same-day question understates the hens needed by roughly 285x.

    With iterations > 0 both the loss chain AND the mixing pool sizes are
    resampled from their triangular lo/mode/hi bands, so the reported
    interval reflects the recorded uncertainty of the inputs rather than
    being asserted. `confidence_level` sets the interval width -- 0.90 gives
    a 5th-95th percentile band, 0.99 gives 0.5th-99.5th.

    The headline `required` figure returned is the MEDIAN of the resampled
    distribution, not its mean, and `res.required_estimator` records which
    (see the field's docstring on `Result`, and #76). A triangular
    distribution's mean sits above its own mode, and `required_individuals`
    divides by every stage's survival fraction in turn, so that upward bias
    compounds across the chain -- on the real loss chain the deterministic
    product-of-modes figure sits at roughly the 19th percentile of its own
    simulated distribution. The median is both the honest centre of the
    band and invariant under that reciprocal transform, which the mean is
    not.

    `correlated_groups` (#77) names loss stages that are not independent of
    one another -- e.g. wing damage, grading downgrade, and transport DOA
    riding the same per-load handling quality -- and gives their pairwise
    correlation `rho`. Sampling every stage independently, as this did
    before groups existed, lets errors partially cancel at roughly sqrt(n)
    and understates the band; grouped stages instead share one latent
    factor per iteration (see `_correlated_pick`). Ungrouped stages, and
    every stage when this is None, sample exactly as before.

    `min_confidence` drops loss stages whose evidence grade is weaker than
    the given level, which answers "what does the answer look like using
    only figures we could actually source?".

    `aggregate_units` says one unit is a blend of many individuals' output
    rather than one individual's discrete part. LEAVE IT NONE: it is derived
    from the figures via `unit_is_aggregate`, which is the only reason the
    CLI, the API and the analysis endpoint cannot disagree about it. They
    each held their own copy of the condition, all three said
    `yield_mode == "continuous"`, and all three were wrong about maple on
    the same day.

    `mixing_subunits_per_unit` is the mirror image of `aggregate_units`: it
    says one unit is not itself the atomic thing the mixing draw assumes, but
    a homogenate made of many smaller, already-blended particles (a ground
    beef patty is not one intact slice of one animal; it is a scoop of a
    slurry). Comes from `product.mixing_subunits_per_unit` -- see the field's
    comment in schema.sql for why a wing does not need this and a patty does.
    None (almost every product) leaves the draw at the unit's own scale, as
    before.

    `params` carries the mixing model's scalar parameters -- separation
    efficiency, scoop size, adjacency retention. They live in
    `data/mixing.yaml` and reach here through `db.load_mixing_params`;
    omitting them applies no mechanism at all rather than a stale default.
    See `MixingParams` for why there is no Python copy of the shipped values.

    `param_bands` (from `db.load_mixing_param_bands`) is the same four
    parameters with their lo/mode/hi bands, and is what lets the Monte Carlo
    loop resample them (#98) the same way it already resamples pool sizes.
    Omitting it holds every parameter at `params`' fixed value for every
    iteration, as it always has -- the deterministic pass above is
    unaffected either way; it stays pinned at the mode regardless, because a
    single reported figure has to come from somewhere fixed.

    Sampled independently. `separation_efficiency` and
    `adjacency_retention_random` both describe how roughly the line treats
    two units of the same individual and are probably correlated in reality
    -- the same caveat `variance_decomposition` records about the same two
    inputs. Asserting independence here is the same simplification, made in
    the same place, for the same reason: a correlated estimator is a larger
    piece of work than this fix, and an uncorrelated resample is still
    strictly more honest than not resampling at all.

    Measured effect (#98), before/after `distinct_hi - distinct_lo` across
    every named supply chain: the saturated commodity routes barely move
    (commodity_foodservice 0.00003 to 0.00006; grocery_retail similarly
    tiny), exactly as expected -- pool-size uncertainty already dominates
    them completely, leaving the parameters nothing to add. Every other
    route widens, several substantially: local_butcher 0.61 to 0.92,
    commodity_ground_beef 0.03 to 0.79, handreeled_silk 0.002 to 0.82,
    garden_saffron 0.80 to 1.79. This is not the negative result the issue
    that opened this considered likely -- the parameters carry real,
    previously-unreported uncertainty on most non-commodity routes, not just
    on local_butcher.
    """
    # Derived from the data before the window rewrites anything, because the
    # question "is a unit a blend?" is about the product's natural output,
    # not about how long the asker is willing to wait.
    if aggregate_units is None:
        aggregate_units = unit_is_aggregate(units_per_individual, recurring)

    excluded = [s.slug for s in loss_stages
                if not meets_confidence(s.confidence, min_confidence)]
    if excluded:
        loss_stages = [s for s in loss_stages
                       if meets_confidence(s.confidence, min_confidence)]

    # For a recurring product the per-individual yield is a function of the
    # window, so it must be recomputed before anything downstream uses it --
    # the loss chain and the mixing cascade both take it as an input.
    hard_floor = None
    if recurring is not None:
        units_per_individual = recurring.units_per_individual
        hard_floor, _ = recurring_floor(units_requested, recurring)

    floor = floor_individuals(units_requested, units_per_individual)
    required, trace = required_individuals(
        units_requested, units_per_individual, loss_stages,
        anatomical=anatomical, floor_source=floor_source,
    )

    draw_units, draw_upi, drawn_label = mixing_draw_scale(
        units_requested, units_per_individual, floor,
        aggregate_units=aggregate_units,
        mixing_subunits_per_unit=mixing_subunits_per_unit,
    )

    def _draw(stages, use_params=None):
        """One pass of the mixing cascade, in whatever unit the question is
        being asked in.

        A closure rather than two call sites, because there WERE two: the
        deterministic pass below re-expressed an aggregate unit in
        individual-shares and the Monte Carlo pass at the bottom of this
        function did not, so `wings count 12 --product saffron_gram
        --iterations 2000` and `/api/scientific` reported 12 flowers for a
        floor of 1,800 -- the same contradiction the shares fix exists to
        remove, surviving in the path nobody re-ran.

        `use_params` lets the Monte Carlo pass substitute a per-iteration
        jittered `MixingParams` (#98) without disturbing the deterministic
        pass above, which must stay pinned at the mode.
        """
        return draw_from_cascade(stages, draw_units, draw_upi,
                                  use_params if use_params is not None
                                  else params)

    container, distinct_in_container, notes, distinct = _draw(mixing_stages)

    trace.append(StepTrace(
        sequence=len(trace),
        kind="mixing",
        stage_slug="mixing_cascade",
        stage_label="Mixing cascade",
        value_used=distinct_in_container,
        running_total=distinct,
        explanation=(
            f"Drawing {drawn_label} from a container of "
            f"{container:,} gives about {distinct:.2f} distinct individuals."
        ),
        confidence="estimate",
    ))

    res = Result(
        units_requested=units_requested,
        units_per_individual=units_per_individual,
        floor=floor,
        required=required,
        distinct_mean=distinct,
        distinct_lo=distinct,
        distinct_hi=distinct,
        container_units=container,
        paired_individuals=distinct_in_container,
        draw_units=draw_units,
        draw_upi=draw_upi,
        distinct_ceiling=(
            ceil(floor) if aggregate_units
            # A homogenate's ceiling is not "how many units you asked for"
            # -- that is the wing assumption, and a patty is not one wing.
            # It is bounded by the pool it was actually drawn from: you can
            # never represent more individuals than existed upstream, no
            # matter how finely the draw is expressed.
            else min(float(draw_units), distinct_in_container)
            if mixing_subunits_per_unit and mixing_subunits_per_unit > 1
            else float(units_requested)
        ),
        trace=trace,
        mixing_notes=notes,
        confidence_level=confidence_level,
        excluded_stages=excluded,
        window_days=recurring.window_days if recurring else None,
        hard_floor=hard_floor,
        rate_per_day=recurring.rate_per_day if recurring else None,
        cap_per_individual=(
            recurring.cap_per_individual if recurring else None
        ),
    )
    res.required_lo = res.required_hi = required
    res.distinct_lo = res.distinct_hi = distinct

    if iterations > 0:
        rng = random.Random(seed)
        req_s: list[float] = []
        dist_s: list[float] = []

        # Map each (post-exclusion) stage to the group it belongs to, if
        # any, once -- not per iteration. A group left with fewer than two
        # of its stages present (excluded by min_confidence, or simply not
        # part of this chain) has nothing left to correlate.
        stage_group: dict[str, CorrelatedGroup] = {}
        for g in (correlated_groups or []):
            present = [s for s in g.stage_slugs
                       if any(st.slug == s for st in loss_stages)]
            if len(present) < 2:
                continue
            for slug in present:
                stage_group[slug] = g
        active_groups = {g.slug for g in stage_group.values()}

        for _ in range(iterations):
            # One shared latent draw per group per iteration -- every
            # member stage this iteration sees the SAME value, which is
            # what makes them move together rather than independently.
            group_shared = {gs: rng.gauss(0.0, 1.0) for gs in active_groups}
            picks = {
                s.slug: _correlated_pick(
                    s, stage_group.get(s.slug), group_shared, rng
                )
                for s in loss_stages
            }
            r, _ = required_individuals(
                units_requested, units_per_individual, loss_stages, picks
            )
            req_s.append(r)

            # Resample the mixing cascade too. Pool sizes are among the
            # softest numbers in the model, so holding them fixed would
            # understate the spread on the headline figure.
            jittered = _jitter_pools(mixing_stages, [
                _triangular(*m.band(), rng) for m in mixing_stages
            ])
            # Resample the scalar parameters too (#98), independently of
            # each other and of the pools -- the same band-sampling as
            # above, applied to separation efficiency, scoop size, and
            # both adjacency-retention parameters instead of pool sizes.
            # `replace` starts from `base` so any field absent from
            # `param_bands` keeps its fixed value rather than reverting to
            # MixingParams()'s inert zero.
            mc_params = (
                replace(params or MixingParams(), **{
                    name: _triangular(lo, mode, hi, rng)
                    for name, (_, lo, mode, hi, _) in param_bands.items()
                })
                if param_bands else params
            )
            # Same draw as the deterministic pass, aggregate handling and
            # all. It is the same function precisely so it cannot differ.
            dist_s.append(_draw(jittered, mc_params)[3])

        req_s.sort()
        dist_s.sort()
        tail = (1.0 - confidence_level) / 2.0

        res.iterations = iterations
        # Median, not mean (#76) -- see the docstring above and on
        # `Result.required_estimator` for why the two disagree by enough to
        # matter here.
        res.required = _percentile(req_s, 0.5)
        res.required_estimator = "monte_carlo_median"
        res.required_lo = _percentile(req_s, tail)
        res.required_hi = _percentile(req_s, 1.0 - tail)
        res.distinct_mean = sum(dist_s) / len(dist_s)
        res.distinct_lo = _percentile(dist_s, tail)
        res.distinct_hi = _percentile(dist_s, 1.0 - tail)

        if keep_samples:
            res.required_samples = req_s
            res.distinct_samples = dist_s

    return res


# ---------------------------------------------------------------------------
# Sensitivity
# ---------------------------------------------------------------------------

@dataclass
class Sensitivity:
    slug: str
    label: str
    applies_to: str
    confidence: str
    low_result: float          # birds required with this stage at survive_hi
    high_result: float         # birds required with this stage at survive_lo
    swing: float               # high - low, the tornado bar width
    share: float = 0.0         # fraction of total swing across all stages


def sensitivity(
    units_requested: float,
    units_per_individual: float,
    loss_stages: list[LossStage],
) -> list[Sensitivity]:
    """One-at-a-time tornado: which stage moves the answer most?

    Each stage is swung across its own lo/hi while every other stage is held
    at its mode. The result is directly interpretable as "how much does our
    uncertainty about THIS number cost us?", which is what decides where
    more research is worth doing.

    Mass-only stages come back with zero swing, correctly: they cannot move
    a count no matter how uncertain they are. That is a useful thing to see
    on the chart rather than something to hide.

    OAT IS NOT A SHORTCUT HERE. IT IS EXACT, AND IT SHOULD NOT BE
    "UPGRADED" TO A SOBOL ANALYSIS.
    -------------------------------------------------------------
    `required_individuals` divides the floor by each stage's survival
    fraction in turn, so required = floor / prod(f_i) -- a pure product.
    Take logs and it is exactly additive:

        log required = log floor - sum_i log f_i

    with d(log required)/d(log f_i) = -1 no matter what any other stage is
    doing. A function with no interaction terms has no higher-order Sobol
    indices to find: ST equals S1 for every stage, the first-order indices
    sum to one, and swinging one stage across its band with the others held
    at their modes recovers that stage's entire contribution. A
    variance-based decomposition of this chain would spend N*(n+2) noisy
    model evaluations reproducing what these 2n deterministic ones already
    give exactly.

    Three honest caveats, none of which changes that conclusion. The bars
    are reported in linear individuals rather than in log space, so `share`
    is a share of total SWING and only approximately a share of variance --
    read it as "where is more research worth doing", which is what it is
    for. `CorrelatedGroup` (#77) means the stages are not independent;
    correlation changes how the variances add up, but it is a property of
    the inputs rather than of the model's functional form, and the absence
    of interaction terms survives it. And mass-only stages drop out of the
    product entirely, which is why they register zero.

    NONE OF THIS TRANSFERS TO `distinct`. The mixing cascade takes a max
    over pools, a ratio, a product of retentions, a (1 - share)^upi and an
    iterative separation top-up. It is not a product of factors and its
    inputs genuinely interact: on the commodity cascade the first-order
    indices sum to only about 0.7, so nearly a third of the variance lives
    in interactions that a one-at-a-time sweep cannot see by construction.
    That is `variance_decomposition`, below. Two different questions about
    two different outputs, kept apart on purpose.
    """
    out: list[Sensitivity] = []
    for target in loss_stages:
        best = {target.slug: target.survive_hi}    # least loss
        worst = {target.slug: target.survive_lo}   # most loss
        lo_r, _ = required_individuals(
            units_requested, units_per_individual, loss_stages, best
        )
        hi_r, _ = required_individuals(
            units_requested, units_per_individual, loss_stages, worst
        )
        out.append(Sensitivity(
            slug=target.slug,
            label=target.label,
            applies_to=target.applies_to,
            confidence=target.confidence,
            low_result=lo_r,
            high_result=hi_r,
            swing=hi_r - lo_r,
        ))

    total = sum(s.swing for s in out) or 1.0
    for s in out:
        s.share = s.swing / total
    out.sort(key=lambda s: s.swing, reverse=True)
    return out


# ---------------------------------------------------------------------------
# Variance decomposition
# ---------------------------------------------------------------------------
#
# WHY THIS EXISTS SEPARATELY FROM `sensitivity`
# ---------------------------------------------
# `sensitivity` above answers "which loss stage moves `required` most?" by
# one-at-a-time swings, and for that question OAT is not an approximation --
# see its docstring. This answers a different question about a different
# output: which mixing input moves `distinct`, the number the project is
# named after? The mixing model takes a max over pools, a ratio, a product
# of retentions, a (1 - share)^upi and an iterative separation top-up. It is
# not a product of factors, its inputs genuinely interact, and OAT would
# miss exactly the interaction that matters. So this is variance-based.
#
# Everything here is stdlib `random` and `math`. The project has one runtime
# dependency (PyYAML) and hand-rolls `_norm_cdf` and `_triangular_ppf` to
# keep it that way; pulling in numpy/scipy/SALib for an estimator that is
# nine lines of arithmetic would be a poor trade.


@dataclass
class VarianceShare:
    """One input's share of the variance in `distinct`.

    Deliberately NOT the same shape as `Sensitivity`. That one reports a
    swing measured in chickens on `required`; this one reports a
    dimensionless share of variance in `distinct`. Two different questions,
    two different outputs, kept apart so they cannot be read off one axis.
    """
    slug: str
    label: str
    kind: str                  # 'pool' | 'parameter'
    confidence: str            # the input's own grade
    first_order: float         # S1: this input acting alone
    total_order: float         # ST: this input including its interactions
    first_lo: float = 0.0      # bootstrap percentile band on S1
    first_hi: float = 0.0
    total_lo: float = 0.0      # ... and on ST
    total_hi: float = 0.0
    degenerate: bool = False   # lo == hi: no band, so nothing to propagate
    inert: bool = False        # real band, but the model never reads it


@dataclass
class VarianceDecomposition:
    output: str = "distinct"
    mean: float = 0.0
    variance: float = 0.0
    sd: float = 0.0
    sample_lo: float = 0.0     # observed spread, in individuals
    sample_hi: float = 0.0
    samples: int = 0           # N
    evaluations: int = 0       # N * (n + 2)
    bootstrap: int = 0
    confidence_level: float = 0.90
    seed: int | None = None
    shares: list[VarianceShare] = field(default_factory=list)
    sum_first_order: float = 0.0
    sum_total_order: float = 0.0
    notes: list[str] = field(default_factory=list)


def _centre(fa: list[float], fb: list[float]) -> tuple[list[float],
                                                       list[float],
                                                       float, float]:
    """Centre both output vectors on their joint mean, and return the variance.

    THE CENTRING IS LOAD-BEARING AND IS NOT A STYLISTIC CHOICE.

    On the commodity cascade `distinct` is about 12.0 and its variance is
    about 4.5e-10. Forming products of uncentred values at that ratio is
    almost pure floating-point cancellation: the first version of this code
    returned a first-order index of -15138 for the distributor stage, and
    -20818 for the sum. Subtracting the mean first returns +0.457, on
    identical model evaluations. Anyone who re-derives these estimators from
    a paper and drops the centring will conclude the model is broken.
    """
    n = len(fa)
    mu = (sum(fa) + sum(fb)) / (2 * n)
    a = [x - mu for x in fa]
    b = [x - mu for x in fb]
    var = (sum(x * x for x in a) + sum(x * x for x in b)) / (2 * n - 1)
    return a, b, mu, var


def _sobol_pair(a: list[float], b: list[float], ab: list[float],
                var: float) -> tuple[float, float]:
    """(first-order, total-order) for one input, from centred vectors.

    S1 is Saltelli et al. (2010); ST is Jansen (1999). Both are the standard
    estimators and both are chosen for the same reason: they are differences
    between paired evaluations, so the shared part of the output cancels and
    what survives is the part the input actually moved. That matters here
    more than usual, because the shared part is essentially all of it.
    """
    if var <= 0.0:
        return 0.0, 0.0
    n = len(a)
    s1 = sum(b[k] * (ab[k] - a[k]) for k in range(n)) / n / var
    st = sum((a[k] - ab[k]) ** 2 for k in range(n)) / (2.0 * n) / var
    return s1, st


def _bootstrap_bands(
    fa: list[float],
    fb: list[float],
    fabs: list[list[float]],
    replicates: int,
    confidence_level: float,
    rng: random.Random,
) -> list[tuple[float, float, float, float]]:
    """Percentile bands on every index, by resampling the rows we already have.

    No extra model evaluations: a bootstrap replicate re-uses the same
    (A, B, AB) triples with rows drawn with replacement. One index set is
    drawn per replicate and shared across all inputs, which is both cheaper
    and more honest -- the inputs' indices are estimated from the same rows,
    so their errors are correlated and resampling them independently would
    understate that.

    The project publishes an interval on every figure it publishes. An index
    quoted bare would be the only number in scientific mode without one.
    """
    n = len(fa)
    n_in = len(fabs)
    if replicates <= 0 or n < 2:
        return [(0.0, 0.0, 0.0, 0.0)] * n_in

    firsts: list[list[float]] = [[] for _ in range(n_in)]
    totals: list[list[float]] = [[] for _ in range(n_in)]
    for _ in range(replicates):
        idx = [rng.randrange(n) for _ in range(n)]
        ra = [fa[k] for k in idx]
        rb = [fb[k] for k in idx]
        a, b, mu, var = _centre(ra, rb)
        for i in range(n_in):
            rab = [fabs[i][k] - mu for k in idx]
            s1, st = _sobol_pair(a, b, rab, var)
            firsts[i].append(s1)
            totals[i].append(st)

    tail = (1.0 - confidence_level) / 2.0
    out = []
    for i in range(n_in):
        f = sorted(firsts[i])
        t = sorted(totals[i])
        out.append((
            _percentile(f, tail), _percentile(f, 1.0 - tail),
            _percentile(t, tail), _percentile(t, 1.0 - tail),
        ))
    return out


def variance_decomposition(
    mixing_stages: list[MixingStage],
    param_bands: dict[str, tuple[str, float, float, float, str]],
    units_requested: int,
    units_per_individual: float,
    samples: int = 1024,
    seed: int | None = 12345,
    bootstrap: int = 200,
    confidence_level: float = 0.90,
    base_params: MixingParams | None = None,
) -> VarianceDecomposition:
    """Sobol first- and total-order indices for `distinct`, over mixing inputs.

    Every mixing input is varied simultaneously across its own corpus band --
    the pool size of each stage, plus the scalar parameters -- and the
    variance in the resulting `distinct` is attributed among them.

      first-order (S1)  the share this input would own if it were the only
                        thing uncertain.
      total-order (ST)  its share including every interaction it takes part
                        in. ST above S1 IS the interaction, and the gap is
                        the whole reason this is not a tornado.

    `param_bands` maps a `MixingParams` field name to
    (label, lo, mode, hi, confidence). Any field absent from it is held at
    `base_params` rather than defaulted, because `MixingParams()` is the
    inert configuration and silently swapping a corpus figure for zero would
    move the answer while looking like an omission.

    WHAT THIS WILL TELL YOU ON THE COMMODITY CASCADE, AND HOW TO READ IT
    -------------------------------------------------------------------
    The indices are scale-free ratios that sum to about one; they cannot all
    be near zero and it is a mistake to expect them to be. What is near zero
    is the VARIANCE: about 2e-5 of a chicken, on a mean of 11.99997. The
    cascade is saturated, the answer is pinned against its ceiling, and the
    shares merely divide a quantity that has already vanished. Read
    `sd` first and the bars second, or the chart says the opposite of what
    the numbers say.

    On a route that is not saturated -- `local_butcher` -- the same call
    returns a standard deviation of about 0.2 of a chicken and the shares
    become real research priorities. Same chart, opposite reading, and the
    `notes` say which case you are in rather than leaving you to guess.

    ONE ASSUMPTION WORTH DISTRUSTING
    --------------------------------
    Sobol indices in this form require the inputs to be independent, and
    these are probably not. `separation_efficiency` and
    `adjacency_retention_random` both describe how roughly the line treats
    two units of the same individual, and `cascade_retention` already
    multiplies them together. #77 established that this project does not
    silently assert zero correlation between loss stages; asserting it
    between mixing parameters is the same move, and it is recorded in
    `notes` rather than buried here. Correlated inputs need a different
    estimator (Kucherenko), which is a larger piece of work.
    """
    rng = random.Random(seed)
    base = base_params or MixingParams()
    pnames = sorted(param_bands)
    field_names = {f.name for f in fields(MixingParams)}

    # (label, kind, confidence, lo, mode, hi) per swept input, pools first.
    inputs: list[tuple[str, str, str, str, float, float, float]] = []
    for m in mixing_stages:
        lo, mode, hi = m.band()
        inputs.append((m.slug, m.label, "pool", m.confidence,
                       float(lo), float(mode), float(hi)))
    for name in pnames:
        label, lo, mode, hi, conf = param_bands[name]
        inputs.append((name, label, "parameter", conf,
                       float(lo), float(mode), float(hi)))

    dec = VarianceDecomposition(
        samples=samples, bootstrap=bootstrap, seed=seed,
        confidence_level=confidence_level,
    )
    n_in = len(inputs)
    if n_in == 0 or samples < 2:
        dec.notes.append("No mixing inputs to decompose.")
        return dec

    unknown = [p for p in pnames if p not in field_names]
    if unknown:
        dec.notes.append(
            f"Ignoring {len(unknown)} parameter(s) with no matching field on "
            f"MixingParams: {', '.join(unknown)}."
        )
    missing = sorted(field_names - set(pnames))
    if missing:
        dec.notes.append(
            f"{len(missing)} mixing parameter(s) were not swept and are held "
            f"fixed: {', '.join(missing)}. Their contribution to the spread "
            f"is therefore not measured rather than measured as zero."
        )

    n_pool = len(mixing_stages)

    def evaluate(u: list[float]) -> float:
        pools = [_triangular_ppf(u[i], inputs[i][4], inputs[i][5],
                                 inputs[i][6]) for i in range(n_pool)]
        kw = {}
        for j, name in enumerate(pnames):
            if name in field_names:
                col = inputs[n_pool + j]
                kw[name] = _triangular_ppf(u[n_pool + j], col[4], col[5],
                                           col[6])
        params = replace(base, **kw) if kw else base
        return draw_from_cascade(
            _jitter_pools(mixing_stages, pools),
            units_requested, units_per_individual, params,
        )[3]

    # Two independent sample matrices, and the n cross-matrices that take one
    # column from the other. Plain pseudo-random rather than a Sobol or Latin
    # hypercube sequence: those converge faster but break the i.i.d. rows the
    # bootstrap above depends on, and the model is cheap enough (about 20us a
    # call) that buying the error bar with extra samples is the better deal.
    mat_a = [[rng.random() for _ in range(n_in)] for _ in range(samples)]
    mat_b = [[rng.random() for _ in range(n_in)] for _ in range(samples)]
    fa = [evaluate(row) for row in mat_a]
    fb = [evaluate(row) for row in mat_b]

    fabs: list[list[float]] = []
    for i in range(n_in):
        col = []
        for k in range(samples):
            row = list(mat_a[k])
            row[i] = mat_b[k][i]
            col.append(evaluate(row))
        fabs.append(col)

    a, b, mu, var = _centre(fa, fb)
    bands = _bootstrap_bands(fa, fb, fabs, bootstrap, confidence_level, rng)

    for i, (slug, label, kind, conf, lo, mode, hi) in enumerate(inputs):
        s1, st = _sobol_pair(a, b, [x - mu for x in fabs[i]], var)
        degenerate = lo >= hi
        dec.shares.append(VarianceShare(
            slug=slug, label=label, kind=kind, confidence=conf,
            first_order=s1, total_order=st,
            first_lo=bands[i][0], first_hi=bands[i][1],
            total_lo=bands[i][2], total_hi=bands[i][3],
            degenerate=degenerate,
            # A non-degenerate input whose total-order index is EXACTLY zero
            # was not merely unimportant, it was never read: every AB
            # evaluation returned the A value bit-for-bit. `resolve_pool`
            # consults only the largest pool in the cascade and the pool at
            # the draw stage, so a middling stage can be recorded, sourced,
            # and structurally invisible. That is worth saying out loud
            # rather than rendering as a very short bar.
            inert=(not degenerate and st == 0.0 and s1 == 0.0),
        ))

    dec.mean = mu
    dec.variance = var
    dec.sd = sqrt(var) if var > 0 else 0.0
    dec.sample_lo = min(min(fa), min(fb))
    dec.sample_hi = max(max(fa), max(fb))
    dec.evaluations = samples * (n_in + 2)
    dec.sum_first_order = sum(s.first_order for s in dec.shares)
    dec.sum_total_order = sum(s.total_order for s in dec.shares)
    dec.shares.sort(key=lambda s: s.total_order, reverse=True)

    dec.notes.extend(_variance_notes(dec, mixing_stages, units_requested,
                                     units_per_individual))
    return dec


def _variance_notes(
    dec: VarianceDecomposition,
    mixing_stages: list[MixingStage],
    units_requested: int,
    units_per_individual: float,
) -> list[str]:
    """The findings, computed from the run rather than asserted about it.

    Each of these was a sentence someone would otherwise have written into
    the UI by hand and left there while the corpus moved underneath it.
    """
    notes: list[str] = []

    if mixing_stages:
        # The stream is the LARGEST pool, so its worst case -- the low end of
        # the largest band -- is the least-saturated cascade the corpus
        # admits. Same test `saturation_threshold` is already used for in
        # test_scientific.py, applied to the same quantity.
        worst_stream = max(s.band()[0] for s in mixing_stages)
        thresh = saturation_threshold(units_requested, units_per_individual)
        if worst_stream >= thresh:
            notes.append(
                f"Saturated: even the smallest pool this cascade's bands "
                f"admit ({worst_stream:,}) is above the saturation threshold "
                f"of {thresh:,}, so the answer is pinned against its ceiling "
                f"and there is almost no variance left for any input to own. "
                f"The shares say which input owns what little remains. They "
                f"do not say the answer is uncertain."
            )
        else:
            notes.append(
                f"Not saturated: the cascade's smallest admissible stream "
                f"({worst_stream:,}) is below the saturation threshold of "
                f"{thresh:,}, so the pool figures genuinely move the answer "
                f"and these shares are a research priority ranking."
            )

    n_inert = sum(1 for s in dec.shares if s.inert)
    if n_inert:
        notes.append(
            f"{n_inert} of {len(dec.shares)} inputs score exactly zero "
            f"because the model never reads them: `resolve_pool` uses only "
            f"the largest pool in the cascade and the pool at the draw "
            f"stage. The rest are recorded and cited, and structurally "
            f"invisible. That is a zero by construction, not a finding."
        )

    n_deg = sum(1 for s in dec.shares if s.degenerate)
    if n_deg:
        notes.append(
            f"{n_deg} input(s) have no band recorded at all (lo == hi), so "
            f"they have no uncertainty to propagate and score zero for that "
            f"reason rather than because they do not matter. On a chain with "
            f"a pool override this is usually the override collapsing the "
            f"band (#116), not the corpus lacking one."
        )

    notes.append(
        "These indices assume the inputs are independent, and they are "
        "probably not: separation efficiency and adjacency retention both "
        "describe how roughly the line treats two units of one individual, "
        "and the model already multiplies them together. Correlation would "
        "move share between inputs; it would not create variance that is "
        "not there."
    )
    return notes
