"""Bounded runtime system prompt assembler for Aether."""

from __future__ import annotations

import json
from typing import Any

try:
    from aia_canvas.src.memory.profile_manager import ProfileManager
except ModuleNotFoundError:
    from memory.profile_manager import ProfileManager

class PromptAssembler:
    """Assembles bounded runtime system prompts from profile and spatial context."""

    CORE_PERSONA: str = ""

    def __init__(self, profile_manager: ProfileManager | None = None) -> None:
        if profile_manager is not None:
            self.profile_manager = profile_manager
        else:
            self.profile_manager = ProfileManager()

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Returns approximate token count (max(1, len(text) // 4))."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    @staticmethod
    def _truncate_to_tokens(text: str, max_tokens: int) -> str:
        """Truncate string to fit within max_tokens budget."""
        if max_tokens <= 0:
            return ""
        if PromptAssembler._estimate_tokens(text) <= max_tokens:
            return text
        char_limit = max_tokens * 4
        if char_limit <= 3:
            return text[:char_limit]
        return text[: char_limit - 3].rstrip() + "..."

    @staticmethod
    def _format_field(val: Any) -> str:
        """Format an identity or state value cleanly into a readable string."""
        if val is None or val == "" or val == {} or val == []:
            return "None"
        if isinstance(val, dict):
            items = []
            for k, v in val.items():
                if isinstance(v, dict):
                    if v:
                        items.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
                elif isinstance(v, (list, tuple)):
                    if v:
                        items.append(f"{k}: [{', '.join(str(x) for x in v)}]")
                elif v is not None and v != "":
                    items.append(f"{k}: {v}")
            return ", ".join(items) if items else "None"
        if isinstance(val, (list, tuple)):
            return ", ".join(str(x) for x in val) if val else "None"
        return str(val)

    def format_ground_truth(self, identity_data: dict[str, Any] | None = None) -> str:
        """Extracts entities, system_environment, and collaboration_style into a ground truth block.

        Truncates if exceeding 450 tokens.
        """
        if identity_data is None:
            identity_data = self.profile_manager.get_identity() if self.profile_manager else {}
        if not isinstance(identity_data, dict):
            identity_data = {}

        env = identity_data.get("system_environment", {})
        style = identity_data.get("collaboration_style", {})
        entities = identity_data.get("entities", {})

        lines = [
            "[GROUND TRUTH MEMORY]",
            f"- Environment: {self._format_field(env)}",
            f"- Style: {self._format_field(style)}",
            f"- Known Entities: {self._format_field(entities)}",
        ]
        block = "\n".join(lines)
        return self._truncate_to_tokens(block, 450)


    def format_working_state(self, working_data: dict[str, Any] | None = None) -> str:
        """Formats active project, top 5 hot topics, and staged nodes.

        Truncates if exceeding 400 tokens.
        """
        if working_data is None:
            working_data = self.profile_manager.get_working_state() if self.profile_manager else {}
        if not isinstance(working_data, dict):
            working_data = {}

        active_project = working_data.get("active_project") or "None"

        hot_topics = working_data.get("hot_topics", [])
        if isinstance(hot_topics, list):
            hot_topics_str = ", ".join(str(t) for t in hot_topics[:5]) if hot_topics else "None"
        elif hot_topics:
            hot_topics_str = str(hot_topics)
        else:
            hot_topics_str = "None"

        staged_nodes = working_data.get("staged_nodes", [])
        if isinstance(staged_nodes, list) and staged_nodes:
            node_strs = []
            for n in staged_nodes:
                if isinstance(n, dict):
                    title = (
                        n.get("title")
                        or n.get("path")
                        or n.get("name")
                        or n.get("label")
                        or n.get("node_id")
                        or n.get("id")
                        or str(n)
                    )
                    node_strs.append(str(title))
                else:
                    node_strs.append(str(n))
            staged_str = ", ".join(node_strs) if node_strs else "None"
        elif staged_nodes:
            staged_str = str(staged_nodes)
        else:
            staged_str = "None"

        lines = [
            "[ACTIVE WORKING STATE]",
            f"- Current Objective / Project: {active_project}",
            f"- Hot Topics: {hot_topics_str}",
            f"- Staged Nodes: {staged_str}",
        ]
        block = "\n".join(lines)
        return self._truncate_to_tokens(block, 400)

    def format_focal_context(self, focal_nodes: list[dict[str, Any]] | None = None) -> str:
        """Formats focal nodes in the clearing.

        If empty, returns empty string.
        Truncates if exceeding 250 tokens.
        """
        if not focal_nodes:
            return ""

        node_strs = []
        for n in focal_nodes:
            if isinstance(n, dict):
                title = (
                    n.get("title")
                    or n.get("path")
                    or n.get("name")
                    or n.get("label")
                    or n.get("node_id")
                    or n.get("id")
                    or str(n)
                )
                node_strs.append(str(title))
            else:
                node_strs.append(str(n))

        if not node_strs:
            return ""

        nodes_str = ", ".join(node_strs)
        lines = [
            "[FOCAL CONTEXT]",
            f"- In Clearing: {nodes_str}",
        ]
        block = "\n".join(lines)
        return self._truncate_to_tokens(block, 250)

    def assemble_system_prompt(
        self,
        focal_nodes: list[dict[str, Any]] | None = None,
        max_tokens: int = 1300,
    ) -> str:
        """Combines CORE_PERSONA + Ground Truth + Working State + Focal Context.

        Enforces the hard max_tokens ceiling (1300 tokens). If total exceeds the budget,
        trims focal context first, then working state, preserving CORE_PERSONA and Ground Truth.
        Returns the compiled system prompt string.
        """
        identity_data = self.profile_manager.get_identity() if self.profile_manager else {}
        working_data = self.profile_manager.get_working_state() if self.profile_manager else {}

        core = self.CORE_PERSONA
        ground_truth = self.format_ground_truth(identity_data)
        working_state = self.format_working_state(working_data)
        focal_context = self.format_focal_context(focal_nodes)

        # 1. Attempt full assembly
        sections = [core, ground_truth, working_state]
        if focal_context:
            sections.append(focal_context)
        prompt = "\n\n".join(s for s in sections if s)

        if self._estimate_tokens(prompt) <= max_tokens:
            return prompt

        # 2. Exceeds budget: trim focal context first
        if focal_context:
            base_without_focal = "\n\n".join(s for s in [core, ground_truth, working_state] if s)
            base_tokens = self._estimate_tokens(base_without_focal)
            avail_fc = max_tokens - base_tokens - 1
            if avail_fc >= 15:
                focal_context = self._truncate_to_tokens(focal_context, avail_fc)
            else:
                focal_context = ""

            sections = [core, ground_truth, working_state]
            if focal_context:
                sections.append(focal_context)
            prompt = "\n\n".join(s for s in sections if s)

            if self._estimate_tokens(prompt) <= max_tokens:
                return prompt

        # If still exceeding budget, focal context is completely dropped
        focal_context = ""

        # 3. Next, trim working state
        base_without_ws = "\n\n".join(s for s in [core, ground_truth] if s)
        base_tokens = self._estimate_tokens(base_without_ws)
        avail_ws = max_tokens - base_tokens - 1
        if avail_ws >= 15:
            working_state = self._truncate_to_tokens(working_state, avail_ws)
        else:
            working_state = ""

        sections = [core, ground_truth]
        if working_state:
            sections.append(working_state)
        prompt = "\n\n".join(s for s in sections if s)

        if self._estimate_tokens(prompt) <= max_tokens:
            return prompt

        # 4. Final safety net: if even core + ground_truth exceeds max_tokens
        return self._truncate_to_tokens(prompt, max_tokens)


try:
    from aia_canvas.src.omni.engines.conversation.persona import AETHER_SYSTEM_INSTRUCTION
except ModuleNotFoundError:
    from omni.engines.conversation.persona import AETHER_SYSTEM_INSTRUCTION

CORE_PERSONA: str = AETHER_SYSTEM_INSTRUCTION
PromptAssembler.CORE_PERSONA = AETHER_SYSTEM_INSTRUCTION


