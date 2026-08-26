"""
OmniContext Dataclass and Spatial Context Assembler
Holds query text, active selection state, and spatial file/graph telemetry context.
"""

from dataclasses import dataclass, field
import datetime
import mimetypes
import os
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional

from .models import SpatialContext


@dataclass
class OmniContext:
    raw_query: str
    focused_node_id: Optional[str] = None
    focused_node_path: Optional[str] = None
    selected_node_ids: List[str] = field(default_factory=list)
    typing_cadence_ms: float = 0.0



def _is_binary_file(path_str: str, mime_type: Optional[str]) -> bool:
    """Helper to determine if a file is binary using MIME types, extensions, and content probing."""
    if mime_type:
        main_type = mime_type.split("/", 1)[0] if "/" in mime_type else ""
        if main_type in ("image", "audio", "video", "font"):
            return True
        if mime_type in (
            "application/octet-stream",
            "application/pdf",
            "application/zip",
            "application/x-tar",
            "application/x-gzip",
            "application/x-executable",
            "application/x-sharedlib",
            "application/x-sqlite3",
            "application/java-archive",
        ):
            return True

    ext = Path(path_str).suffix.lower()
    binary_extensions = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".tiff",
        ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz",
        ".exe", ".so", ".dylib", ".dll", ".pyc", ".pyo", ".pyd", ".o", ".a",
        ".db", ".sqlite", ".sqlite3", ".bin", ".dat", ".iso", ".class",
        ".wasm", ".ttf", ".otf", ".woff", ".woff2",
    }
    if ext in binary_extensions:
        return True

    try:
        with open(path_str, "rb") as f:
            chunk = f.read(2048)
            if b"\x00" in chunk:
                return True
    except Exception:
        pass

    return False


def _query_graph_db(
    graph_db_path: Optional[str], target_path: Optional[str]
) -> tuple[List[Dict[str, str]], int]:
    """Queries weaver_graph.db in read-only mode for node count and target neighbors."""
    neighbors: List[Dict[str, str]] = []
    node_count = 0

    if not graph_db_path:
        default_db = Path.home() / ".config" / "aether" / "weaver_graph.db"
        if default_db.exists():
            graph_db_path = str(default_db)
        elif Path("weaver_graph.db").exists():
            graph_db_path = "weaver_graph.db"

    if not graph_db_path or not os.path.exists(graph_db_path):
        return neighbors, node_count

    try:
        db_abs = os.path.abspath(graph_db_path)
        uri = f"file:{db_abs}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=1.0)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM nodes")
            row = cursor.fetchone()
            if row:
                node_count = row[0]
        except sqlite3.Error:
            pass

        if target_path:
            node_id = None
            cursor.execute("SELECT id FROM nodes WHERE file_path = ?", (target_path,))
            row = cursor.fetchone()
            if row:
                node_id = row[0]
            else:
                cursor.execute(
                    "SELECT id FROM nodes WHERE file_path LIKE ?",
                    (f"%{Path(target_path).name}",)
                )
                row = cursor.fetchone()
                if row:
                    node_id = row[0]

            if node_id is not None:
                query = """
                    SELECT n.file_path, e.edge_type
                    FROM edges e
                    JOIN nodes n ON (
                        CASE WHEN e.source_id = ? THEN e.target_id ELSE e.source_id END = n.id
                    )
                    WHERE e.source_id = ? OR e.target_id = ?
                    ORDER BY e.weight DESC
                    LIMIT 5
                """
                cursor.execute(query, (node_id, node_id, node_id))
                for r in cursor.fetchall():
                    neighbors.append({"neighbor_path": r[0], "relation_type": r[1]})

        conn.close()
    except Exception:
        pass

    return neighbors, node_count


