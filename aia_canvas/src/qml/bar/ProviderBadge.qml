import QtQuick
import ".."

/**
 * ProviderBadge.qml
 * Header status badge displaying active LLM provider name, SVG vector icon, and streaming indicator dot.
 * Entirely frameless/boxless container with reordered elements: Icon/Glyph -> Name -> Active Status Dot.
 */
Item {
    id: root

    property string engineState: "IDLE"
    property var providerMeta: null
    property bool isConversationalMode: false
    property bool showDialogueOutput: false

    implicitWidth: headerRow.implicitWidth
    implicitHeight: headerRow.implicitHeight
    width: implicitWidth
    height: implicitHeight
    z: 10

    function getIconSource(meta) {
        if (!meta) return "";
        var path = meta.icon_path || "";
        if (!path && meta.id) {
            path = "assets/icons/providers/" + meta.id + ".svg";
        }
        if (!path) return "";

        if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("file://") || path.startsWith("qrc:/")) {
            return path;
        }
        if (path.startsWith("/")) {
            return "file://" + path;
        }
        if (path.startsWith("aia_canvas/")) {
            path = path.substring(11);
        }
        if (path.startsWith("assets/")) {
            return "../../../" + path;
        }
        return "../../../assets/icons/providers/" + path;
    }

    Row {
        id: headerRow
        objectName: "headerRow"
        anchors.centerIn: parent
        spacing: 6

        Image {
            id: providerIcon
            objectName: "providerIcon"
            width: 12
            height: 12
            sourceSize.width: 12
            sourceSize.height: 12
            anchors.verticalCenter: parent.verticalCenter
            fillMode: Image.PreserveAspectFit
            smooth: true
            visible: status === Image.Ready && source !== ""
            source: root.getIconSource(root.providerMeta)
        }

        Text {
            id: glyphText
            objectName: "glyphText"
            text: root.providerMeta ? (root.providerMeta.icon_glyph || "✦") : "✦"
            font.pixelSize: 11
            color: root.providerMeta ? (root.providerMeta.accent_color || "#38BDF8") : Theme.accentAI
            anchors.verticalCenter: parent.verticalCenter
            visible: !providerIcon.visible && text !== ""
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
    }
}
