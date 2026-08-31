import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../bar"

/**
 * OmniDialogueSurface.qml
 * Ephemeral slide-out dialogue container presenting streaming AI text in Theme.fontAiVoice, action chips, and provider metadata.
 */
Item {
    id: root
    objectName: "dialogueDrawer"

    property bool showDialogueOutput: false
    property string dialogueFullText: ""
    property string activePrompt: ""
    property string engineState: "IDLE"
    property var providerMeta: null
    property bool isConversationalMode: false
    property alias dialogueListView: dialogueListView

    visible: showDialogueOutput || height > 0

    Behavior on height { NumberAnimation { duration: Theme.animCollapseDuration; easing.type: Theme.animCollapseEasing } }

    function formatDialogueMarkdown(rawText) {
        if (!rawText) return "";
        var clean = rawText;

        // Ensure bullet items starting with bold tags (e.g., "* **Lead:**" or "- **Lead:**") parse cleanly
        clean = clean.replace(/^(\s*[\*\-\+])(\*\*[^*]+)/gm, "$1 $2");

        return clean;
    }

    Rectangle {
        id: dialogueDrawerBg
        objectName: "dialogueDrawerBg"
        anchors.fill: parent
        color: Theme.surfaceGlass
        border.color: root.engineState === "STREAMING" ? Theme.accentAI : Theme.borderFrosted
        border.width: 1
        radius: 12
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Active Prompt & Provider Badge Header Row
        Item {
            id: activePromptRow
            objectName: "activePromptRow"
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            Layout.leftMargin: 16
            Layout.rightMargin: 14
            Layout.topMargin: 4

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: providerHeaderPill.left
                anchors.rightMargin: 8
                spacing: 8
                clip: true

                Text {
                    text: "?"
                    font.family: Theme.fontCode
                    font.pixelSize: 14
                    font.bold: true
                    color: Theme.accentAI
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    id: promptTextDisplay
                    objectName: "promptTextDisplay"
                    text: {
                        var p = root.activePrompt || "";
                        return p.startsWith("?") ? p.substring(1).trim() : p;
                    }
                    font.family: Theme.fontUi
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    font.italic: true
                    color: "#94A3B8"
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            ProviderBadge {
                id: providerHeaderPill
                objectName: "providerHeaderPill"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                engineState: root.engineState
                providerMeta: root.providerMeta
                isConversationalMode: root.isConversationalMode
                showDialogueOutput: root.showDialogueOutput
            }
        }

        // Subtle Horizontal Rule Separator
        Rectangle {
            id: promptSeparator
            objectName: "promptSeparator"
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
            opacity: 0.6
        }

        // Dedicated Scrollable Response Body Viewport
        ScrollView {
            id: dialogueScrollView
            objectName: "dialogueScrollView"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.topMargin: 12
            Layout.bottomMargin: 12
            Layout.leftMargin: 16
            Layout.rightMargin: 16
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
                    text: root.formatDialogueMarkdown(modelData)
                    font.family: Theme.fontAiBody
                    font.pixelSize: 14
                    font.weight: Font.Normal
                    lineHeight: 1.4
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    elide: Text.ElideNone
                    color: Theme.aiTextColorForRole("dialogue")
                }

                onCountChanged: {
                    positionViewAtEnd();
                }
            }
        }

        // Action Bar Baseline
        Item {
            id: actionChipsRowContainer
            objectName: "actionChipsRowContainer"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(Theme.touchHitboxMin, 32)
            Layout.topMargin: 4
            Layout.bottomMargin: 8
            Layout.leftMargin: 16
            Layout.rightMargin: 16

            Item {
                id: actionChipsRow
                objectName: "actionChipsRow"
                anchors.fill: parent

                // Copy Chip Action aligned bottom-right (maintained minimum 44px hitbox)
                Rectangle {
                    id: copyChip
                    objectName: "copyChip"
                    height: 24
                    width: 56
                    radius: 12
                    color: copyMouse.containsMouse ? Theme.surfaceButtonHover : Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "Copy"
                        font.family: Theme.fontSans
                        font.pixelSize: 11
                        color: Theme.textSecondary
                    }

                    MouseArea {
                        id: copyMouse
                        objectName: "copyMouse"
                        anchors.centerIn: parent
                        width: Math.max(Theme.touchHitboxMin, parent.width)
                        height: Math.max(Theme.touchHitboxMin, parent.height)
                        hoverEnabled: true
                        onClicked: {
                            var cleanPrompt = root.activePrompt || "";
                            if (cleanPrompt.startsWith("?")) cleanPrompt = cleanPrompt.substring(1).trim();
                            var formattedCopy = "Prompt: " + cleanPrompt + "\n\nResponse: " + root.dialogueFullText;
                            if (typeof bridge !== "undefined" && bridge && bridge.clipboard) {
                                bridge.clipboard.set_text(formattedCopy);
                            } else if (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.clipboard) {
                                canvasBridge.clipboard.set_text(formattedCopy);
                            }
                        }
                    }
                }
            }
        }
    }
}
