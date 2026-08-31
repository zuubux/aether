"""
Fuzzy Search Engine
Scores loaded canvas nodes by stem matching, archetype matching, and preview snippet line matching.
"""

from typing import Any, Dict, List, Optional, Union
from ..base import OmniEngine, OmniResult
from ..context import OmniContext


class FuzzySearchEngine(OmniEngine):
    def __init__(self, store: Optional[Any] = None):
        self.store = store

    def can_handle(self, query: str, context: OmniContext) -> float:
        q = query.strip()
        if not q:
            return 0.0
        if q.startswith(">") or q.startswith("?") or q.startswith("/"):
            return 0.0
        return 0.8

    async def execute(
        self, query: str, context: OmniContext
    ) -> List[OmniResult]:
        q_clean = query.strip().lower()
        if not q_clean:
            return []

        nodes = []
        if self.store and hasattr(self.store, "get_all_nodes"):
            nodes = self.store.get_all_nodes()
        elif context.metadata and "nodes" in context.metadata:
            nodes = context.metadata["nodes"]

        results: List[OmniResult] = []
        ext_query = q_clean.lstrip("*").removeprefix(".")

        for node in nodes:
            # Gather node text fields
            node_id = str(getattr(node, "id", getattr(node, "node_id", "")))
            file_name = getattr(node, "fileName", getattr(node, "file_name", ""))
            display_title = getattr(node, "display_title", getattr(node, "title", file_name))
            extension = getattr(node, "extension", "")
            archetype = getattr(node, "archetype", "document")
            path = getattr(node, "filePath", getattr(node, "path", ""))

            # Gather preview snippet line content
            content_str = str(getattr(node, "preview_text", getattr(node, "snippet", getattr(node, "content", getattr(node, "summary", getattr(node, "text", ""))))))

            fn_lower = file_name.lower()
            dt_lower = str(display_title).lower()
            ext_lower = str(extension).lower().removeprefix(".")
            arch_lower = str(archetype).lower()

            # Calculate match score (0.0 to 1.0)
            score = 0.0
            matched_snippet = getattr(node, "snippet", "")

            # Exact title or filename match
            if q_clean == fn_lower or q_clean == dt_lower:
                score = 1.0
            # Title or filename starts with query stem
            elif fn_lower.startswith(q_clean) or dt_lower.startswith(q_clean):
                score = 0.95
            # Substring in title or filename
            elif q_clean in fn_lower or q_clean in dt_lower:
                score = 0.85
            # Word token match
            elif any(q_clean in word for word in fn_lower.split("_") + dt_lower.split()):
                score = 0.75
            # Preview snippet line matching
            elif content_str and q_clean in content_str.lower():
                score = 0.70
                # Extract the matching line for snippet display
                for line in content_str.splitlines():
                    if q_clean in line.lower():
                        matched_snippet = line.strip()
                        break
            # Extension match
            elif ext_query and (ext_query == ext_lower or ext_query in ext_lower):
                score = 0.65
            # Archetype match
            elif q_clean in arch_lower or arch_lower in q_clean:
                score = 0.55

            if score > 0.0:
                result_item = OmniResult(
                    id=node_id,
                    title=display_title if display_title else file_name,
                    category=archetype,
                    score=score,
                    metadata={
                        "fileName": file_name,
                        "extension": extension,
                        "archetype": archetype,
                        "path": path,
                        "snippet": matched_snippet,
                        "node_id": node_id,
                    },
                    icon=extension if extension else archetype,
                )
                results.append(result_item)

        # Sort results by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def get_mode_metadata(self) -> Dict[str, Any]:
        return {
            "mode": "search",
            "glow_color": "#30363D",
            "placeholder": "Search nodes, content, or commands...",
            "icon": "search",
        }

