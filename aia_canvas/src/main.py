#!/usr/bin/env python3
"""
Aether Interface Architecture - Presentation Layer (aia_canvas)
Entry point, Qt Scene Graph bootstrap, and observability initialization.
"""

import sys
import signal
import logging
from pathlib import Path
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QTimer

from bridge import CanvasBridge

# Allow clean Ctrl+C termination from terminal
signal.signal(signal.SIGINT, signal.SIG_DFL)

def setup_observability():
    """Configure structured stdout logging for systemd-journald."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger("aia_canvas.main")

def main():
    logger = setup_observability()
    logger.info("Initializing Aether Canvas...")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Aether Canvas")
    app.setOrganizationName("Aether")

    engine = QQmlApplicationEngine()

    bridge = CanvasBridge()
    app._bridge = bridge

    engine.rootContext().setContextProperty("canvasBridge", bridge)

    qml_file = Path(__file__).parent / "qml" / "Canvas.qml"
    engine.load(str(qml_file))

    if not engine.rootObjects():
        logger.error("Failed to load QML interface.")
        sys.exit(-1)

    logger.info("Aether Canvas UI loaded successfully. Awaiting IPC backend...")

    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(250)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()