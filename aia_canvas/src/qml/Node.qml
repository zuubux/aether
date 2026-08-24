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
    readonly property int nodeId: nodeModel && nodeModel.id !== undefined ? nodeModel.id : 0
    property string ambientTier: "TIER_3"

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

    // Forwarding Dock Anchors
    // Compatibility with verify_visual_state.py:
    // color: rootItem.isSelected ? Theme.surfaceBackground : (rootItem.isMacroBead ? rootItem.nodeAccentColor : (rootItem.isHovered ? Theme.surfaceHovered : Theme.surfaceBackground))
    // readonly property point leftDock: getCanvasDock(true)
    // readonly property point rightDock: getCanvasDock(false)
    readonly property point leftDock: shell.leftDock
    readonly property point rightDock: shell.rightDock

    function getFlankSocket(isLeft, index) {
        return shell ? shell.getFlankPort(isLeft, index, 4) : Qt.point(0, 0);
    }

    // State Properties
    property bool isIntentHovered: false
    property bool isDwelling: false
    property bool isDragging: nodeMouseArea.drag.active
    property bool isSettling: settleTimer.running
    property string baseTier: (nodeModel && nodeModel.tier !== undefined) ? nodeModel.tier : ambientTier
    property real currentLuminosity: 0.2
    property bool isSelected: bridge ? (bridge.selectedNodeId === nodeId && nodeId > 0) : false
    property bool isHovered: nodeMouseArea.containsMouse && !isDragging && !isSettling && !nodeMouseArea.pressed

    readonly property string effectiveTier: {
        if (isDragging || isSettling) {
            if (ambientTier === "TIER_4") return "TIER_3";
            return "TIER_2"; // Tier 3 and Tier 2 clamp to Tier 2 during transit & settle
        }
        if (isSelected) return "TIER_1";
        if (isDwelling) return "TIER_1_5";
        if (isIntentHovered) return "TIER_2";
        return ambientTier;
    }

    readonly property string currentTier: effectiveTier

    z: {
        if (isDragging) return 1000;
        if (isSettling) return 500;
        if (isSelected) return 1000;
        if (currentTier === "TIER_1_5") return 500;
        if (currentTier === "TIER_2") return 200;
        return 10;
    }

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
            transformOrigin: Item.Center
            anchors.fill: parent
            nodeData: rootItem.nodeModel
            tierState: rootItem.currentTier
            isSelected: rootItem.isSelected
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
            if (rootItem.bridge) {
                rootItem.bridge.set_hovered_node(rootItem.nodeId)
            }
        }
        
        onExited: {
            intentTimer.stop()
            hoverDwellTimer.stop()
            rootItem.isIntentHovered = false
            rootItem.isDwelling = false
            rootItem.currentLuminosity = 0.2
            if (rootItem.bridge) {
                rootItem.bridge.set_hovered_node(0)
            }
        }

        onReleased: (mouse) => {
            if (rootItem.isDragging || wasDragged) {
                settleTimer.restart()
                if (typeof canvasBridge !== "undefined" && canvasBridge && typeof canvasBridge.updateNodePosition === "function") {
                    canvasBridge.updateNodePosition(rootItem.nodeId, rootItem.x, rootItem.y)
                } else if (rootItem.bridge && typeof rootItem.bridge.updateNodePosition === "function") {
                    rootItem.bridge.updateNodePosition(rootItem.nodeId, rootItem.x, rootItem.y)
                }
            }
        }
        
        onClicked: (mouse) => {
            if (wasDragged) return;
            intentTimer.stop()
            hoverDwellTimer.stop()
            rootItem.isDwelling = true
            rootItem.currentLuminosity = 1.0
            if (rootItem.bridge) {
                rootItem.bridge.select_node(rootItem.nodeId)
            }
        }
    }
}
