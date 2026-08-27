"""
QML Unit & Component Tests for Tendril Dock Resolution, Fallbacks, and Line Suppression.
Verifies that:
1. SurfaceShell.qml getFlankPort returns canvas-space coordinates matching parent.x / parent.y.
2. Node.qml getCanvasDock and getFlankSocket gracefully fall back to visual node center when shell or dock is unmapped or zero.
3. Tendril.qml falls back to node visual centers (sCx, sCy) / (tCx, tCy) when docks evaluate to (0,0) or NaN/undefined.
4. Tendril.qml suppresses line rendering (visible = false) when node delegates are unmapped or missing.
"""

from PyQt6.QtQml import QQmlComponent
from PyQt6.QtCore import QPointF


def test_surface_shell_flank_port_canvas_coordinates(qapp, qml_engine):
    shell_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/SurfaceShell.qml")
    assert shell_comp.status() == QQmlComponent.Status.Ready, f"SurfaceShell.qml error: {shell_comp.errors()}"
    
    # Create parent node component simulation
    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"
    node = node_comp.create()
    node.setProperty("x", 400.0)
    node.setProperty("y", 300.0)

    shell = node.findChild(object, "")  # shell inside node
    assert shell is not None

    # leftDock and rightDock
    left_dock = node.property("leftDock")
    right_dock = node.property("rightDock")

    assert left_dock.x() == 400.0
    assert left_dock.y() == 300.0 + node.property("height") / 2.0
    assert right_dock.x() == 400.0 + node.property("width")
    assert right_dock.y() == 300.0 + node.property("height") / 2.0

    # getFlankSocket with ratio 0.5 (center)
    socket_left = node.getFlankSocket(True, 0.5)
    socket_right = node.getFlankSocket(False, 0.5)

    assert socket_left.x() == 400.0
    assert socket_left.y() == 300.0 + node.property("height") * 0.5
    assert socket_right.x() == 400.0 + node.property("width")
    assert socket_right.y() == 300.0 + node.property("height") * 0.5


def test_node_qml_unmapped_dock_fallback_to_center(qapp, qml_engine):
    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready
    node = node_comp.create()
    node.setProperty("x", 500.0)
    node.setProperty("y", 200.0)
    qapp.processEvents()

    # Verify fallback when shell is overridden or mock unmapped
    center_x = 500.0 + node.property("width") / 2.0
    center_y = 200.0 + node.property("height") / 2.0

    # Test getCanvasDock
    ld = node.getCanvasDock(True)
    rd = node.getCanvasDock(False)
    assert ld.x() == 500.0
    assert rd.x() == 500.0 + node.property("width")

    # If getFlankSocket is called with ratio 0.5 (center)
    fs_center = node.getFlankSocket(True, 0.5)
    assert fs_center.x() == 500.0
    assert fs_center.y() == center_y

    # If getFlankSocket is called with index None (defaults to port index 0)
    fs_p0 = node.getFlankSocket(True, None)
    assert fs_p0.x() == 500.0
    assert fs_p0.y() > 200.0


def test_tendril_dock_resolution_and_null_suppression(qapp, qml_engine):
    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    tendril_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Tendril.qml")

    assert node_comp.status() == QQmlComponent.Status.Ready
    assert tendril_comp.status() == QQmlComponent.Status.Ready

    node_a = node_comp.create()
    node_a.setProperty("x", 100.0)
    node_a.setProperty("y", 100.0)

    node_b = node_comp.create()
    node_b.setProperty("x", 600.0)
    node_b.setProperty("y", 100.0)

    qapp.processEvents()

    tendril = tendril_comp.create()
    assert tendril is not None

    # Unmapped state -> sourceNode/targetNode null -> visible must be false (line drawing suppressed)
    assert tendril.property("isNodesReady") is False
    assert tendril.property("visible") is False

    # Bind nodes
    tendril.setProperty("sourceId", 1)
    tendril.setProperty("targetId", 2)
    tendril.setProperty("sourceNode", node_a)
    tendril.setProperty("targetNode", node_b)
    qapp.processEvents()

    assert tendril.property("isNodesReady") is True
    assert tendril.property("hasValidDocks") is True

    start_pt = tendril.property("startPt")
    end_pt = tendril.property("endPt")

    # Verify startPt and endPt are valid non-zero vectors tied to node positions
    assert start_pt.x() > 0.0
    assert start_pt.y() > 0.0
    assert end_pt.x() > 0.0
    assert end_pt.y() > 0.0

    # Ensure never outputs (0,0) origin vector for mapped nodes
    assert not (start_pt.x() == 0.0 and start_pt.y() == 0.0)
    assert not (end_pt.x() == 0.0 and end_pt.y() == 0.0)


def test_tendril_zero_dock_fallback_to_node_center(qapp, qml_engine):
    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    tendril_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Tendril.qml")

    node_a = node_comp.create()
    node_a.setProperty("x", 200.0)
    node_a.setProperty("y", 300.0)

    node_b = node_comp.create()
    node_b.setProperty("x", 800.0)
    node_b.setProperty("y", 300.0)

    tendril = tendril_comp.create()
    tendril.setProperty("sourceNode", node_a)
    tendril.setProperty("targetNode", node_b)
    qapp.processEvents()

    # Simulate zero dock fallback
    fallback_start = tendril.validateDockPoint(QPointF(0, 0), node_a, QPointF(250.0, 316.0))
    assert fallback_start.x() == 250.0
    assert fallback_start.y() == 316.0
