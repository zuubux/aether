import QtQuick
import QtQuick.Controls
import ".."

/**
 * OmniRibbonItem.qml
 * Individual item delegate rendering result title, category badge, and snippet preview.
 */
Rectangle {
    id: root

    property var resultData: ({})
    property bool isCurrentItem: false

    signal clicked()
    signal hovered()

    width: 128
    implicitWidth: 128
    height: 52
    radius: 8

    color: isCurrentItem ? Theme.surfaceHovered : (hoverArea.containsMouse ? Theme.surfaceButtonHover : Theme.surfaceButton)
    border.color: isCurrentItem ? Theme.accentFocus : (hoverArea.containsMouse ? Theme.borderHover : Theme.borderSubtle)
    border.width: isCurrentItem ? 1.5 : 1

    Behavior on color { ColorAnimation { duration: Theme.animFadeInDuration ?? 160 } }
    Behavior on border.color { ColorAnimation { duration: Theme.animFadeInDuration ?? 160 } }

    Column {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 4

        Row {
            width: parent.width
            spacing: 6

            // Archetype / Extension Pill Badge
            Rectangle {
                id: badgeRect
                anchors.verticalCenter: parent.verticalCenter
                height: 18
                width: badgeText.implicitWidth + 8
                radius: 4
                color: {
                    var arch = resultData ? (resultData.archetype || resultData.category || "") : ""
                    var ext = resultData ? (resultData.extension || resultData.icon || "") : ""
                    return Theme.getBadgeColor(arch, ext)
                }

                Text {
                    id: badgeText
                    anchors.centerIn: parent
                    text: {
                        var ext = resultData ? (resultData.extension || resultData.icon || "") : ""
                        var arch = resultData ? (resultData.archetype || resultData.category || "DOC") : "DOC"
                        return Theme.normalizeExt(ext ? ext : arch)
                    }
                    font.pixelSize: 9
                    font.bold: true
                    font.family: Theme.fontCode
                    color: "#0B0F19"
                }
            }

            // Truncated Title
            Text {
                id: titleText
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - badgeRect.width - 6
                text: resultData ? (resultData.title || "") : ""
                font.pixelSize: 11
                font.bold: true
                font.family: Theme.fontSans
                color: isCurrentItem ? Theme.textPrimary : Theme.textSecondary
                elide: Text.ElideRight
                maximumLineCount: 1
            }
        }

        // Secondary Snippet or Path
        Text {
            id: snippetText
            width: parent.width
            text: resultData ? (resultData.snippet || resultData.path || resultData.category || "") : ""
            font.pixelSize: 10
            font.family: Theme.fontCode
            color: Theme.textMuted
            elide: Text.ElideRight
            maximumLineCount: 1
        }
    }

    MouseArea {
        id: hoverArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: root.hovered()
        onClicked: root.clicked()
    }
}
