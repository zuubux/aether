import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root

    property var modelData: null
    signal clicked()

    // Identity and state extraction
    readonly property string itemId: modelData ? (modelData.id || modelData.itemId || "") : ""
    readonly property string title: modelData ? (modelData.title || "Stream") : "Stream"
    readonly property string itemType: modelData ? (modelData.type || "stream") : "stream"
    readonly property bool isPinned: modelData ? (modelData.is_pinned !== undefined ? modelData.is_pinned : (modelData.isPinned || false)) : false
    readonly property bool isActiveGlow: modelData ? (modelData.is_active_glow !== undefined ? modelData.is_active_glow : (modelData.isActiveGlow || false)) : false
    readonly property bool hasDot: modelData ? (modelData.has_dot !== undefined ? modelData.has_dot : (modelData.hasDot || false)) : false
    readonly property string previewSnippet: {
        if (!modelData) return "";
        if (modelData.snippet) return modelData.snippet;
        var p = modelData.content_payload || modelData.contentPayload || modelData.payload;
        if (p && p.text) return p.text;
        if (p && p.message) return p.message;
        if (p && p.summary) return p.summary;
        return "";
    }

    readonly property string iconGlyph: {
        if (modelData && modelData.icon) return modelData.icon;
        var t = itemType.toLowerCase();
        if (t === "teams" || t === "slack" || t === "chat" || t === "comm") return "💬";
        if (t === "stream" || t === "feed" || t === "build" || t === "log") return "⚡";
        if (t === "mail" || t === "email") return "✉";
        if (t === "code" || t === "git" || t === "repo") return "⌥";
        if (t === "alert" || t === "warning") return "⚠";
        if (t === "doc" || t === "spec") return "📝";
        if (t === "car" || t === "auto" || t === "vehicle") return "🚗";
        return "✦";
    }

    // Dynamic Sizing & Geometry: Zero hardcoded pixel traps
    readonly property real baseHeight: (parent && parent.height > 40) ? Math.min(32, Math.max(26, Math.round(parent.height * 0.72))) : 28
    readonly property real horizontalPadding: 12
    readonly property real innerSpacing: 7

    height: baseHeight
    width: Math.round(contentRow.width + (horizontalPadding * 2))

    // Hover-to-grow scale state
    scale: mouseArea.containsMouse ? 1.06 : 1.0
    Behavior on scale {
        NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
    }

    // Dwell-to-preview tracking
    property bool isDwellPreviewActive: false
    Timer {
        id: dwellTimer
        interval: 320
        running: mouseArea.containsMouse
        repeat: false
        onTriggered: {
            if (mouseArea.containsMouse) root.isDwellPreviewActive = true;
        }
    }

    Rectangle {
        id: pillBody
        anchors.fill: parent
        radius: Math.round(height * 0.5)

        color: root.isActiveGlow
            ? Qt.rgba(0.06, 0.16, 0.26, 0.88)
            : (mouseArea.containsMouse ? Theme.surfaceHovered : Qt.rgba(0.08, 0.11, 0.16, 0.82))

        border.width: 1
        border.color: root.isActiveGlow ? Theme.accentCyan : (mouseArea.containsMouse ? Theme.borderHover : Theme.borderSubtle)

        SequentialAnimation on border.color {
            running: root.isActiveGlow
            loops: Animation.Infinite
            ColorAnimation { to: Theme.accentFocus; duration: 1200; easing.type: Easing.InOutSine }
            ColorAnimation { to: Theme.accentCyan; duration: 1200; easing.type: Easing.InOutSine }
        }

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: root.innerSpacing

            // 1. Icon / Emoji
            Text {
                id: iconText
                text: root.iconGlyph
                font.pixelSize: Math.max(11, Math.round(root.baseHeight * 0.44))
                anchors.verticalCenter: parent.verticalCenter
                color: root.isActiveGlow ? Theme.accentCyan : Theme.textSecondary
            }

            // 2. Title / Label
            Text {
                id: labelText
                text: root.title
                color: root.isActiveGlow ? Theme.textPrimary : (mouseArea.containsMouse ? Theme.textPrimary : Theme.textSecondary)
                font.family: Theme.fontSans
                font.pixelSize: Math.max(11, Math.round(root.baseHeight * 0.40))
                font.weight: root.isActiveGlow ? Font.DemiBold : Font.Normal
                anchors.verticalCenter: parent.verticalCenter
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            // 3. Unread notification dot to the right of the label (matching screenshot & prompt)
            Rectangle {
                id: unreadDot
                visible: root.hasDot
                width: 6
                height: 6
                radius: 3
                color: root.isActiveGlow ? Theme.accentCyan : "#EAB308"
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        onExited: {
            root.isDwellPreviewActive = false;
            dwellTimer.stop();
        }

        onClicked: {
            if (typeof feedController !== "undefined" && feedController && root.itemId) {
                feedController.markSeen(root.itemId);
            }
            root.clicked();
        }
    }
    // Dwell-to-Preview Popover Floating Card
    Rectangle {
        id: previewCard
        z: 250
        visible: opacity > 0.01
        opacity: root.isDwellPreviewActive ? 1.0 : 0.0

        Behavior on opacity {
            NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
        }

        anchors.top: pillBody.bottom
        anchors.topMargin: Math.max(6, Math.round(root.baseHeight * 0.25))
        anchors.right: pillBody.right

        width: Math.max(180, Math.round(root.width * 1.8))
        height: Math.round(previewCol.height + (previewPadding * 2))
        readonly property real previewPadding: Math.max(8, Math.round(root.baseHeight * 0.35))

        radius: Math.max(6, Math.round(root.baseHeight * 0.25))
        color: Theme.surfaceElevated
        border.width: 1
        border.color: root.isActiveGlow ? Theme.accentCyan : Theme.borderSubtle

        Column {
            id: previewCol
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: previewCard.previewPadding
            spacing: Math.max(4, Math.round(previewCard.previewPadding * 0.4))

            Row {
                width: parent.width
                spacing: Math.max(4, Math.round(root.baseHeight * 0.2))

                Text {
                    text: root.iconGlyph
                    font.pixelSize: Math.max(10, Math.round(root.baseHeight * 0.42))
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: root.title
                    color: Theme.textPrimary
                    font.family: Theme.fontSans
                    font.pixelSize: Math.max(11, Math.round(root.baseHeight * 0.42))
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    width: parent.width - (root.baseHeight * 0.6)
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Theme.borderSeamSubtle
            }

            Text {
                text: root.previewSnippet ? root.previewSnippet : ("Active stream // " + root.itemType.toUpperCase())
                color: Theme.textSecondary
                font.family: Theme.fontSans
                font.pixelSize: Math.max(10, Math.round(root.baseHeight * 0.36))
                wrapMode: Text.Wrap
                width: parent.width
                maximumLineCount: 3
                elide: Text.ElideRight
            }

            Text {
                text: root.hasDot ? "● Unread notifications" : "✓ Up to date"
                color: root.hasDot ? Theme.accentCyan : Theme.textDimmed
                font.family: Theme.fontSans
                font.pixelSize: Math.max(9, Math.round(root.baseHeight * 0.32))
            }
        }
    }

}
