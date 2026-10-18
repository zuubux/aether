import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: diagnosticsRoot
    objectName: "diagnosticsOverlay"
    property bool showDiagnostics: false
    readonly property bool hasHorizon: typeof horizonController !== "undefined" && horizonController !== null
    readonly property var weaver: hasHorizon ? horizonController.weaverStatus : ({})
    readonly property var stage: hasHorizon ? horizonController.stageMetrics : ({})

    function toggle() {
        showDiagnostics = !showDiagnostics;
        if (showDiagnostics && typeof horizonController !== "undefined" && horizonController) {
            horizonController.refresh_diagnostics();
        }
    }

    visible: showDiagnostics
    width: 320
    height: content.implicitHeight + 28
    anchors.top: parent ? parent.top : undefined
    anchors.right: parent ? parent.right : undefined
    anchors.topMargin: 52
    anchors.rightMargin: 32
    color: Theme.surfaceBackground
    border.color: Theme.borderSubtle
    border.width: 1
    radius: 8
    z: 500

    component SectionTitle: Text {
        color: Theme.textMuted
        font.family: Theme.fontSans
        font.pixelSize: 10
        font.bold: true
        font.letterSpacing: 1
    }

    component KeyText: Text {
        color: Theme.textMuted
        font.family: Theme.fontSans
        font.pixelSize: 11
        Layout.preferredWidth: 96
    }

    component ValueText: Text {
        color: Theme.textPrimary
        font.family: Theme.fontCode
        font.pixelSize: 11
        elide: Text.ElideMiddle
        Layout.fillWidth: true
    }

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 14
        spacing: 8

        Text {
            text: "SYSTEM DOSSIER"
            color: Theme.textPrimary
            font.family: Theme.fontCode
            font.pixelSize: 12
            font.bold: true
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

        SectionTitle { text: "HOST & SUBSTRATE" }
        GridLayout {
            columns: 2
            columnSpacing: 8
            rowSpacing: 4
            Layout.fillWidth: true

            KeyText { text: "Hostname" }
            ValueText { text: diagnosticsRoot.hasHorizon ? horizonController.hostname : "" }
            KeyText { text: "Username" }
            ValueText { text: diagnosticsRoot.hasHorizon ? horizonController.username : "" }
            KeyText { text: "Kernel" }
            ValueText { text: diagnosticsRoot.hasHorizon ? horizonController.osKernel : "" }
            KeyText { text: "Memory RSS" }
            ValueText { text: (diagnosticsRoot.hasHorizon ? horizonController.memoryRss : 0).toFixed(1) + " MB" }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

        SectionTitle { text: "WEAVER METADATA" }
        GridLayout {
            columns: 2
            columnSpacing: 8
            rowSpacing: 4
            Layout.fillWidth: true

            KeyText { text: "Status" }
            ValueText {
                objectName: "weaverStatusText"
                text: diagnosticsRoot.weaver.is_connected ? "CONNECTED" : "OFFLINE"
                color: diagnosticsRoot.weaver.is_connected ? Theme.accentSuccess : Theme.textDimmed
                font.bold: true
            }
            KeyText { text: "Entities" }
            ValueText { text: String(diagnosticsRoot.weaver.entity_count !== undefined ? diagnosticsRoot.weaver.entity_count : 0) }
            KeyText { text: "DB Path" }
            ValueText { text: diagnosticsRoot.weaver.db_path !== undefined ? diagnosticsRoot.weaver.db_path : "" }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

        SectionTitle { text: "STAGE METRICS" }
        GridLayout {
            columns: 2
            columnSpacing: 8
            rowSpacing: 4
            Layout.fillWidth: true

            KeyText { text: "Active Plates" }
            ValueText { text: String(diagnosticsRoot.stage.active_count !== undefined ? diagnosticsRoot.stage.active_count : 0) }
            KeyText { text: "Capacity" }
            ValueText { text: String(diagnosticsRoot.stage.capacity !== undefined ? diagnosticsRoot.stage.capacity : 0) }
            KeyText { text: "Viewport" }
            ValueText {
                text: (diagnosticsRoot.parent ? Math.round(diagnosticsRoot.parent.width) : 0) + " × " + (diagnosticsRoot.parent ? Math.round(diagnosticsRoot.parent.height) : 0)
            }
        }

        Text {
            text: "F3 or click identity to dismiss"
            color: Theme.textDimmed
            font.family: Theme.fontSans
            font.pixelSize: 9
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
