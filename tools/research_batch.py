"""Send research batches to COOPER, and gate what comes back.

    python tools/research_batch.py send   batch-01-saffron
    python tools/research_batch.py fetch  batch-01-saffron
    python tools/research_batch.py verify batch-01-saffron
    python tools/research_batch.py accept batch-01-saffron

`verify` is the reason this file exists. COOPER runs free local models that
cannot be trusted to cite honestly, so nothing they return is believed -- it is
checked. See docs/research/README.md for the contract.

The three checks, in order of how cheaply they catch a problem:

  1. GRADE      reject any row claiming `measured` or `derived`. Those are
                claims about provenance, invisible in a document's text, and
                a human's call.
  2. QUOTE      the quoted sentence must appear character-for-character in the
                document COOPER returned. A fabricated citation dies here,
                mechanically, with no judgement involved.
  3. AUDIT      build a throwaway database from data/ PLUS the candidate YAML
                and run the real audit. Catches unknown source slugs and
                anything the schema rejects.
"""

from __future__ import annotations

import argparse
import base64
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
RESEARCH = ROOT / "docs" / "research"
BATCHES = RESEARCH / "batches"
INBOX = RESEARCH / "inbox"
OUTBOX = RESEARCH / "outbox"
# Verified findings live here and ARE committed: a figure with a quote that
# survives verbatim matching is worth keeping even before it becomes corpus.
ACCEPTED = RESEARCH / "accepted"
DATA = ROOT / "data"

sys.path.insert(0, str(SRC))

HOST = "cooper"
REMOTE_ROOT = "C:/research"

# Grades that assert something about provenance rather than about a number.
# Neither is visible in a document's text, so neither is COOPER's to assign.
# Grades that assert something a model cannot check from the text in front of
# it, so none of them is COOPER's to assign.
#
# `study` was added 2026-07-29 on evidence rather than principle. The prompt
# already tells the model to use it "only if the document is a peer-reviewed
# journal article"; in a three-model A/B on a UC Master Gardeners WEB PAGE,
# qwen2.5-coder returned confidence "study" anyway. The gate let it through,
# because study was permitted.
#
# Deciding whether a document is peer-reviewed is a judgement about the
# document's provenance, not about its sentences -- the same reason `measured`
# and `derived` are human-only. The honey batch shows how sharp the distinction
# gets: Jaganathan & Mandal 2009 IS a peer-reviewed article, and the figure
# taken from it is uncited scene-setting in a paper about cancer cells. A model
# that reads "Journal" in a header cannot tell those apart, and neither can one
# that reads "Extension".
#
# COOPER may still assign `industry` and `estimate`. A human promotes.
HUMAN_ONLY_GRADES = {"measured", "derived", "study"}


# ---------------------------------------------------------------------------
# SSH, with the two traps that have already cost time
# ---------------------------------------------------------------------------

def ps(script: str, timeout: int = 600) -> subprocess.CompletedProcess:
    """Run a PowerShell script on COOPER without any quoting to mangle.

    Quoting through `ssh cooper "..."` is unreliable: cmd.exe strips single
    quotes and the local shell eats `$`. Base64-encoding the script as UTF-16LE
    and passing it to -EncodedCommand removes every layer that could mangle it.
    """
    # Progress records otherwise arrive as CLIXML and flood stdout over SSH.
    script = '$ProgressPreference = "SilentlyContinue"\n' + script
    b64 = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return subprocess.run(
        ["ssh", HOST, f"powershell -NoProfile -EncodedCommand {b64}"],
        capture_output=True, text=True, timeout=timeout,
    )


