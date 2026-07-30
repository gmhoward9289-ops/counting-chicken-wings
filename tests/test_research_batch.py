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

import research_batch as rb            # noqa: E402
from runner import consensus, sanitize  # noqa: E402


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
    assert rb.HUMAN_ONLY_GRADES == {"measured", "derived"}


@pytest.mark.parametrize("grade", ["measured", "derived"])
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

    (out / "findings.yaml").write_text(yaml.safe_dump({"findings": [{
        "field": "flowers_per_gram", "value_mode": 170,
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
