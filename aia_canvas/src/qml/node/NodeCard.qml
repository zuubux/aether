import QtQuick
import QtQuick.Controls
import ".."

/**
 * NodeCard.qml
 * Canvas card delegate for pinned markdown conversations and documents.
 */
Item {
    id: root
    width: 320
    height: 220

    property var nodeData: null
    property string title: nodeData ? (nodeData.title || nodeData.fileName || "Card") : "Card"
    property string content: nodeData ? (nodeData.content || nodeData.snippet || "") : ""
    property string fileExt: nodeData ? (nodeData.extension || "md") : "md"
    property bool isPinned: true

    Rectangle {
        id: cardShell
        anchors.fill: parent
        radius: 10
        color: Theme.surfaceBackground
        border.color: isPinned ? Theme.accentCyan : Theme.borderSubtle
        border.width: 1

        Item {
            id: headerArea
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 32
            anchors.margins: 8

            Row {
                anchors.fill: parent
                spacing: 6
                verticalAlignment: Text.AlignVCenter

                Rectangle {
                    width: 18
                    height: 14
                    radius: 3
                    color: Theme.getBadgeColor ? Theme.getBadgeColor(root.fileExt, "document") : "#38BDF8"
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        anchors.centerIn: parent
                        text: Theme.normalizeExt ? Theme.normalizeExt(root.fileExt) : "MD"
                        font.pixelSize: 8
                        font.family: Theme.fontCode
                        font.bold: true
                        color: "#0D1117"
                    }
                }

                Text {
                    text: root.title
                    color: Theme.textPrimary
                    font.family: Theme.fontSans
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    anchors.verticalCenter: parent.verticalCenter
                    elide: Text.ElideRight
                    width: parent.width - 24
                }
            }
        }

        // Card body container with enforced clip: true
        Item {
            id: cardBodyContainer
            objectName: "cardBodyContainer"
            anchors.top: headerArea.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            clip: true

            Flickable {
                id: flickable
                anchors.fill: parent
                contentWidth: width
                contentHeight: previewText.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                Text {
                    id: previewText
                    objectName: "previewText"
                    width: parent.width
                    text: root.content
                    textFormat: Text.MarkdownText
                    wrapMode: Text.Wrap
                    color: Theme.textSecondary
                    font.family: Theme.fontAiBody ? Theme.fontAiBody.family : Theme.fontSans
                    font.pixelSize: 11
                    lineHeight: 1.3
                    clip: true
                }
            }
        }
    }
}
