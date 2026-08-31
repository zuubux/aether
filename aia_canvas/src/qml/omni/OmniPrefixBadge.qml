import QtQuick
import QtQuick.Controls
import ".."

/**
 * OmniPrefixBadge.qml
 * Displays mode pills ('AI ?', 'CLI >', 'SET /') with explicit fixed bounds and zero text overlap.
 */
Item {
    id: root

    property string modePrefix: ""
    property string effectiveProvider: ""
    property color borderColor: Theme.borderSubtle
    readonly property bool isSpecialMode: modePrefix.length > 0

    implicitWidth: isSpecialMode ? modePrefixRow.width : prefixIcon.width
    implicitHeight: Math.max(Theme.touchHitboxMin, 32)

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

    // Integrated Mode Indicator Badge & Sigil Row when active
    Row {
        id: modePrefixRow
        objectName: "modePrefixRow"
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
        visible: root.isSpecialMode

        Rectangle {
            id: modeBadge
            objectName: "modeBadge"
            anchors.verticalCenter: parent.verticalCenter
            height: 22
            width: Math.max(36, modeText.implicitWidth + 12)
            radius: 4
            color: {
                if (root.modePrefix === ">") return Theme.accentShell; // Shell ('CLI')
                if (root.modePrefix === "?") return Theme.accentAI;    // LLM ('AI' / 'GEM')
                if (root.modePrefix === "/") return "#10B981";         // System ('SET')
                return "transparent";
            }

            Text {
                id: modeText
                objectName: "modeText"
                anchors.centerIn: parent
                text: {
                    if (root.modePrefix === ">") return "CLI";
                    if (root.modePrefix === "?") {
                        var p = (root.effectiveProvider || "").toLowerCase();
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

        Text {
            id: modeSigil
            objectName: "modeSigil"
            anchors.verticalCenter: parent.verticalCenter
            text: root.modePrefix
            font.pixelSize: 14
            font.bold: true
            font.family: Theme.fontCode
            color: {
                if (root.modePrefix === ">") return Theme.accentShell;
                if (root.modePrefix === "?") return Theme.accentAI;
                if (root.modePrefix === "/") return "#10B981";
                return Theme.textPrimary;
            }
        }
    }
}
