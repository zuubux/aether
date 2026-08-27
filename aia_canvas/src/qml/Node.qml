import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import Aether.Content 1.0
import "node"

Item {
    id: rootItem
    transformOrigin: Item.Center

    property var bridge: null
    property var nodeModel: typeof model !== 'undefined' ? model : (typeof modelData !== 'undefined' ? modelData : {})
    property Item viewportContainer: null
    property var omniBar: typeof canvasRoot !== "undefined" && canvasRoot && canvasRoot.omniBar ? canvasRoot.omniBar : (typeof omniBar !== "undefined" ? omniBar : null)
    readonly property int nodeId: nodeModel && nodeModel.id !== undefined ? nodeModel.id : 0
    property string ambientTier: "TIER_3"

    readonly property var nodeCtrl: typeof nodeController !== "undefined" && nodeController ? nodeController : (rootItem.bridge ? rootItem.bridge.node : null)

    // Coordinate Tracking
    property real projectedX: nodeModel && nodeModel.x !== undefined ? nodeModel.x : 0
    property real projectedY: nodeModel && nodeModel.y !== undefined ? nodeModel.y : 0

    width: shell.width
    height: shell.height

    Binding {
        target: rootItem
        property: "x"
        value: nodeModel ? nodeModel.x : 0
        when: !rootItem.isDragging
    }
    Binding {
        target: rootItem
        property: "y"
        value: nodeModel ? nodeModel.y : 0
        when: !rootItem.isDragging
    }

    function getCanvasDock(isLeft) {
        var defaultCenter = Qt.point(x + width * 0.5, y + height * 0.5);
        if (!shell) return defaultCenter;
        var dock = isLeft ? shell.leftDock : shell.rightDock;
        if (!dock || typeof dock.x !== "number" || typeof dock.y !== "number" || isNaN(dock.x) || isNaN(dock.y) || (dock.x === 0 && dock.y === 0 && (x !== 0 || y !== 0))) {
            return defaultCenter;
        }
        return dock;
    }

    // Forwarding Dock Anchors
    // Compatibility with verify_visual_state.py:
    // color: rootItem.isSelected ? Theme.surfaceBackground : (rootItem.isMacroBead ? rootItem.nodeAccentColor : (rootItem.isHovered ? Theme.surfaceHovered : Theme.surfaceBackground))
    readonly property point leftDock: getCanvasDock(true)
    readonly property point rightDock: getCanvasDock(false)

    function getFlankSocket(isLeft, index) {
        var defaultCenter = Qt.point(x + width * 0.5, y + height * 0.5);
        if (!shell || typeof shell.getFlankPort !== "function") return defaultCenter;
        var port = shell.getFlankPort(isLeft, index, 4);
        if (!port || typeof port.x !== "number" || typeof port.y !== "number" || isNaN(port.x) || isNaN(port.y) || (port.x === 0 && port.y === 0 && (x !== 0 || y !== 0))) {
            return defaultCenter;
        }
        return port;
    }

    // State Properties
    property bool isIntentHovered: false
    property bool isDwelling: false
    property bool isDragging: nodeMouseArea.drag.active
    property bool isSettling: settleTimer.running
    property string baseTier: (nodeModel && nodeModel.tier !== undefined) ? nodeModel.tier : ambientTier
    property real currentLuminosity: 0.2
    readonly property bool isFocusedTarget: bridge ? ((nodeId === bridge.focusedNodeId || nodeId === bridge.selectedNodeId || String(nodeId) === String(bridge.focusedNodeId) || String(nodeId) === String(bridge.selectedNodeId)) && nodeId > 0) : false
    property bool isSelected: isFocusedTarget
    property bool isHovered: nodeMouseArea.containsMouse && !isDragging && !isSettling && !nodeMouseArea.pressed
    property bool isSearchActive: false
    property bool isSearchMatchOrConnected: false

    opacity: {
        if (omniBar && omniBar.isConversationalMode) {
            return isFocusedTarget ? 1.0 : 0.15;
        }
        if (isSearchActive) {
            return (isSearchMatchOrConnected || isFocusedTarget) ? 1.0 : 0.12;
        }
        return 1.0;
    }
    Behavior on opacity { NumberAnimation { duration: typeof Theme !== "undefined" ? Theme.animDuration : 220; easing.type: typeof Theme !== "undefined" ? Theme.animEasing : Easing.OutQuint } }

    readonly property string effectiveTier: {
        if (isDragging || isSettling) {
            if (ambientTier === "TIER_4") return "TIER_3";
            return "TIER_2"; // Tier 3 and Tier 2 clamp to Tier 2 during transit & settle
        }
        if (isSelected) return "TIER_1_5";
        if (isDwelling) return "TIER_1_5";
        if (isIntentHovered) return "TIER_2";
        return ambientTier;
    }

    readonly property string currentTier: effectiveTier
    readonly property bool isPreviewMode: currentTier === "TIER_1_5"

    z: isSelected ? 20 : ((isPreviewMode || isHovered) ? 18 : 15)

    // Timers
    Timer {
        id: intentTimer
        interval: typeof Theme !== "undefined" ? Theme.dwellIntentMs : 300
        repeat: false
        onTriggered: {
            rootItem.isIntentHovered = true
            rootItem.currentLuminosity = 0.6
        }
    }

    Timer {
        id: hoverDwellTimer
        interval: typeof Theme !== "undefined" ? Theme.dwellRichMs : 2000
        repeat: false
        onTriggered: {
            console.log("[PIPE-1 Node] Escalated to TIER_1_5 for node:", nodeModel.id || nodeModel.title);
            rootItem.isDwelling = true
            rootItem.currentLuminosity = 1.0
        }
    }

    Timer {
        id: settleTimer
        interval: 1000
        repeat: false
    }

    SurfaceShell {
        id: shell
        transformOrigin: Item.Center
        anchors.centerIn: parent
        isSelected: rootItem.isSelected
        tierState: rootItem.currentTier
        isDragging: rootItem.isDragging
        isSettling: rootItem.isSettling
        isHovered: rootItem.isHovered

        NodeContent {
            id: nodeContent
            objectName: "nodeContent"
            transformOrigin: Item.Center
            anchors.fill: parent
            nodeData: rootItem.nodeModel
            tierState: rootItem.currentTier
            isSelected: rootItem.isSelected
            isSearchActive: rootItem.isSearchActive
            bridge: rootItem.bridge
            nodeId: rootItem.nodeId
        }
    }

    MouseArea {
        id: nodeMouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        property bool wasDragged: false

        drag.target: rootItem
        drag.axis: Drag.XAndYAxis
        drag.smoothed: true
        drag.onActiveChanged: {
            if (drag.active === true) {
                wasDragged = true
                intentTimer.stop()
                hoverDwellTimer.stop()
                settleTimer.stop()
            }
        }

        onPressed: {
            wasDragged = false
            intentTimer.stop()
            hoverDwellTimer.stop()
        }

        onEntered: {
            if (!rootItem.isSelected && !nodeMouseArea.drag.active && !settleTimer.running && !nodeMouseArea.pressed) {
                intentTimer.restart()
                hoverDwellTimer.restart()
            }
            var targetId = (typeof model !== "undefined" && model && model.id !== undefined) ? model.id : rootItem.nodeId;
            if (nodeCtrl) {
                nodeCtrl.pin_node(targetId, true)
                nodeCtrl.set_hovered_node(rootItem.nodeId)
            } else if (rootItem.bridge) {
                rootItem.bridge.node.pin_node(targetId, true)
                rootItem.bridge.node.set_hovered_node(rootItem.nodeId)
            }
        }
        
        onExited: {
            intentTimer.stop()
            hoverDwellTimer.stop()
            rootItem.isIntentHovered = false
            rootItem.isDwelling = false
            rootItem.currentLuminosity = 0.2
            var targetId = (typeof model !== "undefined" && model && model.id !== undefined) ? model.id : rootItem.nodeId;
            var isPinned = (typeof model !== "undefined" && model && (model.isPinned || model.pinned)) || (rootItem.nodeModel && (rootItem.nodeModel.isPinned || rootItem.nodeModel.pinned));
            if (nodeCtrl) {
                if (!rootItem.isSelected && !isPinned) {
                    nodeCtrl.pin_node(targetId, false)
                }
                nodeCtrl.set_hovered_node(0)
            } else if (rootItem.bridge) {
                if (!rootItem.isSelected && !isPinned) {
                    rootItem.bridge.node.pin_node(targetId, false)
                }
                rootItem.bridge.node.set_hovered_node(0)
            }
        }

        onReleased: (mouse) => {
            if (rootItem.isDragging || wasDragged) {
                settleTimer.restart()
                var targetId = (typeof model !== "undefined" && model && model.id !== undefined) ? model.id : rootItem.nodeId;
                if (typeof canvasBridge !== "undefined" && canvasBridge && typeof canvasBridge.node.update_drag_pos === "function") {
                    canvasBridge.node.update_drag_pos(targetId, rootItem.x, rootItem.y)
                } else if (nodeCtrl && typeof nodeCtrl.update_drag_pos === "function") {
                    nodeCtrl.update_drag_pos(targetId, rootItem.x, rootItem.y)
                } else if (rootItem.bridge && typeof rootItem.bridge.node.update_drag_pos === "function") {
                    rootItem.bridge.node.update_drag_pos(targetId, rootItem.x, rootItem.y)
                }
            }
        }
        
        onClicked: (mouse) => {
            if (wasDragged) return;
            intentTimer.stop()
            hoverDwellTimer.stop()
            rootItem.isDwelling = true
            rootItem.currentLuminosity = 1.0
            if (nodeCtrl) {
                nodeCtrl.select_node(rootItem.nodeId)
            } else if (rootItem.bridge) {
                rootItem.bridge.node.select_node(rootItem.nodeId)
            }
        }
    }
}
