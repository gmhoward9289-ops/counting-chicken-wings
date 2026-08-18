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
import concurrent.futures as cf
import datetime as _dt
import hashlib
import html
import json
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

# COOPER is Windows and its console encoding is cp1252, so ANY non-Latin
# character reaching stdout kills the run -- after the work is done, which is
# the worst place for it. The first Hebrew batch extracted two figures and then
# died printing the item's name, losing findings.yaml with them.
#
# reconfigure() rather than PYTHONIOENCODING because this has to hold however
# the script is invoked: over ssh, from a scheduled task, by hand.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):      # already utf-8, or not a tty
        pass

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
#
# SECOND MODEL SWAPPED 2026-07-29 (later the same day), on an A/B against a
# real chunk with a known answer: the UC ANR saffron page, where the right
# reply is 150 flowers per gram inside a sentence that must come back
# character-for-character.
#
#   model              trivial  real chunk  found 150  full quote verbatim
#   qwen2.5-coder:7b     7.6s      16.5s       yes      no (partial)
#   gemma4-32k          34.1s      43.3s       yes      no (partial)
#   mistral:7b          16.5s      17.5s       yes      YES
#
# mistral is ~2.5x faster than gemma and produced the only fully verbatim
# quote and the only correct confidence grade -- and no markdown fence to
# strip. It is also a different model family from qwen, which is the entire
# point of running two: two models from one family fail the same way, so their
# agreement means nothing.
#
# A WRONG EXPLANATION, CORRECTED, because it was nearly written into the code:
# the swap was first justified by gemma's 9.6 GB "spilling" out of 8 GB of
# VRAM. It does not. 9.6 GB is the manifest size; gemma4-32k loads at 3.27 GB
# and runs 100% on the GPU, exactly as the note below already said. Its cost is
# TOKENS, not memory -- it narrates a reasoning trace before answering, so it
# emits several times more output for the same reply. Measured, not assumed:
#
#   qwen 5.02 GB / gemma 3.27 GB / mistral 5.56 GB, all 100% size_vram.
#
# Note also that no useful pair co-resides in 8 GB (qwen+mistral = 10.6 GB,
# qwen+gemma = 8.3 GB), so the models run sequentially either way and the swap
# costs nothing that was previously being had.
#
# THE A/B WAS MEASURING THE WRONG THING. Read this before trusting it.
#
# batch-04-honey ran an hour later and inverted the result. Recall went UP and
# precision collapsed: mistral answered 13 of 14 calls against qwen's 3, and
# almost every extra answer was junk.
#
#   flowers_per_pound_honey       2670588   <- plausible
#   honey_yield_per_colony_year   2670588   <- same number, different question
#   nectar_to_honey_ratio         2670588   <- same number again
#   colony_size                   "industry"        <- the confidence grade,
#                                                      in the value field
#   forager_fraction              "Several thousand" <- prose, not a figure
#   honey_per_bee_lifetime        "32 mg"   <- a nectar LOAD, not a lifetime
#
# The gate rejected all seven rows, three of them only after a fix it exposed
# (band_in_quote silently passed non-numeric values). So nothing shipped, which
# is the system working -- but the model comparison was confounded and must not
# be read as settled.
#
# WHY IT WAS CONFOUNDED: five of seventeen URLs failed on SSL certificate
# verification on COOPER -- all three PMC articles and the U. Arkansas PDF, the
# four best documents in the batch. Both models were therefore asked to find
# figures that were not in the text they had. qwen mostly declined; mistral
# answered by proximity. That IS the failure mode that matters most for this
# project, and on it qwen's low count looks like correct refusal rather than
# weak recall -- but a fair comparison needs the sources present.
#
# RE-RUN DONE, AND MISTRAL IS OUT. The certificate fix landed all 17 documents
# (59 chunks against 25), so the confound is gone -- and the behaviour did not
# change. With every source present, mistral still returned 2670588 as the
# value for three unrelated fields, "Several thousand" for a fraction, and
# "1 and 1/2 teaspoons" for a mass. 11 answers of 14, and the gate rejected
# every row worth rejecting. qwen answered 4 and declined the rest.
#
# The tell is one number appearing under three different questions. That is not
# weak extraction, it is answering from proximity rather than from meaning, and
# the prompt's "Guessing is worse than not answering" does not restrain it.
#
# So the second model goes back to gemma4-32k -- not because gemma is good, it
# is 2.5x slower and needs a reasoning trace stripped, but because
# qwen + gemma is the ONLY configuration that has ever produced accepted
# corpus (batch-01-saffron, three figures). mistral has produced zero across
# two full runs. Slow and quiet beats fast and confident here, because the
# product is trustworthiness and a fabricated figure costs more than a missing
# one.
#
# What the A/B got right, and why it still misled: mistral genuinely does quote
# more faithfully WHEN THE ANSWER IS PRESENT. That is what was measured, on a
# chunk chosen because it contained the answer. It never tested the case that
# dominates a real batch -- most chunks do not contain most answers -- and on
# that case mistral is the worst of the three.
#
# NEXT THING TO TRY, when a batch next makes sense rather than as a fishing
# expedition: harden the refusal instruction and re-measure with a chunk that
# deliberately does NOT contain the answer. A model's refusal rate on absent
# figures is the number that actually predicts batch quality, and no test here
# has measured it yet.
EXTRACTOR = "qwen2.5-coder:7b"
LONG_CONTEXT = "gemma4-32k"
EMBEDDER = "nomic-embed-text"

