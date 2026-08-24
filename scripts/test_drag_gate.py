import sys
from pathlib import Path
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, QQmlComponent, qmlRegisterType

sys.path.append(str(Path("aia_canvas/src").resolve()))
from content.streamer import MmapTextStreamer
from bridge import CanvasBridge

app = QGuiApplication(sys.argv)
qmlRegisterType(MmapTextStreamer, "Aether.Content", 1, 0, "MmapTextStreamer")

engine = QQmlApplicationEngine()
bridge = CanvasBridge()
engine.rootContext().setContextProperty("canvasBridge", bridge)
engine.addImportPath("aia_canvas/src/qml")

test_comp = QQmlComponent(engine)
test_comp.setData(b"""
import QtQuick
import "aia_canvas/src/qml"

Item {
    id: testRoot
    Node {
        id: testNode
    }
    property alias node: testNode
    readonly property bool isCenter: testNode.transformOrigin === Item.Center
}
""", engine.baseUrl())
test_item = test_comp.create()
assert test_item is not None, f"Failed to create test item: {test_comp.errors()}"
node_item = test_item.property("node")

# Test 1: transformOrigin is Center
assert test_item.property("isCenter") == True, "Expected transformOrigin === Item.Center"
print("CHECK 1: rootItem transformOrigin is Center")

# Test 2: x / y binding behavior
test_model = {"id": 42, "x": 150.0, "y": 250.0, "fileName": "test.txt"}
node_item.setProperty("nodeModel", test_model)
x_val = node_item.property("x")
y_val = node_item.property("y")
assert x_val == 150.0, f"Expected 150.0, got {x_val}"
assert y_val == 250.0, f"Expected 250.0, got {y_val}"
print("CHECK 2: Initial x, y declarative bindings active")

# Simulate dragging
node_item.setProperty("isDragging", True)
node_item.setProperty("x", 500.0)
node_item.setProperty("y", 600.0)

# Update model while dragging
test_model_updated = {"id": 42, "x": 999.0, "y": 888.0, "fileName": "test.txt"}
node_item.setProperty("nodeModel", test_model_updated)

# x/y should NOT jump to model position during drag
x_drag = node_item.property("x")
y_drag = node_item.property("y")
assert x_drag == 500.0, f"Expected 500.0 during drag, got {x_drag}"
assert y_drag == 600.0, f"Expected 600.0 during drag, got {y_drag}"
print("CHECK 3: Model coordinate updates ignored when isDragging is True")

# Stop dragging -> binding re-engages with latest model coords
node_item.setProperty("isDragging", False)
x_rel = node_item.property("x")
y_rel = node_item.property("y")
assert x_rel == 999.0, f"Expected 999.0 after drag release, got {x_rel}"
assert y_rel == 888.0, f"Expected 888.0 after drag release, got {y_rel}"
print("CHECK 4: Declarative binding re-engages when isDragging returns to False")

# Test 5: isHovered property gate
assert node_item.property("isHovered") == False
print("CHECK 5: isHovered clean gate verified")

print("ALL TEST CHECKS PASSED SUCCESSFULLY!")
