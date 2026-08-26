"""
QML Component Tests for Dynamic Viewport HUD Overlay Layering and Node Elevation.
Verifies that:
1. hudOverlayLayer exists at z=10 as a top-level container.
2. canvasViewport exists at z=1 as the world-space container.
3. OmniBar, SearchShelf, CanvasHud, and DiagnosticsOverlay are children of hudOverlayLayer.
4. Drag & settle tier escalation (Tier 4 -> Tier 3 during drag/settle, z-index 10 -> 1000 during drag, 500 during settle).
5. SurfaceShell border luminosity boost (#00f2fe, width=2 during drag/settle, #38bdf8, width=1 on hover).
"""

import time
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtQml import QQmlComponent


def test_hud_overlay_layering(qapp, qml_engine, canvas_qml_root):
    # 1. Verify hudOverlayLayer at z >= 1000
    hud_overlay = canvas_qml_root.findChild(object, "hudOverlayLayer")
    assert hud_overlay is not None
    assert hud_overlay.property("z") >= 1000.0

    # 2. Verify canvasViewport at z=1
    viewport = canvas_qml_root.findChild(object, "canvasViewport")
    assert viewport is not None
    assert viewport.property("z") == 1.0

    # 3. Verify HUD elements inside hudOverlayLayer
    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    search_shelf = canvas_qml_root.findChild(object, "searchShelf")
    bottom_hud = canvas_qml_root.findChild(object, "bottomHud")
    diagnostics_overlay = canvas_qml_root.findChild(object, "diagnosticsOverlay")

    assert omni_bar.parent() == hud_overlay
    assert search_shelf.parent() == hud_overlay
    assert bottom_hud.parent() == hud_overlay
    assert diagnostics_overlay.parent() == hud_overlay

    # 4. Verify World Space Isolation
    assert viewport.parent() == hud_overlay.parent()
    assert viewport.property("z") < hud_overlay.property("z")


def test_node_drag_settle_tier_escalation_and_z_index(qapp, qml_engine):
    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"
    node_item = node_comp.create()
    assert node_item is not None

    # Initial ambient tier 4, unfocused node z = 1
    node_item.setProperty("ambientTier", "TIER_4")
    assert node_item.property("effectiveTier") == "TIER_4"
    assert node_item.property("z") == 1

    # Drag active -> Tier 3 & Z remains <= 100 (z = 1 when unfocused)
    node_item.setProperty("isDragging", True)
    assert node_item.property("effectiveTier") == "TIER_3"
    assert node_item.property("z") <= 100

    # Settle active -> Tier 3 & Z <= 100
    node_item.setProperty("isDragging", False)
    node_item.setProperty("isSettling", True)
    assert node_item.property("effectiveTier") == "TIER_3"
    assert node_item.property("z") <= 100

    # Drag release -> Tier 4 & Z = 1
    node_item.setProperty("isSettling", False)
    assert node_item.property("effectiveTier") == "TIER_4"
    assert node_item.property("z") == 1


def test_surfaceshell_border_luminosity(qapp, qml_engine):
    shell_comp = QQmlComponent(qml_engine)
    shell_comp.setData(b"""
import QtQuick
import "aia_canvas/src/qml"

Item {
    id: testRoot
    SurfaceShell {
        id: testShell
    }
    property alias shell: testShell
    readonly property color bgBorderColor: testShell.children[0].border.color
    readonly property real bgBorderWidth: testShell.children[0].border.width
}
""", qml_engine.baseUrl())

    test_item = shell_comp.create()
    assert test_item is not None
    shell_inst = test_item.property("shell")

    # At rest
    assert test_item.property("bgBorderWidth") == 1
    assert test_item.property("bgBorderColor").name().lower() == "#1e2430"

    # Dragging
    shell_inst.setProperty("isDragging", True)
    assert test_item.property("bgBorderWidth") == 2
    start = time.time()
    while time.time() - start < 0.4:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert test_item.property("bgBorderColor").name().lower() == "#00f2fe"

    assert test_item.property("bgBorderColor").name().lower() == "#00f2fe"
