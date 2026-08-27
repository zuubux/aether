"""
QML Component Tests for Preview Shelf, Ribbon Syncing, and NodePreview Top-Alignment.
"""

from PyQt6.QtQml import QQmlComponent, QQmlExpression, qmlContext
from models import Node


def test_spotlight_search_shelf_state_and_navigation(qapp, qml_engine, mock_bridge, canvas_qml_root):
    search_shelf = canvas_qml_root.findChild(object, "searchShelf")
    search_scrim = canvas_qml_root.findChild(object, "searchScrim")

    assert search_shelf is not None
    assert search_scrim is not None
    assert search_shelf.property("searchActive") is False
    assert search_shelf.property("focusedIndex") == 0

    # Emit search results (10 IDs)
    mock_bridge.searchResultsReceived.emit([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    qapp.processEvents()

    assert search_shelf.property("searchActive") is True

    # Check top 7 limit
    top_matches = search_shelf.property("topMatches")
    if hasattr(top_matches, "toVariant"):
        top_matches = top_matches.toVariant()
    assert len(top_matches) == 7
    assert top_matches == [1, 2, 3, 4, 5, 6, 7]

    # Test navigation (right / wrap around)
    search_shelf.navigateRight()
    qapp.processEvents()
    assert search_shelf.property("focusedIndex") == 1
    assert search_shelf.property("focusedNodeId") == 2

    search_shelf.setProperty("focusedIndex", 0)
    search_shelf.navigateLeft()
    qapp.processEvents()
    assert search_shelf.property("focusedIndex") == 6
    assert search_shelf.property("focusedNodeId") == 7

    # Clear search
    mock_bridge.search.clear_search()
    qapp.processEvents()
    assert search_shelf.property("searchActive") is False


def test_node_preview_top_alignment(qapp, qml_engine):
    preview_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/node/NodePreview.qml")
    assert preview_comp.status() == QQmlComponent.Status.Ready, f"Error: {preview_comp.errors()}"

    # CSV Node
    node_csv = Node(id=101, file_path="/workspace/data.csv", archetype="table", snippet="col1,col2\nval1,val2", size_bytes=1024)
    csv_item = preview_comp.create()
    csv_item.setProperty("nodeData", node_csv)
    qapp.processEvents()
    assert csv_item.property("fileName") == "data.csv"
    assert csv_item.property("isTabular") is True


def test_search_confirm_activates_node_preview(qapp, qml_engine, mock_bridge, canvas_qml_root):
    import time
    n1 = {"id": 1, "filePath": "/docs/guide.md", "x": 1280.0, "y": 720.0, "archetype": "document", "snippet": "User guide markdown"}

    node_comp = QQmlComponent(qml_engine, "aia_canvas/src/qml/Node.qml")
    assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml error: {node_comp.errors()}"
    node_item = node_comp.create()
    node_item.setProperty("bridge", mock_bridge)
    node_item.setProperty("nodeModel", n1)
    qapp.processEvents()

    # Initial state: unselected -> ambient tier
    assert node_item.property("isSelected") is False
    assert node_item.property("effectiveTier") == "TIER_3"

    # Confirm search / Select node -> activates TIER_1_5 (isPreviewMode = True)
    mock_bridge.node.select_node(1)
    qapp.processEvents()

    assert node_item.property("isSelected") is True
    assert node_item.property("effectiveTier") == "TIER_1_5"
    assert node_item.property("currentTier") == "TIER_1_5"

    for _ in range(25):
        time.sleep(0.02)
        qapp.processEvents()

    assert node_item.property("width") == 440
    assert node_item.property("height") == 320

    node_content = node_item.findChild(object, "nodeContent")
    assert node_content is not None
    assert node_content.property("isPreviewMode") is True
    assert node_content.property("isSlateMode") is False
    assert node_content.property("isCapsuleMode") is False



def test_modular_canvas_components(qapp, qml_engine, mock_bridge, canvas_qml_root):
    # DiagnosticsOverlay
    diag = canvas_qml_root.findChild(object, "diagnosticsOverlay")
    assert diag is not None
    assert diag.property("visible") is False
    canvas_qml_root.setProperty("showDiagnostics", True)
    assert diag.property("visible") is True
    canvas_qml_root.setProperty("showDiagnostics", False)
    assert diag.property("visible") is False

    # CanvasHud
    hud = canvas_qml_root.findChild(object, "bottomHud")
    assert hud is not None
    assert hud.property("spacing") == 12


def test_ribbon_preview_synchronization(qapp, qml_engine, mock_bridge, canvas_qml_root):
    n1 = Node(id=1, file_path="/docs/guide.md", x=100.0, y=100.0, archetype="document", snippet="User guide markdown")
    n2 = Node(id=2, file_path="/images/arch.png", x=200.0, y=200.0, archetype="image", snippet="Architecture diagram")
    mock_bridge.store.upsert_node(n1)
    mock_bridge.store.upsert_node(n2)

    omni_bar = canvas_qml_root.findChild(object, "omniBar")
    search_shelf = canvas_qml_root.findChild(object, "searchShelf")

    omni_bar.open()
    mock_bridge.searchResultsReceived.emit([1, 2])
    qapp.processEvents()

    results = [
        {"node_id": 1, "title": "User Guide", "archetype": "document", "snippet": "User guide", "path": "/docs/guide.md"},
        {"node_id": 2, "title": "Arch Diagram", "archetype": "image", "snippet": "Arch diagram", "path": "/images/arch.png"},
    ]
    omni_bar.setProperty("resultsList", results)
    omni_bar.setProperty("currentRibbonIndex", 0)
    qapp.processEvents()

    assert search_shelf.property("searchActive") is True
    assert search_shelf.property("focusedNodeId") == 1

    search_shelf.navigateRight()
    qapp.processEvents()
    assert search_shelf.property("focusedNodeId") == 2



