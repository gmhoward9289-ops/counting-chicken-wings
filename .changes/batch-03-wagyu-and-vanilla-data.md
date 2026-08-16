### Vanilla and wagyu research lands in the corpus

The accepted findings of batch-02-vanilla and batch-03-wagyu (both rounds)
move from review documents into `data/`:

- **Vanilla** gets a species row (*Vanilla planifolia*, horticulture) and a
  curing loss stage: about 6 kg of green pods per kg of cured beans, a
  mass-basis stage that cannot move a count. No product row yet — no source
  states a per-vine yield as a numeral, and the schema refuses a product
  without one.
- **Wagyu** husbandry and yield statistics populate `economic_stat` for a
  second domain for the first time: the 30-month finishing period, the
  Japanese Black carcass yield (62.96% of live weight, computed from
  Gotoh's 756/476 kg weights), the generic US fed-cattle dressing range
  (60–64%) as the comparison figure, SDSU's 65%-of-carcass saleable-meat
  worked example, and the USDA Yield Grade %CTBRC range (45.4–52.3%).
  Three "how much beef" figures, three different denominators, deliberately
  never averaged.
- **Two livestock facts** explain Japan's beef grading: "A5" is two grades
  (yield letter, quality number), and BMS 8 of 12 is the floor of the
  quality 5 that A5 requires. Facts can now carry a `domain:`; everything
  existing defaults to poultry, untouched.
- Four sources added (MSU beef-grades fact sheet, beefresearch.org's USDA
  grading table, Lone Mountain's carcass-grading guide, Gotoh et al. 2018);
  every figure above cites one and passes the audit.