# COOPER: i7-6700 (4c/8t), 32 GB RAM, RTX 2060 SUPER with 8 GB VRAM.
#
# Measured, correcting two things assumed earlier. gemma4-32k's 9.6 GB is its
# DISK size; it loads at 3.25 GB and runs 100% on GPU. qwen loads at 4.57 GB.
# Together that is 7.82 GB against 8 GB of VRAM, which is why ollama keeps
# declining to hold both resident no matter what MAX_LOADED_MODELS says -- the
# binding constraint is VRAM, not the 32 GB of system RAM.
#
# Generation stays on the GPU. A CPU/GPU split was measured and REJECTED: qwen
# takes 19.1s on CPU against 5.5s on GPU, so the CPU leg becomes the bottleneck
# and a concurrent split runs ~74% slower than doing both sequentially on the
# GPU. The idle CPU is used for embeddings, PDF extraction and verification
# instead -- work that is genuinely CPU-shaped and off the critical path.
#
# Calls are still grouped by model, which costs nothing and avoids reloading a
# 4.57 GB model between every call.
WORKERS = 2          # matches OLLAMA_NUM_PARALLEL; more would just queue

# Sized from measurement, not caution. Both models have >=16k context and the
# first run used 6000 chars (~1500 tokens) of it -- a tenth of what was
# available -- which split a 20k-char page into 4 chunks and made it likely the
# answer straddled a boundary. Four of six items found nothing on that run.
# 12000 chars is ~3000 tokens, still far inside the window, and halves the call
# count. Generous overlap because a figure and its unit often sit in different
# sentences.
CHUNK_CHARS = 12000
CHUNK_OVERLAP = 1500


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


GENERATE_API = "http://localhost:11434/api/generate"

# Measured: qwen2.5-coder:7b defaults to a 4096-token context in ollama, NOT its
# architectural maximum. That silently truncated 12000-char chunks (~3000-4000
# tokens plus the prompt template) and took qwen from finding a figure to finding
# nothing at all -- 0 of 12 calls. Nothing errored; the prompt was just cut.
#
# So num_ctx is now set explicitly and generously. Chunk size and context window
# have to be tuned together; changing one alone is how the second run came back
# worse than the first.
NUM_CTX = 8192


