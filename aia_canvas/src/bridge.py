"""
Aether Canvas - Python to QML Bridge
Live temporal co-attention ingestion, priority edge sorting, and telemetry.
"""

import math
import time
import logging
import subprocess
from typing import List, Optional, Set, Dict, Any
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, QTimer

from models import Node, Edge
from store import GraphStore
from ipc.client import WeaverIPCClient
from physics.engine import PhysicsEngine
from utils.security import canonicalize_safe_path

logger = logging.getLogger("aia_canvas.bridge")


class CanvasBridge(QObject):
    nodesChanged = pyqtSignal()
    edgesChanged = pyqtSignal()
    selectedNodeChanged = pyqtSignal(int)
    hoveredNodeChanged = pyqtSignal(int)
    connectionStatusChanged = pyqtSignal(bool)
    workbenchDimensionsChanged = pyqtSignal()
    apertureChanged = pyqtSignal(float)
    clusterHalosChanged = pyqtSignal()
    telemetryChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.store = GraphStore()
        self.physics = PhysicsEngine()

        self._selected_node_id: int = 0
        self._hovered_node_id: int = 0
        self._is_connected = False
        
        self._cached_first_degree: Set[int] = set()
        self._cached_second_degree: Set[int] = set()
        self._cached_second_degree_parent: Dict[int, int] = {}
        self._cached_focal_weights: Dict[int, float] = {}

        self._aperture: float = 1.0
        self._workbench_width: float = 1600.0
        self._workbench_height: float = 1000.0

        self.physics.set_focal_card_dimensions(self._workbench_width, self._workbench_height)
        self.physics.set_aperture(self._aperture)

        self._cluster_halos: list = []
        self._last_frametime_ms: float = 0.0

        # Graph Separation: Structural vs Render Subset
        self._structural_edges: List[Edge] = []
        self._ambient_edges: List[Edge] = []
        self._focal_edges: List[Edge] = []

        # Background IPC
        self.ipc = WeaverIPCClient()
        self.ipc.connected.connect(self._on_ipc_connected)
        self.ipc.disconnected.connect(self._on_ipc_disconnected)
        self.ipc.nodeUpdated.connect(self._on_node_updated)
        self.ipc.nodeDeleted.connect(self._on_node_deleted)
        self.ipc.start()

        # 120Hz Physics Integrator (8ms tick)
        self._physics_timer = QTimer()
        self._physics_timer.timeout.connect(self._on_physics_tick)
        self._physics_timer.start(8)

    def _recalculate_focal_weights(self, primary_id: int):
        self._cached_first_degree.clear()
        self._cached_second_degree.clear()
        self._cached_second_degree_parent.clear()
        self._cached_focal_weights.clear()

        if primary_id <= 0:
            for node in self.store.get_all_nodes():
                node.focus = 0.35
            return

        edges = self._focal_edges
        first_degree: Set[int] = set()
        temporal_first_degree: Set[int] = set()
        focal_weights: Dict[int, float] = {}
        
        for e in edges:
            if primary_id in (e.sourceId, e.targetId):
                target = e.targetId if e.sourceId == primary_id else e.sourceId
                if e.edgeType == "temporal":
                    temporal_first_degree.add(target)
                    self._cached_second_degree_parent[target] = primary_id
                else:
                    first_degree.add(target)
                    focal_weights[target] = max(focal_weights.get(target, 0.0), e.weight)

        second_degree: Set[int] = set()
        for e in edges:
            if e.sourceId in first_degree and e.targetId != primary_id and e.targetId not in first_degree:
                second_degree.add(e.targetId)
                if e.targetId not in self._cached_second_degree_parent:
                    self._cached_second_degree_parent[e.targetId] = e.sourceId
            elif e.targetId in first_degree and e.sourceId != primary_id and e.sourceId not in first_degree:
                second_degree.add(e.sourceId)
                if e.sourceId not in self._cached_second_degree_parent:
                    self._cached_second_degree_parent[e.sourceId] = e.targetId

        # Push temporal breadcrumbs natively into the Tier 2 satellite orbit
        second_degree.update(temporal_first_degree - first_degree)

        self._cached_first_degree = first_degree
        self._cached_second_degree = second_degree
        self._cached_focal_weights = focal_weights

        for node in self.store.get_all_nodes():
            if node.id == primary_id:
                node.focus = 1.0
            elif node.id in first_degree:
                node.focus = 0.70
            elif node.id in second_degree:
                node.focus = 0.45
            else:
                node.focus = 0.22

    def _on_physics_tick(self):
        t0 = time.perf_counter()

        nodes = self.store.get_all_nodes()
        
        # FIX: Physics ALWAYS needs the full structural graph to keep background galaxies glued together.
        active_physics_edges = list(self._structural_edges)
        struct_sigs = {(e.sourceId, e.targetId, e.edgeType) for e in self._structural_edges}
        
        if self._selected_node_id > 0:
            # Add any fresh focal edges (like resurrected temporals) so they get simulated
            for e in self._focal_edges:
                if (e.sourceId, e.targetId, e.edgeType) not in struct_sigs:
                    active_physics_edges.append(e)
        
        # Pass hovered node ID into step
        is_active = self.physics.step(
            nodes, active_physics_edges, self._selected_node_id, self._hovered_node_id, dt=0.008,
            first_degree_set=self._cached_first_degree,
            second_degree_set=self._cached_second_degree,
            second_degree_parent=self._cached_second_degree_parent,
            focal_weights=self._cached_focal_weights
        )
        
        if not is_active and self._physics_timer.isActive():
            self._physics_timer.stop()
            # Still update halos one last time when stopping
            self._cluster_halos = self.physics.get_cluster_halos(
                nodes, active_physics_edges, self._selected_node_id,
                first_degree_set=self._cached_first_degree,
                second_degree_set=self._cached_second_degree
            )
            self.clusterHalosChanged.emit()
            return
            
        self._cluster_halos = self.physics.get_cluster_halos(
            nodes, active_physics_edges, self._selected_node_id,
            first_degree_set=self._cached_first_degree,
            second_degree_set=self._cached_second_degree
        )
        self.clusterHalosChanged.emit()

        t1 = time.perf_counter()
        self._last_frametime_ms = (t1 - t0) * 1000.0
        self.telemetryChanged.emit()

    def _wake_physics(self):
        if not self._physics_timer.isActive():
            self._physics_timer.start(8)

    def _upsert_edge(self, new_edge: Edge):
        """Insert or update edge with balanced multi-tier ambient allocation."""
        self._wake_physics()
        matched = False
        for idx, e in enumerate(self._structural_edges):
            if (e.sourceId == new_edge.sourceId and e.targetId == new_edge.targetId and e.edgeType == new_edge.edgeType) or \
               (e.sourceId == new_edge.targetId and e.targetId == new_edge.sourceId and e.edgeType == new_edge.edgeType):
                self._structural_edges[idx] = new_edge
                matched = True
                break

        if not matched:
            self._structural_edges.append(new_edge)

        temporals = [e for e in self._structural_edges if e.edgeType == "temporal"]
        explicits = [e for e in self._structural_edges if e.edgeType == "explicit"]
        semantics = [e for e in self._structural_edges if e.edgeType == "semantic"]

        temporals.sort(key=lambda e: e.weight, reverse=True)
        explicits.sort(key=lambda e: e.weight, reverse=True)
        semantics.sort(key=lambda e: e.weight, reverse=True)

        self._ambient_edges = temporals[:20] + explicits[:35] + semantics[:35]

    # --- Properties Exposed to QML ---

    @pyqtProperty(list, notify=nodesChanged)
    def nodes(self) -> List[Node]:
        return self.store.get_all_nodes()

    @pyqtProperty(list, notify=edgesChanged)
    def edges(self) -> List[Edge]:
        base_edges = []
        if self._selected_node_id > 0:
            # 1. Start with curated, deduplicated focal edges
            base_edges = list(self._focal_edges)
            
            # 2. Exclude any ambient edges touching the focused node to prevent duplicate filaments
            for e in self._ambient_edges:
                if e.sourceId == self._selected_node_id or e.targetId == self._selected_node_id:
                    continue
                base_edges.append(e)                
        else:
            base_edges = self._ambient_edges
            
        # 3. Global deduplication by priority to ensure no visual overlap
        unique_edges = {}
        priority = {"explicit": 3, "semantic": 2, "temporal": 1}
        for e in base_edges:
            pair_key = (min(e.sourceId, e.targetId), max(e.sourceId, e.targetId))
            current = unique_edges.get(pair_key)
            if not current:
                unique_edges[pair_key] = e
            else:
                if priority.get(e.edgeType, 0) > priority.get(current.edgeType, 0):
                    unique_edges[pair_key] = e
                elif priority.get(e.edgeType, 0) == priority.get(current.edgeType, 0) and e.weight > current.weight:
                    unique_edges[pair_key] = e
                    
        return list(unique_edges.values())

    @pyqtProperty(int, notify=selectedNodeChanged)
    def selectedNodeId(self) -> int:
        return self._selected_node_id

    @pyqtProperty(int, notify=hoveredNodeChanged)
    def hoveredNodeId(self) -> int:
        return self._hovered_node_id

    @pyqtProperty(bool, notify=connectionStatusChanged)
    def isConnected(self) -> bool:
        return self._is_connected

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def workbenchWidth(self) -> float:
        return self._workbench_width

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def workbenchHeight(self) -> float:
        return self._workbench_height

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def wingWidth(self) -> float:
        return (self.physics.viewport_w - self._workbench_width) / 2.0

    @pyqtProperty(float, notify=apertureChanged)
    def aperture(self) -> float:
        return self._aperture

    @pyqtProperty(list, notify=clusterHalosChanged)
    def clusterHalos(self) -> list:
        return self._cluster_halos

    @pyqtProperty(float, notify=telemetryChanged)
    def physicsFrametime(self) -> float:
        return self._last_frametime_ms

    @pyqtProperty(int, notify=telemetryChanged)
    def activeNodeCount(self) -> int:
        return len(self.store.get_all_nodes())

    @pyqtProperty(int, notify=telemetryChanged)
    def activeEdgeCount(self) -> int:
        return len(self.edges)

    # --- Slots Invoked from QML ---

    @pyqtSlot(int)
    def set_hovered_node(self, node_id: int):
        if self._hovered_node_id != node_id:
            self._hovered_node_id = node_id
            self.hoveredNodeChanged.emit(node_id)
            self._wake_physics()

    @pyqtSlot(int, result=int)
    def get_downstream_count(self, node_id: int) -> int:
        edges = self._focal_edges if self._selected_node_id > 0 else self._ambient_edges
        count = 0
        for e in edges:
            if e.sourceId == node_id and e.targetId != self._selected_node_id:
                count += 1
            elif e.targetId == node_id and e.sourceId != self._selected_node_id:
                count += 1
        return count

    @pyqtSlot(float)
    def adjust_aperture(self, delta: float):
        new_val = max(0.20, min(2.20, self._aperture + delta))
        if abs(new_val - self._aperture) > 0.005:
            self._aperture = new_val
            self.physics.set_aperture(new_val)
            self.apertureChanged.emit(new_val)
            self._wake_physics()

    @pyqtSlot(float, float)
    def set_workbench_dimensions(self, width: float, height: float):
        self._wake_physics()
        clamped_w = max(680.0, min(2600.0, width))
        clamped_h = max(420.0, min(1600.0, height))

        if abs(self._workbench_width - clamped_w) > 1.0 or abs(self._workbench_height - clamped_h) > 1.0:
            self._workbench_width = clamped_w
            self._workbench_height = clamped_h
            self.physics.set_focal_card_dimensions(clamped_w, clamped_h)
            self.workbenchDimensionsChanged.emit()

    @pyqtSlot(float, float)
    def update_viewport_dimensions(self, width: float, height: float):
        self._wake_physics()
        self.physics.set_viewport_dimensions(width, height)
        self.workbenchDimensionsChanged.emit()

    @pyqtSlot(int)
    def select_node(self, node_id: int):
        self._wake_physics()
        if self._selected_node_id != node_id:
            self._selected_node_id = node_id
            
            if node_id > 0:
                if node_id in self.physics.recent_node_ids:
                    self.physics.recent_node_ids.remove(node_id)
                self.physics.recent_node_ids.insert(0, node_id)
                self.physics.recent_node_ids = self.physics.recent_node_ids[:8]

            self._recalculate_focal_weights(node_id)
            self.selectedNodeChanged.emit(node_id)

        if node_id == 0:
            self._focal_edges = []
            self.edgesChanged.emit()
            return

        if self._is_connected and node_id > 0:
            self.ipc.call_rpc_sync(
                "touch_node",
                {"node_id": node_id, "event_type": "focus"},
                callback=self._handle_touch_node_response,
            )

            self.ipc.call_rpc_sync(
                "get_neighbors",
                {"node_id": node_id},
                callback=self._handle_neighbors_response,
            )

    @pyqtSlot(int, float, float)
    def pin_node(self, node_id: int, x: float, y: float):
        self._wake_physics()
        self.physics.pin_node(node_id)
        node = self.store.get_node(node_id)
        if node:
            node.x = x
            node.y = y

    @pyqtSlot(int, float, float)
    def update_drag_pos(self, node_id: int, x: float, y: float):
        self._wake_physics()
        node = self.store.get_node(node_id)
        if node:
            node.x = x
            node.y = y

    @pyqtSlot(int, result=str)
    def get_relation_type(self, node_id: int) -> str:
        if self._selected_node_id <= 0 or node_id == self._selected_node_id:
            return ""
        for e in self._focal_edges:
            if (e.sourceId == self._selected_node_id and e.targetId == node_id) or \
               (e.targetId == self._selected_node_id and e.sourceId == node_id):
                return e.edgeType
        return ""

    @pyqtSlot(int)
    def release_node(self, node_id: int):
        self._wake_physics()
        self.physics.unpin_node()

    @pyqtSlot(int, float, float)
    def set_custom_anchor(self, node_id: int, x: float, y: float):
        self.physics.set_custom_anchor(node_id, x, y)

    @pyqtSlot(str)
    def open_in_file_manager(self, file_path: str):
        safe_path = canonicalize_safe_path(file_path)
        if not safe_path:
            return

        target_dir = safe_path if safe_path.is_dir() else safe_path.parent
        if target_dir.exists():
            subprocess.Popen(
                ["xdg-open", str(target_dir)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

    # --- IPC Callbacks ---

    def _on_ipc_connected(self):
        self._is_connected = True
        self.connectionStatusChanged.emit(True)
        self.ipc.call_rpc_sync("get_all_nodes", {}, callback=self._handle_initial_sync)

    def _on_ipc_disconnected(self):
        self._is_connected = False
        self.connectionStatusChanged.emit(False)

    def _handle_initial_sync(self, result: list, error: Optional[str]):
        if error or not isinstance(result, list):
            return

        # Temporarily disconnect the signal to prevent duplicate incoming nodeUpdated events
        self.ipc.nodeUpdated.disconnect(self._on_node_updated)
        try:
            for node_data in result:
                self._on_node_updated(node_data)
        finally:
            self.ipc.nodeUpdated.connect(self._on_node_updated)

        self._wake_physics()

        for n in self.store.get_all_nodes():
            self.ipc.call_rpc_sync("get_neighbors", {"node_id": n.id}, callback=self._handle_ambient_edges_response)

    def _handle_touch_node_response(self, result: Any, error: Optional[str]):
        if error or not isinstance(result, dict):
            return

        raw_temporal = result.get("temporal_edges", [])
        if not raw_temporal:
            return

        for e in raw_temporal:
            src_id = int(e["source_id"])
            tgt_id = int(e["target_id"])
            weight = float(e.get("weight", 1.0))
            edge_obj = Edge(source_id=src_id, target_id=tgt_id, edge_type="temporal", weight=weight)
            self._upsert_edge(edge_obj)

            if self._selected_node_id in (src_id, tgt_id):
                if not any((fe.sourceId == src_id and fe.targetId == tgt_id and fe.edgeType == "temporal") or
                           (fe.sourceId == tgt_id and fe.targetId == src_id and fe.edgeType == "temporal")
                           for fe in self._focal_edges):
                    self._focal_edges.append(edge_obj)

        self._recalculate_focal_weights(self._selected_node_id)
        self.edgesChanged.emit()

    def _handle_ambient_edges_response(self, result: dict, error: Optional[str]):
        if error or not result:
            return

        raw_edges = result.get("edges", [])
        for e in raw_edges:
            src_id = int(e["source_id"])
            tgt_id = int(e["target_id"])
            e_type = e["edge_type"]
            weight = float(e["weight"])
            self._upsert_edge(
                Edge(source_id=src_id, target_id=tgt_id, edge_type=e_type, weight=weight)
            )

        if self._selected_node_id == 0:
            self.edgesChanged.emit()

    def _on_node_updated(self, data: dict):
        self._wake_physics()
        raw_id = data.get("node_id") if data.get("node_id") is not None else data.get("id")
        if raw_id is None:
            return

        node_id = int(raw_id)
        file_path = data.get("file_path", "")
        if not node_id or not file_path:
            return

        node = self.store.get_node(node_id)
        if not node:
            angle = node_id * 2.399963
            # Limit the radius to within the current viewport bounds
            max_r_x = self.physics.viewport_w * 0.4
            max_r_y = self.physics.viewport_h * 0.4
            # Keep within the screen boundaries safely
            base_r = min(max_r_x, max_r_y)
            radius = min(350.0 + (math.sqrt(node_id) * 85.0), max(50.0, base_r - 150.0))
            
            spawn_x = self.physics.center_x + math.cos(angle) * radius
            spawn_y = self.physics.center_y + math.sin(angle) * radius
            
            new_node = Node(id=node_id, file_path=file_path, x=spawn_x, y=spawn_y, focus=0.35)
            # Impart an initial outward impulse so it doesn't just sleep
            new_node.vx = math.cos(angle) * 40.0
            new_node.vy = math.sin(angle) * 40.0
            
            self.store.upsert_node(new_node)
            self.nodesChanged.emit()
        else:
            node.filePath = file_path

        self._recalculate_focal_weights(self._selected_node_id)

    def _on_node_deleted(self, data: dict):
        self._wake_physics()
        raw_id = data.get("node_id") if data.get("node_id") is not None else data.get("id")
        if raw_id is not None:
            node_id = int(raw_id)
            self.store.remove_node(node_id)
            self._structural_edges = [e for e in self._structural_edges if e.sourceId != node_id and e.targetId != node_id]
            self._ambient_edges = [e for e in self._ambient_edges if e.sourceId != node_id and e.targetId != node_id]
            self._focal_edges = [e for e in self._focal_edges if e.sourceId != node_id and e.targetId != node_id]
            self._recalculate_focal_weights(self._selected_node_id)
            self.nodesChanged.emit()
            self.edgesChanged.emit()

    def _handle_neighbors_response(self, result: dict, error: Optional[str]):
        if error or not result:
            return

        raw_edges = result.get("edges", [])
        parsed_edges: List[Edge] = [
            Edge(
                source_id=int(e["source_id"]),
                target_id=int(e["target_id"]),
                edge_type=e["edge_type"],
                weight=float(e["weight"])
            )
            for e in raw_edges
        ]

        # 1. Vacuum Seal: ONLY preserve live temporal edges that ACTUALLY touch the current focal lens
        existing_temporals = [
            e for e in self._focal_edges 
            if e.edgeType == "temporal" and (e.sourceId == self._selected_node_id or e.targetId == self._selected_node_id)
        ]
        
        for te in existing_temporals:
            if not any(
                (pe.sourceId == te.sourceId and pe.targetId == te.targetId and pe.edgeType == te.edgeType) or
                (pe.sourceId == te.targetId and pe.targetId == te.sourceId and pe.edgeType == te.edgeType)
                for pe in parsed_edges
            ):
                parsed_edges.append(te)

        # 2. Universal Deduplication: Keep only the highest priority relational bond
        unique_edges = {}
        for e in parsed_edges:
            if e.sourceId != self._selected_node_id and e.targetId != self._selected_node_id:
                continue
                
            pair_key = (min(e.sourceId, e.targetId), max(e.sourceId, e.targetId))
            current = unique_edges.get(pair_key)
            
            if not current:
                unique_edges[pair_key] = e
            else:
                # Priority mapping ensures Explicit and Semantic links aren't overwritten by Temporal history
                priority = {"explicit": 3, "semantic": 2, "temporal": 1}
                if priority[e.edgeType] > priority[current.edgeType]:
                    unique_edges[pair_key] = e
                elif priority[e.edgeType] == priority[current.edgeType] and e.weight > current.weight:
                    unique_edges[pair_key] = e
                
        deduped_edges = list(unique_edges.values())

        # 3. Categorize and Boost
        temporals = [e for e in deduped_edges if e.edgeType == "temporal"]
        explicits = [e for e in deduped_edges if e.edgeType == "explicit"]
        
        tier1_semantics = []
        tier2_semantics = []
        for e in deduped_edges:
            if e.edgeType == "semantic":
                tier1_semantics.append(e)

        # 4. Tier Allocations & Strict Secondary Quotas
        tier1_edges = explicits + tier1_semantics
        tier1_edges.sort(key=lambda e: e.weight, reverse=True)
        
        tier2_edges = temporals + tier2_semantics
        tier2_edges.sort(key=lambda e: e.weight, reverse=True)

        # Cap: Max 8 primary wings, and strictly cap Tier 2 temporal/satellites to max 4 total globally
        self._focal_edges = tier1_edges[:8] + tier2_edges[:4]

        self._recalculate_focal_weights(self._selected_node_id)
        self.edgesChanged.emit()
