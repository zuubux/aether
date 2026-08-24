import QtQuick
import QtQuick.Controls

FocusScope {
    id: root
    focus: true
    width: Math.round(320)
    height: Math.round(220)

    property int nodeId: 0
    property string archetype: "document"
    property string snippet: ""
    property string initialText: ""
    property string fileName: ""
    property string filePath: ""
    property string sizeFormatted: "0 KB"
    property string hashSnippet: "N/A"
    property int referenceCount: 0
    property color accentColor: "#94a3b8"
    property bool isSelected: false

    property bool isDirty: false
    property bool isSaving: false
    property bool justSaved: false
    property string renderedPreviewText: ""

    property bool isBinaryFile: {
        var ext = filePath ? filePath.split('.').pop().toLowerCase() : "";
        var binaryExts = ["sqlite", "db", "bin", "iso", "exe", "dll", "so", "dylib", "zip", "tar", "gz", "tgz", "bz2", "xz", "whl", "jar", "epub", "rar", "7z", "pdf", "docx", "xlsx", "pptx", "mp4", "mp3", "wav", "avi", "ico", "bmp", "svg", "webp", "png", "jpg", "jpeg", "gif"];
        var arch = (archetype || "").toLowerCase();
        return arch === "binary" || arch === "archive" || arch === "system" || binaryExts.indexOf(ext) !== -1;
    }

    property bool supportsRichView: {
        if (isBinaryFile) return false;
        var ext = filePath.split('.').pop().toLowerCase();
        return ext === "md" || ext === "markdown" || ext === "csv";
    }
    property bool isSourceMode: !supportsRichView

    onFilePathChanged: {
        var ext = filePath.split('.').pop().toLowerCase();
        var isRich = (ext === "md" || ext === "markdown" || ext === "csv");
        isSourceMode = !isRich;
    }

    Component.onCompleted: {
        console.log("[PreviewSlate] ROOT Component.onCompleted.")
        if (isSelected) {
            if (supportsRichView) {
                isSourceMode = false
                root.forceActiveFocus()
            } else {
                isSourceMode = true
                editor.forceActiveFocus()
            }
        }
        root.refreshPreview()
    }

    onIsSelectedChanged: {
        if (isSelected) {
            if (supportsRichView) {
                isSourceMode = false
                root.forceActiveFocus()
                root.refreshPreview()
            } else {
                isSourceMode = true
                editor.forceActiveFocus()
            }
        }
    }

    onInitialTextChanged: {
        if (!isDirty && initialText !== "") {
            editor.text = initialText
            if (!isSourceMode) {
                root.refreshPreview()
            }
        }
    }

    function refreshPreview() {
        if (supportsRichView) {
            renderedPreviewText = editor.text.replace(/\[\[([^\]]+)\]\]/g, '<a href="wikilink:$1" style="color: #58a6ff; text-decoration: none; font-weight: 600;">$1</a>')
        }
    }

    function triggerSave() {
        if (isDirty) {
            isDirty = false
            saveTimer.stop()
            isSaving = true
            bridge.save_node_content(root.nodeId, editor.text)
            
            isSaving = false
            justSaved = true
            pulseTimer.restart()
        }
    }

    function triggerSaveImmediate() {
        if (isDirty) {
            isDirty = false
            saveTimer.stop()
            isSaving = true
            if (typeof bridge !== "undefined" && bridge) {
                bridge.save_node_content(root.nodeId, editor.text)
            }
            isSaving = false
            justSaved = true
            pulseTimer.restart()
        }
    }

    Component.onDestruction: {
        if (root.isDirty) {
            root.triggerSaveImmediate();
        }
    }

    Timer {
        id: saveTimer
        interval: 500
        repeat: false
        onTriggered: {
            root.triggerSave()
        }
    }

    Timer {
        id: pulseTimer
        interval: 250
        repeat: false
        onTriggered: {
            root.justSaved = false
        }
    }

    Keys.onEscapePressed: {
        root.triggerSave()
        if (root.supportsRichView && root.isSourceMode) {
            root.isSourceMode = false
            root.forceActiveFocus()
        } else {
            editor.focus = false
            root.parent.forceActiveFocus()
            if (typeof bridge !== "undefined") {
                bridge.select_node(0)
            }
        }
        event.accepted = true
    }

    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_E && (event.modifiers & Qt.ControlModifier)) {
            if (root.supportsRichView) {
                if (root.isSourceMode) {
                    root.triggerSave()
                }
                root.isSourceMode = !root.isSourceMode
                if (root.isSourceMode) {
                    editor.forceActiveFocus()
                } else {
                    root.forceActiveFocus()
                }
            }
            event.accepted = true
        } else {
            event.accepted = false
        }
    }

    Item {
        id: focalBackground
        anchors.fill: parent
        z: -1

        // Header
        Rectangle {
            id: header
            width: parent.width
            height: 40
            color: "transparent"

                Rectangle {
                    id: revealBtn
                    width: 80
                    height: 24
                    radius: 4
                    color: Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "Reveal File"
                        color: Theme.textMuted
                        font.family: Theme.fontCode
                        font.pixelSize: 10
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: revealBtn.color = Theme.surfaceButtonHover
                        onExited: revealBtn.color = Theme.surfaceButton
                        onClicked: {
                            if (typeof bridge !== "undefined" && bridge) {
                                bridge.open_in_file_manager(root.filePath)
                            } else {
                                Qt.openUrlExternally("file://" + root.filePath)
                            }
                        }
                    }
                }

                Rectangle {
                    id: openBtn
                    width: 100
                    height: 24
                    radius: 4
                    color: Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1
                    anchors.right: revealBtn.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "Open in Editor"
                        color: Theme.textMuted
                        font.family: Theme.fontCode
                        font.pixelSize: 10
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: openBtn.color = Theme.surfaceButtonHover
                        onExited: openBtn.color = Theme.surfaceButton
                        onClicked: {
                            if (typeof bridge !== "undefined" && bridge) {
                                bridge.open_in_external_editor(root.filePath)
                            } else {
                                Qt.openUrlExternally("file://" + root.filePath)
                            }
                        }
                    }
                }

                Rectangle {
                    id: modeToggle
                    visible: root.supportsRichView
                    width: 65
                    height: 24
                    radius: 4
                    color: Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1
                    anchors.right: openBtn.left
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: root.isSourceMode ? "Preview" : "Source"
                        color: root.isSourceMode ? "#58a6ff" : "#7ee787"
                        font.family: root.isSourceMode ? Theme.fontSans : Theme.fontCode
                        font.pixelSize: 11
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: modeToggle.color = Theme.surfaceButtonHover
                        onExited: modeToggle.color = Theme.surfaceButton
                        onClicked: {
                            if (root.isSourceMode) {
                                root.triggerSave()
                            }
                            root.isSourceMode = !root.isSourceMode
                            if (root.isSourceMode) {
                                editor.forceActiveFocus()
                            } else {
                                root.refreshPreview()
                                root.forceActiveFocus()
                            }
                        }
                    }
                }

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.right: root.supportsRichView ? modeToggle.left : revealBtn.left
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                Rectangle {
                    width: 20
                    height: 20
                    radius: 4
                    color: "transparent"
                    border.color: root.accentColor
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: root.archetype === "document" ? "D" : (root.archetype === "code" ? "C" : (root.archetype === "binary" ? "B" : "A"))
                        color: root.accentColor
                        font.family: Theme.fontCode
                        font.pixelSize: 10
                        font.bold: true
                    }
                }

                Text {
                    text: root.fileName
                    color: Theme.textPrimary
                    font.family: Theme.fontCode
                    font.pixelSize: 12
                    font.bold: true
                    elide: Text.ElideRight
                    width: Math.min(implicitWidth, 120)
                    anchors.verticalCenter: parent.verticalCenter
                }

                Rectangle {
                    id: statusDot
                    width: 5
                    height: 5
                    radius: 2.5
                    anchors.verticalCenter: parent.verticalCenter
                    color: root.isDirty ? "#d29922" : "#64d2ff"
                    opacity: root.isDirty ? 0.9 : 0.3
                    visible: true
                    z: 20
                    
                    Behavior on color { ColorAnimation { duration: 150 } }
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                }

                Text {
                    text: root.filePath
                    color: Theme.textDimmed
                    font.family: Theme.fontCode
                    font.pixelSize: 10
                    elide: Text.ElideMiddle
                    width: Math.min(implicitWidth, 130)
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: "#1e293b"
                anchors.bottom: parent.bottom
            }
        }

        // Body
        Item {
            anchors.top: header.bottom
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 12

            // Case 1: Document / Code
            FocusScope {
                id: editorScope
                visible: !root.isBinaryFile && (root.archetype === "document" || root.archetype === "code")
                anchors.fill: parent
                focus: true

                Flickable {
                    id: previewFlickable
                    visible: !root.isSourceMode && root.supportsRichView
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: previewText.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    Text {
                        id: previewText
                        width: parent.width
                        text: root.renderedPreviewText
                        textFormat: Text.MarkdownText
                        wrapMode: Text.Wrap
                        color: "#c9d1d9"
                        onLinkActivated: function(link) {
                            if (link.startsWith("wikilink:")) {
                                var targetName = link.replace("wikilink:", "");
                                if (typeof bridge !== "undefined" && bridge) {
                                    bridge.navigate_to_link(targetName);
                                }
                            } else {
                                Qt.openUrlExternally(link);
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onDoubleClicked: {
                            root.isSourceMode = true
                            editor.forceActiveFocus()
                        }
                    }
                }

                Flickable {
                    id: flickable
                    visible: root.isSourceMode || !root.supportsRichView
                    anchors.fill: parent
                    contentWidth: editorRow.implicitWidth > width ? editorRow.implicitWidth : width
                    contentHeight: editor.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    MouseArea {
                        id: slateBackgroundCatcher
                        anchors.fill: parent
                        z: -1
                        hoverEnabled: true
                        cursorShape: Qt.IBeamCursor
                        onClicked: {
                            editor.forceActiveFocus()
                            editor.cursorPosition = editor.length
                        }
                    }

                    Row {
                        id: editorRow
                        width: Math.max(flickable.width, implicitWidth)
                        height: editor.implicitHeight

                        Item {
                            width: 36
                            height: parent.height
                            
                            Text {
                                anchors.top: parent.top
                                anchors.topMargin: editor.topPadding
                                anchors.right: parent.right
                                anchors.rightMargin: 8
                                color: "#484f58"
                                font.family: Theme.fontCode
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignRight
                                text: {
                                    var arr = [];
                                    var count = editor.lineCount || 1;
                                    // Use split instead of lineCount because TextArea lineCount can be unreliable with NoWrap
                                    var lines = editor.text.split('\n').length;
                                    for (var i = 1; i <= Math.max(1, lines); i++) {
                                        arr.push(i);
                                    }
                                    return arr.join('\n');
                                }
                            }
                        }

                        TextArea {
                            id: editor
                            width: Math.max(flickable.width - 36, implicitWidth)
                            text: root.initialText !== "" ? root.initialText : root.snippet
                            focus: true
                            readOnly: false
                            selectByMouse: true
                            mouseSelectionMode: TextEdit.SelectCharacters
                            cursorVisible: activeFocus
                            wrapMode: TextEdit.NoWrap
                            color: Theme.textSecondary
                            font.family: Theme.fontCode
                            font.pixelSize: 12
                            background: Item {}

                            HoverHandler {
                                cursorShape: Qt.IBeamCursor
                            }
                        
                            onActiveFocusChanged: {
                                if (!editor.activeFocus && root.isDirty) {
                                    root.triggerSaveImmediate()
                                }
                            }

                            onTextChanged: {
                                saveTimer.restart()
                                root.isDirty = true
                            }

                            Keys.onTabPressed: {
                                editor.insert(editor.cursorPosition, "    ")
                                event.accepted = true
                            }
                            
                            Keys.onEscapePressed: {
                                root.triggerSave()
                                if (root.supportsRichView && root.isSourceMode) {
                                    root.isSourceMode = false
                                    root.forceActiveFocus()
                                } else {
                                    editor.focus = false
                                    if (typeof bridge !== "undefined") {
                                        bridge.select_node(0)
                                    } else {
                                        root.parent.forceActiveFocus()
                                    }
                                }
                                event.accepted = true
                            }
                            
                            Keys.onPressed: (event) => {
                                if ((event.key === Qt.Key_Enter || event.key === Qt.Key_Return) && (event.modifiers & Qt.ControlModifier)) {
                                    if (root.supportsRichView && root.isSourceMode) {
                                        root.triggerSave()
                                        root.isSourceMode = false
                                        root.forceActiveFocus()
                                        event.accepted = true
                                    } else {
                                        event.accepted = false
                                    }
                                } else if (event.key === Qt.Key_E && (event.modifiers & Qt.ControlModifier)) {
                                    if (root.supportsRichView) {
                                        root.triggerSave()
                                        root.isSourceMode = false
                                        root.forceActiveFocus()
                                        event.accepted = true
                                    } else {
                                        event.accepted = false
                                    }
                                } else {
                                    event.accepted = false
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 40
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 1.0; color: "#14171d" }
                    }
                }
            }

            // Case 2: Binary / Technical (Centered Fallback Card)
            Item {
                visible: root.isBinaryFile || (root.archetype !== "document" && root.archetype !== "code")
                anchors.fill: parent

                Rectangle {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 24, 380)
                    height: Math.min(parent.height - 24, 180)
                    color: "transparent"
                    border.width: 0
                    radius: 8
                    clip: true

                    Column {
                        anchors.centerIn: parent
                        spacing: 16
                        width: parent.width - 32

                        Row {
                            spacing: 16
                            anchors.horizontalCenter: parent.horizontalCenter

                            // File Badge
                            Rectangle {
                                width: 44
                                height: 44
                                radius: 8
                                color: "#161b22"
                                border.color: root.accentColor
                                border.width: 1.5
                                anchors.verticalCenter: parent.verticalCenter

                                Text {
                                    anchors.centerIn: parent
                                    text: {
                                        var ext = root.filePath ? root.filePath.split('.').pop().toUpperCase() : "";
                                        return ext.slice(0, 3);
                                    }
                                    color: root.accentColor
                                    font.family: Theme.fontCode
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 4

                                Text {
                                    text: root.fileName
                                    color: Theme.textPrimary
                                    font.family: Theme.fontCode
                                    font.pixelSize: 12
                                    font.bold: true
                                    elide: Text.ElideRight
                                    width: 180
                                }

                                Text {
                                    text: "Size: " + root.sizeFormatted
                                    color: Theme.textMuted
                                    font.family: Theme.fontCode
                                    font.pixelSize: 10
                                }

                                Text {
                                    text: "Type: " + (root.filePath ? root.filePath.split('.').pop().toLowerCase() : "") + " (" + root.archetype + ")"
                                    color: Theme.textDimmed
                                    font.family: Theme.fontCode
                                    font.pixelSize: 9
                                }
                            }
                        }

                        // Open in External App action button
                        Rectangle {
                            id: externalOpenBtn
                            width: 180
                            height: 28
                            radius: 6
                            color: Theme.surfaceButton
                            border.color: Theme.borderSubtle
                            border.width: 1
                            anchors.horizontalCenter: parent.horizontalCenter

                            Text {
                                anchors.centerIn: parent
                                text: "Open in External App"
                                color: Theme.textSecondary
                                font.family: Theme.fontCode
                                font.pixelSize: 10
                                font.bold: true
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                hoverEnabled: true
                                onEntered: externalOpenBtn.color = Theme.surfaceButtonHover
                                onExited: externalOpenBtn.color = Theme.surfaceButton
                                onClicked: {
                                    if (typeof bridge !== "undefined" && bridge) {
                                        bridge.open_in_external_editor(root.filePath)
                                    } else {
                                        Qt.openUrlExternally("file://" + root.filePath)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
