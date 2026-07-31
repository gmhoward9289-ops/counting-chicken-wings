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
    assert why  # rejected WITH a reason, whatever wording it uses


def test_missing_document_is_rejected(tmp_path):
    """No artifact means nothing to check against, so the gate must fail
    rather than pass by default."""
    ok, why = rb.quote_in_document("anything", tmp_path / "absent.txt")
    assert not ok
    assert "absent.txt" in why  # names the document it could not find


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
    assert "10" in why  # names the value it rejected


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
    assert "flower" in why and "stigma" in why  # names both subjects


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
    # Assert on the IDENTIFIER, never the prose. This assertion used to read
    # `assert "derived" in why`, and #31 broke it by rewording the message to
    # explain bounds -- a change that made the tool better and the test fail.
    # A rejection has to name the value it rejected; how it explains itself is
    # the author's business.
    assert "10" in why


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
    assert repr(junk) in msg or str(junk) in msg  # names the offending value


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


# ---------------------------------------------------------------------------
# Bot walls -- a 200 with a doorman behind it
#
# Every number below is measured, not invented. PMC's interstitial is quoted
# from batch-05-milk; the matched pairs are from batch-05 (Mac vs COOPER) and
# batch-08 (silk, four sources, zero delta on all four).
# ---------------------------------------------------------------------------

PMC_WALL = (
    "Checking your browser - reCAPTCHA Checking your browser before accessing "
    "pmc.ncbi.nlm.nih.gov ... Click here if you are not automatically "
    "redirected after 5 seconds."
)


def test_the_pmc_interstitial_is_recognised():
    """167 characters, HTTP 200, logged by the runner as a successful fetch of
    a 41,579-character journal article."""
    walled, why = rb.looks_like_interstitial(PMC_WALL)
    assert walled
    assert "recaptcha" in why


def test_a_long_document_mentioning_javascript_is_not_an_interstitial():
    """Real pages carry <noscript>Please enable JavaScript</noscript> in their
    chrome with the whole article underneath. Flagging those would make the
    check noise, and noise gets ignored."""
    body = "Please enable JavaScript. " + ("Fluid milk production rose. " * 400)
    assert len(body) > rb.INTERSTITIAL_MAX_CHARS
    assert not rb.looks_like_interstitial(body)[0]


def test_a_short_body_with_no_marker_is_not_flagged_as_an_interstitial():
    """batch-05's AMS Class III worksheet was 2,039 chars of real content."""
    assert not rb.looks_like_interstitial("Class III price factors: 17.34")[0]


def test_the_measured_pmc_collapse_is_a_failure():
    verdict, why = rb.host_delta_verdict(41579, 167)
    assert verdict == "fail"
    assert "41,579" in why and "167" in why


@pytest.mark.parametrize("local,remote", [
    (12947, 12947), (62520, 62520), (3194, 3194), (30469, 30469),
    (39883, 39883), (34661, 34656),          # batch-05, six of seven HTML
    (16299, 16299), (49272, 49272), (6849, 6849), (1479, 1479),   # batch-08
])
def test_measured_matching_pairs_stay_quiet(local, remote):
    """Eleven real cross-host pairs. If any of these fires, the threshold is
    wrong and the check will be ignored within a week."""
    assert rb.host_delta_verdict(local, remote)[0] == "ok"


def test_a_remote_fetch_that_failed_outright_is_a_failure():
    assert rb.host_delta_verdict(41579, None)[0] == "fail"


def test_ratios_are_not_computed_for_tiny_local_documents():
    """A 300-character local fetch is already too small for its ratio to mean
    anything; the local half reports on it separately."""
    assert rb.host_delta_verdict(300, 60)[0] == "ok"


def test_a_url_dead_on_both_hosts_is_left_to_the_dead_list():
    """Not a wall -- a wall is a DIFFERENCE between the hosts. Double-reporting
    one broken URL as two problems teaches people to skim the output."""
    assert rb.host_delta_verdict(None, 167)[0] == "ok"


# ---------------------------------------------------------------------------
# scout -- must fetch on COOPER, and must never claim to have done so when it
# did not
# ---------------------------------------------------------------------------

SCOUT_SPEC = """# Batch 44 — scout

### Item 1 — walled_field

| | |
|---|---|
| `unit` | pounds |

**Question:** How much?

Quote: "the daily maximum is not defined by physiology alone"

**Candidate URLs:**

- https://pmc.example.org/articles/PMC10289513/
"""

GOOD_BODY = ("Gross 2023. " * 300 +
             "the daily maximum is not defined by physiology alone. " +
             "More text. " * 300)


def _scout_env(tmp_path, monkeypatch, remote):
    """Wire scout to a one-URL spec, a local fetch that succeeds, and whatever
    COOPER is being made to do this time."""
    import runner

    batches = tmp_path / "batches"
    batches.mkdir()
    (batches / "batch-44-scout.md").write_text(SCOUT_SPEC)
    monkeypatch.setattr(rb, "BATCHES", batches)
    monkeypatch.setattr(rb, "RESEARCH", tmp_path)

    def fake_fetch_once(url, doc_dir):
        doc_dir.mkdir(parents=True, exist_ok=True)
        p = doc_dir / "doc.txt"
        p.write_text(GOOD_BODY, encoding="utf-8")
        return p

    monkeypatch.setattr(runner, "fetch_once", fake_fetch_once)
    monkeypatch.setattr(rb, "remote_fetch", remote)
    return "batch-44-scout"


def test_scout_fails_when_cooper_serves_a_wall(tmp_path, monkeypatch):
    """The batch-05 case end to end: reachable and quoted from the Mac, 167
    characters of reCAPTCHA from COOPER. The old scout printed "Safe to send"."""
    batch = _scout_env(
        tmp_path, monkeypatch,
        lambda urls, b, **kw: ({u: {"chars": len(PMC_WALL), "head": PMC_WALL,
                                    "error": None} for u in urls}, None))
    assert rb.scout(batch) == 1


