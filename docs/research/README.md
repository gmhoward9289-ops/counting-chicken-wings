# Research batches

Work-orders for COOPER's local models to execute, and the contract that makes
their output safe to accept into a corpus whose entire value is that **every
number traces to a real source**.

## Why this exists

`audit.py` fails the build if a statistic cites a source that does not exist.
That guard is what makes machine-extracted data safe to accept at all — and it
is the reason a 7B model can be trusted with this work despite being far weaker
than a frontier model. It is not trusted. It is *checked*.

COOPER is free and idle. Frontier tokens are not. So COOPER does everything it
is capable of, and paid attention is spent only on the two things it cannot do.

## What to call this, and what not to call it

**This is machine extraction against human-chosen sources, verified verbatim.
It is not "research done by an AI", and describing it that way is wrong in both
directions at once.**

It overstates COOPER, which does not search. It fetches exactly the URLs a spec
hands it and reads them; an invented URL fetches nothing and the batch comes
back empty for a reason the model cannot report. Deciding a source is
authoritative, and probing whether it actually contains the figure being asked
for, is the work — and it is the step the division of labour below assigns to a
human precisely because a model cannot do it. The World Bank vanilla guide is
strong on yields and says "cured" once in 4,433 lines; nothing in COOPER can
notice that before a batch half-fails on it.

And it understates the gate, which is the part that makes these figures
citable. Every row came back with the sentence containing it and the document
it was read from, and `verify` checked the quote character-for-character before
`accept` would move it. A number here is not trusted because a model produced
it. It is trusted because the quote was checked and the grade was set by a
person.

So: **extracted by** a local model, **specified and graded by** a human,
**verified against** the returned document. Use that phrasing anywhere this
work is described outside the repo — it is the claim that survives a reader who
goes and checks, and "an AI researched it" is the claim that does not.

## Division of labour

| Step | Who |
|---|---|
| Fetch source documents | COOPER — it has internet |
| Chunk, embed, retrieve the right passage | COOPER — `nomic-embed-text` |
| Extract the figure and its verbatim quote | COOPER |
| Normalise units, compute ratios | COOPER |
| Draft `notes:` prose and fact bodies | COOPER |
| Run `build` + `audit` as a self-check | COOPER |
| **Decide a source is authoritative** | **Human** |
| **Promote a confidence grade** | **Human** |
| **Accept into `data/`** | **Human** |

## What COOPER may not do

These are not style preferences. Each one is a place where a local model would
silently corrupt the corpus.

1. **May not assign `measured` or `derived`.** Both are claims about
   *provenance*, not about a number. `measured` means a government agency
   measured it; `derived` means it was computed from figures that were. Neither
   is visible in the text of a document. `verify` rejects any row claiming them.
2. **May not add to `data/sources.yaml`.** New sources go in a
   `proposed_sources:` block for a human to promote. Deciding that a website is
   authoritative is the judgement call this whole design routes around.
3. **May not write to `data/`.** Output lands in `outbox/`. `accept` moves it,
   and only after `verify` passes.
4. **May not resolve a conflict between sources.** It *reports* the conflict.
   `docs/ISRAEL-PLAN.md` does this well: three per-capita figures that disagree,
   laid out side by side with the likely cause named, and no winner declared.
   That is the standard.

## The gate: verbatim quotes

Every figure comes back with the literal sentence containing it, **and the
document COOPER fetched**. `verify` checks the quote appears character-for-
character in that document.

```yaml
- field: flowers_per_gram_dried
  value_lo: 150
  value_mode: 170
  value_hi: 200
  unit: flowers per gram
  confidence: industry
  document: inbox/saffron/03-fao-crocus.txt
  quote: "approximately 150 to 200 flowers are required to produce one gram"
  agreement: 2/2
  verified_by: null
```

A fabricated citation fails mechanically. No judgement required, which is the
point — judgement is the expensive part.

Returning the document is not optional. Without the artifact there is nothing
to check the quote against, and the gate becomes theatre.

## Provenance travels with the figure

Every findings file in `accepted/` carries an `extraction:` block at its head:

```yaml
extraction:
  host: COOPER
  models: [qwen2.5-coder:7b, gemma4-32k]
  ran: 2026-07-29
  specified_by: human            # which URLs, which fields, which questions
  gate: verify (verbatim quote against the returned document)
```

