# Checkpoint — 2026-07-29, ~21:00 ET

Written mid-session because context was filling. Read this first on resume.

## State

| | |
|---|---|
| Released | **v1.2.0**, tagged and pushed |
| `master` | `4fe60b2`, level with `origin/master` |
| Tests | 277 passing |
| Audit | exits 0 — every statistic cited |
| Deployed | https://counting-chicken-wings.onrender.com (tracks `master`, so ahead of the tag) |

**Check `GET /api/version` for the deployed SHA.** "Is v1.2.0 live?" is the
wrong question — Render tracks the branch, not tags.

## Done this session

**v1.2.0 — eggs get their own supply chain.** A correctness release, not a
feature. v1.1.0 had shipped eggs with the right number and the wrong
explanation: eggs had no chain of their own, `default_supply_chain()` took no
product argument, so an egg query inherited the WING cascade and the audit trail
described a cut-up line and a fryer basket to anyone asking about a carton. The
count was right only because a hen's one-egg-a-day ceiling dominates.

Fixed at the design level rather than patched:

- Supply chains scoped to a species; `species_slug` **required** on
  `default_supply_chain()`, with no cross-species fallback. Returning another
  animal's route fails silently, which is worse than failing.
- Egg mixing cascade: nest/belt collection → farm cooler → washing → candling →
  carton → distributor → retail case → fridge. Three routes, and only
  `backyard_eggs` can reach the floor of one hen.
- **Channel-aware losses** via `supply_chain_loss_stage`. `supply_chain`
  previously selected mixing stages but not losses, so every route got every
  stage and `retail_shrink` had to be parked default-off to avoid
  double-counting `kitchen_loss`. New `grocery_retail` route pays retail shrink
  and no kitchen; a test asserts no route claims both.
- Floor prose moved into data as `supply_chain.floor_note`. It was hardcoded
  wing text in **both** `cli.py` and `static/index.html`, so fixing the data
  alone would not have fixed the output.
- Fixed `resolve_pool()` clamping its lower bound to `container/upi` without
  capping at container size — for eggs at `upi=0.789` it reported a 12-egg
  carton as "roughly 15 individuals", more contributors than units.

**Egg grading is documented, not just decided.** Modelling it as ordinary mixing
rather than active separation is a judgement about mechanism, not a sourced
figure. George approved the choice on condition it be explainable, so it now
appears in the stage description and as a learning-centre fact.

## In progress — not mine, do not commit

`data/loss_chain_saffron.yaml`, `data/mixing_saffron.yaml`,
`data/taxonomy_saffron.yaml`, `tests/test_saffron.py`, plus modifications to
`sources.yaml`, `api.py`, `cli.py`, `db.py`, `model.py`.

Another session is integrating saffron. **There will always be in-process data
in this repo** — George said so outright; the research pipeline guarantees it.
Never `git add -A` here. Stage explicit paths, and never suggest he commit or
stash his in-flight work first.

## COOPER — batch-02-vanilla running

Launched detached so it survives the SSH session:

```powershell
Start-Process -FilePath "python" -ArgumentList "C:/research/cooper/runner.py","batch-02-vanilla" -RedirectStandardOutput "C:/research/vanilla.log" -RedirectStandardError "C:/research/vanilla.err" -WindowStyle Hidden
```

Last seen 12% GPU, 7.8 GB of 8 GB VRAM, `outbox/batch-02-vanilla` still empty —
it writes at the end. `vanilla.log` stays empty because Python buffers stdout
when redirected; that is not a failure.

When it finishes:

```bash
python tools/research_batch.py fetch batch-02-vanilla
python tools/research_batch.py verify batch-02-vanilla
python tools/research_batch.py accept batch-02-vanilla   # only after verify
```

**batch-01-saffron already ran and was fetched.** 6 items, 5 figures found, 3
model disagreements correctly flagged rather than averaged, and
`harvest_labour_hours` found in no source. Results in
`docs/research/outbox/batch-01-saffron/`.

## The bottleneck, measured

**Not the GPU** — 9–19% utilisation throughout. It is **spec authoring**, the
one step COOPER structurally cannot do, since deciding a source is authoritative
is the judgement the whole design routes around.

`batch-02-vanilla` and `batch-03-wagyu` were both written as planning documents
with the Items section never filled, so COOPER exited instantly with
`no items found in spec`. Vanilla now has six items against four sources, each
`curl`-verified 200 before being written in — a guessed
`extension.psu.edu/vanilla` returned **404** during that pass and was discarded.

Coverage was probed per source rather than assumed: the World Bank guide is
strong on pollination and yields but says "cured" **once in 4,433 lines**, so it
cannot answer the curing ratio, while the short Package of Practice PDF carries
that figure verbatim.

## Exactly what's next

1. **`batch-03-wagyu` items** — still a stub, still unrunnable. Author it the way
   vanilla was: search, `curl`-verify every URL, probe coverage per source.
2. **Emit the source library as a byproduct of doing (1)** — write the
   verification results to `docs/research/library/red_meat.yaml`. See
   `docs/research/SOURCE-LIBRARY.md`; the recommendation is deliberately NOT to
   build the library as its own project, and to add `tools/verify_sources.py`
   only after the format has survived two subjects.
3. **Fact voting** — from the Chicken Scratch note, still unbuilt. Up/down for
   accuracy, like for enjoyment, no dislike. Treat votes as a triage queue for
   us, never a published score, or anonymous clicks quietly undermine the
   citation guarantee.
4. **Egg loss chain is already done** (5 factors) — not a gap.

## Two hazards learned the hard way

**A concurrent session's index operation silently wiped my staging.**
`git status` briefly reported "working tree clean" while my work sat
uncommitted, and I nearly reported success on a commit that never happened. With
parallel sessions, **stage and commit in one command** — the gap between them is
a real window. Verify HEAD's contents, not the status line.

**`grep -c` returning 0 exits 1 and aborts an `&&` chain.** I read the truncated
output as evidence that a change had been lost. Use `|| true` on counting greps
inside chains.
