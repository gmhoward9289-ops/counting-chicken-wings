### Product pickers sort alphabetically by source, then item

The prefixed names ("Chicken: Bone-in wing", "Silk: Dress") landed in a
list still ordered by internal slug, so sources arrived scattered — the
chicken entries sat at both ends of the dropdown. `list_products` now
orders by `display_name` (case-insensitive, after the existing
active-species-first split), so every picker groups its sources
alphabetically with the items ordered within each: Beef, then the three
Chicken products together, Maple, Saffron, Silk.
