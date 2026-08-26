"""
Data Models for Omni Engine Architecture
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SpatialContext:
    target_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: int = 0
    total_lines: int = 0
    head_excerpt: str = ""
    is_truncated: bool = False
    remaining_lines: int = 0
    is_binary: bool = False
    graph_neighbors: List[Dict[str, str]] = field(default_factory=list)
    cwd: str = ""
    timestamp: str = ""
    node_count: int = 0
