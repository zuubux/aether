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
    property bool searchActive: false
    property int focusedIndex: 0

    readonly property var topMatches: searchResultIds ? searchResultIds.slice(0, 7) : []
    readonly property int focusedNodeId: {
        if (!topMatches || topMatches.length === 0) return 0;
        if (focusedIndex < 0 || focusedIndex >= topMatches.length) return 0;
        var raw = topMatches[focusedIndex];
        return typeof raw === "number" ? raw : parseInt(raw);
    }
    readonly property var activeNodeData: getNodeData(focusedNodeId)

    function getNodeData(nodeId) {
        if (!nodeId) return null;
        if (typeof canvasBridge !== "undefined" && canvasBridge) {
            if (typeof canvasBridge.get_node === "function") {
                var n = canvasBridge.get_node(nodeId);
                if (n) return n;
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
        if (!topMatches || topMatches.length === 0) return;
        focusedIndex = (focusedIndex - 1 + topMatches.length) % topMatches.length;
    }

    function navigateRight() {
        if (!topMatches || topMatches.length === 0) return;
        focusedIndex = (focusedIndex + 1) % topMatches.length;
    }

    function selectFocusedNode() {
        if (focusedNodeId > 0) {
            if (typeof canvasBridge !== "undefined" && canvasBridge) {
                canvasBridge.focus_node(focusedNodeId);
                canvasBridge.clear_search();
            }
            if (omniBar && typeof omniBar.dismiss === "function") {
                omniBar.dismiss();
            }
        }
    }

    // Positioning anchored above OmniBar
    anchors.bottom: omniBar ? omniBar.top : parent.bottom
    anchors.bottomMargin: 28
    anchors.horizontalCenter: omniBar ? omniBar.horizontalCenter : parent.horizontalCenter
    width: Math.max(Theme.tier1_5Width, carouselContainer.width)
    height: mainLayout.implicitHeight

    visible: opacity > 0.001
    opacity: (searchActive && topMatches.length > 0) ? 1.0 : 0.0

    Behavior on opacity {
        NumberAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing }
    }

    onFocusedIndexChanged: {
        if (focusedIndex >= 0 && focusedIndex < topMatches.length) {
            carouselList.positionViewAtIndex(focusedIndex, ListView.Contain);
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
            if (canvasBridge) {
                canvasBridge.clear_search();
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
        // Top Section: Active Item Tier 1.5 Preview Card (380x280px)
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
                anchors.fill: parent
                anchors.margins: 24
                nodeData: searchShelfRoot.activeNodeData
            }
        }

        // =====================================================================
        // Bottom Section: Horizontal Ranked Carousel of Tier 2 Tokens (240x68px)
        // =====================================================================
        Item {
            id: carouselContainer
            anchors.horizontalCenter: parent.horizontalCenter
            width: {
                var totalW = searchShelfRoot.topMatches.length * (Theme.tier2Width + 16) - 16;
                var maxW = searchShelfRoot.parent ? (searchShelfRoot.parent.width - 64) : 900;
                return Math.min(maxW, Math.max(Theme.tier1_5Width, totalW));
            }
            height: Theme.tier2Height

            ListView {
                id: carouselList
                anchors.fill: parent
                orientation: ListView.Horizontal
                spacing: 16
                model: searchShelfRoot.topMatches
                currentIndex: searchShelfRoot.focusedIndex
                clip: true
                interactive: true
                flickableDirection: Flickable.HorizontalFlick
                boundsBehavior: Flickable.StopAtBounds
                preferredHighlightBegin: 0
                preferredHighlightEnd: width
                highlightRangeMode: ListView.ApplyRange

                delegate: Item {
                    id: tokenDelegate
                    readonly property int itemIndex: index
                    readonly property var rawId: modelData
                    readonly property int tokenNodeId: typeof rawId === "number" ? rawId : parseInt(rawId)
                    readonly property var tokenNodeData: searchShelfRoot.getNodeData(tokenNodeId)
                    readonly property bool isCurrent: itemIndex === searchShelfRoot.focusedIndex

                    width: Theme.tier2Width
                    height: Theme.tier2Height

                    Rectangle {
                        id: tokenCard
                        anchors.fill: parent
                        radius: Theme.tier2Radius
                        color: isCurrent ? Theme.surfaceHovered : Theme.surfaceBackground
                        border.color: isCurrent ? Theme.accentFocus : (tokenMouseArea.containsMouse ? Theme.borderHover : Theme.surfaceBorder)
                        border.width: isCurrent ? 1.5 : 1

                        Behavior on color { ColorAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing } }
                        Behavior on border.color { ColorAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing } }

                        // File extension badge
                        Rectangle {
                            id: iconBadge
                            width: Math.max(20, iconBadgeText.implicitWidth + 8)
                            height: 16
                            radius: 3
                            color: Theme.getBadgeColor(tokenNodeData ? tokenNodeData.extension : "", tokenNodeData ? tokenNodeData.archetype : "")
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 8

                            Text {
                                id: iconBadgeText
                                anchors.centerIn: parent
                                text: Theme.normalizeExt(tokenNodeData ? tokenNodeData.extension : "")
                                font.pixelSize: 9
                                font.family: Theme.fontCode
                                font.bold: true
                                color: "#0D1117"
                            }
                        }

                        // Text column
                        Column {
                            anchors.left: iconBadge.right
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 8
                            anchors.rightMargin: 10
                            spacing: 3

                            Text {
                                width: parent.width
                                text: tokenNodeData ? (tokenNodeData.fileName || ("Node " + tokenNodeId)) : ("Node " + tokenNodeId)
                                font.pixelSize: 11
                                font.family: Theme.fontSans
                                font.weight: isCurrent ? Font.DemiBold : Font.Normal
                                color: isCurrent ? Theme.textPrimary : Theme.textSecondary
                                elide: Text.ElideRight
                            }

                            Text {
                                width: parent.width
                                text: tokenNodeData ? (tokenNodeData.snippet || tokenNodeData.filePath || "") : ""
                                font.pixelSize: 9
                                font.family: Theme.fontCode
                                color: Theme.textMuted
                                elide: Text.ElideRight
                                maximumLineCount: 1
                            }
                        }

                        MouseArea {
                            id: tokenMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor

                            onEntered: {
                                searchShelfRoot.focusedIndex = itemIndex;
                            }

                            onClicked: {
                                searchShelfRoot.focusedIndex = itemIndex;
                                searchShelfRoot.selectFocusedNode();
                            }
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: typeof canvasBridge !== "undefined" ? canvasBridge : null

        function onSearchResultsReceived(results) {
            searchShelfRoot.searchResultIds = results || [];
            searchShelfRoot.focusedIndex = 0;
            searchShelfRoot.searchActive = (results && results.length > 0);
        }

        function onSearchCleared() {
            searchShelfRoot.searchActive = false;
            searchShelfRoot.searchResultIds = [];
            searchShelfRoot.focusedIndex = 0;
        }
    }
}
