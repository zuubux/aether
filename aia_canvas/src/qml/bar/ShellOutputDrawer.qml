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
        anchors.left: parent.left
        anchors.leftMargin: 20
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.bottom: systemStatusFooter.visible ? systemStatusFooter.top : parent.bottom
        clip: true

        ScrollBar.vertical: ScrollBar {
            id: shellScrollBar
            policy: ScrollBar.AsNeeded
            active: true
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
                width: shellListView.width
                visible: (modelData.title || modelData.line || "") !== ""
                height: visible ? lineText.implicitHeight : 0

                Text {
                    id: lineText
                    objectName: "shellLineText"
                    width: parent.width
                    textFormat: Text.RichText
                    text: modelData.title || modelData.line || ""
                    font.family: Theme.fontCode || "monospace"
                    font.pixelSize: 12
                    lineHeight: 1.35
                    wrapMode: Text.WrapAnywhere
                    color: {
                        if (modelData.is_tui_warning || modelData.color === "amber" || (modelData.line && modelData.line.indexOf("Interactive TUI") !== -1)) return Theme.accentShell;
                        if (modelData.stream === "stderr") return Theme.ansiRed;
                        if (modelData.stream === "system") {
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
        height: 20
        visible: root.systemStatusItem !== null

        Text {
            id: systemStatusText
            objectName: "systemStatusText"
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter
            text: root.systemStatusItem ? (root.systemStatusItem.title || root.systemStatusItem.line || "") : ""
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
