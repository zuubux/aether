import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: rootFrame
    objectName: "slateFrame"

    property string tierState: "TIER_1_FOCAL" // "TIER_1_FOCAL" or "TIER_1_25_SATELLITE"
    property string titleText: ""
    property string subtitleText: ""
    property color accentColor: Theme.accentCyan
    property alias headerRightContent: headerRightControls.data
    default property alias content: contentSlot.data
    property bool resizable: true
    property real minWidth: 480
    property real minHeight: 320
    property real targetWidth: tierState === "TIER_1_FOCAL" ? Math.min(1040, (parent && parent.width > 0) ? parent.width * 0.70 : 1040) : Math.min(624, (parent && parent.width > 0) ? parent.width * 0.42 : 624)
    property real targetHeight: tierState === "TIER_1_FOCAL" ? Math.min(820, (parent && parent.height > 0) ? parent.height * 0.80 : 820) : Math.min(492, (parent && parent.height > 0) ? parent.height * 0.48 : 492)
    property real targetCenterY: Math.round(((parent && parent.height > 0 ? parent.height : 0) - height) / 2)

    width: targetWidth
    height: targetHeight

    // Single-Stroke Rule: Slate cards must have exactly one root visual element with border.width > 0
    border.width: 1
    radius: 12
    border.color: tierState === "TIER_1_FOCAL" ? Theme.borderSubtle : Qt.rgba(0.39, 0.45, 0.55, 0.40)
    color: tierState === "TIER_1_FOCAL" ? Theme.surfaceElevated : Qt.rgba(0.08, 0.11, 0.17, 0.88)
    z: tierState === "TIER_1_FOCAL" ? 100 : 50

    MouseArea {
        id: interiorAbsorber
        objectName: "interiorAbsorber"
        anchors.fill: parent
    }

    Rectangle {
        id: headerBar
        objectName: "headerBar"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 52
        color: Theme.surfaceGlass
        topLeftRadius: 12
        topRightRadius: 12

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.borderSubtle
        }

        MouseArea {
            id: headerDragArea
            anchors.fill: parent
            enabled: rootFrame.tierState === "TIER_1_25_SATELLITE"
            cursorShape: enabled ? Qt.SizeAllCursor : Qt.ArrowCursor
            drag.target: rootFrame.tierState === "TIER_1_25_SATELLITE" ? rootFrame : null
            drag.axis: Drag.XAndYAxis
        }

        Row {
            id: titleBreadcrumbRow
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: headerRightControls.left
            anchors.rightMargin: 16
            spacing: 8

            Text {
                text: rootFrame.titleText
                font.pixelSize: 12
                font.weight: Font.DemiBold
                color: rootFrame.accentColor
                opacity: 0.85
            }

            Text {
                text: "—"
                font.pixelSize: 12
                color: Theme.textMuted
                opacity: 0.5
                visible: rootFrame.subtitleText.length > 0
            }

            Text {
                id: topicText
                text: rootFrame.subtitleText
                font.pixelSize: 12
                font.italic: true
                font.weight: Font.Normal
                color: Theme.textMuted
                elide: Text.ElideRight
                width: Math.min(implicitWidth, parent.width - 200)
                visible: text.length > 0
            }
        }

        Row {
            id: headerRightControls
            objectName: "headerRightControls"
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: 14
            spacing: 8
        }
    }

    Item {
        id: contentSlot
        objectName: "contentSlot"
        anchors.top: headerBar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
    }

    Item {
        id: resizeCorner
        objectName: "resizeCorner"
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 24
        height: 24
        z: 100
        visible: rootFrame.resizable

        Item {
            id: resizeGrip
            objectName: "resizeGrip"
            anchors.fill: parent

            Rectangle {
                width: 13
                height: 1.5
                rotation: -45
                transformOrigin: Item.Center
                x: 7; y: 15
                color: (typeof Theme !== "undefined" && Theme.borderSubtle) ? Theme.borderSubtle : "#33FFFFFF"
            }

            Rectangle {
                width: 7
                height: 1.5
                rotation: -45
                transformOrigin: Item.Center
                x: 14; y: 18
                color: (typeof Theme !== "undefined" && Theme.borderSubtle) ? Theme.borderSubtle : "#33FFFFFF"
            }
        }

        MouseArea {
            id: resizeMouseArea
            objectName: "resizeMouseArea"
            anchors.fill: parent
            cursorShape: Qt.SizeFDiagCursor
            hoverEnabled: true
            enabled: rootFrame.resizable

            property real startParentX: 0
            property real startParentY: 0
            property real startWidth: 0
            property real startHeight: 0

            onPressed: function(mouse) {
                var p = rootFrame.parent ? rootFrame.parent : rootFrame;
                var pt = mapToItem(p, mouse.x, mouse.y);
                startParentX = pt.x;
                startParentY = pt.y;
                startWidth = rootFrame.width;
                startHeight = rootFrame.height;
            }

            onPositionChanged: function(mouse) {
                if (pressed) {
                    var p = rootFrame.parent ? rootFrame.parent : rootFrame;
                    var pt = mapToItem(p, mouse.x, mouse.y);
                    var deltaX = pt.x - startParentX;
                    var deltaY = pt.y - startParentY;
                    var pw = (rootFrame.parent && rootFrame.parent.width > 0) ? rootFrame.parent.width : 1600;
                    var ph = (rootFrame.parent && rootFrame.parent.height > 0) ? rootFrame.parent.height : 1200;
                    var minW = rootFrame.minWidth;
                    var maxW = pw * 0.95;
                    var minH = rootFrame.minHeight;
                    var maxH = ph * 0.95;

                    rootFrame.width = Math.max(minW, Math.min(maxW, startWidth + deltaX));
                    rootFrame.height = Math.max(minH, Math.min(maxH, startHeight + deltaY));
                }
            }
        }
    }
}
