import QtQuick
import QtQuick.Controls
import ".."
import "../node"

Item {
    id: searchShelfRoot
    objectName: "searchShelf"

    property Item viewport: null
    property Item omniBar: null

    property var searchResultIds: []
    property bool isSearchActiveExplicit: false
    readonly property bool isShellMode: omniBar && omniBar.isShellMode
    readonly property bool isConversationalMode: omniBar && omniBar.isConversationalMode
    readonly property bool searchActive: (omniBar && omniBar.active && omniBar.resultsList && omniBar.resultsList.length > 0 && omniBar.currentRibbonIndex >= 0) || (searchResultIds && searchResultIds.length > 0) || isSearchActiveExplicit
    property int focusedIndex: 0

    readonly property var activeRibbonItem: {
        if (omniBar && omniBar.active && omniBar.resultsList && omniBar.resultsList.length > 0) {
            var idx = omniBar.currentRibbonIndex;
            if (idx >= 0 && idx < omniBar.resultsList.length) {
                return omniBar.resultsList[idx];
            }
        }
        return null;
    }

    readonly property var topMatches: {
        if (searchResultIds && searchResultIds.length > 0) return searchResultIds.slice(0, 7);
        if (omniBar && omniBar.resultsList && omniBar.resultsList.length > 0) {
            var list = [];
            for (var i = 0; i < omniBar.resultsList.length; i++) {
                var item = omniBar.resultsList[i];
                var rawId = item.node_id !== undefined ? item.node_id : item.id;
                var nId = parseInt(rawId);
                if (!isNaN(nId) && list.indexOf(nId) < 0) list.push(nId);
            }
            return list.slice(0, 7);
        }
        return [];
    }

    readonly property int focusedNodeId: {
        if (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.selectedNodeId > 0) {
            return canvasBridge.selectedNodeId;
        }
        if (activeRibbonItem) {
            var rawRibbonId = activeRibbonItem.node_id !== undefined ? activeRibbonItem.node_id : activeRibbonItem.id;
            if (rawRibbonId !== undefined && rawRibbonId !== null) {
                return typeof rawRibbonId === "number" ? rawRibbonId : parseInt(rawRibbonId);
            }
        }
        if (!topMatches || topMatches.length === 0) return 0;
        if (focusedIndex < 0 || focusedIndex >= topMatches.length) return 0;
        var raw = topMatches[focusedIndex];
        return typeof raw === "number" ? raw : parseInt(raw);
    }
    readonly property var activeNodeData: {
        var nodeFromBridge = getNodeData(focusedNodeId);
        if (nodeFromBridge) return nodeFromBridge;
        if (activeRibbonItem) return activeRibbonItem;
        return null;
    }

    function getNodeData(nodeId) {
        if (!nodeId) return null;
        if (typeof canvasBridge !== "undefined" && canvasBridge) {
            if (typeof canvasBridge.get_node === "function") {
                var n = canvasBridge.get_node(nodeId);
                if (n) return n;
            }
            if (typeof canvasBridge.get_node_data === "function") {
                var d = canvasBridge.get_node_data(nodeId);
                if (d && (d.id || d.filePath || d.path)) return d;
            }
            if (canvasBridge.nodes) {
                for (var i = 0; i < canvasBridge.nodes.length; i++) {
                    if (canvasBridge.nodes[i].id === nodeId) {
                        return canvasBridge.nodes[i];
                    }
                }
            }
        }
        if (viewport && typeof viewport.getNode === "function") {
            var vNode = viewport.getNode(nodeId);
            if (vNode && vNode.nodeModel) {
                return vNode.nodeModel;
            }
        }
        return null;
    }

    function navigateLeft() {
        if (omniBar && omniBar.active && omniBar.resultsList && omniBar.resultsList.length > 0) {
            if (omniBar.currentRibbonIndex > 0) {
                omniBar.currentRibbonIndex--;
            }
            return;
        }
        if (!topMatches || topMatches.length === 0) return;
        focusedIndex = (focusedIndex - 1 + topMatches.length) % topMatches.length;
    }

    function navigateRight() {
        if (omniBar && omniBar.active && omniBar.resultsList && omniBar.resultsList.length > 0) {
            var maxIdx = Math.min(16, omniBar.resultsList.length) - 1;
            if (omniBar.currentRibbonIndex < maxIdx) {
                omniBar.currentRibbonIndex++;
            }
            return;
        }
        if (!topMatches || topMatches.length === 0) return;
        focusedIndex = (focusedIndex + 1) % topMatches.length;
    }

    function selectFocusedNode() {
        if (focusedNodeId > 0) {
            if (viewport) {
                viewport.isCameraCached = false;
                if (typeof viewport.steerCameraToNode === "function") {
                    viewport.steerCameraToNode(focusedNodeId, true);
                }
            }
            if (canvasBridge) {
                canvasBridge.node.select_node(focusedNodeId);
                canvasBridge.search.clear_search();
            }
            isSearchActiveExplicit = false;
            if (omniBar) {
                omniBar.dismiss();
            }
        }
    }

    // Positioning decoupled from omniBar.active offscreen sliding
    anchors.bottom: (omniBar && omniBar.active) ? omniBar.top : (parent ? parent.bottom : undefined)
    anchors.bottomMargin: (omniBar && omniBar.active) ? ((omniBar.resultsList && omniBar.resultsList.length > 0) ? 84 : 16) : 36
    anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
    width: Theme.tier1_5Width
    height: mainLayout.implicitHeight

    visible: opacity > 0.001
    opacity: (!isShellMode && !isConversationalMode && searchActive && (activeNodeData !== null || topMatches.length > 0)) ? 1.0 : 0.0

    Behavior on opacity {
        NumberAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing }
    }
    Behavior on anchors.bottomMargin {
        NumberAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing }
    }

    onFocusedIndexChanged: {
        if (focusedIndex >= 0 && focusedIndex < topMatches.length) {
            carouselList.positionViewAtIndex(focusedIndex, ListView.Contain);
        }
    }

    onFocusedNodeIdChanged: {
        if (searchActive && focusedNodeId > 0 && viewport && typeof viewport.steerCameraToNode === "function") {
            viewport.steerCameraToNode(focusedNodeId);
        }
    }

    Keys.priority: Keys.BeforeItem
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Left) {
            navigateLeft();
            event.accepted = true;
        } else if (event.key === Qt.Key_Right) {
            navigateRight();
            event.accepted = true;
        } else if (event.key === Qt.Key_Tab) {
            navigateRight();
            event.accepted = true;
        } else if (event.key === Qt.Key_Backtab) {
            navigateLeft();
            event.accepted = true;
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            selectFocusedNode();
            event.accepted = true;
        } else if (event.key === Qt.Key_Escape) {
            searchShelfRoot.isSearchActiveExplicit = false;
            if (canvasBridge) {
                canvasBridge.search.clear_search();
            }
            if (omniBar) {
                omniBar.dismiss();
            }
            event.accepted = true;
        }
    }

    Column {
        id: mainLayout
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 32

        // =====================================================================
        // Top Section: Active Item Tier 1.5 Preview Card (440x320px)
        // =====================================================================
        Rectangle {
            id: previewCard
            anchors.horizontalCenter: parent.horizontalCenter
            width: Theme.tier1_5Width
            height: Theme.tier1_5Height
            radius: Theme.tier1_5Radius
            color: Theme.surfaceBackground
            border.color: Theme.surfaceBorder
            border.width: 1
            clip: true

            NodePreview {
                id: activePreviewItem
                objectName: "activePreviewItem"
                anchors.fill: parent
                anchors.margins: 24
                nodeData: searchShelfRoot.activeNodeData
                archetype: searchShelfRoot.activeNodeData ? (searchShelfRoot.activeNodeData.archetype || "document") : "document"
                path: searchShelfRoot.activeNodeData ? (searchShelfRoot.activeNodeData.path || searchShelfRoot.activeNodeData.filePath || "") : ""
                thumbnail: searchShelfRoot.activeNodeData ? (searchShelfRoot.activeNodeData.thumbnail || searchShelfRoot.activeNodeData.thumbnailUrl || searchShelfRoot.activeNodeData.preview_path || searchShelfRoot.activeNodeData.previewUrl || "") : ""
                previewUrl: searchShelfRoot.activeNodeData ? (searchShelfRoot.activeNodeData.previewUrl || searchShelfRoot.activeNodeData.thumbnail || searchShelfRoot.activeNodeData.thumbnailUrl || searchShelfRoot.activeNodeData.preview_path || (activePreviewItem.isImage ? path : "")) : ""
            }
        }

    }

    Connections {
        target: typeof canvasBridge !== "undefined" ? canvasBridge : null

        function onSearchResultsReceived(results) {
            searchShelfRoot.searchResultIds = results || [];
            searchShelfRoot.focusedIndex = 0;
        }

        function onSearchCleared() {
            searchShelfRoot.isSearchActiveExplicit = false;
            searchShelfRoot.searchResultIds = [];
            searchShelfRoot.focusedIndex = 0;
        }
    }
}
