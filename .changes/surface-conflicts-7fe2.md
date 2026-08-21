---
bump: second
---
### Recorded disagreements are now a first-class part of the corpus

Where two sources give different figures for the same quantity and we have
chosen not to pick one, the disagreement is now stored as data rather than left
as prose in a source's notes. A new `Conflicts` view, a `/api/conflicts`
endpoint, a `wings conflicts` command and a `conflicts` export all surface the
same three disagreements the corpus already held silently: saffron yield per
acre (Penn State's ~3 lb/acre against UF/IFAS HS661's 8-10), Israel's
live-versus-carcass tonnage basis (CBS against the USDA PSD cross-check), and
beef carcass-to-packaged yield (Mississippi State against South Dakota State).
Neither figure in any of them is loaded into the model.

Sources kept on purpose now say why. A source cited by no loaded figure can
declare a `held_reason` (`corroboration` or `context`), and a source held as one
side of a conflict is cited by its position row, so the audit's "cited by
nothing" warning stops firing on deliberate decisions and goes back to meaning
"a figure was probably dropped and left its citation behind".
