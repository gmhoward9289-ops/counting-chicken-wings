---
bump: third
---
### Seasonality states its identification limit outright, and adds harmonic regression alongside the three heuristics

`seasonality.py` was aware in spirit that one year of twelve monthly points
cannot separate a season from a trend — the `wrap_share` proxy exists
precisely because of it — but the module never said so in those words, and
`NOISE_CEILING`/`PERSISTENCE_FLOOR`/`TREND_WRAP_SHARE` are all calibrated
against twelve *independent* random draws, which is the wrong null for a
smooth, persistent physical series. Filed as #80.

**The limit is now stated explicitly**, in the module docstring and as a new
top-level `identification_limit` field on `/api/seasonality`: any twelve
points are consistent with infinitely many season/trend decompositions, and
this becomes a genuinely identified question only with 3+ years of monthly
data, which the corpus does not yet hold.

**Harmonic regression is added alongside the three existing heuristics, not
replacing them.** `seasonality.harmonic_regression` fits
`y_t = a*sin(2*pi*t/12) + b*cos(2*pi*t/12) + c*t + d` by ordinary least
squares (Gaussian elimination, no numpy dependency) and tests the seasonal
amplitude `sqrt(a^2 + b^2)` against a trend-only null via an exact F-test —
no scipy either: `F(2, d2)` reduces to `Beta(d2/2, 1)`, whose CDF is
elementary, so the p-value is closed-form. Every `Seasonality` for a
complete year now carries a `harmonic` field (amplitude, phase month,
p-value, and an optional bootstrap confidence interval on the amplitude),
exposed at `/api/seasonality` per-region and nationally.

Trend and season are separated by construction here, unlike `wrap_share`'s
proxy, and the test needs no simulation-calibrated constant. It is still a
second lens on the *same* single short series, not independent confirmation
— the module docstring and the new `identification_limit` field say so, so
a caller cannot read agreement between `verdict` and a low `harmonic.p_value`
as two pieces of evidence when it is one.

**The iid-null calibration issue is documented as a known limitation, not
silently recalibrated.** The three heuristic thresholds are permissive by an
unknown factor because their null assumes independence and a time series has
none; quantifying the size of that bias needs a validated AR(1)-null
simulation this module does not yet run, and shipping a recalibration
without validating it against the real corpus risks a wrong number with more
apparent rigor than the one it replaced. Recorded in the module docstring as
an open item rather than guessed at.

No published headline count moves — `verdict.affects_count` is still
`false`, unchanged. New endpoint fields only.
