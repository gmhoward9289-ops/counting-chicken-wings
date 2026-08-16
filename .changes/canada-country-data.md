---
bump: second
---
### Canada joins the corpus, and answers the question at `measured` grade

`GET /api/output/CAN` now answers the wing question for Canada, and answers
it the way no country other than the US has yet managed: Statistics Canada's
table 32-10-0118-01 publishes both head slaughtered — 806.0 million broilers
for 2025 — and meat output (1,416,554 tonnes, eviscerated weight), by
province, same year, same registered-plant survey, all at `measured` grade.
Five-year series for head count, tonnage and farm value (CAD) are loaded,
and the government-only view keeps Canada countable where it strips Israel's
industry-grade head figure. The table also isolates "Chicken" from "Fowl"
(spent laying hens), so the count is broilers, not a blended line.

The provincial breakdown is the opposite finding from Israel's: six named
provinces plus StatCan's Atlantic aggregate sum to *exactly* the national
total, for head count and tonnage alike — a partition of one survey, not two
surveys agreeing. The four Atlantic provinces are loaded individually as
suppressed rows (StatCan's own machine-readable `securityLevelCode`), the
same presence-without-volume pattern CBS and NASS use, and the aggregate
sits at `region_level='district'` so a reader counting provinces gets ten.
`output_stat_year.region_level` gained `'province'` for this, and the
country loader's `districts` block now accepts a list of blocks each naming
its own `measure` — Israel's single unlabelled block still defaults to
`marketed`, unchanged.

What did not ship, deliberately: no average *live* bird weight, because
StatCan's tonnage is eviscerated (per AAFC, twice over) while Chicken
Farmers of Canada's farm-size figures are live weight, and dividing across
bases would understate live weight by roughly a dressing percentage — the
derived 1.76 kg/bird view row is eviscerated-basis and labelled as such. No
standing flock, because a quota-set supply-managed system publishes no such
census — recorded as a structural absence, not a gap. `country.population`
stays `NULL`: AAFC's own 35.64 kg per-capita disappearance figure ships as
a dated fact instead, alongside facts on quota-set production and the
two-weight-bases trap. Full research trail in `docs/CANADA-PLAN.md` and
`docs/research/library/poultry-canada.yaml`, including FAOSTAT found
unreachable for the second country running.
