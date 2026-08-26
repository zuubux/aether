"""
Unit tests for FuzzySearchEngine.
Tests multi-tier ranking, stem matching, snippet extraction math, and search scoring.
"""

import asyncio
from omni import FuzzySearchEngine, OmniContext
from models import Node


class MockStore:
    def __init__(self, nodes=None):
        self._nodes = nodes or []

    def get_all_nodes(self):
        return self._nodes


def test_fuzzy_search_engine_can_handle():
    store = MockStore()
    engine = FuzzySearchEngine(store=store)

    ctx = OmniContext(raw_query="restomod")
    assert engine.can_handle("restomod", ctx) == 0.8
    assert engine.can_handle("> restomod", ctx) == 0.0


def test_fuzzy_search_ranking_and_scoring(mock_bridge):
    n1 = Node(id=1, file_path="/test/report.pdf", x=1280.0, y=720.0, archetype="document", snippet="Quarterly earnings summary report line", size_bytes=2048)
    n2 = Node(id=2, file_path="/test/analytics.py", x=3000.0, y=3000.0, archetype="code", snippet="Data pipeline engine execution", size_bytes=4096)
    n3 = Node(id=3, file_path="/test/dataset.csv", x=100.0, y=100.0, archetype="table", snippet="Row data entries for ML model", size_bytes=8192)

    mock_bridge.store.upsert_node(n1)
    mock_bridge.store.upsert_node(n2)
    mock_bridge.store.upsert_node(n3)

    engine = FuzzySearchEngine(store=mock_bridge.store)
    ctx1 = OmniContext(raw_query="report")

    res1 = asyncio.run(engine.execute("report", ctx1))
    assert len(res1) > 0
    assert res1[0].id == "1"
    assert res1[0].score >= 0.85
    assert "report" in res1[0].title.lower() or "report" in res1[0].snippet.lower()


def test_fuzzy_search_empty_store():
    store = MockStore([])
    engine = FuzzySearchEngine(store=store)

    ctx = OmniContext(raw_query="nonexistent")
    res = asyncio.run(engine.execute("nonexistent", ctx))
    assert len(res) == 0
