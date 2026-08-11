---
bump: second
---
### A pool override rescales its uncertainty band instead of collapsing it

`db.load_mixing_stages` clamped the rescale factor for any per-chain pool
override to a floor of 1.0, which is a no-op in exactly the case an override
exists for: making a pool *smaller* than the plant-scale default. A
40-bird butcher's tray reported `lo == mode == hi == 40` — no band at all —
instead of sampling a butcher-scale range.

Every overridden stage now rescales the default band proportionally, keeping
its shape rather than its absolute size:

| chain | stage | old band | new band |
|---|---|---|---|
| `local_butcher` | separation | 40–40–40 | 4–40–160 |
| `local_butcher` | restaurant_freezer | 40–40–40 | 6–40–200 |
| `farmers_market` | egg_collection | 500–500–500 | 25–500–2000 |
| `farmers_market` | egg_farm_cooler | 500–500–500 | 17–500–2000 |
| `backyard_eggs` | egg_collection | 6–6–6 | 1–6–24 |

The headline commodity-route figures are unaffected — those chains carry no
overrides. `local_butcher`'s and the two egg routes' reported intervals
widen; the point estimate (`pool`, and therefore the headline `distinct`
figure for that route) does not move.

`variance_decomposition` (#78) had been reporting these inputs as
`degenerate: true`, which made the collapse visible but was a mitigation, not
a fix — a degenerate input contributes no variance, so `local_butcher`'s
dominant Sobol share was inflated by every other overridden stage scoring
zero. Fixed, `separation` and `restaurant_freezer` both carry real variance
now and neither is degenerate.
