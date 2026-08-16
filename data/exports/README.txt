# (o>  counting chicken wings -- dataset index
# generated: 2026-08-16
# regenerate with: wings export
# --------------------------------------------

Every file has a .csv twin for spreadsheets and a .txt twin for
reading. Files are kept small and self-describing so any one of
them is usable on its own.

  facts               59 rows  chicken facts
  sources             63 rows  citations
  loss_chain          25 rows  loss chain
  mixing_cascade      30 rows  mixing cascade
  states              46 rows  average live weight by state
  states_census       50 rows  broiler presence by state, Census of Agriculture
  states_monthly     276 rows  average live weight by state and month
  national             2 rows  national slaughter totals
  husbandry           10 rows  grow-out performance by year
  quality_defects      6 rows  meat quality defects
  nutrition            3 rows  nutrition per 100g
  footprint            5 rows  resource footprint per bird
  economics            5 rows  economic measures
  producers            3 rows  producers

Numbers to read carefully:
  loss_chain      survive_* are SURVIVING fractions. applies_to
                  'mass' rows cannot change a unit count.
  footprint       per BIRD. Allocate by mass share before charging
                  to one cut.
  quality_defects degrade quality without removing product, so they
                  are not part of the loss chain.
  states          only states USDA's annual survey publishes
                  individually appear here; others are suppressed
                  for disclosure. states_census has all 50, from a
                  different, five-yearly programme -- do not merge
                  the two: sales_head is not head_slaughtered.
