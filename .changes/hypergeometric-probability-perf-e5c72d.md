---
bump: third
---
### The hypergeometric miss probability no longer loops once per unit removed

`_ratio_choose` evaluated C(W-k, n)/C(W, n) as an explicit k-factor product
in a Python loop. For products asked at particle granularity — a ground beef
patty's mixing draw removes an individual animal's thousands of particles at
a time — that loop ran thousands of iterations, under two calls per
`expected_distinct_general`, under thousands of Monte Carlo resamples:
`tests/test_aggregate_units.py` alone was measured burning 30+ CPU-minutes,
all of it in this one function.

The ratio is now evaluated in closed form as a difference of log-gamma
terms when the loop would exceed 64 factors, which turns the pathological
call from 8.3 ms into 2.4 µs (~3,400x) and brings that test file from 30+
minutes to about 30 seconds. Below 64 factors the original loop is kept, so
every headline path — wings remove 1 or 2 units — is bit-for-bit unchanged.
Above it, the closed form agrees with the loop to within ~1e-8 relative
error (worst case measured across container sizes up to 3,000,000), orders
of magnitude below the model's own stated uncertainty. No published figure
moves.
