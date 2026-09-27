import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root

    property var modelData: null
    signal clicked()

    // Identity and tier extraction
    readonly property string itemId: modelData ? (modelData.id || modelData.itemId || "") : ""
    readonly property string title: modelData ? (modelData.title || "Feed Item") : "Feed Item"
    readonly property string itemType: modelData ? (modelData.type || "item") : "item"
    readonly property real timestamp: modelData ? (modelData.timestamp || 0) : 0
    readonly property bool isPinned: modelData ? (modelData.is_pinned !== undefined ? modelData.is_pinned : (modelData.isPinned || false)) : false
    readonly property bool isActiveGlow: modelData ? (modelData.is_active_glow !== undefined ? modelData.is_active_glow : (modelData.isActiveGlow || false)) : false
    readonly property bool hasDot: modelData ? (modelData.has_dot !== undefined ? modelData.has_dot : (modelData.hasDot || false)) : false

    // Backend Graduated View Tier: full, compact, fading
    readonly property string viewTier: {
        var t = modelData ? (modelData.view_tier || modelData.viewTier || "full") : "full";
        return ("" + t).toLowerCase();
    }
    readonly property bool isFull: viewTier === "full" || viewTier === "expanded" || viewTier === "hero"
    readonly property bool isCompact: viewTier === "compact" || viewTier === "mid" || viewTier === "standard"
    readonly property bool isFading: viewTier === "fading" || viewTier === "dim" || viewTier === "faded" || viewTier === "tail"

    readonly property string snippetText: {
        if (!modelData) return "";
        if (modelData.snippet) return modelData.snippet;
        var p = modelData.content_payload || modelData.contentPayload || modelData.payload;
        if (p) {
            if (p.text) return p.text;
            if (p.message) return p.message;
            if (p.summary) return p.summary;
            if (p.description) return p.description;
        }
        return "";
    }

    readonly property string typeGlyph: {
        var t = itemType.toLowerCase();
        if (t === "teams" || t === "slack" || t === "chat") return "💬";
        if (t === "code" || t === "git" || t === "pr") return "⌥";
        if (t === "doc" || t === "document" || t === "note") return "📄";
        if (t === "log" || t === "terminal" || t === "deploy") return "⌨";
        if (t === "alert" || t === "error") return "⚠";
        return "⚡";
    }

    // Dynamic Sizing & Geometry: Zero hardcoded pixel traps
    width: parent ? parent.width : 280
    readonly property real baseWidth: width > 0 ? width : 280

    // Dynamic Tier-Adaptive Height
    readonly property real targetHeight: {
        if (isFading) return Math.max(30, Math.round(baseWidth * 0.12));
        if (isCompact) return Math.max(50, Math.round(baseWidth * 0.20));
        return Math.max(92, Math.round(baseWidth * 0.38));
    }
    height: targetHeight

    Behavior on height {
        NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
    }

    // Dynamic Tier-Adaptive Opacity
    readonly property real targetOpacity: {
        if (isFading) return mouseArea.containsMouse ? 0.88 : 0.44;
        if (isCompact) return mouseArea.containsMouse ? 1.0 : 0.88;
        return 1.0;
    }
    opacity: targetOpacity

    Behavior on opacity {
        NumberAnimation { duration: 180 }
    }

    radius: Math.max(5, Math.round(baseWidth * 0.024))
    clip: true

    color: mouseArea.containsMouse
        ? Theme.surfaceHovered
        : (isActiveGlow ? Qt.rgba(0.06, 0.14, 0.22, 0.85) : Theme.surfaceElevated)

    border.width: 1
    border.color: {
        if (isActiveGlow) return Theme.accentCyan;
        if (mouseArea.containsMouse) return Theme.borderHover;
        return Theme.borderSubtle;
    }

    readonly property real padH: Math.max(8, Math.round(baseWidth * 0.038))
    readonly property real padV: Math.max(5, Math.round(height * 0.10))
    Column {
        id: itemCol
        anchors.fill: parent
        anchors.leftMargin: root.padH
        anchors.rightMargin: root.padH
        anchors.topMargin: root.padV
        anchors.bottomMargin: root.padV
        spacing: Math.max(3, Math.round(root.padV * 0.4))

        // Header Row: Dot + Icon + Title + Recency
        Row {
            id: headerRow
            width: parent.width
            spacing: Math.max(4, Math.round(root.padH * 0.5))

            // Unread indicator dot
            Rectangle {
                id: dotIndicator
                visible: root.hasDot
                width: Math.max(5, Math.round(root.height * (root.isFading ? 0.22 : 0.14)))
                height: width
                radius: width * 0.5
                color: root.isActiveGlow ? Theme.accentCyan : "#38BDF8"
                anchors.verticalCenter: parent.verticalCenter
            }

            // Type Icon
            Text {
                id: iconDisplay
                text: root.typeGlyph
                font.pixelSize: Math.max(9, Math.round(root.baseWidth * (root.isFading ? 0.034 : 0.040)))
                anchors.verticalCenter: parent.verticalCenter
                color: root.isActiveGlow ? Theme.accentCyan : (root.isFading ? Theme.textDimmed : Theme.textSecondary)
            }

            // Title
            Text {
                id: titleDisplay
                text: root.title
                color: root.isFading ? Theme.textDimmed : (root.isActiveGlow ? Theme.textPrimary : Theme.textSecondary)
                font.family: Theme.fontSans
                font.pixelSize: {
                    if (root.isFading) return Math.max(9, Math.round(root.baseWidth * 0.034));
                    if (root.isCompact) return Math.max(10, Math.round(root.baseWidth * 0.038));
                    return Math.max(11, Math.round(root.baseWidth * 0.042));
                }
                font.weight: root.isFull ? Font.DemiBold : Font.Normal
                elide: Text.ElideRight
                width: Math.max(60, parent.width - (dotIndicator.visible ? dotIndicator.width + 4 : 0) - iconDisplay.width - recencyDisplay.width - (parent.spacing * 3))
                anchors.verticalCenter: parent.verticalCenter
            }

            // Recency / Time Display
            Text {
                id: recencyDisplay
                text: {
                    if (!root.timestamp || root.timestamp <= 0) return "";
                    var delta = Math.max(0, Math.floor((Date.now() / 1000) - root.timestamp));
                    if (delta < 60) return "now";
                    if (delta < 3600) return Math.floor(delta / 60) + "m";
                    if (delta < 86400) return Math.floor(delta / 3600) + "h";
                    return Math.floor(delta / 86400) + "d";
                }
                color: Theme.textDimmed
                font.family: Theme.fontSans
                font.pixelSize: Math.max(8, Math.round(root.baseWidth * 0.030))
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Snippet Body: Visible in full and compact tiers (hidden in fading)
        Text {
            id: snippetDisplay
            visible: !root.isFading && root.snippetText.length > 0
            text: root.snippetText
            color: root.isFull ? Theme.textSecondary : Theme.textMuted
            font.family: Theme.fontSans
            font.pixelSize: Math.max(9, Math.round(root.baseWidth * (root.isFull ? 0.036 : 0.032)))
            wrapMode: Text.Wrap
            width: parent.width
            maximumLineCount: root.isFull ? 2 : 1
            elide: Text.ElideRight
        }

        // Footer Metadata / Tag Row: Visible in full tier only
        Row {
            id: footerRow
            visible: root.isFull
            width: parent.width
            spacing: Math.max(4, Math.round(root.padH * 0.4))

            // Archetype / Source Pill
            Rectangle {
                height: Math.max(14, Math.round(root.height * 0.16))
                width: Math.round(tagText.width + (height * 0.6))
                radius: Math.round(height * 0.3)
                color: Qt.rgba(1.0, 1.0, 1.0, 0.06)
                border.width: 1
                border.color: Theme.borderSeamSubtle

                Text {
                    id: tagText
                    anchors.centerIn: parent
                    text: root.itemType.toUpperCase()
                    color: Theme.textDimmed
                    font.family: Theme.fontSans
                    font.pixelSize: Math.max(8, Math.round(parent.height * 0.60))
                }
            }

            // Pinned indicator
            Text {
                visible: root.isPinned
                text: "📌 pinned"
                color: Theme.accentCyan
                font.family: Theme.fontSans
                font.pixelSize: Math.max(8, Math.round(root.baseWidth * 0.028))
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        onClicked: {
            if (typeof feedController !== "undefined" && feedController && root.itemId) {
                feedController.markSeen(root.itemId);
            }
            root.clicked();
        }
    }

}
