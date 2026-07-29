"""counting-chicken-wings.

How many chickens does it take to make a dozen chicken wings?

Versioning: pyproject.toml is the single source of truth. `__version__` is
read from the INSTALLED package metadata rather than hardcoded here, so the
number cannot be declared in two places and drift between them -- which is
exactly how a release ends up claiming a version it is not.

Deliberately not setuptools-scm. Deriving the version from git tags looks
tidier but breaks on the deploy target: Render clones without tags, so
setuptools-scm would resolve to a bogus `0.1.dev1+...` in production. A
static version plus a CI check that the tag matches is duller and correct.

See docs/VERSIONING.md.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("counting-chicken-wings")
except PackageNotFoundError:
    # Running from a source tree that was never installed. Reported honestly
    # rather than guessed at, so nothing downstream mistakes it for a real
    # release number.
    __version__ = "0+unknown"

__all__ = ["__version__"]
