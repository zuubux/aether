"""
OmniRouter Dispatcher
Routes queries to specialized OmniEngines based on deterministic prefixes or affinity scoring.
"""

import asyncio
import inspect
from typing import Any, AsyncIterator, Dict, List, Optional
from .base import OmniEngine, OmniResult
from .context import OmniContext
from .engines.search import FuzzySearchEngine
from .engines.shell import ShellEngine
from .engines.llm import LLMEngine
from .engines.conversation import ConversationEngine


class SystemEngine(OmniEngine):
    """Engine for '/' prefixed system commands."""

    def can_handle(self, query: str, context: OmniContext) -> float:
        if query.strip().startswith("/"):
            return 1.0
        return 0.0

    async def execute(
        self, query: str, context: OmniContext
    ) -> List[OmniResult]:
        cmd_text = query.strip().removeprefix("/").strip()
        if not cmd_text:
            return []
        title_str = f"System Command: /{cmd_text}"
        result = OmniResult(
            id="sys_cmd",
            title=title_str,
            category="system",
            score=1.0,
            metadata={"command": cmd_text},
            icon="settings",
        )
        return [result]

    def get_mode_metadata(self) -> Dict[str, Any]:
        return {
            "mode": "system",
            "glow_color": "#10B981",
            "placeholder": "System command...",
            "icon": "settings",
        }


class OmniRouter:
    def __init__(self, store: Optional[Any] = None):
        self.store = store
        self.engines: List[OmniEngine] = []

        # Register standard default engines
        self.search_engine = FuzzySearchEngine(store=self.store)
        self.shell_engine = ShellEngine(store=self.store)
        self.conversation_engine = ConversationEngine()
        self.llm_engine = self.conversation_engine
        self.system_engine = SystemEngine()

        self.register_engine(self.shell_engine)
        self.register_engine(self.llm_engine)
        self.register_engine(self.system_engine)
        self.register_engine(self.search_engine)

    def register_engine(self, engine: OmniEngine) -> None:
        if engine not in self.engines:
            self.engines.append(engine)

    def update_store(self, store: Any) -> None:
        self.store = store
        self.search_engine.store = store
        self.shell_engine.store = store

    async def query(
        self, query: str, context: Optional[OmniContext] = None
    ) -> AsyncIterator[str]:
        """Dispatch conversational query directly to ConversationEngine.query()."""
        ctx_dict = {}
        if context:
            ctx_dict = {
                "focused_node_id": context.focused_node_id,
                "selected_node_ids": context.selected_node_ids,
            }
        async for chunk in self.conversation_engine.query(query, context=ctx_dict):
            yield chunk

    def resolve_engine(self, query: str, context: OmniContext) -> OmniEngine:
        q = query.strip()
        # Deterministic prefix evaluation
        if q.startswith(">"):
            return self.shell_engine
        if q.startswith("?"):
            return self.conversation_engine
        if q.startswith("/"):
            return self.system_engine

        # Affinity scoring fallback
        best_engine: OmniEngine = self.search_engine
        best_score = -1.0

        for engine in self.engines:
            try:
                score = engine.can_handle(query, context)
            except Exception:
                score = 0.0
            if score > best_score:
                best_score = score
                best_engine = engine

        return best_engine

    def get_mode_metadata(
        self, query: str, context: Optional[OmniContext] = None
    ) -> Dict[str, Any]:
        if context is None:
            context = OmniContext(raw_query=query)
        engine = self.resolve_engine(query, context)
        return engine.get_mode_metadata()

    async def async_dispatch(
        self, query: str, context: Optional[OmniContext] = None
    ) -> List[OmniResult]:
        if context is None:
            context = OmniContext(raw_query=query)

        engine = self.resolve_engine(query, context)
        results_or_gen = engine.execute(query, context)

        if inspect.isasyncgen(results_or_gen):
            results = [item async for item in results_or_gen]
        elif inspect.iscoroutine(results_or_gen):
            results = await results_or_gen
        else:
            results = results_or_gen  # type: ignore

        return results

    def dispatch(
        self, query: str, context: Optional[OmniContext] = None
    ) -> List[OmniResult]:
        """Synchronous dispatch wrapper for non-async contexts/tests."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If running inside an existing event loop, create a task or run_until_complete
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.async_dispatch(query, context))
                    return future.result()
            else:
                return loop.run_until_complete(self.async_dispatch(query, context))
        except RuntimeError:
            return asyncio.run(self.async_dispatch(query, context))