def test_scout_fails_on_a_size_collapse_with_no_known_marker(tmp_path,
                                                             monkeypatch):
    """A wall that says nothing recognisable is still a wall. The delta is the
    signal, and it does not depend on knowing the vendor's wording."""
    body = "Please sign in to continue." * 5
    batch = _scout_env(
        tmp_path, monkeypatch,
        lambda urls, b, **kw: ({u: {"chars": len(body), "head": body,
                                    "error": None} for u in urls}, None))
    assert rb.scout(batch) == 1


def test_scout_does_not_pass_when_cooper_is_unreachable(tmp_path, monkeypatch):
    """The single most important assertion in this file's newest section.

    A check that reports success when it never ran is how batch-05 was cleared
    to send. Exit 2 says "did not run"; it is deliberately not 0.
    """
    batch = _scout_env(tmp_path, monkeypatch,
                       lambda urls, b, **kw: ({}, "ssh: connect: timed out"))
    assert rb.scout(batch) == 2


def test_scout_passes_when_both_hosts_agree(tmp_path, monkeypatch):
    batch = _scout_env(
        tmp_path, monkeypatch,
        lambda urls, b, **kw: ({u: {"chars": len(GOOD_BODY),
                                    "head": GOOD_BODY[:2000], "error": None}
                                for u in urls}, None))
    assert rb.scout(batch) == 0


def test_scout_still_fails_a_missing_quote_when_the_hosts_agree(tmp_path,
                                                               monkeypatch):
    """batch-08's bows-n-ties page fetched to 7,195 chars on BOTH hosts, ending
    mid-word, with the cited figure absent. The cross-host comparison is happy
    with it. The host check must not be allowed to short-circuit the quote
    check -- the two catch different failures."""
    import runner
    truncated = "Silkworms are reared on mulberry. " * 30 + "The average wor"
    batch = _scout_env(
        tmp_path, monkeypatch,
        lambda urls, b, **kw: ({u: {"chars": len(truncated),
                                    "head": truncated, "error": None}
                                for u in urls}, None))
    def fetch_truncated(url, doc_dir):
        doc_dir.mkdir(parents=True, exist_ok=True)
        p = doc_dir / "doc.txt"
        p.write_text(truncated, encoding="utf-8")
        return p

    monkeypatch.setattr(runner, "fetch_once", fetch_truncated)
    assert rb.scout(batch) == 1


# ---------------------------------------------------------------------------
# quote_lacks_basis -- a figure whose basis cannot be read off its own quote
# ---------------------------------------------------------------------------

def test_the_batch_09_egg_row_is_flagged():
    """"Eggs, 5.1, 1.3%" was a share of total food-loss calories, stored as an
    egg loss rate. Verbatim, correctly located, wrong by about 20x."""
    bare, why = rb.quote_lacks_basis("Eggs, 5.1, 1.3%")
    assert bare
    assert "table row" in why


def test_the_batch_05_milk_table_row_is_flagged():
    """One ERS row severed from the header that said which column was retail
    and which was consumer. Two stages were stored as one band."""
    assert rb.quote_lacks_basis("Fluid milk 109 13 12 22 20 35 32")[0]


@pytest.mark.parametrize("quote", [
    "For example, Joe Dairyman has a herd of 110 Holstein cows in South "
    "Carolina with a rolling herd average for milk of 20,501 pounds.",
    "Each blossom yields only three stigmas, which must be picked by hand.",
    "about 170 flowers per gram of dried saffron",
    "123.61 litres in 24 hours",
    "U.S. farmers had 9.3 million milk cows at",
    "Approximately 150 to 200 flowers are required",
])
def test_legitimate_quotes_are_not_flagged_as_bare_table_rows(quote):
    """A gate that cries wolf gets ignored, which is the disease this check is
    supposed to cure rather than spread."""
    assert not rb.quote_lacks_basis(quote)[0]


def test_a_bare_row_is_a_warning_and_not_a_failure(tmp_path, monkeypatch):
    """It must reach a human, not stop the batch: some legitimate figures do
    live in tables, and quote_looks_truncated set this precedent."""
    out = tmp_path / "outbox" / "b"
    out.mkdir(parents=True)
    doc = tmp_path / "inbox" / "d.txt"
    doc.parent.mkdir(parents=True)
    doc.write_text("Dairy products 367 34 9 75 21 109 30\n"
                   "Fluid milk 109 13 12 22 20 35 32\n")
    (out / "findings.yaml").write_text(yaml.safe_dump({"findings": [{
        "field": "chain_loss", "value_lo": 12, "value_mode": 20,
        "unit": "percent", "confidence": "industry",
        "document": "inbox/d.txt",
        "quote": "Fluid milk 109 13 12 22 20 35 32",
    }]}))
    monkeypatch.setattr(rb, "OUTBOX", tmp_path / "outbox")
    monkeypatch.setattr(rb, "RESEARCH", tmp_path)
    monkeypatch.setattr(rb, "trial_build", lambda files: (True, "skipped"))

    assert rb.verify("b") == 0
    assert (out / ".verified").exists()


def test_remote_fetch_reports_rather_than_raises_when_ssh_is_missing(
        monkeypatch):
    """Degrading honestly is the whole contract: an empty result plus a reason,
    never an empty result that reads like agreement."""
    monkeypatch.setattr(rb.shutil, "which", lambda name: None)
    results, err = rb.remote_fetch(["https://example.org/a"], "batch-44-scout")
    assert results == {}
    assert err and "ssh" in err
