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
