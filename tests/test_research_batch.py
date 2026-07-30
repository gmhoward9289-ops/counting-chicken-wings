"""Tests for the research batch gate.

The gate is the only thing standing between free local models and a corpus
whose whole value is that every number traces to a real source. So these tests
are written adversarially: each one is a way a model could corrupt the data.
"""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "cooper"))

import research_batch as rb                          # noqa: E402
from runner import consensus, parse_spec, sanitize    # noqa: E402


# ---------------------------------------------------------------------------
# sanitize -- fixture captured from a REAL gemma4-32k run, not invented
# ---------------------------------------------------------------------------

# Verbatim from COOPER, 2026-07-29. Note the answer appears TWICE: once inside
# the reasoning ("stated is 170") and once as the real answer after the
# end-of-thinking marker. The ANSI codes are real too.
GEMMA_REAL = (
    "Thinking... Thinking Process:  1. **Analyze the Request:** The goal is to "
    '"Extract the number" from the p\x1b[1D\x1b[K provided text and "Reply with '
    'digits only." 2. **Analyze the Text:** "about 170 flowers per gram." '
    "3. **Identify the Number:** The core numerical value stated is 170. "
    "4. **Format the Output:** The requirement is \"digits only.\"  "
    "5. **Final Answer Generation:** 170 ...done thinking.  170 \r"
)


def test_sanitize_strips_ansi_control_codes():
    out = sanitize(GEMMA_REAL)
    assert "\x1b" not in out
    assert "[1D" not in out and "[K" not in out


def test_sanitize_removes_the_reasoning_trace():
    out = sanitize(GEMMA_REAL)
    assert "Thinking" not in out
    assert "Analyze the Request" not in out


def test_sanitize_returns_only_the_real_answer():
    """The whole point: gemma4 says 170 twice and only the second one is the
    answer. A naive first-number regex would read the reasoning."""
    assert sanitize(GEMMA_REAL) == "170"


def test_sanitize_passes_clean_output_through_untouched():
    """qwen2.5-coder has no trace and must not be mangled."""
    assert sanitize("170") == "170"
    assert sanitize('{"found": true, "value_mode": 170}') == \
        '{"found": true, "value_mode": 170}'


def test_sanitize_handles_empty():
    assert sanitize("") == ""
    assert sanitize(None) == ""


# ---------------------------------------------------------------------------
# Quote verification -- the anti-fabrication gate
# ---------------------------------------------------------------------------

DOC = ("Saffron is harvested by hand. Approximately 150 to 200 flowers are "
       "required to produce one gram of dried saffron threads.")


def test_quote_found_when_present(tmp_path):
    d = tmp_path / "doc.txt"
    d.write_text(DOC)
    ok, _ = rb.quote_in_document(
        "Approximately 150 to 200 flowers are required to produce one gram", d)
    assert ok


def test_fabricated_quote_is_rejected(tmp_path):
    """The failure mode this whole design exists to catch."""
    d = tmp_path / "doc.txt"
    d.write_text(DOC)
    ok, why = rb.quote_in_document(
        "roughly 400 flowers are required to produce one gram", d)
    assert not ok
    assert "does not appear" in why


def test_missing_document_is_rejected(tmp_path):
    """No artifact means nothing to check against, so the gate must fail
    rather than pass by default."""
    ok, why = rb.quote_in_document("anything", tmp_path / "absent.txt")
    assert not ok
    assert "not returned" in why


def test_empty_quote_is_rejected(tmp_path):
    d = tmp_path / "doc.txt"
    d.write_text(DOC)
    assert not rb.quote_in_document("", d)[0]
    assert not rb.quote_in_document("   ", d)[0]


def test_typography_differences_are_forgiven(tmp_path):
    """A quote must match the document's WORDS, not its whitespace and quote
    glyphs. PDF extraction mangles both, and rejecting honest quotes over that
    would teach us to distrust the gate."""
    d = tmp_path / "doc.txt"
    d.write_text("The  crocus\nhas three stigmas — always three.")
    ok, _ = rb.quote_in_document("The crocus has three stigmas - always three.", d)
    assert ok


