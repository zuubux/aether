#!/usr/bin/env python3
"""
Aether Interface Architecture - Presentation Layer (aia_canvas)
Entry point, Qt Scene Graph bootstrap, and observability initialization.
"""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

from aia_intent import IntentEngine
from bridge import CanvasBridge
from content.streamer import MmapTextStreamer
from PyQt6.QtCore import QCoreApplication, QLibraryInfo, QTimer
from PyQt6.QtGui import QGuiApplication, QSurfaceFormat
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType


def setup_observability(debug=False):
    """Configure structured stdout logging for systemd-journald."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger("aia_canvas.main")

def main():
    parser = argparse.ArgumentParser(description="Aether Canvas")
    parser.add_argument("--fullscreen", "--full-screen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--span-all", action="store_true", help="Span across all connected displays")
    parser.add_argument("--screen", type=int, default=0, help="Target display index")
    parser.add_argument("--width", type=int, default=1920, help="Window width")
    parser.add_argument("--height", type=int, default=1080, help="Window height")
    parser.add_argument("-v", "--debug", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("--watch-dir", type=str, help="Directory to index/watch")
    parser.add_argument("--diagnostics", nargs="?", const=3, type=int, help="Run a timed telemetry capture for N seconds, print to stdout and exit.")
    
    # Parse known args so Qt can still parse its own if needed
    args, unparsed_args = parser.parse_known_args()

    logger = setup_observability(args.debug)
    logger.info("Initializing Aether Canvas...")

    # Set 4x hardware MSAA and enable vsync matching your high refresh rate
    surface_format = QSurfaceFormat()
    surface_format.setSamples(4)
    surface_format.setSwapInterval(1)
    QSurfaceFormat.setDefaultFormat(surface_format)

    # Set global Qt Quick Controls style to Basic to bypass KDE Breeze coercion warnings
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

    # Ensure Qt imageformats plugins are registered
    plugin_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
    QCoreApplication.addLibraryPath(plugin_path)

    system_plugin_candidates = [
        "/usr/lib64/qt6/plugins",
        "/usr/lib/qt6/plugins",
        "/usr/lib/x86_64-linux-gnu/qt6/plugins"
    ]
    for path in system_plugin_candidates:
        if os.path.isdir(path):
            QCoreApplication.addLibraryPath(path)

    # Instantiate QGuiApplication exactly once
    sys.argv = [sys.argv[0]] + unparsed_args
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Aether Canvas")
    app.setOrganizationName("Aether")

    # Allow clean Ctrl+C termination from terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    qmlRegisterType(MmapTextStreamer, "Aether.Content", 1, 0, "MmapTextStreamer")

    engine = QQmlApplicationEngine()

    bridge = CanvasBridge()
    bridge.physics_ctrl.start()
    app._bridge = bridge

    engine.rootContext().setContextProperty("canvasBridge", bridge)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.rootContext().setContextProperty("canvasController", bridge.canvas_ctrl)
    engine.rootContext().setContextProperty("nodeController", bridge.node_ctrl)
    engine.rootContext().setContextProperty("physicsController", bridge.physics_ctrl)
    engine.rootContext().setContextProperty("searchController", bridge.search_ctrl)

    intent_engine = IntentEngine(bridge)
    # Forward the nodesSummoned signal from intent_engine to the physics controller
    intent_engine.nodesSummoned.connect(bridge.physics_ctrl.summon_nodes)
    engine.rootContext().setContextProperty("intentEngine", intent_engine)

    screens = app.screens()
    screen_idx = args.screen if 0 <= args.screen < len(screens) else 0
    engine.rootContext().setContextProperty("targetScreenIdx", screen_idx)
    engine.rootContext().setContextProperty("isFullscreen", args.fullscreen)
    engine.rootContext().setContextProperty("isSpanAll", args.span_all)
    
    qml_file = Path(__file__).parent / "qml" / "Canvas.qml"
    engine.load(str(qml_file))

    if not engine.rootObjects():
        logger.error("Failed to load QML interface.")
        sys.exit(-1)

    window = engine.rootObjects()[0]
    
    # Wayland requires screen to be set before showing, but QML handles it via bindings now.
    # We still need to handle span_all explicitly if requested, though Wayland compositor 
    # typically controls span-all placement natively.
    if args.span_all and screens:
        total_rect = screens[0].geometry()
        for s in screens[1:]:
            total_rect = total_rect.united(s.geometry())
        window.setGeometry(total_rect)

    if not args.fullscreen and not args.span_all:
        target_screen = screens[screen_idx]
        geo = target_screen.geometry()
        window.setGeometry(geo.x() + 100, geo.y() + 100, args.width, args.height)

    # Trigger show based on parsed properties (since QML visibility bindings handle the initial map)
    if args.fullscreen or args.span_all:
        window.showFullScreen()
    else:
        window.show()

    logger.info("Aether Canvas UI loaded successfully. Awaiting IPC backend...")

    if args.diagnostics is not None:
        def print_and_exit():
            import json
            snap = bridge.get_telemetry_snapshot()
            print("\n=== SRE TELEMETRY DIAGNOSTICS ===")
            print(json.dumps(snap, indent=2))
            print("=================================\n")
            QCoreApplication.quit()
        QTimer.singleShot(args.diagnostics * 1000, print_and_exit)

    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(250)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()