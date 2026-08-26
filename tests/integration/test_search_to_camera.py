"""
Integration Test: Search Query -> Ribbon Selection -> Camera Target Steering -> HUD Dismissal.
"""

import time
from PyQt6.QtCore import QMetaObject
from models import Node


def test_search_to_camera_steering_and_preview(qapp, qml_engine, mock_bridge, canvas_qml_root):
    # Seed nodes
    n1 = Node(id=1, file_path="/test/report.pdf", x=1280.0, y=720.0, archetype="document", size_bytes=2048)
    n2 = Node(id=2, file_path="/test/bracket_mount.step", x=4000.0, y=4000.0, archetype="model", size_bytes=8192)

    mock_bridge.store.upsert_node(n1)
    mock_bridge.store.upsert_node(n2)
    mock_bridge.nodesChanged.emit()

    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    search_shelf = canvas_qml_root.findChild(object, "searchShelf")
    canvas_viewport = canvas_qml_root.findChild(object, "canvasViewport")

    assert omni_bar is not None
    assert search_shelf is not None
    assert canvas_viewport is not None

    initial_tx = canvas_viewport.property("targetX")
    initial_ty = canvas_viewport.property("targetY")
    initial_n2_x = n2.x
    initial_n2_y = n2.y

    # 1. Open OmniBar and input text 'brack'
    omni_bar.open()
    qapp.processEvents()
    input_field = omni_bar.findChild(object, "inputField")
    input_field.setProperty("focus", True)
    input_field.setProperty("text", "brack")
    qapp.processEvents()

    results = [
        {"id": "2", "node_id": "2", "title": "bracket_mount.step", "archetype": "model", "path": "/test/bracket_mount.step"},
    ]
    omni_bar.setProperty("resultsList", results)
    omni_bar.setProperty("currentRibbonIndex", 0)
    qapp.processEvents()

    # 2. Select result (Enter action)
    QMetaObject.invokeMethod(omni_bar, "selectCurrentRibbonItem")

    for _ in range(12):
        time.sleep(0.02)
        qapp.processEvents()

    # 3. Assertions:
    # a. OmniBar input capsule is dismissed (opacity -> 0.0, active -> False)
    assert not omni_bar.property("active")
    assert omni_bar.property("opacity") == 0.0

    # b. Node 2 is selected in bridge
    assert mock_bridge.selectedNodeId == 2

    # c. SearchShelf preview card is fully dismissed post-confirmation (opacity -> 0.0, searchActive -> False)
    assert search_shelf.property("opacity") == 0.0
    assert search_shelf.property("searchActive") is False

    # d. Target node graph coordinates remain strictly stationary
    assert abs(n2.x - initial_n2_x) < 5.0
    assert abs(n2.y - initial_n2_y) < 5.0

    # e. Canvas viewport camera target steered to node 2 coordinates
    steered_tx = canvas_viewport.property("targetX")
    steered_ty = canvas_viewport.property("targetY")
    assert steered_tx != initial_tx
    assert steered_ty != initial_ty
    assert abs(steered_tx - (-2720.0)) < 100.0
    assert abs(steered_ty - (-3280.0)) < 100.0

    # f. Viewport root translation (x, y) updates to match camera target
    assert canvas_viewport.property("x") == steered_tx
    assert canvas_viewport.property("y") == steered_ty

    # 4. Deselect node 0 to reset state
    mock_bridge.node.select_node(0)

    for _ in range(12):
        time.sleep(0.02)
        qapp.processEvents()

    assert mock_bridge.selectedNodeId == 0
    assert search_shelf.property("opacity") == 0.0