def assemble_spatial_context(
    focused_node_id: Optional[str] = None,
    graph_db_path: Optional[str] = None,
    focused_node_path: Optional[str] = None,
    store: Optional[Any] = None,
) -> SpatialContext:
    """Assembles spatial file and graph context for the focused node or empty canvas."""
    cwd = os.getcwd()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    target_path: Optional[str] = None

    if focused_node_path and isinstance(focused_node_path, str) and focused_node_path.strip():
        candidate_path = Path(focused_node_path).expanduser()
        if candidate_path.exists() and candidate_path.is_file():
            target_path = str(candidate_path.resolve())

    if not target_path and focused_node_id and isinstance(focused_node_id, str) and focused_node_id.strip():
        candidate_path = Path(focused_node_id).expanduser()
        if candidate_path.exists() and candidate_path.is_file():
            target_path = str(candidate_path.resolve())
        elif store:
            try:
                n_id = int(focused_node_id)
                node = store.get_node(n_id)
                if node:
                    f_path = getattr(node, "filePath", None) or getattr(node, "path", None)
                    if f_path:
                        cand = Path(f_path).expanduser()
                        if cand.exists() and cand.is_file():
                            target_path = str(cand.resolve())
            except (ValueError, TypeError):
                pass

    graph_neighbors, total_node_count = _query_graph_db(graph_db_path, target_path)

    if not target_path:
        return SpatialContext(
            target_path=None,
            mime_type=None,
            file_size=0,
            total_lines=0,
            head_excerpt="",
            is_truncated=False,
            remaining_lines=0,
            is_binary=False,
            graph_neighbors=[],
            cwd=cwd,
            timestamp=timestamp,
            node_count=total_node_count,
        )

    file_size = os.path.getsize(target_path)
    guessed_mime, _ = mimetypes.guess_type(target_path)
    is_binary = _is_binary_file(target_path, guessed_mime)

    if is_binary:
        mime_type = guessed_mime or "application/octet-stream"
        return SpatialContext(
            target_path=target_path,
            mime_type=mime_type,
            file_size=file_size,
            total_lines=0,
            head_excerpt="",
            is_truncated=False,
            remaining_lines=0,
            is_binary=True,
            graph_neighbors=graph_neighbors,
            cwd=cwd,
            timestamp=timestamp,
            node_count=total_node_count,
        )

    mime_type = guessed_mime or "text/plain"
    try:
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception:
        all_lines = []

    total_lines = len(all_lines)
    head_lines = all_lines[:50]
    head_str = "".join(head_lines)

    head_bytes = head_str.encode("utf-8")
    if len(head_bytes) > 2048:
        truncated_bytes = head_bytes[:2048]
        head_excerpt = truncated_bytes.decode("utf-8", errors="ignore")
        included_line_count = len(head_excerpt.splitlines())
        is_truncated = True
        remaining_lines = max(0, total_lines - included_line_count)
    else:
        head_excerpt = head_str
        if total_lines > 50:
            is_truncated = True
            remaining_lines = total_lines - 50
        else:
            is_truncated = False
            remaining_lines = 0

    return SpatialContext(
        target_path=target_path,
        mime_type=mime_type,
        file_size=file_size,
        total_lines=total_lines,
        head_excerpt=head_excerpt,
        is_truncated=is_truncated,
        remaining_lines=remaining_lines,
        is_binary=False,
        graph_neighbors=graph_neighbors,
        cwd=cwd,
        timestamp=timestamp,
        node_count=total_node_count,
    )


def format_spatial_envelope(context: SpatialContext) -> str:
    """Serializes SpatialContext into a clean [Spatial Context] Markdown envelope."""
    lines = ["[Spatial Context]"]
    if context.target_path:
        lines.append(f"- Target Path: {context.target_path}")
        if context.mime_type:
            lines.append(f"- MIME Type: {context.mime_type}")
        lines.append(f"- File Size: {context.file_size} bytes")
        if context.is_binary:
            lines.append("- Type: Binary Asset")
        else:
            lines.append(f"- Total Lines: {context.total_lines}")
            if context.is_truncated:
                lines.append(f"- Truncated: True ({context.remaining_lines} remaining lines)")
            else:
                lines.append("- Truncated: False")

        if context.graph_neighbors:
            lines.append("- Graph Neighbors:")
            for neighbor in context.graph_neighbors:
                path = neighbor.get("neighbor_path") or neighbor.get("path") or ""
                rel = neighbor.get("relation_type") or neighbor.get("edge_type") or "connected"
                lines.append(f"  - {path} ({rel})")

        if context.head_excerpt and not context.is_binary:
            lines.append("```")
            lines.append(context.head_excerpt.rstrip("\n"))
            lines.append("```")
    else:
        lines.append("- Target Node: None (Empty Canvas)")
        if context.node_count > 0:
            lines.append(f"- Canvas Node Count: {context.node_count}")

    lines.append(f"- CWD: {context.cwd}")
    lines.append(f"- Timestamp: {context.timestamp}")

    return "\n".join(lines)


