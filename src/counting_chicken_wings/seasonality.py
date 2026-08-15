"""Does the answer change month to month?

The corpus has held twelve months of average live weight for every state NASS
names since the state work landed, and only the annual average was ever
surfaced. This module reads that series and says three things about it: how
big the swing is, when it peaks, and -- the part that matters -- whether the
swing is a season at all or just twelve noisy points.

That last question is why this is a module and not a SQL view. A range over
twelve numbers is trivial to compute and deeply misleading: Iowa's monthly
weights swing 13.6% and Iowa's peak is November, which is not a season, it is
one small state's plant mix moving around. Reporting the 13.6% without
reporting that it is noise would put a number on the page that the data does
not support, which is the failure this project exists to prevent.

Everything here is derived at call time from cited rows and never stored, for
the same reason `v_dressing_yield` and `v_output_derived_weight` are views: a
derived figure that is written down can drift from its parents.

STRUCTURAL LIMIT, STATED OUTRIGHT (#80): one year of twelve monthly points
cannot separate a season from a trend. Any twelve points are consistent with
infinitely many season/trend decompositions -- this is not a defect in the
three heuristics below, it is a fact about the data the corpus currently
holds. `_classify`'s verdict and `harmonic_regression`'s F-test are two
different lenses pointed at the same single, short, unreplicated series, not
two independent confirmations of each other. Both would improve, together,
the day the corpus holds a second year: with 3+ years the seasonal question
becomes genuinely identified and `harmonic_regression` stops being a second
lens on the same limitation and starts being a real test.

THE THREE HEURISTIC THRESHOLDS ASSUME AN IID NULL, AND A TIME SERIES IS NOT
IID. `NOISE_CEILING`, `PERSISTENCE_FLOOR`, and `TREND_WRAP_SHARE` are each
calibrated against twelve INDEPENDENT random draws (see the comments beside
each below). Monthly average bird weight is a smooth, persistent physical
quantity -- neighbouring months resemble each other more than twelve
independent draws would -- so the correct null has positive autocorrelation,
not none. An autocorrelated null produces smoother-looking noise, which is
closer to what these thresholds are trying to rule OUT, so calibrating
against iid noise makes the thresholds more permissive than they should be:
some swings that would fail a proper AR(1)-null test pass these. The
direction of the bias is known; its size is not, because quantifying it
needs a simulation this module does not yet run. Recorded here as a known
limitation rather than silently recalibrated, because a recalibration done
without validating it against the real corpus risks shipping a wrong number
with more apparent rigor than the number it replaced.
"""

from __future__ import annotations

import random
import statistics
from math import atan2, cos, pi, sin
from dataclasses import dataclass, field

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

# A clean twelve-point sinusoid -- the shape a real annual cycle has -- scores
# exactly 6.0 on `signal_ratio` below. Twelve independent random draws score
# 2.96 on average and stay under 4.0 in 95% of trials. So the thresholds are
# not taste: 4.0 is where noise stops explaining the swing, and 5.0 is close
# enough to the ideal cycle to say the word "seasonal" out loud.
#
# These constants are OURS, not a source's. Nothing in NASS says a swing must
# clear 4.0 to be real. `Seasonality.confidence` reports `estimate` for the
# classification even when the underlying weights are `measured`, because the
# weights are surveyed and the verdict about them is a judgement.
IDEAL_CYCLE_RATIO = 6.0
NOISE_CEILING = 4.0
CYCLE_FLOOR = 5.0

# `signal_ratio` alone is not enough, and Texas is why. A series that is flat
# for eleven months and dips once scores **exactly 6.0** -- the ideal-cycle
# score -- because its range is large and its jitter is two big steps averaged
# over twelve. Amplitude over jitter cannot tell a season from a single bad
# month, so on the first pass Texas was reported as the one seasonal state on
# the strength of one June.
#
# `persistence` is the second test: how much of the swing survives a
# three-month circular moving average. A real season is spread across
# neighbouring months and keeps 0.91 of its amplitude; a lone spike keeps
# 0.33, because smoothing is what a spike cannot survive. Twelve random draws
# keep 0.69 at the 95th percentile, so 0.75 clears both failure modes.
#
# A region must pass BOTH tests. One test that a wrong answer can satisfy is
# how this project ships plausible numbers with fictional reasoning.
IDEAL_CYCLE_PERSISTENCE = 0.911
SPIKE_PERSISTENCE = 0.333
PERSISTENCE_FLOOR = 0.75
WEAK_PERSISTENCE_FLOOR = 0.60

