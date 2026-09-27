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
        src_val = d.get("source_id") if d.get("source_id") is not None else d.get("sourceId")
        if src_val is None:
            src_val = d.get("source", 0)
        src = int(src_val)

        tgt_val = d.get("target_id") if d.get("target_id") is not None else d.get("targetId")
        if tgt_val is None:
            tgt_val = d.get("target", 0)
        tgt = int(tgt_val)

        e_type_val = d.get("edge_type") if d.get("edge_type") is not None else d.get("edgeType")
        e_type = str(e_type_val) if e_type_val is not None else "explicit"

        weight_val = d.get("weight")
        weight = float(weight_val) if weight_val is not None else 1.0

        category_val = d.get("category")
        category = str(category_val) if category_val is not None else ("temporal" if e_type == "temporal" else "topological")

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
        created_at_val = d.get("created_at") if d.get("created_at") is not None else d.get("createdAt")
        updated_at_val = d.get("updated_at") if d.get("updated_at") is not None else d.get("updatedAt")
        last_interaction_val = (
            d.get("last_interaction_epoch")
            if d.get("last_interaction_epoch") is not None
            else d.get("lastInteractionEpoch")
        )
        interaction_count_val = (
            d.get("interaction_count")
            if d.get("interaction_count") is not None
            else d.get("interactionCount")
        )
        dwell_time_val = (
            d.get("dwell_time_seconds")
            if d.get("dwell_time_seconds") is not None
            else d.get("dwellTimeSeconds")
        )
        recency_score_val = (
            d.get("recency_score")
            if d.get("recency_score") is not None
            else d.get("recencyScore")
        )
        is_pinned_val = d.get("is_pinned") if d.get("is_pinned") is not None else d.get("isPinned")
        is_user_placed_val = (
            d.get("is_user_placed")
            if d.get("is_user_placed") is not None
            else d.get("isUserPlaced")
        )

        return cls(
            created_at=float(created_at_val) if created_at_val is not None else now,
            updated_at=float(updated_at_val) if updated_at_val is not None else now,
            last_interaction_epoch=float(last_interaction_val) if last_interaction_val is not None else now,
            interaction_count=int(interaction_count_val) if interaction_count_val is not None else 0,
            dwell_time_seconds=float(dwell_time_val) if dwell_time_val is not None else 0.0,
            recency_score=float(recency_score_val) if recency_score_val is not None else 1.0,
            is_pinned=bool(is_pinned_val) if is_pinned_val is not None else False,
            is_user_placed=bool(is_user_placed_val) if is_user_placed_val is not None else False,
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
        raw_neighbors = d.get("neighbor_ids") if d.get("neighbor_ids") is not None else d.get("neighborIds")
        neighbor_set = {int(n) for n in raw_neighbors} if raw_neighbors is not None else set()

        for e in parsed_edges:
            if isinstance(e, PlateEdge):
                neighbor_set.add(e.source_id)
                neighbor_set.add(e.target_id)

        raw_semantic = d.get("semantic_neighbors", [])
        semantic_list: list[tuple[int, float]] = []
        for item in raw_semantic:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                semantic_list.append((int(item[0]), float(item[1])))

        cluster_id_val = d.get("cluster_id") if d.get("cluster_id") is not None else d.get("clusterId")

        return cls(
            edges=parsed_edges,
            neighbor_ids=neighbor_set,
            incoming_count=int(d.get("incoming_count", 0)),
            outgoing_count=int(d.get("outgoing_count", 0)),
            cluster_id=int(cluster_id_val) if cluster_id_val is not None else -1,
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
        col_span_val = d.get("col_span") if d.get("col_span") is not None else d.get("colSpan")
        row_span_val = d.get("row_span") if d.get("row_span") is not None else d.get("rowSpan")
        depth_z_val = d.get("depth_z") if d.get("depth_z") is not None else d.get("depthZ")

        return cls(
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            width=float(d.get("width", 0.0)),
            height=float(d.get("height", 0.0)),
            col_span=int(col_span_val) if col_span_val is not None else 1,
            row_span=int(row_span_val) if row_span_val is not None else 1,
            depth_z=float(depth_z_val) if depth_z_val is not None else 0.0,
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

        raw_path = d.get("file_path") if d.get("file_path") is not None else d.get("filePath")
        if raw_path is None:
            raw_path = d.get("path", "")
        file_path = str(raw_path)

        extension = str(d.get("extension") if d.get("extension") is not None else (Path(file_path).suffix if file_path else ""))

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

        raw_name = d.get("file_name") if d.get("file_name") is not None else d.get("fileName")
        file_name = str(raw_name) if raw_name is not None else ""

        raw_title = d.get("display_title") if d.get("display_title") is not None else d.get("displayTitle")
        display_title = str(raw_title) if raw_title is not None else ""

        raw_size = d.get("size_bytes") if d.get("size_bytes") is not None else d.get("sizeBytes")
        size_bytes = int(raw_size) if raw_size is not None else 0

        raw_thumb = d.get("thumbnail_url") if d.get("thumbnail_url") is not None else d.get("thumbnailUrl")
        if raw_thumb is None:
            raw_thumb = d.get("thumbnail", "")
        thumbnail_url = str(raw_thumb)

        raw_mass = d.get("mass") if d.get("mass") is not None else d.get("focus")
        mass = float(raw_mass) if raw_mass is not None else 1.0

        metadata = dict(d.get("metadata", {})) if isinstance(d.get("metadata"), dict) else {}

        return cls(
            node_id=node_id,
            file_path=file_path,
            file_name=file_name,
            display_title=display_title,
            extension=extension,
            size_bytes=size_bytes,
            archetype=archetype,
            snippet=str(d.get("snippet", "")),
            thumbnail_url=thumbnail_url,
            temporal=temporal,
            relationships=relationships,
            geometry=geometry,
            mass=mass,
            metadata=metadata,
        )

