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
    """lo and hi must each appear in the quote; only mode may interpolate.

    A quote reading "150 to 200 flowers" legitimately supports lo=150, hi=200,
    mode=170 -- the mode is an interpolation within a quoted range, which is
    normal and honest for a lo/mode/hi corpus, and demanding the mode itself
    appear would reject every banded figure. That much was always true.

    What was too loose was accepting a row when ANY one value appeared. A bound
    is not an interpolation: lo and hi are claims the source made, so they have
    to be in the source. batch-08-silk returned lo=1000, mode=3000, hi=9000
    against "from 300 to 900 meters (1000 to 3000 feet) long" -- 9000 appears
    in no silk document -- and the old rule passed it on the strength of the
    other two.

    MEASURED BEFORE CHANGING, over every accepted findings file: saffron 4/4
    and maple 5/5 keep their verdicts, so this costs nothing already banked.

    And it is worth being precise about how narrow it is, because the two other
    bad rows from the same day are NOT reachable this way and it would be easy
    to imagine otherwise:

      - silk's shirt row stored 1700/1800/2000 from "It takes 1700 to 2000
        cocoons to make one silk dress (or about 1,000 cocoons for a silk
        shirt)". Every number is genuinely in the quote. The error is that they
        describe the dress.
      - ground beef stored 100/100/100 from "more than 100 cows can be used",
        flattening a hedged ceiling into a point value. 100 is in the quote.

    Both are semantic, and no arithmetic on the band reaches either. Those are
    the `Watch for` prompt's job, not this check's.
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

    lo, mode, hi = (row.get("value_lo"), row.get("value_mode"),
                    row.get("value_hi"))

    # lo and hi are BOUNDS, and a bound is a claim the source made. Only mode
    # may be interpolated, which is the whole reason the ANY rule existed.
    #
    # Under ANY, one fabricated bound rode along beside two real ones and the
    # gate saw nothing: batch-08-silk returned lo=1000, mode=3000, hi=9000
    # against "from 300 to 900 meters (1000 to 3000 feet) long", where 9000
    # appears in no silk document at all.
    for name, v in (("value_lo", lo), ("value_hi", hi)):
        if v is not None and not value_in_quote(v, quote)[0]:
            return False, (
                f"{name}={v:g} does not appear in the quoted sentence. lo and "
                f"hi are BOUNDS, and a bound is a claim the source made, so it "
                f"has to be in the source. Only mode may be interpolated. If "
                f"this bound came from reasoning on the quote rather than "
                f"reading it -- inverting an '80% loss' into 0.2, say -- that "
                f"is a `derived` or `estimate` claim, and a human has to "
                f"record it as one"
            )

    if mode is not None and not value_in_quote(mode, quote)[0]:
        if lo is None or hi is None:
            return False, (
                f"value_mode={mode:g} does not appear in the quoted sentence "
                f"and has no lo/hi band to interpolate within. If it was "
                f"derived from what the quote says -- inverting an '80% loss' "
                f"into 0.2, say -- that is a `derived` claim and a human has "
                f"to record it as one"
            )
        if not (float(lo) <= float(mode) <= float(hi)):
            return False, (
                f"value_mode={mode:g} does not appear in the quoted sentence "
                f"and falls outside its own band [{lo:g}, {hi:g}], so it is "
                f"neither quoted nor an interpolation"
            )
    return True, ""


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


def quote_lacks_basis(quote: str) -> tuple[bool, str]:
    """Warn when a quote is a bare table row -- numbers with no column label.

    Two batches have now been lost to a figure whose basis cannot be read off
    its own quote, both of them verbatim, both correctly located:

      - batch-09: `"Eggs, 5.1, 1.3%"` -- a share of total food-loss calories,
        stored as an egg loss rate. Wrong by roughly 20x.
      - batch-05-milk: `"Fluid milk 109 13 12 22 20 35 32"` -- one row of an
        ERS loss table, severed from the header eleven lines above that said
        which column was retail and which was consumer. Two sequential stages
        were stored as a single lo/hi band.

    Neither is catchable by quote matching: both sentences exist, and the
    numbers claimed are in them. What is missing is the prose that says what
    the numbers are OF.

    The rule is deliberately narrow -- at most two word-like tokens alongside
    at least two numeric ones. "Fluid milk 109 13 12 22 20 35 32" has two words
    and seven numbers; "Eggs, 5.1, 1.3%" has one and two. A real sentence
    carrying a figure ("123.61 litres in 24 hours", "about 170 flowers per
    gram") has three or more words and stays quiet. A warning rather than a
    failure, for the same reason `quote_looks_truncated` is one: a gate that
    cries wolf gets ignored, and some legitimate figures really do live in
    tables. A human decides whether the basis is legible.
    """
    q = quote.strip()
    if not q:
        return False, ""
    tokens = q.split()
    if len(tokens) < 3:
        return False, ""
    numeric = [t for t in tokens if re.fullmatch(r"[\d][\d.,%$/()\[\]:;-]*", t)]
    words = [t for t in tokens
             if re.search(r"[A-Za-z]{2,}", t) and t not in numeric]
    if len(numeric) >= 2 and len(words) <= 2:
        return True, ("quote reads as a bare table row: "
                      f"{len(numeric)} number(s) against {len(words)} word(s), "
                      "so the basis of the figure cannot be read off the quote")
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

            bare, why = quote_lacks_basis(row["quote"])
            if bare:
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


# ---------------------------------------------------------------------------
# Bot walls: what a fetch looks like when the answer is 200 and the body is a
# doorman
# ---------------------------------------------------------------------------

# Phrases that appear in an interstitial and essentially nowhere in a document
# that is actually about a subject. Matched only against SHORT bodies, because
# a real page may carry <noscript>Please enable JavaScript</noscript> in its
# chrome and still contain the whole article underneath.
INTERSTITIAL_MARKERS = (
    "recaptcha",
    "checking your browser",
    "enable javascript",
    "javascript is disabled",
    "cf-browser-verification",
    "cloudflare",
    "just a moment...",
    "attention required!",
    "verify you are human",
    "are you a robot",
    "access denied",
    "request unsuccessful",
    "ddos protection",
)

# A body under this many characters is too small to be the document a spec
# cites, so an interstitial marker inside it is the whole page rather than a
# fragment of one. PMC's wall was 167 characters; the smallest real document
# in batch-05 was 2,039.
INTERSTITIAL_MAX_CHARS = 1500

# Remote-over-local ratio below which the two hosts are not being served the
# same thing. Measured evidence sets this very loosely on purpose: across
# batch-05 and batch-08 eleven of twelve cross-host pairs agreed exactly or to
# within five characters, and the one wall collapsed 41,579 -> 167, a ratio of
# 0.004. Anything between 0.004 and ~1.0 is unobserved, so the threshold sits
# in a wide empty gap and fires on order-of-magnitude collapse rather than on
# the small differences a dynamic page legitimately produces.
COLLAPSE_RATIO = 0.25

# Below this, ratios stop meaning anything -- a 300-character local fetch is
# already too small to matter and its ratio is noise.
COLLAPSE_MIN_LOCAL_CHARS = 1000


def looks_like_interstitial(text: str,
                            total_chars: int | None = None) -> tuple[bool, str]:
    """True when a fetch is a doorman rather than a document.

    The dangerous case is not an error: FSIS 403s to COOPER and the runner says
    so. PMC returned HTTP 200 and 167 characters of "Checking your browser -
    reCAPTCHA", which every layer downstream treated as a successful fetch of
    Gross 2023.
    """
    n = len(text) if total_chars is None else total_chars
    if n > INTERSTITIAL_MAX_CHARS:
        return False, ""
    low = text.lower()
    for m in INTERSTITIAL_MARKERS:
        if m in low:
            return True, (f"body is {n} chars and contains {m!r} -- this is an "
                          f"interstitial, not the document")
    return False, ""


def host_delta_verdict(local_chars: int | None,
                       remote_chars: int | None) -> tuple[str, str]:
    """Compare one URL's local and remote fetch. Returns (verdict, why).

    Verdicts: "ok", "fail". A fetch that failed outright on COOPER is a
    failure, and so is one whose body collapses relative to the Mac's.
    """
    if remote_chars is None:
        return "fail", "COOPER could not fetch this URL at all"
    if local_chars is None:
        # The local side already reported this as dead; nothing to compare.
        return "ok", ""
    if (local_chars >= COLLAPSE_MIN_LOCAL_CHARS
            and remote_chars < COLLAPSE_RATIO * local_chars):
        pct = 100.0 * remote_chars / max(local_chars, 1)
        return "fail", (f"COOPER got {remote_chars:,} chars where this Mac got "
                        f"{local_chars:,} ({pct:.1f}%) -- the two hosts are not "
                        f"being served the same document")
    return "ok", ""


# The probe runs ON COOPER, importing the same runner.py the real run uses, so
# the fetch under test is the fetch that will happen. It prints one JSON object
# after a marker line; anything PowerShell or the console adds before that is
# ignored.
_PROBE_SOURCE = '''\
import json, sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import runner

urls = [u.strip() for u in
        Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if u.strip()]
doc_dir = Path(sys.argv[3])
out = {}
for u in urls:
    try:
        p = runner.fetch_once(u, doc_dir)
    except Exception as e:
        out[u] = {"chars": None, "head": "", "error": repr(e)}
        continue
    if p is None or not p.exists():
        out[u] = {"chars": None, "head": "", "error": "fetch returned nothing"}
        continue
    # Read as TEXT, and fold CRLF. COOPER writes Windows line endings, so a
    # byte count differs from the Mac's by exactly the line count on every
    # single document -- comparing bytes would flag everything.
    t = p.read_text(encoding="utf-8", errors="replace").replace("\\r\\n", "\\n")
    out[u] = {"chars": len(t), "head": t[:2000], "error": None}
print("---SCOUT-JSON---")
print(json.dumps(out))
'''


def remote_fetch(urls: list[str], batch: str,
                 timeout: int = 900) -> tuple[dict[str, dict], str | None]:
    """Fetch every URL ON COOPER with the same runner the real run uses.

    Returns (results, error). `error` is not None when the remote check could
    not be performed at all, and in that case the caller must report the check
    as NOT RUN. Reporting a check that never ran as a pass is the exact failure
    this whole file exists to prevent.

    Transport is the one `send` already uses: scp `tools/cooper/` to
    COOPER, then run PowerShell through `ps()` so no quoting can mangle
    anything.
    """
    if shutil.which("ssh") is None or shutil.which("scp") is None:
        return {}, "ssh/scp not available on this machine"

    remote_dir = f"{REMOTE_ROOT}/_scout/{batch}"
    try:
        r = ps(f'New-Item -ItemType Directory -Force -Path "{remote_dir}" '
               f'| Out-Null; Write-Output ok', timeout=120)
    except (subprocess.SubprocessError, OSError) as e:
        return {}, f"{type(e).__name__}: {e}"
    if r.returncode != 0:
        return {}, f"could not reach {HOST}: {(r.stderr or '').strip()}"

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "probe.py").write_text(_PROBE_SOURCE, encoding="utf-8")
        (tmp / "urls.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")
        try:
            scp(str(ROOT / "tools" / "cooper"), f"{HOST}:{REMOTE_ROOT}/",
                timeout=300)
            scp(str(tmp / "probe.py"), f"{HOST}:{remote_dir}/", timeout=120)
            scp(str(tmp / "urls.txt"), f"{HOST}:{remote_dir}/", timeout=120)
        except (SystemExit, subprocess.SubprocessError, OSError) as e:
            return {}, f"could not stage the probe on {HOST}: {e}"

    cmd = (f'python "{remote_dir}/probe.py" "{REMOTE_ROOT}/cooper" '
           f'"{remote_dir}/urls.txt" "{remote_dir}/docs"')
    try:
        r = ps(cmd, timeout=timeout)
    except (subprocess.SubprocessError, OSError) as e:
        return {}, f"probe did not complete on {HOST}: {type(e).__name__}: {e}"
    out = r.stdout or ""
    if "---SCOUT-JSON---" not in out:
        why = (r.stderr or out or "").strip().splitlines()
        return {}, ("probe produced no result on "
                    f"{HOST}: {why[-1] if why else 'no output'}")
    try:
        import json                                  # noqa: PLC0415
        results = json.loads(out.split("---SCOUT-JSON---", 1)[1].strip())
    except ValueError as e:
        return {}, f"probe output was not JSON: {e}"
    return results, None


def scout(batch: str) -> int:
    """Check every URL in a spec is reachable AND still carries its quote.

    Run this BEFORE send. It exists because "confirmed 200 with the figure
    present" turned out to mean nothing when confirmed in the wrong tool, and
    the two ways that goes wrong are invisible from a browser:

      - batch-08-silk cited bows-n-ties for "120 to 130 cocoons". Real sentence,
        live page. COOPER's fetch of it contains no 120 and no 130 -- the figure
        is rendered by JavaScript. Both models correctly returned nothing, and
        the run read as model weakness rather than a dead source.
      - batch-06 cited fsis.usda.gov. Every path 403s to this fetcher while a
        browser sails through.

    So the check has to use the SAME code that will do the real fetch, and it
    has to look for the figure, not just a 200. A spec's `Quote:` lines are
    exactly the claim being made, so they are what gets verified.

    An earlier version of this docstring claimed reachability "is a property of
    the fetcher and its user agent, not of the host running it, so this is
    faithful from either machine". batch-05-milk measured that and it is false.
    Same code, same user agent, minutes apart:

        pmc.ncbi.nlm.nih.gov/articles/PMC10289513/
            Mac     41,579 chars -- Gross 2023
            COOPER     167 chars -- "Checking your browser - reCAPTCHA"

    Six of the seven other HTML fetches in that batch matched across the two
    hosts to within five characters, so this was one host-dependent bot wall
    rather than noise. Bot-walling keys on address and reputation, which belong
    to the host. The scout therefore fetches every URL ON COOPER and compares
    the result with a local fetch.

    TWO DIFFERENT FAILURES, AND NEITHER CHECK SUBSTITUTES FOR THE OTHER:

      - A BOT WALL is short and host-dependent. Only the cross-host comparison
        sees it: 41,579 vs 167 is a ratio of 0.004, and the collapse is the
        signal. A quote check would also miss the figure here, but it could not
        tell "walled" from "the source never said it".
      - JS TRUNCATION is long and host-INDEPENDENT. batch-08's bows-n-ties page
        came back at 7,195 characters on both machines, ending mid-word at
        "The average wor", with the cited "120 to 130 cocoons" nowhere in it.
        The cross-host comparison is perfectly happy with it -- both hosts got
        the same bytes -- and only the quote-presence check catches it.

    So a document can be long, fetch identically everywhere, and still be
    useless; and it can fetch fine here and be a doorman there. Both checks
    run, and a spec has to survive both.

    Exit codes: 0 clean, 1 the spec has a problem, 2 the COOPER half of the
    check DID NOT RUN. 2 is not a pass. If COOPER is unreachable this reports
    what it could not do rather than reporting success, because a check that
    claims to have run when it did not is the failure mode that produced
    batch-05 in the first place.
    """
    spec = BATCHES / f"{batch}.md"
    if not spec.exists():
        raise SystemExit(f"no spec at {spec}")

    sys.path.insert(0, str(ROOT / "tools" / "cooper"))
    import runner                                    # noqa: PLC0415

    items = runner.parse_spec(spec)["items"]
    text = spec.read_text(encoding="utf-8")
    doc_dir = RESEARCH / "inbox" / f"_scout-{batch}"
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Quotes the spec claims, per item block, so a miss names the item.
    def flat(s: str) -> str:
        # Spec quotes are wrapped across markdown lines and the fetched text has
        # its own line breaks, so whitespace has to go before anything matches.
        return re.sub(r"\s+", " ", normalise(s)).strip()

    claims: dict[str, list[str]] = {}
    for block in re.split(r"^### Item\b", text, flags=re.M)[1:]:
        head = re.sub(r"^\s*\d+\s*[—–-]\s*", "",
                      block.splitlines()[0]).strip()
        # Stop at the next '###' heading. A block that is deliberately NOT an
        # Item -- batch-06 parks its FSIS-blocked figure that way -- otherwise
        # merges into the item above and its quote gets blamed on the wrong
        # field. Same trap the URL inheritance sets, one parser along.
        body = re.split(r"\n#{3}\s", block)[0]
        claims[head] = re.findall(r'Quote:\s*"([^"]{12,})"', body)

    seen: dict[str, str | None] = {}
    dead, unquoted, ok = [], [], 0

    for it in items:
        bodies = []
        for url in it["urls"]:
            if url not in seen:
                try:
                    p = runner.fetch_once(url, doc_dir)
                except Exception as e:               # noqa: BLE001
                    p = None
                    print(f"  FETCH-ERROR {type(e).__name__} {url}")
                seen[url] = (p.read_text(encoding="utf-8", errors="replace")
                             if p and p.exists() else None)
            if seen[url] is None:
                dead.append((it["field"], url))
            else:
                ok += 1
                bodies.append((url, flat(seen[url])))

        # A quote lives in ONE of the item's sources, not all of them, so an
        # item is satisfied if any document carries it. Match on a prefix
        # rather than the whole sentence: the failure worth catching is a
        # figure that is absent entirely, and demanding the full sentence just
        # punishes a spec that trimmed a trailing clause.
        for q in claims.get(it["field"], []):
            probe = flat(q)[:50]
            if bodies and not any(probe in b for _u, b in bodies):
                unquoted.append((it["field"], probe,
                                 ", ".join(u for u, _b in bodies)))

    print(f"\nscouted {batch} locally: {len(seen)} distinct URL(s), "
          f"{ok} reachable, {len(dead)} dead")
    for field, url in dead:
        print(f"  [DEAD]     {field}: {url}")
    for field, q, url in unquoted:
        print(f"  [NO-QUOTE] {field}: {q!r}...")
        print(f"             not in what the fetcher retrieves from {url}")

    walled: list[tuple[str, str]] = []

    # A wall can also be served to THIS machine. Cheap to check, and it makes
    # the local half of the scout honest on its own terms.
    for url, body in seen.items():
        if body is None:
            continue
        inter, why = looks_like_interstitial(body)
        if inter:
            walled.append((url, f"local fetch: {why}"))

    # --- the COOPER half -------------------------------------------------
    print(f"\nfetching the same {len(seen)} URL(s) on {HOST} "
          f"(the host that will do the real run)...")
    results, err = remote_fetch(list(seen), batch)

    if err is not None:
        print(f"\n  REMOTE CHECK DID NOT RUN: {err}")
        print(f"\n{batch}: the local half is "
              f"{'CLEAN' if not (dead or unquoted or walled) else 'NOT clean'}, "
              f"and the {HOST} half was not performed.")
        for url, why in walled:
            print(f"  [WALLED]   {url}\n             {why}")
        print("\nThis is NOT a pass. batch-05-milk was cleared by a Mac-only "
              f"scout and then lost its best source to a reCAPTCHA served only "
              f"to {HOST}. Bring {HOST} up and re-scout before sending.")
        return 2

    for url in seen:
        r = results.get(url)
        if r is None:
            walled.append((url, f"{HOST} returned no result for this URL"))
            continue
        local_chars = len(seen[url]) if seen[url] is not None else None
        remote_chars = r.get("chars")
        head = r.get("head") or ""
        lc = f"{local_chars:,}" if local_chars is not None else "dead"
        rc = f"{remote_chars:,}" if remote_chars is not None else "dead"
        print(f"  {lc:>10} local  {rc:>10} {HOST}   {url}")

        inter, why = looks_like_interstitial(head, remote_chars)
        if inter:
            walled.append((url, f"{HOST} fetch: {why}"))
            continue
        verdict, why = host_delta_verdict(local_chars, remote_chars)
        if verdict == "fail":
            walled.append((url, why))

    for url, why in walled:
        print(f"  [WALLED]   {url}\n             {why}")

    if dead or unquoted or walled:
        print("\nFix the spec before sending. A dead URL wastes a run; a URL "
              "whose quote is absent invites a confident answer from the "
              f"wrong sentence; a URL that collapses on {HOST} returns a "
              "doorman with a 200 on it and is logged as a successful fetch.")
        return 1
    print(f"\nEvery URL reachable from this Mac AND from {HOST}, sizes agree, "
          "and every claimed quote is present. Safe to send.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="research_batch")
    p.add_argument("action",
                   choices=["scout", "send", "fetch", "verify", "accept"])
    p.add_argument("batch")
    a = p.parse_args(argv if argv is not None else sys.argv[1:])
    return {"scout": scout, "send": send, "fetch": fetch,
            "verify": verify, "accept": accept}[a.action](a.batch)


if __name__ == "__main__":
    raise SystemExit(main())
