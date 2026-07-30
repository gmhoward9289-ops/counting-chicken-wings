# batch-08-silk — human review record (NEGATIVE RESULT)

Run on COOPER 2026-07-30, twice. **`verify` FAILED both times and nothing was
accepted.** Recorded here anyway, in the batch-04-honey tradition: the run is
worth more as a bug report on the pipeline than it would have been as three
figures about neckties.

7 items asked, 5 figures returned, 2 items (`cocoons_per_worm`,
`cocoons_per_tie`) returned nothing at all.

## What this run exposed

### 1. HTML entities were never decoded — a false-negative that reads as fabrication

**Fixed this run.** `fetch_url()` stripped tags but never called
`html.unescape()`, so `&nbsp;` and `&#xE5D2;` survived into the inbox. The inbox
is what `verify` matches quotes against, so a model that read the prose
correctly and wrote it back as ordinary words produced a quote that could
**never** match.

It cost the batch's single best row. `reeling_cocoons_per_thread` came back at
**2/2 consensus** and was rejected as "quote does not appear in the document".
The document actually held:

```
...places it on a winding\n\nbobbin. &nbsp; Then a machine unrolls the cocoon...
```

The correlation is exact: `suekayton` carried **47** `&nbsp;` and produced the
failing quote; `newworldencyclopedia` carried **0** and its quotes verified.
After the fix, all three documents carry zero and that row passes.

This is the mirror image of the filename-collision bug in `08a4cf1` — same
organ, opposite sign. That one manufactured false confidence; this one
manufactured false guilt, and reads exactly like a model inventing a citation.

### 2. The scout confirmed a figure the pipeline cannot see

`cocoons_per_tie` returned nothing from both models, and **they were right to
decline.** The batch spec cites bows-n-ties for "a single tie requires about 120
to 130 cocoons" — a real sentence, confirmed 200 during scouting. COOPER's fetch
of that same URL contains the word "cocoon" but **no `120` and no `130`**; it
opens with `NEW: Summer Collection 2026 - SHOP HERE ... shopping_cart Cart`.
The scout's fetcher renders JavaScript. COOPER's does not.

So "confirmed 200 with the figure present" was confirmed with the *wrong tool*.
That check needs to be "present in what COOPER retrieves", not "present in what
a browser shows me" — which puts a question mark over any remaining unscouted
URL in batches 06 and 08 that leans on a JS-heavy commercial page.

### 3. The grounding rule is ANY-of-lo/mode/hi, and one bound can be junk

`cocoons_per_shirt` passed every check and is **wrong**. Its quote reads:

> It takes 1700 to 2000 cocoons to make one silk dress (or about 1,000 cocoons
> for a silk shirt).

The row stored `lo 1700 / mode 1800 / hi 2000` for a **shirt**. Those are the
*dress* numbers from the same sentence; the shirt figure is ~1,000. It grounds
because 1700 and 2000 do appear in the quote — the rule asks only that *any*
value appear, deliberately, so an interpolated mode is allowed.

The first run showed the same gap more starkly: `filament_length_per_cocoon`
stored `hi = 9000`, a number appearing in **no** silk document, riding along
beside a legitimate 1000 and 3000 from "300 to 900 meters (1000 to 3000 feet)" —
and it flipped the spec's unit from metres to feet while doing so.

A possible refinement, offered rather than applied, because it changes what the
gate accepts and that is not a machine's call: **`lo` and `hi` are bounds and
should each appear in the quote; only `mode` may be interpolated, and only
inside `[lo, hi]`.** That keeps saffron's legitimate "150 to 200 → mode 170" and
rejects both `hi = 9000` and the shirt row. Worth checking against the whole
accepted corpus before adopting.

Two-model disagreement did work here: qwen answered **1000** (correct) against
gemma's 1800, and the row was flagged. It was the flag, not the gate, that
caught it.

### 4. What the gate caught cleanly

Run two produced `cocoons_per_dress: estimate` — the model wrote its own
confidence grade into a value field. Rejected with an exact message. No notes.

## What was NOT the problem

**Chunking.** The going theory after maple was that 4 chunks across ~30k chars
was starving retrieval. It is not: at `CHUNK_CHARS = 12000` the silk documents
are 2 + 1 + 1 chunks, every item's own document was in front of the model, and
the figures that failed did so with the right text on screen. The maple REVIEW
carries the same correction.

## Recommendation

Do not promote any silk row. Before re-running: replace the bows-n-ties URL with
a source COOPER can actually read, and decide the `lo`/`hi` grounding question
above. The `reeling_cocoons_per_thread: 5` row is the only one that now both
verifies and appears correct, and one row does not make a subject.
