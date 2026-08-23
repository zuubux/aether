"""
Aether Canvas - Python to QML Bridge
Live temporal co-attention ingestion, priority edge sorting, and telemetry.
"""

import logging
import math
import time
from typing import Any

from ipc.client import WeaverIPCClient
from models import Edge, Node
from physics.engine import PhysicsEngine
from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot
from store import GraphStore
from telemetry import TelemetryCollector

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
    searchResultsReceived = pyqtSignal(list)
    searchCleared = pyqtSignal()
    searchActiveChanged = pyqtSignal(bool)
    nodeRemoved = pyqtSignal(int)

    # Async Media Signals
    pdfPageReady = pyqtSignal(str, int, str, arguments=['filePath', 'pageIndex', 'imagePath'])
    pdfCountReady = pyqtSignal(str, int, arguments=['filePath', 'pageCount'])
    csvDataReady = pyqtSignal(str, 'QVariantMap', arguments=['filePath', 'tableData'])
    imageReady = pyqtSignal(str, str, arguments=['filePath', 'sourceUrl'])
    mediaError = pyqtSignal(str, str, arguments=['filePath', 'errorMessage'])

    def __init__(self):
        super().__init__()
        import time
        self._t0 = time.perf_counter()
        self._qml_ready_time = 0.0
        self.store = GraphStore()
        self.physics = PhysicsEngine()

        from controllers.canvas_controller import CanvasController
        from controllers.node_controller import NodeController
        from controllers.physics_controller import PhysicsController
        from controllers.search_controller import SearchController

        self.canvas_ctrl = CanvasController(self)
        self.search_ctrl = SearchController(self)
        self.node_ctrl = NodeController(self)
        self.physics_ctrl = PhysicsController(self)

        # Connect controller child signals to the corresponding bridge signals
        self.canvas_ctrl.workbenchDimensionsChanged.connect(self.workbenchDimensionsChanged)
        self.canvas_ctrl.apertureChanged.connect(self.apertureChanged)
        
        self.search_ctrl.searchResultsReceived.connect(self._handle_search_results)
        self.search_ctrl.searchCleared.connect(self._handle_search_cleared)
        
        self.node_ctrl.selectedNodeChanged.connect(self.selectedNodeChanged)
        self.node_ctrl.hoveredNodeChanged.connect(self.hoveredNodeChanged)
        self.node_ctrl.nodeRemoved.connect(self.nodeRemoved)
        
        # Connect Async Media Signals
        self.node_ctrl.pdfPageReady.connect(self.pdfPageReady)
        self.node_ctrl.pdfCountReady.connect(self.pdfCountReady)
        self.node_ctrl.csvDataReady.connect(self.csvDataReady)
        self.node_ctrl.imageReady.connect(self.imageReady)
        self.node_ctrl.mediaError.connect(self.mediaError)
        
        self.physics_ctrl.nodesChanged.connect(self.nodesChanged)
        self.physics_ctrl.edgesChanged.connect(self.edgesChanged)
        self.physics_ctrl.clusterHalosChanged.connect(self.clusterHalosChanged)
        self.physics_ctrl.telemetryChanged.connect(self.telemetryChanged)
        self.physics_ctrl.connectionStatusChanged.connect(self.connectionStatusChanged)

        self._SUPPORTED_IMAGE_EXTS = {
            "bmp", "gif", "ico", "jpeg", "jpg", "png", "pbm", "pgm", "ppm", "xbm", "xpm",
            "svg", "svgz", "webp", "tif", "tiff", "heic", "heif"
        }

        self._failed_image_conversions: set[str] = set()

        self._selected_node_id: int = 0
        self._hovered_node_id: int = 0
        self._is_connected = False
        self._search_active = False
        
        self._cached_first_degree: set[int] = set()
        self._cached_second_degree: set[int] = set()
        self._cached_second_degree_parent: dict[int, int] = {}
        self._cached_focal_weights: dict[int, float] = {}

        self._aperture: float = 1.0
        self._workbench_width: float = 1600.0
        self._workbench_height: float = 1000.0

        self.physics.set_focal_card_dimensions(self._workbench_width, self._workbench_height)
        self.physics.set_aperture(self._aperture)

        self._cluster_halos: list = []
        self._last_frametime_ms: float = 0.0
        
        self.telemetry = TelemetryCollector()

        # Graph Separation: Structural vs Render Subset
        self._structural_edges: list[Edge] = []
        self._ambient_edges: list[Edge] = []
        self._focal_edges: list[Edge] = []

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
        first_degree: set[int] = set()
        temporal_first_degree: set[int] = set()
        focal_weights: dict[int, float] = {}
        
        for e in edges:
            if primary_id in (e.sourceId, e.targetId):
                target = e.targetId if e.sourceId == primary_id else e.sourceId
                if e.edgeType == "temporal":
                    temporal_first_degree.add(target)
                    self._cached_second_degree_parent[target] = primary_id
                else:
                    first_degree.add(target)
                    focal_weights[target] = max(focal_weights.get(target, 0.0), e.weight)

        second_degree: set[int] = set()
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

    @pyqtProperty(bool, notify=searchActiveChanged)
    def searchActive(self) -> bool:
        return self._search_active

    @pyqtProperty(list, notify=nodesChanged)
    def nodes(self) -> list[Node]:
        return self.physics_ctrl.nodes

    @pyqtProperty(list, notify=edgesChanged)
    def edges(self) -> list[Edge]:
        return self.physics_ctrl.edges

    @pyqtProperty(int, notify=selectedNodeChanged)
    def selectedNodeId(self) -> int:
        return self.node_ctrl.selectedNodeId

    @pyqtProperty(int, notify=hoveredNodeChanged)
    def hoveredNodeId(self) -> int:
        return self.node_ctrl.hoveredNodeId

    @pyqtProperty(bool, notify=connectionStatusChanged)
    def isConnected(self) -> bool:
        return self.physics_ctrl.isConnected

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def workbenchWidth(self) -> float:
        return self.canvas_ctrl.workbenchWidth

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def workbenchHeight(self) -> float:
        return self.canvas_ctrl.workbenchHeight

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def wingWidth(self) -> float:
        return self.canvas_ctrl.wingWidth

    @pyqtProperty(float, notify=apertureChanged)
    def aperture(self) -> float:
        return self.canvas_ctrl.aperture

    @pyqtProperty(list, notify=clusterHalosChanged)
    def clusterHalos(self) -> list:
        return self.physics_ctrl.clusterHalos

    @pyqtProperty(float, notify=telemetryChanged)
    def physicsFrametime(self) -> float:
        return self.physics_ctrl.physicsFrametime

    @pyqtProperty(int, notify=telemetryChanged)
    def activeNodeCount(self) -> int:
        return self.physics_ctrl.activeNodeCount

    @pyqtProperty(int, notify=telemetryChanged)
    def activeEdgeCount(self) -> int:
        return self.physics_ctrl.activeEdgeCount

    # --- Slots Invoked from QML ---
    
    @pyqtSlot()
    def notify_ui_ready(self):
        import time
        self._qml_ready_time = (time.perf_counter() - self._t0) * 1000.0
        self._ui_ready = True
        if self._is_connected:
            print(f"[T+{(time.perf_counter() - self._t0)*1000:.1f}ms] Canvas sent `initial_sync` request")
            self.ipc.call_rpc_sync("get_all_nodes", {}, callback=self._handle_initial_sync)

    @pyqtSlot(result='QVariantMap')
    def get_telemetry_snapshot(self) -> dict:
        return self.telemetry.get_snapshot()
        
    @pyqtSlot(float)
    def record_frame(self, delta_ms: float):
        self.telemetry.record_frame(delta_ms)

    @pyqtSlot(str, int, result='QVariantMap')
    @pyqtSlot(str, result='QVariantMap')
    def get_csv_preview(self, file_path: str, max_rows: int = 5) -> dict:
        return self.node_ctrl.get_csv_preview(file_path, max_rows)

    @pyqtSlot(str, int)
    @pyqtSlot(str)
    def request_csv_data(self, file_path: str, max_rows: int = 1000):
        self.node_ctrl.request_csv_data(file_path, max_rows)

    @pyqtSlot(str, int, int, str, result=bool)
    def update_csv_cell(self, file_path: str, row_idx: int, col_idx: int, new_value: str) -> bool:
        return self.node_ctrl.update_csv_cell(file_path, row_idx, col_idx, new_value)

    @pyqtSlot(str, result=bool)
    def copy_csv_data(self, file_path: str) -> bool:
        return self.node_ctrl.copy_csv_data(file_path)

    @pyqtSlot(str, result=bool)
    def copy_image_to_clipboard(self, file_path: str) -> bool:
        return self.node_ctrl.copy_image_to_clipboard(file_path)

    @pyqtSlot(str, result=int)
    def get_pdf_page_count(self, file_path: str) -> int:
        return self.node_ctrl.get_pdf_page_count(file_path)

    @pyqtSlot(str)
    def request_pdf_page_count(self, file_path: str):
        self.node_ctrl.request_pdf_page_count(file_path)

    @pyqtSlot(str, int, int)
    @pyqtSlot(str, int)
    @pyqtSlot(str)
    def request_pdf_page(self, file_path: str, page_index: int = 0, target_width: int = 1800):
        self.node_ctrl.request_pdf_page(file_path, page_index, target_width)

    @pyqtSlot(str, int, result=bool)
    @pyqtSlot(str, result=bool)
    def copy_pdf_page_to_clipboard(self, file_path: str, page_index: int = 0) -> bool:
        return self.node_ctrl.copy_pdf_page_to_clipboard(file_path, page_index)

    @pyqtSlot(str, result=bool)
    def is_image_file(self, file_path: str) -> bool:
        return self.node_ctrl.is_image_file(file_path)

    @pyqtSlot(str)
    def request_image_source(self, file_path: str):
        self.node_ctrl.request_image_source(file_path)

    def _handle_search_results(self, results):
        self._search_active = True
        self.searchActiveChanged.emit(True)
        self.searchResultsReceived.emit(results)

    def _handle_search_cleared(self):
        self._search_active = False
        self.searchActiveChanged.emit(False)
        self.searchCleared.emit()

    @pyqtSlot(str)
    def submit_query(self, query: str):
        self.search_ctrl.submit_query(query)

    @pyqtSlot()
    def clear_search(self):
        self.search_ctrl.clear_search()

    @pyqtSlot(bool)
    def set_search_active(self, active: bool):
        self.search_ctrl.set_search_active(active)

    @pyqtSlot(list, float, float)
    def set_staged_nodes(self, node_id_strs: list, viewport_w: float, shelf_y: float):
        self.search_ctrl.set_staged_nodes(node_id_strs, viewport_w, shelf_y)

    @pyqtSlot(int)
    def set_hovered_node(self, node_id: int):
        self.node_ctrl.set_hovered_node(node_id)

    @pyqtSlot(int, result=int)
    def get_downstream_count(self, node_id: int) -> int:
        return self.physics_ctrl.get_downstream_count(node_id)

    @pyqtSlot(float)
    def adjust_aperture(self, delta: float):
        self.canvas_ctrl.adjust_aperture(delta)

    @pyqtSlot(float, float)
    def set_workbench_dimensions(self, width: float, height: float):
        self.canvas_ctrl.set_workbench_dimensions(width, height)

    @pyqtSlot(float, float)
    def update_viewport_dimensions(self, width: float, height: float):
        self.canvas_ctrl.update_viewport_dimensions(width, height)

    @pyqtSlot(str)
    def navigate_to_link(self, target_name: str):
        self.node_ctrl.navigate_to_link(target_name)

    @pyqtSlot(int)
    def select_node(self, node_id: int):
        self.node_ctrl.select_node(node_id)

    @pyqtSlot(int, float, float)
    def pin_node(self, node_id: int, x: float, y: float):
        self.node_ctrl.pin_node(node_id, x, y)

    @pyqtSlot(int, float, float)
    def update_drag_pos(self, node_id: int, x: float, y: float):
        self.node_ctrl.update_drag_pos(node_id, x, y)

    @pyqtSlot(int, result=str)
    def get_relation_type(self, node_id: int) -> str:
        return self.physics_ctrl.get_relation_type(node_id)

    @pyqtSlot(int)
    def release_node(self, node_id: int):
        self.node_ctrl.release_node(node_id)

    @pyqtSlot(int, float, float)
    def set_custom_anchor(self, node_id: int, x: float, y: float):
        self.node_ctrl.set_custom_anchor(node_id, x, y)

    @pyqtSlot(int, str)
    def save_node_content(self, node_id: int, new_content: str):
        self.node_ctrl.save_node_content(node_id, new_content)

    @pyqtSlot(str)
    def open_in_file_manager(self, file_path: str):
        self.node_ctrl.open_in_file_manager(file_path)

    @pyqtSlot(str)
    def open_in_external_editor(self, file_path: str):
        self.node_ctrl.open_in_external_editor(file_path)

    # --- IPC Callbacks ---

    def _on_ipc_connected(self):
        import time
        print(f"[T+{(time.perf_counter() - self._t0)*1000:.1f}ms] Canvas connected to IPC")
        self._is_connected = True
        self.connectionStatusChanged.emit(True)
        if getattr(self, "_ui_ready", False):
            print(f"[T+{(time.perf_counter() - self._t0)*1000:.1f}ms] Canvas sent `initial_sync` request")
            self.ipc.call_rpc_sync("get_all_nodes", {}, callback=self._handle_initial_sync)

    def _on_ipc_disconnected(self):
        self._is_connected = False
        self.connectionStatusChanged.emit(False)

    def _handle_initial_sync(self, result: dict, error: str | None):
        if error or not isinstance(result, dict):
            # Fallback if result is just a list
            if isinstance(result, list):
                result = {"nodes": result, "timing": {"db_load": 0.0, "embed_cache": 0.0}}
            else:
                return

        nodes = result.get("nodes", [])
        edges_payload = result.get("edges", [])
        if isinstance(nodes, dict):
            nodes = list(nodes.values())
        elif isinstance(result, dict) and "nodes" not in result:
            nodes = list(result.values())
            
        timing = result.get("timing", {"db_load": 0.0, "embed_cache": 0.0})
        db_load_ms = timing.get("db_load", 0.0)
        embed_cache_ms = timing.get("embed_cache", 0.0)

        import time
        t_received = time.perf_counter()
        print(f"[T+{(t_received - self._t0)*1000:.1f}ms] Canvas received `initial_sync` payload ({len(nodes)} nodes)")

        # Temporarily disconnect the signal to prevent duplicate incoming nodeUpdated events
        self.ipc.nodeUpdated.disconnect(self._on_node_updated)
        
        t0 = time.perf_counter()
        self._initial_sync_active = True
        
        # Pre-load all edges immediately
        for e in edges_payload:
            src_id = int(e["source_id"])
            tgt_id = int(e["target_id"])
            e_type = e["edge_type"]
            weight = float(e["weight"])
            self._upsert_edge(
                Edge(source_id=src_id, target_id=tgt_id, edge_type=e_type, weight=weight)
            )
            
        def load_batch(nodes_to_load, current_idx=0, batch_size=110):
            if current_idx >= len(nodes_to_load):
                self._initial_sync_active = False
                self.edgesChanged.emit()
                self.ipc.nodeUpdated.connect(self._on_node_updated)
                self._wake_physics()
                import time
                t1 = time.perf_counter()
                qml_ready_ms = self._qml_ready_time
                physics_init_ms = (t1-t0) * 1000.0 * 0.15 # Approx setup cost
                print(f"[T+{(t1 - self._t0)*1000:.1f}ms] All batches completed")
                print(f"[STARTUP PERF] DB Load: {db_load_ms:.1f}ms | Embeddings/Cache: {embed_cache_ms:.1f}ms | Physics Init: {physics_init_ms:.1f}ms | QML Ready: {qml_ready_ms:.1f}ms")
                return

            end_idx = min(current_idx + batch_size, len(nodes_to_load))
            self.blockSignals(True)
            for i in range(current_idx, end_idx):
                node_data = nodes_to_load[i]
                self._on_node_updated(node_data)
            self.blockSignals(False)
            self.nodesChanged.emit()
            
            if current_idx == 0:
                import time
                print(f"[T+{(time.perf_counter() - self._t0)*1000:.1f}ms] Canvas rendered Batch 1 (First visual node on screen)")
            
            if end_idx >= len(nodes_to_load):
                # Don't wait for another event loop tick if we're done
                load_batch(nodes_to_load, end_idx, batch_size)
            else:
                QTimer.singleShot(50, lambda: load_batch(nodes_to_load, end_idx, batch_size))
            
        load_batch(nodes, 0, 110)

    def _handle_touch_node_response(self, result: Any, error: str | None):
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

        if not getattr(self, "_initial_sync_active", False):
            self._recalculate_focal_weights(self._selected_node_id)
        self.edgesChanged.emit()

    def _handle_ambient_edges_response(self, result: dict, error: str | None):
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

        if self._selected_node_id == 0 and not getattr(self, "_initial_sync_active", False):
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

        archetype = data.get("archetype", "document")
        snippet = data.get("snippet", "")
        size_bytes = data.get("size_bytes", 0)

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
            
            new_node = Node(
                id=node_id, 
                file_path=file_path, 
                x=spawn_x, 
                y=spawn_y, 
                focus=0.35, 
                archetype=archetype, 
                snippet=snippet, 
                size_bytes=size_bytes
            )
            # Impart an initial outward impulse so it doesn't just sleep
            new_node.vx = math.cos(angle) * 40.0
            new_node.vy = math.sin(angle) * 40.0
            
            self.store.upsert_node(new_node)
            self.nodesChanged.emit()
        else:
            node.filePath = file_path
            node._archetype = archetype
            node._snippet = snippet
            node._size_bytes = size_bytes

        self._recalculate_focal_weights(self._selected_node_id)

    def _on_node_deleted(self, data: dict):
        self._wake_physics()
        raw_id = data.get("node_id") if data.get("node_id") is not None else data.get("id")
        if raw_id is not None:
            node_id = int(raw_id)
            node = self.store.get_node(node_id)
            if node:
                node.isDeleted = True
                
                def deferred_remove():
                    self.store.remove_node(node_id)
                    self._structural_edges = [e for e in self._structural_edges if e.sourceId != node_id and e.targetId != node_id]
                    self._ambient_edges = [e for e in self._ambient_edges if e.sourceId != node_id and e.targetId != node_id]
                    self._focal_edges = [e for e in self._focal_edges if e.sourceId != node_id and e.targetId != node_id]
                    self._recalculate_focal_weights(self._selected_node_id)
                    self.nodesChanged.emit()
                    self.edgesChanged.emit()
                    self.nodeRemoved.emit(node_id)
                
                QTimer.singleShot(250, deferred_remove)
            else:
                self.store.remove_node(node_id)
                self._structural_edges = [e for e in self._structural_edges if e.sourceId != node_id and e.targetId != node_id]
                self._ambient_edges = [e for e in self._ambient_edges if e.sourceId != node_id and e.targetId != node_id]
                self._focal_edges = [e for e in self._focal_edges if e.sourceId != node_id and e.targetId != node_id]
                self._recalculate_focal_weights(self._selected_node_id)
                self.nodesChanged.emit()
                self.edgesChanged.emit()
                self.nodeRemoved.emit(node_id)

    def _handle_neighbors_response(self, result: dict, error: str | None):
        if error or not result:
            return

        raw_edges = result.get("edges", [])
        parsed_edges: list[Edge] = [
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
                if priority[e.edgeType] > priority[current.edgeType] or priority[e.edgeType] == priority[current.edgeType] and e.weight > current.weight:
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
