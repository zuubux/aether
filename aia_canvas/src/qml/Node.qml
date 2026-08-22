import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import Aether.Content 1.0
import "node"

Item {
    id: rootItem

    property var bridge: null
    property Item viewportContainer: null
    property var nodeModel: null

    readonly property var activeBridge: rootItem.bridge ? rootItem.bridge : (typeof canvasBridge !== "undefined" ? canvasBridge : null)

    readonly property int nodeId: nodeModel ? nodeModel.id : 0
    readonly property bool isSelected: bridge ? (bridge.selectedNodeId === nodeId && nodeId > 0) : false
    property bool isHovered: false
    property bool isDwellTriggered: false
    readonly property real focusWeight: nodeModel ? nodeModel.focus : 0.35

    readonly property real focalWidth: {
        if (rootItem.isSelected) {
            if ((rootItem.isImageFile || rootItem.isPdfFile || rootItem.isTableFile) && focalSlateLoader.item && focalSlateLoader.item.hasError) return 520 + 24
            return rootItem.activeBridge ? rootItem.activeBridge.workbenchWidth : 1400
        }
        if (rootItem.isMacroBead) return 16
        if (rootItem.isCompactCapsule) return (nodePill.implicitWidth > 0 ? nodePill.implicitWidth + 24 : 140)
        return 280
    }

    readonly property real focalHeight: {
        if (rootItem.isSelected) {
            if ((rootItem.isImageFile || rootItem.isPdfFile || rootItem.isTableFile) && focalSlateLoader.item && focalSlateLoader.item.hasError) return 340 + 24
            return rootItem.activeBridge ? rootItem.activeBridge.workbenchHeight : 900
        }
        if (rootItem.isMacroBead) return 16
        if (rootItem.isCompactCapsule) return 32
        return 115
    }

    // Relational Focus Classification
    readonly property bool hasActiveFocus: bridge ? (bridge.selectedNodeId > 0) : false
    readonly property bool isDirectNeighbor: hasActiveFocus && focusWeight >= 0.60

    // Aperture & Semantic Zoom Thresholds
    readonly property real currentAperture: bridge ? bridge.aperture : 1.0
    readonly property real macroThreshold: 0.50
    readonly property real secondaryBeadThreshold: 1.15
    readonly property real compactThreshold: 1.20

    // Semantic Zoom Classification
    readonly property int baseTier: currentAperture < 0.40 ? 4 : (currentAperture > 1.00 ? 2 : 3)

    readonly property bool isPreviewMode: !isSelected && (isSearchResult || (isHovered && isDwellTriggered))
    readonly property bool isSlateMode: !isSelected && !isPreviewMode && (baseTier === 2)
    readonly property bool isCapsuleMode: !isSelected && !isPreviewMode && !isSlateMode && (baseTier === 3 || (baseTier === 4 && isHovered))
    readonly property bool isBeadMode: !isSelected && !isPreviewMode && (baseTier === 4 && !isHovered)

    // Old mode properties mapped to new strict flags for compatibility if needed elsewhere
    readonly property bool showPreviewSlate: isPreviewMode
    readonly property bool isMacroBead: isBeadMode
    readonly property bool isCompactCapsule: isCapsuleMode
    readonly property bool isFullToken: isSlateMode

    property real radius: isSelected ? cardRadius :
                          isPreviewMode ? 12 :
                          isSlateMode ? 8 :
                          isBeadMode ? 7 : 16

    // Semantic Extension Colors
    readonly property string ext: nodeModel ? nodeModel.extension.toLowerCase() : ".txt"
    readonly property string filePath: nodeModel ? nodeModel.filePath : ""
    readonly property bool isImageFile: (filePath && typeof bridge !== "undefined") ? bridge.is_image_file(filePath.toString()) : false
    readonly property bool isPdfFile: ext === ".pdf"
    readonly property bool isTableFile: ext === ".csv" || ext === ".tsv"
    readonly property color nodeAccentColor: {
        if (ext === ".py") return "#38bdf8"
        if (ext === ".sh" || ext === ".bash" || ext === ".zsh") return "#fbbf24"
        if (ext === ".md" || ext === ".org" || ext === ".txt") return "#a78bfa"
        if (ext === ".json" || ext === ".yaml" || ext === ".toml") return "#34d399"
        if (ext === ".pdf") return "#ef4444"
        if (ext === ".csv" || ext === ".tsv") return "#fb7185" // rose for table data
        return "#94a3b8"
    }

    readonly property color accentColor: nodeAccentColor

    readonly property string relationType: bridge ? bridge.get_relation_type(nodeId) : ""
    readonly property color relationAccentColor: {
        if (relationType === "semantic") return "#a78bfa" // Violet/Purple accent
        if (relationType === "explicit") return "#38bdf8" // Cyan accent
        if (relationType === "temporal") return "#fbbf24" // Amber/Yellow accent
        return rootItem.nodeAccentColor
    }

    // Downstream Connection Count
    readonly property int downstreamCount: bridge ? bridge.get_downstream_count(nodeId) : 0

    readonly property string snippet: nodeModel ? nodeModel.snippet : ""
    readonly property string initialText: (rootItem.isSelected && textStreamer.content) ? textStreamer.content : snippet
    readonly property int referenceCount: downstreamCount

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

    Timer {
        id: hoverDwellTimer
        interval: 400
        repeat: false
        onTriggered: {
            if (rootItem.isHovered && !rootItem.isSelected) {
                rootItem.isDwellTriggered = true
            }
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
        if (isSelected) {
            if ((isImageFile || isPdfFile || isTableFile) && focalSlateLoader.item && focalSlateLoader.item.hasError) return 520 + 24
            return bridge ? bridge.workbenchWidth : 1400
        }
        if (showPreviewSlate) return 320
        if (isMacroBead) return 16
        if (isCompactCapsule) return (nodePill.implicitWidth > 0 ? nodePill.implicitWidth + 24 : 140)
        return 280
    }

    readonly property real targetHeight: {
        if (isSelected) {
            if ((isImageFile || isPdfFile || isTableFile) && focalSlateLoader.item && focalSlateLoader.item.hasError) return 340 + 24
            return bridge ? bridge.workbenchHeight : 900
        }
        if (showPreviewSlate) return 220
        if (isMacroBead) return 16
        if (isCompactCapsule) return 32
        return 115
    }

    readonly property real cardRadius: {
        if (isSelected) return 14
        if (isMacroBead) return 8
        if (isCompactCapsule) return 16
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
    x: Math.round(isSelected ? (viewportContainer ? (viewportContainer.width - width) / 2 : 0) : (isSearchResult ? (stagedX - width / 2) : (projectedX - width / 2)))
    y: Math.round(isSelected ? (viewportContainer ? (viewportContainer.height - height) / 2 : 0) : (isSearchResult ? (stagedY - height / 2) + verticalOffset : (projectedY - height / 2)))
    width: isSelected ? focalWidth :
           isPreviewMode ? 320 :
           isSlateMode ? 220 :
           isBeadMode ? 14 :
           (nodePill.implicitWidth > 0 ? nodePill.implicitWidth + 24 : 140)

    height: isSelected ? focalHeight :
            isPreviewMode ? 220 :
            isSlateMode ? 64 :
            isBeadMode ? 14 : 32

    Behavior on x {
        enabled: rootItem.isSelected && !nodeMouseArea.isDragging && !resizeMouseArea.isResizing
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }
    Behavior on y {
        enabled: rootItem.isSelected && !nodeMouseArea.isDragging && !resizeMouseArea.isResizing
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }
    Behavior on width {
        enabled: !resizeMouseArea.isResizing
        NumberAnimation { duration: 220; easing.type: Easing.OutQuint }
    }
    Behavior on height {
        enabled: !resizeMouseArea.isResizing
        NumberAnimation { duration: 220; easing.type: Easing.OutQuint }
    }

    // Strict Scale Lock: Keep selected workbench card at exactly 1.0 to ensure 1:1 resize fidelity
    scale: (isSelected ? 1.0 : ((isHovered ? 1.05 : 1.0) * perspectiveScale)) * nodeAura.spawnScaleMultiplier * nodeAura.deleteScaleMultiplier
    Behavior on scale {
        enabled: !nodeAura.isSpawnActive && !nodeAura.isDeleteActive && !rootItem.isSelected && !nodeMouseArea.isDragging && !resizeMouseArea.isResizing
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    // Depth Stacking
    z: isSelected ? 99999 : (isHovered ? 7000 : Math.round((1.0 - depthZ) * 1000 + focusWeight * 100))

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
        var baseOpacity = 1.0;
        if (viewportContainer && viewportContainer.searchActive) {
            baseOpacity = isSearchResult ? 1.0 : 0.15;
        } else {
            baseOpacity = (isSelected ? 1.0 : (isHovered ? 1.0 : Math.max(0.0, focusWeight * (1.0 - depthZ * 0.35)))) * wingSqueezeOpacity * macroOpacityFade;
        }
        return baseOpacity * nodeAura.spawnOpacityMultiplier * nodeAura.deleteOpacityMultiplier
    }
    Behavior on opacity {
        enabled: !nodeAura.isSpawnActive && !nodeAura.isDeleteActive
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    Rectangle {
        id: cardBody
        anchors.fill: parent
        radius: rootItem.radius
        clip: true

        Behavior on radius {
            NumberAnimation { duration: 220; easing.type: Easing.OutQuint }
        }

        color: rootItem.isSelected ? "#0c0e12" : (rootItem.isMacroBead ? rootItem.nodeAccentColor : (rootItem.isHovered ? "#161c28" : "#0a0c10"))
        border.color: rootItem.isSearchResult ? "#64d2ff" : (rootItem.isSelected ? "#38bdf8" : (rootItem.isMacroBead ? Qt.lighter(rootItem.nodeAccentColor, 1.3) : (rootItem.isHovered ? rootItem.nodeAccentColor : (rootItem.isDirectNeighbor ? rootItem.relationAccentColor : "#1e2430"))))
        border.width: rootItem.isSearchResult ? 2.5 : (rootItem.isMacroBead ? 1.5 : (rootItem.isSelected || rootItem.isHovered ? 1.5 : 1.0))
        antialiasing: true
        smooth: true

        Behavior on color { ColorAnimation { duration: 180 } }
        Behavior on border.color { ColorAnimation { duration: 180 } }

        // NodeAura Component Integration
        NodeAura {
            id: nodeAura
            isNew: (typeof model !== "undefined" && model) ? (model.isNew || false) : (nodeModel ? nodeModel.isNew || false : false)
            isDeleted: (typeof model !== "undefined" && model) ? (model.isDeleted || false) : (nodeModel ? nodeModel.isDeleted || false : false)
            accentColor: rootItem.accentColor
            radius: rootItem.radius
        }

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
        NodePill {
            id: nodePill
            anchors.fill: parent
            fileName: (typeof model !== "undefined" && model && model.fileName) ? model.fileName : (rootItem.nodeModel ? rootItem.nodeModel.fileName : "")
            extensionStr: (typeof model !== "undefined" && model && model.extension) ? model.extension : (rootItem.ext || "")
            archetype: (typeof model !== "undefined" && model && model.archetype) ? model.archetype : (rootItem.nodeModel ? rootItem.nodeModel.archetype : "")
            accentColor: rootItem.accentColor
            cardRadius: rootItem.radius
            isHovered: rootItem.isHovered
            isSearchResult: rootItem.isSearchResult
            visible: rootItem.isCapsuleMode
            opacity: rootItem.isCapsuleMode ? 1.0 : 0.0
        }

        // =====================================================================
        // TIER 2: Orbital Horizon Token
        // =====================================================================
        Item {
            id: tokenView
            anchors.fill: parent
            visible: rootItem.isSlateMode
            opacity: rootItem.isSlateMode ? 1.0 : 0.0

            Column {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                Row {
                    spacing: 8
                    width: parent.width

                    Rectangle {
                        width: 18
                        height: 16
                        radius: 3
                        color: rootItem.accentColor || "#00E5FF"
                        Text {
                            anchors.centerIn: parent
                            text: (rootItem.nodeModel && rootItem.nodeModel.extension ? rootItem.nodeModel.extension : "md").replace(".", "").toUpperCase()
                            font.pixelSize: 8
                            font.bold: true
                            color: "#0D1117"
                        }
                    }

                    Text {
                        text: rootItem.nodeModel ? rootItem.nodeModel.fileName : ""
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                        color: "#E6EDF3"
                        elide: Text.ElideRight
                        width: parent.width - 26
                    }
                }

                Text {
                    text: rootItem.nodeModel && rootItem.nodeModel.filePath ? rootItem.nodeModel.filePath : ""
                    font.pixelSize: 10
                    color: "#8B949E"
                    elide: Text.ElideMiddle
                    width: parent.width
                }
            }
        }

        MmapTextStreamer {
            id: textStreamer
        }

        Connections {
            target: rootItem
            function onIsSelectedChanged() {
                if (rootItem.isSelected && rootItem.nodeModel && rootItem.nodeModel.filePath) {
                    if (rootItem.nodeModel.filePath !== textStreamer.filePath) {
                        textStreamer.load_file(rootItem.nodeModel.filePath, -1);
                    }
                }
            }
        }

        NodePreview {
            id: nodePreview
            anchors.fill: parent
            fileName: (typeof model !== "undefined" && model && model.fileName) ? model.fileName : (rootItem.nodeModel ? rootItem.nodeModel.fileName : "")
            snippetText: (typeof model !== "undefined" && model && (model.snippet || model.summary)) ? (model.snippet || model.summary) : (rootItem.nodeModel ? rootItem.nodeModel.snippet : "")
            archetype: (typeof model !== "undefined" && model && model.archetype) ? model.archetype : (rootItem.nodeModel ? rootItem.nodeModel.archetype : "")
            accentColor: rootItem.accentColor
            cardRadius: rootItem.radius
            isSearchResult: rootItem.isSearchResult
            isHovered: rootItem.isHovered
            showPreviewSlate: rootItem.showPreviewSlate
            visible: rootItem.isPreviewMode
            opacity: rootItem.isPreviewMode ? 1.0 : 0.0
        }

        // =====================================================================
        // TIER 1: Editor / Preview Slate
        // =====================================================================
        Loader {
            id: focalSlateLoader
            focus: rootItem.isSelected
            anchors.centerIn: parent
            width: rootItem.isSelected ? (parent.width - 24) : 320
            height: rootItem.isSelected ? (parent.height - 24) : 220
            active: rootItem.isSelected
            visible: opacity > 0.01
            opacity: rootItem.isSelected ? 1.0 : 0.0
            source: rootItem.isImageFile ? "ImageSlate.qml" : (rootItem.isPdfFile ? "PdfSlate.qml" : (rootItem.isTableFile ? "TableSlate.qml" : "PreviewSlate.qml"))
            z: 10
            
            Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutQuad } }

            onLoaded: {
                if (item) {
                    if (item.hasOwnProperty("width")) item.width = Qt.binding(function() { return focalSlateLoader.width });
                    if (item.hasOwnProperty("height")) item.height = Qt.binding(function() { return focalSlateLoader.height });
                }
            }

            Binding { target: focalSlateLoader.item; property: "nodeId"; value: rootItem.nodeId; restoreMode: Binding.RestoreBinding }
            Binding { target: focalSlateLoader.item; property: "isSelected"; value: rootItem.isSelected; restoreMode: Binding.RestoreBinding }
            Binding {
                target: focalSlateLoader.item
                property: "viewportContainer"
                value: rootItem.viewportContainer
                when: focalSlateLoader.item !== null && typeof focalSlateLoader.item.viewportContainer !== "undefined"
                restoreMode: Binding.RestoreBinding
            }
            Binding { target: focalSlateLoader.item; property: "archetype"; value: rootItem.nodeModel ? rootItem.nodeModel.archetype : "document"; restoreMode: Binding.RestoreBinding }
            Binding {
                target: focalSlateLoader.item
                property: "snippet"
                value: rootItem.snippet
                when: !rootItem.isImageFile && !rootItem.isPdfFile && !rootItem.isTableFile && focalSlateLoader.item !== null
                restoreMode: Binding.RestoreBinding
            }
            Binding {
                target: focalSlateLoader.item
                property: "initialText"
                value: rootItem.initialText
                when: !rootItem.isImageFile && !rootItem.isPdfFile && !rootItem.isTableFile && focalSlateLoader.item !== null
                restoreMode: Binding.RestoreBinding
            }
            Binding { target: focalSlateLoader.item; property: "fileName"; value: rootItem.nodeModel ? rootItem.nodeModel.fileName : ""; restoreMode: Binding.RestoreBinding }
            Binding { target: focalSlateLoader.item; property: "filePath"; value: rootItem.nodeModel ? rootItem.nodeModel.filePath : ""; restoreMode: Binding.RestoreBinding }
            Binding { target: focalSlateLoader.item; property: "sizeFormatted"; value: rootItem.nodeModel ? (rootItem.nodeModel.sizeBytes / 1024).toFixed(1) + " KB" : "0 KB"; restoreMode: Binding.RestoreBinding }
            Binding {
                target: focalSlateLoader.item
                property: "referenceCount"
                value: rootItem.referenceCount
                when: !rootItem.isImageFile && !rootItem.isPdfFile && !rootItem.isTableFile && focalSlateLoader.item !== null
                restoreMode: Binding.RestoreBinding
            }
            Binding { target: focalSlateLoader.item; property: "accentColor"; value: rootItem.nodeAccentColor; restoreMode: Binding.RestoreBinding }
            Binding {
                target: focalSlateLoader.item
                property: "bridge"
                value: (typeof bridge !== "undefined" ? bridge : rootItem.bridge)
                when: focalSlateLoader.item !== null && ("bridge" in focalSlateLoader.item || typeof focalSlateLoader.item.bridge !== "undefined")
                restoreMode: Binding.RestoreBinding
            }
        }

        // =====================================================================
        // Main Card Drag & Interaction Handler
        // =====================================================================
        MouseArea {
            id: nodeMouseArea
            z: 99
            anchors.fill: parent
            anchors.margins: -16 // Hit-box stabilization padding
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            cursorShape: Qt.PointingHandCursor
            // Disable drag handling when clicking near the bottom-right resize corner on selected cards
            enabled: !resizeMouseArea.isResizing && !rootItem.isSelected
            visible: !rootItem.isSelected

            property real pressStartX: 0
            property real pressStartY: 0
            property real dragOffsetX: 0
            property real dragOffsetY: 0
            property bool isDragging: false
            property bool isDragMoved: false

            onEntered: {
                rootItem.isHovered = true
                rootItem.isDwellTriggered = false
                if (!rootItem.isSearchResult && !rootItem.isSelected) {
                    hoverDwellTimer.restart()
                }
                if (rootItem.bridge && !rootItem.isSelected) {
                    rootItem.bridge.set_hovered_node(rootItem.nodeId)
                }
            }

            onExited: {
                rootItem.isHovered = false
                rootItem.isDwellTriggered = false
                hoverDwellTimer.stop()
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
                            Math.max(480, Math.min(2600, startW + deltaX)),
                            Math.max(320, Math.min(1600, startH + deltaY))
                        )
                    }
                }

                onReleased: { isResizing = false }
                onCanceled: { isResizing = false }
            }
        }
    }
}