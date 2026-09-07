import QtQuick
import QtQuick.Controls
import ".."

/**
 * ProviderBadge.qml
 * Dedicated read-only status capsule displaying active LLM provider glyph/icon and model display name.
 */
Rectangle {
    id: root

    property string engineState: "IDLE"
    property var providerMeta: null
    property bool isConversationalMode: false
    property bool showDialogueOutput: false
    property bool showAscendAction: false

    height: 24
    radius: 12
    color: (typeof Theme !== "undefined" && Theme.surfaceRaised) ? Theme.surfaceRaised : Qt.rgba(255, 255, 255, 0.06)
    border.width: 1
    border.color: (typeof Theme !== "undefined" && Theme.borderSubtle) ? Theme.borderSubtle : Qt.rgba(255, 255, 255, 0.1)

    implicitWidth: headerRow.implicitWidth + 16
    implicitHeight: 24
    width: implicitWidth
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
            width: visible ? 12 : 0
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
            color: root.providerMeta ? (root.providerMeta.accent_color || "#38BDF8") : ((typeof Theme !== "undefined" && Theme.accentAI) ? Theme.accentAI : "#38BDF8")
            anchors.verticalCenter: parent.verticalCenter
            visible: !providerIcon.visible && text !== ""
        }

        Text {
            id: nameText
            objectName: "nameText"
            text: root.providerMeta ? (root.providerMeta.display_name || "Flash") : "Flash"
            font.family: (typeof Theme !== "undefined" && Theme.fontSans) ? Theme.fontSans : ""
            font.pixelSize: 10
            color: root.providerMeta ? (root.providerMeta.accent_color || "#38BDF8") : ((typeof Theme !== "undefined" && Theme.accentAI) ? Theme.accentAI : "#38BDF8")
            anchors.verticalCenter: parent.verticalCenter
        }
        Rectangle {
            id: statusIndicatorDot
            objectName: "statusIndicatorDot"
            width: 6
            height: 6
            radius: 3
            anchors.verticalCenter: parent.verticalCenter
            visible: true
            color: root.engineState === "ERROR" ? 
                   ((typeof Theme !== "undefined" && Theme.accentRed) ? Theme.accentRed : "#EF4444") : 
                   ((typeof Theme !== "undefined" && Theme.accentAI) ? Theme.accentAI : "#38BDF8")
            opacity: root.engineState === "ERROR" ? 1.0 : (root.engineState === "STREAMING" ? pulseAnim.pulseVal : 0.5)

            QtObject {
                id: pulseAnim
                property real pulseVal: 0.8
                SequentialAnimation on pulseVal {
                    running: root.engineState === "STREAMING"
                    loops: Animation.Infinite
                    NumberAnimation { from: 1.0; to: 0.2; duration: 600; easing.type: Easing.InOutQuad }
                    NumberAnimation { from: 0.2; to: 1.0; duration: 600; easing.type: Easing.InOutQuad }
                }
            }
        }

    }
}


