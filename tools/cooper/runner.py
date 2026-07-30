"""Runs ON COOPER. Fetch, retrieve, extract, self-audit -- all on free models.

    python C:/research/cooper/runner.py batch-01-saffron

Everything here is deliberately dependency-light: stdlib plus PyYAML, calling
`ollama` as a subprocess. COOPER is a Windows box with Python 3.14 and no
project venv, and this script should keep working when the chicken project's
own dependencies change.

Its output is not trusted by anything downstream. `tools/research_batch.py
verify` re-checks every quote against the documents this script returns, which
is why fetched documents are written to inbox/ and kept.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required on COOPER: python -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
OUTBOX = ROOT / "outbox"
BATCHES = ROOT / "batches"

# Measured on COOPER 2026-07-29, and the numbers assign the roles.
#
# qwen2.5-coder:7b  15.6s, returned exactly "170" -- no preamble, parseable.
# gemma4-32k        11.2s, correct but wrapped in a reasoning trace AND ANSI
#                   control codes. Only worth its 32k context on long docs.
EXTRACTOR = "qwen2.5-coder:7b"
LONG_CONTEXT = "gemma4-32k"
EMBEDDER = "nomic-embed-text"

# Chunk small enough that the chunk, the instruction and the answer all fit
# well inside the smaller model's window with room to spare.
CHUNK_CHARS = 6000
CHUNK_OVERLAP = 400


# ---------------------------------------------------------------------------
# Output sanitising -- required, not optional
# ---------------------------------------------------------------------------

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# gemma4 wraps its answer in a visible reasoning trace. Captured verbatim from
# a real run rather than guessed at:
#   "Thinking... Thinking Process: 1. **Analyze the Request:** ...
#    5. **Final Answer Generation:** 170 ...done thinking.  170 \r"
DONE_THINKING = re.compile(r".*?\.\.\.\s*done\s+thinking\.", re.IGNORECASE | re.DOTALL)


def sanitize(raw: str) -> str:
    """Strip ANSI codes and any reasoning trace, returning just the answer.

    The trap this exists for: gemma4 prints the number TWICE -- once inside its
    reasoning ("the core numerical value stated is 170") and once as the real
    answer after "...done thinking.". A naive "first number in the output" regex
    picks up whichever appeared in the reasoning, which may not be the answer at
    all. So cut everything through the end-of-thinking marker rather than trying
    to parse around it.
    """
    if not raw:
        return ""
    text = ANSI.sub("", raw).replace("\r", "\n")
    # Only cut if the marker is present; qwen has no trace and must pass through.
    if "done thinking" in text.lower():
        text = DONE_THINKING.sub("", text, count=1)
    return text.strip()


def ollama(model: str, prompt: str, timeout: int = 300) -> str:
    """Call a local model. Free, so retries cost only time."""
    try:
        r = subprocess.run(
            ["ollama", "run", model],
            input=prompt, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return ""
    return sanitize(r.stdout or "")


# ---------------------------------------------------------------------------
# Fetch and chunk
# ---------------------------------------------------------------------------

def fetch_url(url: str, dest: Path) -> Path | None:
    """Save a URL to disk. The artifact is the evidence, so it must persist."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "counting-chicken-wings/research"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
    except Exception as e:                          # noqa: BLE001
        print(f"    fetch failed: {url} -- {type(e).__name__}: {e}")
        return None

    if url.lower().endswith(".pdf") or body[:4] == b"%PDF":
        pdf = dest.with_suffix(".pdf")
        pdf.write_bytes(body)
        txt = pdf.with_suffix(".txt")
        # pdftotext if present; otherwise keep the PDF and say so, rather than
        # pretending we extracted text.
        try:
            subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)],
                           capture_output=True, timeout=120, check=True)
            print(f"    fetched + extracted {txt.name}")
            return txt
        except Exception:                           # noqa: BLE001
            print(f"    fetched {pdf.name} but no pdftotext -- text not extracted")
            return None

    text = body.decode("utf-8", errors="replace")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text,
                  flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    dest = dest.with_suffix(".txt")
    dest.write_text(text, encoding="utf-8")
    print(f"    fetched {dest.name} ({len(text):,} chars)")
    return dest


def chunks(text: str) -> list[str]:
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + CHUNK_CHARS])
        i += CHUNK_CHARS - CHUNK_OVERLAP
    return out


