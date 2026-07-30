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
DATA = ROOT / "data"

sys.path.insert(0, str(SRC))

HOST = "cooper"
REMOTE_ROOT = "C:/research"

# Grades that assert something about provenance rather than about a number.
# Neither is visible in a document's text, so neither is COOPER's to assign.
HUMAN_ONLY_GRADES = {"measured", "derived"}


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

    with tempfile.TemporaryDirectory() as tmp:
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
    marker = OUTBOX / batch / ".verified"
    if not marker.exists():
        raise SystemExit(
            f"{batch} has not passed verify. Run verify first -- accept "
            f"deliberately refuses to move unverified data into data/."
        )
    moved = []
    for f in candidate_files(batch):
        dst = DATA / f.name
        shutil.copy(f, dst)
        moved.append(dst.name)
    print(f"accepted {len(moved)} file(s) into data/:")
    for m in moved:
        print(f"  {m}")
    print("\nnow, on a Python 3.12 venv:")
    print("  python -m counting_chicken_wings.build")
    print("  python -m counting_chicken_wings.audit")
    print("  pytest -q")
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
