---
bump: second
---
### The mixing simulator now works for every product, not just wings

`/api/mixing-curve` was pinned to `whole_wing` -- it took `draw` and
`units_per_individual` directly rather than a product slug, so the web
page's mixing simulator always showed a chicken-and-wings curve no matter
what the calculator itself was asking about. The endpoint now takes
`product` (and `count`, `window_days` for recurring products) the same way
`/api/calculate` and `/api/scientific` already do, and computes the curve
at the same granularity the headline answer uses for that product:
individual-shares for a blended unit like a gram of saffron, mixing
sub-units for a homogenate like a ground beef patty
(`beef-patty-mixing-granularity`'s fix), and the unit's own scale for
everything else. That re-expression used to be duplicated logic risk
waiting to happen -- it now lives once, in `model.mixing_draw_scale`, and
both `run()` and the curve endpoint call it.

The mixing simulator page gained a product selector (and a window control
for recurring products) so a reader can actually drag the pool for a dozen
eggs, a ground beef patty, a gram of saffron, or a gallon of maple syrup,
not only a dozen wings.

`bump: second` because this is a new capability at the API surface -- a
query parameter and a control the corpus diff cannot see -- not a change to
any published figure.
