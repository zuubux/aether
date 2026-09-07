import QtQuick
import QtQuick.Controls
import ".."
import "../hud"

/**
 * OmniInputCapsule.qml
 * Input capsule displaying active mode badges, prefix sigils, and text entry field.
 */
Item {
    id: root

    readonly property bool isSpecialMode: modePrefix.length > 0
    property string modePrefix: ""
    property string effectiveProvider: ""
    property color borderColor: Theme.borderSubtle
    property bool active: false
    property bool isConversationalMode: false
    property bool isShellMode: false
    property bool shelfExpanded: false
    property string engineState: "IDLE"
    property bool isThinking: root.engineState === "STREAMING"
    
    // Properties that will be manipulated directly or read
    property alias inputField: inputField
    property alias text: inputField.text
    property alias cursorPosition: inputField.cursorPosition
    
    // Signals
    signal tabLastQueryChanged(string newQuery)
    signal inputTextChanged()
    signal accepted()
    signal escapePressed()
    signal tabPressed(bool shiftModifier)
    signal upPressed()
    signal downPressed()
    signal leftPressed()
    signal rightPressed()
    signal returnPressed(bool shiftModifier)

    Row {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: root.isConversationalMode ? 40 : 20
        spacing: 10

        // Search Icon when no mode prefix is active
        Text {
            id: prefixIcon
            objectName: "prefixIcon"
            anchors.verticalCenter: parent.verticalCenter
            font.family: Theme.fontCode
            font.pixelSize: 14
            font.bold: true
            color: root.borderColor
            text: "⌕"
            visible: !root.isSpecialMode
        }

        // Integrated Mode Indicator Badge when active in left inset
        Rectangle {
            id: modeBadge
            objectName: "modeBadge"
            anchors.verticalCenter: parent.verticalCenter
            height: 22
            width: modeText.implicitWidth + 12
            radius: 4
            visible: root.isSpecialMode
            color: {
                if (root.modePrefix === ">") return Theme.accentShell; // Shell ('CLI')
                if (root.modePrefix === "?") return Theme.accentAI; // LLM ('AI' or provider badge e.g. 'GEM')
                if (root.modePrefix === "/") return "#10B981"; // System ('SET')
                return "transparent";
            }

            Text {
                id: modeText
                objectName: "modeText"
                anchors.centerIn: parent
                text: {
                    if (root.modePrefix === ">") return "CLI";
                    if (root.modePrefix === "?") {
                        var p = root.effectiveProvider.toLowerCase();
                        if (p === "gemini" || p === "gem") return "GEM";
                        return "AI";
                    }
                    if (root.modePrefix === "/") return "SET";
                    return "";
                }
                font.pixelSize: 10
                font.bold: true
                font.family: Theme.fontCode
                color: "#0B0F19"
            }
        }

        // Mode-Matched Colored & Bold Prefix Sigil
        Text {
            id: modeSigil
            objectName: "modeSigil"
            anchors.verticalCenter: parent.verticalCenter
            visible: root.isSpecialMode
            text: root.modePrefix
            font.bold: true
            font.family: Theme.fontCode
            font.pixelSize: 14
            color: {
                if (root.modePrefix === ">") return Theme.accentShell;
                if (root.modePrefix === "?") return Theme.accentAI;
                if (root.modePrefix === "/") return "#10B981";
                return "transparent";
            }
        }

        FontMetrics {
            id: inputFontMetrics
            font: inputField.font
        }

        TextField {
            id: inputField
            objectName: "inputField"
            width: parent.width - (root.isSpecialMode ? (modeBadge.width + modeSigil.implicitWidth + 20) : prefixIcon.width) - 54
            height: parent.height
            anchors.verticalCenter: parent.verticalCenter
            clip: true
            font.family: Theme.fontCode
            font.pixelSize: 14
            color: Theme.textPrimary
            verticalAlignment: TextInput.AlignVCenter
            selectByMouse: true
            leftPadding: {
                if (!root.isSpecialMode) return 0;
                var txt = inputField.text;
                var sigil = root.modePrefix;
                if (!sigil || !txt.startsWith(sigil)) return 0;
                var prefixToHide = txt.startsWith(sigil + " ") ? (sigil + " ") : sigil;
                return -Math.round(inputFontMetrics.advanceWidth(prefixToHide));
            }
            placeholderText: ""
            background: Item {}

            Text {
                id: customPlaceholder
                objectName: "customPlaceholderText"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                verticalAlignment: Text.AlignVCenter
                font.family: inputField.font.family
                font.pixelSize: inputField.font.pixelSize
                color: Theme.textMuted
                text: {
                    if (root.modePrefix === ">") return "Run command...";
                    if (root.modePrefix === "?") return "Ask AI reasoning engine...";
                    if (root.modePrefix === "/") return "Execute system command...";
                    return "Search nodes, content, or commands...";
                }
                visible: {
                    if (inputField.text.length === 0) return true;
                    var q = inputField.text.trim();
                    if ((q === ">" || q === "?" || q === "/") && inputField.text.trim().length === 1) return true;
                    return false;
                }
            }
            
            onTextChanged: {
                root.inputTextChanged();
            }

            onAccepted: {
                root.accepted();
            }

            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Tab) {
                    root.tabPressed(event.modifiers & Qt.ShiftModifier);
                    event.accepted = true;
                } else if (event.key === Qt.Key_Backtab) {
                    root.tabPressed(true);
                    event.accepted = true;
                } else if (event.key === Qt.Key_Left) {
                    root.leftPressed();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Right) {
                    root.rightPressed();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Up) {
                    root.upPressed();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Down) {
                    root.downPressed();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Escape) {
                    root.escapePressed();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    root.returnPressed(event.modifiers & Qt.ShiftModifier);
                    event.accepted = true;
                }
            }
        }
    }

    Connections {
        target: {
            var conv = (typeof bridge !== "undefined" && bridge && bridge.conversation) ? bridge.conversation : (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.conversation ? canvasBridge.conversation : null);
            if (conv) return conv;
            if (typeof bridge !== "undefined" && bridge) return bridge;
            if (typeof canvasBridge !== "undefined" && canvasBridge) return canvasBridge;
            return null;
        }
        ignoreUnknownSignals: true
        function onEngineStateChanged(state) {
            root.engineState = state;
            root.isThinking = (state === "STREAMING");
        }
        function onResponseFinished(fullText) {
            root.isThinking = false;
            if (root.engineState === "STREAMING") {
                root.engineState = "IDLE";
            }
        }
    }

    AmbientRadarHUD {
        id: capsuleRadar
        objectName: "capsuleRadar"
        compact: true
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        visible: root.isConversationalMode
        engineState: {
            if (root.engineState === "DISTILLING") return "DISTILLING";
            if (root.isThinking || root.engineState === "STREAMING" || root.engineState === "WORKING") return "WORKING";
            return "LATENT";
        }
    }

    function focusInput() {
        inputField.forceActiveFocus();
    }
}
