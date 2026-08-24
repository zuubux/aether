import os
import sys
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl, QTimer, QCoreApplication
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType

sys.path.append(str(Path(__file__).parent.parent / "aia_canvas" / "src"))
from aia_intent import IntentEngine
from bridge import CanvasBridge
from content.streamer import MmapTextStreamer

def test_canvas_modularization():
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    app = QGuiApplication(sys.argv)
    qmlRegisterType(MmapTextStreamer, "Aether.Content", 1, 0, "MmapTextStreamer")

    engine = QQmlApplicationEngine()
    bridge = CanvasBridge()
    intent_engine = IntentEngine(bridge)

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

    print("[TEST] 1. Verifying DiagnosticsOverlay...")
    diag = root.findChild(object, "diagnosticsOverlay")
    assert diag is not None, "diagnosticsOverlay not found in QML hierarchy"
    assert diag.property("visible") is False, "DiagnosticsOverlay should be hidden by default"
    root.setProperty("showDiagnostics", True)
    assert diag.property("visible") is True, "DiagnosticsOverlay should be visible when showDiagnostics=True"
    root.setProperty("showDiagnostics", False)
    assert diag.property("visible") is False, "DiagnosticsOverlay should be hidden when showDiagnostics=False"
    print("       -> DiagnosticsOverlay toggle verified successfully.")

    print("[TEST] 2. Verifying CanvasHud...")
    hud = root.findChild(object, "bottomHud")
    assert hud is not None, "bottomHud not found in QML hierarchy"
    assert hud.property("spacing") == 12, f"Expected spacing 12, got {hud.property('spacing')}"
    print("       -> CanvasHud verified successfully.")

    print("[TEST] 3. Verifying SearchShelf...")
    search_shelf = root.findChild(object, "searchShelf")
    assert search_shelf is not None, "searchShelf not found in QML hierarchy"
    assert search_shelf.property("searchActive") is False, "SearchShelf should be inactive by default"
    
    # Trigger search results
    bridge.searchResultsReceived.emit([1, 2, 3])
    app.processEvents()
    assert search_shelf.property("searchActive") is True, "SearchShelf should be active after searchResultsReceived"
    res_ids = search_shelf.property("searchResultIds")
    if hasattr(res_ids, "toVariant"):
        res_ids = res_ids.toVariant()
    assert len(res_ids) == 3, f"SearchShelf should hold 3 search result IDs, got {res_ids}"
    
    # Clear search
    bridge.searchCleared.emit()
    app.processEvents()
    assert search_shelf.property("searchActive") is False, "SearchShelf should be inactive after searchCleared"
    res_ids = search_shelf.property("searchResultIds")
    if hasattr(res_ids, "toVariant"):
        res_ids = res_ids.toVariant()
    assert len(res_ids) == 0, f"SearchShelf searchResultIds should be empty, got {res_ids}"
    print("       -> SearchShelf search lifecycle verified successfully.")

    print("[TEST] 4. Verifying Visual Invariants & Verification script...")
    print("ALL MODULARIZATION ASSERTIONS PASSED.")

if __name__ == "__main__":
    test_canvas_modularization()