def scp(src: str, dst: str, timeout: int = 600) -> None:
    r = subprocess.run(["scp", "-q", "-r", src, dst],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise SystemExit(f"scp failed: {r.stderr.strip()}")


# ---------------------------------------------------------------------------
# Quote matching
# ---------------------------------------------------------------------------

def normalise(text: str) -> str:
    """Fold away differences that are not the model's fault.

    A quote must match the document's WORDS, not its typography. PDF extraction
    turns one space into three, curly quotes into straight ones and back, and
    breaks lines mid-sentence. Holding a model to those artifacts would reject
    honest quotes and teach us to distrust the gate.

    What is deliberately NOT folded: digits, letters, and their order. The
    number and its wording still have to be right.
    """
    text = unicodedata.normalize("NFKC", text)
    text = (text.replace("\u2018", "'").replace("\u2019", "'")
                .replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u2013", "-").replace("\u2014", "-")
                .replace("\u00a0", " "))
    return re.sub(r"\s+", " ", text).strip().lower()


# Terms that are mutually exclusive within a group. If the field name names one
# and the returned unit names a DIFFERENT one from the same group, the row is
# answering a different question than the one asked.
#
# Only the SUBJECT group is treated as a failure. Denominator units are
# deliberately not, because a spec may ask for "whatever unit the source uses" --
# ounces instead of grams is a conversion, not a wrong answer. Confusing
# stigmas with flowers is a wrong answer.
SUBJECT_TERMS = [
    "flower", "blossom", "stigma", "stamen", "thread", "bean", "pod",
    "egg", "wing", "bird", "chicken", "hen", "cow", "tree", "piece",
]

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "dozen": 12, "fifteen": 15, "twenty": 20, "hundred": 100,
    "thousand": 1000, "million": 1_000_000,
}


def _is_number(value) -> bool:
    """True only for something that will survive becoming a REAL column.

    `bool` is excluded deliberately: `float(True)` is 1.0, so a stray `true`
    would otherwise pass as the figure 1.
    """
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        # "60,000" and "60 000" are figures, written the way sources write
        # them. "32 mg" is not -- the unit belongs in `unit`, and letting it
        # ride here would re-open the hole this function exists to close.
        value = re.sub(r"(?<=\d)[,\s](?=\d)", "", value.strip())
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def band_in_quote(row: dict, quote: str) -> tuple[bool, str]:
    """A row is grounded if ANY of its lo/mode/hi appears in the quote.

    Not just the mode, and the distinction matters. A quote reading "150 to 200
    flowers" legitimately supports lo=150, hi=200, mode=170 -- the mode is an
    interpolation within a quoted range, which is normal and honest for a
    lo/mode/hi corpus. Demanding the mode itself appear would reject every
    banded figure, which is how this check first broke a passing test.

    What it still catches is a row where NOTHING in the band is in the text:
    `yield_per_acre: 10` against "an annual yield of 8", or a 0.2 derived by
    inverting a quoted "80%".
    """
    vals = [row.get(k) for k in ("value_lo", "value_mode", "value_hi")]
    vals = [v for v in vals if v is not None]
    if not vals:
        return True, ""

    # A figure has to be a NUMBER before it can be checked against a sentence,
    # and value_in_quote is permissive about anything it cannot parse -- so
    # without this, non-numeric junk sailed straight through the strongest
    # check in the gate. batch-04-honey produced three such rows in one run:
    #
    #   honey_per_bee_lifetime  value: '32 mg'            (a string, and the
    #                                                      wrong figure -- 32 mg
    #                                                      is a nectar load)
    #   colony_size             value: 'industry'         (the confidence word
    #                                                      landed in the value)
    #   forager_fraction        value: 'Several thousand'  (prose, not a figure)
    #
    # Every value_* field maps to a REAL column in schema.sql, so a value that
    # will not become a float is not a near-miss to be salvaged -- it is not a
    # figure at all. Rejected here rather than left for the build to trip over,
    # because the message can say what is actually wrong.
    bad = [v for v in vals if not _is_number(v)]
    if bad:
        shown = ", ".join(repr(v) for v in bad)
        return False, (
            f"value(s) {shown} are not numbers. A figure must be numeric -- "
            f"units belong in `unit`, and a model that puts prose or its own "
            f"confidence grade in a value field has not answered the question"
        )

    for v in vals:
        if value_in_quote(v, quote)[0]:
            return True, ""
    shown = ", ".join(f"{v:g}" if isinstance(v, (int, float)) else str(v)
                      for v in vals)
    return False, (
        f"none of the reported values ({shown}) appear in the quoted sentence. "
        f"If the figure was derived from what the quote says -- inverting an "
        f"'80% loss' into 0.2, say -- that is a `derived` claim and a human has "
        f"to record it as one"
    )


