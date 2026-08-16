import QtQuick
import QtQuick.Controls

Item {
    id: rootItem

    property var bridge: null
    property Item viewportContainer: null
    property var nodeModel: null

    readonly property int nodeId: nodeModel ? nodeModel.id : 0
    readonly property bool isSelected: bridge ? (bridge.selectedNodeId === nodeId && nodeId > 0) : false
    readonly property bool isHovered: bridge ? (bridge.hoveredNodeId === nodeId) : false
    readonly property real focusWeight: nodeModel ? nodeModel.focus : 0.35

    // Relational Focus Classification
    readonly property bool hasActiveFocus: bridge ? (bridge.selectedNodeId > 0) : false
    readonly property bool isDirectNeighbor: hasActiveFocus && focusWeight >= 0.60

    // Aperture & Semantic Zoom Thresholds
    readonly property real currentAperture: bridge ? bridge.aperture : 1.0
    readonly property real macroThreshold: 0.35
    readonly property real secondaryBeadThreshold: 0.74
    readonly property real compactThreshold: 0.78

    // Semantic Zoom Classification
    readonly property bool wouldBeBead: {
        if (isSelected) return false
        if (hasActiveFocus) {
            if (!isDirectNeighbor) return currentAperture < secondaryBeadThreshold
            return currentAperture < macroThreshold
        }
        return currentAperture < macroThreshold
    }

    readonly property bool isMacroBead: wouldBeBead && !isHovered
    readonly property bool isHoverBloomed: wouldBeBead && isHovered

    readonly property bool isCompactCapsule: {
        if (isSelected || isMacroBead || isHoverBloomed) return false
        if (hasActiveFocus && !isDirectNeighbor) return true
        return currentAperture < compactThreshold
    }

    readonly property bool isFullToken: !isSelected && !isMacroBead && !isCompactCapsule && !isHoverBloomed

    // Semantic Extension Colors
    readonly property string ext: nodeModel ? nodeModel.extension.toLowerCase() : ".txt"
    readonly property color nodeAccentColor: {
        if (ext === ".py") return "#38bdf8"
        if (ext === ".sh" || ext === ".bash" || ext === ".zsh") return "#fbbf24"
        if (ext === ".md" || ext === ".org" || ext === ".txt") return "#a78bfa"
        if (ext === ".json" || ext === ".yaml" || ext === ".toml") return "#34d399"
        return "#94a3b8"
    }

    // Downstream Connection Count
    readonly property int downstreamCount: bridge ? bridge.get_downstream_count(nodeId) : 0

    // Target Dimensions
    readonly property real targetWidth: {
        if (isSelected) return bridge ? bridge.workbenchWidth : 1400
        if (isMacroBead) return 16
        if (isHoverBloomed) return 160
        if (isCompactCapsule) return 180
        return 280
    }

    readonly property real targetHeight: {
        if (isSelected) return bridge ? bridge.workbenchHeight : 900
        if (isMacroBead) return 16
        if (isHoverBloomed) return 32
        if (isCompactCapsule) return 48
        return 115
    }

    readonly property real cardRadius: {
        if (isSelected) return 14
        if (isMacroBead) return 8
        if (isHoverBloomed) return 16
        if (isCompactCapsule) return 24
        return 10
    }

    // Geometry exports for Tendril.qml
    readonly property real cardWidth: cardBody.width * scale
    readonly property real cardHeight: cardBody.height * scale
    readonly property real cardCenterX: x
    readonly property real cardCenterY: y

    // Direct Physics Drive with Selective Glide on Selection
    x: nodeModel ? nodeModel.x : 0
    y: nodeModel ? nodeModel.y : 0
    width: 0
    height: 0

    Behavior on x {
        enabled: rootItem.isSelected && !dragArea.isDragging
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }
    Behavior on y {
        enabled: rootItem.isSelected && !dragArea.isDragging
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }

    scale: isHoverBloomed ? 1.15 : (isHovered ? 1.05 : 1.0)
    Behavior on scale {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    z: isSelected ? 400 : (isHoverBloomed ? 350 : (isHovered ? 300 : Math.round(focusWeight * 100)))

    opacity: isHovered ? 1.0 : Math.max(0.25, focusWeight)
    Behavior on opacity {
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    Rectangle {
        id: cardBody
        anchors.centerIn: parent
        width: rootItem.targetWidth
        height: rootItem.targetHeight
        radius: rootItem.cardRadius
        clip: true

        Behavior on width {
            enabled: !resizeMouseArea.isResizing
            NumberAnimation { duration: 380; easing.type: Easing.OutQuint }
        }
        Behavior on height {
            enabled: !resizeMouseArea.isResizing
            NumberAnimation { duration: 380; easing.type: Easing.OutQuint }
        }
        Behavior on radius {
            NumberAnimation { duration: 300; easing.type: Easing.OutQuint }
        }

        color: rootItem.isSelected ? "#0c0e12" : (rootItem.isMacroBead ? rootItem.nodeAccentColor : (rootItem.isHovered ? "#161c28" : "#0a0c10"))
        border.color: rootItem.isSelected ? "#38bdf8" : (rootItem.isMacroBead ? Qt.lighter(rootItem.nodeAccentColor, 1.3) : (rootItem.isHovered ? rootItem.nodeAccentColor : "#1e2430"))
        border.width: rootItem.isMacroBead ? 1.5 : (rootItem.isSelected || rootItem.isHovered ? 1.5 : 1.0)

        Behavior on color { ColorAnimation { duration: 180 } }
        Behavior on border.color { ColorAnimation { duration: 180 } }

        // Star Bead Core Dot
        Rectangle {
            visible: rootItem.isMacroBead
            anchors.centerIn: parent
            width: 6
            height: 6
            radius: 3
            color: "#ffffff"
            opacity: 0.85
        }

        // =====================================================================
        // TIER 4: Hover-Bloomed Preview Capsule
        // =====================================================================
        Item {
            id: bloomView
            anchors.fill: parent
            anchors.margins: 6
            opacity: rootItem.isHoverBloomed ? 1.0 : 0.0
            visible: opacity > 0.01

            Behavior on opacity { NumberAnimation { duration: 150 } }

            Row {
                anchors.centerIn: parent
                spacing: 8

                Rectangle {
                    width: 8
                    height: 8
                    radius: 4
                    color: rootItem.nodeAccentColor
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: rootItem.nodeModel ? rootItem.nodeModel.fileName : ""
                    color: "#f8fafc"
                    font.family: "Monospace"
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                    width: 120
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // =====================================================================
        // TIER 3: Compact Capsule
        // =====================================================================
        Item {
            id: deepPillView
            anchors.fill: parent
            anchors.margins: 8
            opacity: rootItem.isCompactCapsule ? 1.0 : 0.0
            visible: opacity > 0.01

            Behavior on opacity { NumberAnimation { duration: 180 } }

            Row {
                anchors.centerIn: parent
                spacing: 8

                Rectangle {
                    width: 32
                    height: 18
                    radius: 4
                    color: "#111827"
                    border.color: rootItem.nodeAccentColor
                    border.width: 1
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: rootItem.ext
                        color: rootItem.nodeAccentColor
                        font.family: "Monospace"
                        font.pixelSize: 8
                        font.bold: true
                    }
                }

                Text {
                    text: rootItem.nodeModel ? rootItem.nodeModel.fileName : ""
                    color: rootItem.isHovered ? "#ffffff" : (rootItem.isDirectNeighbor ? "#cbd5e1" : "#64748b")
                    font.family: "Monospace"
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                    width: 115
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // =====================================================================
        // TIER 2: Orbital Horizon Token
        // =====================================================================
        Item {
            id: tokenView
            anchors.fill: parent
            anchors.margins: 14
            opacity: rootItem.isFullToken ? 1.0 : 0.0
            visible: opacity > 0.01

            Behavior on opacity { NumberAnimation { duration: 180 } }

            Column {
                anchors.fill: parent
                spacing: 6

                Row {
                    width: parent.width
                    spacing: 8

                    Rectangle {
                        width: 38
                        height: 18
                        radius: 4
                        color: "#111827"
                        border.color: rootItem.isDirectNeighbor ? rootItem.nodeAccentColor : "#1e293b"
                        border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: rootItem.ext
                            color: rootItem.nodeAccentColor
                            font.family: "Monospace"
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }

                    Text {
                        text: rootItem.nodeModel ? rootItem.nodeModel.fileName : ""
                        color: rootItem.isHovered ? "#ffffff" : (rootItem.isDirectNeighbor ? "#f1f5f9" : "#64748b")
                        font.family: "Monospace"
                        font.pixelSize: 13
                        font.bold: true
                        elide: Text.ElideRight
                        width: parent.width - (rootItem.downstreamCount > 0 ? 86 : 46)
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        visible: rootItem.downstreamCount > 0
                        width: 30
                        height: 18
                        radius: 9
                        color: rootItem.isHovered ? "#0369a1" : "#162032"
                        border.color: rootItem.isHovered ? "#38bdf8" : "#1e293b"
                        border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "⤹ " + rootItem.downstreamCount
                            color: rootItem.isHovered ? "#f0f9ff" : "#60a5fa"
                            font.family: "Monospace"
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: rootItem.isDirectNeighbor ? "#1f242d" : "#14171f"
                }

                Text {
                    text: rootItem.nodeModel ? rootItem.nodeModel.filePath : ""
                    color: rootItem.isHovered ? "#94a3b8" : (rootItem.isDirectNeighbor ? "#64748b" : "#334155")
                    font.family: "Monospace"
                    font.pixelSize: 10
                    elide: Text.ElideMiddle
                    width: parent.width
                }
            }
        }

        // =====================================================================
        // TIER 1: Focal Workbench
        // =====================================================================
        Item {
            id: workbenchView
            anchors.fill: parent
            anchors.margins: 18

            readonly property bool isExpandedEnough: cardBody.width > (rootItem.targetWidth * 0.65)
            opacity: (rootItem.isSelected && isExpandedEnough) ? 1.0 : 0.0
            visible: opacity > 0.01
            z: 10

            Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutQuad } }

            Column {
                anchors.fill: parent
                spacing: 12

                Row {
                    width: parent.width
                    spacing: 10

                    Rectangle {
                        width: 46
                        height: 22
                        radius: 4
                        color: "#1e293b"
                        border.color: rootItem.nodeAccentColor
                        border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: rootItem.ext
                            color: rootItem.nodeAccentColor
                            font.family: "Monospace"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    Text {
                        text: rootItem.nodeModel ? rootItem.nodeModel.fileName : ""
                        color: "#f8fafc"
                        font.family: "Monospace"
                        font.pixelSize: 15
                        font.bold: true
                        elide: Text.ElideRight
                        width: parent.width - 160
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        width: 90
                        height: 24
                        radius: 4
                        color: "#161b22"
                        border.color: "#30363d"
                        border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "Reveal File"
                            color: "#94a3b8"
                            font.family: "Monospace"
                            font.pixelSize: 10
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (rootItem.bridge && rootItem.nodeModel) {
                                    rootItem.bridge.open_in_file_manager(rootItem.nodeModel.filePath)
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: "#1f242d"
                }

                Text {
                    text: rootItem.nodeModel ? rootItem.nodeModel.filePath : ""
                    color: "#94a3b8"
                    font.family: "Monospace"
                    font.pixelSize: 10
                    elide: Text.ElideMiddle
                    width: parent.width
                }

                Rectangle {
                    width: parent.width
                    height: parent.height - 75
                    color: "#08090c"
                    radius: 8
                    border.color: "#161922"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "[ Live Workbench Canvas: " + (rootItem.nodeModel ? rootItem.nodeModel.fileName : "") + " ]\nReady for active text buffer, terminal shell, or media viewport."
                        color: "#3b4252"
                        font.family: "Monospace"
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }

        // =====================================================================
        // Workbench Resizing Grip
        // =====================================================================
        Rectangle {
            id: resizeGrip
            visible: rootItem.isSelected
            width: 28
            height: 28
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            anchors.margins: 4
            color: "transparent"
            z: 500

            Canvas {
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = "#38bdf8"
                    ctx.lineWidth = 2.0
                    ctx.beginPath()
                    ctx.moveTo(22, 10); ctx.lineTo(10, 22)
                    ctx.moveTo(22, 16); ctx.lineTo(16, 22)
                    ctx.stroke()
                }
            }

            MouseArea {
                id: resizeMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.SizeFDiagCursor

                property bool isResizing: false
                property real startMouseX: 0
                property real startMouseY: 0
                property real startW: 0
                property real startH: 0

                onPressed: function(mouse) {
                    isResizing = true
                    var globalPt = mapToItem(null, mouse.x, mouse.y)
                    startMouseX = globalPt.x
                    startMouseY = globalPt.y
                    startW = cardBody.width
                    startH = cardBody.height
                }

                onPositionChanged: function(mouse) {
                    if (isResizing && rootItem.bridge) {
                        var globalPt = mapToItem(null, mouse.x, mouse.y)
                        var deltaX = (globalPt.x - startMouseX) * 2.0
                        var deltaY = (globalPt.y - startMouseY) * 2.0
                        rootItem.bridge.set_workbench_dimensions(
                            Math.max(700, startW + deltaX),
                            Math.max(450, startH + deltaY)
                        )
                    }
                }

                onReleased: { isResizing = false }
                onCanceled: { isResizing = false }
            }
        }

        // =====================================================================
        // Interaction & Hover Reporting
        // =====================================================================
        MouseArea {
            id: dragArea
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            cursorShape: Qt.PointingHandCursor

            property real pressStartX: 0
            property real pressStartY: 0
            property real dragOffsetX: 0
            property real dragOffsetY: 0
            property bool isDragging: false
            property bool isDragMoved: false

            onEntered: {
                if (rootItem.bridge && !rootItem.isSelected) {
                    rootItem.bridge.set_hovered_node(rootItem.nodeId)
                }
            }

            onExited: {
                if (rootItem.bridge && !isDragging) {
                    rootItem.bridge.set_hovered_node(0)
                }
            }

            onPressed: function(mouse) {
                if (mouse.button === Qt.RightButton) {
                    if (rootItem.bridge && rootItem.nodeModel) {
                        rootItem.bridge.open_in_file_manager(rootItem.nodeModel.filePath)
                    }
                    return
                }

                isDragging = true
                isDragMoved = false
                pressStartX = mouse.x
                pressStartY = mouse.y

                var container = rootItem.viewportContainer || rootItem.parent
                var posInParent = mapToItem(container, mouse.x, mouse.y)
                var centerAnchorX = rootItem.nodeModel ? rootItem.nodeModel.x : rootItem.x
                var centerAnchorY = rootItem.nodeModel ? rootItem.nodeModel.y : rootItem.y
                dragOffsetX = posInParent.x - centerAnchorX
                dragOffsetY = posInParent.y - centerAnchorY

                if (rootItem.bridge) {
                    rootItem.bridge.pin_node(rootItem.nodeId, centerAnchorX, centerAnchorY)
                }
            }

            onPositionChanged: function(mouse) {
                if (isDragging && rootItem.bridge) {
                    var dx = Math.abs(mouse.x - pressStartX)
                    var dy = Math.abs(mouse.y - pressStartY)
                    if (dx > 6 || dy > 6) {
                        isDragMoved = true
                    }

                    var container = rootItem.viewportContainer || rootItem.parent
                    var posInParent = mapToItem(container, mouse.x, mouse.y)
                    rootItem.bridge.update_drag_pos(
                        rootItem.nodeId,
                        posInParent.x - dragOffsetX,
                        posInParent.y - dragOffsetY
                    )
                }
            }

            onReleased: function(mouse) {
                if (isDragging) {
                    isDragging = false
                    if (rootItem.bridge) {
                        rootItem.bridge.release_node(rootItem.nodeId)
                        if (!isDragMoved) {
                            rootItem.bridge.select_node(rootItem.nodeId)
                            rootItem.bridge.set_hovered_node(0)
                        }
                    }
                }
            }

            onCanceled: {
                if (isDragging) {
                    isDragging = false
                    if (rootItem.bridge) {
                        rootItem.bridge.release_node(rootItem.nodeId)
                    }
                }
            }
        }
    }
}