It is written where it is for one reason: a row that gets read, quoted or
copied out of this directory should say what produced it without the reader
having to know what `docs/research/` means. A directory name is not provenance
— it is an implication, and it does not survive the first copy-paste.

The block describes the batch; `agreement:` on each row carries the per-figure
detail, including which model went quiet (`1/1`, `1/2 disagree: 20 vs None`).
Those two together are the honest record. Do not collapse them into a single
"extracted by" string per row unless the runner starts recording which model
won each field, which it currently does not — a per-row attribution nobody
measured is exactly the kind of tidy-looking fiction this pipeline exists to
keep out.

`extraction:` is metadata. `verify` reads `findings:` and ignores it, so the
block cannot be used to smuggle a claim past the gate.

## Three free quality mechanisms

All three cost only COOPER's idle time.

1. **Quote verification** — above.
2. **Two-model consensus.** Extraction runs on `qwen2.5-coder:7b` and
   `gemma4-32k`. Different families fail differently, so agreement is
   meaningful. Disagreement is *not* an error and is never averaged — it is
   flagged `needs_human`, because two models reading different numbers out of
   one sentence is exactly the case a person should look at.
3. **Self-audit.** COOPER runs `build` + `audit` before returning, so
   malformed YAML never reaches review.

## Confidence grades

| Grade | COOPER may assign? | Meaning |
|---|---|---|
| `measured` | No | A government agency measured it |
| `derived` | No | Computed from measured figures |
| `study` | **No** (changed 2026-07-29) | Peer-reviewed |
| `industry` | Yes | Trade body or trade press |
| `estimate` | Yes | Reasoning, flagged as such |

`study` used to be allowed when the document was a journal article. It was
withdrawn on evidence: in a three-model A/B on a **UC Master Gardeners web
page**, qwen2.5-coder returned `confidence: "study"` regardless, and the gate
permitted it.

Whether a document is peer-reviewed is a fact about its provenance, not about
its sentences — which is exactly why `measured` and `derived` were human-only
from the start. The honey batch shows how fine the distinction gets: Jaganathan
& Mandal 2009 *is* peer-reviewed, and the figure everyone takes from it is
uncited scene-setting in a paper about cancer cells. A model that sees "Journal"
in a header cannot tell those apart.

COOPER assigns `industry` or `estimate`. A human promotes.

## Model notes, measured rather than assumed

Both were timed on COOPER on 2026-07-29:

- **`qwen2.5-coder:7b`** — 15.6s, returned exactly `170` with no preamble.
  **Use this for structured extraction.**
- **`gemma4-32k`** — 11.2s, correct answer but wrapped in a visible reasoning
  trace (`Thinking... ...done thinking.`) *and* ANSI control codes
  (`ESC[1D`, `ESC[K`, trailing `\r`). **Use only when 32k context is actually
  needed**, and always through `sanitize()`.

The trap worth knowing: gemma4 prints the answer **twice** — once inside its
reasoning ("the core numerical value stated is 170") and once after
`...done thinking.`. A naive regex for the first number in the output can pick
up a number from the reasoning rather than the answer. `sanitize()` cuts
everything up to and including `...done thinking.` for this reason.

At 11–16s on a *trivial* prompt, expect 30–90s per real document chunk. A
6-item batch across two models runs 10–20 minutes: idle-time work, not
sit-and-watch work.

## Workflow

```bash
python tools/research_batch.py scout  batch-01-saffron   # pre-flight, BOTH hosts
python tools/research_batch.py send   batch-01-saffron   # spec -> COOPER
# ... COOPER runs tools/cooper/runner.py, 10-20 min ...
python tools/research_batch.py fetch  batch-01-saffron   # results + documents
python tools/research_batch.py verify batch-01-saffron   # the gate
python tools/research_batch.py accept batch-01-saffron   # only if verify passed
```

`accept` writes `data/<prefix>_<subject>.yaml`, which the existing
`build.merge_files()` globbing picks up with **no code change** — the same
mechanism that let eggs arrive as `taxonomy_eggs.yaml` and
`loss_chain_eggs.yaml`.

Then, on the Mac, on a **Python 3.12** venv per `CLAUDE.md`:

```bash
python -m counting_chicken_wings.build
python -m counting_chicken_wings.audit
pytest -q
```