# ---------------------------------------------------------------------------
# Retrieval -- free, via nomic-embed-text
# ---------------------------------------------------------------------------

OLLAMA_API = "http://localhost:11434/api/embeddings"


def embed(text: str) -> list[float] | None:
    """Embed via the HTTP API, not the CLI.

    `ollama embed` does not exist in ollama 0.32.5, which is what COOPER runs --
    verified, after an earlier version of this function called it and would have
    silently fallen back to keyword matching. The fallback would have looked like
    "the embedder is unavailable" when in fact it was reachable the whole time,
    just at a different address. The HTTP API is stable across versions.
    """
    try:
        body = json.dumps({"model": EMBEDDER, "prompt": text[:8000]}).encode()
        req = urllib.request.Request(
            OLLAMA_API, data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        vec = data.get("embedding")
        return vec if isinstance(vec, list) and vec else None
    except Exception:                               # noqa: BLE001
        return None


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def best_chunks(question: str, cs: list[str], k: int = 3) -> list[str]:
    """Rank chunks by embedding similarity, falling back to keyword overlap.

    The fallback matters: if the embedder is unavailable the batch should still
    run, just less precisely. Silently returning nothing would look like "the
    document does not contain it", which is a different and wrong conclusion.
    """
    qv = embed(question)
    if qv:
        scored = []
        for c in cs:
            cv = embed(c)
            if cv:
                scored.append((cosine(qv, cv), c))
        if scored:
            scored.sort(key=lambda t: t[0], reverse=True)
            return [c for _, c in scored[:k]]

    print("    (embedder unavailable, falling back to keyword overlap)")
    words = {w for w in re.findall(r"[a-z]{4,}", question.lower())}
    ranked = sorted(
        cs, reverse=True,
        key=lambda c: len(words & set(re.findall(r"[a-z]{4,}", c.lower()))),
    )
    return ranked[:k]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

PROMPT = """You extract one figure from a source document. Reply with JSON only.

RULES, and breaking any of them makes the answer useless:
- The "quote" MUST be copied character-for-character from the text below. It is
  checked against the document automatically. Do not paraphrase or tidy it.
- If the text does not contain the figure, reply {{"found": false}}. Guessing is
  worse than not answering.
- Never use confidence "measured" or "derived". Only "industry", "estimate", or
  "study" if the document is a peer-reviewed journal article.

QUESTION: {question}
UNIT WANTED: {unit}

TEXT:
{text}

JSON with keys: found, value_lo, value_mode, value_hi, unit, confidence, quote
"""


def extract(question: str, unit: str, text: str, model: str) -> dict | None:
    raw = ollama(model, PROMPT.format(question=question, unit=unit, text=text))
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return d if d.get("found") else None


def consensus(a: dict | None, b: dict | None) -> tuple[dict | None, str]:
    """Two models, two families, so they fail differently.

    Disagreement is never averaged. Averaging two different readings of one
    sentence invents a third number that no source states, which is precisely
    what this project exists not to do.
    """
    if a and b:
        va, vb = a.get("value_mode"), b.get("value_mode")
        try:
            same = abs(float(va) - float(vb)) < 1e-9
        except (TypeError, ValueError):
            same = va == vb
        return (a, "2/2") if same else (a, f"1/2 disagree: {va} vs {vb}")
    if a:
        return a, "1/1 (second model returned nothing)"
    if b:
        return b, "1/1 (first model returned nothing)"
    return None, "0/2"


# ---------------------------------------------------------------------------
# Batch spec parsing -- deliberately forgiving
# ---------------------------------------------------------------------------

def parse_spec(path: Path) -> dict:
    """Pull items out of the markdown spec.

    Kept loose on purpose: the spec is a human document first. An item needs a
    Question and at least one URL; everything else is optional.
    """
    text = path.read_text(encoding="utf-8")
    items: list[dict] = []
    inherited: list[str] = []

    for block in re.split(r"^### Item\b", text, flags=re.M)[1:]:
        lines = block.splitlines()
        header = lines[0] if lines else ""

        q = re.search(r"\*\*Question:\*\*\s*(.+)", block)
        if not q:
            continue

        # Strip the "1 — " / "1 - " prefix off the heading so the field name is
        # the field name, not the field name with an item number glued to it.
        field = re.sub(r"^\s*\d+\s*[—–-]\s*", "", header).strip()

        unit = re.search(r"\|\s*`?unit`?\s*\|\s*([^|]+)\|", block, re.I)

        urls = [u.rstrip(").,;")
                for u in re.findall(r"^\s*[-*]\s*(https?://\S+)", block,
                                    flags=re.M)]
        if urls:
            inherited = urls
        else:
            # Specs written for humans say "Candidate URLs: as Item 1" rather
            # than repeating three long URLs six times. An earlier version
            # required URLs per item and silently dropped five of six items in
            # batch-01 -- caught only because the parser was run before the
            # batch. Inherit from the previous item that listed any.
            urls = inherited
            if not urls:
                continue

        items.append({
            "field": field,
            "question": q.group(1).strip(),
            "unit": unit.group(1).strip() if unit else "",
            "urls": urls,
        })
    return {"items": items}


def run(batch: str) -> int:
    spec_path = BATCHES / f"{batch}.md"
    if not spec_path.exists():
        sys.exit(f"no spec at {spec_path}")

    subject = batch.split("-", 2)[-1]
    doc_dir = INBOX / subject
    out_dir = OUTBOX / batch
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = parse_spec(spec_path)
    if not spec["items"]:
        sys.exit("no items found in spec -- each needs **Question:** and a URL")

    print(f"{batch}: {len(spec['items'])} item(s)\n")
    results, report = [], []

    for n, item in enumerate(spec["items"], 1):
        print(f"[{n}/{len(spec['items'])}] {item['field']}")
        for url in item["urls"]:
            doc = fetch_url(url, doc_dir / f"{n:02d}-{re.sub(r'[^a-z0-9]+', '-', url.lower())[:40]}")
            if not doc:
                continue

            text = doc.read_text(encoding="utf-8", errors="replace")
            cs = chunks(text)
            picked = best_chunks(item["question"], cs)
            print(f"    {len(cs)} chunk(s), trying top {len(picked)}")

            for chunk in picked:
                a = extract(item["question"], item["unit"], chunk, EXTRACTOR)
                b = extract(item["question"], item["unit"], chunk, LONG_CONTEXT)
                merged, agree = consensus(a, b)
                if not merged:
                    continue

                grade = merged.get("confidence", "estimate")
                if grade in {"measured", "derived"}:
                    # Downgrade rather than drop: the figure may be fine, but
                    # the grade is not COOPER's to give. verify would reject it.
                    report.append(
                        f"{item['field']}: model claimed '{grade}', "
                        f"downgraded to 'estimate' -- human may promote it")
                    grade = "estimate"

                results.append({
                    "field": item["field"],
                    "value_lo": merged.get("value_lo"),
                    "value_mode": merged.get("value_mode"),
                    "value_hi": merged.get("value_hi"),
                    "unit": merged.get("unit") or item["unit"],
                    "confidence": grade,
                    "document": str(doc.relative_to(ROOT)).replace("\\", "/"),
                    "quote": merged.get("quote", ""),
                    "agreement": agree,
                    "verified_by": None,
                })
                print(f"    -> {merged.get('value_mode')} [{agree}]")
                break
            else:
                continue
            break
        else:
            report.append(f"{item['field']}: no figure found in any source")
            print("    -> nothing found")

    (out_dir / "findings.yaml").write_text(
        yaml.safe_dump({"batch": batch, "subject": subject,
                        "findings": results, "proposed_sources": []},
                       sort_keys=False, allow_unicode=True),
        encoding="utf-8")

    lines = [f"batch: {batch}", f"items: {len(spec['items'])}",
             f"figures found: {len(results)}", ""]
    disagreed = [r for r in results if not r["agreement"].startswith("2/2")]
    if disagreed:
        lines.append(f"{len(disagreed)} figure(s) where the models disagreed "
                     f"-- flagged, NOT averaged:")
        lines += [f"  {r['field']}: {r['agreement']}" for r in disagreed]
        lines.append("")
    lines += report
    (out_dir / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nwrote {out_dir}/findings.yaml and report.txt")
    print(f"{len(results)} figure(s), {len(disagreed)} needing human review")
    print("\nnothing here is trusted -- run 'research_batch.py verify' on the Mac")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="runner")
    p.add_argument("batch")
    a = p.parse_args(argv if argv is not None else sys.argv[1:])
    return run(a.batch)


if __name__ == "__main__":
    raise SystemExit(main())
