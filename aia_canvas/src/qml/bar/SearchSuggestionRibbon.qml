import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root
    
    property bool active: false
    property bool isShellMode: false
    property bool isConversationalMode: false
    property bool shelfExpanded: false
    property var resultsList: []
    property int currentRibbonIndex: -1
    property int resultsCount: resultsList ? resultsList.length : 0
    property alias resultsModel: ribbonListView

    signal ribbonItemHovered(int index)
    signal ribbonItemClicked(int index)
    signal selectCurrentRibbonItem()

    visible: active && !isShellMode && !isConversationalMode && resultsCount > 0
    height: shelfExpanded ? 240 : 52

    Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutQuint } }

    Row {
        anchors.fill: parent
        spacing: 8

        // Horizontal ListView when NOT expanded
        ListView {
            id: ribbonListView
            objectName: "ribbonListView"
            width: overflowIndicator.visible ? (parent.width - overflowIndicator.width - 8) : parent.width
            height: parent.height
            orientation: ListView.Horizontal
            spacing: 10
            clip: true
            visible: !root.shelfExpanded
            model: root.resultsList ? root.resultsList.slice(0, 16) : []
            currentIndex: root.currentRibbonIndex
            onCurrentIndexChanged: {
                if (!root.shelfExpanded && root.currentRibbonIndex !== currentIndex) {
                    root.currentRibbonIndex = currentIndex;
                }
            }

            delegate: OmniRibbonItem {
                resultData: modelData
                isCurrentItem: index === root.currentRibbonIndex
                onHovered: {
                    root.ribbonItemHovered(index);
                }
                onClicked: {
                    root.ribbonItemClicked(index);
                }
            }
        }

        // High-density vertical multi-row GridView when expanded
        GridView {
            id: shelfGridView
            objectName: "shelfGridView"
            width: overflowIndicator.visible ? (parent.width - overflowIndicator.width - 8) : parent.width
            height: parent.height
            cellWidth: 138
            cellHeight: 58
            clip: true
            visible: root.shelfExpanded
            model: root.resultsList || []
            currentIndex: root.currentRibbonIndex
            onCurrentIndexChanged: {
                if (root.shelfExpanded && root.currentRibbonIndex !== currentIndex) {
                    root.currentRibbonIndex = currentIndex;
                }
            }

            delegate: OmniRibbonItem {
                width: 128
                height: 52
                resultData: modelData
                isCurrentItem: index === root.currentRibbonIndex
                onHovered: {
                    root.ribbonItemHovered(index);
                }
                onClicked: {
                    root.ribbonItemClicked(index);
                }
            }
        }

        // Overflow Indicator / Shelf Toggle Pill Badge
        Rectangle {
            id: overflowIndicator
            objectName: "overflowIndicator"
            width: 90
            height: 32
            radius: 16
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 10
            color: overflowMouseArea.containsMouse ? Theme.surfaceHovered : Theme.surfaceButton
            border.color: Theme.borderSubtle
            border.width: 1
            visible: root.resultsCount > 4

            Text {
                anchors.centerIn: parent
                text: root.shelfExpanded ? "Collapse v" : ("+" + Math.max(0, root.resultsCount - 4) + " more ^")
                font.pixelSize: 10
                font.bold: true
                font.family: Theme.fontCode
                color: Theme.textSecondary
            }

            MouseArea {
                id: overflowMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.shelfExpanded = !root.shelfExpanded;
                }
            }
        }
    }
}
