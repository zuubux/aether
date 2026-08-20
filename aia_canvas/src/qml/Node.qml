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

    readonly property string relationType: bridge ? bridge.get_relation_type(nodeId) : ""
    readonly property color relationAccentColor: {
        if (relationType === "semantic") return "#a78bfa" // Violet/Purple accent
        if (relationType === "explicit") return "#38bdf8" // Cyan accent
        if (relationType === "temporal") return "#fbbf24" // Amber/Yellow accent
        return rootItem.nodeAccentColor
    }

    // Downstream Connection Count
    readonly property int downstreamCount: bridge ? bridge.get_downstream_count(nodeId) : 0

    // =========================================================================
    // 2.5D Panoramic Horizon Projection (Decoupled X/Y Spread)
    // =========================================================================
    readonly property real wingWidth: bridge ? bridge.wingWidth : 300.0

    readonly property real vpX: {
        if (bridge && bridge.selectedNodeId > 0) {
            return (viewportContainer ? (viewportContainer.width - bridge.wingWidth) / 2.0 : 1280)
        }
        return viewportContainer ? viewportContainer.width / 2 : 1280
    }
    readonly property real vpY: viewportContainer ? viewportContainer.height * 0.20 : 280
    readonly property real rawPhysicsX: nodeModel ? nodeModel.x : 0
    readonly property real rawPhysicsY: nodeModel ? nodeModel.y : 0

    // Depth: z=0 foreground (bottom), z=1 horizon (top)
    readonly property real depthZ: {
        if (isSelected) return 0.0
        if (nodeModel && nodeModel.depthZ !== undefined) {
            return nodeModel.depthZ
        }
        var normalizedY = Math.max(0.0, Math.min(1.0, 1.0 - (rawPhysicsY / (viewportContainer ? viewportContainer.height : 1440))))
        return normalizedY * (1.0 - focusWeight * 0.5)
    }

    readonly property real perspectiveScale: 1.0 / (1.0 + depthZ * 1.25)
    readonly property real xSpreadFactor: 0.85 + 0.15 * perspectiveScale
    readonly property real projectedX: vpX + (rawPhysicsX - vpX) * xSpreadFactor
    readonly property real projectedY: vpY + (rawPhysicsY - vpY) * perspectiveScale

    // Wing Squeeze Opacity & Label fading for progressive depth cascade
    readonly property real wingSqueezeOpacity: {
        if (!hasActiveFocus) return 1.0
        if (!isDirectNeighbor) {
            if (wingWidth < 120.0) {
                return 0.2 + 0.8 * (wingWidth / 120.0)
            }
        }
        return 1.0
    }

    readonly property real labelOpacity: {
        if (hasActiveFocus && isDirectNeighbor) {
            if (wingWidth < 120.0) {
                return Math.max(0.0, wingWidth / 120.0)
            }
        }
        return 1.0
    }

    // Target Dimensions
    readonly property real targetWidth: {
        if (isSelected) return bridge ? bridge.workbenchWidth : 1400
        if (isMacroBead || isHoverBloomed) return 16
        if (isCompactCapsule) return 180
        return 280
    }

    readonly property real targetHeight: {
        if (isSelected) return bridge ? bridge.workbenchHeight : 900
        if (isMacroBead || isHoverBloomed) return 16
        if (isCompactCapsule) return 48
        return 115
    }

    readonly property real cardRadius: {
        if (isSelected) return 14
        if (isMacroBead || isHoverBloomed) return 8
        if (isCompactCapsule) return 24
        return 10
    }

    // Geometry exports for Tendril.qml
    readonly property real cardWidth: width * scale
    readonly property real cardHeight: height * scale
    readonly property real cardCenterX: x + width / 2
    readonly property real cardCenterY: y + height / 2

    // Projected Coordinate Anchors
    x: isSelected ? (viewportContainer ? (viewportContainer.width - targetWidth) / 2 : 0) : (projectedX - targetWidth / 2)
    y: isSelected ? (viewportContainer ? (viewportContainer.height - targetHeight) / 2 : 0) : (projectedY - targetHeight / 2)
    width: targetWidth
    height: targetHeight

    Behavior on x {
        enabled: rootItem.isSelected && !dragArea.isDragging && !resizeMouseArea.isResizing
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }
    Behavior on y {
        enabled: rootItem.isSelected && !dragArea.isDragging && !resizeMouseArea.isResizing
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }
    Behavior on width {
        enabled: !resizeMouseArea.isResizing
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }
    Behavior on height {
        enabled: !resizeMouseArea.isResizing
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }

    // Strict Scale Lock: Keep selected workbench card at exactly 1.0 to ensure 1:1 resize fidelity
    scale: isSelected ? 1.0 : ((isHoverBloomed ? 1.15 : (isHovered ? 1.05 : 1.0)) * perspectiveScale)
    Behavior on scale {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    // Depth Stacking
    z: isSelected ? 9000 : (isHoverBloomed ? 8000 : (isHovered ? 7000 : Math.round((1.0 - depthZ) * 1000 + focusWeight * 100)))

    readonly property real insideClusterFactor: {
        if (!nodeModel || nodeModel.clusterId === undefined || nodeModel.clusterId < 0) return 0.0;
        if (!bridge || !bridge.clusterHalos) return 0.0;
        var halos = bridge.clusterHalos;
        for (var i = 0; i < halos.length; i++) {
            if (halos[i].id === "component_" + nodeModel.clusterId) {
                var cx = halos[i].centerX;
                var cy = halos[i].centerY;
                var r = Math.min(halos[i].width, halos[i].height) * 0.5;
                var dx = rawPhysicsX - cx;
                var dy = rawPhysicsY - cy;
                var dist = Math.sqrt(dx * dx + dy * dy);
                
                var margin = 40.0;
                var innerR = r - margin;
                var outerR = r + margin;
                
                if (dist <= innerR) {
                    return 1.0;
                } else if (dist >= outerR) {
                    return 0.0;
                } else {
                    return (outerR - dist) / (2.0 * margin);
                }
            }
        }
        return 0.0;
    }

    readonly property bool isInsideCluster: insideClusterFactor > 0.5

    readonly property real macroOpacityFade: {
        if (isSelected || isHovered) return 1.0
        if (currentAperture >= 0.35) return 1.0
        
        var hasValidCluster = nodeModel && nodeModel.clusterId !== undefined && nodeModel.clusterId >= 0;
        if (!hasValidCluster) return 1.0;
        
        var fadedVal = Math.max(0.0, (currentAperture - 0.20) / 0.15);
        return 1.0 * (1.0 - insideClusterFactor) + fadedVal * insideClusterFactor;
    }

    // Atmospheric Haze Attenuation & Progressive Squeeze Falloff
    opacity: (isSelected ? 1.0 : (isHovered ? 1.0 : Math.max(0.0, focusWeight * (1.0 - depthZ * 0.35)))) * wingSqueezeOpacity * macroOpacityFade
    Behavior on opacity {
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    // =====================================================================
    // TIER 4: Hover-Bloomed Preview Capsule Overlay
    // =====================================================================
    Rectangle {
        id: bloomOverlay
        width: 160
        height: 32
        anchors.centerIn: parent
        radius: 16
        color: "#161c28"
        border.color: rootItem.nodeAccentColor
        border.width: 1.5
        opacity: rootItem.isHoverBloomed ? 1.0 : 0.0
        visible: opacity > 0.01
        z: 9999
        enabled: false

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

    Rectangle {
        id: cardBody
        anchors.fill: parent
        radius: rootItem.cardRadius
        clip: true
        opacity: rootItem.isHoverBloomed ? 0.0 : 1.0
        
        Behavior on opacity { NumberAnimation { duration: 150 } }

        Behavior on radius {
            NumberAnimation { duration: 300; easing.type: Easing.OutQuint }
        }

        color: rootItem.isSelected ? "#0c0e12" : (rootItem.isMacroBead ? rootItem.nodeAccentColor : (rootItem.isHovered ? "#161c28" : "#0a0c10"))
        border.color: rootItem.isSelected ? "#38bdf8" : (rootItem.isMacroBead ? Qt.lighter(rootItem.nodeAccentColor, 1.3) : (rootItem.isHovered ? rootItem.nodeAccentColor : (rootItem.isDirectNeighbor ? rootItem.relationAccentColor : "#1e2430")))
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
            opacity: rootItem.isFullToken ? rootItem.labelOpacity : 0.0
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
                        border.color: rootItem.isDirectNeighbor ? rootItem.relationAccentColor : "#1e293b"
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

            readonly property bool isExpandedEnough: cardBody.width > 600
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
        // Main Card Drag & Interaction Handler
        // =====================================================================
        MouseArea {
            id: dragArea
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            cursorShape: Qt.PointingHandCursor
            // Disable drag handling when clicking near the bottom-right resize corner on selected cards
            enabled: !resizeMouseArea.isResizing

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

                // If selected, do not drag through physics; let it sit anchored
                if (rootItem.isSelected) return

                isDragging = true
                isDragMoved = false
                pressStartX = mouse.x
                pressStartY = mouse.y

                var container = rootItem.viewportContainer || rootItem.parent
                var posInParent = mapToItem(container, mouse.x, mouse.y)
                var centerAnchorX = rootItem.rawPhysicsX
                var centerAnchorY = rootItem.rawPhysicsY
                dragOffsetX = posInParent.x - rootItem.projectedX
                dragOffsetY = posInParent.y - rootItem.projectedY

                if (rootItem.bridge) {
                    rootItem.bridge.pin_node(rootItem.nodeId, centerAnchorX, centerAnchorY)
                }
            }

            onPositionChanged: function(mouse) {
                if (isDragging && rootItem.bridge && !rootItem.isSelected) {
                    var dx = Math.abs(mouse.x - pressStartX)
                    var dy = Math.abs(mouse.y - pressStartY)
                    if (dx > 6 || dy > 6) {
                        isDragMoved = true
                    }

                    var container = rootItem.viewportContainer || rootItem.parent
                    var posInParent = mapToItem(container, mouse.x, mouse.y)
                    
                    var unprojX = rootItem.vpX + (posInParent.x - dragOffsetX - rootItem.vpX) / rootItem.xSpreadFactor
                    var unprojY = rootItem.vpY + (posInParent.y - dragOffsetY - rootItem.vpY) / rootItem.perspectiveScale

                    rootItem.bridge.update_drag_pos(rootItem.nodeId, unprojX, unprojY)
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
                } else if (!rootItem.isSelected && !isDragMoved) {
                    if (rootItem.bridge) {
                        rootItem.bridge.select_node(rootItem.nodeId)
                        rootItem.bridge.set_hovered_node(0)
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

        // =====================================================================
        // Workbench Resizing Grip (Top-Layer Z: 1000)
        // =====================================================================
        Rectangle {
            id: resizeGrip
            visible: rootItem.isSelected
            width: 32
            height: 32
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            anchors.margins: 4
            color: "transparent"
            z: 1000

            Canvas {
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = "#38bdf8"
                    ctx.lineWidth = 2.0
                    ctx.beginPath()
                    ctx.moveTo(26, 12); ctx.lineTo(12, 26)
                    ctx.moveTo(26, 18); ctx.lineTo(18, 26)
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
                    startW = rootItem.bridge ? rootItem.bridge.workbenchWidth : cardBody.width
                    startH = rootItem.bridge ? rootItem.bridge.workbenchHeight : cardBody.height
                }

                onPositionChanged: function(mouse) {
                    if (isResizing && rootItem.bridge) {
                        var globalPt = mapToItem(null, mouse.x, mouse.y)
                        var deltaX = (globalPt.x - startMouseX) * 2.0
                        var deltaY = (globalPt.y - startMouseY) * 2.0
                        rootItem.bridge.set_workbench_dimensions(
                            Math.max(650, Math.min(2400, startW + deltaX)),
                            Math.max(400, Math.min(1400, startH + deltaY))
                        )
                    }
                }

                onReleased: { isResizing = false }
                onCanceled: { isResizing = false }
            }
        }
    }
}