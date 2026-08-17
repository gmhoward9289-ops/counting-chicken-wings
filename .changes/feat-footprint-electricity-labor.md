### What changed

Added an `electricity` metric (kWh, on-farm growout only) to the broiler
resource footprint, alongside the existing five ReCiPe impact categories.
The figure — 0.251 kWh grid electricity per broiler at 6.37 lb live weight,
0.0869 kWh per kg live weight — comes straight out of the *same*
already-cited source's own raw lifecycle inventory table
(`ncc-broiler-lca-2020`, Table 7), which reports it separately from the
`fossil_resources` (kg oil eq) proxy already in the corpus. It was never
transcribed into `resources.yaml` before now. Scoped explicitly to on-farm
growout — hatchery incubation and processing-plant/cold-chain electricity
are real additional draws this figure does not cover and are not currently
sourced anywhere in this project.

Looked for, and did not add, a labor-hours-per-bird or per-dozen-wings
figure distinct from the existing `direct_jobs` employment total. The two
candidates found were rejected rather than shipped: a 1955 USDA hand-line
processing study (70 years out of date for a "how many minutes did this
take" claim) and a derived BLS/USDA ratio that could not be verified
against a primary BLS document during this pass and mixes turkey/other
poultry into a chicken-only denominator. See the comment at the end of
`data/resources.yaml`'s economics block for the full accounting.
