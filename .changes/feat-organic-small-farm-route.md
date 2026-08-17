---
bump: third
---
### Added an organic / small farm supply-chain route

New `organic_small_farm` supply chain (dropdown label "Organic / small
farm") for wings from a small, often-organic farm that processes on-site or
via a rented Mobile Poultry Processing Unit and sells direct to the
consumer — no grading, no freezer tunnel, no distributor, the same shape as
the existing local butcher route.

The batch size is sourced rather than estimated: NCAT/ATTRA's *Small-Scale
Poultry Processing* bulletin puts on-farm processing capacity at 50-100
birds per day, run 1-30 days a year, so `pool_override: 75` (the midpoint)
replaces a guess with a documented figure. Loss stages reuse the species
defaults, the same choice `local_butcher` already makes, because no sourced
figure exists that is both route-specific and expressible in this model's
species/product-scoped loss-factor schema — including a real, sourced
finding that small/manual processing is *harder* on wings than a
mechanized line (16-30% of birds needing cut-up for bruises and broken
bones at small plants, against the corpus's existing ~5.7% commodity
wing-damage rate), which is documented in prose rather than converted into
an unsourced number.

Organic certification (a USDA National Organic Program inputs/feed/land
standard) and small-scale processing (a throughput fact) are different
axes, and research turned up no source giving a genuinely different
pool or loss profile for the certified-organic subset — so this ships as
one route representing the realistic common case rather than two routes
modeling axes nothing here can distinguish.

Two new sources: `ncat-attra-small-scale-poultry-processing` (batch sizes,
the 16-30% cut-up figure) and `cornell-small-farms-1000-bird-exemption`
(the federal PPIA 1,000-bird producer/grower exemption, cited for context
on why this route skips grading/freezer/distributor).
