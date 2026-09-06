"""Bounded runtime system prompt assembler for Aether."""

from __future__ import annotations

from typing import Any

try:
    from aia_canvas.src.memory.profile_manager import ProfileManager
except ModuleNotFoundError:
    from memory.profile_manager import ProfileManager


def _get_context_builder_cls():
    try:
        from aia_canvas.src.omni.context import AetherContextBuilder
        return AetherContextBuilder
    except ModuleNotFoundError:
        from omni.context import AetherContextBuilder
        return AetherContextBuilder


class PromptAssembler:
    """Assembles bounded runtime system prompts from profile and spatial context by delegating to AetherContextBuilder."""

    CORE_PERSONA: str = ""

    def __init__(self, profile_manager: ProfileManager | None = None) -> None:
        if profile_manager is not None:
            self.profile_manager = profile_manager
        else:
            self.profile_manager = ProfileManager()
        builder_cls = _get_context_builder_cls()
        self._builder = builder_cls(profile_manager=self.profile_manager)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return _get_context_builder_cls()._estimate_tokens(text)

    @staticmethod
    def _truncate_to_tokens(text: str, max_tokens: int) -> str:
        return _get_context_builder_cls()._truncate_to_tokens(text, max_tokens)

    @staticmethod
    def _format_field(val: Any) -> str:
        return _get_context_builder_cls()._format_field(val)

    def format_ground_truth(self, identity_data: dict[str, Any] | None = None) -> str:
        return self._builder.format_ground_truth(identity_data)

    def format_working_state(self, working_data: dict[str, Any] | None = None) -> str:
        return self._builder.format_working_state(working_data)

    def format_focal_context(
        self, focal_nodes: list[dict[str, Any]] | None = None
    ) -> str:
        return self._builder.format_focal_context(focal_nodes)

    def assemble_system_prompt(
        self,
        focal_nodes: list[dict[str, Any]] | None = None,
        max_tokens: int = 1300,
    ) -> str:
        return self._builder.assemble_system_prompt(
            focal_nodes=focal_nodes,
            max_tokens=max_tokens,
            base_instruction=self.CORE_PERSONA,
        )


try:
    from aia_canvas.src.omni.engines.conversation.persona import (
        AETHER_SYSTEM_INSTRUCTION,
    )
except ModuleNotFoundError:
    from omni.engines.conversation.persona import AETHER_SYSTEM_INSTRUCTION

CORE_PERSONA: str = AETHER_SYSTEM_INSTRUCTION
PromptAssembler.CORE_PERSONA = AETHER_SYSTEM_INSTRUCTION



