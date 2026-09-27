import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: diagnosticsRoot
    objectName: "diagnosticsOverlay"
    property bool showDiagnostics: false
    visible: showDiagnostics
    width: 290
    height: 380
    anchors.top: parent ? parent.top : undefined
    anchors.right: parent ? parent.right : undefined
    anchors.margins: 20
    color: Theme.surfaceBackground
    border.color: Theme.borderSubtle
    border.width: 1
    radius: 8
    opacity: 0.92
    z: 9000

    Column {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        // Header Row: Title & FPS Badge
        RowLayout {
            width: parent.width

            Text {
                text: "AETHER DIAGNOSTICS"
                color: Theme.textPrimary
                font.family: Theme.fontCode
                font.pixelSize: 12
                font.bold: true
                Layout.fillWidth: true
            }

            Rectangle {
                width: fpsText.implicitWidth + 12
                height: 18
                radius: 4
                color: "#1e293b"
                border.color: Theme.accentFocus
                border.width: 1

                Text {
                    id: fpsText
                    anchors.centerIn: parent
                    text: (canvasBridge ? canvasBridge.renderFps.toFixed(0) : "120") + " FPS"
                    color: Theme.accentFocus
                    font.family: Theme.fontCode
                    font.pixelSize: 10
                    font.bold: true
                }
            }
        }

        Rectangle { width: parent.width; height: 1; color: Theme.borderSubtle }

        // ENGINE SECTION
        Text {
            text: "ENGINE"
            color: Theme.textMuted
            font.family: Theme.fontCode
            font.pixelSize: 10
            font.bold: true
        }

        Grid {
            columns: 2
            spacing: 8
            rowSpacing: 6
            width: parent.width

            Text { text: "Nodes:"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 110 }
            Text { text: canvasBridge ? canvasBridge.activeNodeCount : 0; color: Theme.accentFocus; font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true }

            Text { text: "Edges (Render):"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 110 }
            Text { text: canvasBridge ? canvasBridge.activeEdgeCount : 0; color: Theme.accentFocus; font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true }
        }

        Rectangle { width: parent.width; height: 1; color: Theme.borderSubtle }

        // PIPELINE / IPC SECTION
        Text {
            text: "PIPELINE / IPC"
            color: Theme.textMuted
            font.family: Theme.fontCode
            font.pixelSize: 10
            font.bold: true
        }

        Grid {
            columns: 2
            spacing: 8
            rowSpacing: 6
            width: parent.width

            Text { text: "IPC RTT:"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 110 }
            Text { text: canvasBridge ? canvasBridge.ipcRttMs.toFixed(1) + " ms" : "0.0 ms"; color: Theme.textPrimary; font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true }

            Text { text: "DB Query:"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 110 }
            Text { text: canvasBridge ? canvasBridge.dbQueryMs.toFixed(1) + " ms" : "0.0 ms"; color: Theme.textPrimary; font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true }

            Text { text: "LLM TTFT:"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 110 }
            Text { text: canvasBridge ? canvasBridge.llmTtftMs.toFixed(1) + " ms" : "0.0 ms"; color: Theme.textPrimary; font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true }

            Text { text: "Backend Socket:"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 110 }
            Text {
                text: (canvasBridge && canvasBridge.isConnected) ? "CONNECTED" : "OFFLINE"
                color: (canvasBridge && canvasBridge.isConnected) ? Theme.accentSuccess : "#ef4444"
                font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true
            }
        }

        Rectangle { width: parent.width; height: 1; color: Theme.borderSubtle }

        Text {
