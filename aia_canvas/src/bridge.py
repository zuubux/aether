"""
Aether Canvas - Python to QML Bridge
Adapter exposing multi-tier focal weights, telemetry, and secure OS interactions.
"""

import logging
import time
import subprocess
from utils.security import canonicalize_safe_path
from typing import List, Optional, Set
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
        
        self._selected_node_id: int = 1
        self._hovered_node_id: int = 0
        self._is_connected = False

        self._aperture: float = 1.0
        self._workbench_width: float = 1400.0
        self._workbench_height: float = 900.0
        
        self.physics.set_focal_card_dimensions(self._workbench_width, self._workbench_height)
        self.physics.set_aperture(self._aperture)

        self._cluster_halos: list = []

        # IPC Setup
        self.ipc = WeaverIPCClient()
        self.ipc.connected.connect(self._on_ipc_connected)
        self.ipc.disconnected.connect(self._on_ipc_disconnected)
        self.ipc.nodeUpdated.connect(self._on_node_updated)
        self.ipc.nodeDeleted.connect(self._on_node_deleted)
        self.ipc.start()

        # Telemetry State
        self._last_frametime_ms: float = 0.0

        # Physics Timer Setup
        self._physics_timer = QTimer()
        self._physics_timer.timeout.connect(self._on_physics_tick)
        self._physics_timer.start(8)  # 120Hz Integration

    def _recalculate_focal_weights(self, primary_id: int):
        """Tiered salience assignment mapping biological focus across the graph topology."""
        if primary_id <= 0:
            for node in self.store.get_all_nodes():
                node.focus = 0.30
            return

        edges = self.store.get_all_edges()
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
        edges = self.store.get_all_edges()
        self.physics.step(nodes, edges, self._selected_node_id, dt=0.008)
        self._cluster_halos = self.physics.get_cluster_halos(nodes, edges, self._selected_node_id)
        self.clusterHalosChanged.emit()
        
        t1 = time.perf_counter()
        frametime_ms = (t1 - t0) * 1000.0
        
        # Update Telemetry & Check Golden Signals
        self._last_frametime_ms = frametime_ms
        self.telemetryChanged.emit()

        if frametime_ms > 6.5:
            logger.warning(f"Physics frame deadline breached! Took {frametime_ms:.2f}ms (Budget: 8.0ms)")

    # --- Secure Subprocess Execution ---
    @pyqtSlot(str)
    def open_in_file_manager(self, file_path: str):
        """Strictly isolated OS interaction leveraging xdg-open for agnostic POSIX compliance."""
        import subprocess
        
        safe_path = canonicalize_safe_path(file_path)
        if not safe_path:
            return

        target_dir = safe_path if safe_path.is_dir() else safe_path.parent
        if target_dir.exists():
            subprocess.Popen(
                ["xdg-open", str(target_dir)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

    # --- Properties Exposed to QML ---

    @pyqtProperty(list, notify=nodesChanged)
    def nodes(self) -> List[Node]:
        return self.store.get_all_nodes()

    @pyqtProperty(list, notify=edgesChanged)
    def edges(self) -> List[Edge]:
        return self.store.get_all_edges()

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
        return len(self.store.get_all_edges())

    # --- Slots Invoked from QML ---

    @pyqtSlot(int)
    def set_hovered_node(self, node_id: int):
        if self._hovered_node_id != node_id:
            self._hovered_node_id = node_id
            self.hoveredNodeChanged.emit(node_id)

    @pyqtSlot(int, result=int)
    def get_downstream_count(self, node_id: int) -> int:
        """Count downstream satellite connections excluding the active focus."""
        edges = self.store.get_all_edges()
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
            self._recalculate_focal_weights(node_id)
            self.selectedNodeChanged.emit(node_id)

        if self._is_connected and node_id > 0:
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
        import subprocess
        from pathlib import Path
        path = Path(file_path)
        if path.exists():
            subprocess.Popen(["dolphin", "--select", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent if path.parent.exists() else Path.home())])

    # --- IPC Callbacks ---

    def _on_ipc_connected(self):
        self._is_connected = True
        self.connectionStatusChanged.emit(True)
        self.select_node(self._selected_node_id)

    def _on_ipc_disconnected(self):
        self._is_connected = False
        self.connectionStatusChanged.emit(False)

    def _on_node_updated(self, data: dict):
        node_id = int(data.get("node_id", 0))
        file_path = data.get("file_path", "")
        if not node_id or not file_path:
            return

        node = self.store.get_node(node_id)
        if not node:
            node = Node(id=node_id, file_path=file_path, x=800.0, y=450.0)
            self.store.upsert_node(node)
            self.nodesChanged.emit()
        else:
            node.filePath = file_path

        self._recalculate_focal_weights(self._selected_node_id)

    def _on_node_deleted(self, data: dict):
        node_id = int(data.get("node_id", 0))
        if node_id:
            self.store.remove_node(node_id)
            self._recalculate_focal_weights(self._selected_node_id)
            self.nodesChanged.emit()
            self.edgesChanged.emit()

    def _handle_neighbors_response(self, result: dict, error: Optional[str]):
        if error or not result:
            return

        raw_edges = result.get("edges", [])
        parsed_edges: List[Edge] = []
        for e in raw_edges:
            parsed_edges.append(
                Edge(
                    source_id=int(e["source_id"]),
                    target_id=int(e["target_id"]),
                    edge_type=e["edge_type"],
                    weight=float(e["weight"]),
                )
            )

        self.store.set_edges_for_neighborhood(self._selected_node_id, parsed_edges)
        self._recalculate_focal_weights(self._selected_node_id)
        self.edgesChanged.emit()