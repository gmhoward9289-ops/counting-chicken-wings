# Batch 05 — Israel, the Hebrew-language sources

**Archetype:** `provenance-audit` + `how-many`

**Question in one sentence:** Does anyone in Israel officially publish how many
broilers are slaughtered per year — and if not, who publishes the closest thing?

**Expected confidence ceiling:** `measured` for items 1 and 2 if they exist at
all; `industry` for everything else. Item 5 should probably not ship.

---

## Read this before running the batch

**The English web has been exhausted.** Two passes are recorded in
`docs/research/library/poultry-israel.yaml`: the CBS route (which works, and
gives tonnage, a year-end flock and districts) and the press route (which gives
a single industry head figure of ~260 million birds a year from a named
official). What is missing is not findable in English, which is the whole
premise of this batch.

**Everything here needs Hebrew.** Search terms are given in Hebrew because the
English equivalents return the same trade-press recycling we already hold.

**Two hard constraints from the earlier passes:**

1. **COOPER fetches exactly the URLs it is given and never searches.** So the
   candidate URLs below are deliberately blank. Fill them from a real Hebrew
   search pass before sending; an invented URL fails silently and the batch
   returns empty for a reason nobody can see.
2. **`gov.il` and `moag.gov.il` return 403 to every fetcher tried, including
   plain curl**, with an identical 5,481-byte body. That is an Akamai bot
   filter, not an absent page. If the figure lives there, a fetch will not get
   it — it needs a real browser session. Flag rather than retry.

---

## Item 1 — The Poultry Board (מועצת הלול)

**Question:** Does the Poultry Board publish annual broiler slaughter in head,
and if so where and for which years?

**Search in Hebrew:** `מועצת הלול נתונים`, `מועצת הלול דוח שנתי`,
`שחיטת עופות נתונים שנתיים`, `מועצת הלול פטמים`

**Why it matters:** this is the Israeli analogue of the National Chicken
Council and it is the single most likely publisher of the missing denominator.
We have never confirmed its domain — a guessed `ofek-poultry.org.il` does not
resolve, and that guess is recorded as a dead end so nobody repeats it.

**Done means:** either a URL that carries a head figure with a year attached,
or a recorded statement that the Board publishes no head series, with the page
that shows what it does publish. **An absence, recorded, is a successful
outcome for this item.**

**Candidate URLs:** _(fill from a Hebrew search pass)_

---

## Item 2 — Ministry of Agriculture veterinary services

**Question:** Do the veterinary services publish slaughter statistics — birds
inspected, birds condemned — the way FSIS does?

**Search in Hebrew:** `השירותים הווטרינריים שחיטה`,
`משרד החקלאות נתוני שחיטה`, `פסולי שחיטה עופות`

**Why it matters:** this is the only realistic route to two things at once —
a government head count, and a **condemnation rate**, which the model currently
has only for the US. Kosher slaughter plausibly rejects on different grounds
than FSIS does, and this is where that would be visible.

**Do not confuse** with the kosher *bedikah* rejection in item 4. Veterinary
condemnation and rabbinical rejection are different stages with different
authorities, and merging them would double-count or hide one entirely.

**Candidate URLs:** _(fill from a Hebrew search pass)_

---

## Item 3 — TheMarker, on plant market shares

**Question:** What did TheMarker actually report about Of HaGalil's and Of Oz's
share of Israeli chicken slaughter, and who did it attribute the figures to?

**Search in Hebrew:** `דה מרקר של הגליל שחיטה אחוז`, `עוף עוז נתח שוק`

**Why it matters:** Poultry World gives ~15% and ~5%, but that is Poultry World
citing TheMarker citing unnamed industry sources — third-hand, and not loaded
for that reason. The original might name its source, which would move the figure
from unusable to `industry`.

**Both plants sit in districts we already hold.** Of HaGalil is in Kiryat
Shmona in the north; Of Oz is in Sha'ar HaNegev, which marketed 9,813 tonnes of
broilers in 2024. If a share figure and our district tonnage disagree wildly,
that disagreement is itself a finding.

**Done means:** the original article, its own attribution, and whether the
percentages are of head or of tonnage — those are different claims.

**Candidate URLs:** _(fill from a Hebrew search pass)_

---

## Item 4 — A bedikah rejection rate, if one exists anywhere

**Question:** What proportion of birds are rejected at post-slaughter kosher
inspection?

**Search in Hebrew:** `אחוז טרפות עופות`, `בדיקת ריאות עופות אחוז`,
`שחיטה כשרה פסולים אחוז`

**Why it matters:** this is the strongest unexploited modelling content in the
whole Israel plan — a loss stage with no US analogue, in a country where
essentially all commercial slaughter is kosher. It should push the
birds-required number up.

**Why it will probably fail:** two English kosher-agency sources describe the
procedure in detail and neither publishes a rate. Certification agencies have
no reason to publish rejection statistics.

**Done means a rate with a source, or a clear statement that no rate is
published.** Do NOT return an estimate. An invented figure here would be the
worst outcome available: it would move the headline answer for an entire
country on the strength of nobody's data.

**Candidate URLs:** _(fill from a Hebrew search pass)_

---

## Item 5 — Per-capita consumption, and why this one is a trap

**Question:** Is there a primary Israeli or FAO series for per-capita chicken
consumption, with its definition stated?

**Status: three reachable sources give three different "world's highest"
figures** — 58.2 kg (OECD-FAO, via a now-dead article), 70.83 kg (World
Population Review, citing FAOSTAT food balances, 2022), and 64.9 kg circulating
without clear provenance. A 20% spread across sources that all claim the same
rank.

**The spread is almost certainly definition drift:** poultry meat versus chicken
meat, carcass weight versus retail weight, and different years. FAOSTAT's own
API and bulk downloads are currently closed (401/403/521), and the OECD-FAO
annex PDF uses a custom font encoding that extracts as gibberish.

**Recommendation: do not ship a per-capita figure from this batch.** If COOPER
returns one, it goes in as a `proposed_source` with the definition quoted
verbatim and the year named, or not at all. "Israel is #1" is the claim a guest
can disprove on their phone, and an honest #2 beats a #1 that collapses.

**Candidate URLs:** _(leave blank unless a primary series is found)_

---

## What COOPER may not do on this batch

The standard rules in `../README.md` apply, and two are worth restating because
this batch is unusually exposed to both:

- **May not assign `measured`.** Even if a Hebrew government page carries a head
  figure, promoting it is a human decision.
- **May not resolve the per-capita conflict.** Report all three figures with
  their definitions. Choosing between them is exactly the judgement this
  pipeline routes around.