COOPER runs 3.14, so its self-check is a pre-filter. Acceptance happens here.

## Walls, truncation, and where each is caught

A fetch can lie in two ways, and they need two different checks.

| Failure | Looks like | Caught by |
|---|---|---|
| Bot wall | short, HTTP 200 — PMC gave the Mac 41,579 chars of Gross 2023 and COOPER 167 chars of reCAPTCHA | `document_is_a_wall`, in `verify` |
| JS truncation | long, byte-identical everywhere — bows-n-ties came back at 7,195 chars on both hosts, ending mid-word, with the cited figure absent | the verbatim quote check |

**The wall is per-request, not per-host.** batch-06 fetched that same PMC URL
from COOPER and got 82,331 characters of the real article, hours after
batch-05 got 167 characters of reCAPTCHA from the same machine with the same
fetcher. So no pre-flight check can promise anything about the fetch the run
will make ten minutes later, and the defence has to live where the documents
actually arrive:

- **`verify` fails any row whose document is an interstitial** — a body under
  1,500 characters carrying reCAPTCHA / Cloudflare / "enable JavaScript"
  wording. It reports the wall by name, so the failure does not read as the
  model having made its quote up.
- **`fetch` prints the same list** as the documents land, because a walled
  document usually explains an item that returned *nothing*, and a row that
  returned nothing never reaches the gate. batch-05 read as "the models
  declined" when one of them had been handed 167 characters of doorman.

`scout` still runs before `send`, checks every URL from this Mac **and from
COOPER** through the same `runner.fetch_once`, and compares the two character
counts. Treat it as a **smoke test for a persistent wall, not a guarantee**: a
URL fails when COOPER returns under a quarter of what the Mac does (measured:
eleven of twelve cross-host pairs agreed exactly or within five characters, and
the one wall collapsed to 0.4%, so the threshold sits in a wide empty gap). A
green scout is one sample of an intermittent behaviour.

Compare **characters, not bytes**: COOPER writes CRLF, so every document's byte
count differs across the two hosts by exactly its line count.

Scout exit codes: `0` clean · `1` the spec has a problem · **`2` the COOPER
smoke test did not run**. Two is not a pass — batch-05 was cleared to send by a
Mac-only scout that printed "Safe to send".

## Quotes that verify and still say nothing

Two checks warn `[needs_human]` rather than failing, because both have honest
counter-examples and a gate that cries wolf gets ignored:

- **A bare table row.** `"Eggs, 5.1, 1.3%"` (batch-09, a share of total
  food-loss calories read as an egg loss rate, wrong by ~20×) and `"Fluid milk
  109 13 12 22 20 35 32"` (batch-05, severed from the header that said which
  column was retail and which consumer). Fires on at least two numbers against
  no more than two words, or on numbers with no words at all (`"150 -185"`).
- **A quote that is not a sentence.** Ending punctuation is no longer taken as
  proof of completeness: `"(60 pounds versus 2,000 pounds)"` is balanced,
  complete and unreviewable, and used to pass because its last character was a
  bracket.

The extraction prompt (`tools/cooper/runner.py`) also carries a standing
instruction to copy a table's column header into the quote, not just the row,
and to decline rather than guess when no header can be found. That is
instruction, not enforcement -- it costs nothing to ignore, which is why
`quote_lacks_basis` still runs at gate time regardless of what the model was
told.

## SSH, and two traps that have already cost time

- **Quoting through `ssh cooper "..."` is unreliable.** cmd.exe strips single
  quotes and the local shell eats `$`. Write the script to a file, base64-encode
  it as UTF-16LE, and run
  `powershell -NoProfile -EncodedCommand <b64>`. `research_batch.py` does this;
  never interpolate a command string.
- **PowerShell progress records flood stdout over SSH** as CLIXML. Every remote
  script starts with `$ProgressPreference = "SilentlyContinue"`.

## Expect thin data, and say so

Chicken had USDA NASS. Saffron does not. These subjects will come back mostly
`industry` and `estimate` — and COOPER cannot assign anything stronger anyway.

That is acceptable **only because the audit prints the confidence mix on every
build**, so the thinness stays visible instead of being laundered by proximity
to well-sourced poultry figures. Each batch spec restates this.

If a subject returns nothing above `estimate`, ship it flagged or do not ship
it. Do not promote a grade to make a page look better.
