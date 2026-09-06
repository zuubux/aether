import QtQuick
import QtQuick.Controls
import ".."

/**
 * DialogueDrawer.qml
 * Renders the sliding drawer for conversational AI dialogue output and LLM responses.
 */
Item {
    id: root

    property bool showDialogueOutput: false
    property string dialogueFullText: ""
    property string activePrompt: ""
    property string engineState: "IDLE"
    property var providerMeta: null
    property bool isConversationalMode: false
    property alias dialogueListView: dialogueListView

    signal ascendRequested()

    visible: showDialogueOutput

    Behavior on height { NumberAnimation { duration: Theme.animCollapseDuration; easing.type: Theme.animCollapseEasing } }

    Rectangle {
        id: dialogueDrawerBg
        objectName: "dialogueDrawerBg"
        anchors.fill: parent
        color: "transparent"
    }

    Item {
        id: activePromptHeader
        objectName: "activePromptHeader"
        anchors.top: parent.top
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.right: ascendBtn.left
        anchors.rightMargin: 12
        height: 24
        visible: activePromptText.text !== ""

        Text {
            id: activePromptText
            objectName: "activePromptText"
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter
            text: root.activePrompt ? root.activePrompt.replace(/^[\?\s]+/, "") : ""
            font.family: Theme.fontAiBody.family
            font.pixelSize: 12
            font.italic: true
            color: Theme.textMuted
            elide: Text.ElideRight
        }
    }

    Rectangle {
        id: ascendBtn
        objectName: "ascendBtn"
        anchors.verticalCenter: providerHeaderPill.verticalCenter
        anchors.right: providerHeaderPill.left
        anchors.rightMargin: 8
        width: 22
        height: 22
        radius: 4
        color: ascendMouseArea.containsMouse ? Theme.surfaceHovered : "transparent"
        border.color: ascendMouseArea.containsMouse ? Theme.borderHover : "transparent"
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: "⤢"
            font.pixelSize: 14
            color: ascendMouseArea.containsMouse ? Theme.accentCyan : Theme.textMuted
        }

        ToolTip.visible: ascendMouseArea.containsMouse
        ToolTip.text: "Ascend to Focal Lens (Shift+Enter)"
        ToolTip.delay: 500

        MouseArea {
            id: ascendMouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.ascendRequested()
        }
    }

    ProviderBadge {
        id: providerHeaderPill
        objectName: "providerHeaderPill"
        anchors.top: parent.top
        anchors.topMargin: 10
        anchors.right: parent.right
        anchors.rightMargin: 14
        engineState: root.engineState
        providerMeta: root.providerMeta
        isConversationalMode: root.isConversationalMode
        showDialogueOutput: root.showDialogueOutput
    }

    ScrollView {
        id: dialogueScrollView
        objectName: "dialogueScrollView"
        anchors.top: parent.top
        anchors.topMargin: 42
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        clip: true

        ScrollBar.vertical: ScrollBar {
            id: dialogueScrollBar
            policy: ScrollBar.AsNeeded
            active: true
        }

        ListView {
            id: dialogueListView
            objectName: "dialogueListView"
            width: dialogueScrollView.width - 12
            clip: true
            spacing: 6
            model: [root.dialogueFullText]

            delegate: Text {
                id: dialogueText
                objectName: "dialogueText"
                width: dialogueListView.width
                textFormat: Text.MarkdownText
                text: modelData
                font: Theme.fontAiBody
                lineHeight: 1.3
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                elide: Text.ElideNone
                color: Theme.aiTextColorForRole("dialogue")
            }

            onCountChanged: {
                positionViewAtEnd();
            }
        }
    }
}