def test_digits_are_not_forgiven(tmp_path):
    """Typography folding must not extend to the number itself."""
    d = tmp_path / "doc.txt"
    d.write_text("about 170 flowers per gram")
    assert not rb.quote_in_document("about 180 flowers per gram", d)[0]


# ---------------------------------------------------------------------------
# Grade tiers
# ---------------------------------------------------------------------------

def test_human_only_grades_are_named():
    """`study` joined this set on 2026-07-29, on evidence rather than
    principle: in a three-model A/B against a UC Master Gardeners WEB PAGE,
    qwen2.5-coder returned confidence "study" even though the prompt permits it
    only for peer-reviewed journal articles -- and the gate let it through.
    Judging peer-review is a claim about provenance, not about sentences."""
    assert rb.HUMAN_ONLY_GRADES == {"measured", "derived", "study"}


@pytest.mark.parametrize("grade", ["measured", "derived", "study"])
def test_verify_rejects_human_only_grades(tmp_path, monkeypatch, grade):
    """A local model claiming a government agency measured something is the
    highest-consequence failure available to it."""
    batch = "batch-99-test"
    out = tmp_path / "outbox" / batch
    out.mkdir(parents=True)
    doc_dir = tmp_path / "inbox" / "test"
    doc_dir.mkdir(parents=True)
    (doc_dir / "d.txt").write_text(DOC)

    (out / "findings.yaml").write_text(yaml.safe_dump({"findings": [{
        "field": "flowers_per_gram",
        "value_mode": 170,
        "confidence": grade,
        "document": "inbox/test/d.txt",
        "quote": "Approximately 150 to 200 flowers are required",
        "verified_by": None,
    }]}))

    monkeypatch.setattr(rb, "OUTBOX", tmp_path / "outbox")
    monkeypatch.setattr(rb, "RESEARCH", tmp_path)
    monkeypatch.setattr(rb, "trial_build", lambda files: (True, "skipped"))

    assert rb.verify(batch) == 1
    assert not (out / ".verified").exists()


def test_verify_rejects_preset_verified_by(tmp_path, monkeypatch):
    """Only a human sets verified_by. A model setting it would be claiming its
    own output had been reviewed."""
    batch = "batch-98-test"
    out = tmp_path / "outbox" / batch
    out.mkdir(parents=True)
    doc_dir = tmp_path / "inbox" / "test"
    doc_dir.mkdir(parents=True)
    (doc_dir / "d.txt").write_text(DOC)

    (out / "findings.yaml").write_text(yaml.safe_dump({"findings": [{
        "field": "f", "value_mode": 170, "confidence": "industry",
        "document": "inbox/test/d.txt",
        "quote": "Approximately 150 to 200 flowers are required",
        "verified_by": "cooper",
    }]}))

    monkeypatch.setattr(rb, "OUTBOX", tmp_path / "outbox")
    monkeypatch.setattr(rb, "RESEARCH", tmp_path)
    monkeypatch.setattr(rb, "trial_build", lambda files: (True, "skipped"))
    assert rb.verify(batch) == 1


def test_verify_accepts_a_clean_batch(tmp_path, monkeypatch):
    batch = "batch-97-test"
    out = tmp_path / "outbox" / batch
    out.mkdir(parents=True)
    doc_dir = tmp_path / "inbox" / "test"
    doc_dir.mkdir(parents=True)
    (doc_dir / "d.txt").write_text(DOC)

    # Carries lo/hi as a real banded row would. The mode is interpolated
    # between the quoted bounds, which is legitimate -- the band is what the
    # quote grounds, not the midpoint. An earlier version of this fixture had a
    # bare mode of 170 and no bounds, which the band check correctly rejected.
    (out / "findings.yaml").write_text(yaml.safe_dump({"findings": [{
        "field": "flowers_per_gram", "value_lo": 150, "value_mode": 170,
        "value_hi": 200,
        "confidence": "industry", "document": "inbox/test/d.txt",
        "quote": "Approximately 150 to 200 flowers are required",
        "agreement": "2/2", "verified_by": None,
    }]}))

    monkeypatch.setattr(rb, "OUTBOX", tmp_path / "outbox")
    monkeypatch.setattr(rb, "RESEARCH", tmp_path)
    monkeypatch.setattr(rb, "trial_build", lambda files: (True, "audit clean"))

    assert rb.verify(batch) == 0
    assert (out / ".verified").exists()


