"""
Plate Engine - Foundational Data Models
Authoritative, strictly typed data structures representing canonical plates, archetypes,
temporal lifecycles, relational topology, and spatial geometry.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PlateArchetype(str, Enum):
    """
    Canonical archetype categories for plates across the Aether ecosystem.
    """
    DOCUMENT = "document"
    CODE = "code"
    IMAGE = "image"
    MEDIA = "media"
    DATA = "data"
    ARCHIVE = "archive"
    MODEL = "model"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, val: str | None, extension: str | None = None) -> PlateArchetype:
        """
        Safely resolve an archetype enum member from a raw string identifier
        or fallback to file extension inference.
        """
        norm_val = (val or "").strip().lower()

        mapping: dict[str, PlateArchetype] = {
            "document": cls.DOCUMENT,
            "doc": cls.DOCUMENT,
            "markdown": cls.DOCUMENT,
            "text": cls.DOCUMENT,
            "code": cls.CODE,
            "script": cls.CODE,
            "image": cls.IMAGE,
            "img": cls.IMAGE,
            "media": cls.MEDIA,
            "audio": cls.MEDIA,
            "video": cls.MEDIA,
            "data": cls.DATA,
            "table": cls.DATA,
            "spreadsheet": cls.DATA,
            "database": cls.DATA,
            "archive": cls.ARCHIVE,
            "model": cls.MODEL,
            "asset": cls.MODEL,
            "3d": cls.MODEL,
        }

        if norm_val in mapping:
            return mapping[norm_val]

        ext = (extension or "").strip().lower()
        if ext:
            if not ext.startswith("."):
                ext = f".{ext}"
            return cls.from_extension(ext)

        return cls.UNKNOWN

    @classmethod
    def from_extension(cls, ext: str) -> PlateArchetype:
        """
        Deduce archetype from a file extension.
        """
        norm_ext = ext.lower()
        if not norm_ext.startswith("."):
            norm_ext = f".{norm_ext}"

        ext_map: dict[str, PlateArchetype] = {
            # Document
            ".md": cls.DOCUMENT, ".markdown": cls.DOCUMENT, ".txt": cls.DOCUMENT,
            ".pdf": cls.DOCUMENT, ".docx": cls.DOCUMENT, ".doc": cls.DOCUMENT,
            ".odt": cls.DOCUMENT, ".rtf": cls.DOCUMENT, ".org": cls.DOCUMENT,
            ".epub": cls.DOCUMENT, ".tex": cls.DOCUMENT, ".rst": cls.DOCUMENT,
            # Code
            ".py": cls.CODE, ".js": cls.CODE, ".ts": cls.CODE, ".jsx": cls.CODE,
            ".tsx": cls.CODE, ".c": cls.CODE, ".cpp": cls.CODE, ".h": cls.CODE,
            ".hpp": cls.CODE, ".rs": cls.CODE, ".go": cls.CODE, ".java": cls.CODE,
            ".kt": cls.CODE, ".rb": cls.CODE, ".php": cls.CODE, ".sh": cls.CODE,
            ".bash": cls.CODE, ".zsh": cls.CODE, ".sql": cls.CODE, ".html": cls.CODE,
            ".css": cls.CODE, ".scss": cls.CODE, ".vue": cls.CODE, ".svelte": cls.CODE,
            ".zig": cls.CODE, ".swift": cls.CODE, ".lua": cls.CODE,
            # Image
            ".png": cls.IMAGE, ".jpg": cls.IMAGE, ".jpeg": cls.IMAGE,
            ".gif": cls.IMAGE, ".webp": cls.IMAGE, ".svg": cls.IMAGE,
            ".ico": cls.IMAGE, ".bmp": cls.IMAGE, ".tiff": cls.IMAGE,
            ".tif": cls.IMAGE, ".avif": cls.IMAGE,
            # Media
            ".mp4": cls.MEDIA, ".mkv": cls.MEDIA, ".avi": cls.MEDIA,
            ".mov": cls.MEDIA, ".webm": cls.MEDIA, ".flv": cls.MEDIA,
            ".wmv": cls.MEDIA, ".mp3": cls.MEDIA, ".flac": cls.MEDIA,
            ".wav": cls.MEDIA, ".ogg": cls.MEDIA, ".aac": cls.MEDIA,
            ".m4a": cls.MEDIA, ".opus": cls.MEDIA,
            # Data
            ".csv": cls.DATA, ".tsv": cls.DATA, ".json": cls.DATA,
            ".yaml": cls.DATA, ".yml": cls.DATA, ".toml": cls.DATA,
            ".sqlite": cls.DATA, ".sqlite3": cls.DATA, ".db": cls.DATA,
            ".xlsx": cls.DATA, ".xls": cls.DATA, ".parquet": cls.DATA,
            ".feather": cls.DATA, ".arrow": cls.DATA, ".xml": cls.DATA,
            ".ini": cls.DATA, ".env": cls.DATA,
            # Archive
            ".zip": cls.ARCHIVE, ".tar": cls.ARCHIVE, ".gz": cls.ARCHIVE,
            ".bz2": cls.ARCHIVE, ".xz": cls.ARCHIVE, ".zst": cls.ARCHIVE,
            ".7z": cls.ARCHIVE, ".rar": cls.ARCHIVE, ".tgz": cls.ARCHIVE,
            # 3D / Asset
            ".step": cls.MODEL, ".stp": cls.MODEL, ".obj": cls.MODEL,
            ".stl": cls.MODEL, ".fbx": cls.MODEL, ".blend": cls.MODEL,
            ".gltf": cls.MODEL, ".glb": cls.MODEL,
        }
        return ext_map.get(norm_ext, cls.UNKNOWN)

    @property
    def is_visual(self) -> bool:
        """Indicates if archetype primarily carries visual/media rendering."""
        return self in (PlateArchetype.IMAGE, PlateArchetype.MEDIA, PlateArchetype.MODEL)

    @property
    def is_textual(self) -> bool:
        """Indicates if archetype primarily carries text/syntax rendering."""
        return self in (PlateArchetype.DOCUMENT, PlateArchetype.CODE, PlateArchetype.DATA)



class PlateEdgeCategory(str, Enum):
    """Broad classification category of a graph relationship edge."""
    TOPOLOGICAL = "topological"
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"


class PlateEdgeType(str, Enum):
    """Specific edge relation subtype."""
    EXPLICIT = "explicit"
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    WIKILINK = "wikilink"
    CO_ACCESS = "co_access"


@dataclass(slots=True)
class PlateEdge:
    """
    Representation of a relational graph edge between two plate nodes.
    """
    source_id: int
    target_id: int
    edge_type: str = "explicit"
    weight: float = 1.0
    category: str = "topological"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "sourceId": self.source_id,
            "targetId": self.target_id,
            "edge_type": self.edge_type,
            "edgeType": self.edge_type,
            "weight": self.weight,
            "category": self.category,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlateEdge:
        src = int(d.get("source_id") or d.get("sourceId") or d.get("source", 0))
        tgt = int(d.get("target_id") or d.get("targetId") or d.get("target", 0))
        e_type = str(d.get("edge_type") or d.get("edgeType") or "explicit")
        weight = float(d.get("weight", 1.0))
        category = str(d.get("category") or ("temporal" if e_type == "temporal" else "topological"))
        meta = d.get("metadata")
        return cls(
            source_id=src,
            target_id=tgt,
            edge_type=e_type,
            weight=weight,
            category=category,
            metadata=dict(meta) if isinstance(meta, dict) else {},
        )


@dataclass(slots=True)
class TemporalState:
    """
    Tracks time-series decay, interaction history, and pinning state.
    """
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_interaction_epoch: float = field(default_factory=time.time)
    interaction_count: int = 0
    dwell_time_seconds: float = 0.0
    recency_score: float = 1.0
    is_pinned: bool = False
    is_user_placed: bool = False

    def touch(self, epoch: float | None = None) -> None:
        """Records an active user interaction touch."""
        ts = epoch if epoch is not None else time.time()
        self.last_interaction_epoch = ts
        self.updated_at = ts
        self.interaction_count += 1
        self.recency_score = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_interaction_epoch": self.last_interaction_epoch,
            "lastInteractionEpoch": self.last_interaction_epoch,
            "interaction_count": self.interaction_count,
            "interactionCount": self.interaction_count,
            "dwell_time_seconds": self.dwell_time_seconds,
            "dwellTimeSeconds": self.dwell_time_seconds,
            "recency_score": self.recency_score,
            "recencyScore": self.recency_score,
            "is_pinned": self.is_pinned,
            "isPinned": self.is_pinned,
            "is_user_placed": self.is_user_placed,
            "isUserPlaced": self.is_user_placed,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TemporalState:
        now = time.time()
        return cls(
            created_at=float(d.get("created_at") or d.get("createdAt") or now),
            updated_at=float(d.get("updated_at") or d.get("updatedAt") or now),
            last_interaction_epoch=float(
                d.get("last_interaction_epoch") or d.get("lastInteractionEpoch") or now
            ),
            interaction_count=int(d.get("interaction_count") or d.get("interactionCount") or 0),
            dwell_time_seconds=float(d.get("dwell_time_seconds") or d.get("dwellTimeSeconds") or 0.0),
            recency_score=float(d.get("recency_score") or d.get("recencyScore") or 1.0),
            is_pinned=bool(d.get("is_pinned") or d.get("isPinned") or False),
            is_user_placed=bool(d.get("is_user_placed") or d.get("isUserPlaced") or False),
        )




@dataclass(slots=True)
class NodeRelationships:
    """
    Topology, edges, neighbors, and cluster affiliation for a plate.
    """
    edges: list[PlateEdge] = field(default_factory=list)
    neighbor_ids: set[int] = field(default_factory=set)
    incoming_count: int = 0
    outgoing_count: int = 0
    cluster_id: int = -1
    cluster_label: str = ""
    semantic_neighbors: list[tuple[int, float]] = field(default_factory=list)

    def add_edge(self, edge: PlateEdge) -> None:
        """Appends an edge and maintains neighbor references."""
        self.edges.append(edge)
        self.neighbor_ids.add(edge.source_id)
        self.neighbor_ids.add(edge.target_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edges": [e.to_dict() for e in self.edges],
            "neighbor_ids": sorted(list(self.neighbor_ids)),
            "neighborIds": sorted(list(self.neighbor_ids)),
            "incoming_count": self.incoming_count,
            "outgoing_count": self.outgoing_count,
            "cluster_id": self.cluster_id,
            "clusterId": self.cluster_id,
            "cluster_label": self.cluster_label,
            "semantic_neighbors": [list(item) for item in self.semantic_neighbors],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NodeRelationships:
        raw_edges = d.get("edges", [])
        parsed_edges = [
            PlateEdge.from_dict(e) if isinstance(e, dict) else e
            for e in raw_edges
            if isinstance(e, (dict, PlateEdge))
        ]
        raw_neighbors = d.get("neighbor_ids") or d.get("neighborIds") or []
        neighbor_set = {int(n) for n in raw_neighbors}

        for e in parsed_edges:
            if isinstance(e, PlateEdge):
                neighbor_set.add(e.source_id)
                neighbor_set.add(e.target_id)

        raw_semantic = d.get("semantic_neighbors", [])
        semantic_list: list[tuple[int, float]] = []
        for item in raw_semantic:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                semantic_list.append((int(item[0]), float(item[1])))

        return cls(
            edges=parsed_edges,
            neighbor_ids=neighbor_set,
            incoming_count=int(d.get("incoming_count", 0)),
            outgoing_count=int(d.get("outgoing_count", 0)),
            cluster_id=int(d.get("cluster_id") or d.get("clusterId") or -1),
            cluster_label=str(d.get("cluster_label", "")),
            semantic_neighbors=semantic_list,
        )


@dataclass(slots=True)
class PlateGeometry:
    """
    Spatial layout metrics and bento grid positioning.
    """
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    col_span: int = 1
    row_span: int = 1
    depth_z: float = 0.0
    tier: float = 3.0
    zone: int = 2  # 0: Desk/Focal, 1: Mid-field/Shelf, 2: Horizon

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "col_span": self.col_span,
            "colSpan": self.col_span,
            "row_span": self.row_span,
            "rowSpan": self.row_span,
            "depth_z": self.depth_z,
            "depthZ": self.depth_z,
            "tier": self.tier,
            "zone": self.zone,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlateGeometry:
        return cls(
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            width=float(d.get("width", 0.0)),
            height=float(d.get("height", 0.0)),
            col_span=int(d.get("col_span") or d.get("colSpan") or 1),
            row_span=int(d.get("row_span") or d.get("rowSpan") or 1),
            depth_z=float(d.get("depth_z") or d.get("depthZ") or 0.0),
            tier=float(d.get("tier", 3.0)),
            zone=int(d.get("zone", 2)),
        )




@dataclass(slots=True)
class PlateNodePayload:
    """
    Canonical data model representing an interactive Plate in the Aether Canvas.
    Encapsulates raw Weaver file properties, semantic archetypes, temporal lifecycles,
    graph relationship topology, and layout geometry.
    """
    node_id: int
    file_path: str
    file_name: str = ""
    display_title: str = ""
    extension: str = ""
    size_bytes: int = 0
    archetype: PlateArchetype = PlateArchetype.DOCUMENT
    snippet: str = ""
    thumbnail_url: str = ""
    temporal: TemporalState = field(default_factory=TemporalState)
    relationships: NodeRelationships = field(default_factory=NodeRelationships)
    geometry: PlateGeometry = field(default_factory=PlateGeometry)
    mass: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.file_name and self.file_path:
            self.file_name = Path(self.file_path).name

        if not self.extension and self.file_path:
            self.extension = Path(self.file_path).suffix

        if not self.display_title:
            self.display_title = self._compute_default_title()

    def _compute_default_title(self) -> str:
        """Derives a clean human-friendly display title."""
        name = self.file_name or (Path(self.file_path).name if self.file_path else "")
        if not name:
            return ""

        if name.startswith(".") and name.count(".") == 1:
            return name

        compound_suffixes = ('.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst')
        for suffix in compound_suffixes:
            if name.lower().endswith(suffix):
                return name[:-len(suffix)]

        return Path(name).stem

    @property
    def is_visual(self) -> bool:
        """Returns True if plate archetype is visual."""
        return self.archetype.is_visual

    @property
    def is_textual(self) -> bool:
        """Returns True if plate archetype is text/code/data."""
        return self.archetype.is_textual

    @property
    def is_pinned(self) -> bool:
        """Convenience accessor for pinned state."""
        return self.temporal.is_pinned

    @property
    def preview_path(self) -> str:
        """
        Resolved path for UI image/media preview surfaces.
        Prefers generated thumbnail URL if set, otherwise file_path for visual archetypes.
        """
        if self.thumbnail_url:
            return self.thumbnail_url
        if self.is_visual:
            return self.file_path
        return ""


    def to_dict(self) -> dict[str, Any]:
        """
        Serializes to a dictionary schema compatible with QML Bridge and IPC layers.
        """
        return {
            "id": self.node_id,
            "node_id": self.node_id,
            "nodeId": self.node_id,
            "file_path": self.file_path,
            "filePath": self.file_path,
            "path": self.file_path,
            "file_name": self.file_name,
            "fileName": self.file_name,
            "display_title": self.display_title,
            "displayTitle": self.display_title,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "sizeBytes": self.size_bytes,
            "archetype": self.archetype.value,
            "snippet": self.snippet,
            "thumbnail_url": self.thumbnail_url,
            "thumbnailUrl": self.thumbnail_url,
            "thumbnail": self.thumbnail_url,
            "preview_path": self.preview_path,
            "previewUrl": self.preview_path,
            "mass": self.mass,
            "focus": self.mass,
            "temporal": self.temporal.to_dict(),
            "relationships": self.relationships.to_dict(),
            "geometry": self.geometry.to_dict(),
            # Flattened fields for QML / legacy compatibility
            "x": self.geometry.x,
            "y": self.geometry.y,
            "tier": self.geometry.tier,
            "zone": self.geometry.zone,
            "cluster_id": self.relationships.cluster_id,
            "clusterId": self.relationships.cluster_id,
            "is_pinned": self.temporal.is_pinned,
            "isPinned": self.temporal.is_pinned,
            "is_user_placed": self.temporal.is_user_placed,
            "isUserPlaced": self.temporal.is_user_placed,
            "last_interaction_epoch": self.temporal.last_interaction_epoch,
            "lastInteractionEpoch": self.temporal.last_interaction_epoch,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlateNodePayload:
        """
        Reconstructs a PlateNodePayload instance from a serialized dictionary.
        """
        raw_id = d.get("node_id") if d.get("node_id") is not None else d.get("id")
        if raw_id is None:
            raw_id = d.get("nodeId", 0)
        node_id = int(raw_id)

        file_path = str(d.get("file_path") or d.get("filePath") or d.get("path") or "")
        extension = str(d.get("extension") or (Path(file_path).suffix if file_path else ""))

        raw_archetype = d.get("archetype")
        archetype = PlateArchetype.from_str(str(raw_archetype) if raw_archetype else None, extension)

        temporal = (
            TemporalState.from_dict(d["temporal"])
            if isinstance(d.get("temporal"), dict)
            else TemporalState.from_dict(d)
        )

        relationships = (
            NodeRelationships.from_dict(d["relationships"])
            if isinstance(d.get("relationships"), dict)
            else NodeRelationships.from_dict(d)
        )

        geometry = (
            PlateGeometry.from_dict(d["geometry"])
            if isinstance(d.get("geometry"), dict)
            else PlateGeometry.from_dict(d)
        )

        return cls(
            node_id=node_id,
            file_path=file_path,
            file_name=str(d.get("file_name") or d.get("fileName") or ""),
            display_title=str(d.get("display_title") or d.get("displayTitle") or ""),
            extension=extension,
            size_bytes=int(d.get("size_bytes") or d.get("sizeBytes") or 0),
            archetype=archetype,
            snippet=str(d.get("snippet", "")),
            thumbnail_url=str(d.get("thumbnail_url") or d.get("thumbnailUrl") or d.get("thumbnail") or ""),
            temporal=temporal,
            relationships=relationships,
            geometry=geometry,
            mass=float(d.get("mass") or d.get("focus") or 1.0),
            metadata=dict(d.get("metadata", {})) if isinstance(d.get("metadata"), dict) else {},
        )

