import os
import sys
import re

def verify_files():
    failures = []
    
    # 1. Check Node.qml for opaque #0B0F19 background
    with open("aia_canvas/src/qml/Node.qml", "r") as f:
        node_qml = f.read()
        
    if "color: rootItem.isSelected ? Theme.surfaceBackground : (rootItem.isMacroBead ? rootItem.nodeAccentColor : (rootItem.isHovered ? Theme.surfaceHovered : Theme.surfaceBackground))" not in node_qml:
        failures.append("Node.qml does not contain the required opaque background rule.")

    if "readonly property point rightDock: getCanvasDock(false)" not in node_qml or "readonly property point leftDock: getCanvasDock(true)" not in node_qml:
        failures.append("Node.qml does not expose leftDock/rightDock anchors properly.")
        
    # 2. Check PreviewSlate.qml for stripped background/borders
    with open("aia_canvas/src/qml/PreviewSlate.qml", "r") as f:
        preview_slate = f.read()
        
    if "color: \"#0a0c10\"" in preview_slate and "border.color: \"#30363d\"" in preview_slate:
        # Check if the fallback card still has a background
        # We removed it, but we should make sure
        failures.append("PreviewSlate.qml still has inner background or borders.")

    # 3. Check NodePreview.qml
    with open("aia_canvas/src/qml/node/NodePreview.qml", "r") as f:
        node_preview = f.read()
        
    if "color: \"#0B0F19\"" in node_preview and "border.color: \"#3D5AFE\"" in node_preview:
        failures.append("NodePreview.qml still has a previewBg with borders.")
        
    if len(failures) == 0:
        print("PASS: Visual invariants confirmed.")
        sys.exit(0)
    else:
        for f in failures:
            print("FAIL:", f)
        sys.exit(1)

if __name__ == "__main__":
    verify_files()