# And a third failure mode, which the first two both pass: a series that rises
# every month and starts over in January. That is the shape of a TREND -- and
# broiler weight does trend, roughly 1% a year on genetics and bird programs --
# not of a season, but it scores 6.0 on jitter and 0.9 on persistence.
#
# What gives it away is that the year does not close. `wrap_share` is the size
# of the December-to-January step as a fraction of all movement in the year: a
# sinusoid spends at most 0.13 of its movement there in any phase, twelve
# random draws 0.19 at the 95th percentile, and a ramp with a reset spends
# 0.50. A cycle comes back to where it started; a trend jumps back.
TREND_WRAP_SHARE = 0.30


@dataclass
class Seasonality:
    """One region's twelve months, and what can honestly be said about them."""

    region: str
    year: int
    unit: str
    # Index 0 is January. A month with no figure is None and is excluded from
    # every statistic rather than interpolated -- NASS suppresses months, and
    # a filled-in gap is a number we invented.
    values: list[float | None]

    months_present: int = 0
    lo: float = 0.0
    hi: float = 0.0
    mean: float = 0.0
    peak_month: int = 0
    trough_month: int = 0
    swing: float = 0.0
    swing_pct: float = 0.0
    jitter: float = 0.0
    signal_ratio: float = 0.0
    # Fraction of the swing that survives three-month smoothing. Separates a
    # season from one anomalous month; see the constants above.
    persistence: float = 0.0
    # Share of the year's total movement spent in the December-to-January
    # step. A high value means the year does not close: a trend, not a cycle.
    wrap_share: float = 0.0
    verdict: str = "insufficient"
    # Grade of the classification, never of the weights themselves.
    confidence: str = "estimate"
    explanation: str = ""
    source_slug: str | None = None
    notes: list[str] = field(default_factory=list)
    # A second, independent lens on the same twelve points (#80). Not a
    # second series -- see the module docstring on why this cannot be read
    # as independent confirmation of `verdict` above.
    harmonic: "HarmonicFit | None" = None

    @property
    def peak_month_name(self) -> str:
        return MONTH_NAMES[self.peak_month - 1] if self.peak_month else ""

    @property
    def trough_month_name(self) -> str:
        return MONTH_NAMES[self.trough_month - 1] if self.trough_month else ""

    @property
    def is_seasonal(self) -> bool:
        return self.verdict == "cycle"


def mean_absolute_step(values: list[float]) -> float:
    """Average month-to-month movement, wrapping December back to January.

    The wrap is deliberate. A series that climbs all year and drops off a
    cliff between December and January is a trend with a reset, not a cycle,
    and closing the loop is what makes the cliff count against it.
    """
    n = len(values)
    if n < 2:
        return 0.0
    steps = [abs(values[(i + 1) % n] - values[i]) for i in range(n)]
    return statistics.fmean(steps)


def smooth(values: list[float]) -> list[float]:
    """Three-month centred moving average, wrapping December to January."""
    n = len(values)
    return [
        (values[(i - 1) % n] + values[i] + values[(i + 1) % n]) / 3
        for i in range(n)
    ]


def wrap_share(values: list[float]) -> float:
    """How much of the year's movement is spent crossing December to January."""
    n = len(values)
    steps = [abs(values[(i + 1) % n] - values[i]) for i in range(n)]
    total = sum(steps)
    return steps[-1] / total if total else 0.0


# ---------------------------------------------------------------------------
# Harmonic regression (#80)
#
# The standard tool for exactly this question, run ALONGSIDE the three
# heuristics above rather than replacing them, so the two can be compared on
# the real corpus. Fits
#
#     y_t = a*sin(2*pi*t/12) + b*cos(2*pi*t/12) + c*t + d
#
# by ordinary least squares and tests the seasonal amplitude
# sqrt(a^2 + b^2) against a model with the sin/cos terms dropped (c*t + d
# only), via an F-test. Trend (c*t) and season (a, b) are separated by
# construction here, rather than by the wrap_share proxy above -- and no
# simulation-calibrated constant is needed, because the F-test's null
# distribution is exact.
#
# No numpy/scipy in this project's dependencies, so both the least-squares
# solve and the F-distribution tail are done by hand below rather than
# imported. Gaussian elimination for the first; for the second, the F(2, d2)
# survival function has a closed form because two seasonal parameters (a, b)
# means d1=2, and F(2, d2) reduces to Beta(d2/2, 1), whose CDF is elementary:
#
#     P(F >= f) = (1 + 2f/d2) ** (-d2/2)
# ---------------------------------------------------------------------------

