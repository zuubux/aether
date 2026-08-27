import os
import sys
from pathlib import Path
import pytest

# Add source paths to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CANVAS_SRC = PROJECT_ROOT / "aia_canvas" / "src"
WEAVER_SRC = PROJECT_ROOT / "aia_weaver" / "src"

if str(CANVAS_SRC) not in sys.path:
    sys.path.insert(0, str(CANVAS_SRC))
if str(WEAVER_SRC) not in sys.path:
    sys.path.insert(0, str(WEAVER_SRC))

# Configure headless Qt environment
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType

from bridge import CanvasBridge
from content.streamer import MmapTextStreamer
from aia_intent import IntentEngine
from controllers.conversation_controller import ConversationController


@pytest.fixture(scope="session")
def qapp():
    """Single global QGuiApplication instance for headless tests."""
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    qmlRegisterType(MmapTextStreamer, "Aether.Content", 1, 0, "MmapTextStreamer")
    yield app


@pytest.fixture
def qml_engine(qapp):
    """Provides a fresh QQmlApplicationEngine configured with canvas QML import paths."""
    engine = QQmlApplicationEngine()
    qml_dir = CANVAS_SRC / "qml"
    engine.addImportPath(str(qml_dir))
    yield engine
    # Cleanup root objects
    for obj in engine.rootObjects():
        obj.deleteLater()
    qapp.processEvents()


@pytest.fixture
def mock_bridge(qapp, monkeypatch):
    """Provides a fresh CanvasBridge instance with cleanup on teardown."""
    monkeypatch.setattr(ConversationController, "stream_prompt", lambda *args, **kwargs: None)
    bridge = CanvasBridge()
    yield bridge
    if hasattr(bridge, "_physics_timer") and bridge._physics_timer:
        bridge._physics_timer.stop()
    if hasattr(bridge, "physics_ctrl") and bridge.physics_ctrl:
        bridge.physics_ctrl.stop()
    if hasattr(bridge, "_telemetry_timer") and bridge._telemetry_timer:
        bridge._telemetry_timer.stop()
    if hasattr(bridge, "conversation_ctrl") and bridge.conversation_ctrl:
        bridge.conversation_ctrl.stop()
    if hasattr(bridge, "weaver_client") and bridge.weaver_client:
        bridge.weaver_client._running = False
    qapp.processEvents()


@pytest.fixture
def mock_search_controller(mock_bridge):
    """Provides the SearchController from mock_bridge."""
    return mock_bridge.search_ctrl


@pytest.fixture
def canvas_qml_root(qapp, qml_engine, mock_bridge):
    """Loads Canvas.qml with all standard context properties set."""
    intent_engine = IntentEngine(mock_bridge)
    ctx = qml_engine.rootContext()
    ctx.setContextProperty("canvasBridge", mock_bridge)
    ctx.setContextProperty("bridge", mock_bridge)
    ctx.setContextProperty("canvasController", mock_bridge.canvas_ctrl)
    ctx.setContextProperty("nodeController", mock_bridge.node_ctrl)
    ctx.setContextProperty("physicsController", mock_bridge.physics_ctrl)
    ctx.setContextProperty("searchController", mock_bridge.search_ctrl)
    ctx.setContextProperty("intentEngine", intent_engine)
    ctx.setContextProperty("targetScreenIdx", 0)
    ctx.setContextProperty("isFullscreen", False)
    ctx.setContextProperty("isSpanAll", False)

    qml_file = CANVAS_SRC / "qml" / "Canvas.qml"
    qml_engine.load(str(qml_file))

    assert len(qml_engine.rootObjects()) > 0, "Failed to load Canvas.qml"
    root = qml_engine.rootObjects()[0]
    qapp.processEvents()
    return root

