"""
Fuzzy Search Engine
Scores loaded canvas nodes by stem matching, archetype matching, and preview snippet line matching.
Directly connects to Weaver SQLite DB (weaver_graph.db) when in-memory store is unpopulated.
"""

import html
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Union
from ..base import OmniEngine, OmniResult
from ..context import OmniContext


def strip_html_tags(text: str) -> str:
    """Strips HTML markup and decodes entities into clean text lines."""
    if not text:
        return ""
    clean = re.sub(r"<(?:br|/p|/div|/pre)[^>]*>", "\n", text, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = html.unescape(clean)
    lines = [line.strip() for line in clean.splitlines() if line.strip()]
    return "\n".join(lines)


class FuzzySearchEngine(OmniEngine):
    def __init__(
        self,
        store: Optional[Any] = None,
        db_path: Optional[Union[str, Path]] = None,
    ):
        self.store = store
        self.db_path = (
            Path(db_path)
            if db_path is not None
            else (Path.home() / ".config" / "aether" / "weaver_graph.db")
        )

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

        # If nodes is empty from self.store / context, query SQLite directly
        if not nodes:
            db_path = self.db_path
            if isinstance(db_path, str):
                db_path = Path(db_path)
            if db_path.exists():
                try:
                    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id, file_path, extension, archetype, snippet FROM nodes;")
                        rows = cursor.fetchall()
                        nodes = [
                            {
                                "id": row[0],
                                "file_path": row[1],
                                "extension": row[2],
                                "archetype": row[3],
                                "snippet": row[4],
                            }
                            for row in rows
                        ]
                except Exception:
                    nodes = []

        results: List[OmniResult] = []
        ext_query = q_clean.lstrip("*").removeprefix(".")

        for node in nodes:
            # Gather node text fields
            if isinstance(node, dict):
                node_id = str(node.get("id") if node.get("id") is not None else node.get("node_id", ""))
                path = str(node.get("file_path") or node.get("filePath") or node.get("path", "") or "")
                file_name = str(node.get("fileName") or node.get("file_name", "") or "")
                if not file_name and path:
                    file_name = os.path.basename(path)
                display_title = str(node.get("display_title") or node.get("title") or "")
                if not display_title and file_name:
                    display_title = file_name
                extension = str(node.get("extension") or "")
                if not extension and file_name:
                    extension = os.path.splitext(file_name)[1]
                archetype = str(node.get("archetype") or "document")
                raw_snippet = str(node.get("snippet", "") or node.get("preview_text", "") or node.get("content", ""))
            else:
                node_id = str(getattr(node, "id", getattr(node, "node_id", "")))
                path = str(getattr(node, "filePath", getattr(node, "path", getattr(node, "file_path", ""))))
                file_name = str(getattr(node, "fileName", getattr(node, "file_name", "")))
                if not file_name and path:
                    file_name = os.path.basename(path)
                display_title = str(getattr(node, "display_title", getattr(node, "title", file_name)))
                if not display_title and file_name:
                    display_title = file_name
                extension = str(getattr(node, "extension", ""))
                if not extension and file_name:
                    extension = os.path.splitext(file_name)[1]
                archetype = str(getattr(node, "archetype", "document"))
                raw_snippet = str(getattr(node, "preview_text", getattr(node, "snippet", getattr(node, "content", getattr(node, "summary", getattr(node, "text", ""))))))

            # Strip HTML tags from snippet when calculating snippet match scores
            clean_snippet = strip_html_tags(raw_snippet)
            content_str = clean_snippet if clean_snippet else raw_snippet
            clean_lines = [l for l in clean_snippet.splitlines() if l.strip()]
            default_snippet = clean_lines[0] if clean_lines else (raw_snippet.strip() if raw_snippet else "")

            fn_lower = file_name.lower()
            dt_lower = display_title.lower()
            ext_lower = str(extension).lower().removeprefix(".")
            arch_lower = str(archetype).lower()

            # Calculate match score (0.0 to 1.0)
            score = 0.0
            matched_snippet = default_snippet

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
            elif any(q_clean in word for word in fn_lower.replace(".", "_").split("_") + dt_lower.split()):
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

