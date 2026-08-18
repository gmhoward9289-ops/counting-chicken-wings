"""Test-suite-wide setup for the API key gate.

`api.py` requires an `API_KEY` on every /api/* route (except /healthz) and
on GET / itself -- see the api-key-gate comment near the top of that module.
Almost every test file in this directory calls the app through
`fastapi.testclient.TestClient` directly, without going through any fixture
that could attach a header, and the task that added the gate was explicit
that the existing suite has to keep passing rather than growing an
`X-API-Key` header at every call site across a dozen files.

So the key check is set to a known value for the whole test session, and the
dependency itself is overridden to a no-op for the whole session too --
`app.dependency_overrides` is FastAPI's own supported mechanism for this,
and it applies to every `TestClient(app)` instance built from the same `app`
object, however many of them a given test file constructs.

Auth-specific tests in `test_api.py` remove the override for the duration of
a single test (see `bypass_removed` there) to prove the gate actually
rejects an unkeyed request -- this file does not test that; it exists so
every OTHER test does not have to think about the gate at all.
"""

import os

import pytest

# Read before `counting_chicken_wings.api` is imported by anything, so
# `require_api_key`'s `os.environ.get("API_KEY")` never sees an unset key
# even for the one test that removes the override.
os.environ.setdefault("API_KEY", "test-key-for-ci")

from counting_chicken_wings.api import app, require_api_key, require_page_key  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _bypass_api_key_gate():
    app.dependency_overrides[require_api_key] = lambda: None
    app.dependency_overrides[require_page_key] = lambda: os.environ["API_KEY"]
    yield
    app.dependency_overrides.pop(require_api_key, None)
    app.dependency_overrides.pop(require_page_key, None)
