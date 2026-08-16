---
bump: major
---
### A ground beef patty's headline answer no longer treats it as one wing

`ground_beef_patty` previously reported "at least 1 animal, ceiling 1" for a
single quarter-pound patty — a floor that is arithmetically true and was being
read, in front of a scientific audience, as the model's actual claim. The
mixing draw was expressing a patty as one indivisible unit (the same
assumption that is correct for a wing, which really is one intact piece from
one bird), when a patty is a scoop of a slurry already blended, at the
grinder, from every animal in that shift's combo bins. The corpus's own
best-sourced figure — Hu et al. 2012's DNA-measured grind-batch pool of
411-1,367 animals — was one file away and never reached the patty answer.

`product.mixing_subunits_per_unit` re-expresses the mixing draw at the
grinder's actual granularity instead of the unit's. Applied to
`ground_beef_patty` with an `estimate`-grade particle count derived from
commercial grind-plate hole sizes, a single patty now reports roughly 600
distinct animals, bounded by the batch pool rather than by "how many patties
you asked for." Every other product is unaffected — the new column is `NULL`
by default, and the draw stays exactly as before wherever it is unset. Wings,
eggs, saffron, silk, and maple were independently re-audited and none share
the failure mode: each has an anatomically atomic unit for which "1 unit = 1
draw" is physically correct.

`bump: major` because this changes the meaning of an already-published
headline figure, which `tools/release_check.py`'s corpus diff cannot detect on
its own.
