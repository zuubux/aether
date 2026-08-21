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
    readonly property real macroThreshold: 0.50
    readonly property real secondaryBeadThreshold: 1.15
    readonly property real compactThreshold: 1.20

    // Semantic Zoom Classification
    readonly property int baseTier: {
        if (hasActiveFocus) {
            if (!isDirectNeighbor) return currentAperture < secondaryBeadThreshold ? 4 : 3
            return currentAperture < macroThreshold ? 4 : (currentAperture < compactThreshold ? 3 : 2)
        }
        return currentAperture < macroThreshold ? 4 : (currentAperture < compactThreshold ? 3 : 2)
    }

    readonly property int effectiveTier: {
        if (isSelected) return 1
        if (isStaged || sustainedHover) return 15 // Tier 1.5 Preview Slate
        if (isHovered) {
            if (baseTier === 4) return 3
            if (baseTier === 3) return 2
            if (baseTier === 2) return 15
        }
        return baseTier
    }

    readonly property bool isMacroBead: effectiveTier === 4
    readonly property bool isCompactCapsule: effectiveTier === 3
    readonly property bool isFullToken: effectiveTier === 2
    readonly property bool showPreviewSlate: effectiveTier === 15

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

    // Search / Spotlight State
    readonly property bool isSearchResult: viewportContainer && viewportContainer.searchActive ? (viewportContainer.searchResultIds.indexOf(nodeId.toString()) !== -1) : false
    readonly property bool isSearchDimmed: viewportContainer && viewportContainer.searchActive && !isSearchResult
    readonly property int searchResultIndex: isSearchResult && viewportContainer ? viewportContainer.searchResultIds.indexOf(nodeId.toString()) : -1
    readonly property int totalSlots: viewportContainer && viewportContainer.searchActive ? viewportContainer.searchResultIds.length : 0
    readonly property int columns: viewportContainer ? Math.max(1, Math.floor((viewportContainer.width * 0.85) / 340)) : 1
    readonly property int gridRow: searchResultIndex >= 0 ? Math.floor(searchResultIndex / columns) : 0
    readonly property int gridCol: searchResultIndex >= 0 ? (searchResultIndex % columns) : 0
    readonly property int itemsInCurrentRow: (searchResultIndex >= 0 && totalSlots > 0) ? Math.min(columns, totalSlots - gridRow * columns) : 1
    readonly property real slotWidth: 340
    readonly property real stagedX: viewportContainer ? (viewportContainer.width / 2) + (gridCol - (itemsInCurrentRow - 1) / 2.0) * slotWidth : 0
    readonly property real stagedY: viewportContainer ? viewportContainer.height * 0.28 + gridRow * 240 : 0

    property bool isStaged: isSearchResult
    property bool sustainedHover: false
    Timer {
        id: dwellTimer
        interval: 1500
        running: rootItem.isHovered && !rootItem.isStaged && !rootItem.isSelected
        onTriggered: {
            sustainedHover = true
        }
    }
    onIsHoveredChanged: {
        if (!isHovered) {
            sustainedHover = false
        }
    }

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
        if (showPreviewSlate) return 320
        if (isMacroBead) return 16
        if (isCompactCapsule) return 180
        return 280
    }

    readonly property real targetHeight: {
        if (isSelected) return bridge ? bridge.workbenchHeight : 900
        if (showPreviewSlate) return 220
        if (isMacroBead) return 16
        if (isCompactCapsule) return 48
        return 115
    }

    readonly property real cardRadius: {
        if (isSelected) return 14
        if (isMacroBead) return 8
        if (isCompactCapsule) return 24
        return 10
    }

    // Geometry exports for Tendril.qml
    readonly property real cardWidth: width * scale
    readonly property real cardHeight: height * scale
    readonly property real cardCenterX: x + width / 2
    readonly property real cardCenterY: y + height / 2

    property real verticalOffset: (isStaged && !isHovered && !isSelected) ? Math.sin((viewportContainer ? viewportContainer.canvasGlobalTime : 0) * 0.0025 + searchResultIndex * 0.75) * 3.5 : 0.0
    Behavior on verticalOffset { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }

    // Projected Coordinate Anchors
    transformOrigin: Item.Center
    x: isSelected ? (viewportContainer ? (viewportContainer.width - width) / 2 : 0) : (isSearchResult ? (stagedX - width / 2) : (projectedX - width / 2))
    y: isSelected ? (viewportContainer ? (viewportContainer.height - height) / 2 : 0) : (isSearchResult ? (stagedY - height / 2) + verticalOffset : (projectedY - height / 2))
    width: Math.round(targetWidth)
    height: Math.round(targetHeight)

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
    scale: isSelected ? 1.0 : ((isHovered ? 1.05 : 1.0) * perspectiveScale)
    Behavior on scale {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    // Depth Stacking
    z: isSelected ? 9000 : (isHovered ? 7000 : Math.round((1.0 - depthZ) * 1000 + focusWeight * 100))

    readonly property real insideClusterFactor: {
        if (!nodeModel || nodeModel.clusterId === undefined || nodeModel.clusterId < 0) return 0.0;
        if (!bridge || !bridge.clusterHalos) return 0.0;
        
        var apertureFactor = 1.0 - Math.max(0.0, Math.min(1.0, (currentAperture - 0.30) / 0.20));
        if (apertureFactor <= 0.0) return 0.0;

        var halos = bridge.clusterHalos;
        for (var i = 0; i < halos.length; i++) {
            if (halos[i].id === "component_" + nodeModel.clusterId) {
                var cx = halos[i].centerX;
                var cy = halos[i].centerY;
                // Expanded fade radius and soft 30px transition buffer
                var r = Math.max(halos[i].haloWidth, halos[i].haloHeight) * 0.6; 
                var dx = rawPhysicsX - cx;
                var dy = rawPhysicsY - cy;
                var dist = Math.sqrt(dx * dx + dy * dy);
                
                var margin = 30.0;
                var innerR = r - margin;
                var outerR = r + margin;
                
                var baseFactor = 0.0;
                if (dist <= innerR) {
                    baseFactor = 1.0;
                } else if (dist >= outerR) {
                    baseFactor = 0.0;
                } else {
                    baseFactor = (outerR - dist) / (2.0 * margin);
                }
                return baseFactor * apertureFactor;
            }
        }
        return 0.0;
    }

    readonly property bool isInsideCluster: insideClusterFactor > 0.5

    readonly property real macroOpacityFade: {
        if (isSelected || isHovered) return 1.0
        
        var hasValidCluster = nodeModel && nodeModel.clusterId !== undefined && nodeModel.clusterId >= 0;
        if (!hasValidCluster) return 1.0;
        
        // Do not fade interior nodes to 0.0; clamp at macro aperture to faint star beads
        var fade = 1.0 - insideClusterFactor;
        if (currentAperture <= 0.50) {
            return Math.max(0.45, fade);
        }
        return Math.max(0.45, fade);
    }

    // Atmospheric Haze Attenuation & Progressive Squeeze Falloff
    opacity: {
        if (viewportContainer && viewportContainer.searchActive) {
            return isSearchResult ? 1.0 : 0.15
        }
        return (isSelected ? 1.0 : (isHovered ? 1.0 : Math.max(0.0, focusWeight * (1.0 - depthZ * 0.35)))) * wingSqueezeOpacity * macroOpacityFade
    }
    Behavior on opacity {
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    Rectangle {
        id: cardBody
        anchors.fill: parent
        radius: rootItem.cardRadius
        clip: true

        Behavior on radius {
            NumberAnimation { duration: 300; easing.type: Easing.OutQuint }
        }

        color: rootItem.isSelected ? "#0c0e12" : (rootItem.isMacroBead ? rootItem.nodeAccentColor : (rootItem.isHovered ? "#161c28" : "#0a0c10"))
        border.color: rootItem.isSearchResult ? "#64d2ff" : (rootItem.isSelected ? "#38bdf8" : (rootItem.isMacroBead ? Qt.lighter(rootItem.nodeAccentColor, 1.3) : (rootItem.isHovered ? rootItem.nodeAccentColor : (rootItem.isDirectNeighbor ? rootItem.relationAccentColor : "#1e2430"))))
        border.width: rootItem.isSearchResult ? 2.5 : (rootItem.isMacroBead ? 1.5 : (rootItem.isSelected || rootItem.isHovered ? 1.5 : 1.0))
        antialiasing: true
        smooth: true

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
            opacity: rootItem.isCompactCapsule && !rootItem.showPreviewSlate && !rootItem.isSelected ? 1.0 : 0.0
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
            opacity: rootItem.isFullToken && !rootItem.showPreviewSlate && !rootItem.isSelected ? rootItem.labelOpacity : 0.0
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
        // TIER 1.5: Preview Slate
        // =====================================================================
        Loader {
            id: previewLoader
            anchors.centerIn: parent
            width: 320
            height: 220
            active: rootItem.showPreviewSlate && !rootItem.isSelected
            visible: opacity > 0.01
            opacity: rootItem.showPreviewSlate && !rootItem.isSelected ? 1.0 : 0.0
            source: "PreviewSlate.qml"
            
            Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutQuad } }

            onLoaded: {
                item.archetype = Qt.binding(function() { return rootItem.nodeModel ? rootItem.nodeModel.archetype : "document" })
                item.snippet = Qt.binding(function() { return rootItem.nodeModel ? rootItem.nodeModel.snippet : "" })
                item.fileName = Qt.binding(function() { return rootItem.nodeModel ? rootItem.nodeModel.fileName : "" })
                item.filePath = Qt.binding(function() { return rootItem.nodeModel ? rootItem.nodeModel.filePath : "" })
                item.sizeFormatted = Qt.binding(function() { return rootItem.nodeModel ? (rootItem.nodeModel.sizeBytes / 1024).toFixed(1) + " KB" : "0 KB" })
                item.referenceCount = Qt.binding(function() { return rootItem.downstreamCount })
                item.accentColor = Qt.binding(function() { return rootItem.nodeAccentColor })
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
            anchors.margins: -16 // Hit-box stabilization padding
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
                    }
                }
            }

            onClicked: function(mouse) {
                if (mouse.button === Qt.LeftButton && !rootItem.isSelected) {
                    if (rootItem.bridge) {
                        rootItem.bridge.select_node(rootItem.nodeId)
                        rootItem.bridge.set_hovered_node(0)
                        
                        if (rootItem.viewportContainer && typeof rootItem.viewportContainer.closeSearchAndOmniBar === "function") {
                            rootItem.viewportContainer.closeSearchAndOmniBar()
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