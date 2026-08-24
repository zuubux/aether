import QtQuick
import ".."

Rectangle {
    id: diagnosticsRoot
    property bool showDiagnostics: false
    visible: showDiagnostics
    width: 270
    height: 270
    anchors.top: parent ? parent.top : undefined
    anchors.right: parent ? parent.right : undefined
    anchors.margins: 20
    color: Theme.surfaceBackground
    border.color: Theme.borderSubtle
    border.width: 1
    radius: 8
    opacity: 0.90
    z: 9000

    Column {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8

        Text {
            text: "AIA CANVAS SRE HUD"
            color: Theme.textPrimary
            font.family: Theme.fontCode
            font.pixelSize: 12
            font.bold: true
        }

        Rectangle { width: parent.width; height: 1; color: Theme.borderSubtle }

        Grid {
            columns: 2
            spacing: 8
            rowSpacing: 6

            Text { text: "Nodes:"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 120 }
            Text { text: canvasBridge ? canvasBridge.activeNodeCount : 0; color: Theme.accentFocus; font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true }

            Text { text: "Edges (Render):"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 120 }
            Text { text: canvasBridge ? canvasBridge.activeEdgeCount : 0; color: Theme.tendrilTemporal; font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true }

            Text { text: "Physics Step:"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 120 }
            Text { 
                text: canvasBridge ? canvasBridge.physicsFrametime.toFixed(2) + " ms" : "0.00 ms"
                color: (canvasBridge && canvasBridge.physicsFrametime > 6.5) ? "#ef4444" : Theme.accentSuccess 
                font.family: Theme.fontCode; font.pixelSize: 11; font.bold: true 
            }

            Text { text: "Backend Socket:"; color: Theme.textMuted; font.family: Theme.fontCode; font.pixelSize: 11; width: 120 }
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
