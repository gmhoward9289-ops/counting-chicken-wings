# batch-09-own-loss-factors — human review record

**Outcome: nothing accepted. One figure returned, it passed the gate, and it
was wrong by a factor of twenty.**

The most instructive run so far, and the clearest argument yet for why a human
reads every row.

## What came back

| | |
|---|---|
| Fetches | **8 of 8, zero failures** — the certifi fix held |
| Documents chunked | 8, into 31 chunks |
| qwen2.5-coder:7b | **0 of 8** calls returned a figure |
| gemma4-32k | **1 of 8** |
| Gate verdict | **PASSED** |
| Accepted | **nothing** |

The single figure:

```yaml
field: egg_kitchen_breakage
value_mode: 1.3
unit: percent of eggs lost at consumer level
quote: "Eggs, 5.1, 1.3%"
```

## Why the gate passed it, and why it is wrong

`1.3` appears verbatim in the document. The unit string mentions eggs and
percent, the field mentions eggs, and the document is the right one. Every
check we have said yes.

**It is a pie-chart label.** From EIB-121 Figure 3, *"Estimated total number of
calories of food loss in the United States per day by food group"*:

```
Eggs, 5.1, 1.3%
```

5.1 is **billion calories**. 1.3% is **eggs' share of all food-group calorie
loss** — grain products are 21.7% on the same chart. It is not a rate at which
eggs are lost. It is eggs' slice of a total that has nothing to do with eggs.

**The real figure was on the previous page**, in Table 5, whose header states
the columns explicitly:

```
Commodity   Food Supply | Retail level: cal, Percent | Consumer level: cal, Percent | Total
Eggs             15.5   |        1.1        7        |        4.0       26          | 5.1  33
```

So **eggs: 7% retail loss, 26% consumer loss, 33% total.** The extraction was
out by 20×, on the right page range, in the right document, with a real quote.

### The failure class this exposes

Not fabrication — the quote is real. Not misattribution in the saffron sense —
the subject genuinely is eggs. This is **a number stripped of the header that
gave it meaning**, and none of the four checks can see it:

| check | why it passes |
|---|---|
| quote-in-document | the string is verbatim |
| value-in-band | 1.3 is in the quote |
| unit-matches-field | "eggs"/"percent" appear in both |
| truncation | the fragment ends cleanly |

The spec predicted this shape — *"these are table cells, not sentences, expect
this item to need a human"* — and predicting it was not enough to stop it
passing. **A figure whose basis cannot be read off its own quote is not usable,
however well it verifies.** That is the source-verify rule, and it needs to
become a gate check or a standing instruction, not a note in one spec.

## The bug that made the run look like source scarcity

Three govinfo URLs in this batch share their first 47 characters. The document
filename was `slug[:48]`, so all three wrote to
`https-www-govinfo-gov-content-pkg-cfr-2024-title`:

```
CFR-2024-title9-vol2-part381.pdf     693,586 chars   <- overwritten
CFR-2024-title7-vol3-part70.pdf       79,871 chars   <- overwritten
CFR-2024-title9-vol2-sec381-90.pdf     3,954 chars   <- survived
```

**Two documents were downloaded, logged as `fetched + extracted`, and deleted
by the next fetch.** The 693 KB 9 CFR 381 text — the one carrying `tolerance`
×21 and `wings` ×8, the whole basis of item 2 — never reached the extractor.

So "0 of 8 figures" is partly an artifact of this, not a finding about the
sources. It is the worst shape a bug can take here, because the inbox is what
the gate checks quotes against: losing a document does not merely lose a
figure, it makes any quote from that document unverifiable.

Fixed by appending an 8-character hash of the full URL to the filename, with a
regression test that asserts three same-prefix URLs get three names.

## Also confirmed

**eCFR is bot-walled from COOPER.** It returned **1,502 characters** — a block
page — where the same URL gives 1.4 MB from a Mac. My own scouting verified it
from the Mac and listed it as usable, which was a real error on my part:
**a URL verified from one host is not verified for another.** The govinfo PDF
of the same regulation is the route that works from both.

## Where the four factors stand

| factor | status |
|---|---|
| `transport_doa` | **documented absence**, as predicted. FSIS 403s wholesale; "dead on arrival" is in none of the readable documents. |
| `grading_downgrade` | **unresolved, and untested** — its primary document was the one the filename collision destroyed. Worth one re-run now the bug is fixed. |
| `transit_rejection` | not returned. EIB-121 carries poultry at 4% retail / 18% consumer, but on a **calorie** basis and with no frozen-versus-fresh split. |
| `egg_kitchen_breakage` | **a real ERS figure now exists** — 7% retail, 26% consumer — but see below. |

### The egg figure is a human judgement, not a drop-in

Our placeholder is 1% loss. ERS says 26% at consumer level. That is not a
26× correction to make quietly, because **the two measure different things**:
ERS "consumer level" covers spoilage, plate waste, and everything after
purchase, while `egg_kitchen_breakage` is specifically *cracked in the carton
before use, plus shells dropped in cooking*. The corpus also already has
`egg_checks` at grading, and plate waste is a separate stage elsewhere.

So 26% is a **ceiling** on our stage, not our stage. Adopting it wholesale
would double-count against stages we already have. The honest options are to
split the ERS figure across the stages it actually spans, or to record it as a
bound and say so — and that decision belongs to a person.

Note too that Table 5 is in calories. LAFA applies one loss assumption per
commodity, so the percentage carries across bases — fluid milk reads 12%/20%
here and 12%/20% in the quantity series — but that equivalence should be
confirmed against the quantity table before the figure ships.

## What this batch cost and bought

Two runs of honey and one of this have produced **zero accepted figures**. What
they have produced: the non-numeric gate hole, COOPER's missing CA bundle, the
API ceiling bug, the filename collision, and now a named failure class the gate
cannot yet catch. The pipeline is getting more trustworthy while shipping
nothing, which is the right order.