def test_value_without_a_quote_is_rejected(tmp_path, monkeypatch):
    batch = "batch-96-test"
    out = tmp_path / "outbox" / batch
    out.mkdir(parents=True)
    (out / "findings.yaml").write_text(yaml.safe_dump({"findings": [
        {"field": "f", "value_mode": 170, "confidence": "industry"},
    ]}))
    monkeypatch.setattr(rb, "OUTBOX", tmp_path / "outbox")
    monkeypatch.setattr(rb, "RESEARCH", tmp_path)
    monkeypatch.setattr(rb, "trial_build", lambda files: (True, "skipped"))
    assert rb.verify(batch) == 1


# ---------------------------------------------------------------------------
# accept refuses unverified data
# ---------------------------------------------------------------------------

def test_accept_refuses_without_the_verified_marker(tmp_path, monkeypatch):
    batch = "batch-95-test"
    out = tmp_path / "outbox" / batch
    out.mkdir(parents=True)
    (out / "findings.yaml").write_text("findings: []\n")
    monkeypatch.setattr(rb, "OUTBOX", tmp_path / "outbox")
    monkeypatch.setattr(rb, "DATA", tmp_path / "data")
    with pytest.raises(SystemExit, match="has not passed verify"):
        rb.accept(batch)


# ---------------------------------------------------------------------------
# Consensus never averages
# ---------------------------------------------------------------------------

def test_agreement_is_recorded_when_models_match():
    a = {"value_mode": 170, "quote": "q"}
    b = {"value_mode": 170, "quote": "q"}
    merged, agree = consensus(a, b)
    assert agree == "2/2"
    assert merged["value_mode"] == 170


def test_disagreement_is_flagged_and_never_averaged():
    """Averaging two readings of one sentence invents a third number that no
    source states -- exactly what this project exists not to do."""
    a = {"value_mode": 150, "quote": "q"}
    b = {"value_mode": 200, "quote": "q"}
    merged, agree = consensus(a, b)
    assert "disagree" in agree
    assert merged["value_mode"] in (150, 200)
    assert merged["value_mode"] != 175


def test_one_model_silent_is_reported_honestly():
    merged, agree = consensus({"value_mode": 170}, None)
    assert merged["value_mode"] == 170
    assert agree.startswith("1/1")


def test_both_silent_yields_nothing():
    merged, agree = consensus(None, None)
    assert merged is None
    assert agree == "0/2"


# ---------------------------------------------------------------------------
# Spec parsing -- regression: five of six items were silently dropped
# ---------------------------------------------------------------------------

SPEC = """# Batch 42 — test

### Item 1 — first_field

| | |
|---|---|
| `unit` | widgets per thing |

**Question:** How many widgets per thing?

**Candidate URLs:**

- https://example.org/a — because
- https://example.org/b

### Item 2 — second_field

| | |
|---|---|
| `unit` | things per box |

**Question:** How many things per box?

**Candidate URLs:** as Item 1.

### Item 3 — third_field

**Question:** A question with no table row for unit.

**Candidate URLs:** as Item 1.
"""


def _spec(tmp_path):
    p = tmp_path / "batch-42-test.md"
    p.write_text(SPEC)
    return parse_spec(p)


def test_parse_spec_finds_every_item(tmp_path):
    """The bug this locks: items saying 'as Item 1' rather than repeating URLs
    were dropped, so batch-01-saffron parsed as 1 item instead of 6."""
    assert len(_spec(tmp_path)["items"]) == 3


def test_parse_spec_inherits_urls(tmp_path):
    items = _spec(tmp_path)["items"]
    assert items[1]["urls"] == items[0]["urls"]
    assert items[2]["urls"] == items[0]["urls"]
    assert len(items[0]["urls"]) == 2


def test_parse_spec_strips_the_item_number_from_the_field_name(tmp_path):
    """Was returning '1 — first_field' rather than 'first_field'."""
    assert [i["field"] for i in _spec(tmp_path)["items"]] == [
        "first_field", "second_field", "third_field"]


def test_parse_spec_trims_trailing_punctuation_from_urls(tmp_path):
    for u in _spec(tmp_path)["items"][0]["urls"]:
        assert not u.endswith((".", ",", ")", ";"))


