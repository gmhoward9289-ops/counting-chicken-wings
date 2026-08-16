### Added Brazil

Brazil (BRA) joins the corpus as a fifth country, at `measured` grade on
both national head count and tonnage — the second country, after Canada,
where the primary statistical agency (IBGE, via its SIDRA REST API)
answers directly rather than needing a secondhand attaché report to stand
in. A real subnational breakdown covers 19 of Brazil's 27 states, with the
remaining 8 loaded as suppressed presence-without-volume rows, reconciling
to within about 1.1% of the national total on both head count and tonnage
independently.

A second, real, industry-grade national head count exists from ABPA
(Brazil's poultry trade body, citing federal-inspection-only slaughter)
and disagrees with IBGE's by about 17% — documented as an open conflict in
`docs/BRAZIL-PLAN.md` rather than silently dropped or averaged in, since
the schema allows only one head-count value per country per year. Also
loaded: national output value, export share, per-capita consumption, and
four learning-centre facts, all at the confidence grade their source
actually supports.

Declared `second` because a fifth country and a new state-level dataset
(19 Brazilian states, at `measured` grade) is new *capability* the corpus
diff should catch on its own, but the two-source conflict this branch
documents and resolves — which figure wins, and why — is exactly the kind
of judgment call `release_check.py` cannot see in a diff.
