import QtQuick
import QtQuick.Controls

Item {
    id: previewRoot
    anchors.fill: parent
    z: 5

    // Public Interface Contract
    property string fileName: ""
    property string snippetText: ""
    property string archetype: ""
    property color accentColor: "#00E5FF"
    property real cardRadius: 8
    property bool isSearchResult: false
    property bool isHovered: false
    property bool showPreviewSlate: false

    // Decoupled properties to resolve context cleanly without direct outer/global references
    readonly property string filePath: parent && parent.parent && parent.parent.filePath !== undefined ? parent.parent.filePath : ""
    readonly property var activeBridge: parent && parent.parent && parent.parent.activeBridge !== undefined ? parent.parent.activeBridge : null
    readonly property string ext: {
        var dotIdx = fileName.lastIndexOf(".");
        return dotIdx !== -1 ? fileName.substring(dotIdx).toLowerCase() : ".txt";
    }
    readonly property bool isPdfFile: ext === ".pdf"
    readonly property bool isTableFile: ext === ".csv" || ext === ".tsv"
    readonly property bool isImageFile: {
        var e = ext;
        return e === ".png" || e === ".jpg" || e === ".jpeg" || e === ".gif" || e === ".webp" || e === ".svg" || e === ".ico";
    }

    Item {
        id: hoverSnippetContainer
        anchors.fill: parent
        visible: previewRoot.showPreviewSlate
        opacity: previewRoot.showPreviewSlate ? 1.0 : 0.0

        Column {
            id: contentCol
            anchors {
                top: parent.top
                left: parent.left
                right: parent.right
                bottom: parent.bottom
                margins: 12
            }
            spacing: 6
            clip: true

            // Header row
            Row {
                width: parent.width
                spacing: 8
                Text {
                    text: previewRoot.fileName
                    font.bold: true
                    font.pixelSize: 13
                    color: "#FFFFFF"
                    elide: Text.ElideRight
                    width: parent.width
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: "#1f242d"
            }

            // Body text
            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: previewRoot.snippetText.length > 0 ? (previewRoot.ext === ".md" || previewRoot.ext === ".markdown" || previewRoot.ext === ".txt" || previewRoot.ext === ".org" ? hoverSnippetContainer.formatMarkdownWithWikilinks(previewRoot.snippetText) : previewRoot.snippetText) : (previewRoot.fileName + " • (" + (previewRoot.archetype ? previewRoot.archetype : "document") + ")")
                textFormat: previewRoot.snippetText.length > 0 && (previewRoot.ext === ".md" || previewRoot.ext === ".markdown" || previewRoot.ext === ".txt" || previewRoot.ext === ".org") ? Text.MarkdownText : Text.PlainText
                font.pixelSize: 11
                color: "#D0D7DE"
                maximumLineCount: 8
                elide: Text.ElideRight
                visible: !previewRoot.isImageFile && !previewRoot.isPdfFile && !previewRoot.isTableFile
            }

            // Table Hover Preview (Tier 1.5 hover)
            Loader {
                id: tableHoverLoader
                width: parent.width
                height: parent.height - 30
                active: previewRoot.showPreviewSlate && previewRoot.isTableFile
                visible: active
                sourceComponent: Rectangle {
                    anchors.fill: parent
                    color: "#0a0c10"
                    radius: 8
                    clip: true
                    border.color: "#30363d"
                    border.width: 1

                    // Cache the table preview object via property
                    property var previewData: (previewRoot.activeBridge && previewRoot.filePath) ? previewRoot.activeBridge.get_csv_preview(previewRoot.filePath, 5) : {"headers":[], "rows":[], "total_rows":0, "total_cols":0}

                    ScrollView {
                        anchors.fill: parent
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded

                        Column {
                            spacing: 0
                            width: Math.max(parent.width, 400)

                            // Headers
                            Row {
                                spacing: 0
                                height: 24
                                Repeater {
                                    model: previewData.headers
                                    delegate: Rectangle {
                                        width: 80
                                        height: 24
                                        color: "#161b22"
                                        border.color: "#21262d"
                                        border.width: 1
                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData
                                            color: "#E0E6ED"
                                            font.family: "JetBrains Mono, monospace"
                                            font.pixelSize: 9
                                            font.bold: true
                                            elide: Text.ElideRight
                                            width: 70
                                        }
                                    }
                                }
                            }

                            // Rows
                            Repeater {
                                model: previewData.rows
                                delegate: Row {
                                    spacing: 0
                                    height: 20
                                    Repeater {
                                        model: modelData
                                        delegate: Rectangle {
                                            width: 80
                                            height: 20
                                            color: "#0d1117"
                                            border.color: "#21262d"
                                            border.width: 1
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData
                                                color: "#E0E6ED"
                                                font.family: "JetBrains Mono, monospace"
                                                font.pixelSize: 8
                                                elide: Text.ElideRight
                                                width: 70
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Loader {
                id: imageHoverLoader
                width: parent.width
                height: parent.height - 30
                active: previewRoot.showPreviewSlate && (previewRoot.isImageFile || previewRoot.isPdfFile)
                visible: active
                sourceComponent: Rectangle {
                    anchors.fill: parent
                    color: "#0a0c10"
                    radius: 8
                    clip: true
                    border.color: "#30363d"
                    border.width: 1
                    
                    readonly property bool isAnimatedFormat: previewRoot.ext === ".gif" || previewRoot.ext === ".webp"

                    AnimatedImage {
                        id: previewImg
                        anchors.fill: parent
                        playing: previewRoot.isHovered && parent.isAnimatedFormat
                        paused: !previewRoot.isHovered || !parent.isAnimatedFormat
                        source: {
                            if (!parent.isAnimatedFormat) return "";
                            if (previewRoot.isPdfFile) {
                                if (!previewRoot.filePath) return "";
                                return previewRoot.activeBridge ? previewRoot.activeBridge.get_pdf_page_image(previewRoot.filePath, 0, 400) : "";
                            }
                            if (!previewRoot.isImageFile || !previewRoot.filePath) return "";
                            if (previewRoot.activeBridge) {
                                return previewRoot.activeBridge.get_image_source(previewRoot.filePath);
                            }
                            let path = previewRoot.filePath;
                            if (path.startsWith("file://")) return path;
                            return "file://" + path;
                        }
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        visible: parent.isAnimatedFormat && status !== Image.Error && source !== ""
                    }

                    Image {
                        id: staticImg
                        anchors.fill: parent
                        source: {
                            if (parent.isAnimatedFormat) return "";
                            if (previewRoot.isPdfFile) {
                                if (!previewRoot.filePath) return "";
                                return previewRoot.activeBridge ? previewRoot.activeBridge.get_pdf_page_image(previewRoot.filePath, 0, 400) : "";
                            }
                            if (!previewRoot.isImageFile || !previewRoot.filePath) return "";
                            if (previewRoot.activeBridge) {
                                return previewRoot.activeBridge.get_image_source(previewRoot.filePath);
                            }
                            let path = previewRoot.filePath;
                            if (path.startsWith("file://")) return path;
                            return "file://" + path;
                        }
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        visible: !parent.isAnimatedFormat && status !== Image.Error && source !== ""
                    }

                    // Preview Error Fallback
                    Rectangle {
                        visible: parent.isAnimatedFormat ? (previewImg.status === Image.Error) : (staticImg.status === Image.Error)
                        anchors.fill: parent
                        color: "#0d1117"

                        Column {
                            anchors.centerIn: parent
                            spacing: 8
                            width: parent.width - 16

                            Row {
                                spacing: 8
                                anchors.horizontalCenter: parent.horizontalCenter

                                Rectangle {
                                    width: 24
                                    height: 24
                                    radius: 4
                                    color: "#161b22"
                                    border.color: previewRoot.accentColor
                                    border.width: 1
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        anchors.centerIn: parent
                                        text: previewRoot.ext.replace(".", "").toUpperCase().slice(0, 3)
                                        color: previewRoot.accentColor
                                        font.family: "Monospace"
                                        font.pixelSize: 8
                                        font.bold: true
                                    }
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 1

                                    Text {
                                        text: previewRoot.fileName
                                        color: "#E0E6ED"
                                        font.family: "Monospace"
                                        font.pixelSize: 10
                                        font.bold: true
                                        elide: Text.ElideRight
                                        width: 120
                                    }

                                    Text {
                                        text: "Decoder not available"
                                        color: "#f87171"
                                        font.family: "Monospace"
                                        font.pixelSize: 8
                                    }
                                }
                            }

                            Rectangle {
                                id: miniOpenBtn
                                width: 120
                                height: 20
                                radius: 4
                                color: "#161b22"
                                border.color: "#30363d"
                                border.width: 1
                                anchors.horizontalCenter: parent.horizontalCenter

                                Text {
                                    anchors.centerIn: parent
                                    text: "Open in External App"
                                    color: "#E0E6ED"
                                    font.family: "Monospace"
                                    font.pixelSize: 8
                                    font.bold: true
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    hoverEnabled: true
                                    onEntered: miniOpenBtn.color = "#21262d"
                                    onExited: miniOpenBtn.color = "#161b22"
                                    onClicked: {
                                        if (previewRoot.activeBridge && previewRoot.filePath) {
                                            previewRoot.activeBridge.open_in_external_editor(previewRoot.filePath)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        function formatMarkdownWithWikilinks(text) {
            if (!text) return "";
            var formatted = text.replace(/\[\[(.*?)\]\]/g, function(match, p1) {
                var parts = p1.split('|');
                var target = parts[0];
                var display = parts.length > 1 ? parts[1] : target;
                return `<a href="obsidian://open?file=${encodeURIComponent(target)}" style="color: #60a5fa; text-decoration: none;">${display}</a>`;
            });
            return formatted;
        }
    }
}
