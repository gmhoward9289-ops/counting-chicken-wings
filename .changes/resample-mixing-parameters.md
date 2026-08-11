---
bump: second
---
### The Monte Carlo loop resamples the mixing parameters it has bands for

PR #96 moved separation efficiency, scoop size, and both adjacency-retention
parameters into the audited `model_parameter` table, each with a lo/mode/hi
band. The pool sizes beside them were resampled every iteration; these four
were held at the mode regardless of `iterations`, so the reported interval on
`distinct` reflected pool-size uncertainty only. Disclosed in `model.run`'s
docstring rather than hidden — filed as #98, fixed here.

`run(..., param_bands=db.load_mixing_param_bands(conn))` now resamples all
four independently each iteration, the same triangular-band sampling already
used for pools. Independently, not jointly: `separation_efficiency` and
`adjacency_retention_random` both describe line handling quality and are
probably correlated in reality, the same caveat `variance_decomposition`
already records about the same two inputs. A correlated estimator is a
larger piece of work than this fix; an uncorrelated resample is still
strictly more honest than not resampling at all.

Measured effect, `distinct_hi - distinct_lo` before/after across every named
supply chain:

| chain | before | after |
|---|---:|---:|
| commodity_foodservice | 0.00003 | 0.00006 |
| grocery_retail | 0.00003 | 0.00055 |
| commodity_spice | 0.00003 | 0.00345 |
| home_ground_beef | 0.00000 | 0.00000 |
| whole_bird_home | 0.00000 | 0.00000 |
| commercial_carton | 0.00055 | 0.01488 |
| commodity_syrup | 0.00030 | 0.14401 |
| commodity_ground_beef | 0.02962 | 0.78659 |
| commodity_silk | 0.00008 | 0.34011 |
| handreeled_silk | 0.00206 | 0.82321 |
| farmers_market | 0.08044 | 0.40631 |
| local_butcher | 0.61326 | 0.92321 |
| sugarhouse_direct | 0.15582 | 0.70913 |
| garden_saffron | 0.80441 | 1.79423 |
| backyard_eggs | 3.58378 | 3.52092 |

**This is not the negative result the issue considered likely.** The
saturated commodity routes barely move, as expected — pool-size uncertainty
already dominates them completely. Every other route widens, several
substantially, because the parameters carry real uncertainty the model had
been silently omitting on routes where they are not negligible next to the
pool. `backyard_eggs` narrowed marginally (3.58 to 3.52), within the noise of
a finite-sample Monte Carlo estimate at this pool size.

No change for any caller that does not pass `param_bands` — the CLI and API
call sites now do; nothing else changes behavior. The single deterministic
`distinct` figure returned at `iterations=0` is unaffected either way, since
it stays pinned at the mode regardless.
