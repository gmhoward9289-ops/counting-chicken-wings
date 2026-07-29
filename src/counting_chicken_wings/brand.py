"""Project identity: ASCII art and banner composition.

Authored here rather than sourced, which makes it categorically free of
copyright risk -- the reason ASCII was the right first move for the project's
look. The same art serves the CLI banner and the web header, so the two
surfaces cannot drift apart.

Kept dependency-free and importable on its own so the CLI can print a banner
without touching the database.
"""

from __future__ import annotations

# A hen facing right. Deliberately small: it has to sit above a terminal
# prompt without pushing the answer off screen.
CHICKEN = r"""
       ,\
       \\\
        (o>
    \\\_//)
     \__ _)
        ""
"""

# One-line variant for tight spaces -- prompts, log lines, export headers.
CHICKEN_INLINE = r"(o>"

# A wing, for section headers on the wing-specific views.
WING = r"""
      .-~-.
    .'     `.
   /  .-~-.  \
  |  /     \  |
   \ \     / /
    `.`-.-'.'
      `---'
"""

TITLE = "counting chicken wings"
TAGLINE = "always six or more, usually close to twelve"


def art(name: str = "chicken") -> str:
    """Return one piece of art by name, without leading/trailing blank lines."""
    pieces = {"chicken": CHICKEN, "wing": WING}
    if name not in pieces:
        raise KeyError(f"unknown art: {name}")
    return pieces[name].strip("\n")


def banner(colour: bool = False, tagline: bool = True) -> str:
    """Compose the startup banner.

    The hen sits to the left of the wordmark rather than above it, so the
    whole banner costs six lines instead of ten. On a CLI whose entire point
    is a two-line answer, that difference matters.
    """
    amber, dim, reset = ("\033[33m", "\033[2m", "\033[0m") if colour else ("", "", "")

    bird = art("chicken").split("\n")
    text = ["", "", TITLE, TAGLINE if tagline else "", "", ""]

    out = []
    for i, line in enumerate(bird):
        right = text[i] if i < len(text) else ""
        left = f"{amber}{line:<12}{reset}"
        if right == TITLE:
            out.append(f"{left}  {amber}{right}{reset}")
        elif right:
            out.append(f"{left}  {dim}{right}{reset}")
        else:
            out.append(left.rstrip())
    return "\n".join(out)


def export_header(title: str, generated: str, source_note: str = "") -> str:
    """Plain-text header for exported data files.

    Exports are meant to be read by humans and by local models, so the
    header carries provenance inline rather than assuming the reader has
    the repo open next to them.
    """
    lines = [
        f"{CHICKEN_INLINE}  {TITLE} -- {title}",
        f"generated: {generated}",
    ]
    if source_note:
        lines.append(source_note)
    width = max(len(x) for x in lines)
    return "\n".join(["# " + x for x in lines] + ["# " + "-" * width])
