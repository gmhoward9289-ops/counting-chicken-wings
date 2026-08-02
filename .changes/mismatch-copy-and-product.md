---
bump: second
---
### One product for the whole page, and the refusal sentence comes from the API

Two follow-ups to the scope markers in v1.15.x.

**The calculator and Nutrition & impact each held their own product.** Neither
knew about the other, so setting Nutrition to a silk product and walking to
Trends produced a scope marker citing whatever the *calculator* still had —
right about the view and wrong about the question. It also contradicted the
strapline, which says the page re-scopes itself to whatever you ask it about.

There is one selection now. Changing either control carries the other with it,
re-derives the calculator's supply chain and window for the new species, and
recomputes whichever of the two views has been built. Nutrition & impact also
opens on the page's current product rather than resetting the question to wings.

**The mismatch sentence is composed by the API, not by the page.** `GET
/api/scope?product=<slug>` returns one pre-composed refusal per species:

> Gallon of maple syrup is a Sugar maple product, and nothing measured on
> Broiler chicken is its to borrow.

Keyed by species, so switching tabs costs no request. #110's constraint is that
scope copy is either app copy or comes from the API — the second is the better
one, because every noun in it is the corpus' own and renaming a species renames
the sentence. The pattern is the one `/api/footprint.allocation_note` already
established for the same situation one panel down; reusing that *string* is not
possible, because it is written with panel-relative deixis ("there is nothing
*here* to allocate", "the economic figures *below*") that does not survive being
hoisted to the tab level.
