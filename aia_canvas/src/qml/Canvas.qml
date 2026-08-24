import QtQuick
import QtQuick.Controls
import "hud"
import "search"

Window {
    id: canvasRoot
    width: 2560
    height: 1440
    title: "Aether Canvas"
    color: "#07080b"
    property bool showDiagnostics: false

    readonly property Item focalCardItem: (canvasBridge && canvasBridge.selectedNodeId > 0) ? canvasViewport.getNode(canvasBridge.selectedNodeId) : null

    readonly property int nodeCount: (canvasBridge && canvasBridge.nodes) ? Math.max(1, canvasBridge.nodes.length) : 1
    readonly property real viewportArea: width * height
    readonly property real pixelBudgetPerNode: (viewportArea * Math.pow(canvasBridge ? canvasBridge.aperture : 1.0, 2)) / nodeCount

    readonly property string ambientTier: {
        var ap = canvasBridge ? canvasBridge.aperture : 1.0;
        if (ap < 0.45 || pixelBudgetPerNode < 15000) return "TIER_4";
        if (ap >= 1.6 && pixelBudgetPerNode > 120000) return "TIER_2";
        return "TIER_3";
    }

    Binding {
        target: canvasBridge
        property: "focalCardWidth"
        value: focalCardItem ? focalCardItem.width : 880.0
        when: canvasBridge !== null && focalCardItem !== null
    }
    Binding {
        target: canvasBridge
        property: "focalCardHeight"
        value: focalCardItem ? focalCardItem.height : 600.0
        when: canvasBridge !== null && focalCardItem !== null
    }
    
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
                    omniBar.dismiss()
                    if (searchShelf.searchActive && canvasBridge) {
                        canvasBridge.clear_search()
                    }
                }
            } else if (searchShelf.searchActive) {
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
        context: Qt.ApplicationShortcut // Global across all child focus scopes
        onActivated: {
            if (typeof omniBar !== "undefined" && omniBar) {
                if (omniBar.visible) {
                    omniBar.dismiss();
                } else {
                    omniBar.open();
                }
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
    Component.onCompleted: {
        syncViewportDimensions()
        if (canvasBridge && typeof canvasBridge.notify_ui_ready === "function") {
            canvasBridge.notify_ui_ready()
        }
    }
    onWidthChanged: syncViewportDimensions()
    onHeightChanged: syncViewportDimensions()

    function syncViewportDimensions() {
        if (canvasBridge) {
            canvasBridge.update_viewport_dimensions(canvasRoot.width, canvasRoot.height)
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
                if (searchShelf.searchActive && canvasBridge) {
                    canvasBridge.clear_search()
                } else if (canvasBridge) {
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

        // Ambient Canvas Dimming Scrim
        Rectangle {
            id: searchScrim
            objectName: "searchScrim"
            anchors.fill: parent
            z: 9000
            color: "#07080B"
            opacity: (searchShelf.searchActive || (omniBar.active && omniBar.textLength > 0)) ? 0.72 : 0.0
            visible: opacity > 0.001

            Behavior on opacity {
                NumberAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing }
            }

            MouseArea {
                anchors.fill: parent
                preventStealing: true
                onClicked: {
                    if (omniBar.active) {
                        omniBar.dismiss()
                    }
                    if (canvasBridge) {
                        canvasBridge.clear_search()
                    }
                }
            }
        }

        OmniBar {
            id: omniBar
            searchShelf: searchShelf
            anchors.horizontalCenter: parent.horizontalCenter
            z: 10000

            onQuerySubmitted: function(text) {
                if (canvasBridge) {
                    canvasBridge.execute_intent(text)
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

        SearchShelf {
            id: searchShelf
            objectName: "searchShelf"
            z: 10000
            viewport: canvasViewport
            omniBar: omniBar
        }

        Item {
            id: canvasViewport
            anchors.fill: parent

            property real canvasGlobalTime: 0.0
            FrameAnimation {
                running: true
                onTriggered: {
                    canvasViewport.canvasGlobalTime += frameTime * 1000.0
                    if (canvasBridge) {
                        canvasBridge.record_frame(frameTime * 1000.0)
                    }
                }
            }

            property var nodeRegistry: ({})

            Connections {
                target: typeof canvasBridge !== "undefined" ? canvasBridge : null
                
                function onSelectedNodeChanged(nodeId) {
                    if (nodeId > 0) {
                        // Trigger focal camera zoom/pan to center the selected node in the viewport
                        canvasViewport.targetX = 0;
                        canvasViewport.targetY = 0;
                        canvasViewport.targetScale = 1.0;
                    }
                }

                function onNodeRemoved(nodeId) {
                    console.log("QML: Node with ID " + nodeId + " was removed dynamically from canvas view.")
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
            Item {
                id: tendrilLayer
                anchors.fill: parent
                z: 10

                Repeater {
                    // In focal mode, ONLY feed the deduplicated focalEdges list
                    model: (canvasBridge && canvasBridge.selectedNodeId > 0) ? canvasBridge.focalEdges : (canvasBridge ? canvasBridge.ambientEdges : [])

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
            }

            // 3. Cards & Constellations (Foreground Layer)
            Item {
                id: nodeLayer
                anchors.fill: parent
                z: 15

                Repeater {
                    model: canvasBridge ? canvasBridge.nodes : []

                    Node {
                        id: nodeItem
                        required property var modelData

                        bridge: canvasBridge
                        viewportContainer: canvasViewport
                        nodeModel: modelData
                        ambientTier: canvasRoot.ambientTier

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

        CanvasHud {
            id: bottomHud
            objectName: "bottomHud"
        }

        DiagnosticsOverlay {
            id: diagnosticsOverlay
            objectName: "diagnosticsOverlay"
            showDiagnostics: canvasRoot.showDiagnostics
        }
    }
}
