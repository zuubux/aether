"""
Aether Physics Worker - Dedicated QThread Simulation Worker
Wraps PhysicsEngine and manages high-frequency integration timer.
"""

import logging
import threading
import time
import types
from typing import Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from .engine import PhysicsEngine

logger = logging.getLogger("aia_canvas.physics_worker")


class PhysicsWorker(QObject):
    """
    Worker QObject designed to execute on a dedicated QThread.
    Wraps PhysicsEngine, manages the simulation QTimer, and processes integration ticks.
    Implements a thread-safe latest-snapshot buffer and non-blocking signal pacing to
    prevent event loop flooding under consumer lag.
    """

    positions_updated = pyqtSignal(object)
    step_completed = pyqtSignal(float)
    stopped = pyqtSignal()

    def __init__(self, engine: PhysicsEngine | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self.engine: PhysicsEngine = engine if engine is not None else PhysicsEngine()
        self._timer: QTimer | None = None

        # State buffers for physics step calculations
        self._nodes: list = []
        self._edges: list = []
        self._focused_node_id: int = 0
        self._hovered_node_id: int = 0
        self._dt: float = 0.008
        self._first_degree_set: set | None = None
        self._second_degree_set: set | None = None
        self._second_degree_parent: dict | None = None
        self._focal_weights: dict | None = None

        # Coalescing & pacing snapshot buffer
        self._lock = threading.Lock()
        self._latest_snapshot: Any = None
        self._pending_update: bool = False

    @property
    def pending_update(self) -> bool:
        """Returns True if an update signal is pending consumption."""
        with self._lock:
            return self._pending_update

    @pyqtSlot(result=object)
    def get_latest_snapshot(self) -> Any:
        """
        Thread-safe retrieval of the latest position snapshot.
        Clears the pending update flag so subsequent worker ticks will emit updates.
        """
        with self._lock:
            self._pending_update = False
            return self._latest_snapshot

    @pyqtSlot()
    @pyqtSlot(int)
    def start(self, interval_ms: int = 8):
        """Starts the dedicated simulation QTimer on the worker's thread."""
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._on_timer_tick)

        if not self._timer.isActive():
            self._timer.start(interval_ms)

    @pyqtSlot()
    def stop(self):
        """Stops the simulation QTimer."""
        if self._timer and self._timer.isActive():
            self._timer.stop()
        self.stopped.emit()

    @pyqtSlot(str, float, float)
    @pyqtSlot(int, float, float)
    @pyqtSlot(object, float, float)
    def apply_node_drag(self, node_id: Any, x: float, y: float):
        """
        Updates internal simulation position and velocities when a drag command arrives.
        Executes on worker thread asynchronously.
        """
        try:
            nid = int(node_id)
        except (ValueError, TypeError):
            return

        x_val = float(x)
        y_val = float(y)

        self.engine.set_custom_anchor(nid, x_val, y_val)

        for node in self._nodes:
            if getattr(node, "id", None) == nid:
                node.x = x_val
                node.y = y_val
                if hasattr(node, "vx"):
                    node.vx = 0.0
                if hasattr(node, "vy"):
                    node.vy = 0.0
                break

        if self._timer and not self._timer.isActive():
            self._timer.start(8)

    @pyqtSlot(str, bool)
    @pyqtSlot(int, bool)
    @pyqtSlot(object, bool)
    def set_node_pinned(self, node_id: Any, pinned: bool):
        """
        Sets or clears pinned state on the simulation engine.
        """
        try:
            nid = int(node_id)
        except (ValueError, TypeError):
            return

        if pinned:
            self.engine.pin_node(nid)
        else:
            self.engine.unpin_node()
            if nid in self.engine.custom_anchors:
                del self.engine.custom_anchors[nid]

        if self._timer and not self._timer.isActive():
            self._timer.start(8)

    @pyqtSlot(str, bool)
    @pyqtSlot(int, bool)
    @pyqtSlot(object, bool)
    def set_active_focus(self, node_id: Any, is_focus: bool):
        """
        Updates active focus node ID on the worker simulation engine.
        """
        try:
            nid = int(node_id)
        except (ValueError, TypeError):
            return

        if is_focus:
            self._focused_node_id = nid
        elif self._focused_node_id == nid:
            self._focused_node_id = 0

        if self._timer and not self._timer.isActive():
            self._timer.start(8)

    @pyqtSlot(list, float, float)
    @pyqtSlot(list, float, float, float)
    def summon_nodes(self, node_ids: list, target_x: float, target_y: float, strength: float = 0.6):
        """Applies active summoning attractor vectors on the simulation engine."""
        self.engine.summon_nodes(node_ids, target_x, target_y, strength)
        if self._timer and not self._timer.isActive():
            self._timer.start(8)

    @pyqtSlot(float, float)
    def set_viewport_dimensions(self, width: float, height: float):
        """Updates viewport dimensions on the simulation engine."""
        self.engine.set_viewport_dimensions(width, height)

    @pyqtSlot(float, float)
    def set_focal_card_dimensions(self, width: float, height: float):
        """Updates focal card dimensions on the simulation engine."""
        self.engine.set_focal_card_dimensions(width, height)

    @pyqtSlot(float)
    def set_aperture(self, aperture: float):
        """Updates cognitive aperture on the simulation engine."""
        self.engine.set_aperture(aperture)

    @pyqtSlot(list, list)
    def sync_graph_data(self, nodes: list, edges: list):
        """
        Syncs full node/edge state buffers to worker.
        Converts input dict payloads into SimpleNamespace instances for internal engine integration.
        """
        self._nodes = [
            types.SimpleNamespace(**n) if isinstance(n, dict) else n
            for n in nodes
        ]
        self._edges = [
            types.SimpleNamespace(**e) if isinstance(e, dict) else e
            for e in edges
        ]

    @pyqtSlot()
    def step(
        self,
        nodes: list | None = None,
        edges: list | None = None,
        focused_node_id: int = 0,
        hovered_node_id: int = 0,
        dt: float = 0.008,
        first_degree_set: set | None = None,
        second_degree_set: set | None = None,
        second_degree_parent: dict | None = None,
        focal_weights: dict | None = None,
    ) -> bool:
        """
        Executes a single physics integration step via self.engine.step(...).
        Updates state buffers when explicit parameters are passed.
        Emits step_completed(float) and positions_updated(object) (paced).
        Returns True if system remains active, False if settled.
        """
        if nodes is not None:
            self._nodes = [
                types.SimpleNamespace(**n) if isinstance(n, dict) else n
                for n in nodes
            ]
        if edges is not None:
            self._edges = [
                types.SimpleNamespace(**e) if isinstance(e, dict) else e
                for e in edges
            ]
        self._focused_node_id = focused_node_id
        self._hovered_node_id = hovered_node_id
        self._dt = dt
        if first_degree_set is not None:
            self._first_degree_set = first_degree_set
        if second_degree_set is not None:
            self._second_degree_set = second_degree_set
        if second_degree_parent is not None:
            self._second_degree_parent = second_degree_parent
        if focal_weights is not None:
            self._focal_weights = focal_weights

        t0 = time.perf_counter_ns()

        is_active = self.engine.step(
            nodes=self._nodes,
            edges=self._edges,
            focused_node_id=self._focused_node_id,
            hovered_node_id=self._hovered_node_id,
            dt=self._dt,
            first_degree_set=self._first_degree_set,
            second_degree_set=self._second_degree_set,
            second_degree_parent=self._second_degree_parent,
            focal_weights=self._focal_weights,
        )

        t1 = time.perf_counter_ns()
        step_ms = (t1 - t0) / 1e6

        with self._lock:
            self._latest_snapshot = [
                {
                    "id": int(getattr(n, "id", None) if not isinstance(n, dict) else n.get("id")),
                    "x": float(getattr(n, "x", 0.0) if not isinstance(n, dict) else n.get("x", 0.0)),
                    "y": float(getattr(n, "y", 0.0) if not isinstance(n, dict) else n.get("y", 0.0)),
                }
                for n in self._nodes
            ]
            should_emit = not self._pending_update
            if should_emit:
                self._pending_update = True

        if should_emit:
            self.positions_updated.emit(self._latest_snapshot)

        self.step_completed.emit(step_ms)

        if not is_active and self._timer and self._timer.isActive():
            self._timer.stop()

        return is_active

    def _on_timer_tick(self):
        self.step()