def _solve_normal_equations(cols: list[list[float]], y: list[float]) -> list[float]:
    """OLS coefficients for y ~ cols, by Gaussian elimination on X'X.

    `cols` is the design matrix given column-major (one list per regressor),
    all the same length as `y`. No pivoting: every design matrix this module
    builds is a fixed, well-conditioned trigonometric/linear basis over 12
    equally-spaced points, never user-supplied, so a numerically pathological
    case cannot reach here.
    """
    k = len(cols)
    n = len(y)
    xtx = [[sum(cols[i][t] * cols[j][t] for t in range(n)) for j in range(k)]
           for i in range(k)]
    xty = [sum(cols[i][t] * y[t] for t in range(n)) for i in range(k)]

    # Augmented matrix, forward elimination, back substitution.
    aug = [row[:] + [xty[i]] for i, row in enumerate(xtx)]
    for col in range(k):
        pivot_row = max(range(col, k), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot = aug[col][col]
        for r in range(col + 1, k):
            factor = aug[r][col] / pivot
            for c in range(col, k + 1):
                aug[r][c] -= factor * aug[col][c]
    beta = [0.0] * k
    for r in range(k - 1, -1, -1):
        s = aug[r][k] - sum(aug[r][c] * beta[c] for c in range(r + 1, k))
        beta[r] = s / aug[r][r]
    return beta


def _residual_sum_of_squares(cols: list[list[float]], y: list[float],
                              beta: list[float]) -> float:
    n = len(y)
    fitted = [sum(cols[i][t] * beta[i] for i in range(len(cols)))
              for t in range(n)]
    return sum((y[t] - fitted[t]) ** 2 for t in range(n))


@dataclass
class HarmonicFit:
    """One region's year, read through harmonic regression instead of the
    three heuristics above. A second lens on the SAME single short series
    (see the module docstring), not independent confirmation of it."""

    amplitude: float = 0.0
    phase_month: float = 0.0
    p_value: float = 1.0
    ci_lo: float | None = None
    ci_hi: float | None = None
    confidence_level: float = 0.90
    bootstrap: int = 0
    seed: int | None = None
    notes: list[str] = field(default_factory=list)


def harmonic_regression(
    values: list[float | None],
    bootstrap: int = 0,
    seed: int | None = None,
    confidence_level: float = 0.90,
) -> HarmonicFit | None:
    """Fit y_t = a*sin(2*pi*t/12) + b*cos(2*pi*t/12) + c*t + d and test the
    seasonal amplitude sqrt(a^2 + b^2) against a trend-only null via an
    F-test.

    Returns None when fewer than 12 months are present -- the fit needs an
    equally-spaced annual cycle and a partial year is not one, the same
    restriction `_classify` applies to the three heuristics.

    `bootstrap > 0` adds a percentile confidence interval on the amplitude
    by residual resampling: refit `bootstrap` times against the fitted trend
    plus a with-replacement resample of the observed residuals, and report
    the `confidence_level` central interval of the resulting amplitudes.
    With `bootstrap=0` (the default) `ci_lo`/`ci_hi` stay `None` -- the point
    estimate and p-value do not need it and it is not free to compute.
    """
    present = [v for v in values if v is not None]
    if len(present) != 12:
        return HarmonicFit(notes=[
            f"Only {len(present)} of 12 months are published; harmonic "
            f"regression needs a complete, equally-spaced year."
        ])

    n = 12
    t = list(range(n))
    s_col = [sin(2 * pi * i / 12) for i in t]
    c_col = [cos(2 * pi * i / 12) for i in t]
    t_col = [float(i) for i in t]
    one_col = [1.0] * n

    full_cols = [s_col, c_col, t_col, one_col]
    trend_cols = [t_col, one_col]

    beta_full = _solve_normal_equations(full_cols, present)
    beta_trend = _solve_normal_equations(trend_cols, present)

    a, b = beta_full[0], beta_full[1]
    amplitude = (a * a + b * b) ** 0.5
    # atan2(a, b) because the fitted term is a*sin + b*cos; the peak of
    # A*sin(x + phi) form sits where the derivative is zero, which resolves
    # to this angle. Reported as a fractional month index for the caller to
    # round or interpret, not forced into a named month here.
    phase_month = (atan2(a, b) * 12 / (2 * pi)) % 12

    rss_full = _residual_sum_of_squares(full_cols, present, beta_full)
    rss_trend = _residual_sum_of_squares(trend_cols, present, beta_trend)

    df1, df2 = 2, n - 4
    if rss_full <= 0:
        p_value = 0.0
    else:
        f_stat = ((rss_trend - rss_full) / df1) / (rss_full / df2)
        f_stat = max(0.0, f_stat)
        # Closed form for d1=2 -- see the section docstring above.
        p_value = (1 + 2 * f_stat / df2) ** (-df2 / 2)

    fit = HarmonicFit(
        amplitude=amplitude, phase_month=phase_month, p_value=p_value,
        confidence_level=confidence_level, bootstrap=bootstrap, seed=seed,
    )

    if bootstrap > 0:
        rng = random.Random(seed)
        fitted_trend_season = [
            sum(full_cols[i][k] * beta_full[i] for i in range(4))
            for k in range(n)
        ]
        residuals = [present[k] - fitted_trend_season[k] for k in range(n)]
        amps = []
        for _ in range(bootstrap):
            resampled = [rng.choice(residuals) for _ in range(n)]
            y_star = [fitted_trend_season[k] + resampled[k] for k in range(n)]
            beta_star = _solve_normal_equations(full_cols, y_star)
            amps.append((beta_star[0] ** 2 + beta_star[1] ** 2) ** 0.5)
        amps.sort()
        tail = (1.0 - confidence_level) / 2.0
        lo_idx = max(0, min(len(amps) - 1, round(tail * (len(amps) - 1))))
        hi_idx = max(0, min(len(amps) - 1,
                             round((1.0 - tail) * (len(amps) - 1))))
        fit.ci_lo, fit.ci_hi = amps[lo_idx], amps[hi_idx]

    return fit


def _classify(
    ratio: float, persistence: float, wrap: float, months_present: int,
) -> tuple[str, str]:
    if months_present < 12:
        return (
            "insufficient",
            f"Only {months_present} of 12 months are published, so the shape "
            f"of the year cannot be read. The figures shown are real; the "
            f"pattern between them is not established.",
        )

    smooth_note = (
        f"{persistence:.0%} of the swing survives three-month smoothing, "
        f"against {IDEAL_CYCLE_PERSISTENCE:.0%} for a clean cycle and "
        f"{SPIKE_PERSISTENCE:.0%} for a single odd month."
    )

    if wrap >= TREND_WRAP_SHARE:
        return (
            "trend",
            f"{wrap:.0%} of the year's movement is spent in the single step "
            f"from December to January, against at most 13% for any phase of a "
            f"clean cycle. The series climbs or falls through the year and then "
            f"jumps back, which is a trend with a January reset rather than a "
            f"season. Broiler weight does trend -- about 1% a year on genetics "
            f"and bird programs -- and a trend read as a season would put the "
            f"peak in whichever month the year happens to end on.",
        )
    if ratio >= CYCLE_FLOOR and persistence >= PERSISTENCE_FLOOR:
        return (
            "cycle",
            f"The swing is {ratio:.1f}x the typical month-to-month movement, "
            f"against {IDEAL_CYCLE_RATIO:.0f}x for a clean annual cycle, and "
            f"{smooth_note} It rises and falls across neighbouring months "
            f"rather than jumping once, so calling this seasonal is supported.",
        )
    if ratio >= CYCLE_FLOOR:
        # Large range, low persistence: the shape of one anomalous month.
        return (
            "spike",
            f"The swing is {ratio:.1f}x the typical month-to-month movement, "
            f"which on that test alone would read as seasonal -- but only "
            f"{smooth_note} That is the signature of one unusual month in an "
            f"otherwise flat year, not of a season. The range is real; the "
            f"pattern is not.",
        )
    if ratio >= NOISE_CEILING and persistence >= WEAK_PERSISTENCE_FLOOR:
        return (
            "weak",
            f"The swing is {ratio:.1f}x the typical month-to-month movement. "
            f"That is above what random variation usually produces "
            f"({NOISE_CEILING:.0f}x) but short of a clean cycle "
            f"({IDEAL_CYCLE_RATIO:.0f}x), and {smooth_note} Suggestive, not "
            f"established.",
        )
    return (
        "noise",
        f"The swing is {ratio:.1f}x the typical month-to-month movement, and "
        f"twelve unrelated numbers score 3.0x on average. {smooth_note} The "
        f"range is real arithmetic on real figures and it is not a season.",
    )


def analyse(
    region: str,
    year: int,
    values: list[float | None],
    unit: str = "lb",
    source_slug: str | None = None,
    harmonic_bootstrap: int = 0,
    harmonic_seed: int | None = None,
) -> Seasonality:
    """Describe one region's year. `values` is twelve entries, January first.

    `harmonic_bootstrap` and `harmonic_seed` pass straight through to
    `harmonic_regression` for the confidence interval on the seasonal
    amplitude (#80). Default 0 skips the bootstrap -- the point estimate and
    p-value are always computed for a full year, but the interval is not
    free and most callers do not need it.
    """
    if len(values) != 12:
        raise ValueError(f"expected 12 monthly values, got {len(values)}")

    s = Seasonality(
        region=region, year=year, unit=unit, values=list(values),
        source_slug=source_slug,
    )
    present = [v for v in values if v is not None]
    s.months_present = len(present)
    if not present:
        s.verdict, s.explanation = _classify(0.0, 0.0, 0.0, 0)
        return s

    s.lo, s.hi = min(present), max(present)
    s.mean = statistics.fmean(present)
    s.swing = s.hi - s.lo
    s.swing_pct = 100.0 * s.swing / s.mean if s.mean else 0.0
    # Ties break toward the earlier month, which is arbitrary but stated, so
    # two callers never disagree about which month peaked.
    s.peak_month = values.index(s.hi) + 1
    s.trough_month = values.index(s.lo) + 1

    if s.months_present == 12:
        full = [v for v in values if v is not None]
        s.jitter = mean_absolute_step(full)
        s.signal_ratio = s.swing / s.jitter if s.jitter else 0.0
        sm = smooth(full)
        s.persistence = (max(sm) - min(sm)) / s.swing if s.swing else 0.0
        s.wrap_share = wrap_share(full)
        s.harmonic = harmonic_regression(
            full, bootstrap=harmonic_bootstrap, seed=harmonic_seed)
    s.verdict, s.explanation = _classify(
        s.signal_ratio, s.persistence, s.wrap_share, s.months_present)

    if s.verdict in ("noise", "spike", "trend"):
        s.notes.append(
            "Do not quote this region's swing as a seasonal figure."
        )
    if s.verdict == "spike":
        s.notes.append(
            f"The swing is carried by {MONTH_NAMES[s.trough_month - 1]} and "
            f"{MONTH_NAMES[s.peak_month - 1]} alone."
        )
    return s


def rank(series: list[Seasonality]) -> list[Seasonality]:
    """Order regions the way they should be read: signal first, size second.

    Sorting by swing alone puts the noisiest small states at the top, which is
    exactly the wrong impression.
    """
    order = {
        "cycle": 0, "weak": 1, "trend": 2, "spike": 3, "noise": 4,
        "insufficient": 5,
    }
    return sorted(series, key=lambda s: (order[s.verdict], -s.swing_pct))


@dataclass
class Concordance:
    """Do independent regions agree about when the year peaks?

    This exists because the per-region verdict turned out to be the wrong test.
    Not one state's weight series is a clean cycle and the national series is
    not either -- and yet 13 of 22 states peak in the same three months. A
    range statistic on one series cannot see that; agreement between series is
    a different and much stronger kind of evidence, and it is the same
    instinct as `tests/test_cross_validation.py`: two things that were not
    derived from each other, pointing the same way.
    """

    kind: str                      # "peak" or "trough"
    regions_counted: int = 0
    regions_excluded: int = 0      # Regions excluded due to incomplete data
    window: tuple[int, int, int] = (0, 0, 0)
    in_window: int = 0
    expected: float = 0.0
    p_value: float = 1.0
    p_corrected: float = 1.0
    verdict: str = "no agreement"
    confidence: str = "estimate"
    explanation: str = ""
    caveats: list[str] = field(default_factory=list)

    @property
    def window_names(self) -> list[str]:
        return [MONTH_NAMES[m - 1] for m in self.window]


def _binom_tail(n: int, k: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Exact, so no scipy dependency."""
    from math import comb
    return sum(
        comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1)
    )


def concordance(series: list[Seasonality], kind: str = "peak") -> Concordance:
    """Test whether regional peak (or trough) months cluster in one season.

    Pass the STATES only. A national row is the sum of its states and would be
    counted as a 23rd independent witness to its own evidence.

    Only full-year regions (months_present == 12) are used. Partial-year
    regions are excluded to ensure the null hypothesis (uniform distribution
    over 12 months) holds for all witnesses.
    """
    if kind not in ("peak", "trough"):
        raise ValueError("kind must be 'peak' or 'trough'")

    # Filter to full-year regions only, tracking exclusions
    full_year = [s for s in series if s.months_present == 12]
    excluded = len(series) - len(full_year)

    months = [
        (s.peak_month if kind == "peak" else s.trough_month)
        for s in full_year
        if (s.peak_month if kind == "peak" else s.trough_month)
    ]
    c = Concordance(kind=kind, regions_counted=len(months), regions_excluded=excluded)
    if len(months) < 4:
        c.explanation = (
            f"Only {len(months)} regions have a {kind} month, too few to test "
            f"agreement."
        )
        return c

    # Best three-month window, wrapping the year.
    windows = [((m, m % 12 + 1, (m + 1) % 12 + 1)) for m in range(1, 13)]
    best = max(windows, key=lambda w: sum(1 for m in months if m in w))
    c.window = best
    c.in_window = sum(1 for m in months if m in best)
    c.expected = len(months) * 3 / 12
    c.p_value = _binom_tail(len(months), c.in_window, 0.25)
    # The window was picked BY looking at the answer, and there are twelve of
    # them, so the raw p-value is optimistic by roughly that factor. Corrected
    # rather than quoted raw, because quoting the raw one would be the oldest
    # trick in the book.
    c.p_corrected = min(1.0, c.p_value * len(windows))

    if c.p_corrected < 0.01:
        c.verdict = "strong agreement"
    elif c.p_corrected < 0.05:
        c.verdict = "agreement"
    else:
        c.verdict = "no agreement"

    names = [MONTH_NAMES[m - 1] for m in best]
    c.explanation = (
        f"{c.in_window} of {len(months)} states {kind} in "
        f"{names[0]}-{names[2]}, where {c.expected:.1f} would be expected if "
        f"the {kind} month were random. That is p={c.p_corrected:.4f} after "
        f"correcting for having chosen the window from the data."
    )
    c.caveats = [
        "States are not fully independent witnesses: the same companies, "
        "genetics and bird programs operate across state lines, so some of "
        "the agreement is shared cause rather than shared season.",
        "The window was chosen from the data. The p-value shown is multiplied "
        "by the twelve windows that could have been chosen.",
        "This tests WHEN the year turns, not how much it moves. The movement "
        "is small: under 3% nationally.",
    ]
    if c.regions_excluded > 0:
        c.caveats.insert(
            0,
            f"{c.regions_excluded} region(s) with incomplete monthly data "
            f"(fewer than 12 months) were excluded from this test, because the "
            f"null hypothesis (uniform peak over 12 months) does not hold for "
            f"partial-year series.",
        )
    return c


def sparkline(values: list[float | None]) -> str:
    """Eight-level block sparkline, scaled to the series' own range.

    A gap prints as a space rather than a low bar, so a suppressed month never
    looks like a light month.
    """
    blocks = "▁▂▃▄▅▆▇█"
    present = [v for v in values if v is not None]
    if not present:
        return " " * len(values)
    lo, hi = min(present), max(present)
    span = hi - lo
    out = []
    for v in values:
        if v is None:
            out.append(" ")
        elif span == 0:
            out.append(blocks[0])
        else:
            idx = int(round((v - lo) / span * (len(blocks) - 1)))
            out.append(blocks[idx])
    return "".join(out)
