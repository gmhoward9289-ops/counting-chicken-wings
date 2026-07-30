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

**URLs ARE FILLED AND VERIFIED (2026-07-30).** A Hebrew search pass ran before
this batch was sent; every URL below returned 200 to curl with an ordinary
browser user-agent on that date, with the byte size recorded. Two things that
pass found and this batch now depends on:

- The Poultry Board's domain is **ofot.org.il**. The earlier guess of
  `ofek-poultry.org.il` does not resolve and is recorded as a dead end.
- A treifot RATE appears to exist in halachic sources -- 5-7% at the tendon
  junction (צומת הגידים). That is item 4's whole question, and it changes the
  instruction there from "expect to fail" to "extract it carefully".

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

### Item 1 — The Poultry Board (מועצת הלול)

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

**Candidate URLs:**

- https://www.ofot.org.il/page_14377 — Poultry Board, דוחות מבוקרים (audited reports). 200, 29,440 bytes. The likeliest home of a figure on a site that is otherwise recipes and nutrition advice.
- https://www.ofot.org.il/ — Poultry Board front page. 200, 48,935 bytes.
- http://www.ofotm.org.il — the growers' site the council links to. 200, 60,576 bytes.
- https://ofot.co.il/%D7%A2%D7%A0%D7%A3-%D7%94%D7%9C%D7%95%D7%9C-%D7%A1%D7%99%D7%9B%D7%95%D7%9D-2021/ — "ענף הלול - סיכום 2021", a sector summary from the growers' organisation. 200, 122,696 bytes. Note the different domain: ofot.CO.il is the growers, ofot.ORG.il is the council.

**Warning from the manual pass:** ofot.org.il is largely a consumer nutrition
and recipe site. Do not conclude from a thin front page that the council
publishes nothing -- check the audited-reports page and the growers' site
before recording an absence.

---

### Item 2 — Ministry of Agriculture veterinary services

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

**Candidate URLs:**

- https://library.mevaker.gov.il/sites/DigitalLibrary/Documents/65c/2015-65c-218-Halul.pdf — State Comptroller, "ענף הלול - היבטים באסדרה, בטיפול ובפיקוח". 200, 456,705 bytes. A GOVERNMENT audit of the poultry sector and its regulation.
- https://library.mevaker.gov.il/sites/DigitalLibrary/Pages/Reports/297-24.aspx — the landing page with the summary, if the PDF extracts badly. 200, 74,855 bytes.

**Read the date before trusting it:** this is annual report 65c, covering 2014
and the 2013 accounts. It is a decade old and it is about *regulation*, not
about slaughter volumes. It is listed because it is the only reachable
government document on the Israeli poultry sector found so far, and because an
audit of the Poultry Board will say what the Board is supposed to publish --
which is how you find the series, even if the numbers in it are stale.

**gov.il itself is closed.** Both `gov.il` and `moag.gov.il` return 403 with an
identical 5,481-byte body to every fetcher tried, including a
`/he/departments/publications/reports/` path. Do not spend the batch retrying
it; record the block and move on.

---

### Item 3 — A bedikah rejection rate, if one exists anywhere

**Question:** What proportion of birds are rejected at post-slaughter kosher
inspection?

**Search in Hebrew:** `אחוז טרפות עופות`, `בדיקת ריאות עופות אחוז`,
`שחיטה כשרה פסולים אחוז`

**Why it matters:** this is the strongest unexploited modelling content in the
whole Israel plan — a loss stage with no US analogue, in a country where
essentially all commercial slaughter is kosher. It should push the
birds-required number up.

**A rate appears to exist, and this changes the item.** The English kosher
agencies describe the procedure and publish no rate, but Hebrew halachic
sources discuss one directly: roughly **5-7% of birds are treif at the tendon
junction** (צומת הגידים), the exact stage OU Kosher describes as part of
poultry bedikah.

**Extract it with more care than usual, because of what it is not.** A rabbinic
authority stating a working percentage is not a survey. It is closer to our
`industry` grade than to anything measured, it may be a figure repeated between
authorities rather than independently established, and the tendon junction is
only one of the grounds for rejection -- lungs and intestines are inspected too,
so a tendon-junction rate is a FLOOR on total bedikah rejection, not the whole
of it.

**Done means:** the percentage, the verbatim Hebrew sentence, which authority
said it, and whether it is presented as an observation or as a halachic
assumption. If two authorities give different numbers, report both as a
conflict; do not average them.

