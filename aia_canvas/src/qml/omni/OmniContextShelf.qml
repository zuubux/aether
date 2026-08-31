import QtQuick
import QtQuick.Controls
import ".."

/**
 * OmniContextShelf.qml
 * Horizontal row for attached canvas context chips and dragged node tokens with removable close pills.
 */
Item {
    id: root
    objectName: "contextShelf"

    property var contextItems: []
    signal itemRemoved(int index, var item)

    readonly property int contextCount: (contextItems && typeof contextItems.length === "number") ? contextItems.length : (contextItems && typeof contextItems.count === "number" ? contextItems.count : 0)

    implicitHeight: contextCount > 0 ? Math.max(Theme.touchHitboxMin, 32) : 0
    height: implicitHeight
    visible: contextCount > 0

    function getCloseHitboxWidth(index) {
        var item = chipRepeater ? chipRepeater.itemAt(index) : null;
        return item ? item.closeAreaWidth : Math.max(Theme.touchHitboxMin, 44);
    }

    function getCloseHitboxHeight(index) {
        var item = chipRepeater ? chipRepeater.itemAt(index) : null;
        return item ? item.closeAreaHeight : Math.max(Theme.touchHitboxMin, 44);
    }

    Row {
        id: contextShelfRow
        objectName: "contextShelfRow"
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 12
        spacing: 8

        Repeater {
            id: chipRepeater
            objectName: "chipRepeater"
            model: root.contextItems
            delegate: Rectangle {
                id: chip
                objectName: "contextChip"
                height: 28
                width: chipRow.implicitWidth + 16
                radius: 14
                color: Theme.surfaceElevated
                property color chipTint: Theme.aiTextColorForRole(modelData.role)
                border.color: Qt.rgba(chipTint.r, chipTint.g, chipTint.b, 0.3)
                border.width: 1

                property real closeAreaWidth: closeArea.width
                property real closeAreaHeight: closeArea.height

                Row {
                    id: chipRow
                    anchors.centerIn: parent
                    spacing: 6

                    Text {
                        objectName: "chipText"
                        text: modelData.label || modelData.title || modelData.name || String(modelData.id || "Node")
                        color: chip.chipTint
                        font.family: Theme.fontSans
                        font.pixelSize: 11
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        id: closePill
                        objectName: "closePill"
                        width: 16
                        height: 16
                        radius: 8
                        color: closeArea.containsMouse ? Theme.surfaceButtonHover : "transparent"
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            objectName: "closeGlyph"
                            anchors.centerIn: parent
                            text: "×"
                            color: Theme.textMuted
                            font.pixelSize: 12
                            font.bold: true
                        }

                        MouseArea {
                            id: closeArea
                            objectName: "closeArea"
                            anchors.centerIn: parent
                            width: Math.max(Theme.touchHitboxMin, 44)
                            height: Math.max(Theme.touchHitboxMin, 44)
                            hoverEnabled: true
                            onClicked: root.itemRemoved(index, modelData)
                        }
                    }
                }
            }
        }
    }
}
