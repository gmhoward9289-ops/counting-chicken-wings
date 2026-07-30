"""Rewrite the README's generated corpus-stats block.

    python tools/update_readme.py            # rewrite in place
    python tools/update_readme.py --check    # exit 1 if it would change

Run this after any data change. `tests/test_readme.py` asserts the same thing,
so forgetting is caught rather than shipped -- but the test only tells you the
block is stale, and this fixes it.

Why a tool and not a hand edit: the README's claim about how much of the corpus
is unsourced is the most load-bearing sentence in the project, and it drifted
three times while maintained by hand. The last drift had it claiming 7 of 12
estimates when the truth was 11 of 21, which overstated the data's quality.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from counting_chicken_wings.audit import (  # noqa: E402
    STATS_BEGIN,
    STATS_END,
    stats_block,
)

README = Path(__file__).resolve().parents[1] / "README.md"


def replace_block(text: str, block: str) -> str:
    """Swap whatever is between the markers for `block`.

    Raises rather than appending if the markers are missing. A README that has
    lost its markers is a README somebody edited by hand, and silently
    bolting the block onto the end would bury that.
    """
    start = text.find(STATS_BEGIN)
    end = text.find(STATS_END)
    if start == -1 or end == -1:
        raise SystemExit(
            f"{README.name} has no generated block. Expected the markers\n"
            f"  {STATS_BEGIN}\n  {STATS_END}\n"
            "Restore them where the corpus figures belong, then re-run."
        )
    if end < start:
        raise SystemExit(f"{README.name}: end marker precedes begin marker.")
    return text[:start] + block + text[end + len(STATS_END):]


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    text = README.read_text()
    updated = replace_block(text, stats_block())

    if "--check" in argv:
        if updated != text:
            print(f"{README.name} is stale. Run: python "
                  f"tools/update_readme.py", file=sys.stderr)
            return 1
        print(f"{README.name} is current")
        return 0

    if updated == text:
        print(f"{README.name} already current")
        return 0
    README.write_text(updated)
    print(f"{README.name} updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
