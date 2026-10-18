import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root

    // Populated by the Repeater delegate injection (a plain `modelData: modelData` binding would self-reference)
    required property var modelData
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
        if (modelData.title) return modelData.title;
        if (fileName) return fileName;
        if (filePath) return filePath.slice(filePath.lastIndexOf("/") + 1);
        return "Plate #" + plateId;
    }
    readonly property string extension: {
        if (modelData && modelData.extension) return ("" + modelData.extension).replace(/^\./, "");
        if (fileName && fileName.lastIndexOf(".") !== -1) return fileName.slice(fileName.lastIndexOf(".") + 1);
        return "";
    }
    readonly property string archetype: modelData ? (modelData.archetype || "document") : "document"
    readonly property string snippetText: modelData ? (modelData.snippet || modelData.preview_text || modelData.previewText || "") : ""
    readonly property string previewUrl: {
        if (!modelData) return "";
        if (modelData.preview_path) return modelData.preview_path;
        if (modelData.previewUrl) return modelData.previewUrl;
        if (modelData.thumbnail_url) return modelData.thumbnail_url;
        if (modelData.thumbnail) return modelData.thumbnail;
        return filePath;
    }
    readonly property string aiSummaryText: modelData ? (modelData.ai_summary || modelData.aiSummary || "") : ""
    readonly property bool isPreview: {
        if (!modelData) return false;
        if (modelData.is_preview !== undefined) return !!modelData.is_preview;
        if (modelData.isPreview !== undefined) return !!modelData.isPreview;
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

    // Interior padding scales with the allocated card size
    readonly property real padH: Math.max(8, Math.round(width * 0.035))
    readonly property real padV: Math.max(8, Math.round(height * 0.03))

    x: targetX
    y: targetY
    width: targetWidth
    height: targetHeight

    Behavior on x { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on y { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on width { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on height { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }

    opacity: (modelData && (modelData.is_preview || modelData.isPreview)) ? 0.75 : 1.0
    Behavior on opacity { NumberAnimation { duration: 180 } }

    z: isSelected ? 40 : 10
    radius: 16
    clip: true

    // Visual Card Shell
    color: Theme.surfacePlate
    border.width: 1
    // Saccade Focus Equality: focus is signalled solely by a 1px cyan accent border (no dimming of neighbours)
    border.color: isSelected ? Theme.accentCyan : Theme.borderCream

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
    readonly property bool hasImageSource: /\.(png|jpe?g|webp|svg|gif|bmp)(\?.*)?$/i.test(previewUrl)
    // Crown: calm identity row (no window chrome)
    Item {
        id: titleBar
        z: 2  // above cardHoverArea (z: 1) so the shelve glyph receives clicks; the row itself has no MouseArea
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 30

        Rectangle {
            id: statusDot
            width: 6
            height: 6
            radius: 3
            color: root.isSelected ? Theme.accentCyan : root.archetypeBadgeColor
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            id: titleText
            text: root.displayTitle
            color: Theme.textDimmed
            font.family: Theme.fontCode
            font.pixelSize: 11
            elide: Text.ElideMiddle
            anchors.left: statusDot.right
            anchors.leftMargin: 8
            anchors.right: metaTag.left
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            id: metaTag
            text: root.extension ? Theme.normalizeExt(root.extension) : root.archetype
            color: Theme.textDimmed
            font.family: Theme.fontCode
            font.pixelSize: 11
            opacity: 0.35
            anchors.right: shelveBtn.left
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            id: shelveBtn
            text: "⇥"
            font.family: Theme.fontCode
            font.pixelSize: 13
            color: shelveMouseArea.containsMouse ? Theme.accentFocus : Theme.textDimmed
            opacity: shelveMouseArea.containsMouse ? 0.9 : 0.25
            verticalAlignment: Text.AlignVCenter
            anchors.right: parent.right
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter

            MouseArea {
                id: shelveMouseArea
                anchors.fill: parent
                anchors.margins: -4
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (typeof plateCanvasController !== "undefined" && plateCanvasController) {
                        plateCanvasController.shelve_plate(String(root.plateId));
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
                anchors.leftMargin: root.padH
                anchors.rightMargin: root.padH
                anchors.bottomMargin: root.padV
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
                // Only decode genuine image sources; raw documents (.docx/.md/.csv) must never reach the image decoder
                source: (root.isVisual && root.hasImageSource) ? root.previewUrl : ""
                visible: root.isVisual && root.hasImageSource
                enabled: root.isVisual && root.hasImageSource
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
                anchors.leftMargin: root.padH
                anchors.rightMargin: root.padH
                anchors.topMargin: root.padV
                anchors.bottomMargin: root.padV
                contentWidth: width
                contentHeight: docSnippet.implicitHeight
                clip: true

                Text {
                    id: docSnippet
                    width: parent.width
                    text: root.snippetText ? root.snippetText : "Document content ready. Open in focal stage or trigger AI summary for distilled extraction."
                    textFormat: Text.AutoText
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

    // Card Surface Click & Selection MouseArea (above the body so inner Flickables cannot swallow the press;
    // wheel events still fall through to the snippet Flickables)
    MouseArea {
        id: cardHoverArea
        anchors.fill: parent
        hoverEnabled: true
        z: 1
        cursorShape: root.isPreview ? Qt.PointingHandCursor : Qt.ArrowCursor

        onClicked: {
            if (typeof plateCanvasController !== "undefined" && plateCanvasController && root.plateId > 0) {
                if (root.isPreview) {
                    if (typeof plateCanvasController.open_plate === "function") {
                        plateCanvasController.open_plate(root.plateId);
                    } else if (typeof plateCanvasController.openPlate === "function") {
                        plateCanvasController.openPlate(root.plateId);
                    }
                } else {
                    plateCanvasController.selectPlate(root.plateId);
                }
            }
            root.clicked();
        }
    }

    // Elastic Gutter Handle: dragging yields neighbour width proportionally (adjust_plate_weight)
    MouseArea {
        id: gutterHandle
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: root.radius
        anchors.bottomMargin: root.radius
        anchors.right: parent.right
        width: 14
        z: 50
        hoverEnabled: true
        preventStealing: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.SplitHCursor

        property real lastStageX: 0

        function stageX(mouse) {
            return root.parent ? mapToItem(root.parent, mouse.x, mouse.y).x : mouse.x
        }

        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: Theme.accentCyan
            opacity: (gutterHandle.containsMouse || gutterHandle.pressed) ? 0.35 : 0.0
            Behavior on opacity { NumberAnimation { duration: 120 } }
        }

        onPressed: function(mouse) { lastStageX = stageX(mouse) }

        onPositionChanged: function(mouse) {
            if (!pressed || !root.parent || root.parent.width <= 0) return
            var sx = stageX(mouse)
            var deltaRatio = (sx - lastStageX) / root.parent.width
            lastStageX = sx
            if (deltaRatio !== 0 && typeof plateCanvasController !== "undefined" && plateCanvasController && root.plateId > 0) {
                plateCanvasController.adjust_plate_weight(root.plateId, deltaRatio)
            }
        }
    }

    // Diagonal Corner Handle: dragging resizes width and height proportionally (resize_plate_proportional).
    // Sits above the card surface so panning/selection never fires while the corner is dragged.
    MouseArea {
        id: cornerHandle
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 16
        height: 16
        z: 60
        hoverEnabled: true
        preventStealing: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.SizeFDiagCursor

        // Stage-space coordinates: the card itself moves/resizes under the cursor mid-drag
        property real lastX: 0
        property real lastY: 0

        function stagePoint(mouse) {
            return root.parent ? mapToItem(root.parent, mouse.x, mouse.y) : Qt.point(mouse.x, mouse.y)
        }

        Canvas {
            id: cornerGlyph
            anchors.fill: parent
            opacity: (cornerHandle.containsMouse || cornerHandle.pressed) ? 0.6 : 0.0
            Behavior on opacity { NumberAnimation { duration: 120 } }
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.strokeStyle = "" + Theme.accentCyan
                ctx.lineWidth = 1
                ctx.beginPath()
                ctx.moveTo(width - 3, height * 0.45)
                ctx.lineTo(width * 0.45, height - 3)
                ctx.moveTo(width - 3, height * 0.75)
                ctx.lineTo(width * 0.75, height - 3)
                ctx.stroke()
            }
        }

        onPressed: function(mouse) {
            var p = stagePoint(mouse)
            lastX = p.x
            lastY = p.y
        }

        onPositionChanged: function(mouse) {
            if (!pressed || !root.parent || root.parent.width <= 0 || root.parent.height <= 0) return
            var p = stagePoint(mouse)
            var deltaW = (p.x - lastX) / root.parent.width
            var deltaH = (p.y - lastY) / root.parent.height
            lastX = p.x
            lastY = p.y
            if ((deltaW !== 0 || deltaH !== 0) && typeof plateCanvasController !== "undefined" && plateCanvasController && root.plateId > 0) {
                plateCanvasController.resize_plate_proportional(root.plateId, deltaW, deltaH)
            }
        }
    }

}