def ollama(model: str, prompt: str, timeout: int = 300) -> str:
    """Call a local model over the HTTP API. Free, so retries cost only time.

    The API rather than `ollama run` for two reasons: it accepts num_ctx (the
    CLI does not, so context was pinned at the 4096 default and truncating), and
    it returns a JSON field instead of terminal output, so the ANSI escape codes
    the CLI emits never appear. gemma's reasoning trace still does, hence
    sanitize() remains.
    """
    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"num_ctx": NUM_CTX, "temperature": 0},
    }).encode()
    try:
        req = urllib.request.Request(
            GENERATE_API, data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception:                               # noqa: BLE001
        return ""
    return sanitize(data.get("response") or "")


# ---------------------------------------------------------------------------
# Fetch and chunk
# ---------------------------------------------------------------------------

_FETCH_CACHE: dict[str, Path | None] = {}
_EMBED_CACHE: dict[str, list[float] | None] = {}

# Documents this run fetched that turned out to be doormen. Collected so the
# end of the run can say so in one place: the per-fetch line scrolls past under
# 200 chunk messages, and the batch-05 wall went unnoticed for exactly that
# reason.
WALLED_FETCHES: list[tuple[str, str]] = []

# ---------------------------------------------------------------------------
# Bot walls: what a fetch looks like when the answer is 200 and the body is a
# doorman.
#
# This is the CANONICAL definition and it lives here, in the fetcher, for two
# reasons. It has to run on COOPER, where only tools/cooper/ is present and
# nothing else of the project is importable; and the check belongs next to the
# code whose output it describes. tools/research_batch.py imports these names
# rather than restating them -- two copies of this list would drift, and the
# half that drifted would be the half that stayed silent.
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


def looks_like_interstitial(text: str,
                            total_chars: int | None = None) -> tuple[bool, str]:
    """True when a fetch is a doorman rather than a document.

    The dangerous case is not an error: FSIS 403s to COOPER and the runner says
    so. PMC returned HTTP 200 and 167 characters of "Checking your browser -
    reCAPTCHA", which every layer downstream treated as a successful fetch of
    Gross 2023 (Animal Frontiers) -- the strongest source in batch-05-milk.

    `total_chars` exists for the scout, which only ships the first 2,000
    characters of a remote body back across the wire and must judge the size on
    the count rather than on what it holds.
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


def fetch_once(url: str, doc_dir: Path) -> Path | None:
    """Fetch a URL at most once per run.

    The first version fetched per item, so a six-item batch pulled the same
    Penn State page six times and embedded it six times over. Same bytes, same
    embeddings, six times the work and six times the load on someone else's
    server -- which is also just rude.
    """
    if url in _FETCH_CACHE:
        return _FETCH_CACHE[url]
    # The 48-character truncation alone SILENTLY DESTROYED DOCUMENTS. In
    # batch-09 three govinfo URLs --
    #
    #   .../CFR-2024-title9-vol2-part381.pdf     693,586 chars
    #   .../CFR-2024-title7-vol3-part70.pdf       79,871 chars
    #   .../CFR-2024-title9-vol2-sec381-90.pdf     3,954 chars
    #
    # share their first 47 characters, so all three wrote to
    # "https-www-govinfo-gov-content-pkg-cfr-2024-title" and the last fetch
    # won. Two documents were downloaded, logged as fetched, and deleted by the
    # next fetch. The run then reported 0 of 8 extractions and looked like
    # source scarcity.
    #
    # This is the worst shape a bug can take here: the evidence directory is
    # the thing the gate checks quotes against, so losing a document does not
    # just lose a figure, it makes any quote from it unverifiable. A short hash
    # of the FULL url keeps names readable and collisions impossible.
    digest = hashlib.sha256(url.encode()).hexdigest()[:8]
    stem = re.sub(r"[^a-z0-9]+", "-", url.lower())[:48].strip("-")
    _FETCH_CACHE[url] = fetch_url(url, doc_dir / f"{stem}-{digest}")
    return _FETCH_CACHE[url]


def _ca_context() -> ssl.SSLContext | None:
    """An SSL context with a real CA bundle, or None to use the default.

    COOPER's Python 3.14 reports `cafile: None` and `capath: None` -- it has no
    CA bundle at all -- so certificate verification fails for any site whose
    chain Windows has not already cached. In batch-04-honey that silently cost
    the four best documents in the batch: all three PMC articles and the U.
    Arkansas PDF, every one of which fetches fine from a Mac.

    The failure mode is the dangerous kind. Each one printed a single `fetch
    failed` line among sixteen successes, the run completed, models were asked
    for figures that were not in the text they had, and the output looked like a
    model problem rather than a plumbing one.

    Verification is never disabled to make a fetch succeed. An unverified
    document is not evidence, and this pipeline exists to produce evidence.
    """
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


_SSL_CTX = _ca_context()
_WARNED_ABOUT_CERTIFI = False


def _warn_once_about_trust_store() -> None:
    """Say it when it can matter -- at the first fetch, not at import.

    Deliberately does not name a machine. This module is imported on the Mac
    too -- research_batch.py imports it for the spec parser and the bot-wall
    definitions, and the tests import it directly -- and the Mac has a working
    system trust store, so asserting "COOPER does not have one" was simply
    wrong half the time it printed.

    It is deferred to the first fetch for the same reason it is worded that
    way: research_batch's `verify` and `accept` never open a socket, and a
    warning printed on every invocation of a command it cannot apply to is
    noise. Noise on a channel that also carries [WALLED] is not free.
    """
    global _WARNED_ABOUT_CERTIFI
    if _SSL_CTX is not None or _WARNED_ABOUT_CERTIFI:
        return
    _WARNED_ABOUT_CERTIFI = True
    print("  WARNING: certifi is not installed, so HTTPS verification falls "
          "back to whatever trust store this interpreter has. On a host with "
          "none (COOPER reports cafile=None) expect fetch failures on PMC and "
          "some .edu hosts. Fix: pip install certifi")


def _note_if_walled(url: str, text: str, path: Path) -> None:
    """Say loudly when what just landed is a doorman, not a document.

    Deliberately does NOT return None to the caller and does NOT delete the
    file. The artifact is the evidence: `research_batch verify` re-checks every
    document that arrives and `fetch` reports the walls it finds, and both of
    those need the file to exist. Suppressing it here would only move the
    silence one layer down.

    This is a WARNING at fetch time and a FAILURE at gate time, and that split
    is on purpose. The wall is per-request -- COOPER was served PMC's reCAPTCHA
    during batch-05 and 82,331 characters of the same article during batch-06 --
    so the fetcher's job is to make it visible, not to adjudicate it.
    """
    walled, why = looks_like_interstitial(text)
    if not walled:
        return
    WALLED_FETCHES.append((url, why))
    print(f"    [WALLED] {path.name}: {why}")
    print(f"             {url}")
    print("             This is a 200 with a doorman behind it. Any item "
          "resting on it will\n             come back empty for a plumbing "
          "reason, not a source one.")


# Contact info in the UA is the single highest-value courtesy for an
# unattended fetcher: it gives a host operator someone to email before they
# reach for a block. Named for the project, not the machine -- this same
# string is sent whether it runs on the Mac or on COOPER.
FETCH_UA = ("counting-chicken-wings/research "
            "(+https://github.com/gmhoward9289-ops/counting-chicken-wings; "
            "low-volume research batches, contact: dev@swamplink.com)")

# Seconds between requests to the same host. A batch is single digits to low
# tens of URLs, so this costs seconds per run, not minutes -- there is no
# reason to skip it for a tool that fetches on a human's say-so rather than
# crawling.
MIN_HOST_INTERVAL = 1.5

_ROBOTS_CACHE: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_LAST_FETCH: dict[str, float] = {}


def _robots_allows(url: str) -> bool:
    """Check robots.txt for this URL's host, caching the parser per host.

    A disallow SKIPS the fetch with a warning; it does not raise. This tool is
    a human triggering retrieval of specific pages they already decided to
    fetch -- closer to a browser than a spider -- so robots.txt is a courtesy
    to honour, not a gate to enforce absolutely. But honouring it by default
    costs nothing and removes an argument against us.

    Any failure to fetch robots.txt itself -- dead host, timeout, no
    robots.txt at all, a host that 404s it -- is treated as "allowed". A
    missing or broken robots.txt must never block a legitimate fetch; that
    would be the opposite of what the file is for.
    """
    host = urllib.parse.urlparse(url).netloc
    if host not in _ROBOTS_CACHE:
        scheme = urllib.parse.urlparse(url).scheme or "https"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{scheme}://{host}/robots.txt")
        try:
            req = urllib.request.Request(
                rp.url, headers={"User-Agent": FETCH_UA})
            with urllib.request.urlopen(req, timeout=15,
                                        context=_SSL_CTX) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            rp.parse(body.splitlines())
        except Exception:                            # noqa: BLE001
            rp = None                    # unreachable/missing: treat as allow
        _ROBOTS_CACHE[host] = rp
    rp = _ROBOTS_CACHE[host]
    if rp is None:
        return True
    try:
        return rp.can_fetch(FETCH_UA, url)
    except Exception:                                # noqa: BLE001
        return True                      # a broken parse must not block a fetch


def _throttle(url: str) -> None:
    """Sleep, if needed, so this host is not hit more than once every
    MIN_HOST_INTERVAL seconds. Per-host, not global: a batch that cites two
    different sites should not slow down waiting on a host it is not talking
    to."""
    host = urllib.parse.urlparse(url).netloc
    if host in _LAST_FETCH:
        wait = MIN_HOST_INTERVAL - (time.monotonic() - _LAST_FETCH[host])
        if wait > 0:
            time.sleep(wait)
    _LAST_FETCH[host] = time.monotonic()


def _log_fetch(dest: Path, url: str, status: str, body: bytes | None) -> None:
    """Append one line of fetch provenance beside the documents this run
    produces.

    This pipeline exists to verify citations, so what was fetched, from
    where, and when IS the product, not an afterthought. Logging failures are
    swallowed deliberately -- a fetch that succeeded must never be reported as
    failed because a log write hit a permissions problem.
    """
    entry = {
        "url": url,
        "status": status,
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "chars": len(body) if body is not None else None,
        "sha256": hashlib.sha256(body).hexdigest() if body is not None else None,
    }
    try:
        log_path = dest.parent / "_fetch_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def fetch_url(url: str, dest: Path) -> Path | None:
    """Save a URL to disk. The artifact is the evidence, so it must persist."""
    _warn_once_about_trust_store()
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not _robots_allows(url):
        print(f"    robots.txt disallows fetching this page, skipping: {url}")
        _log_fetch(dest, url, "robots-disallow", None)
        return None

    _throttle(url)

    req = urllib.request.Request(url, headers={"User-Agent": FETCH_UA})
    try:
        with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):
            # Respect Retry-After when the host bothers to send one; a flat
            # fallback otherwise. One retry only -- this is a batch of a few
            # URLs run once, not a queue worth re-driving.
            retry_after = e.headers.get("Retry-After")
            delay = (float(retry_after) if retry_after
                     and retry_after.strip().isdigit() else 5.0)
            print(f"    got {e.code} from {url}, retrying once after "
                  f"{delay:.0f}s")
            time.sleep(delay)
            try:
                with urllib.request.urlopen(req, timeout=60,
                                            context=_SSL_CTX) as resp:
                    body = resp.read()
            except Exception as e2:                  # noqa: BLE001
                print(f"    fetch failed: {url} -- {type(e2).__name__}: {e2}")
                _log_fetch(dest, url, f"error:{type(e2).__name__}", None)
                return None
        else:
            print(f"    fetch failed: {url} -- {type(e).__name__}: {e}")
            _log_fetch(dest, url, f"error:{type(e).__name__}", None)
            return None
    except Exception as e:                          # noqa: BLE001
        print(f"    fetch failed: {url} -- {type(e).__name__}: {e}")
        _log_fetch(dest, url, f"error:{type(e).__name__}", None)
        return None

    _log_fetch(dest, url, "ok", body)

    if url.lower().endswith(".pdf") or body[:4] == b"%PDF":
        pdf = dest.with_suffix(".pdf")
        pdf.write_bytes(body)
        txt = pdf.with_suffix(".txt")
        # pdftotext if present; otherwise keep the PDF and say so, rather than
        # pretending we extracted text.
        try:
            subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)],
                           capture_output=True, timeout=120, check=True)
            print(f"    fetched + extracted {txt.name} (pdftotext)")
            return txt
        except Exception:                           # noqa: BLE001
            pass
        # COOPER has no pdftotext, and the first run therefore skipped the
        # UF/IFAS source entirely -- a third of batch-01's evidence, lost
        # silently. pypdf is pure Python, runs on the idle CPU, and recovers it.
        try:
            import pypdf
            reader = pypdf.PdfReader(str(pdf))
            text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
            if text.strip():
                txt.write_text(text, encoding="utf-8")
                print(f"    fetched + extracted {txt.name} "
                      f"(pypdf, {len(reader.pages)} pages, {len(text):,} chars)")
                _note_if_walled(url, text, txt)
                return txt
            print(f"    {pdf.name}: pypdf found no extractable text "
                  f"(likely a scanned image -- would need OCR)")
        except ImportError:
            print(f"    fetched {pdf.name} but neither pdftotext nor pypdf "
                  f"available -- run: python -m pip install pypdf")
        except Exception as e:                      # noqa: BLE001
            print(f"    {pdf.name}: pypdf failed -- {type(e).__name__}: {e}")
        return None

    text = body.decode("utf-8", errors="replace")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text,
                  flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode entities AFTER tag stripping, so an escaped &lt;tag&gt; sitting in
    # prose cannot be turned into a real tag and then eaten by the line above.
    #
    # Left raw, &nbsp; and &#xE5D2; survive into the inbox -- and the inbox is
    # what `verify` matches quotes against. A model that reads the prose
    # correctly and writes it back as ordinary words then produces a quote that
    # can NEVER match, however honest it was. batch-08-silk lost a 2/2 consensus
    # row to exactly this: suekayton carries 47 &nbsp; and its reeling quote
    # spanned one; newworldencyclopedia carries none and its quotes verified.
    # That is a false NEGATIVE, the mirror of the filename-collision bug, and
    # just as invisible -- it reads as "the model made the quote up".
    #
    # NBSP decodes to U+00A0, which verify's NFKC pass folds to a space, so
    # nothing further is needed here.
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    dest = dest.with_suffix(".txt")
    dest.write_text(text, encoding="utf-8")
    print(f"    fetched {dest.name} ({len(text):,} chars)")
    _note_if_walled(url, text, dest)
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
    """Embed via the HTTP API, not the CLI. Cached by content.

    Chunks are re-scored for every item in a batch, and the chunk text does not
    change between items -- only the question does. Caching by content hash
    turns N_items x N_chunks embedding calls into N_chunks.

    `ollama embed` does not exist in ollama 0.32.5, which is what COOPER runs --
    verified, after an earlier version of this function called it and would have
    silently fallen back to keyword matching. The fallback would have looked like
    "the embedder is unavailable" when in fact it was reachable the whole time,
    just at a different address. The HTTP API is stable across versions.
    """
    key = hashlib.sha256(text[:8000].encode("utf-8", "replace")).hexdigest()
    if key in _EMBED_CACHE:
        return _EMBED_CACHE[key]
    try:
        # num_gpu=0 pins this to the idle CPU. Embeddings are a ranking step,
        # not on the critical path, and nomic-embed-text is only 274 MB -- so
        # this is the one place CPU inference is clearly right. Generation is
        # not: qwen measured 19.1s on CPU against 5.5s on GPU.
        body = json.dumps({
            "model": EMBEDDER, "prompt": text[:8000],
            "options": {"num_gpu": 0},
        }).encode()
        req = urllib.request.Request(
            OLLAMA_API, data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        vec = data.get("embedding")
        out = vec if isinstance(vec, list) and vec else None
    except Exception:                               # noqa: BLE001
        out = None
    _EMBED_CACHE[key] = out
    return out


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
- confidence MUST be either "industry" or "estimate". Nothing else is accepted.
  Do not use "measured", "derived" or "study" -- those are claims about where a
  document came from, not about what it says, and a human assigns them. This
  used to permit "study" for journal articles and a model applied it to an
  extension web page, so the option was removed rather than re-explained.
- If the number you want to use comes from a table, do not quote only the row.
  A bare row of digits does not say what the number IS -- retail loss and
  consumer loss can sit side by side in two columns, and a pie chart's percent
  and its total calories can sit side by side on one line, and a quote of just
  the row cannot tell those apart afterward. Copy the column header too, even
  if it is several lines above the row in the text, so "quote" carries both the
  number and the label that gives it meaning. If you cannot find a header that
  names what the number counts, reply {{"found": false}} rather than guessing
  from the row alone.

QUESTION: {question}
UNIT WANTED: {unit}
{watch}
TEXT:
{text}

JSON with keys: found, value_lo, value_mode, value_hi, unit, confidence, quote
"""

# Rendered only when the item actually carries a Watch for, so items without one
# are byte-identical to the old prompt and stay comparable against past runs.
WATCH_BLOCK = """
KNOWN TRAP FOR THIS FIGURE -- read before answering:
{watch_for}
If the only number you can find falls into that trap, reply {{"found": false}}
rather than reporting it. A wrong figure that quotes correctly is worse than
none, because every automatic check downstream will pass it.
"""


def extract(question: str, unit: str, text: str, model: str,
            watch_for: str = "") -> dict | None:
    watch = WATCH_BLOCK.format(watch_for=watch_for) if watch_for else ""
    raw = ollama(model,
                 PROMPT.format(question=question, unit=unit, text=text,
                               watch=watch))
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

        # "Watch for" is the spec's warning about the definition trap that this
        # specific figure falls into, and until now it was parsed by nobody and
        # read by nobody but us. The model never saw a word of it.
        #
        # That is the mechanism behind a pattern already noted in 08a4cf1 --
        # "the spec predicted this shape and predicting it did not stop it
        # passing." It could not: the warning was not in the prompt. Two more
        # instances on 2026-07-30, both foreseen in writing and both landed
        # anyway: ground beef stored a hedged ceiling ("more than 100 ... can be
        # used") as a point value under a Watch for that named exactly that, and
        # silk returned feet under one insisting on metres.
        #
        # Stop at the next bold lead-in so "Done means"/"Watch for" ordering
        # cannot swallow the rest of the block.
        watch = re.search(r"\*\*Watch for:\*\*\s*(.+?)(?=\n\s*\n\*\*|\n---|\Z)",
                          block, re.S)

        items.append({
            "field": field,
            "question": q.group(1).strip(),
            "unit": unit.group(1).strip() if unit else "",
            "urls": urls,
            "watch_for": re.sub(r"\s+", " ", watch.group(1)).strip()[:700]
                         if watch else "",
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

    items = spec["items"]
    print(f"{batch}: {len(items)} item(s)\n")
    report: list[str] = []

    # -- Phase 1: fetch every distinct URL once -------------------------------
    urls = list(dict.fromkeys(u for it in items for u in it["urls"]))
    print(f"fetching {len(urls)} distinct URL(s) "
          f"(was {sum(len(i['urls']) for i in items)} fetches before caching)")
    for u in urls:
        fetch_once(u, doc_dir)
    docs = [d for d in (_FETCH_CACHE.get(u) for u in urls) if d]
    if not docs:
        sys.exit("no documents could be fetched -- check the URLs in the spec")

    # Report the walls together, after the fetch phase and before the models
    # get anything, so the count is legible. batch-05 reported "0 fetch
    # failures" and had suffered one; this is the line that would have said so.
    if WALLED_FETCHES:
        print(f"\n  {len(WALLED_FETCHES)} of {len(docs)} document(s) are "
              f"interstitials, not sources:")
        for u, why in WALLED_FETCHES:
            print(f"    [WALLED] {u}\n             {why}")
        print("  These were fetched with a 200 and are worth nothing. Expect "
              "the items resting\n  on them to return empty, and do not read "
              "that as the models declining.")

    # -- Phase 2: chunk and embed each document once -------------------------
    print(f"\nchunking + embedding {len(docs)} document(s)")
    doc_chunks: list[tuple[Path, str]] = []
    for d in docs:
        text = d.read_text(encoding="utf-8", errors="replace")
        cs = chunks(text)
        doc_chunks += [(d, c) for c in cs]
        for c in cs:
            embed(c)          # warm the cache; scored against many questions
    print(f"  {len(doc_chunks)} chunk(s) across all documents")

    # Pick candidate chunks per item, before any extraction, so the expensive
    # model phase has nothing left to decide.
    plan: list[tuple[dict, Path, str]] = []
    for it in items:
        allowed = [(d, c) for d, c in doc_chunks
                   if any(str(d).endswith(Path(u).name[:0] or d.name)
                          for u in it["urls"]) or True]
        ranked = best_chunks(it["question"], [c for _, c in allowed], k=2)
        for c in ranked:
            d = next(dd for dd, cc in allowed if cc == c)
            plan.append((it, d, c))

    # -- Phase 3: one model at a time -----------------------------------------
    # MAX_LOADED_MODELS=1, so each switch costs a full unload/reload. Run every
    # call for one model before touching the other.
    def run_model(model: str) -> dict[int, dict]:
        out: dict[int, dict] = {}
        print(f"\nextracting with {model} ({len(plan)} call(s), "
              f"{WORKERS} at a time)")
        with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futs = {
                pool.submit(extract, it["question"], it["unit"], c, model,
                            it.get("watch_for", "")): i
                for i, (it, _d, c) in enumerate(plan)
            }
            for fut in cf.as_completed(futs):
                i = futs[fut]
                try:
                    got = fut.result()
                except Exception:                   # noqa: BLE001
                    got = None
                if got:
                    out[i] = got
        print(f"  {len(out)}/{len(plan)} call(s) returned a figure")
        return out

    first = run_model(EXTRACTOR)
    second = run_model(LONG_CONTEXT)

    # -- Phase 4: consensus, first hit per item wins ---------------------------
    results = []
    seen: set[str] = set()
    for i, (it, d, _c) in enumerate(plan):
        if it["field"] in seen:
            continue
        merged, agree = consensus(first.get(i), second.get(i))
        if not merged:
            continue
        seen.add(it["field"])

        grade = merged.get("confidence", "estimate")
        if grade in {"measured", "derived"}:
            # Downgrade rather than drop: the figure may be fine, but the grade
            # is not COOPER's to give, and verify would reject the row outright.
            report.append(
                f"{it['field']}: model claimed '{grade}', downgraded to "
                f"'estimate' -- a human may promote it")
            grade = "estimate"

        results.append({
            "field": it["field"],
            "value_lo": merged.get("value_lo"),
            "value_mode": merged.get("value_mode"),
            "value_hi": merged.get("value_hi"),
            "unit": merged.get("unit") or it["unit"],
            "confidence": grade,
            "document": str(d.relative_to(ROOT)).replace("\\", "/"),
            "quote": merged.get("quote", ""),
            "agreement": agree,
            "verified_by": None,
        })
        print(f"  {it['field']}: {merged.get('value_mode')} [{agree}]")

    for it in items:
        if it["field"] not in seen:
            report.append(f"{it['field']}: no figure found in any source")

    # Provenance is written by the runner rather than added by hand at accept
    # time, because a convention that depends on somebody remembering it decays
    # on the batch nobody was watching. It records what produced these rows so
    # a figure quoted out of this file still says where it came from -- the
    # directory it happens to sit in is an implication, not provenance.
    #
    # `verify` walks for dicts carrying `quote` or `confidence`; this block has
    # neither key, so it is metadata the gate cannot be fed. Keep it that way.
    extraction = {
        "host": socket.gethostname(),
        "models": [EXTRACTOR, LONG_CONTEXT],
        "ran": _dt.date.today().isoformat(),
        "specified_by": "human",
        "gate": "verify (verbatim quote against the returned document)",
    }

    (out_dir / "findings.yaml").write_text(
        yaml.safe_dump({"batch": batch, "subject": subject,
                        "extraction": extraction,
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
