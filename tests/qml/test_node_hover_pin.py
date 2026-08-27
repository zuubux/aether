"""
QML and Controller Tests for Node Hover Drift Locking and Z-Index Stacking.
Verifies that:
1. Mouse hover calls pin_node(node_id, true) and unpin on exit via NodeController.
2. NodeController.pin_node supports boolean pin/unpin toggles.
3. Node.qml z-index stacking follows: isSelected ? 20 : ((isPreviewMode || isHovered) ? 18 : 15).
"""

import time
from PyQt6.QtQml import QQmlComponent
from PyQt6.QtCore import QCoreApplication
from controllers.node_controller import NodeController


def test_node_controller_boolean_pin_slot(qapp, mock_bridge):
    node_ctrl = NodeController(mock_bridge)
    
    # Pin node 42
    node_ctrl.pin_node(42, True)
    start = time.time()
    while mock_bridge.physics_engine.pinned_node_id != 42 and time.time() - start < 1.0:
        qapp.processEvents()
        time.sleep(0.01)
    assert mock_bridge.physics_engine.pinned_node_id == 42

    # Unpin node 42
    node_ctrl.pin_node(42, False)
    start = time.time()
    while mock_bridge.physics_engine.pinned_node_id != 0 and time.time() - start < 1.0:
        qapp.processEvents()
        time.sleep(0.01)
    assert mock_bridge.physics_engine.pinned_node_id == 0


def test_node_qml_hover_preview_z_index_stacking(qapp, qml_engine):
    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"
    node_item = node_comp.create()
    assert node_item is not None

    # Default ambient state -> z = 15
    assert node_item.property("z") == 15

    # Hovered state -> z = 18
    node_item.setProperty("isHovered", True)
    assert node_item.property("z") == 18
    node_item.setProperty("isHovered", False)
    assert node_item.property("z") == 15

    # Dwelling / Tier 1.5 preview state -> z = 18
    node_item.setProperty("isDwelling", True)
    assert node_item.property("effectiveTier") == "TIER_1_5"
    assert node_item.property("isPreviewMode") is True
    assert node_item.property("z") == 18
    node_item.setProperty("isDwelling", False)

    # Selected / focused state -> z = 20
    node_item.setProperty("isSelected", True)
    assert node_item.property("z") == 20


def test_node_qml_hover_dwell_debounce(qapp, qml_engine, mock_bridge):
    ctx = qml_engine.rootContext()
    ctx.setContextProperty("bridge", mock_bridge)
    ctx.setContextProperty("nodeController", mock_bridge.node_ctrl)

    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"
    node_item = node_comp.create()
    assert node_item is not None

    node_item.setProperty("bridge", mock_bridge)
    node_item.setProperty("nodeModel", {"id": 101, "x": 100.0, "y": 200.0})

    mouse_area = node_item.findChild(object, "nodeMouseArea")
    assert mouse_area is not None, "MouseArea not found in Node.qml"

    # Initially isHovered should be False
    assert node_item.property("isHovered") is False
    assert mock_bridge.physics_engine.pinned_node_id == 0

    # 1. Quick Pass-Through (< 140ms)
    mouse_area.entered.emit()
    QCoreApplication.processEvents()
    # Immediately after onEntered, isHovered remains False and node is NOT pinned
    assert node_item.property("isHovered") is False
    assert mock_bridge.physics_engine.pinned_node_id == 0

    # Quick exit before 140ms debounce timer fires
    mouse_area.exited.emit()
    QCoreApplication.processEvents()
    assert node_item.property("isHovered") is False
    assert mock_bridge.physics_engine.pinned_node_id == 0

    # 2. Sustained Hover Dwell (> 140ms)
    mouse_area.entered.emit()
    QCoreApplication.processEvents()
    assert node_item.property("isHovered") is False

    # Wait for the 140ms hoverDwellTimer to trigger
    start_time = time.time()
    while not node_item.property("isHovered") and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert node_item.property("isHovered") is True
    assert mock_bridge.physics_engine.pinned_node_id == 101
    assert node_item.property("z") == 18

    # Exit after dwell
    mouse_area.exited.emit()
    start_time = time.time()
    while mock_bridge.physics_engine.pinned_node_id != 0 and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert node_item.property("isHovered") is False
    assert mock_bridge.physics_engine.pinned_node_id == 0
    assert node_item.property("z") == 15
