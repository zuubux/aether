"""
QML and Controller Tests for Node Hover Drift Locking, Relative Tier Escalation, Z-Index Stacking, and Deep Horizon Dissipation.
Verifies that:
1. Mouse hover calls pin_node(node_id, true) and unpin on exit via NodeController.
2. NodeController.pin_node supports boolean pin/unpin toggles.
3. Node.qml z-index stacking follows: isSelected ? 20 : ((isPreviewMode || isHovered) ? 18 : 15).
4. Relative tier escalation steps up +1 tier on 240ms dwell, then to Tier 1.5 on sustained dwell (~1340ms total: 240ms + 1100ms intent), resetting on mouse exit:
   - Tier 4 -> Tier 3 (240ms) -> Tier 1.5 (~1340ms) -> Tier 4 (exit)
   - Tier 3 -> Tier 2 (240ms) -> Tier 1.5 (~1340ms) -> Tier 3 (exit)
   - Tier 2 -> Tier 2 hovered/pinned (240ms) -> Tier 1.5 (~1340ms) -> Tier 2 (exit)
5. Nodes at distFromCenter > 850 render as TIER_4 Star Beads / Embers when unhovered and elevate to TIER_3 on 240ms hover.
"""

import time
import pytest
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


@pytest.mark.parametrize("base_tier,expected_hover_tier", [
    ("TIER_4", "TIER_3"),
    ("TIER_3", "TIER_2"),
    ("TIER_2", "TIER_2"),
])
def test_node_qml_relative_hover_dwell_escalation(qapp, qml_engine, mock_bridge, base_tier, expected_hover_tier):
    ctx = qml_engine.rootContext()
    ctx.setContextProperty("bridge", mock_bridge)
    ctx.setContextProperty("nodeController", mock_bridge.node_ctrl)

    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"
    node_item = node_comp.create()
    assert node_item is not None

    node_item.setProperty("bridge", mock_bridge)
    node_item.setProperty("ambientTier", base_tier)
    node_item.setProperty("nodeModel", {"id": 101, "x": 1280.0, "y": 720.0, "tier": base_tier})

    mouse_area = node_item.findChild(object, "nodeMouseArea")
    assert mouse_area is not None, "MouseArea not found in Node.qml"

    # Initially isHovered should be False, currentTier == base_tier, unpinned
    assert node_item.property("isHovered") is False
    assert node_item.property("currentTier") == base_tier
    assert mock_bridge.physics_engine.pinned_node_id == 0

    # 1. Quick Pass-Through (< 240ms) -> remains base_tier, unpinned
    mouse_area.entered.emit()
    QCoreApplication.processEvents()
    assert node_item.property("isHovered") is False
    assert node_item.property("currentTier") == base_tier
    assert mock_bridge.physics_engine.pinned_node_id == 0

    # Quick exit before 240ms debounce timer fires
    mouse_area.exited.emit()
    QCoreApplication.processEvents()
    assert node_item.property("isHovered") is False
    assert node_item.property("currentTier") == base_tier
    assert mock_bridge.physics_engine.pinned_node_id == 0

    # 2. Sustained Hover Dwell (240ms) -> expected_hover_tier, pinned, isHovered = True
    mouse_area.entered.emit()
    QCoreApplication.processEvents()
    assert node_item.property("isHovered") is False

    # Wait for the 240ms hoverDwellTimer to trigger
    start_time = time.time()
    while not node_item.property("isHovered") and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert node_item.property("isHovered") is True
    assert mock_bridge.physics_engine.pinned_node_id == 101
    assert node_item.property("currentTier") == expected_hover_tier
    assert node_item.property("z") == 18

    # 3. Sustained Hover Dwell (> 1340ms total) -> escalates to Tier 1.5 preview slate (currentTier == "TIER_1_5")
    start_time = time.time()
    while node_item.property("currentTier") != "TIER_1_5" and (time.time() - start_time) < 2.5:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert node_item.property("currentTier") == "TIER_1_5"
    assert node_item.property("isPreviewMode") is True
    assert node_item.property("isHovered") is True
    assert mock_bridge.physics_engine.pinned_node_id == 101

    # 4. Exit after dwell -> collapses back to base_tier and unpins
    mouse_area.exited.emit()
    start_time = time.time()
    while mock_bridge.physics_engine.pinned_node_id != 0 and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert node_item.property("isHovered") is False
    assert node_item.property("isDwelling") is False
    assert node_item.property("currentTier") == base_tier
    assert mock_bridge.physics_engine.pinned_node_id == 0
    assert node_item.property("z") == 15


