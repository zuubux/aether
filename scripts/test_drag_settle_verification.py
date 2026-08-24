import sys
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QCoreApplication
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, QQmlComponent, qmlRegisterType

sys.path.append(str(Path("aia_canvas/src").resolve()))
from content.streamer import MmapTextStreamer
from bridge import CanvasBridge
from aia_intent import IntentEngine

app = QGuiApplication(sys.argv)
qmlRegisterType(MmapTextStreamer, "Aether.Content", 1, 0, "MmapTextStreamer")

engine = QQmlApplicationEngine()
bridge = CanvasBridge()
app._bridge = bridge

engine.rootContext().setContextProperty("canvasBridge", bridge)
engine.rootContext().setContextProperty("canvasController", bridge.canvas_ctrl)
engine.rootContext().setContextProperty("nodeController", bridge.node_ctrl)
engine.rootContext().setContextProperty("physicsController", bridge.physics_ctrl)
engine.rootContext().setContextProperty("searchController", bridge.search_ctrl)

intent_engine = IntentEngine(bridge)
engine.rootContext().setContextProperty("intentEngine", intent_engine)
engine.rootContext().setContextProperty("targetScreenIdx", 0)
engine.rootContext().setContextProperty("isFullscreen", False)
engine.rootContext().setContextProperty("isSpanAll", False)

engine.addImportPath("aia_canvas/src/qml")

# Test 1: Load Canvas.qml
qml_file = Path("aia_canvas/src/qml/Canvas.qml").resolve()
warnings = []
engine.warnings.connect(lambda w: warnings.extend(w))
engine.load(str(qml_file))
root_objects = engine.rootObjects()
if not root_objects:
    print("QML Engine Errors:")
    for w in warnings:
        print(" -", w.toString())
assert len(root_objects) > 0, "Failed to load Canvas.qml"
print("PASS 1: Canvas.qml loaded successfully")

# Test 2: Instantiate Node.qml and test drag & settle tier escalation
node_comp = QQmlComponent(engine, "aia_canvas/src/qml/Node.qml")
assert node_comp.status() == QQmlComponent.Status.Ready, f"Node.qml component error: {node_comp.errors()}"
node_item = node_comp.create()
assert node_item is not None, "Failed to create Node item"

# Verify initial ambient tier 4
node_item.setProperty("ambientTier", "TIER_4")
eff_tier = node_item.property("effectiveTier")
assert eff_tier == "TIER_4", f"Expected TIER_4, got {eff_tier}"
z_val = node_item.property("z")
assert z_val == 10, f"Expected z=10, got {z_val}"

# Test drag active -> Tier 3 for Tier 4 bead
node_item.setProperty("isDragging", True)
eff_tier = node_item.property("effectiveTier")
assert eff_tier == "TIER_3", f"Expected TIER_3 during drag, got {eff_tier}"
z_val = node_item.property("z")
assert z_val == 1000, f"Expected z=1000 during drag, got {z_val}"

# Test settle active -> Tier 3 for Tier 4 bead
node_item.setProperty("isDragging", False)
node_item.setProperty("isSettling", True)
eff_tier = node_item.property("effectiveTier")
assert eff_tier == "TIER_3", f"Expected TIER_3 during settle, got {eff_tier}"
z_val = node_item.property("z")
assert z_val == 500, f"Expected z=500 during settle, got {z_val}"

# Test ambient Tier 3 during drag -> Tier 2
node_item.setProperty("ambientTier", "TIER_3")
node_item.setProperty("isDragging", True)
node_item.setProperty("isSettling", False)
eff_tier = node_item.property("effectiveTier")
assert eff_tier == "TIER_2", f"Expected TIER_2 during drag for Tier 3, got {eff_tier}"

# Test ambient Tier 3 during settle -> Tier 2
node_item.setProperty("isDragging", False)
node_item.setProperty("isSettling", True)
eff_tier = node_item.property("effectiveTier")
assert eff_tier == "TIER_2", f"Expected TIER_2 during settle for Tier 3, got {eff_tier}"
z_val = node_item.property("z")
assert z_val == 500, f"Expected z=500 during settle, got {z_val}"

# Test settle finishes -> falls back to ambientTier TIER_3
node_item.setProperty("isSettling", False)
eff_tier = node_item.property("effectiveTier")
assert eff_tier == "TIER_3", f"Expected TIER_3 after settle, got {eff_tier}"
z_val = node_item.property("z")
assert z_val == 10, f"Expected z=10 at rest, got {z_val}"

print("PASS 2: Tier escalation, effectiveTier, and Z-Index verified")

# Test 3: SurfaceShell border color and width
shell_comp = QQmlComponent(engine)
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
""", engine.baseUrl())
test_item = shell_comp.create()
assert test_item is not None, f"Failed to create test item: {shell_comp.errors()}"
shell_inst = test_item.property("shell")

# At rest
assert shell_inst.property("isDragging") == False
assert shell_inst.property("isSettling") == False
assert shell_inst.property("isHovered") == False
assert test_item.property("bgBorderWidth") == 1
assert test_item.property("bgBorderColor").name().lower() == "#1e2430"

# Dragging
shell_inst.setProperty("isDragging", True)
assert test_item.property("bgBorderWidth") == 2, f"Expected 2, got {test_item.property('bgBorderWidth')}"
# Advance event loop for 500ms to let ColorAnimation complete
import time
start = time.time()
while time.time() - start < 0.5:
    QCoreApplication.processEvents()
    time.sleep(0.01)

assert test_item.property("bgBorderColor").name().lower() == "#00f2fe", f"Expected #00f2fe, got {test_item.property('bgBorderColor').name()}"
print("PASS 3: Border luminosity boost (color & width 2) verified for dragging")

# Settling
shell_inst.setProperty("isDragging", False)
shell_inst.setProperty("isSettling", True)
assert test_item.property("bgBorderWidth") == 2, f"Expected 2, got {test_item.property('bgBorderWidth')}"
start = time.time()
while time.time() - start < 0.5:
    QCoreApplication.processEvents()
    time.sleep(0.01)
assert test_item.property("bgBorderColor").name().lower() == "#00f2fe", f"Expected #00f2fe, got {test_item.property('bgBorderColor').name()}"
print("PASS 3b: Border luminosity boost (color & width 2) verified for settling")

# Hovered
shell_inst.setProperty("isDragging", False)
shell_inst.setProperty("isSettling", False)
shell_inst.setProperty("isHovered", True)
assert test_item.property("bgBorderWidth") == 1, f"Expected 1, got {test_item.property('bgBorderWidth')}"
start = time.time()
while time.time() - start < 0.5:
    QCoreApplication.processEvents()
    time.sleep(0.01)
assert test_item.property("bgBorderColor").name().lower() == "#38bdf8", f"Expected #38bdf8, got {test_item.property('bgBorderColor').name()}"
print("PASS 4: Border hover verified")

# Test 4: updateNodePosition slot verification on CanvasBridge and NodeController
assert hasattr(bridge, "updateNodePosition"), "CanvasBridge missing updateNodePosition slot"
assert hasattr(bridge.node_ctrl, "updateNodePosition"), "NodeController missing updateNodePosition slot"
bridge.updateNodePosition(1, 100.0, 200.0)
print("PASS 5: updateNodePosition bridge slot callable and operational")

print("ALL TEST CHECKS PASSED SUCCESSFULLY!")
