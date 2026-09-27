"""
Plate Engine - Payload Ingestion & Graph Parser
Parses raw IPC/Weaver dictionaries and events into canonical PlateNodePayload models,
hydrating relational topologies, temporal states, and geometry metrics.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .models import (
    PlateArchetype,
    PlateEdge,
    PlateGeometry,
    PlateNodePayload,
    TemporalState,
)

logger = logging.getLogger("aia_canvas.plate_engine.parser")


class PlatePayloadParser:
    """
    Ingestion parser mapping heterogeneous JSON-RPC frames, Weaver SQLite rows,
    and legacy Canvas dictionaries into strongly typed PlateNodePayload structures.
    """

    @staticmethod
    def parse_node(data: dict[str, Any]) -> PlateNodePayload:
        """
        Parses a single node dictionary into a PlateNodePayload.
        Raises ValueError if required identity fields cannot be resolved.
        """
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict for plate payload, got {type(data).__name__}")

        # 1. Resolve Identity
        raw_id = data.get("node_id") if data.get("node_id") is not None else data.get("id")
        if raw_id is None:
            raw_id = data.get("nodeId")
        if raw_id is None:
            raise ValueError("Payload missing required identifier ('node_id', 'id', or 'nodeId')")

        try:
            node_id = int(raw_id)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid plate ID value: {raw_id}") from exc

        # 2. File Path & Names
        raw_path = data.get("file_path") if data.get("file_path") is not None else data.get("filePath")
        if raw_path is None:
            raw_path = data.get("path", "")
        file_path = str(raw_path).strip()

        raw_name = data.get("file_name") if data.get("file_name") is not None else data.get("fileName")
        file_name = str(raw_name) if raw_name is not None else ""
        if not file_name and file_path:
            file_name = Path(file_path).name

        raw_title = data.get("display_title") if data.get("display_title") is not None else data.get("displayTitle")
        if raw_title is None:
            raw_title = data.get("title", "")
        display_title = str(raw_title).strip()

        raw_ext = data.get("extension")
        extension = str(raw_ext).strip() if raw_ext is not None else ""
        if not extension and file_path:
            extension = Path(file_path).suffix

        # 3. Size & Archetype
        raw_size = data.get("size_bytes") if data.get("size_bytes") is not None else data.get("sizeBytes")
        if raw_size is None:
            raw_size = data.get("size", 0)
        try:
            size_bytes = int(raw_size)
        except (ValueError, TypeError):
            size_bytes = 0

        raw_archetype = data.get("archetype")
        archetype = PlateArchetype.from_str(str(raw_archetype) if raw_archetype else None, extension)

        snippet = str(data.get("snippet", ""))

        # 4. Preview / Thumbnail
        raw_thumb = data.get("thumbnail_url") if data.get("thumbnail_url") is not None else data.get("thumbnailUrl")
        if raw_thumb is None:
            raw_thumb = data.get("thumbnail", "")
        thumbnail_url = str(raw_thumb).strip()

        # 5. Temporal State
        temporal_dict = data.get("temporal")
        if isinstance(temporal_dict, dict):
            temporal = TemporalState.from_dict(temporal_dict)
        else:
            temporal = TemporalState.from_dict(data)

        # 6. Geometry
        geometry_dict = data.get("geometry")
        if isinstance(geometry_dict, dict):
            geometry = PlateGeometry.from_dict(geometry_dict)
        else:
            geometry = PlateGeometry.from_dict(data)

        # 7. Mass / Cognitive Weight
        raw_mass = data.get("mass") if data.get("mass") is not None else data.get("focus")
        try:
            mass = float(raw_mass) if raw_mass is not None else 1.0
        except (ValueError, TypeError):
            mass = 1.0

        # 8. Extra Metadata Bag
        known_keys = {
            "node_id", "id", "nodeId", "file_path", "filePath", "path",
            "file_name", "fileName", "display_title", "displayTitle", "title",
            "extension", "size_bytes", "sizeBytes", "size", "archetype",
            "snippet", "thumbnail_url", "thumbnailUrl", "thumbnail",
            "temporal", "relationships", "geometry", "mass", "focus",
            "x", "y", "width", "height", "col_span", "row_span", "depth_z",
            "tier", "zone", "cluster_id", "clusterId", "is_pinned", "isPinned",
            "is_user_placed", "isUserPlaced", "last_interaction_epoch",
            "lastInteractionEpoch", "edges",
        }
        meta = {k: v for k, v in data.items() if k not in known_keys}
        if "metadata" in data and isinstance(data["metadata"], dict):
            meta.update(data["metadata"])

        payload = PlateNodePayload(
            node_id=node_id,
            file_path=file_path,
            file_name=file_name,
            display_title=display_title,
            extension=extension,
            size_bytes=size_bytes,
            archetype=archetype,
            snippet=snippet,
            thumbnail_url=thumbnail_url,
            temporal=temporal,
            geometry=geometry,
            mass=mass,
            metadata=meta,
        )

        # Parse pre-existing relationships if embedded
        rel_dict = data.get("relationships")
        if isinstance(rel_dict, dict):
            from .models import NodeRelationships
            payload.relationships = NodeRelationships.from_dict(rel_dict)

        return payload


    @classmethod
    def parse_nodes_batch(cls, items: Sequence[dict[str, Any]]) -> list[PlateNodePayload]:
        """
        Parses a sequence of raw node payloads, skipping invalid entries and logging warnings.
        """
        parsed: list[PlateNodePayload] = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict item at index {idx}: {type(item).__name__}")
                continue
            try:
                parsed.append(cls.parse_node(item))
            except Exception as e:
                logger.warning(f"Failed parsing item index {idx}: {e}")
        return parsed

    @staticmethod
    def parse_edge(data: dict[str, Any]) -> PlateEdge | None:
        """
        Parses a single graph edge dictionary. Returns None on validation failure.
        """
        if not isinstance(data, dict):
            return None
        try:
            return PlateEdge.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed parsing edge data {data}: {e}")
            return None

    @classmethod
    def parse_edges_batch(cls, items: Sequence[dict[str, Any]]) -> list[PlateEdge]:
        """Parses a sequence of raw edge payloads."""
        edges: list[PlateEdge] = []
        for item in items:
            edge = cls.parse_edge(item)
            if edge is not None:
                edges.append(edge)
        return edges

    @classmethod
    def hydrate_topology(
        cls,
        plates: dict[int, PlateNodePayload],
        edges: Sequence[dict[str, Any] | PlateEdge],
    ) -> None:
        """
        Hydrates bidirectional graph topology into plate relationships.
        Populates neighbor sets, incoming/outgoing counts, and edge lists.
        """
        for item in edges:
            edge = item if isinstance(item, PlateEdge) else cls.parse_edge(item)
            if edge is None:
                continue

            src = edge.source_id
            tgt = edge.target_id

            if src in plates:
                plates[src].relationships.add_edge(edge)
                plates[src].relationships.outgoing_count += 1
                plates[src].relationships.neighbor_ids.add(tgt)

            if tgt in plates:
                plates[tgt].relationships.add_edge(edge)
                plates[tgt].relationships.incoming_count += 1
                plates[tgt].relationships.neighbor_ids.add(src)

    @classmethod
    def parse_sync_payload(
        cls, payload: dict[str, Any]
    ) -> tuple[dict[int, PlateNodePayload], list[PlateEdge]]:
        """
        Processes a full sync payload (such as `get_all_nodes` response).
        Returns a dictionary of node_id -> PlateNodePayload (with hydrated topology)
        and the full list of parsed PlateEdges.
        """
        raw_nodes = payload.get("nodes", [])
        if isinstance(raw_nodes, dict):
            raw_nodes = list(raw_nodes.values())

        raw_edges = payload.get("edges", [])
        if isinstance(raw_edges, dict):
            raw_edges = list(raw_edges.values())

        nodes_list = cls.parse_nodes_batch(raw_nodes)
        plates_map = {n.node_id: n for n in nodes_list}

        edges_list = cls.parse_edges_batch(raw_edges)
        cls.hydrate_topology(plates_map, edges_list)

        return plates_map, edges_list


# Convenience module-level aliases
parse_plate_payload = PlatePayloadParser.parse_node
parse_plate_payloads_batch = PlatePayloadParser.parse_nodes_batch
parse_plate_edge = PlatePayloadParser.parse_edge
parse_plate_edges_batch = PlatePayloadParser.parse_edges_batch
hydrate_relationships = PlatePayloadParser.hydrate_topology

