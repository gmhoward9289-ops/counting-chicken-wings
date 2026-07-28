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
from dataclasses import dataclass, field
from math import comb


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

def _ratio_choose(total: int, removed: int, drawn: int) -> float:
    """C(total-removed, drawn) / C(total, drawn), computed without big ints.

    Equals prod_{i=0}^{removed-1} (total-drawn-i) / (total-i), which is the
    probability that none of a specific individual's `removed` units are in
    a draw of `drawn` from `total`.
    """
    if drawn > total:
        raise ValueError("cannot draw more units than the container holds")
    r = 1.0
    for i in range(removed):
        denom = total - i
        if denom <= 0:
            return 0.0
        r *= (total - drawn - i) / denom
        if r <= 0.0:
            return 0.0
    return r


def expected_distinct_general(
    drawn: int,
    container_units: int,
    distinct_in_container: float,
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

    e = n_lo * (1.0 - _ratio_choose(container_units, lo, drawn))
    if n_hi > 0:
        e += n_hi * (1.0 - _ratio_choose(container_units, lo + 1, drawn))
    return min(e, float(drawn))


def expected_distinct(
    drawn: int,
    container_units: int,
    paired_individuals: float,
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

    miss_two = _ratio_choose(container_units, 2, drawn)
    miss_one = _ratio_choose(container_units, 1, drawn)

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


# How thoroughly a 'separating' stage pulls an individual's two units apart.
# Size grading routes a bird's wings to different boxes whenever they
# straddle a grade boundary, which is most of the time but not all of it.
SEPARATION_EFFICIENCY = 0.90


def resolve_pool(
    stages: list[MixingStage],
    units_requested: int,
    units_per_individual: float,
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
    """
    notes: list[str] = []
    upi = units_per_individual

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
    share = min(1.0, container / (stream * upi))
    distinct = stream * (1.0 - (1.0 - share) ** upi)

    # A separating stage routes an individual's units into different
    # streams, so more individuals are represented by fewer units each --
    # which pushes distinct up toward the container size.
    for s in stages:
        if s.mixing_kind != "separating":
            continue
        distinct += (container - distinct) * SEPARATION_EFFICIENCY
        notes.append(
            f"{s.label} actively separates an individual's units, so "
            f"{SEPARATION_EFFICIENCY:.0%} of the units that would have "
            f"shared a source are split apart."
        )

    distinct = max(container / upi, min(distinct, float(container)))

    per = container / distinct
    notes.append(
        f"Largest commingled pool is {stream:,} individuals; the container "
        f"drawn from holds about {container:,} units representing roughly "
        f"{distinct:,.0f} individuals, or {per:.3f} units each."
    )
    return container, distinct, notes


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
) -> tuple[float, list[StepTrace]]:
    """Walk the loss chain backwards from delivered units to individuals.

    Each surviving fraction divides, because we are running the pipeline in
    reverse: to end up with 12 wings after a stage that loses 5.7%, more
    than 12 had to enter it.
    """
    picks = picks or {}
    trace: list[StepTrace] = []
    seq = 0

    floor = floor_individuals(units_requested, units_per_individual)
    trace.append(StepTrace(
        sequence=seq,
        kind="floor",
        stage_slug="floor",
        stage_label="Anatomical floor",
        value_used=units_per_individual,
        running_total=floor,
        explanation=(
            f"{units_requested:g} units at {units_per_individual:g} per "
            f"individual is a hard minimum of {floor:g}. No loss anywhere "
            f"in the chain can push this number down."
        ),
        confidence="measured",
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
    trace: list[StepTrace] = field(default_factory=list)
    mixing_notes: list[str] = field(default_factory=list)
    iterations: int = 0
    # The interval actually reported, e.g. 0.90 for a 5th-95th percentile
    # band. Recorded on the result so a chart can never mislabel its axis.
    confidence_level: float = 0.90
    # Raw Monte Carlo draws, kept for histograms. Empty unless requested.
    required_samples: list[float] = field(default_factory=list)
    distinct_samples: list[float] = field(default_factory=list)
    excluded_stages: list[str] = field(default_factory=list)


def _triangular(lo: float, mode: float, hi: float, rng: random.Random) -> float:
    if lo == hi:
        return mode
    return rng.triangular(lo, hi, mode)


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
) -> Result:
    """Compute floor, required, and distinct for one question.

    With iterations > 0 both the loss chain AND the mixing pool sizes are
    resampled from their triangular lo/mode/hi bands, so the reported
    interval reflects the recorded uncertainty of the inputs rather than
    being asserted. `confidence_level` sets the interval width -- 0.90 gives
    a 5th-95th percentile band, 0.99 gives 0.5th-99.5th.

    `min_confidence` drops loss stages whose evidence grade is weaker than
    the given level, which answers "what does the answer look like using
    only figures we could actually source?".
    """
    excluded = [s.slug for s in loss_stages
                if not meets_confidence(s.confidence, min_confidence)]
    if excluded:
        loss_stages = [s for s in loss_stages
                       if meets_confidence(s.confidence, min_confidence)]

    floor = floor_individuals(units_requested, units_per_individual)
    required, trace = required_individuals(
        units_requested, units_per_individual, loss_stages
    )

    container, distinct_in_container, notes = resolve_pool(
        mixing_stages, units_requested, units_per_individual
    )
    distinct = expected_distinct_general(
        int(units_requested), container, distinct_in_container
    )

    trace.append(StepTrace(
        sequence=len(trace),
        kind="mixing",
        stage_slug="mixing_cascade",
        stage_label="Mixing cascade",
        value_used=distinct_in_container,
        running_total=distinct,
        explanation=(
            f"Drawing {units_requested} units from a container of "
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
        trace=trace,
        mixing_notes=notes,
        confidence_level=confidence_level,
        excluded_stages=excluded,
    )
    res.required_lo = res.required_hi = required
    res.distinct_lo = res.distinct_hi = distinct

    if iterations > 0:
        rng = random.Random(seed)
        req_s: list[float] = []
        dist_s: list[float] = []

        for _ in range(iterations):
            picks = {
                s.slug: _triangular(s.survive_lo, s.survive_mode,
                                    s.survive_hi, rng)
                for s in loss_stages
            }
            r, _ = required_individuals(
                units_requested, units_per_individual, loss_stages, picks
            )
            req_s.append(r)

            # Resample the mixing cascade too. Pool sizes are among the
            # softest numbers in the model, so holding them fixed would
            # understate the spread on the headline figure.
            if mixing_stages:
                jittered = []
                for m in mixing_stages:
                    lo, mode, hi = m.band()
                    p = max(1, int(_triangular(lo, mode, hi, rng)))
                    jittered.append(MixingStage(
                        slug=m.slug, label=m.label, pool=p,
                        mixing_kind=m.mixing_kind,
                    ))
                c, d, _ = resolve_pool(
                    jittered, units_requested, units_per_individual
                )
            else:
                c, d, _ = resolve_pool(
                    [], units_requested, units_per_individual
                )
            dist_s.append(
                expected_distinct_general(int(units_requested), c, d)
            )

        req_s.sort()
        dist_s.sort()
        tail = (1.0 - confidence_level) / 2.0

        res.iterations = iterations
        res.required = sum(req_s) / len(req_s)
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
