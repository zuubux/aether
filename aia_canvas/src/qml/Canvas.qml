import QtQuick
import QtQuick.Controls
import "hud"
import "search"
import "bar"

Window {
    id: canvasRoot
    width: 2560
    height: 1440
    title: "Aether Canvas"
    color: "#07080b"
    property bool showDiagnostics: false
    readonly property alias omniBar: omniBar

    readonly property Item focalCardItem: (canvasBridge && canvasBridge.selectedNodeId > 0 && !isSearchActive) ? canvasViewport.getNode(canvasBridge.selectedNodeId) : null

    readonly property int nodeCount: (canvasBridge && canvasBridge.nodes) ? Math.max(1, canvasBridge.nodes.length) : 1
    readonly property real viewportArea: width * height
    readonly property real pixelBudgetPerNode: (viewportArea * Math.pow(canvasBridge ? canvasBridge.aperture : 1.0, 2)) / nodeCount

    readonly property string ambientTier: {
        var ap = canvasBridge ? canvasBridge.aperture : 1.0;
        if (ap < 0.45 || pixelBudgetPerNode < 15000) return "TIER_4";
        if (ap >= 1.6 && pixelBudgetPerNode > 120000) return "TIER_2";
        return "TIER_3";
    }

    readonly property var activeSearchMatchIds: {
        var ids = [];
        if (searchShelf && searchShelf.searchResultIds && searchShelf.searchResultIds.length > 0) {
            ids = searchShelf.searchResultIds;
        } else if (omniBar && omniBar.resultsList && omniBar.resultsList.length > 0) {
            for (var i = 0; i < omniBar.resultsList.length; i++) {
                var item = omniBar.resultsList[i];
                var nid = item.node_id !== undefined ? item.node_id : item.id;
                if (nid !== undefined && nid !== null) {
                    var intId = parseInt(nid);
                    if (!isNaN(intId) && ids.indexOf(intId) < 0) ids.push(intId);
                }
            }
        }
        return ids;
    }

    readonly property bool isSearchActive: (omniBar && omniBar.active && omniBar.textLength > 0 && !omniBar.isConversationalMode) || (searchShelf && searchShelf.searchActive)

    readonly property var directConnectedMatchIds: {
        if (!isSearchActive || !activeSearchMatchIds || activeSearchMatchIds.length === 0) return ({});
        var map = ({});
        for (var i = 0; i < activeSearchMatchIds.length; i++) {
            var mId = activeSearchMatchIds[i];
            map[mId] = true;
        }
        var edges = canvasBridge ? (canvasBridge.selectedNodeId > 0 ? canvasBridge.focalEdges : canvasBridge.ambientEdges) : [];
        if (edges) {
            for (var j = 0; j < edges.length; j++) {
                var e = edges[j];
                if (map[e.sourceId]) map[e.targetId] = true;
                if (map[e.targetId]) map[e.sourceId] = true;
            }
        }
        return map;
    }

    onIsSearchActiveChanged: {
        if (isSearchActive) {
            if (!canvasViewport.isCameraCached) {
                canvasViewport.preSearchX = canvasViewport.targetX;
                canvasViewport.preSearchY = canvasViewport.targetY;
                canvasViewport.preSearchScale = canvasViewport.targetScale;
                canvasViewport.isCameraCached = true;
            }
        } else {
            if (canvasViewport.isCameraCached) {
                canvasViewport.targetX = canvasViewport.preSearchX;
                canvasViewport.targetY = canvasViewport.preSearchY;
                canvasViewport.targetScale = canvasViewport.preSearchScale;
                canvasViewport.isCameraCached = false;
            }
        }
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
                canvasBridge.node.select_node(0)
            } else if (omniBar.active) {
                if (omniBar.textLength > 0) {
                    omniBar.clearTextAndCancel()
                } else {
                    omniBar.dismiss()
                    if (searchShelf.searchActive && canvasBridge) {
                        canvasBridge.search.clear_search()
                    }
                }
            } else if (searchShelf.searchActive) {
                if (canvasBridge) {
                    canvasBridge.search.clear_search()
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
                if (omniBar.active) {
                    omniBar.dismiss();
                } else {
                    omniBar.open();
                }
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+K"
        context: Qt.ApplicationShortcut
        onActivated: {
            if (typeof omniBar !== "undefined" && omniBar) {
                if (omniBar.active) {
                    omniBar.dismiss();
                } else {
                    omniBar.open();
                }
            }
        }
    }

    Shortcut {
        sequence: "/"
        context: Qt.ApplicationShortcut
        onActivated: {
            if (typeof omniBar !== "undefined" && omniBar && !omniBar.active) {
                omniBar.open();
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
            canvasBridge.canvas.update_viewport_dimensions(canvasRoot.width, canvasRoot.height)
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
                    canvasBridge.search.clear_search()
                } else if (canvasBridge) {
                    canvasBridge.node.select_node(0)
                }
            }

            onWheel: function(wheel) {
                if (canvasBridge) {
                    var delta = wheel.angleDelta.y > 0 ? 0.06 : -0.06
                    canvasBridge.canvas.adjust_aperture(delta)
                }
            }
        }

        Item {
            id: canvasViewport
            objectName: "canvasViewport"
            width: parent ? parent.width : 2560
            height: parent ? parent.height : 1440
            transformOrigin: Item.TopLeft
            z: 1

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
                        canvasViewport.isCameraCached = false;
                        canvasViewport.steerCameraToNode(nodeId, true);
                    }
                }

                function onNodeRemoved(nodeId) {
                    console.log("QML: Node with ID " + nodeId + " was removed dynamically from canvas view.")
                }
            }

            property real targetX: 0
            property real targetY: 0
            property real targetScale: 1.0

            property real preSearchX: 0
            property real preSearchY: 0
            property real preSearchScale: 1.0
            property bool isCameraCached: false

            onTargetXChanged: console.log("[CameraViewport] targetX animated to:", targetX)
            onTargetYChanged: console.log("[CameraViewport] targetY animated to:", targetY)

            Connections {
                target: searchShelf
                function onFocusedNodeIdChanged() {
                    if (searchShelf.searchActive && searchShelf.focusedNodeId > 0) {
                        canvasViewport.steerCameraToNode(searchShelf.focusedNodeId);
                    }
                }
            }

            function steerCameraToNode(nodeId) {
                var force = (arguments.length > 1 && arguments[1] === true);
                if (!nodeId || nodeId <= 0) return;
                var nx = 0;
                var ny = 0;
                var nodeItem = getNode(nodeId);
                if (nodeItem) {
                    nx = nodeItem.x + (nodeItem.width > 0 ? nodeItem.width / 2 : 0);
                    ny = nodeItem.y + (nodeItem.height > 0 ? nodeItem.height / 2 : 0);
                } else if (canvasBridge && typeof canvasBridge.get_node === "function") {
                    var bNode = canvasBridge.get_node(nodeId);
                    if (bNode && bNode.x !== undefined && bNode.y !== undefined) {
                        nx = bNode.x;
                        ny = bNode.y;
                    } else {
                        console.log("[CameraSteer] Node " + nodeId + " position not available in canvasBridge store.");
                        return;
                    }
                } else {
                    console.log("[CameraSteer] Node " + nodeId + " not found in registry or store.");
                    return;
                }

                var screenX = targetX + nx * targetScale;
                var screenY = targetY + ny * targetScale;

                var vw = canvasRoot.width;
                var vh = canvasRoot.height;

                var dzLeft = vw * 0.25;
                var dzRight = vw * 0.75;
                var dzTop = vh * 0.20;
                var dzBottom = vh * 0.70;

                var startX = targetX;
                var startY = targetY;

                if (force || screenX < dzLeft || screenX > dzRight || screenY < dzTop || screenY > dzBottom) {
                    var destX = -(nx * targetScale) + (vw / 2);
                    var destY = -(ny * targetScale) + (vh / 2);
                    console.log("[CameraSteer] Steering camera to node " + nodeId + " at world (" + nx.toFixed(1) + ", " + ny.toFixed(1) + "). startX/Y: (" + startX.toFixed(1) + ", " + startY.toFixed(1) + ") -> targetX/Y: (" + destX.toFixed(1) + ", " + destY.toFixed(1) + ") | force=" + force);
                    targetX = destX;
                    targetY = destY;
                } else {
                    console.log("[CameraSteer] Node " + nodeId + " at world (" + nx.toFixed(1) + ", " + ny.toFixed(1) + ") inside deadzone. startX/Y: (" + startX.toFixed(1) + ", " + startY.toFixed(1) + ")");
                }
            }

            x: targetX
            y: targetY
            scale: targetScale

            Behavior on x { NumberAnimation { duration: 250; easing.type: Easing.OutQuint } }
            Behavior on y { NumberAnimation { duration: 250; easing.type: Easing.OutQuint } }
            Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutQuint } }
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
                        isSearchActive: canvasRoot.isSearchActive
                        isSearchMatchOrConnected: canvasRoot.directConnectedMatchIds[modelData.id] === true
                        omniBar: canvasRoot.omniBar

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

        // Dedicated Top-Level Viewport HUD Overlay Layer
        Item {
            id: hudOverlayLayer
            objectName: "hudOverlayLayer"
            anchors.fill: parent
            z: 1000  // Guaranteed elevation above all world-space items

            readonly property alias searchShelf: searchShelf
            readonly property alias previewCard: searchShelf
            readonly property alias omniBar: omniBar

            // Ambient Canvas Dimming Scrim
            Rectangle {
                id: searchScrim
                objectName: "searchScrim"
                anchors.fill: parent
                z: 1
                color: "#07080B"
                opacity: (!omniBar.isConversationalMode && (searchShelf.searchActive || (omniBar.active && omniBar.textLength > 0))) ? 0.72 : 0.0
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
                            canvasBridge.search.clear_search()
                        }
                    }
                }
            }

            SearchShelf {
                id: searchShelf
                objectName: "searchShelf"
                z: 2
                viewport: canvasViewport
                omniBar: omniBar
            }

            OmniBar {
                id: omniBar
                objectName: "omniBar"
                searchShelf: searchShelf
                anchors.horizontalCenter: parent.horizontalCenter
                z: 3

                onQuerySubmitted: function(text) {
                    if (canvasBridge) {
                        canvasBridge.execute_intent(text)
                    }
                }

                onCancelQuery: {
                    if (canvasBridge) {
                        canvasBridge.search.clear_search()
                    }
                }

                onDismissed: {
                    active = false
                }
            }

            CanvasHud {
                id: bottomHud
                objectName: "bottomHud"
                z: 4
            }

            DiagnosticsOverlay {
                id: diagnosticsOverlay
                objectName: "diagnosticsOverlay"
                showDiagnostics: canvasRoot.showDiagnostics
                z: 5
            }
        }
    }
}
