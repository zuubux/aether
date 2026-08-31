import QtQuick
import QtQuick.Controls
import ".."

/**
 * ShellOutputDrawer.qml
 * Sliding terminal output drawer displaying rich text process output lines and system status.
 */
Item {
    id: root
    
    property bool showShellOutput: false
    property var shellOutputModel: []
    property var systemStatusItem: null
    property alias shellListView: shellListView

    visible: showShellOutput

    function getItemText(item) {
        if (!item) return "";
        if (typeof item === "string") return item;
        return item.title || item.line || "";
    }

    function isValidOutputText(item) {
        if (!item) return false;
        var txt = getItemText(item).trim();
        if (txt === "" || txt.length <= 1) return false;
        // Strictly check if text starts with a backslash followed by a character (e.g. \S, \r, \m, \l)
        if (/^\\./.test(txt)) return false;
        // Strictly check if text contains only non-printable control characters
        if (txt.replace(/[\x00-\x1F\x7F-\x9F\u200B-\u200D\uFEFF]/g, "").trim() === "") return false;
        return true;
    }

    Behavior on height { NumberAnimation { duration: Theme.animCollapseDuration; easing.type: Theme.animCollapseEasing } }

    Rectangle {
        id: shellDrawerBg
        objectName: "shellDrawerBg"
        anchors.fill: parent
        color: "transparent"
    }

    ScrollView {
        id: shellScrollView
        objectName: "shellScrollView"
        anchors.top: parent.top
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.leftMargin: 20
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.bottom: systemStatusFooter.visible ? systemStatusFooter.top : parent.bottom
        clip: true

        ScrollBar.vertical: ScrollBar {
            id: shellScrollBar
            policy: ScrollBar.AsNeeded
        }

        ListView {
            id: shellListView
            objectName: "shellListView"
            width: shellScrollView.width
            clip: true
            topMargin: 24
            bottomMargin: 12
            spacing: 4
            model: root.shellOutputModel

            delegate: Item {
                id: lineDelegate
                width: shellListView.width
                visible: root.isValidOutputText(modelData)
                height: visible ? lineText.implicitHeight : 0

                Text {
                    id: lineText
                    objectName: "shellLineText"
                    width: parent.width
                    visible: lineDelegate.visible
                    textFormat: Text.RichText
                    text: root.getItemText(modelData)
                    font.family: Theme.fontCode || "monospace"
                    font.pixelSize: 12
                    lineHeight: 1.35
                    wrapMode: Text.WrapAnywhere
                    color: {
                        if (modelData && (modelData.is_tui_warning || modelData.color === "amber" || (modelData.line && modelData.line.indexOf("Interactive TUI") !== -1))) return Theme.accentShell;
                        if (modelData && modelData.stream === "stderr") return Theme.ansiRed;
                        if (modelData && modelData.stream === "system") {
                            if (modelData.exit_code === 0) return Theme.ansiGreen;
                            if (modelData.exit_code !== undefined && modelData.exit_code !== 0) return Theme.ansiRed;
                            return Theme.textMuted;
                        }
                        return Theme.textPrimary;
                    }
                }
            }

            onCountChanged: {
                positionViewAtEnd();
            }
        }
    }

    Item {
        id: systemStatusFooter
        objectName: "systemStatusFooter"
        anchors.left: parent.left
        anchors.leftMargin: 20
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        height: visible ? 20 : 0
        visible: root.systemStatusItem !== null && root.isValidOutputText(root.systemStatusItem)

        Text {
            id: systemStatusText
            objectName: "systemStatusText"
            anchors.fill: parent
            visible: systemStatusFooter.visible
            verticalAlignment: Text.AlignVCenter
            text: root.getItemText(root.systemStatusItem)
            font.family: Theme.fontCode
            font.pixelSize: 11
            font.bold: true
            color: {
                if (!root.systemStatusItem) return Theme.textMuted;
                if (root.systemStatusItem.is_tui_warning || root.systemStatusItem.color === "amber") return "#F59E0B";
                return "#EF4444";
            }
        }
    }
}