def test_node_qml_deep_horizon_dissipation_and_hover_elevation(qapp, qml_engine, mock_bridge):
    ctx = qml_engine.rootContext()
    ctx.setContextProperty("bridge", mock_bridge)
    ctx.setContextProperty("nodeController", mock_bridge.node_ctrl)

    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"
    node_item = node_comp.create()
    assert node_item is not None

    node_item.setProperty("bridge", mock_bridge)
    
    # 1. Just past horizon threshold (distFromCenter = 851px) -> currentTier = TIER_4, emberOpacity ~= 0.543
    # Default canvas center (1280, 720), so x = 1280 + 851 = 2131, y = 720
    node_item.setProperty("nodeModel", {"id": 202, "x": 2131.0, "y": 720.0, "tier": "TIER_3"})
    assert node_item.property("distFromCenter") > 850
    assert node_item.property("currentTier") == "TIER_4"
    assert abs(node_item.property("emberOpacity") - 0.543) < 0.01

    # Wait for 220ms opacity NumberAnimation Behavior to complete
    start_time = time.time()
    while abs(node_item.property("opacity") - 0.543) >= 0.01 and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert abs(node_item.property("opacity") - 0.543) < 0.01

    # 2. At distFromCenter = 1100px -> emberOpacity = 0.85 - (1100/1800)*0.65 = 0.453
    node_item.setProperty("nodeModel", {"id": 202, "x": 2380.0, "y": 720.0, "tier": "TIER_3"})
    assert abs(node_item.property("distFromCenter") - 1100.0) < 0.01
    assert abs(node_item.property("emberOpacity") - 0.453) < 0.01

    start_time = time.time()
    while abs(node_item.property("opacity") - 0.453) >= 0.01 and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert abs(node_item.property("opacity") - 0.453) < 0.01

    # 3. Far beyond horizon (distFromCenter = 2000px) -> clamped emberOpacity = 0.20
    node_item.setProperty("nodeModel", {"id": 202, "x": 3280.0, "y": 720.0, "tier": "TIER_3"})
    assert abs(node_item.property("distFromCenter") - 2000.0) < 0.01
    assert abs(node_item.property("emberOpacity") - 0.20) < 0.01

    start_time = time.time()
    while abs(node_item.property("opacity") - 0.20) >= 0.01 and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert abs(node_item.property("opacity") - 0.20) < 0.01

    mouse_area = node_item.findChild(object, "nodeMouseArea")
    assert mouse_area is not None

    # Hover over Deep Horizon ember for 240ms -> elevates immediately to TIER_3 and restores opacity to 1.0
    mouse_area.entered.emit()
    start_time = time.time()
    while not node_item.property("isHovered") and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert node_item.property("isHovered") is True
    assert node_item.property("currentTier") == "TIER_3"

    start_time = time.time()
    while abs(node_item.property("opacity") - 1.0) >= 0.01 and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert abs(node_item.property("opacity") - 1.0) < 0.01

    # Mouse exit -> collapses back to TIER_4 and attenuated opacity (0.20 at 2000px)
    mouse_area.exited.emit()
    QCoreApplication.processEvents()
    assert node_item.property("currentTier") == "TIER_4"

    start_time = time.time()
    while abs(node_item.property("opacity") - 0.20) >= 0.01 and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert abs(node_item.property("opacity") - 0.20) < 0.01


def test_aperture_20_percent_tier_4_and_hover_elevation(qapp, qml_engine, mock_bridge):
    ctx = qml_engine.rootContext()
    ctx.setContextProperty("bridge", mock_bridge)
    ctx.setContextProperty("nodeController", mock_bridge.node_ctrl)

    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"

    # 1. Central node at 20% Aperture zoom (ambientTier == "TIER_4")
    central_node = node_comp.create()
    assert central_node is not None
    central_node.setProperty("bridge", mock_bridge)
    central_node.setProperty("ambientTier", "TIER_4")
    central_node.setProperty("nodeModel", {"id": 301, "x": 1280.0, "y": 720.0, "tier": "TIER_3"})

    # 2. Outer node at 20% Aperture zoom (distFromCenter > 850px)
    outer_node = node_comp.create()
    assert outer_node is not None
    outer_node.setProperty("bridge", mock_bridge)
    outer_node.setProperty("ambientTier", "TIER_4")
    outer_node.setProperty("nodeModel", {"id": 302, "x": 2131.0, "y": 720.0, "tier": "TIER_3"})

    # Both central and outer nodes must resolve to TIER_4 (Star Beads)
    assert central_node.property("distFromCenter") == 0.0
    assert central_node.property("currentTier") == "TIER_4"

    assert outer_node.property("distFromCenter") > 850.0
    assert outer_node.property("currentTier") == "TIER_4"

    # 3. 240ms hover on central bead in 20% zoom elevates to TIER_3
    mouse_area = central_node.findChild(object, "nodeMouseArea")
    assert mouse_area is not None

    mouse_area.entered.emit()
    start_time = time.time()
    while not central_node.property("isHovered") and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert central_node.property("isHovered") is True
    assert central_node.property("currentTier") == "TIER_3"

    # Mouse exit collapses back to TIER_4
    mouse_area.exited.emit()
    QCoreApplication.processEvents()
    assert central_node.property("isHovered") is False
    assert central_node.property("currentTier") == "TIER_4"



