import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root

    property bool showDialogueOutput: false
    property string dialogueFullText: ""
    property string engineState: "IDLE"
    property var providerMeta: null
    property bool isConversationalMode: false

    visible: showDialogueOutput

    Behavior on height { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

    Rectangle {
        id: dialogueDrawerBg
        objectName: "dialogueDrawerBg"
        anchors.fill: parent
        color: "transparent"
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

    Text {
        id: dialogueTextDummy
        objectName: "dialogueTextDummy"
        visible: false
        width: Math.max(100, dialogueScrollView.width - 12)
        textFormat: Text.MarkdownText
        text: "<style>code, pre { font-family: '" + Theme.fontAiCode.family + "', monospace; font-size: 12px; }</style>" + root.dialogueFullText
        font.family: Theme.fontAiBody.family
        font.pixelSize: 13
        lineHeight: 1.3
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        elide: Text.ElideNone
    }

    ScrollView {
        id: dialogueScrollView
        objectName: "dialogueScrollView"
        anchors.top: parent.top
        anchors.topMargin: 34
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
                text: "<style>code, pre { font-family: '" + Theme.fontAiCode.family + "', monospace; font-size: 12px; }</style>" + modelData
                font.family: Theme.fontAiBody.family
                font.pixelSize: 13
                lineHeight: 1.3
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                elide: Text.ElideNone
                color: Theme.textPrimary
            }

            onCountChanged: {
                positionViewAtEnd();
            }
        }
    }
}
