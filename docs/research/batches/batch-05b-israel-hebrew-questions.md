# Batch 05b — the same Hebrew documents, asked in Hebrew

**Archetype:** `experiment`

**This is not a research batch. It is an A/B test of the pipeline itself,** and
the only thing that changes from batch-05 is the language of the questions.

## The hypothesis

Batch-05 sent three items over ten Hebrew documents to two models and got
**zero figures**. The documents were fine — every URL fetched, the 40-page State
Comptroller PDF extracted to 103,610 characters, and 18,137 Hebrew characters
survived in the Badatz page alone. Chunking produced 21 chunks across ~290,000
characters, which is the expected count.

Then a human read the same returned artifacts and found real figures in minutes.

**So the failure is between the chunks and the model, and the likeliest cause is
cross-language retrieval:** the questions were English, the chunks are Hebrew,
and `nomic-embed-text` is English-centric. An English query embedding scored
against Hebrew chunk embeddings is close to noise, so the top-k chunks handed to
the model are probably not the ones holding the numbers.

**If that is right, asking in Hebrew fixes it with no code change.** If it is
wrong, the embedder is the problem and that is a real change to `runner.py` worth
scoping on its own.

## The controlled part

Item 1 below targets `ofot.co.il`, and **we already know the answer**. The
document contains this table, and a human found it by reading the file COOPER
downloaded:

> סוג התוצרת / מספר מגדלים / כמות תוצרת / יחידות / מיליוני ₪ / אחוזים
> בשר פטמים 604 · 515,400 טון · 3,414 · 57.3%
> שלוחות הרבייה 78 · 244 מיל' אפרוחים · 980 · 16.4%

That makes this a test with a known answer rather than a fishing trip. **604
growers and 515,400 tonnes are the target.** If a Hebrew question retrieves that
chunk and either model reads either number out of it, the hypothesis holds and
Hebrew batches become viable. If it still returns nothing, stop asking in Hebrew
and go change the embedder.

**Read the result as a pipeline finding either way.** A figure that comes back
here is still not corpus: it goes through `verify` like everything else, and the
figures themselves are already recorded in
`docs/research/accepted/batch-05-israel-hebrew-REVIEW.md` from the human read.

---

### Item 1 — מספר מגדלי פטמים וכמות התוצרת

**Question:** כמה מגדלי פטמים יש בישראל, וכמה טונות בשר פטמים יוצרו בשנת 2021?

**Field:** broiler growers and output, 2021

**Done means:** the number of growers (604) or the tonnage (515,400), with the
verbatim Hebrew sentence it came from. Either one counts as a pass.

**Candidate URLs:**

- https://ofot.co.il/%D7%A2%D7%A0%D7%A3-%D7%94%D7%9C%D7%95%D7%9C-%D7%A1%D7%99%D7%9B%D7%95%D7%9D-2021/ — ארגון מגדלי עופות, "ענף הלול - סיכום 2021". 200, 122,696 bytes. Contains the target table.
- http://www.ofotm.org.il — the growers' site. 200, 60,576 bytes.

---

### Item 2 — אפרוחים בשלוחות הרבייה

**Question:** כמה מיליוני אפרוחים סיפקו שלוחות הרבייה בישראל בשנת 2021?

**Field:** chicks placed, 2021

**Done means:** 244 million chicks, with its verbatim sentence.

**Why this one matters beyond the experiment:** chicks placed is a throughput
proxy, and 244 million in 2021 sits just under the 260 million broilers a year
that the Times of Israel reports for 2025 — two industry bodies, four years
apart, differing by about 6%. That is the only independent check the Israeli
head count has.

**It is NOT birds slaughtered.** Mortality sits between chicks placed and birds
slaughtered, and the model already carries a grow-out mortality factor. Whatever
comes back is a `chicks_placed` figure and nothing else.

**Candidate URLs:**

- https://ofot.co.il/%D7%A2%D7%A0%D7%A3-%D7%94%D7%9C%D7%95%D7%9C-%D7%A1%D7%99%D7%9B%D7%95%D7%9D-2021/ — same document as item 1. 200, 122,696 bytes.

---

### Item 3 — אחוז הטרפות בשחיטת עופות

**Question:** מהו אחוז העופות הנפסלים כטרפה בבדיקה שלאחר השחיטה?

**Field:** bedikah rejection rate

**Done means:** a percentage with the authority who stated it, or a clear
statement that these four documents contain none.

**Expected to fail, and that is informative.** A human pass over these four
files found **zero** occurrences of `%` or `אחוז` in any of them. So this item is
the negative control: if a model returns a rejection rate from documents that
provably contain no percentage, it is hallucinating, the quote gate should catch
it, and that is a finding about the gate rather than about Israel.

**Candidate URLs:**

- https://ph.yhb.org.il/17-20-15/ — פניני הלכה, "הלכה טו - בדיקות נוספות". 200, 238,606 bytes.
- https://www.toraland.org.il/%D7%9E%D7%90%D7%9E%D7%A8%D7%99%D7%9D/%D7%9B%D7%A9%D7%A8%D7%95%D7%AA-%D7%94%D7%9E%D7%96%D7%95%D7%9F/%D7%9B%D7%A9%D7%A8%D7%95%D7%AA-%D7%9B%D7%9C%D7%9C%D7%99/%D7%A8%D7%9E%D7%95%D7%AA-%D7%9B%D7%A9%D7%A8%D7%95%D7%AA-%D7%91%D7%A2%D7%95%D7%A4%D7%95%D7%AA/ — מכון התורה והארץ, "רמות כשרות בעופות". 200, 505,593 bytes.
- https://www.kosharot.co.il/index2.php?id=29758&lang=HEB — כושרות. 200, 62,918 bytes.
- https://www.badatz.biz/article/%D7%A9%D7%97%D7%99%D7%98%D7%AA-%D7%A2%D7%95%D7%A4%D7%95%D7%AA-%D7%A4%D7%98%D7%9D-%D7%91%D7%93%D7%A6-%D7%91%D7%99%D7%AA-%D7%99%D7%95%D7%A1%D7%A3/ — בד"ץ בית יוסף. 200, 115,933 bytes.

---

## What COOPER may not do

Everything in `../README.md` applies unchanged. Restated because this batch is
an experiment and an experiment invites shortcuts:

- **May not assign `measured`, `derived` or `study`.** Not even for a figure
  from a growers' organisation that looks official.
- **May not resolve the chicks-versus-slaughter distinction.** Report the number
  the document gives, with its own words for what it counts.
