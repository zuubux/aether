import QtQuick
import QtQuick.Controls

Item {
    id: root
    width: 320
    height: 220

    property string archetype: "document"
    property string snippet: ""
    property string fileName: ""
    property string filePath: ""
    property string sizeFormatted: "0 KB"
    property string hashSnippet: "N/A"
    property int referenceCount: 0
    property color accentColor: "#94a3b8"

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: 12
        color: "#161c28" // 90% opacity implied by context or #14171de6
        opacity: 0.90
        border.color: "#64d2ff"
        border.width: 1
        antialiasing: true
        smooth: true

        // Header
        Rectangle {
            id: header
            width: parent.width
            height: 40
            color: "transparent"
            border.width: 0

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                Rectangle {
                    width: 20
                    height: 20
                    radius: 4
                    color: "transparent"
                    border.color: root.accentColor
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: root.archetype === "document" ? "D" : (root.archetype === "code" ? "C" : (root.archetype === "binary" ? "B" : "A"))
                        color: root.accentColor
                        font.family: "Monospace"
                        font.pixelSize: 10
                        font.bold: true
                    }
                }

                Text {
                    text: root.fileName
                    color: "#f8fafc"
                    font.family: "Monospace"
                    font.pixelSize: 12
                    font.bold: true
                    elide: Text.ElideRight
                    width: 180
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: "#1e293b"
                anchors.bottom: parent.bottom
            }
        }

        // Body
        Item {
            anchors.top: header.bottom
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 12

            // Case 1: Document / Code
            Item {
                visible: root.archetype === "document" || root.archetype === "code"
                anchors.fill: parent

                Text {
                    id: snippetText
                    text: root.snippet === "" ? "(No preview content available)" : root.snippet
                    color: "#c9d1d9"
                    font.family: "Monospace"
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    width: parent.width - 24
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    elide: Text.ElideRight
                    maximumLineCount: 10
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 40
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 1.0; color: "#14171d" }
                    }
                }
            }

            // Case 2: Binary / Technical
            Item {
                visible: root.archetype === "binary" || root.archetype === "archive" || root.archetype === "system"
                anchors.fill: parent

                Row {
                    anchors.fill: parent
                    spacing: 16

                    Rectangle {
                        width: 60
                        height: 60
                        anchors.verticalCenter: parent.verticalCenter
                        color: "transparent"
                        border.color: "#334155"
                        border.width: 1
                        radius: 8

                        Text {
                            anchors.centerIn: parent
                            text: "[ O ]"
                            color: "#64748b"
                            font.family: "Monospace"
                            font.pixelSize: 16
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8

                        Text {
                            text: "SIZE: " + root.sizeFormatted
                            color: "#94a3b8"
                            font.family: "Monospace"
                            font.pixelSize: 10
                        }

                        Text {
                            text: "HASH: " + root.hashSnippet
                            color: "#94a3b8"
                            font.family: "Monospace"
                            font.pixelSize: 10
                        }

                        Text {
                            text: "REFS: " + root.referenceCount
                            color: "#94a3b8"
                            font.family: "Monospace"
                            font.pixelSize: 10
                        }
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    // Fake grid accent could go here if needed
                    opacity: 0.1
                    border.color: "#334155"
                    border.width: 1
                    radius: 6
                    z: -1
                }
            }
        }
    }
}
