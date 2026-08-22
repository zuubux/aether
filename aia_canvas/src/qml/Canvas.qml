import QtQuick
import QtQuick.Controls

Window {
    id: root
    width: 2560
    height: 1440
    title: "Aether Canvas"
    color: "#07080b"
    property bool showDiagnostics: false
    
    screen: Qt.application.screens[targetScreenIdx !== undefined ? targetScreenIdx : 0]
    visibility: (isFullscreen || isSpanAll) ? Window.FullScreen : Window.Windowed

    // Global Hotkeys
    Shortcut {
        sequence: "Ctrl+Q"
        onActivated: Qt.quit()
    }

    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (canvasBridge && canvasBridge.selectedNodeId > 0) {
                canvasBridge.select_node(0)
            } else if (omniBar.active) {
                if (omniBar.textLength > 0) {
                    omniBar.clearTextAndCancel()
                } else {
                    omniBar.active = false
                    if (canvasViewport.searchActive && canvasBridge) {
                        canvasBridge.clear_search()
                    }
                }
            } else if (canvasViewport.searchActive) {
                if (canvasBridge) {
                    canvasBridge.clear_search()
                }
            } else {
                Qt.quit()
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+Space"
        context: Qt.ApplicationShortcut
        onActivated: {
            if (omniBar.active) {
                omniBar.active = false
            } else {
                omniBar.active = true
            }
        }
    }
    Shortcut {
        sequence: "F3"
        onActivated: showDiagnostics = !showDiagnostics
    }
    
    Shortcut {
        sequence: "Ctrl+I"
        onActivated: {
            if (intentEngine) {
                // Summoning test trigger
                intentEngine.process_query("database architecture")
            }
        }
    }

    // Viewport Dimension Sync
    Component.onCompleted: syncViewportDimensions()
    onWidthChanged: syncViewportDimensions()
    onHeightChanged: syncViewportDimensions()

    function syncViewportDimensions() {
        if (canvasBridge) {
            canvasBridge.update_viewport_dimensions(root.width, root.height)
        }
    }

    Item {
        id: canvasSpace
        anchors.fill: parent
        z: 100

        // Background Horizon Plane & Iso-lines
        HorizonGrid {
            z: -1
        }

        // Void Click & Aperture Scroll Controller
        MouseArea {
            id: voidArea
            anchors.fill: parent

            onClicked: function(mouse) {
                if (canvasBridge) {
                    canvasBridge.select_node(0)
                }
            }

            onWheel: function(wheel) {
                if (canvasBridge) {
                    var delta = wheel.angleDelta.y > 0 ? 0.06 : -0.06
                    canvasBridge.adjust_aperture(delta)
                }
            }
        }

        OmniBar {
            id: omniBar
            anchors.horizontalCenter: parent.horizontalCenter
            z: 10000

            onQuerySubmitted: function(text) {
                if (canvasBridge) {
                    canvasBridge.submit_query(text)
                }
            }

            onCancelQuery: {
                if (canvasBridge) {
                    canvasBridge.clear_search()
                }
            }

            onDismissed: {
                active = false
                if (canvasBridge) {
                    canvasBridge.clear_search()
                }
            }
        }

        Item {
            id: canvasViewport
            anchors.fill: parent

            property real canvasGlobalTime: 0.0
            FrameAnimation {
                running: canvasViewport.searchActive
                onTriggered: canvasViewport.canvasGlobalTime += frameTime * 1000.0
            }

            property var nodeRegistry: ({})
            property var searchResultIds: []
            property bool searchActive: false

            Connections {
                target: canvasBridge
                function onSearchResultsReceived(results) {
                    canvasViewport.searchResultIds = results
                    canvasViewport.searchActive = true

                    var sumX = 0
                    var sumY = 0
                    var count = 0

                    for (var i = 0; i < results.length; i++) {
                        var node = canvasViewport.getNode(results[i])
                        if (node) {
                            sumX += node.x + node.width / 2
                            sumY += node.y + node.height / 2
                            count++
                        }
                    }

                    if (count > 0 && canvasBridge) {
                        var shelfY = root.height * 0.35;
                        canvasBridge.set_staged_nodes(results, root.width, shelfY);
                    }
                }

                function onSearchCleared() {
                    canvasViewport.searchActive = false
                    canvasViewport.searchResultIds = []
                    // Retain target defaults explicitly
                    canvasViewport.targetX = 0
                    canvasViewport.targetY = 0
                    canvasViewport.targetScale = 1.0
                }
            }

            property real targetX: 0
            property real targetY: 0
            property real targetScale: 1.0

            x: targetX
            y: targetY
            scale: targetScale

            Behavior on x { NumberAnimation { duration: 450; easing.type: Easing.OutCubic } }
            Behavior on y { NumberAnimation { duration: 450; easing.type: Easing.OutCubic } }
            Behavior on scale { NumberAnimation { duration: 450; easing.type: Easing.OutCubic } }
            property int registryEpoch: 0

            function registerNode(id, item) {
                nodeRegistry[id] = item
                registryEpoch++
            }

            function unregisterNode(id) {
                delete nodeRegistry[id]
                registryEpoch++
            }

            function getNode(id) {
                var _dummy = registryEpoch
                return nodeRegistry[id] || null
            }

            function closeSearchAndOmniBar() {
                omniBar.active = false
                omniBar.visible = false
                omniBar.clearTextAndCancel()
                if (searchActive && canvasBridge) {
                    canvasBridge.clear_search()
                }
                canvasSpace.forceActiveFocus()
            }
            
            // 1. Atmospheric Cluster Halos (Background Layer)
            Repeater {
                model: canvasBridge ? canvasBridge.clusterHalos : []

                ClusterHalo {
                    required property var modelData

                    centerX: modelData.centerX
                    centerY: modelData.centerY
                    
                    // Replaced haloRadius with independent width/height mapping
                    haloWidth: modelData.width
                    haloHeight: modelData.height
                    
                    haloColor: modelData.color
                    isFocalCluster: modelData.isFocalCluster
                    nodeCount: modelData.nodeCount
                    currentAperture: canvasBridge ? canvasBridge.aperture : 1.0
                    densityWeight: modelData.densityWeight !== undefined ? modelData.densityWeight : 1.0
                }
            }

            // 2. Dynamic Synaptic Tendrils (Midground Layer)
            Repeater {
                model: canvasBridge ? canvasBridge.edges : []

                Tendril {
                    required property var modelData

                    sourceId: modelData.sourceId
                    targetId: modelData.targetId
                    edgeType: modelData.edgeType
                    weight: modelData.weight
                    currentAperture: canvasBridge ? canvasBridge.aperture : 1.0
                    selectedNodeId: canvasBridge ? canvasBridge.selectedNodeId : 0
                    hoveredNodeId: canvasBridge ? canvasBridge.hoveredNodeId : 0
                    sourceNode: canvasViewport.getNode(modelData.sourceId)
                    targetNode: canvasViewport.getNode(modelData.targetId)
                }
            }

            // 3. Cards & Constellations (Foreground Layer)
            Repeater {
                model: canvasBridge ? canvasBridge.nodes : []

                Node {
                    id: nodeItem
                    required property var modelData

                    bridge: canvasBridge
                    viewportContainer: canvasViewport
                    nodeModel: modelData

                    Component.onCompleted: {
                        canvasViewport.registerNode(modelData.id, nodeItem)
                    }
                    Component.onDestruction: {
                        canvasViewport.unregisterNode(modelData.id)
                    }
                }
            }
        }
    }

    // =========================================================================
    // Bottom Controls: IPC Status & Aperture Gauge
    // =========================================================================
    Row {
        id: bottomHud
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 20
        spacing: 12
        z: 10

        // IPC Status Pill
        Rectangle {
            width: 130
            height: 30
            radius: 15
            color: "#0e1117"
            border.color: (canvasBridge && canvasBridge.isConnected) ? "#10b981" : "#475569"
            border.width: 1
            opacity: 0.85

            Row {
                anchors.centerIn: parent
                spacing: 8

                Rectangle {
                    width: 7
                    height: 7
                    radius: 3.5
                    color: (canvasBridge && canvasBridge.isConnected) ? "#10b981" : "#64748b"
                    anchors.verticalCenter: parent.verticalCenter

                    SequentialAnimation on opacity {
                        running: canvasBridge ? canvasBridge.isConnected : false
                        loops: Animation.Infinite
                        PropertyAnimation { to: 0.4; duration: 1200; easing.type: Easing.InOutSine }
                        PropertyAnimation { to: 1.0; duration: 1200; easing.type: Easing.InOutSine }
                    }
                }

                Text {
                    text: (canvasBridge && canvasBridge.isConnected) ? "Weaver Live" : "Standalone"
                    color: (canvasBridge && canvasBridge.isConnected) ? "#e2e8f0" : "#94a3b8"
                    font.family: "Monospace"
                    font.pixelSize: 10
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // Aperture Gauge Pill
        Rectangle {
            width: 140
            height: 30
            radius: 15
            color: "#0e1117"
            border.color: "#1e293b"
            border.width: 1
            opacity: 0.85

            Row {
                anchors.centerIn: parent
                spacing: 8

                Text {
                    text: "Aperture"
                    color: "#64748b"
                    font.family: "Monospace"
                    font.pixelSize: 10
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: Math.round((canvasBridge ? canvasBridge.aperture : 1.0) * 100) + "%"
                    color: "#38bdf8"
                    font.family: "Monospace"
                    font.pixelSize: 11
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }

    // =========================================================================
    // Diagnostic HUD (F3 Toggle)
    // =========================================================================
    Rectangle {
        visible: root.showDiagnostics
        width: 270
        height: 270
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 20
        color: "#0a0c10"
        border.color: "#334155"
        border.width: 1
        radius: 8
        opacity: 0.90
        z: 9000

        Column {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            Text {
                text: "AIA CANVAS SRE HUD"
                color: "#f8fafc"
                font.family: "Monospace"
                font.pixelSize: 12
                font.bold: true
            }

            Rectangle { width: parent.width; height: 1; color: "#1e293b" }

            Grid {
                columns: 2
                spacing: 8
                rowSpacing: 6

                Text { text: "Nodes:"; color: "#94a3b8"; font.family: "Monospace"; font.pixelSize: 11; width: 120 }
                Text { text: canvasBridge ? canvasBridge.activeNodeCount : 0; color: "#38bdf8"; font.family: "Monospace"; font.pixelSize: 11; font.bold: true }

                Text { text: "Edges (Render):"; color: "#94a3b8"; font.family: "Monospace"; font.pixelSize: 11; width: 120 }
                Text { text: canvasBridge ? canvasBridge.activeEdgeCount : 0; color: "#fbbf24"; font.family: "Monospace"; font.pixelSize: 11; font.bold: true }

                Text { text: "Physics Step:"; color: "#94a3b8"; font.family: "Monospace"; font.pixelSize: 11; width: 120 }
                Text { 
                    text: canvasBridge ? canvasBridge.physicsFrametime.toFixed(2) + " ms" : "0.00 ms"
                    color: (canvasBridge && canvasBridge.physicsFrametime > 6.5) ? "#ef4444" : "#10b981" 
                    font.family: "Monospace"; font.pixelSize: 11; font.bold: true 
                }

                Text { text: "Backend Socket:"; color: "#94a3b8"; font.family: "Monospace"; font.pixelSize: 11; width: 120 }
                Text { 
                    text: (canvasBridge && canvasBridge.isConnected) ? "CONNECTED" : "OFFLINE" 
                    color: (canvasBridge && canvasBridge.isConnected) ? "#10b981" : "#ef4444"
                    font.family: "Monospace"; font.pixelSize: 11; font.bold: true 
                }
            }

            Rectangle { width: parent.width; height: 1; color: "#1e293b" }

            Text {
                text: "TENDRIL COLOR KEY"
                color: "#94a3b8"
                font.family: "Monospace"
                font.pixelSize: 10
                font.bold: true
            }

            Column {
                spacing: 5
                width: parent.width

                Row {
                    spacing: 8
                    Rectangle { width: 14; height: 3; radius: 1.5; color: "#38bdf8"; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Explicit ([[WikiLinks]])"; color: "#e2e8f0"; font.family: "Monospace"; font.pixelSize: 10 }
                }

                Row {
                    spacing: 8
                    Rectangle { width: 14; height: 3; radius: 1.5; color: "#a78bfa"; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Semantic (Embeddings)"; color: "#e2e8f0"; font.family: "Monospace"; font.pixelSize: 10 }
                }

                Row {
                    spacing: 8
                    Rectangle { width: 14; height: 3; radius: 1.5; color: "#fbbf24"; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Temporal (Co-edit / Session)"; color: "#e2e8f0"; font.family: "Monospace"; font.pixelSize: 10 }
                }

                Row {
                    spacing: 8
                    Rectangle { width: 14; height: 3; radius: 1.5; color: "#67e8f9"; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Hover / Active Bloom"; color: "#e2e8f0"; font.family: "Monospace"; font.pixelSize: 10 }
                }
            }
        }
    }
}