def test_parse_spec_tolerates_a_missing_unit(tmp_path):
    assert _spec(tmp_path)["items"][2]["unit"] == ""


def test_parse_spec_yields_nothing_without_urls(tmp_path):
    """Batches 02 and 03 deliberately have no URLs. Zero items is correct and
    must fail loudly rather than fetch nothing and look successful."""
    p = tmp_path / "batch-43-empty.md"
    p.write_text("### Item 1 — f\n\n**Question:** Q?\n\nNo urls here.\n")
    assert parse_spec(p)["items"] == []


# ---------------------------------------------------------------------------
# value_in_quote -- the check that catches what quote verification cannot
# ---------------------------------------------------------------------------

def test_value_must_appear_in_the_quote():
    """The real failure this was added for: a run reported yield_per_acre = 10
    against the quote 'an annual yield of 8'. Verbatim, right document, wrong
    number. Quote verification proves a sentence exists; only this proves the
    sentence says the figure."""
    ok, why = rb.value_in_quote(10, "an annual yield of 8")
    assert not ok
    assert "does not appear" in why


def test_value_found_as_digits():
    assert rb.value_in_quote(3, "yields only three stigmas")[0]
    assert rb.value_in_quote(150, "about 150 flowers per gram")[0]


def test_value_found_across_thousands_separators():
    """Sources write 210,000; a model reports 210000. Same claim."""
    assert rb.value_in_quote(
        210000, "it takes 210,000 stigmas to make 1 pound")[0]


def test_value_found_as_a_word():
    """Sources say 'three stigmas' at least as often as '3'."""
    assert rb.value_in_quote(3, "Each blossom yields only three stigmas")[0]
    assert rb.value_in_quote(12, "a dozen wings on the plate")[0]


def test_derived_value_is_flagged_not_silently_accepted():
    """'lose 80% of their weight' supports 0.2 retained -- but only by
    inversion, which is a DERIVATION. Derived figures need the `derived` grade,
    which COOPER may not assign, so a human has to record it."""
    ok, _ = rb.value_in_quote(0.2, "the stigmas lose 80% of their weight")
    assert not ok


def test_non_numeric_values_pass_through():
    assert rb.value_in_quote(None, "anything")[0]
    assert rb.value_in_quote("n/a", "anything")[0]


# ---------------------------------------------------------------------------
# unit_matches_field -- catches misattribution
# ---------------------------------------------------------------------------

def test_subject_mismatch_is_rejected():
    """The row that slipped through: flowers_per_gram_dried answered with a
    stigmas-per-pound figure. A crocus has three stigmas per flower, so the two
    differ by exactly the factor being measured."""
    ok, why = rb.unit_matches_field(
        "flowers_per_gram_dried", "stigmas per pound")
    assert not ok
    assert "different question" in why


def test_matching_subject_passes():
    assert rb.unit_matches_field("stigmas_per_pound", "stigmas per pound")[0]
    assert rb.unit_matches_field("wings_per_bird", "wings per bird")[0]


def test_denominator_difference_is_allowed():
    """Deliberately permitted: a spec may ask for 'whatever unit the source
    uses', so ounces instead of grams is a conversion, not a wrong answer.
    Only the SUBJECT of the count is treated as a contradiction."""
    assert rb.unit_matches_field(
        "flowers_per_gram_dried", "flowers per ounce")[0]


def test_unit_check_is_silent_when_it_cannot_tell():
    """No subject term in the field name means no contradiction to find. The
    check must not invent one."""
    assert rb.unit_matches_field("drying_mass_yield", "fraction retained")[0]
    assert rb.unit_matches_field("anything", "")[0]


# ---------------------------------------------------------------------------
# quote_looks_truncated -- a warning, not a failure
# ---------------------------------------------------------------------------

def test_truncated_quote_is_flagged():
    trunc, _ = rb.quote_looks_truncated("an annual yield of 8")
    assert trunc


def test_quote_ending_mid_phrase_is_flagged():
    assert rb.quote_looks_truncated("the stigmas are picked by hand and")[0]


def test_complete_sentence_is_not_flagged():
    assert not rb.quote_looks_truncated(
        "Each blossom yields only three stigmas, which must be picked by hand."
    )[0]


