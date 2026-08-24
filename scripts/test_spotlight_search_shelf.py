import os
import sys
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType

sys.path.append(str(Path(__file__).parent.parent / "aia_canvas" / "src"))
from aia_intent import IntentEngine
from bridge import CanvasBridge
from content.streamer import MmapTextStreamer
from models import Node

def test_spotlight_search_shelf():
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    app = QGuiApplication(sys.argv)
    qmlRegisterType(MmapTextStreamer, "Aether.Content", 1, 0, "MmapTextStreamer")

    engine = QQmlApplicationEngine()
    bridge = CanvasBridge()
    intent_engine = IntentEngine(bridge)

    for i in range(1, 12):
        node = Node(
            id=i,
            file_path=f"/test/doc_{i}.md",
            x=100.0 * i,
            y=150.0 * i,
            archetype="document",
            snippet=f"Snippet preview for document {i}",
            size_bytes=1024 * i
        )
        bridge.store.upsert_node(node)

    engine.rootContext().setContextProperty("canvasBridge", bridge)
    engine.rootContext().setContextProperty("canvasController", bridge.canvas_ctrl)
    engine.rootContext().setContextProperty("nodeController", bridge.node_ctrl)
    engine.rootContext().setContextProperty("physicsController", bridge.physics_ctrl)
    engine.rootContext().setContextProperty("searchController", bridge.search_ctrl)
    engine.rootContext().setContextProperty("intentEngine", intent_engine)
    engine.rootContext().setContextProperty("targetScreenIdx", 0)
    engine.rootContext().setContextProperty("isFullscreen", False)
    engine.rootContext().setContextProperty("isSpanAll", False)

    qml_file = Path(__file__).parent.parent / "aia_canvas" / "src" / "qml" / "Canvas.qml"
    engine.load(str(qml_file))

    assert len(engine.rootObjects()) > 0, "Failed to load Canvas.qml"
    root = engine.rootObjects()[0]

    print("[TEST 1] Verifying SearchShelf properties and initial state...")
    search_shelf = root.findChild(object, "searchShelf")
    assert search_shelf is not None, "searchShelf not found in QML hierarchy"
    assert search_shelf.property("searchActive") is False
    assert search_shelf.property("focusedIndex") == 0
    top_matches = search_shelf.property("topMatches")
    if hasattr(top_matches, "toVariant"):
        top_matches = top_matches.toVariant()
    assert len(top_matches) == 0

    print("[TEST 2] Verifying search results reception & top 7 ranking limit...")
    bridge.searchResultsReceived.emit([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    app.processEvents()

    assert search_shelf.property("searchActive") is True
    res_ids = search_shelf.property("searchResultIds")
    if hasattr(res_ids, "toVariant"):
        res_ids = res_ids.toVariant()
    assert len(res_ids) == 10
    top_matches = search_shelf.property("topMatches")
    if hasattr(top_matches, "toVariant"):
        top_matches = top_matches.toVariant()
    assert len(top_matches) == 7, f"Expected topMatches length 7, got {len(top_matches)}"
    assert top_matches == [1, 2, 3, 4, 5, 6, 7]
    assert search_shelf.property("focusedIndex") == 0
    assert search_shelf.property("focusedNodeId") == 1

    print("[TEST 3] Verifying Keyboard Traversal (Left/Right navigation)...")
    search_shelf.navigateRight()
    app.processEvents()
    assert search_shelf.property("focusedIndex") == 1
    assert search_shelf.property("focusedNodeId") == 2

    # Wrap around left
    search_shelf.setProperty("focusedIndex", 0)
    search_shelf.navigateLeft()
    app.processEvents()
    assert search_shelf.property("focusedIndex") == 6
    assert search_shelf.property("focusedNodeId") == 7

    # Wrap around right
    search_shelf.navigateRight()
    app.processEvents()
    assert search_shelf.property("focusedIndex") == 0
    assert search_shelf.property("focusedNodeId") == 1

    print("[TEST 4] Verifying bridge.focus_node and Selection on Enter...")
    assert hasattr(bridge, "focus_node"), "bridge missing focus_node slot"
    search_shelf.setProperty("focusedIndex", 2) # Node 3
    search_shelf.selectFocusedNode()
    app.processEvents()
    assert bridge.selectedNodeId == 3
    assert search_shelf.property("searchActive") is False

    print("[TEST 5] Verifying searchScrim dimming overlay...")
    search_scrim = root.findChild(object, "searchScrim")
    assert search_scrim is not None, "searchScrim not found in QML hierarchy"
    bridge.searchResultsReceived.emit([2, 4, 6])
    import time
    for _ in range(5):
        time.sleep(0.05)
        app.processEvents()
    assert search_shelf.property("searchActive") is True
    assert search_scrim.property("opacity") > 0.0

    print("[TEST 6] Verifying Search Clear lifecycle...")
    bridge.clear_search()
    app.processEvents()
    assert search_shelf.property("searchActive") is False

    print("ALL SPOTLIGHT SEARCH SHELF TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_spotlight_search_shelf()
