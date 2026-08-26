import QtQuick
import ".."

Rectangle {
    id: root

    property string engineState: "IDLE"
    property var providerMeta: null
    property bool isConversationalMode: false
    property bool showDialogueOutput: false

    color: Theme.surfaceElevated
    opacity: 0.3
    radius: 4
    border.color: Theme.borderSubtle
    border.width: 1
    implicitWidth: headerRow.implicitWidth + 8
    implicitHeight: headerRow.implicitHeight + 8
    z: 10

    Row {
        id: headerRow
        objectName: "headerRow"
        anchors.centerIn: parent
        spacing: 6

        Rectangle {
            id: statusIndicatorDot
            objectName: "statusIndicatorDot"
            width: 6
            height: 6
            radius: 3
            color: root.engineState === "ERROR" ? Theme.accentRed : (root.providerMeta ? (root.providerMeta.accent_color || "#38BDF8") : Theme.accentAI)
            opacity: root.engineState === "ERROR" ? 1.0 : (root.engineState === "IDLE" ? 0.5 : 1.0)
            anchors.verticalCenter: parent.verticalCenter
            visible: root.isConversationalMode && root.showDialogueOutput

            SequentialAnimation on opacity {
                running: statusIndicatorDot.visible && root.engineState === "STREAMING"
                loops: Animation.Infinite
                PropertyAnimation { to: 0.3; duration: 800; easing.type: Easing.InOutSine }
                PropertyAnimation { to: 1.0; duration: 800; easing.type: Easing.InOutSine }
            }
        }

        Text {
            id: glyphText
            objectName: "glyphText"
            text: root.providerMeta ? (root.providerMeta.icon_glyph || "✦") : "✦"
            font.pixelSize: 11
            color: root.providerMeta ? (root.providerMeta.accent_color || "#38BDF8") : Theme.accentAI
            anchors.verticalCenter: parent.verticalCenter
            visible: text !== ""
        }

        Text {
            id: nameText
            objectName: "nameText"
            text: root.providerMeta ? (root.providerMeta.display_name || "Flash") : "Flash"
            font.family: typeof Theme !== "undefined" && Theme.fontAiCode ? Theme.fontAiCode.family : ""
            font.pixelSize: 10
            color: root.providerMeta ? (root.providerMeta.accent_color || "#38BDF8") : Theme.accentAI
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
