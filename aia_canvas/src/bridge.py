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
    ambientEdgesChanged = pyqtSignal()
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
    focalCardDimensionsChanged = pyqtSignal()

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
        from core.intent_dispatcher import IntentDispatcher
        from core.completion_engine import CompletionEngine

        self.canvas_ctrl = CanvasController(self)
        self.intent_dispatcher = IntentDispatcher(self)
        self.search_ctrl = SearchController(self)
        self.node_ctrl = NodeController(self)
        self.physics_ctrl = PhysicsController(self)
        self.completion_engine = CompletionEngine(self)

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
        self._focal_card_width: float = 880.0
        self._focal_card_height: float = 600.0

        self.physics.set_focal_card_dimensions(self._workbench_width, self._workbench_height)
        self.physics.set_aperture(self._aperture)

        self._cluster_halos: list = []
        self._last_frametime_ms: float = 0.0
        
        self.telemetry = TelemetryCollector()

        # Graph Separation: Structural vs Render Subset
        self._structural_edges: list[Edge] = []
        self._ambient_edges: list[Edge] = []
        self._focal_edges: list[Edge] = []

        self.TOPOLOGICAL_PRIORITY = {
            "explicit": 3,
            "wikilink": 3,
            "direct": 3,
            "semantic_link": 2,
            "semantic": 1
        }

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

        # Ensure explicit edges from ambient pool are also included to maintain Tier 1 retention
        ambient_explicits = [e for e in self._ambient_edges if getattr(e, "edgeType", None) in ("explicit", "wikilink", "direct")]
        edges = self._get_deduplicated_edges(self._focal_edges + ambient_explicits)
        edges = self.deduplicate_undirected_focal_edges(primary_id, edges)
        
        explicit_first_degree: set[int] = set()
        semantic_first_degree: set[int] = set()
        temporal_first_degree: set[int] = set()
        focal_weights: dict[int, float] = {}
        
        for e in edges:
            if primary_id in (e.sourceId, e.targetId):
                target = e.targetId if e.sourceId == primary_id else e.sourceId
                if e.edgeType == "temporal":
                    temporal_first_degree.add(target)
                    self._cached_second_degree_parent[target] = primary_id
                    focal_weights[target] = max(focal_weights.get(target, 0.0), e.weight)
                elif getattr(e, "edgeType", None) in ("explicit", "wikilink"):
                    explicit_first_degree.add(target)
                    focal_weights[target] = max(focal_weights.get(target, 0.0), e.weight)
                else:
                    semantic_first_degree.add(target)
                    focal_weights[target] = max(focal_weights.get(target, 0.0), e.weight)

        first_degree = explicit_first_degree.union(semantic_first_degree).union(temporal_first_degree)

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

        # Temporals go to Tier 2 (Focus 0.35)
        # To handle this cleanly we can keep them out of standard second_degree or just map their focus explicitly
        temporal_only = temporal_first_degree - (explicit_first_degree | semantic_first_degree)

        self._cached_first_degree = first_degree
        self._cached_second_degree = second_degree
        self._cached_focal_weights = focal_weights

        for node in self.store.get_all_nodes():
            if node.id == primary_id:
                node.focus = 1.0
            elif node.id in explicit_first_degree:
                node.focus = 0.70
            elif node.id in semantic_first_degree:
                node.focus = 0.60
            elif node.id in temporal_only:
                node.focus = 0.35
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
        explicits = [e for e in self._structural_edges if e.edgeType in ("explicit", "wikilink", "direct")]
        semantics = [e for e in self._structural_edges if e.edgeType in ("semantic", "semantic_link")]

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
        if hasattr(self.physics_ctrl, "edges"):
            return self.physics_ctrl.edges
        return getattr(self, "_ambient_edges", [])

    @pyqtProperty(list, notify=ambientEdgesChanged)
    def ambientEdges(self) -> list[Edge]:
        return getattr(self, "_ambient_edges", [])

    @pyqtProperty(list, notify=edgesChanged)
    def focalEdges(self) -> list[Edge]:
        return getattr(self, "_focal_edges", [])

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

    @pyqtProperty(float, notify=focalCardDimensionsChanged)
    def focalCardWidth(self) -> float:
        return self._focal_card_width

    @focalCardWidth.setter
    def focalCardWidth(self, val: float):
        if self._focal_card_width != val:
            self._focal_card_width = val
            self.physics.set_focal_card_dimensions(self._focal_card_width, self._focal_card_height)
            self.focalCardDimensionsChanged.emit()
            self._wake_physics()

    @pyqtProperty(float, notify=focalCardDimensionsChanged)
    def focalCardHeight(self) -> float:
        return self._focal_card_height

    @focalCardHeight.setter
    def focalCardHeight(self, val: float):
        if self._focal_card_height != val:
            self._focal_card_height = val
            self.physics.set_focal_card_dimensions(self._focal_card_width, self._focal_card_height)
            self.focalCardDimensionsChanged.emit()
            self._wake_physics()

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
        if hasattr(self.physics_ctrl, "activeEdgeCount"):
            return self.physics_ctrl.activeEdgeCount
        return len(getattr(self, "_ambient_edges", []))

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

    @pyqtSlot(str)
    @pyqtSlot(str, int)
    def execute_intent(self, raw_text: str, context_override: int = 0):
        ctx = context_override if context_override > 0 else None
        self.intent_dispatcher.dispatch(raw_text, ctx)

    @pyqtSlot(str, int, result=list)
    def get_completions(self, text: str, cursor_pos: int) -> list:
        return self.completion_engine.get_completions(text, cursor_pos)

    @pyqtSlot()
    def clear_search(self):
        self.search_ctrl.clear_search()

    @pyqtSlot(bool)
    def set_search_active(self, active: bool):
        self.search_ctrl.set_search_active(active)

    @pyqtSlot(int)
    @pyqtSlot(str)
    def focus_node(self, node_id):
        if isinstance(node_id, str):
            try:
                node_id = int(node_id)
            except ValueError:
                return
        self.node_ctrl.select_node(node_id)

    @pyqtSlot(int, result=QObject)
    def get_node(self, node_id: int):
        if hasattr(self, "store") and self.store:
            return self.store.get_node(node_id)
        return None

    @pyqtSlot(int)
    def set_hovered_node(self, node_id: int):
        self._hovered_node_id = node_id
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

    @pyqtSlot(int, float, float)
    def updateNodePosition(self, node_id: int, x: float, y: float):
        self.node_ctrl.update_drag_pos(node_id, x, y)

    @pyqtSlot(int, float, float)
    def update_node_position(self, node_id: int, x: float, y: float):
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
            
        self._structural_edges = self._get_deduplicated_edges(self._structural_edges)
            
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
        raw_persisted = result.get("persisted_edges", [])

        # Merge incoming edges with existing explicit links in memory
        existing_explicit = [e for e in self._focal_edges if getattr(e, "edgeType", None) in ("explicit", "wikilink")]
        
        for e in raw_temporal:
            src_id = int(e["source_id"])
            tgt_id = int(e["target_id"])
            weight = float(e.get("weight", 1.0))
            edge_obj = Edge(source_id=src_id, target_id=tgt_id, edge_type="temporal", weight=weight, category="temporal")
            self._upsert_edge(edge_obj)

            if self._selected_node_id in (src_id, tgt_id):
                existing_explicit.append(edge_obj)

        for e in raw_persisted:
            src_id = int(e["source_id"])
            tgt_id = int(e["target_id"])
            edge_type = e.get("edge_type", "explicit")
            weight = float(e.get("weight", 1.0))
            edge_obj = Edge(source_id=src_id, target_id=tgt_id, edge_type=edge_type, weight=weight, category="topological")
            self._upsert_edge(edge_obj)

            if self._selected_node_id in (src_id, tgt_id):
                existing_explicit.append(edge_obj)

        # Run deduplication to fix lane offsets if topo exists
        self._focal_edges = self._get_deduplicated_edges(existing_explicit)

        if not getattr(self, "_initial_sync_active", False):
            self._recalculate_focal_weights(self._selected_node_id)
        self.edgesChanged.emit()

    def _handle_ambient_edges_response(self, result: dict, error: str | None):
        if error or not result:
            return

        raw_edges = result.get("edges", [])
        raw_edges.extend(result.get("neighbors", []))
        raw_edges.extend(result.get("persisted_edges", []))
        raw_edges.extend(result.get("temporal_edges", []))
        
        for e in raw_edges:
            src_id = int(e["source_id"])
            tgt_id = int(e["target_id"])
            e_type = e.get("edge_type", e.get("edgeType", "semantic"))
            weight = float(e.get("weight", 1.0))
            category = "temporal" if e_type == "temporal" else "topological"
            self._upsert_edge(
                Edge(source_id=src_id, target_id=tgt_id, edge_type=e_type, weight=weight, category=category)
            )

        if not getattr(self, "_initial_sync_active", False):
            self.ambientEdgesChanged.emit()
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
        thumbnail_url = data.get("thumbnail_url", "")

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
                size_bytes=size_bytes,
                thumbnail_url=thumbnail_url
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
            node._thumbnail_url = thumbnail_url

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

    def _get_deduplicated_edges(self, raw_edges: list) -> list:
        topo_edges = {}
        temporal_edges = {}

        for e in raw_edges:
            # Handle both Edge objects and dicts
            is_obj = isinstance(e, Edge)
            src = e.sourceId if is_obj else (e.get("source") or e.get("sourceId") or e.get("source_id"))
            tgt = e.targetId if is_obj else (e.get("target") or e.get("targetId") or e.get("target_id"))
            etype = e.edgeType if is_obj else (e.get("edgeType") or e.get("edge_type", "semantic"))
            weight = e.weight if is_obj else float(e.get("weight", 1.0))
            
            pair_key = tuple(sorted([int(src), int(tgt)]))

            if etype == "temporal":
                if pair_key not in temporal_edges:
                    temporal_edges[pair_key] = Edge(
                        source_id=int(src), target_id=int(tgt), edge_type=etype, weight=weight,
                        category="temporal"
                    )
            else:
                if pair_key not in topo_edges:
                    topo_edges[pair_key] = Edge(
                        source_id=int(src), target_id=int(tgt), edge_type=etype, weight=weight,
                        category="topological"
                    )
                else:
                    curr_type = topo_edges[pair_key].edgeType
                    if self.TOPOLOGICAL_PRIORITY.get(etype, 0) > self.TOPOLOGICAL_PRIORITY.get(curr_type, 0):
                        topo_edges[pair_key] = Edge(
                            source_id=int(src), target_id=int(tgt), edge_type=etype, weight=weight,
                            category="topological"
                        )

        deduped_edges = list(topo_edges.values()) + list(temporal_edges.values())
        # print(f"[Bridge] Edges before dedup: {len(raw_edges)} | After dedup: {len(deduped_edges)} (Topo + Temporal)")
        return deduped_edges

    def deduplicate_undirected_focal_edges(self, focal_id: int, edges: list) -> list:
        seen_pairs = set()
        deduped = []

        for edge in edges:
            is_obj = hasattr(edge, "sourceId") or isinstance(edge, Edge)
            src = edge.sourceId if is_obj else (edge.get("source") or edge.get("sourceId") or edge.get("source_id"))
            tgt = edge.targetId if is_obj else (edge.get("target") or edge.get("targetId") or edge.get("target_id"))
            edge_type = edge.edgeType if is_obj else (edge.get("edgeType") or edge.get("edge_type", "semantic"))
            
            if src is None or tgt is None:
                continue
            src, tgt = int(src), int(tgt)
            # 1. Enforce max 1 SEMANTIC edge per wing target
            pair_key = (min(src, tgt), max(src, tgt), edge_type)
            if pair_key in seen_pairs:
                continue
            
            seen_pairs.add(pair_key)
            deduped.append(edge)

        # After basic pair-key deduplication, we also enforce:
        # "each target node receives exactly ONE radial line from the focal card unless it has distinct explicit + temporal pairings."
        by_target = {}
        for edge in deduped:
            is_obj = hasattr(edge, "sourceId") or isinstance(edge, Edge)
            src = edge.sourceId if is_obj else (edge.get("source") or edge.get("sourceId") or edge.get("source_id"))
            tgt = edge.targetId if is_obj else (edge.get("target") or edge.get("targetId") or edge.get("target_id"))
            src, tgt = int(src), int(tgt)
            other_id = tgt if src == focal_id else src
            if other_id not in by_target:
                by_target[other_id] = []
            by_target[other_id].append(edge)
            
        final_deduped = []
        for other_id, target_edges in by_target.items():
            explicits = []
            temporals = []
            semantics = []
            for e in target_edges:
                is_obj = hasattr(e, "sourceId") or isinstance(e, Edge)
                etype = e.edgeType if is_obj else (e.get("edgeType") or e.get("edge_type", "semantic"))
                if etype in ("explicit", "wikilink", "direct"):
                    explicits.append(e)
                elif etype == "temporal":
                    temporals.append(e)
                elif etype in ("semantic", "knn", "semantic_link"):
                    semantics.append(e)
            
            def get_weight(e):
                is_obj = hasattr(e, "sourceId") or isinstance(e, Edge)
                return e.weight if is_obj else float(e.get("weight", 0.0))

            if explicits and temporals:
                best_explicit = sorted(explicits, key=get_weight, reverse=True)[0]
                best_temporal = sorted(temporals, key=get_weight, reverse=True)[0]
                final_deduped.append(best_explicit)
                final_deduped.append(best_temporal)
            elif explicits:
                best_explicit = sorted(explicits, key=get_weight, reverse=True)[0]
                final_deduped.append(best_explicit)
            elif temporals:
                best_temporal = sorted(temporals, key=get_weight, reverse=True)[0]
                final_deduped.append(best_temporal)
            elif semantics:
                best_semantic = sorted(semantics, key=get_weight, reverse=True)[0]
                final_deduped.append(best_semantic)
                
        return final_deduped

    def budget_focal_edges(self, focal_node_id: int, raw_edges: list, max_total: int = 8) -> list:
        # Deduplicate raw edges first so we filter by unique pair keys/rules
        deduped_raw = self.deduplicate_undirected_focal_edges(focal_node_id, raw_edges)

        # Separate edges by classification
        explicit_edges = [e for e in deduped_raw if getattr(e, "edgeType", None) in ("explicit", "wikilink")]
        semantic_edges = sorted(
            [e for e in deduped_raw if getattr(e, "edgeType", None) in ("semantic", "knn", "semantic_link")],
            key=lambda e: getattr(e, "weight", 0.0),
            reverse=True
        )
        temporal_edges = sorted(
            [e for e in deduped_raw if getattr(e, "edgeType", None) == "temporal"],
            key=lambda e: getattr(e, "weight", 0.0),
            reverse=True
        )

        # Ensure only 1 temporal connection exists between any unique node pair
        seen_temporal_targets = set()
        deduped_temporal = []
        for edge in temporal_edges:
            target_id = edge.targetId if edge.sourceId == focal_node_id else edge.sourceId
            if target_id not in seen_temporal_targets:
                seen_temporal_targets.add(target_id)
                deduped_temporal.append(edge)
        temporal_edges = deduped_temporal

        # Quota allocation
        # Explicit: up to 4
        explicit_quota = min(4, len(explicit_edges))
        explicit_rollover = max(0, 4 - explicit_quota)
        
        # Semantic: 2 + explicit_rollover
        semantic_target = 2 + explicit_rollover
        semantic_quota = min(semantic_target, len(semantic_edges))
        semantic_rollover = max(0, semantic_target - semantic_quota)
        
        # Temporal: 2 + semantic_rollover
        temporal_target = 2 + semantic_rollover
        temporal_quota = min(temporal_target, len(temporal_edges))
        
        selected_edges = (
            explicit_edges[:explicit_quota] + 
            semantic_edges[:semantic_quota] + 
            temporal_edges[:temporal_quota]
        )
        
        return selected_edges

    def _handle_neighbors_response(self, result: dict, error: str | None):
        if error or not result:
            return

        raw_edges = result.get("edges", [])
        raw_edges.extend(result.get("neighbors", []))
        raw_edges.extend(result.get("persisted_edges", []))
        raw_edges.extend(result.get("temporal_edges", []))
        
        # 1. Vacuum Seal: ONLY preserve live temporal edges that ACTUALLY touch the current focal lens
        existing_temporals = [
            e for e in self._focal_edges 
            if e.edgeType == "temporal" and (e.sourceId == self._selected_node_id or e.targetId == self._selected_node_id)
        ]

        active_explicit = [
            e for e in self._focal_edges 
            if getattr(e, "edgeType", None) in ("explicit", "wikilink")
        ]
        
        filtered_raw = [
            e for e in raw_edges 
            if e.get("edgeType", e.get("edge_type", None)) not in ("explicit", "wikilink")
        ]
        
        combined_edges = filtered_raw + existing_temporals + active_explicit
        
        # 2. Universal Deduplication using the new dual-track method
        deduped_edges = self._get_deduplicated_edges(combined_edges)
        
        # Sibling Edge Filtering
        filtered_edges = []
        for edge in deduped_edges:
            is_direct_spoke = (edge.sourceId == self._selected_node_id or edge.targetId == self._selected_node_id)
            edge_type = getattr(edge, "edgeType", "semantic")

            if is_direct_spoke:
                filtered_edges.append(edge)
            else:
                if edge_type in ("explicit", "wikilink", "temporal"):
                    filtered_edges.append(edge)
                elif edge_type in ("semantic", "knn"):
                    continue

        connected_edges = filtered_edges

        # Use new budget logic (8 total max across left/right)
        self._focal_edges = self.budget_focal_edges(self._selected_node_id, connected_edges, max_total=8)

        self._recalculate_focal_weights(self._selected_node_id)
        self.edgesChanged.emit()
