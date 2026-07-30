# Batch 05b — asking in Hebrew: the result

**The hypothesis holds. Hebrew questions get figures out of Hebrew documents;
English questions do not.**

| | batch-05 | batch-05b |
|---|---|---|
| Questions | English | Hebrew |
| Documents | the same ten | six of the same ten |
| Retrieval | `nomic-embed-text` embeddings | **keyword overlap** (embedder down) |
| qwen2.5-coder:7b | 0/6 | 0/6 |
| gemma4-32k | 0/6 | **2/6** |
| Quote gate | — | **2/2 passed** |

Both figures came back with quotes that matched the source document
character-for-character, in Hebrew, and `verify` passed with the audit clean.

## What the two figures were

Exactly the ones the human read had already found — which is the point of using
a target with a known answer:

```
field: אפרוחים בשלוחות הרבייה
value: 244   unit: מיל' אפרוחים
quote: שלוחות הרבייה 78 244 מיל' אפרוחים 980 16.4%

field: מספר מגדלי פטמים וכמות התוצרת
value_lo: 515400   unit: טון
quote: "בשר פטמים\t604\t515,400 טון\t3,414\t57.3%"
```

So COOPER independently reproduced the manual extraction from the same
document it had already downloaded and failed to read a day earlier. Nothing
here changes the corpus — both figures were promoted by hand in v1.6.0 — but the
reproduction is what makes the finding trustworthy rather than anecdotal.

## The retrieval detail that strengthens the result

**The embedder was unavailable for this run** — `nomic-embed-text` did not
answer, and retrieval silently fell back to keyword overlap. So batch-05b won
with *worse* retrieval machinery than batch-05 had:

- English question + real embeddings → 0 figures
- Hebrew question + crude keyword overlap → 2 figures

That is a cleaner result than the one hoped for. If embeddings were the whole
story, the fallback should have made things worse. Instead, **matching the
question's language to the document's is what mattered**, and keyword overlap
between Hebrew and Hebrew beats semantic search across a language boundary.

It also means the multilingual-embedder change is **not** the next step. It may
still help, but it is no longer the diagnosis, and it should not be built on the
strength of this run.

## The negative control behaved

Item 3 asked for a bedikah rejection rate over four documents that provably
contain no `%` or `אחוז` at all. Both models returned nothing. No hallucinated
rate, so the gate was never tested on one — which is the right kind of
uninformative.

## What broke, and it was not the extraction

The first attempt at this batch **completed the extraction and then crashed**
printing the results: COOPER is Windows, its console is cp1252, and the item
names are Hebrew. `UnicodeEncodeError` after all the work, taking
`findings.yaml` with it. Fixed in `runner.py` by reconfiguring stdout and stderr
to UTF-8 at startup.

Worth stating as a general lesson: the pipeline had a **language bug in its
reporting layer, not just in its reading layer**, and the reporting one was
silent until the day something non-Latin reached it.

## What to do with this

1. **Write Hebrew-language items with Hebrew questions.** No code change needed.
   The same applies to any non-English source: match the question's language to
   the document's.
2. **Do not switch embedders on this evidence.** The fallback outperformed the
   embedder here; that experiment needs its own run with the embedder actually
   up.
3. **Check why `nomic-embed-text` was unavailable** before reading too much into
   any run's retrieval quality. A silent fallback that still produces answers is
   the kind of thing that makes two runs incomparable without anyone noticing.
4. **The bedikah rate remains unfound.** Consumer-facing certification pages
   explain the rules and never the rates; try responsa collections and
   slaughterhouse kashrut training material.
