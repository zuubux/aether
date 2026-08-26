"""
Conversation Engine Implementation
Manages active session history buffer and delegates to LLM providers.
"""

from collections import deque
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from ...base import OmniResult
from ...context import OmniContext, assemble_spatial_context, format_spatial_envelope
from ..llm import LLMEngine
from .base import BaseLLMProvider, ProviderMetadata
from .gemini import GeminiProvider
from .persona import AETHER_SYSTEM_INSTRUCTION


class ConversationEngine(LLMEngine):
    """Conversation engine managing in-memory sliding dialogue history and provider streaming."""

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        max_history: int = 20,
        bridge: Optional[Any] = None,
    ):
        super().__init__()
        self.provider: BaseLLMProvider = provider or GeminiProvider()
        self.max_history: int = max_history
        self._history: deque = deque(maxlen=max_history)
        self.bridge: Optional[Any] = bridge

    @property
    def provider_metadata(self) -> ProviderMetadata:
        """Return metadata for the active LLM provider."""
        if hasattr(self.provider, "metadata"):
            return self.provider.metadata
        return ProviderMetadata()

    def set_bridge(self, bridge: Any) -> None:
        """Associate bridge instance for resolving active canvas focus state."""
        self.bridge = bridge

    def set_provider(self, provider: BaseLLMProvider) -> None:
        """Switch the active LLM provider."""
        self.provider = provider

    def get_history(self) -> List[Dict[str, str]]:
        """Return snapshot of active dialogue history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear active session history."""
        self._history.clear()

    async def stream_prompt(
        self,
        prompt: str,
        context: Optional[Union[Dict[str, Any], OmniContext]] = None,
    ) -> AsyncIterator[str]:
        """Stream conversational prompt response with spatial context assembly.

        Args:
            prompt: Query prompt (can be prefixed with '?').
            context: Optional context dictionary or OmniContext.

        Yields:
            str: Response token chunks from provider stream.
        """
        clean_prompt = prompt.strip()
        if clean_prompt.startswith("?"):
            clean_prompt = clean_prompt[1:].strip()

        if not clean_prompt:
            return

        # Build context dictionary
        if isinstance(context, OmniContext):
            ctx_dict = {
                "focused_node_id": context.focused_node_id,
                "focused_node_path": context.focused_node_path,
                "selected_node_ids": context.selected_node_ids,
            }
        elif isinstance(context, dict):
            ctx_dict = dict(context)
        else:
            ctx_dict = {}

        focused_node_id = ctx_dict.get("focused_node_id")
        focused_node_path = ctx_dict.get("focused_node_path")

        if not focused_node_id and not focused_node_path and self.bridge:
            if hasattr(self.bridge, "get_focused_node_id"):
                focused_node_id = self.bridge.get_focused_node_id()
                focused_node_path = self.bridge.get_focused_node_path()
            elif hasattr(self.bridge, "selectedNodeId") and self.bridge.selectedNodeId:
                focused_node_id = str(self.bridge.selectedNodeId)

        store = ctx_dict.get("store") or getattr(self.bridge, "store", None)
        graph_db_path = ctx_dict.get("graph_db_path")

        # Target node identifier or file path for spatial context assembly
        target = focused_node_path or focused_node_id

        # Assemble and format spatial context envelope
        spatial_ctx = assemble_spatial_context(
            focused_node_id=target,
            graph_db_path=graph_db_path,
            focused_node_path=focused_node_path,
            store=store,
        )
        envelope_str = format_spatial_envelope(spatial_ctx)

        # Prepend formatted [Spatial Context] envelope to prompt turn sent to LLM provider
        provider_prompt = f"{envelope_str}\n\n{clean_prompt}"

        # Context for provider retains clean turn history and system instruction
        provider_ctx = dict(ctx_dict)
        provider_ctx["history"] = list(self._history)
        if "system_instruction" not in provider_ctx:
            provider_ctx["system_instruction"] = AETHER_SYSTEM_INSTRUCTION

        # Record user's clean prompt query in sliding history buffer (no envelope pollution)
        self._history.append({"role": "user", "content": clean_prompt})

        full_response_chunks: List[str] = []
        async for chunk in self.provider.stream_chat(provider_prompt, provider_ctx):
            full_response_chunks.append(chunk)
            yield chunk

        full_response = "".join(full_response_chunks)
        if full_response:
            self._history.append({"role": "assistant", "content": full_response})

    async def execute_prompt(
        self,
        prompt: str,
        context: Optional[Union[Dict[str, Any], OmniContext]] = None,
    ) -> str:
        """Execute conversational prompt and return full accumulated response string."""
        chunks: List[str] = []
        async for chunk in self.stream_prompt(prompt, context=context):
            chunks.append(chunk)
        return "".join(chunks)

    async def query(
        self,
        prompt: str,
        context: Optional[Union[Dict[str, Any], OmniContext]] = None,
    ) -> AsyncIterator[str]:
        """Query active LLM provider with streaming output and session history tracking."""
        async for chunk in self.stream_prompt(prompt, context=context):
            yield chunk

    def get_mode_metadata(self) -> Dict[str, Any]:
        """Return visual mode config dictionary."""
        return {
            "mode": "llm",
            "glow_color": "#38BDF8",
            "placeholder": "Ask AI reasoning engine...",
            "icon": "sparkles",
        }

    async def execute(
        self, query: str, context: OmniContext
    ) -> List[OmniResult]:
        """OmniEngine execution interface compatibility returning OmniResult list."""
        prompt_text = query.strip().removeprefix("?").strip()
        if not prompt_text:
            return []

        title_str = f"Ask AI: {prompt_text}"

        result = OmniResult(
            id="llm_query",
            title=title_str,
            category="llm",
            score=1.0,
            metadata={
                "prompt": prompt_text,
                "focused_node_id": context.focused_node_id,
                "selected_node_ids": context.selected_node_ids,
            },
            icon="sparkles",
        )
        return [result]