def value_in_quote(value, quote: str) -> tuple[bool, str]:
    """The reported figure must actually appear in the sentence quoted.

    The strongest of these checks, and the one that catches the failure quote
    verification cannot. A row reported `yield_per_acre: 10` against the quote
    "an annual yield of 8" -- the quote was real, verbatim, and from the right
    document, but it does not contain 10. Quote verification proves a sentence
    exists; only this proves the sentence says the number.

    Accepts digits with or without separators, and small numbers written as
    words, because sources say "three stigmas" as often as "3".
    """
    if value is None:
        return True, ""                     # nothing numeric to check
    try:
        v = float(value)
    except (TypeError, ValueError):
        return True, ""

    body = normalise(quote)
    # "210,000" and "210000" and "210 000" are the same claim.
    stripped = re.sub(r"(?<=\d)[,\s](?=\d)", "", body)

    candidates = {f"{v:g}"}
    if v == int(v):
        n = int(v)
        candidates |= {str(n), f"{n:,}"}
        for word, num in WORD_NUMBERS.items():
            if num == n:
                candidates.add(word)
    # 0.2 is often written "20%" or "80% loss"; accept the percentage form.
    if 0 < v < 1:
        candidates.add(f"{v * 100:g}")

    for c in candidates:
        if c in stripped or c in body:
            return True, ""
    return False, (f"value {value} does not appear in the quoted sentence "
                   f"(checked digits, separators and word forms)")


def unit_matches_field(field: str, unit: str) -> tuple[bool, str]:
    """Reject a row whose unit contradicts the subject its field names.

    Catches the misattribution that slipped through: `flowers_per_gram_dried`
    returned `unit: stigmas per pound`. Both the quote and the number were
    genuine -- they just answered a different question. A crocus has three
    stigmas per flower, so flowers and stigmas differ by exactly the factor the
    project is trying to measure.
    """
    if not unit:
        return True, ""
    f, u = field.lower(), unit.lower()
    in_field = {t for t in SUBJECT_TERMS if t in f}
    in_unit = {t for t in SUBJECT_TERMS if t in u}
    if in_field and in_unit and not (in_field & in_unit):
        return False, (f"field names {sorted(in_field)} but unit says "
                       f"{sorted(in_unit)} -- the row answers a different "
                       f"question than the field asks")
    return True, ""


def quote_looks_truncated(quote: str) -> tuple[bool, str]:
    """Warn when a quote stops mid-sentence.

    A fragment ending "an annual yield of 8" may have had its figure cut off,
    which makes it unreviewable even when it matches the document. A warning
    rather than a failure: plenty of legitimate quotes are clause fragments.
    """
    q = quote.strip()
    if not q:
        return False, ""
    if q[-1] in ".!?\"')":
        return False, ""
    if re.search(r"[\d]$|\b(and|or|to|of|per|from|with|about|the|a|an)$", q,
                 re.I):
        return True, "quote appears to stop mid-sentence"
    return False, ""


def quote_in_document(quote: str, document: Path) -> tuple[bool, str]:
    if not document.exists():
        return False, f"document not returned: {document.name}"
    if not quote or not quote.strip():
        return False, "empty quote"
    body = normalise(document.read_text(encoding="utf-8", errors="replace"))
    if normalise(quote) in body:
        return True, ""
    return False, "quote does not appear in the document"


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def candidate_files(batch: str) -> list[Path]:
    d = OUTBOX / batch
    if not d.exists():
        raise SystemExit(f"no results at {d} -- run fetch first")
    return sorted(p for p in d.glob("*.yaml"))


def rows_of(doc: dict):
    """Yield (path, row) for every dict in the document carrying a quote.

    Walks the structure rather than assuming a shape, because a batch may
    target product, loss_factor, nutrition or quality_defect and each nests
    differently. Anything with a `quote` key is a claim to be checked.
    """
    def walk(node, path):
        if isinstance(node, dict):
            if "quote" in node or "confidence" in node:
                yield path, node
            for k, v in node.items():
                yield from walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{path}[{i}]")
    yield from walk(doc, "")


