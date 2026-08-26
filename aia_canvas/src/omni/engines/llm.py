"""
LLM Engine
Handles conversational reasoning queries prefixed with '?'
"""

from typing import Any, Dict, List
from ..base import OmniEngine, OmniResult
from ..context import OmniContext


class LLMEngine(OmniEngine):
    def can_handle(self, query: str, context: OmniContext) -> float:
        if query.strip().startswith("?"):
            return 1.0
        return 0.0

    async def execute(
        self, query: str, context: OmniContext
    ) -> List[OmniResult]:
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

    def get_mode_metadata(self) -> Dict[str, Any]:
        return {
            "mode": "llm",
            "glow_color": "#38BDF8",
            "placeholder": "Ask AI reasoning engine...",
            "icon": "sparkles",
        }
