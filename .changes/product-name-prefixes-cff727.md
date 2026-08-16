### Product pickers now lead with the source: "Chicken: Bone-in wing"

Every product dropdown mixes species, so a bare "Egg" or "Gram of dried
saffron" never said what was being counted. Each product now carries a
`display_name` in the taxonomy — "Chicken: Boneless wing", "Beef: Ground
beef 1/4-lb patty", "Silk: Dress", "Maple: Gallon of syrup" — and the
calculator, mixing-simulator, and impact pickers all show it. The bare
`label` is unchanged and still what prose composes mid-sentence ("a
boneless wing contains no wing meat"), which is exactly why the picker
name is a separate column rather than a rename. A test now requires every
active product to declare the prefixed form.
