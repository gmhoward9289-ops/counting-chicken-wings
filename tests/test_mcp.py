"""MCP tool surface — citations on calculate are never optional."""

from __future__ import annotations

import pytest

from counting_chicken_wings import tools


@pytest.fixture
def tools_db(tmp_path, monkeypatch):
    """Build a fresh DB under tmp so MCP tests do not share the repo file."""
    import counting_chicken_wings.db as db_mod
    from counting_chicken_wings.build import build

    db_path = tmp_path / "chickens.db"
    build(db_path)
    monkeypatch.setattr(db_mod, "DEFAULT_DB", db_path)
    return db_path


class TestWingsMeta:
    def test_lists_products_and_chains(self, tools_db):
        body = tools.wings_meta(db=tools_db)
        assert body["products"]
        assert body["chains"]
        assert body["package_version"]


class TestWingsCalculate:
    def test_dozen_wings_carries_citations(self, tools_db):
        body = tools.wings_calculate(count=12, product="whole_wing", db=tools_db)
        assert "error" not in body
        assert body["answer"]["floor"] >= 6
        assert body["answer"]["required"] >= body["answer"]["floor"]
        # Two questions, never conflated.
        assert "required" in body["answer"]
        assert "distinct" in body["answer"]
        assert body["sources"]
        cited = [s for s in body["trace"] if s.get("source")]
        assert cited
        for step in cited:
            assert step["source"] in body["sources"]
            src = body["sources"][step["source"]]
            assert src["title"]
            assert src["url"] or src["publisher"]

    def test_unknown_product(self, tools_db):
        body = tools.wings_calculate(product="not_a_real_product", db=tools_db)
        assert "error" in body


class TestWingsSources:
    def test_catalog_has_used_by(self, tools_db):
        body = tools.wings_sources(db=tools_db)
        assert body["sources"]
        assert any(s.get("used_by", 0) > 0 for s in body["sources"])


class TestWingsFacts:
    def test_facts_carry_source_fields(self, tools_db):
        body = tools.wings_facts(limit=5, db=tools_db)
        assert body["facts"]
        for f in body["facts"]:
            assert f["source_slug"]
            assert f["source_title"]
            assert f["url"] or f["publisher"]


class TestWingsScope:
    def test_anchor_present(self, tools_db):
        body = tools.wings_scope(db=tools_db)
        assert body["species"]
        assert "anchor" in body


class TestServerRegistration:
    def test_tools_registered(self):
        pytest.importorskip("mcp")
        import counting_chicken_wings.server as srv

        for n in (
            "wings_meta",
            "wings_scope",
            "wings_calculate",
            "wings_sources",
            "wings_facts",
        ):
            assert hasattr(srv, n)
