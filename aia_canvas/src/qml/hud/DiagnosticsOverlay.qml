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
            Text { text: canvasBridge ? canvasBridge.activeEdgeCount : 0; color: Theme.tendrilTemporal; font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true }

            Text { text: "Physics Step:"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 110 }
            
            Row {
                spacing: 6

                Text {
                    id: physicsValueText
                    property real stepMs: canvasBridge ? canvasBridge.physicsStepMs : 0.0
                    text: stepMs.toFixed(2) + " ms"
                    color: stepMs > 8.0 ? "#ef4444" : (stepMs > 6.5 ? "#f59e0b" : Theme.accentSuccess)
                    font.family: Theme.fontCode
                    font.pixelSize: 11
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }

                Rectangle {
                    property real stepMs: canvasBridge ? canvasBridge.physicsStepMs : 0.0
                    width: statusPillText.implicitWidth + 8
                    height: 16
                    radius: 3
                    color: stepMs > 8.0 ? "#451a1a" : (stepMs > 6.5 ? "#453010" : "#143820")
                    border.color: stepMs > 8.0 ? "#ef4444" : (stepMs > 6.5 ? "#f59e0b" : "#22c55e")
                    border.width: 1
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        id: statusPillText
                        property real stepMs: canvasBridge ? canvasBridge.physicsStepMs : 0.0
                        anchors.centerIn: parent
                        text: stepMs > 8.0 ? "CRIT" : (stepMs > 6.5 ? "WARN" : "GOOD")
                        color: stepMs > 8.0 ? "#ef4444" : (stepMs > 6.5 ? "#f59e0b" : "#22c55e")
                        font.family: Theme.fontCode
                        font.pixelSize: 9
                        font.bold: true
                    }
                }
            }
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
            text: "TENDRIL COLOR KEY"
            color: Theme.textMuted
            font.family: Theme.fontCode
            font.pixelSize: 10
            font.bold: true
        }

        Column {
            spacing: 5
            width: parent.width

            Row {
                spacing: 8
                Rectangle { width: 14; height: 3; radius: 1.5; color: Theme.tendrilExplicit; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Explicit ([[WikiLinks]])"; color: Theme.textSecondary; font.family: Theme.fontCode; font.pixelSize: 10 }
            }

            Row {
                spacing: 8
                Rectangle { width: 14; height: 3; radius: 1.5; color: Theme.tendrilSemantic; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Semantic (Embeddings)"; color: Theme.textSecondary; font.family: Theme.fontCode; font.pixelSize: 10 }
            }

            Row {
                spacing: 8
                Rectangle { width: 14; height: 3; radius: 1.5; color: Theme.tendrilTemporal; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Temporal (Co-edit / Session)"; color: Theme.textSecondary; font.family: Theme.fontCode; font.pixelSize: 10 }
            }

            Row {
                spacing: 8
                Rectangle { width: 14; height: 3; radius: 1.5; color: "#67e8f9"; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Hover / Active Bloom"; color: Theme.textSecondary; font.family: Theme.fontCode; font.pixelSize: 10 }
            }
        }
    }
}
