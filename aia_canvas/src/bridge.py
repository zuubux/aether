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

        # 120Hz Physics Integrator (8ms)
        self._physics_timer = QTimer()
        self._physics_timer.timeout.connect(self._on_physics_tick)
        self._physics_timer.start(8)

    def _recalculate_focal_weights(self, primary_id: int):
        if primary_id <= 0:
            for node in self.store.get_all_nodes():
                node.focus = 0.35
            return

        edges = self._focal_edges
        first_degree: Set[int] = {
            e.targetId if e.sourceId == primary_id else e.sourceId
            for e in edges if primary_id in (e.sourceId, e.targetId)
        }

        second_degree: Set[int] = set()
        for e in edges:
            if e.sourceId in first_degree and e.targetId != primary_id:
                second_degree.add(e.targetId)
            elif e.targetId in first_degree and e.sourceId != primary_id:
                second_degree.add(e.sourceId)

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
        active_physics_edges = self._focal_edges if self._selected_node_id > 0 else self._structural_edges
        
        self.physics.step(nodes, active_physics_edges, self._selected_node_id, dt=0.008)
        self._cluster_halos = self.physics.get_cluster_halos(nodes, active_physics_edges, self._selected_node_id)
        self.clusterHalosChanged.emit()

        t1 = time.perf_counter()
        self._last_frametime_ms = (t1 - t0) * 1000.0
        self.telemetryChanged.emit()

    def _upsert_edge(self, new_edge: Edge):
        """Insert or update edge with balanced multi-tier ambient allocation."""
        matched = False
        for idx, e in enumerate(self._structural_edges):
            if (e.sourceId == new_edge.sourceId and e.targetId == new_edge.targetId and e.edgeType == new_edge.edgeType) or \
               (e.sourceId == new_edge.targetId and e.targetId == new_edge.sourceId and e.edgeType == new_edge.edgeType):
                self._structural_edges[idx] = new_edge
                matched = True
                break

        if not matched:
            self._structural_edges.append(new_edge)

        # Balanced Ambient Composition: Prevent any single type from crowding out the others
        temporals = [e for e in self._structural_edges if e.edgeType == "temporal"]
        explicits = [e for e in self._structural_edges if e.edgeType == "explicit"]
        semantics = [e for e in self._structural_edges if e.edgeType == "semantic"]

        temporals.sort(key=lambda e: e.weight, reverse=True)
        explicits.sort(key=lambda e: e.weight, reverse=True)
        semantics.sort(key=lambda e: e.weight, reverse=True)

        # 20 Recent Sessions, 35 Structural Links, 35 Semantic Relationships
        self._ambient_edges = temporals[:20] + explicits[:35] + semantics[:35]

    # --- Properties Exposed to QML ---

    @pyqtProperty(list, notify=nodesChanged)
    def nodes(self) -> List[Node]:
        return self.store.get_all_nodes()

    @pyqtProperty(list, notify=edgesChanged)
    def edges(self) -> List[Edge]:
        return self._focal_edges if self._selected_node_id > 0 else self._ambient_edges

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

    @pyqtSlot(float, float)
    def set_workbench_dimensions(self, width: float, height: float):
        clamped_w = max(680.0, min(2600.0, width))
        clamped_h = max(420.0, min(1600.0, height))

        if abs(self._workbench_width - clamped_w) > 1.0 or abs(self._workbench_height - clamped_h) > 1.0:
            self._workbench_width = clamped_w
            self._workbench_height = clamped_h
            self.physics.set_focal_card_dimensions(clamped_w, clamped_h)
            self.workbenchDimensionsChanged.emit()

    @pyqtSlot(float, float)
    def update_viewport_dimensions(self, width: float, height: float):
        self.physics.set_viewport_dimensions(width, height)

    @pyqtSlot(int)
    def select_node(self, node_id: int):
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
            # 1. Fire live focus touch event to Weaver
            self.ipc.call_rpc_sync(
                "touch_node",
                {"node_id": node_id, "event_type": "focus"},
                callback=self._handle_touch_node_response,
            )

            # 2. Query neighborhood topology for focal workbench
            self.ipc.call_rpc_sync(
                "get_neighbors",
                {"node_id": node_id},
                callback=self._handle_neighbors_response,
            )

    @pyqtSlot(int, float, float)
    def pin_node(self, node_id: int, x: float, y: float):
        self.physics.pin_node(node_id)
        node = self.store.get_node(node_id)
        if node:
            node.x = x
            node.y = y

    @pyqtSlot(int, float, float)
    def update_drag_pos(self, node_id: int, x: float, y: float):
        node = self.store.get_node(node_id)
        if node:
            node.x = x
            node.y = y

    @pyqtSlot(int)
    def release_node(self, node_id: int):
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
            subprocess.Popen(["xdg-open", str(target_dir)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

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

        for node_data in result:
            self._on_node_updated(node_data)

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

            # Keep focal view populated if currently viewing one of the nodes
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
            radius = 350.0 + (math.sqrt(node_id) * 85.0)
            spawn_x, spawn_y = self.physics.center_x + math.cos(angle) * radius, self.physics.center_y + math.sin(angle) * radius
            self.store.upsert_node(Node(id=node_id, file_path=file_path, x=spawn_x, y=spawn_y, focus=0.35))
            self.nodesChanged.emit()
        else:
            node.filePath = file_path

        self._recalculate_focal_weights(self._selected_node_id)

    def _on_node_deleted(self, data: dict):
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
            Edge(source_id=int(e["source_id"]), target_id=int(e["target_id"]), edge_type=e["edge_type"], weight=float(e["weight"]))
            for e in raw_edges
        ]

        # Preserve any live temporal edges currently in the focal set
        existing_temporals = [e for e in self._focal_edges if e.edgeType == "temporal"]
        for te in existing_temporals:
            if not any((pe.sourceId == te.sourceId and pe.targetId == te.targetId and pe.edgeType == te.edgeType) or
                       (pe.sourceId == te.targetId and pe.targetId == te.sourceId and pe.edgeType == te.edgeType)
                       for pe in parsed_edges):
                parsed_edges.append(te)

        type_priority = {"temporal": 3, "explicit": 2, "semantic": 1}
        parsed_edges.sort(key=lambda e: (type_priority.get(e.edgeType, 0), e.weight), reverse=True)

        self._focal_edges = parsed_edges[:16]
        self._recalculate_focal_weights(self._selected_node_id)
        self.edgesChanged.emit()