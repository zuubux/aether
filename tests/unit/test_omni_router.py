"""
Unit tests for OmniRouter, OmniContext, and search mode engines.
Tests prefix routing, mode transitions, empty-query guards, and engine resolution.
"""

from omni import (
    FuzzySearchEngine,
    LLMEngine,
    OmniContext,
    OmniResult,
    OmniRouter,
    ShellEngine,
)


class MockNode:
    def __init__(
        self,
        node_id: int,
        file_name: str,
        title: str = "",
        extension: str = "",
        archetype: str = "document",
    ):
        self.id = node_id
        self.fileName = file_name
        self.title = title or file_name
        self.display_title = self.title
        self.extension = extension
        self.archetype = archetype
        self.filePath = f"/tmp/{file_name}"


class MockStore:
    def __init__(self, nodes=None):
        self._nodes = nodes or []

    def get_all_nodes(self):
        return self._nodes


def test_omni_context_fields():
    ctx = OmniContext(
        raw_query="> ls -la",
        focused_node_id="node_101",
        selected_node_ids=["node_101", "node_102"],
        typing_cadence_ms=120.5,
    )
    assert ctx.raw_query == "> ls -la"
    assert ctx.focused_node_id == "node_101"
    assert ctx.selected_node_ids == ["node_101", "node_102"]
    assert ctx.typing_cadence_ms == 120.5


def test_shell_engine():
    engine = ShellEngine()
    ctx = OmniContext(raw_query="> git status")

    assert engine.can_handle("> git status", ctx) == 1.0
    assert engine.can_handle("git status", ctx) == 0.0

    meta = engine.get_mode_metadata()
    assert meta["mode"] == "shell"
    assert meta["glow_color"] == "#F59E0B"


def test_llm_engine():
    engine = LLMEngine()
    ctx = OmniContext(raw_query="? summarize q3 revenue")

    assert engine.can_handle("? summarize q3 revenue", ctx) == 1.0
    assert engine.can_handle("summarize q3 revenue", ctx) == 0.0

    meta = engine.get_mode_metadata()
    assert meta["mode"] == "llm"
    assert meta["glow_color"] == "#38BDF8"


def test_prefix_routing_shell():
    nodes = [
        MockNode(10, "gpu_shaders.vert", "GPU Shaders", "vert", "code"),
        MockNode(20, "budget_2026.xlsx", "2026 Budget", "xlsx", "spreadsheet"),
    ]
    store = MockStore(nodes)
    router = OmniRouter(store=store)

    ctx = OmniContext(raw_query="> uptime")
    engine = router.resolve_engine("> uptime", ctx)
    assert isinstance(engine, ShellEngine)

    meta = router.get_mode_metadata("> uptime", ctx)
    assert meta["glow_color"] == "#F59E0B"

    results = router.dispatch("> uptime", ctx)
    assert len(results) >= 1
    assert results[0].category == "shell"


def test_prefix_routing_llm():
    store = MockStore()
    router = OmniRouter(store=store)

    ctx = OmniContext(raw_query="? how does aether physics work")
    engine = router.resolve_engine("? how does aether physics work", ctx)
    assert isinstance(engine, LLMEngine)

    meta = router.get_mode_metadata("? how does aether physics work", ctx)
    assert meta["glow_color"] == "#38BDF8"

    results = router.dispatch("? how does aether physics work", ctx)
    assert len(results) == 1
    assert results[0].category == "llm"


def test_prefix_routing_system():
    store = MockStore()
    router = OmniRouter(store=store)

    ctx = OmniContext(raw_query="/reset")
    meta = router.get_mode_metadata("/reset", ctx)
    assert meta["glow_color"] == "#10B981"

    results = router.dispatch("/reset", ctx)
    assert len(results) == 1
    assert results[0].category == "system"


def test_empty_query_prefix_guards():
    store = MockStore()
    router = OmniRouter(store=store)
    for prefix in [">", "?", "/"]:
        ctx = OmniContext(raw_query=prefix)
        results = router.dispatch(prefix, ctx)
        assert results == [], f"Prefix '{prefix}' should return empty list of results"


def test_fallback_plain_text():
    nodes = [
        MockNode(10, "gpu_shaders.vert", "GPU Shaders", "vert", "code"),
        MockNode(20, "budget_2026.xlsx", "2026 Budget", "xlsx", "spreadsheet"),
    ]
    store = MockStore(nodes)
    router = OmniRouter(store=store)

    ctx = OmniContext(raw_query="budget")
    engine = router.resolve_engine("budget", ctx)
    assert isinstance(engine, FuzzySearchEngine)

    meta = router.get_mode_metadata("budget", ctx)
    assert meta["glow_color"] == "#30363D"

    results = router.dispatch("budget", ctx)
    assert len(results) > 0
    assert results[0].id == "20"