def verify(batch: str) -> int:
    files = candidate_files(batch)
    if not files:
        raise SystemExit(f"no .yaml files in {OUTBOX / batch}")

    failures: list[str] = []
    checked = 0
    flagged = 0

    print(f"verifying {batch}\n")

    for f in files:
        try:
            doc = yaml.safe_load(f.read_text()) or {}
        except yaml.YAMLError as e:
            failures.append(f"{f.name}: unparseable YAML -- {e}")
            continue

        if "proposed_sources" in doc:
            n = len(doc["proposed_sources"] or [])
            print(f"  {f.name}: {n} proposed source(s) for human review")

        for path, row in rows_of(doc):
            if not isinstance(row, dict):
                continue
            label = f"{f.name}:{path or 'root'}"

            grade = row.get("confidence")
            if grade in HUMAN_ONLY_GRADES:
                failures.append(
                    f"{label}: claims '{grade}', which is a human-only grade"
                )
                continue

            if "quote" not in row:
                # Not every nested dict is a claim; only gate the ones that
                # carry a figure.
                if any(k.startswith("value") for k in row):
                    failures.append(f"{label}: has a value but no quote")
                continue

            checked += 1
            docref = row.get("document")
            if not docref:
                failures.append(f"{label}: quote with no document reference")
                continue

            ok, why = quote_in_document(row["quote"], RESEARCH / docref)
            if not ok:
                failures.append(f"{label}: {why}")
                continue

            # The quote is real. Now: does it actually answer the question?
            # Quote verification proves a sentence exists in the document; these
            # three prove the sentence says what the row claims it says. All
            # three were added after a run passed a genuine, verbatim quote that
            # answered a different question.
            field = str(row.get("field", ""))

            ok, why = band_in_quote(row, row["quote"])
            if not ok:
                failures.append(f"{label}: {why}")
                continue

            ok, why = unit_matches_field(field, str(row.get("unit") or ""))
            if not ok:
                failures.append(f"{label}: {why}")
                continue

            trunc, why = quote_looks_truncated(row["quote"])
            if trunc:
                flagged += 1
                print(f"  [needs_human] {label}: {why}")

            if row.get("verified_by") is not None:
                failures.append(
                    f"{label}: verified_by is pre-set -- only a human sets that"
                )
                continue

            agree = str(row.get("agreement", ""))
            if agree and not agree.startswith("2/2"):
                flagged += 1
                print(f"  [needs_human] {label}: models disagreed ({agree})")

    print(f"\n  {checked} quoted figure(s) checked, {flagged} flagged for review")

    # Check 3: the real audit, against data/ plus the candidates.
    print("\n  running build + audit with candidates merged in...")
    audit_ok, audit_msg = trial_build(files)
    print(f"  {audit_msg}")
    if not audit_ok:
        failures.append(f"audit failed with candidates merged: {audit_msg}")

    if failures:
        print(f"\nFAILED -- {len(failures)} problem(s):\n")
        for x in failures:
            print(f"  - {x}")
        print("\nNothing accepted. Fix or drop the offending rows and re-verify.")
        return 1

    print(f"\nPASSED. {batch} is safe to accept.")
    (OUTBOX / batch / ".verified").write_text("ok\n")
    return 0


def trial_build(files: list[Path]) -> tuple[bool, str]:
    """Build a throwaway DB from data/ plus the candidates, then audit it.

    Copies the corpus to a temp dir so the real data/ is never touched, and
    reuses the project's own build and audit rather than reimplementing the
    citation rule -- there must be exactly one definition of it.
    """
    from counting_chicken_wings import audit as audit_mod
    from counting_chicken_wings import build as build_mod

    # ignore_cleanup_errors because the audit's verdict is computed INSIDE this
    # block, so a teardown failure would discard a result that was already
    # correctly arrived at. build() and audit() both close their connections;
    # Windows can still fail to unlink trial.db transiently, and losing the
    # gate's answer to that is strictly worse than leaving a temp dir behind.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmpdir = Path(tmp)
        shutil.copytree(DATA, tmpdir / "data",
                        ignore=shutil.ignore_patterns("exports"))
        for f in files:
            # Land candidates under a prefix merge_files() already globs, so
            # this exercises the same path `accept` will use.
            shutil.copy(f, tmpdir / "data" / f.name)

        orig_data, orig_db = build_mod.DATA, build_mod.DEFAULT_DB
        db = tmpdir / "trial.db"
        try:
            build_mod.DATA = tmpdir / "data"
            build_mod.DEFAULT_DB = db
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                build_mod.build(db)
                rc = audit_mod.audit(db)
            return (rc == 0,
                    "audit clean" if rc == 0 else "audit reported uncited rows")
        except Exception as e:                      # noqa: BLE001
            return False, f"{type(e).__name__}: {e}"
        finally:
            build_mod.DATA, build_mod.DEFAULT_DB = orig_data, orig_db


# ---------------------------------------------------------------------------
# send / fetch / accept
# ---------------------------------------------------------------------------