def test_aperture_above_160_percent_high_zoom_floor(qapp, qml_engine, mock_bridge):
    """
    Verifies that when Aperture / scale > 160% (>1.6):
    - Central focal nodes (distFromCenter <= 500 * scale) evaluate to TIER_2 (Inspection Slates).
    - Outer nodes evaluate to TIER_3 (Micro-Labels floor, zero TIER_4 Star Beads).
    - Hovering an outer TIER_3 node for 240ms steps up to TIER_2.
    """
    ctx = qml_engine.rootContext()
    ctx.setContextProperty("bridge", mock_bridge)
    ctx.setContextProperty("nodeController", mock_bridge.node_ctrl)
    mock_bridge.canvas_ctrl.set_aperture(2.0)

    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"

    # 1. Central node (x: 1280.0, y: 720.0, distFromCenter == 0.0 <= 500 * 2.0 = 1000)
    central_node = node_comp.create()
    assert central_node is not None
    central_node.setProperty("bridge", mock_bridge)
    central_node.setProperty("ambientTier", "TIER_2")
    central_node.setProperty("nodeModel", {"id": 401, "x": 1280.0, "y": 720.0, "tier": "TIER_3"})

    # 2. Outer node (x: 2500.0, y: 720.0, distFromCenter == 1220.0 > 1000)
    outer_node = node_comp.create()
    assert outer_node is not None
    outer_node.setProperty("bridge", mock_bridge)
    outer_node.setProperty("ambientTier", "TIER_2")
    outer_node.setProperty("nodeModel", {"id": 402, "x": 2500.0, "y": 720.0, "tier": "TIER_3"})

    # Assertions
    assert central_node.property("distFromCenter") == 0.0
    assert central_node.property("currentTier") == "TIER_2"

    assert outer_node.property("distFromCenter") > 500.0 * outer_node.property("canvasScale")
    assert outer_node.property("currentTier") == "TIER_3"
    assert outer_node.property("currentTier") != "TIER_4"

    # Hovering outer node steps up to TIER_2 on 240ms dwell
    mouse_area = outer_node.findChild(object, "nodeMouseArea")
    assert mouse_area is not None

    mouse_area.entered.emit()
    start_time = time.time()
    while not outer_node.property("isHovered") and (time.time() - start_time) < 1.0:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert outer_node.property("isHovered") is True
    assert outer_node.property("currentTier") == "TIER_2"

    mouse_area.exited.emit()
    QCoreApplication.processEvents()
    assert outer_node.property("isHovered") is False
    assert outer_node.property("currentTier") == "TIER_3"


def test_aperture_below_40_percent_low_zoom_ceiling(qapp, qml_engine, mock_bridge):
    """
    Verifies that when Aperture / scale <= 40% (<=0.4):
    - Strict ceiling enforces TIER_4 (Star Beads) across all nodes (central and outer).
    """
    ctx = qml_engine.rootContext()
    ctx.setContextProperty("bridge", mock_bridge)
    ctx.setContextProperty("nodeController", mock_bridge.node_ctrl)
    mock_bridge.canvas_ctrl.set_aperture(0.3)

    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"

    central_node = node_comp.create()
    assert central_node is not None
    central_node.setProperty("bridge", mock_bridge)
    central_node.setProperty("ambientTier", "TIER_4")
    central_node.setProperty("nodeModel", {"id": 501, "x": 1280.0, "y": 720.0, "tier": "TIER_3"})

    outer_node = node_comp.create()
    assert outer_node is not None
    outer_node.setProperty("bridge", mock_bridge)
    outer_node.setProperty("ambientTier", "TIER_4")
    outer_node.setProperty("nodeModel", {"id": 502, "x": 2500.0, "y": 720.0, "tier": "TIER_3"})

    assert central_node.property("currentTier") == "TIER_4"
    assert outer_node.property("currentTier") == "TIER_4"


def test_aperture_100_percent_standard_radial_lod(qapp, qml_engine, mock_bridge):
    """
    Verifies standard radial LOD at Aperture @ 100% (1.0):
    - Central focal nodes evaluate to TIER_3.
    - Outer nodes (distFromCenter > 850 * scale) dissolve to TIER_4 (Bokeh Embers).
    """
    ctx = qml_engine.rootContext()
    ctx.setContextProperty("bridge", mock_bridge)
    ctx.setContextProperty("nodeController", mock_bridge.node_ctrl)
    mock_bridge.canvas_ctrl.set_aperture(1.0)

    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"

    central_node = node_comp.create()
    assert central_node is not None
    central_node.setProperty("bridge", mock_bridge)
    central_node.setProperty("ambientTier", "TIER_3")
    central_node.setProperty("nodeModel", {"id": 601, "x": 1280.0, "y": 720.0, "tier": "TIER_3"})

    outer_node = node_comp.create()
    assert outer_node is not None
    outer_node.setProperty("bridge", mock_bridge)
    outer_node.setProperty("ambientTier", "TIER_3")
    outer_node.setProperty("nodeModel", {"id": 602, "x": 2500.0, "y": 720.0, "tier": "TIER_3"})

    assert central_node.property("distFromCenter") == 0.0
    assert central_node.property("currentTier") == "TIER_3"

    assert outer_node.property("distFromCenter") > 850.0 * outer_node.property("canvasScale")
    assert outer_node.property("currentTier") == "TIER_4"
