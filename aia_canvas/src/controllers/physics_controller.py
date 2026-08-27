from typing import Any
from PyQt6.QtCore import QCoreApplication, QThread, pyqtProperty, pyqtSignal, pyqtSlot

from core.telemetry import TelemetrySink
from physics.worker import PhysicsWorker
from .base_controller import BaseController


class PhysicsController(BaseController):
    """
    Controller managing graph physics mechanics, simulation loops, worker threads,
    repulsive/attractive forces, tendril physics telemetry, and relations.
    """

    nodesChanged = pyqtSignal()
    edgesChanged = pyqtSignal()
    clusterHalosChanged = pyqtSignal()
    telemetryChanged = pyqtSignal()
    connectionStatusChanged = pyqtSignal(bool)

    # Async signals routing to worker thread slots
    request_start = pyqtSignal(int)
    request_stop = pyqtSignal()
    request_drag = pyqtSignal(object, float, float)
    request_pin = pyqtSignal(object, bool)
    request_focus = pyqtSignal(object, bool)
    request_sync = pyqtSignal(list, list)
    request_summon = pyqtSignal(list, float, float)
    request_viewport = pyqtSignal(float, float)
    request_focal_card = pyqtSignal(float, float)
    request_aperture = pyqtSignal(float)

    def __init__(self, bridge, parent=None):
        super().__init__(bridge, parent)

        engine = getattr(bridge, "physics_engine", None)
        self.worker = PhysicsWorker(engine=engine)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        # Signal connections from worker
        self.worker.positions_updated.connect(self._on_positions_updated)
        self.worker.step_completed.connect(self._on_worker_step_completed)
        self.worker.stopped.connect(self.thread.quit)

        # Thread lifecycle connections
        self.thread.finished.connect(self.worker.deleteLater)

        # Internal cross-thread worker request routes
        self.request_start.connect(self.worker.start)
        self.request_stop.connect(self.worker.stop)
        self.request_drag.connect(self.worker.apply_node_drag)
        self.request_pin.connect(self.worker.set_node_pinned)
        self.request_focus.connect(self.worker.set_active_focus)
        self.request_sync.connect(self.worker.sync_graph_data)
        self.request_summon.connect(self.worker.summon_nodes)
        self.request_viewport.connect(self.worker.set_viewport_dimensions)
        self.request_focal_card.connect(self.worker.set_focal_card_dimensions)
        self.request_aperture.connect(self.worker.set_aperture)

        # Clean deterministic teardown on application exit
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.stop)

        self.thread.start()

    @pyqtSlot()
    @pyqtSlot(int)
    def start(self, interval_ms: int = 8):
        """Starts the physics worker simulation loop via queued signal."""
        self.request_start.emit(interval_ms)

    @pyqtSlot()
    def stop(self):
        """Stops physics worker loop and terminates worker QThread deterministically."""
        if hasattr(self, "worker") and self.worker:
            self.request_stop.emit()
        if hasattr(self, "thread") and self.thread and self.thread.isRunning():
            self.thread.quit()
            if not self.thread.wait(500):
                self.logger.warning("Physics QThread did not stop within 500ms timeout.")

    @pyqtSlot(str, float, float)
    @pyqtSlot(int, float, float)
    @pyqtSlot(object, float, float)
    def apply_node_drag(self, node_id: Any, x: float, y: float):
        """Routes node drag command asynchronously to PhysicsWorker slot."""
        self.request_drag.emit(node_id, float(x), float(y))

    @pyqtSlot(str, bool)
    @pyqtSlot(int, bool)
    @pyqtSlot(object, bool)
    def set_node_pinned(self, node_id: Any, pinned: bool):
        """Routes node pin state asynchronously to PhysicsWorker slot."""
        self.request_pin.emit(node_id, bool(pinned))

    @pyqtSlot(str, bool)
    @pyqtSlot(int, bool)
    @pyqtSlot(object, bool)
    def set_active_focus(self, node_id: Any, is_focus: bool):
        """Routes active focus node state asynchronously to PhysicsWorker slot."""
        self.request_focus.emit(node_id, bool(is_focus))

    @pyqtSlot(list, float, float)
    def summon_nodes(self, node_ids: list, target_x: float, target_y: float):
        """Routes node summoning command asynchronously to PhysicsWorker slot."""
        self.request_summon.emit(node_ids, float(target_x), float(target_y))

    @pyqtSlot(float, float)
    def set_viewport_dimensions(self, width: float, height: float):
        """Routes viewport dimension updates asynchronously to PhysicsWorker slot."""
        self.request_viewport.emit(float(width), float(height))

    @pyqtSlot(float, float)
    def set_focal_card_dimensions(self, width: float, height: float):
        """Routes focal card dimension updates asynchronously to PhysicsWorker slot."""
        self.request_focal_card.emit(float(width), float(height))

    @pyqtSlot(float)
    def set_aperture(self, aperture: float):
        """Routes aperture updates asynchronously to PhysicsWorker slot."""
        self.request_aperture.emit(float(aperture))

    @pyqtSlot(list, list)
    def sync_graph_data(self, nodes: list, edges: list):
        """Routes graph data buffer sync as pure primitive dicts to PhysicsWorker slot."""
        node_dicts = [
            {
                "id": int(n.id) if hasattr(n, "id") else int(n["id"]),
                "x": float(n.x) if hasattr(n, "x") else float(n["x"]),
                "y": float(n.y) if hasattr(n, "y") else float(n["y"]),
                "vx": float(getattr(n, "vx", 0.0) if not isinstance(n, dict) else n.get("vx", 0.0)),
                "vy": float(getattr(n, "vy", 0.0) if not isinstance(n, dict) else n.get("vy", 0.0)),
                "focus": float(getattr(n, "focus", 0.35) if not isinstance(n, dict) else n.get("focus", 0.35)),
                "clusterId": int(getattr(n, "clusterId", -1) if not isinstance(n, dict) else n.get("clusterId", -1)),
            }
            for n in nodes
        ]
        edge_dicts = [
            {
                "sourceId": int(e.sourceId) if hasattr(e, "sourceId") else int(e["sourceId"]),
                "targetId": int(e.targetId) if hasattr(e, "targetId") else int(e["targetId"]),
                "edgeType": str(getattr(e, "edgeType", "semantic") if not isinstance(e, dict) else e.get("edgeType", "semantic")),
                "weight": float(getattr(e, "weight", 1.0) if not isinstance(e, dict) else e.get("weight", 1.0)),
                "category": str(getattr(e, "category", "topological") if not isinstance(e, dict) else e.get("category", "topological")),
            }
            for e in edges
        ]
        self.request_sync.emit(node_dicts, edge_dicts)

    @pyqtSlot(object)
    def _on_positions_updated(self, snapshot: Any = None):
        """
        Paced reception slot for latest position snapshots from PhysicsWorker.
        Fetches the latest snapshot from the worker, clearing the worker's pending update flag,
        and triggers UI notifications without blocking the main event loop.
        """
        latest = self.worker.get_latest_snapshot()
        if latest is None:
            latest = snapshot

        if hasattr(self.bridge, "_on_positions_updated"):
            self.bridge._on_positions_updated(latest)

        self.nodesChanged.emit()

    def _on_worker_step_completed(self, step_ms: float):
        TelemetrySink.instance().record_physics_step(step_ms)
        if hasattr(self.bridge, "_last_frametime_ms"):
            self.bridge._last_frametime_ms = step_ms
        self.telemetryChanged.emit()

    @pyqtProperty(list, notify=nodesChanged)
    def nodes(self) -> list:
        if hasattr(self.bridge, "store") and self.bridge.store:
            return self.bridge.store.get_all_nodes()
        return []

    @pyqtProperty(list, notify=edgesChanged)
    def edges(self) -> list:
        base_edges = []
        if getattr(self.bridge, "_selected_node_id", 0) > 0:
            # 1. Start with curated, deduplicated focal edges
            base_edges = list(getattr(self.bridge, "_focal_edges", []))
            
            # 2. Exclude any ambient edges touching the focused node to prevent duplicate filaments
            selected_node_id = self.bridge._selected_node_id
            for e in getattr(self.bridge, "_ambient_edges", []):
                if e.sourceId == selected_node_id or e.targetId == selected_node_id:
                    if getattr(e, "edgeType", None) not in ("explicit", "wikilink", "direct"):
                        continue
                base_edges.append(e)
        else:
            base_edges = getattr(self.bridge, "_ambient_edges", [])
            
        # 3. Global deduplication by priority to ensure no visual overlap
        unique_edges = {}
        priority = {
            "explicit": 3,
            "wikilink": 3,
            "direct": 3,
            "semantic_link": 2,
            "semantic": 1,
            "temporal": 0
        }
        for e in base_edges:
            # Include category in pair_key so temporal and topological can coexist as dual tendrils
            pair_key = (min(e.sourceId, e.targetId), max(e.sourceId, e.targetId), e.category)
            current = unique_edges.get(pair_key)
            if not current:
                unique_edges[pair_key] = e
            else:
                if priority.get(e.edgeType, 0) > priority.get(current.edgeType, 0) or (priority.get(e.edgeType, 0) == priority.get(current.edgeType, 0) and e.weight > current.weight):
                    unique_edges[pair_key] = e
                    
        return list(unique_edges.values())

    @pyqtProperty(list, notify=clusterHalosChanged)
    def clusterHalos(self) -> list:
        return getattr(self.bridge, "_cluster_halos", [])

    @pyqtProperty(float, notify=telemetryChanged)
    def physicsFrametime(self) -> float:
        step_ms = TelemetrySink.instance().physics_step_ms
        return step_ms if step_ms > 0.0 else getattr(self.bridge, "_last_frametime_ms", 0.0)

    @pyqtProperty(int, notify=telemetryChanged)
    def activeNodeCount(self) -> int:
        if hasattr(self.bridge, "store") and self.bridge.store:
            return len(self.bridge.store.get_all_nodes())
        return 0

    @pyqtProperty(int, notify=telemetryChanged)
    def activeEdgeCount(self) -> int:
        return len(self.edges)

    @pyqtProperty(bool, notify=connectionStatusChanged)
    def isConnected(self) -> bool:
        return getattr(self.bridge, "_is_connected", False)