def test_empty_quote_is_not_flagged_as_truncated():
    """Empty quotes fail the earlier quote check; this one must not double-report."""
    assert not rb.quote_looks_truncated("")[0]


def test_band_is_grounded_if_any_bound_is_quoted():
    """A quote reading "150 to 200 flowers" legitimately supports lo=150,
    hi=200, mode=170 -- the mode is an interpolation within a quoted range,
    which is normal for a lo/mode/hi corpus. Requiring the mode itself to
    appear rejected every banded figure and broke a passing test."""
    row = {"value_lo": 150, "value_mode": 170, "value_hi": 200}
    assert rb.band_in_quote(row, "Approximately 150 to 200 flowers are required")[0]


def test_band_with_nothing_quoted_is_rejected():
    row = {"value_lo": 10, "value_mode": 10, "value_hi": 10}
    ok, why = rb.band_in_quote(row, "an annual yield of 8")
    assert not ok
    assert "derived" in why


def test_band_with_no_values_passes():
    assert rb.band_in_quote({"field": "x"}, "any text")[0]


# ---------------------------------------------------------------------------
# Non-numeric values -- the hole batch-04-honey found
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("junk", ["32 mg", "industry", "Several thousand",
                                  "2.6 million", True])
def test_non_numeric_values_are_rejected(junk):
    """value_in_quote is permissive about anything it cannot parse as a float,
    so before this check three junk rows passed the strongest gate in one run:
    a value of '32 mg' (string, and the wrong figure), a value of 'industry'
    (the confidence grade in the value field), and 'Several thousand' (prose).

    Every value_* field maps to a REAL column, so a value that will not become
    a float is not a figure at all."""
    ok, msg = rb.band_in_quote({"value_mode": junk}, "a quote mentioning 32 mg")
    assert not ok
    assert "not numbers" in msg


@pytest.mark.parametrize("good,quote", [
    ("60,000", "a colony of 60,000 workers"),
    ("60 000", "a colony of 60 000 workers"),
    (3, "exactly three stigmas"),
])
def test_numbers_written_the_way_sources_write_them_still_pass(good, quote):
    """Thousands separators are how sources actually print figures. Rejecting
    them would trade one false negative for a stream of false positives."""
    assert rb._is_number(good)
    assert rb.band_in_quote({"value_mode": good}, quote)[0]


# ---------------------------------------------------------------------------
# Document filenames must be collision-free
# ---------------------------------------------------------------------------

def test_distinct_urls_get_distinct_document_names(tmp_path, monkeypatch):
    """The bug this catches destroyed evidence silently.

    batch-09 fetched three govinfo PDFs whose URLs share their first 47
    characters. The slug truncated at 48, so all three wrote to
    "https-www-govinfo-gov-content-pkg-cfr-2024-title" and the last fetch won:
    693,586 and 79,871 characters were downloaded, logged as fetched, and then
    deleted by the next fetch. The run reported 0 of 8 extractions and read as
    source scarcity.

    Worse than losing a figure: the inbox is what the gate checks quotes
    against, so a lost document makes any quote from it unverifiable.
    """
    import runner

    urls = [
        "https://www.govinfo.gov/content/pkg/CFR-2024-title9-vol2/pdf/"
        "CFR-2024-title9-vol2-part381.pdf",
        "https://www.govinfo.gov/content/pkg/CFR-2024-title7-vol3/pdf/"
        "CFR-2024-title7-vol3-part70.pdf",
        "https://www.govinfo.gov/content/pkg/CFR-2024-title9-vol2/pdf/"
        "CFR-2024-title9-vol2-sec381-90.pdf",
    ]
    # Shared prefix long enough to defeat any pure-truncation scheme.
    assert len({u[:48] for u in urls}) == 1

    seen = []
    monkeypatch.setattr(runner, "_FETCH_CACHE", {})
    monkeypatch.setattr(runner, "fetch_url",
                        lambda url, dest: seen.append(dest) or dest)
    for u in urls:
        runner.fetch_once(u, tmp_path)

    assert len(seen) == len(urls)
    assert len({p.name for p in seen}) == len(urls), (
        f"filenames collided: {[p.name for p in seen]}")
