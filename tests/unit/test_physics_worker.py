"""
Unit tests for PhysicsWorker, PhysicsController thread lifecycle, and PhysicsEngine synchronous harness.
"""

from unittest.mock import MagicMock
import pytest
from PyQt6.QtCore import QCoreApplication, QThread

from models import Node, Edge
from physics.engine import PhysicsEngine
from physics.worker import PhysicsWorker
from controllers.physics_controller import PhysicsController


def test_physics_worker_initialization():
    """Verify PhysicsWorker wraps PhysicsEngine correctly."""
    engine = PhysicsEngine()
    worker = PhysicsWorker(engine=engine)
    assert worker.engine is engine

    # Test default initialization creates its own engine instance
    default_worker = PhysicsWorker()
    assert isinstance(default_worker.engine, PhysicsEngine)


def test_physics_worker_step_signals(qapp):
    """Verify PhysicsWorker.step emits positions_updated and step_completed signals."""
    engine = PhysicsEngine()
    worker = PhysicsWorker(engine=engine)

    positions_received = []
    step_times = []

    worker.positions_updated.connect(lambda pos: positions_received.append(pos))
    worker.step_completed.connect(lambda dt: step_times.append(dt))

    node = Node(id=1, file_path="/test/node.md", x=100.0, y=100.0)
    nodes = [node]

    is_active = worker.step(nodes=nodes, dt=0.008)

    assert len(positions_received) == 1
    assert positions_received[0][0]["id"] == node.id
    assert len(step_times) == 1
    assert isinstance(step_times[0], float)
    assert step_times[0] >= 0.0


def test_physics_worker_start_stop_slots(qapp):
    """Verify PhysicsWorker start and stop slots manage simulation timer and emit stopped signal."""
    worker = PhysicsWorker()
    stopped_emitted = []
    worker.stopped.connect(lambda: stopped_emitted.append(True))

    assert worker._timer is None or not worker._timer.isActive()

    worker.start(16)
    assert worker._timer is not None
    assert worker._timer.isActive()

    worker.stop()
    assert not worker._timer.isActive()
    assert len(stopped_emitted) == 1


def test_physics_controller_thread_lifecycle(qapp):
    """Verify PhysicsController moves worker to QThread and cleans up deterministically."""
    mock_bridge = MagicMock()
    mock_bridge.physics_engine = PhysicsEngine()

    ctrl = PhysicsController(mock_bridge)

    assert hasattr(ctrl, "worker")
    assert isinstance(ctrl.worker, PhysicsWorker)
    assert ctrl.worker.thread() == ctrl.thread
    assert ctrl.thread.isRunning()

    ctrl.start(16)

    # Verify deterministic teardown
    ctrl.stop()
    assert not ctrl.thread.isRunning()


def test_synchronous_physics_engine_step_harness():
    """Verify PhysicsEngine.step remains directly and synchronously callable without async waits."""
    engine = PhysicsEngine()
    n1 = Node(id=1, file_path="/test/a.md", x=0.0, y=0.0)
    n2 = Node(id=2, file_path="/test/b.md", x=10.0, y=10.0)
    edge = Edge(source_id=1, target_id=2, edge_type="explicit", category="topological")

    nodes = [n1, n2]
    edges = [edge]

    # Synchronous step call
    is_active = engine.step(nodes=nodes, edges=edges, focused_node_id=0)
    assert isinstance(is_active, bool)


def test_physics_worker_snapshot_coalescing():
    """Verify that PhysicsWorker coalesces rapid steps and drops intermediate updates when consumer is delayed."""
    engine = PhysicsEngine()
    worker = PhysicsWorker(engine=engine)

    signal_emissions = []
    worker.positions_updated.connect(lambda snapshot: signal_emissions.append(snapshot))

    n1 = Node(id=1, file_path="/test/a.md", x=0.0, y=0.0)
    n2 = Node(id=2, file_path="/test/b.md", x=10.0, y=10.0)
    edge = Edge(source_id=1, target_id=2, edge_type="explicit", category="topological")
    nodes = [n1, n2]
    edges = [edge]

    # First step emits signal and marks update as pending
    worker.step(nodes=nodes, edges=edges)
    assert len(signal_emissions) == 1
    assert worker.pending_update is True

    # Subsequent high-frequency ticks without consumer reading snapshot MUST NOT emit additional signals
    for _ in range(10):
        worker.step()

    assert len(signal_emissions) == 1
    assert worker.pending_update is True

    # Main thread consumer reads latest snapshot
    latest_snapshot = worker.get_latest_snapshot()
    assert worker.pending_update is False
    assert latest_snapshot[0]["id"] == n1.id

    # Next step after consumption emits a new signal
    worker.step()
    assert len(signal_emissions) == 2