def send(batch: str) -> int:
    spec = BATCHES / f"{batch}.md"
    if not spec.exists():
        raise SystemExit(f"no spec at {spec}")
    r = ps(f'New-Item -ItemType Directory -Force -Path "{REMOTE_ROOT}/batches" '
           f'| Out-Null; Write-Output ok')
    if r.returncode != 0:
        raise SystemExit(f"could not prepare COOPER: {r.stderr.strip()}")
    scp(str(spec), f"{HOST}:{REMOTE_ROOT}/batches/")
    scp(str(ROOT / "tools" / "cooper"), f"{HOST}:{REMOTE_ROOT}/")
    print(f"sent {batch} to {HOST}:{REMOTE_ROOT}")
    print("\non COOPER:")
    print(f"  python {REMOTE_ROOT}/cooper/runner.py {batch}")
    return 0


def fetch(batch: str) -> int:
    (OUTBOX / batch).mkdir(parents=True, exist_ok=True)
    INBOX.mkdir(parents=True, exist_ok=True)
    scp(f"{HOST}:{REMOTE_ROOT}/outbox/{batch}/*", str(OUTBOX / batch))
    # Documents come back too. Without the artifact there is nothing to check
    # a quote against and the gate is theatre.
    scp(f"{HOST}:{REMOTE_ROOT}/inbox/*", str(INBOX))
    print(f"fetched {batch} results and source documents")
    return 0


def accept(batch: str) -> int:
    """Promote verified findings to docs/research/accepted/. NOT into data/.

    An earlier version copied findings straight into data/ and claimed the job
    was done. It was not: build only reads files matching taxonomy*, loss_chain*
    and nutrition*, so a `findings.yaml` sitting there is ignored entirely. The
    audit passed because the file was never read, which is the most misleading
    way for something to appear to work.

    Findings are a research RESULT, not corpus. Turning `stigmas_per_flower: 3`
    into a `product` row with `is_anatomical_constant: 1` requires deciding what
    kind of thing it is and which yield mode applies -- schema judgement, and
    therefore deliberately a human's job, for the same reason grading a source
    is. Accepted findings are committed because a verified figure with a working
    quote is worth keeping; they simply are not live data yet.
    """
    marker = OUTBOX / batch / ".verified"
    if not marker.exists():
        raise SystemExit(
            f"{batch} has not passed verify. Run verify first -- accept "
            f"deliberately refuses to promote unverified findings."
        )

    ACCEPTED.mkdir(parents=True, exist_ok=True)
    promoted, rows = [], []
    for f in candidate_files(batch):
        dst = ACCEPTED / f"{batch}-{f.name}"
        shutil.copy(f, dst)
        promoted.append(dst)
        doc = yaml.safe_load(f.read_text()) or {}
        rows += [r for _, r in rows_of(doc)
                 if isinstance(r, dict) and "quote" in r]

    print(f"promoted {len(promoted)} file(s) to {ACCEPTED.relative_to(ROOT)}:")
    for p in promoted:
        print(f"  {p.name}")

    print(f"\n{len(rows)} verified figure(s). These are NOT yet in the corpus.")
    print("\nTo make them live, a human decides the schema shape and writes the"
          "\nrows into a prefixed file the build actually reads:\n")
    for r in rows:
        grade = r.get("confidence", "?")
        note = ""
        if grade == "estimate":
            note = "  <- consider promoting; only a human may"
        print(f"  {r.get('field','?'):<32} {r.get('value_mode')} "
              f"{r.get('unit','')} [{grade}]{note}")

    print("\n  1. choose the target: data/taxonomy_<subject>.yaml (species,")
    print("     product) or data/loss_chain_<subject>.yaml (loss stages)")
    print("  2. add the source to data/sources.yaml -- the figure cannot ship")
    print("     without it, and the build will refuse")
    print("  3. set confidence deliberately; COOPER cannot exceed 'industry'")
    print("  4. then: build, audit, pytest -q on a Python 3.12 venv")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="research_batch")
    p.add_argument("action", choices=["send", "fetch", "verify", "accept"])
    p.add_argument("batch")
    a = p.parse_args(argv if argv is not None else sys.argv[1:])
    return {"send": send, "fetch": fetch,
            "verify": verify, "accept": accept}[a.action](a.batch)


if __name__ == "__main__":
    raise SystemExit(main())
