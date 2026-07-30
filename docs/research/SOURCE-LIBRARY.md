# Building a source library

## The problem this solves

COOPER is not the bottleneck. Measured 2026-07-29 while a batch ran: GPU at
**9%**, 2.8 GB of 8 GB, fetch finishing in seconds. The RTX 2060 is idle almost
all the time.

The bottleneck is **spec authoring**, and specifically the one step COOPER
cannot do: deciding which sources are authoritative and framing questions that
are extractable from them. Two of the three batches written so far
(`batch-02-vanilla`, `batch-03-wagyu`) were planning documents with the Items
section never filled, so neither could run at all. Vanilla sat unrunnable until
a single search pass produced six items with four verified URLs — after which
COOPER started immediately.

That step recurs for **every** subject. A library makes it cumulative instead.

## Why not just let COOPER search

Because "this website is authoritative" is a judgement about provenance, and
provenance is the entire product. `docs/research/README.md` already routes
around this deliberately: COOPER may not add to `data/sources.yaml`, and may not
assign `measured` or `derived`. Letting it choose its own sources would hand it
the decision the whole design exists to keep away from it.

There is also a blunter reason. COOPER fetches exactly the URLs listed and does
not search, so a plausible-looking invented URL fetches nothing and the batch
returns empty **for a reason nobody can see**. A guessed
`extension.psu.edu/vanilla` returned 404 during the vanilla pass. Had it been
written in unverified, the failure would have looked like "no data exists".

## What a library entry is

Not a bookmark. A bookmark tells you a page exists; it does not tell you whether
a figure is in it. Entries record **coverage**, because that is what the vanilla
pass actually produced and what saved time:

> The World Bank vanilla guide is strong on pollination and field yields — 43
> and 48 keyword hits across 4,433 lines — but mentions "cured" exactly **once**,
> so it cannot answer the curing ratio. The Package of Practice PDF is 136 lines
> and carries that ratio verbatim.

Two documents, opposite shapes, and knowing which is which is the difference
between a batch that works and one that half-fails. Proposed shape, as YAML in
`docs/research/library/<domain>.yaml`:

```yaml
- url: https://...
  title: Guide on sustainable vanilla cultivation
  publisher: World Bank
  kind: institutional        # government | academic | extension | institutional
                             # | trade_body | trade_press | commercial
  verified_on: '2026-07-29'
  http_status: 200
  content_type: application/pdf
  text_lines: 4433           # after pdftotext; a proxy for how much is there
  subjects: [vanilla]
  covers:                    # what it can actually answer
    - pollination
    - field_yield_per_hectare
    - plant_level_yield
  does_not_cover:            # measured, not assumed -- the expensive half
    - green_to_cured_ratio   # "cured" appears once in 4,433 lines
  confidence_ceiling: industry
  notes: >-
    Institutional rather than peer-reviewed, so `industry` is the ceiling. Rich
    on Madagascar field economics.
```

The `does_not_cover` field is the one that earns its keep. Recording an absence
stops the next batch pointing an item at a source that cannot answer it, which
is the failure that looks like missing data.

## How entries get created

A byproduct of batch authoring, not a separate project. The vanilla pass already
did every step; it just threw the results away afterwards.

1. **Search** — frontier model, since it is a judgement call.
2. **Verify** — `curl` every URL. Record status, content type, size. Non-200 is
   discarded, never left in looking plausible.
3. **Probe coverage** — fetch, `pdftotext`, keyword-count the figures the batch
   needs. Cheap, and it is what tells you the World Bank guide cannot answer a
   curing question.
4. **Write the entry**, including what it does *not* cover.
5. **Author the items** against entries rather than against a fresh search.

Steps 2 and 3 are mechanical and scriptable — a `tools/verify_sources.py` that
takes a list of URLs and emits candidate library YAML would remove most of the
manual work. Step 1 stays human-judged.

## Reuse is the point

Sources cross subjects, and the second use is free:

- Land-grant extension services (UF/IFAS, Penn State, UC ANR) cover many crops
  and already appear in both saffron and vanilla
- FAO and World Bank cover many commodities
- USDA NASS is the poultry backbone and reaches other livestock
- PMC carries peer-reviewed work across every biological subject

A library also makes the corpus's **evidence profile** visible. Right now 8 of
14 loss factors are unsourced estimates, and the reason is not laziness — it is
that no source was ever found. A library turns that into a queryable gap list:
"which subjects have no `government` or `academic` source at all" is exactly the
question that should drive the next search pass.

## Failure modes to design against

**Staleness.** A URL that resolved in July may 404 in December, and a dead link
in a spec produces a silently empty batch. `verified_on` plus a re-check job is
the answer; treat an entry older than ~6 months as unverified.

**Coverage rot.** Publishers reorganise. A page that had the figure may lose it.
Re-probe on re-verify, do not just check the status code.

**Ceiling inflation.** An entry claiming `government` for something
institutional quietly launders credibility into every figure citing it. Set the
ceiling from the publisher, once, and treat raising it as the human-only
decision it already is.

**Becoming a bookmark pile.** The value is in `covers` / `does_not_cover`. An
entry without them is worse than nothing, because it invites pointing an item at
a source nobody checked.

## What this would have saved

Vanilla needed: a search pass, five URL verifications (one 404), two PDF
downloads, and two coverage probes — to produce six items. Wagyu needs the same
work from scratch today. With a library, wagyu inherits USDA and FAO entries
already verified for poultry and only needs the beef-specific gaps.

## Recommendation

Do not build this as a standalone project. Build it as **the output of the next
batch you author**:

1. Write `batch-03-wagyu` items the way vanilla was written.
2. Instead of discarding the verification work, write it to
   `docs/research/library/red_meat.yaml`.
3. Add `tools/verify_sources.py` for steps 2 and 3 once the format has survived
   two subjects, not before.

That way the library is populated by work already being done, and its format is
shaped by two real subjects rather than by a guess.
