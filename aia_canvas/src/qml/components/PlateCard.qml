import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root

    property var modelData: null
    property var bentoAlloc: null
    property bool isFocal: false
    signal clicked()

    // Identity extraction
    readonly property int plateId: {
        if (!modelData) return 0;
        if (modelData.node_id !== undefined) return parseInt(modelData.node_id);
        if (modelData.nodeId !== undefined) return parseInt(modelData.nodeId);
        if (modelData.id !== undefined) return parseInt(modelData.id);
        return 0;
    }

    readonly property string filePath: modelData ? (modelData.file_path || modelData.filePath || modelData.path || "") : ""
    readonly property string fileName: modelData ? (modelData.file_name || modelData.fileName || "") : ""
    readonly property string displayTitle: {
        if (!modelData) return "Plate";
        if (modelData.display_title) return modelData.display_title;
        if (modelData.displayTitle) return modelData.displayTitle;
        if (fileName) return fileName;
        return "Plate #" + plateId;
    }
    readonly property string extension: {
        if (modelData && modelData.extension) return ("" + modelData.extension).replace(/^\./, "");
        if (fileName && fileName.lastIndexOf(".") !== -1) return fileName.slice(fileName.lastIndexOf(".") + 1);
        return "";
    }
    readonly property string archetype: modelData ? (modelData.archetype || "document") : "document"
    readonly property string snippetText: modelData ? (modelData.snippet || "") : ""
    readonly property string previewUrl: {
        if (!modelData) return "";
        if (modelData.preview_path) return modelData.preview_path;
        if (modelData.previewUrl) return modelData.previewUrl;
        if (modelData.thumbnail_url) return modelData.thumbnail_url;
        if (modelData.thumbnail) return modelData.thumbnail;
        return filePath;
    }
    readonly property string aiSummaryText: modelData ? (modelData.ai_summary || modelData.aiSummary || "") : ""
    readonly property bool isPinned: {
        if (!modelData) return false;
        if (modelData.is_pinned !== undefined) return modelData.is_pinned;
        if (modelData.isPinned !== undefined) return modelData.isPinned;
        if (modelData.temporal && modelData.temporal.is_pinned !== undefined) return modelData.temporal.is_pinned;
        return false;
    }

    // Selection State
    readonly property bool isSelected: {
        if (isFocal) return true;
        if (typeof plateCanvasController !== "undefined" && plateCanvasController && plateCanvasController.focalPlateId === plateId && plateId > 0) {
            return true;
        }
        return false;
    }

    // Single-key AI summary drawer toggle
    property bool isSummaryOpen: false

    // Bento Geometry Positioning: Fluid ratio scaling with zero hardcoded pixel traps
    readonly property real targetX: bentoAlloc ? bentoAlloc.x : (modelData && modelData.x !== undefined ? modelData.x : 0)
    readonly property real targetY: bentoAlloc ? bentoAlloc.y : (modelData && modelData.y !== undefined ? modelData.y : 0)
    readonly property real targetWidth: bentoAlloc ? bentoAlloc.width : (modelData && modelData.width !== undefined ? modelData.width : (parent ? parent.width * 0.45 : 360))
    readonly property real targetHeight: bentoAlloc ? bentoAlloc.height : (modelData && modelData.height !== undefined ? modelData.height : (parent ? parent.height * 0.40 : 240))

    x: targetX
    y: targetY
    width: targetWidth
    height: targetHeight

    Behavior on x { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on y { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on width { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on height { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }

    z: isSelected ? 40 : 10
    radius: Math.max(8, Math.round(Math.min(width, height) * 0.032))
    clip: true

    // Visual Card Shell
    color: isSelected ? Qt.rgba(0.09, 0.13, 0.20, 0.95) : Qt.rgba(0.06, 0.08, 0.12, 0.88)
    border.width: isSelected ? 2 : 1
    border.color: isSelected ? Theme.accentFocus : (cardHoverArea.containsMouse ? Theme.borderHover : Theme.borderSubtle)

    readonly property color archetypeBadgeColor: Theme.getBadgeColor(extension, archetype)

    // Archetype categorization
    readonly property bool isLog: {
        var ext = extension.toLowerCase();
        var f = fileName.toLowerCase();
        var t = displayTitle.toLowerCase();
        return ext === "log" || f.endsWith(".log") || t.endsWith(".log") || archetype === "log";
    }
    readonly property bool isVisual: {
        var a = archetype.toLowerCase();
        return a === "image" || a === "media" || a === "video";
    }
    // Title Bar
    Rectangle {
        id: titleBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: Math.max(30, Math.min(44, Math.round(root.height * 0.13)))
        color: Qt.rgba(0.04, 0.06, 0.10, 0.70)

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.borderSeamSubtle
        }

        Row {
            id: titleLeftRow
            anchors.left: parent.left
            anchors.leftMargin: Math.max(8, Math.round(titleBar.height * 0.28))
            anchors.verticalCenter: parent.verticalCenter
            spacing: Math.max(6, Math.round(titleBar.height * 0.22))
            width: parent.width - titleRightRow.width - (anchors.leftMargin * 2)

            Rectangle {
                id: archetypePill
                height: Math.max(16, Math.round(titleBar.height * 0.56))
                width: Math.round(archetypeLabel.width + (height * 0.65))
                radius: Math.round(height * 0.3)
                color: Qt.rgba(root.archetypeBadgeColor.r, root.archetypeBadgeColor.g, root.archetypeBadgeColor.b, 0.18)
                border.width: 1
                border.color: root.archetypeBadgeColor
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    id: archetypeLabel
                    anchors.centerIn: parent
                    text: root.extension ? Theme.normalizeExt(root.extension) : root.archetype.toUpperCase()
                    color: root.archetypeBadgeColor
                    font.family: Theme.fontCode
                    font.pixelSize: Math.max(8, Math.round(parent.height * 0.62))
                    font.weight: Font.DemiBold
                }
            }

            Text {
                id: titleText
                text: root.displayTitle
                color: root.isSelected ? Theme.textPrimary : Theme.textSecondary
                font.family: Theme.fontSans
                font.pixelSize: Math.max(11, Math.round(titleBar.height * 0.38))
                font.weight: Font.Medium
                elide: Text.ElideRight
                width: Math.max(40, parent.width - archetypePill.width - parent.spacing)
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Row {
            id: titleRightRow
            anchors.right: parent.right
            anchors.rightMargin: Math.max(8, Math.round(titleBar.height * 0.28))
            anchors.verticalCenter: parent.verticalCenter
            spacing: Math.max(4, Math.round(titleBar.height * 0.16))

            // Single-key AI summary badge / toggle
            Rectangle {
                id: aiSummaryBadge
                height: Math.max(18, Math.round(titleBar.height * 0.60))
                width: Math.round(aiSummaryRow.width + (height * 0.6))
                radius: Math.round(height * 0.32)
                color: (root.isSummaryOpen || root.aiSummaryText.length > 0)
                    ? Qt.rgba(0.08, 0.22, 0.32, 0.85)
                    : Qt.rgba(1.0, 1.0, 1.0, 0.05)
                border.width: 1
                border.color: (root.isSummaryOpen || root.aiSummaryText.length > 0)
                    ? Theme.accentCyan
                    : Theme.borderSeamSubtle
                anchors.verticalCenter: parent.verticalCenter

                Row {
                    id: aiSummaryRow
                    anchors.centerIn: parent
                    spacing: 3

                    Text {
                        text: "✦"
                        color: Theme.accentCyan
                        font.pixelSize: Math.max(9, Math.round(parent.parent.height * 0.58))
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: "AI"
                        color: (root.isSummaryOpen || root.aiSummaryText.length > 0)
                            ? Theme.aiVoiceGlacial
                            : Theme.textDimmed
                        font.family: Theme.fontSans
                        font.pixelSize: Math.max(9, Math.round(parent.parent.height * 0.54))
                        font.weight: Font.DemiBold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (!root.aiSummaryText && typeof plateCanvasController !== "undefined" && plateCanvasController && root.plateId > 0) {
                            plateCanvasController.getAiSummary(root.plateId);
                        }
                        root.isSummaryOpen = !root.isSummaryOpen;
                    }
                }
            }
            // Pin toggle button
            Rectangle {
                id: pinButton
                height: Math.max(18, Math.round(titleBar.height * 0.60))
                width: height
                radius: Math.round(height * 0.3)
                color: root.isPinned ? Qt.rgba(0.2, 0.6, 0.8, 0.2) : Qt.rgba(1.0, 1.0, 1.0, 0.05)
                border.width: 1
                border.color: root.isPinned ? Theme.accentCyan : Theme.borderSeamSubtle
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: "📌"
                    font.pixelSize: Math.max(9, Math.round(parent.height * 0.55))
                    opacity: root.isPinned ? 1.0 : 0.45
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof plateCanvasController !== "undefined" && plateCanvasController && root.plateId > 0) {
                            plateCanvasController.togglePin(root.plateId);
                        }
                    }
                }
            }

            // Close button
            Rectangle {
                id: closeButton
                height: Math.max(18, Math.round(titleBar.height * 0.60))
                width: height
                radius: Math.round(height * 0.3)
                color: closeHoverArea.containsMouse ? Qt.rgba(0.9, 0.2, 0.2, 0.25) : Qt.rgba(1.0, 1.0, 1.0, 0.05)
                border.width: 1
                border.color: closeHoverArea.containsMouse ? Theme.accentRed : Theme.borderSeamSubtle
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: closeHoverArea.containsMouse ? Theme.accentRed : Theme.textDimmed
                    font.pixelSize: Math.max(9, Math.round(parent.height * 0.50))
                }

                MouseArea {
                    id: closeHoverArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof plateCanvasController !== "undefined" && plateCanvasController && root.plateId > 0) {
                            plateCanvasController.closePlate(root.plateId);
                        }
                    }
                }
            }

        }
    }

    // Content Body Area: Strictly bounded
    Rectangle {
        id: contentContainer
        anchors.top: titleBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        color: "transparent"
        clip: true

        // 1. Log Card Container: Monospace styling inside container card
        Rectangle {
            id: logContainer
            visible: root.isLog
            anchors.fill: parent
            color: Qt.rgba(0.02, 0.03, 0.05, 0.98)

            Rectangle {
                id: logStatusBar
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: Math.max(18, Math.round(root.height * 0.08))
                color: Qt.rgba(0.05, 0.07, 0.10, 0.90)

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 8

                    Text {
                        text: "$ tail -f " + (root.fileName ? root.fileName : "system.log")
                        color: Theme.ansiGreen
                        font.family: Theme.fontCode
                        font.pixelSize: Math.max(8, Math.round(logStatusBar.height * 0.55))
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Item { width: 8; height: 1 }

                    Text {
                        text: "[LIVE TTY]"
                        color: Theme.accentCyan
                        font.family: Theme.fontCode
                        font.pixelSize: Math.max(8, Math.round(logStatusBar.height * 0.50))
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            Flickable {
                id: logFlickable
                anchors.top: logStatusBar.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: Math.max(6, Math.round(root.width * 0.025))
                contentWidth: width
                contentHeight: logText.implicitHeight
                clip: true

                Text {
                    id: logText
                    width: parent.width
                    text: root.snippetText ? root.snippetText : (
                        "[00:00:01.104] INFO  aether::kernel initializing memory map...\n" +
                        "[00:00:01.218] INFO  weaver_ipc connecting to unix socket: /tmp/weaver.sock\n" +
                        "[00:00:01.352] DEBUG bento::allocator compute_grid_geometry: 12-col sync\n" +
                        "[00:00:01.490] INFO  storage::sqlite WAL mode activated\n" +
                        "[00:00:01.611] OK    telemetry horizon bar active // 60.0 FPS\n" +
                        "[00:00:01.780] INFO  subsystem ready. listening for graph delta streams..."
                    )
                    color: Theme.ansiGreen
                    font.family: Theme.fontCode
                    font.pixelSize: Math.max(9, Math.round(Math.min(root.width, root.height) * 0.042))
                    wrapMode: Text.Wrap
                    lineHeight: 1.35
                }
            }
        }

        // 2. Visual / Image Card Body
        Item {
            id: visualContainer
            visible: root.isVisual && !root.isLog
            anchors.fill: parent

            Image {
                id: previewImage
                anchors.fill: parent
                source: root.previewUrl
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                clip: true

                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 1.0; color: Qt.rgba(0.04, 0.06, 0.09, 0.5) }
                    }
                }
            }
        }
        // 3. Document / Code / Data Card Body
        Item {
            id: docContainer
            visible: !root.isVisual && !root.isLog
            anchors.fill: parent

            Flickable {
                anchors.fill: parent
                anchors.margins: Math.max(8, Math.round(root.width * 0.035))
                contentWidth: width
                contentHeight: docSnippet.implicitHeight
                clip: true

                Text {
                    id: docSnippet
                    width: parent.width
                    text: root.snippetText ? root.snippetText : "Document content ready. Open in focal stage or trigger AI summary for distilled extraction."
                    color: Theme.textSecondary
                    font.family: root.archetype === "code" ? Theme.fontCode : Theme.fontSans
                    font.pixelSize: Math.max(9, Math.round(Math.min(root.width, root.height) * 0.044))
                    wrapMode: Text.Wrap
                    lineHeight: 1.35
                }
            }
        }

        // AI Summary Slide-Up Drawer Overlay
        Rectangle {
            id: summaryDrawer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: root.isSummaryOpen ? Math.round(parent.height * 0.75) : 0
            visible: height > 0
            color: Qt.rgba(0.05, 0.12, 0.18, 0.96)
            border.width: 1
            border.color: Theme.accentCyan
            clip: true

            Behavior on height {
                NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
            }

            Column {
                anchors.fill: parent
                anchors.margins: Math.max(8, Math.round(parent.width * 0.035))
                spacing: 6

                Row {
                    width: parent.width
                    spacing: 6

                    Text {
                        text: "✦ AI SYNTHESIS"
                        color: Theme.accentCyan
                        font.family: Theme.fontCode
                        font.pixelSize: Math.max(9, Math.round(root.height * 0.05))
                        font.weight: Font.DemiBold
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Item { width: 10; height: 1 }

                    Text {
                        text: "✕"
                        color: Theme.textDimmed
                        font.pixelSize: 10
                        anchors.verticalCenter: parent.verticalCenter

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.isSummaryOpen = false
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Theme.borderSeamSubtle
                }

                Text {
                    width: parent.width
                    text: root.aiSummaryText ? root.aiSummaryText : "Extracting synthesis summary from plate context..."
                    color: Theme.aiVoiceGlacial
                    font.family: Theme.fontAiVoice
                    font.pixelSize: Math.max(9, Math.round(root.height * 0.055))
                    wrapMode: Text.Wrap
                    lineHeight: 1.3
                }
            }
        }

    }

    // Card Surface Click & Selection MouseArea
    MouseArea {
        id: cardHoverArea
        anchors.fill: parent
        hoverEnabled: true
        z: -1
        cursorShape: Qt.PointingHandCursor

        onClicked: {
            if (typeof plateCanvasController !== "undefined" && plateCanvasController && root.plateId > 0) {
                plateCanvasController.selectPlate(root.plateId);
            }
            root.clicked();
        }
    }

}