**Still forbidden:** returning an estimate of your own. The instruction that has
not changed is that an invented figure here would move an entire country's
headline answer on nobody's data.

**Candidate URLs:**

- https://ph.yhb.org.il/17-20-15/ — פניני הלכה, Rabbi Eliezer Melamed, "הלכה טו - בדיקות נוספות" in the chapter on טריפות. 200, 238,606 bytes. The most systematic of these.
- https://www.toraland.org.il/%D7%9E%D7%90%D7%9E%D7%A8%D7%99%D7%9D/%D7%9B%D7%A9%D7%A8%D7%95%D7%AA-%D7%94%D7%9E%D7%96%D7%95%D7%9F/%D7%9B%D7%A9%D7%A8%D7%95%D7%AA-%D7%9B%D7%9C%D7%9C%D7%99/%D7%A8%D7%9E%D7%95%D7%AA-%D7%9B%D7%A9%D7%A8%D7%95%D7%AA-%D7%91%D7%A2%D7%95%D7%A4%D7%95%D7%AA/ — Torah VeHa'aretz Institute, "רמות כשרות בעופות", where the different inspection standards get compared. 200, 505,593 bytes.
- https://www.kosharot.co.il/index2.php?id=29758&lang=HEB — Kosharot, consumer Q&A on chicken and turkey certification. 200, 62,918 bytes.
- https://www.badatz.biz/article/%D7%A9%D7%97%D7%99%D7%98%D7%AA-%D7%A2%D7%95%D7%A4%D7%95%D7%AA-%D7%A4%D7%98%D7%9D-%D7%91%D7%93%D7%A6-%D7%91%D7%99%D7%AA-%D7%99%D7%95%D7%A1%D7%A3/ — Badatz Beit Yosef on broiler slaughter specifically, a certifying body describing its own process. 200, 115,933 bytes.

---

## Deferred — written up, deliberately NOT sent

Two items were dropped from the batch rather than sent with no URLs of their
own, because of how `parse_spec` behaves: **an item with no `- https://` line
inherits the previous item's URLs.** An unfilled item is therefore not skipped,
it is answered against the wrong documents — and a confident answer sourced from
an unrelated page is the exact failure this pipeline exists to prevent. So they
live here, below every `### Item` heading and phrased without the markers the
parser looks for.

**TheMarker on plant market shares.** What did TheMarker actually report about
Of HaGalil's and Of Oz's share of Israeli chicken slaughter, and who did it
attribute the figures to? Poultry World gives ~15% and ~5%, but that is Poultry
World citing TheMarker citing unnamed industry sources — third-hand, and not
loaded for that reason. The original might name its source, which would move the
figure from unusable to `industry`. Both plants sit in districts we already
hold: Of HaGalil in Kiryat Shmona in the north, Of Oz in Sha'ar HaNegev, which
marketed 9,813 tonnes of broilers in 2024 — so a share figure that disagrees
wildly with our district tonnage is itself a finding. Search
`דה מרקר של הגליל שחיטה` and `עוף עוז נתח שוק`, and record whether the
percentages are of head or of tonnage; those are different claims.

**Per-capita consumption.** Is there a primary Israeli or FAO series, with its
definition stated? **Five reachable sources give five figures for the same
rank** — 58.2 kg (OECD-FAO via a now-404 article), 57.7 kg (trade press), 64.9
kg (no clear provenance), 70.83 kg (World Population Review citing FAOSTAT food
balances, 2022), and a separate dataset putting Kuwait at 65.43 kg *ahead* of
Israel. A 20% spread across sources that all claim first place is not a
citation. The spread is almost certainly definition drift — poultry meat versus
chicken meat, carcass versus retail weight, different years — and the two series
that would settle it are both closed: FAOSTAT's API and bulk downloads return
401/403/521, and the OECD-FAO annex PDF extracts as font-encoded gibberish.

This one is deferred rather than merely unfilled: it needs a *primary series*,
which is a human research task with a browser, not a fetch. Until then no
per-capita figure ships, in a fact, a note, or a statistic — and a test enforces
it. "Israel is #1" is the claim a guest can disprove on their phone, and an
honest #2 beats a #1 that collapses.

## What COOPER may not do on this batch

The standard rules in `../README.md` apply, and two are worth restating because
this batch is unusually exposed to both:

- **May not assign `measured`.** Even if a Hebrew government page carries a head
  figure, promoting it is a human decision.
- **May not resolve the per-capita conflict.** Report all three figures with
  their definitions. Choosing between them is exactly the judgement this
  pipeline routes around.
