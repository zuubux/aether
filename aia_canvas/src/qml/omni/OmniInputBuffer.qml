import QtQuick
import QtQuick.Controls
import ".."

/**
 * OmniInputBuffer.qml
 * Encapsulates TextField and placeholder logic with dynamic left anchoring and touch target enforcement.
 */
TextField {
    id: inputField
    objectName: "inputField"

    property string modePrefix: ""
    property bool isSpecialMode: modePrefix.length > 0
    property alias inputField: inputField

    signal inputTextChanged()
    signal escapePressed()
    signal tabPressed(bool shiftModifier)
    signal upPressed()
    signal downPressed()
    signal leftPressed()
    signal rightPressed()
    signal returnPressed()

    height: Math.max(Theme.touchHitboxMin, 44)
    verticalAlignment: TextInput.AlignVCenter
    clip: true
    font.family: Theme.fontCode
    font.pixelSize: 14
    color: Theme.textPrimary
    selectByMouse: true
    placeholderText: ""
    background: Item {}
    leftPadding: {
        if (!isSpecialMode) return 0;
        var txt = inputField.text;
        var sigil = modePrefix;
        if (!sigil || !txt.startsWith(sigil)) return 0;
        var prefixToHide = txt.startsWith(sigil + " ") ? (sigil + " ") : sigil;
        return -inputFontMetrics.advanceWidth(prefixToHide);
    }

    FontMetrics {
        id: inputFontMetrics
        font: inputField.font
    }

    Text {
        id: customPlaceholder
        objectName: "customPlaceholderText"
        anchors.left: parent.left
        anchors.leftMargin: Math.max(0, inputField.leftPadding)
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        verticalAlignment: Text.AlignVCenter
        font.family: inputField.font.family
        font.pixelSize: inputField.font.pixelSize
        color: Theme.textMuted
        text: {
            if (inputField.modePrefix === ">") return "Run command...";
            if (inputField.modePrefix === "?") return "Ask AI reasoning engine...";
            if (inputField.modePrefix === "/") return "Execute system command...";
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
        inputField.inputTextChanged();
    }
    
    onAccepted: {
        returnPressed();
    }

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Tab) {
            event.accepted = true;
            tabPressed(event.modifiers & Qt.ShiftModifier);
        } else if (event.key === Qt.Key_Backtab) {
            event.accepted = true;
            tabPressed(true);
        } else if (event.key === Qt.Key_Left) {
            event.accepted = true;
            leftPressed();
        } else if (event.key === Qt.Key_Right) {
            event.accepted = true;
            rightPressed();
        } else if (event.key === Qt.Key_Up) {
            event.accepted = true;
            upPressed();
        } else if (event.key === Qt.Key_Down) {
            event.accepted = true;
            downPressed();
        } else if (event.key === Qt.Key_Escape) {
            event.accepted = true;
            escapePressed();
        }
    }

    function focusInput() {
        inputField.forceActiveFocus();
    }
}