def test_physics_controller_paced_reception(qapp):
    """Verify PhysicsController receives position snapshots in a non-blocking paced slot and updates UI signals."""
    mock_bridge = MagicMock()
    mock_bridge.physics_engine = PhysicsEngine()
    mock_bridge._on_positions_updated = MagicMock()

    ctrl = PhysicsController(mock_bridge)

    nodes_changed_events = []
    ctrl.nodesChanged.connect(lambda: nodes_changed_events.append(True))

    n1 = Node(id=1, file_path="/test/a.md", x=50.0, y=50.0)
    ctrl.worker.step(nodes=[n1])

    # Signal connection triggers _on_positions_updated, which clears pending_update
    assert ctrl.worker.pending_update is False
    assert len(nodes_changed_events) >= 1
    mock_bridge._on_positions_updated.assert_called()

    ctrl.stop()


def test_physics_worker_high_frequency_lag_prevention(qapp):
    """Verify high-frequency ticks under consumer delay deliver the newest state without unbound signal queue growth."""
    worker = PhysicsWorker()

    signals = []
    worker.positions_updated.connect(lambda snapshot: signals.append(snapshot))

    nodes = [Node(id=1, file_path="/test/node.md", x=0.0, y=0.0)]

    # Run 50 ticks rapidly
    for i in range(50):
        nodes[0].x = float(i)
        worker.step(nodes=nodes)

    # Exactly 1 signal should be queued/emitted despite 50 ticks
    assert len(signals) == 1
    assert worker.pending_update is True

    # Consumer reads snapshot: gets latest coordinate (>45.0), not stale initial x=0.0
    freshest = worker.get_latest_snapshot()
    assert freshest[0]["x"] > 45.0
    assert worker.pending_update is False



def test_physics_worker_drag_pin_focus_slots(qapp):
    """Verify Phase 3 drag, pin, and focus slots update internal state correctly."""
    from core.telemetry import TelemetrySink

    engine = PhysicsEngine()
    worker = PhysicsWorker(engine=engine)

    node = Node(id=42, file_path="/test/drag.md", x=0.0, y=0.0)
    worker.sync_graph_data([node], [])

    # Drag node with string ID
    worker.apply_node_drag("42", 500.0, 300.0)
    assert engine.custom_anchors[42] == (500.0, 300.0)
    assert worker._nodes[0].x == 500.0
    assert worker._nodes[0].y == 300.0

    # Pin node with int ID
    worker.set_node_pinned(42, True)
    assert engine.pinned_node_id == 42

    # Unpin node with string ID
    worker.set_node_pinned("42", False)
    assert engine.pinned_node_id == 0

    # Set active focus
    worker.set_active_focus("42", True)
    assert worker._focused_node_id == 42
    worker.set_active_focus(42, False)
    assert worker._focused_node_id == 0


def test_physics_controller_telemetry_sink_hook(qapp):
    """Verify PhysicsWorker step execution records latencies in TelemetrySink."""
    from core.telemetry import TelemetrySink

    sink = TelemetrySink.instance()
    sink.reset()

    mock_bridge = MagicMock()
    mock_bridge.physics_engine = PhysicsEngine()

    ctrl = PhysicsController(mock_bridge)
    ctrl._on_worker_step_completed(2.45)

    assert sink.physics_step_ms == 2.45
    assert ctrl.physicsFrametime == 2.45

    ctrl.stop()


def test_end_to_end_bridge_positions_update_handshake(qapp):
    """Verify CanvasBridge updates main thread Node models upon consuming position snapshots."""
    from bridge import CanvasBridge

    bridge = CanvasBridge()
    node = Node(id=99, file_path="/test/handshake.md", x=10.0, y=10.0)
    bridge.store.upsert_node(node)

    # Worker snapshot arrives with updated coordinates
    updated_node = Node(id=99, file_path="/test/handshake.md", x=250.0, y=180.0)
    bridge._on_positions_updated([updated_node])

    assert node.x == 250.0
    assert node.y == 180.0

    if hasattr(bridge, "physics_ctrl") and bridge.physics_ctrl:
        bridge.physics_ctrl.stop()

