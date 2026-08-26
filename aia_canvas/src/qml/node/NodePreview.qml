import QtQuick 2.15
import ".."

Item {
    id: previewRoot
    anchors.fill: parent
    anchors.margins: 16

    property var nodeData: null
    property int nodeId: {
        if (!nodeData) return 0;
        var val = (nodeData.id !== undefined && nodeData.id !== null) ? nodeData.id : nodeData.nodeId;
        if (val === undefined || val === null) return 0;
        var parsed = parseInt(val, 10);
        return isNaN(parsed) ? 0 : parsed;
    }
    property string archetype: (nodeData && nodeData.archetype) ? nodeData.archetype : "document"
    property string path: (nodeData && (nodeData.path || nodeData.filePath)) ? (nodeData.path || nodeData.filePath) : ""
    property string filePath: path
    property string fileName: (nodeData && (nodeData.fileName || nodeData.title)) ? (nodeData.fileName || nodeData.title) : (filePath ? filePath.split('/').pop() : "")
    property string displayTitle: (nodeData && (nodeData.displayTitle || nodeData.display_title)) ? (nodeData.displayTitle || nodeData.display_title) : fileName
    property string snippetText: (nodeData && nodeData.snippet) ? nodeData.snippet : ""
    property string fileExt: {
        var ext = (nodeData && nodeData.extension) ? nodeData.extension : "";
        if (!ext && filePath) {
            var idx = filePath.lastIndexOf(".");
            if (idx !== -1) ext = filePath.substring(idx);
        }
        if (ext && !ext.startsWith(".")) ext = "." + ext;
        return ext.toLowerCase();
    }
    property string mimeType: (nodeData && nodeData.mimeType) ? nodeData.mimeType : ""
    property string thumbnail: {
        var t = (nodeData && (nodeData.thumbnailUrl || nodeData.thumbnail)) ? String(nodeData.thumbnailUrl || nodeData.thumbnail) : "";
        if (t === "None" || t === "null" || t === "undefined") return "";
        return t;
    }
    property string thumbnailUrl: thumbnail
    property string previewUrl: {
        if (thumbnailUrl && thumbnailUrl.length > 0) return thumbnailUrl;
        if (nodeData) {
            var t = (nodeData.thumbnailUrl || nodeData.thumbnail) ? String(nodeData.thumbnailUrl || nodeData.thumbnail) : "";
            if (t && t !== "None" && t !== "null" && t !== "undefined" && t.length > 0) return t;
        }
        if ((isStaticImage || isAnimatedGif) && filePath && filePath.length > 0) return filePath;
        return "";
    }
    readonly property bool hasThumbnail: (previewUrl && previewUrl.length > 0)

    readonly property bool isAnimatedGif: (previewRoot.filePath && previewRoot.filePath.toLowerCase().endsWith(".gif"))
    readonly property bool isStaticImage: (previewRoot.archetype && (previewRoot.archetype.toUpperCase() === "MEDIA" || previewRoot.archetype.toUpperCase() === "IMAGE" || previewRoot.archetype.toUpperCase() === "ASSET")) || (previewRoot.filePath && (previewRoot.filePath.toLowerCase().endsWith(".png") || previewRoot.filePath.toLowerCase().endsWith(".jpg") || previewRoot.filePath.toLowerCase().endsWith(".jpeg") || previewRoot.filePath.toLowerCase().endsWith(".webp")))
    readonly property bool isPdf: (previewRoot.archetype && (previewRoot.archetype.toUpperCase() === "DOCUMENT" || previewRoot.archetype.toUpperCase() === "PDF")) && previewRoot.filePath && previewRoot.filePath.toLowerCase().endsWith(".pdf")

    property bool isImage: isStaticImage || isAnimatedGif || fileExt === ".svg" || fileExt === ".ico" || mimeType.startsWith("image/") || mimeType === "image/x-icon" || mimeType === "image/vnd.microsoft.icon"
    property bool isHeavyImage: fileExt === ".png" || fileExt === ".jpg" || fileExt === ".jpeg" || fileExt === ".webp"
    property bool isIcon: fileExt === ".ico" || mimeType.includes("icon")
    property bool isGif: isAnimatedGif
    property bool isSvg: fileExt === ".svg"
    property bool isArchive: (previewRoot.archetype && previewRoot.archetype.toUpperCase() === "ARCHIVE") || (fileExt === ".zip" || fileExt === ".tar" || fileExt === ".tgz" || fileExt === ".gz" || fileExt === ".bz2" || fileExt === ".xz" || fileExt === ".whl" || fileExt === ".jar" || fileExt === ".epub" || (filePath && (filePath.toLowerCase().endsWith(".tar.gz") || filePath.toLowerCase().endsWith(".tar.bz2") || filePath.toLowerCase().endsWith(".tar.xz"))))
    property bool isTabular: !isArchive && ((previewRoot.archetype && (previewRoot.archetype.toUpperCase() === "TABLE" || previewRoot.archetype.toUpperCase() === "DATABASE" || previewRoot.archetype.toUpperCase() === "NOTEBOOK")) || fileExt === ".csv" || fileExt === ".tsv" || fileExt === ".json" || fileExt === ".py" || fileExt === ".sh" || fileExt === ".yml" || fileExt === ".xlsx" || fileExt === ".sqlite" || fileExt === ".db" || fileExt === ".ipynb")
    property bool isDocument: !isArchive && ((previewRoot.archetype && (previewRoot.archetype.toUpperCase() === "PRESENTATION" || previewRoot.archetype.toUpperCase() === "DOCX")) || fileExt === ".md" || fileExt === ".txt" || fileExt === ".pdf" || fileExt === ".doc" || fileExt === ".docx" || fileExt === ".pptx")
    property bool isCsv: !isArchive && (fileExt === ".csv" || fileExt === ".tsv" || (previewRoot.archetype && previewRoot.archetype.toUpperCase() === "TABLE"))

    readonly property string archiveSummaryString: {
        if (!previewRoot.snippetText) return "0 items • 0 B uncompressed";
        var lines = previewRoot.snippetText.trim().split(/\r?\n/);
        if (lines.length > 0 && lines[0].length > 0) {
            return lines[0];
        }
        return "0 items • 0 B uncompressed";
    }

    readonly property string archiveManifestString: {
        if (!previewRoot.snippetText) return "(Empty archive)";
        var lines = previewRoot.snippetText.trim().split(/\r?\n/);
        if (lines.length > 1) {
            return lines.slice(1).join("\n");
        }
        return "(Empty archive)";
    }

    function getCsvRows(snippet) {
        if (!snippet || previewRoot.isHtmlSnippet || (snippet.indexOf(",") === -1 && snippet.indexOf("\t") === -1)) return [];
        var lines = snippet.trim().split(/\r?\n/);
        var table = [];
        var maxRows = Math.min(lines.length, 9);
        for (var r = 0; r < maxRows; r++) {
            var line = lines[r].trim();
            if (!line) continue;
            var rawCols = line.indexOf("\t") !== -1 ? line.split("\t") : line.split(",");
            var row = [];
            var maxCols = Math.min(rawCols.length, 6);
            for (var c = 0; c < maxCols; c++) {
                row.push(rawCols[c].trim().replace(/^["']|["']$/g, ''));
            }
            table.push(row);
        }
        return table;
    }

    readonly property bool isHtmlSnippet: {
        var txt = previewRoot.snippetText;
        if (!txt) return false;
        return (txt.indexOf("<span") !== -1 || txt.indexOf("<div") !== -1 || txt.indexOf("<p") !== -1 || txt.indexOf("<style") !== -1 || txt.indexOf("<html") !== -1 || txt.indexOf("<body") !== -1 || txt.indexOf("<table") !== -1);
    }

    property string cleanSnippetText: {
        var txt = previewRoot.snippetText;
        if (!txt) return previewRoot.filePath;
        if (isPdf && (txt.startsWith("%PDF") || txt.indexOf("\\x") !== -1)) {
            var size = (nodeData && nodeData.size) ? nodeData.size + " bytes" : "Unknown size";
            return "PDF Document\nSize: " + size;
        }
        if (previewRoot.isHtmlSnippet) {
            return Theme.snippetCss + txt;
        }
        return txt;
    }

    Item {
        id: headerLayout
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 20
        z: 20
        
        Row {
            anchors.fill: parent
            height: 18
            spacing: 6
            
            Rectangle {
                id: badgeRect
                width: Math.max(16, badgeText.implicitWidth + 6)
                height: 13
                radius: 3
                color: Theme.getBadgeColor(previewRoot.fileExt, previewRoot.nodeData ? previewRoot.nodeData.archetype : "")
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    id: badgeText
                    anchors.centerIn: parent
                    text: Theme.normalizeExt(previewRoot.fileExt)
                    font.family: Theme.fontCode
                    font.pixelSize: 7
                    font.bold: true
                    color: "#0D1117"
                }
            }
            
            Text {
                text: previewRoot.displayTitle || previewRoot.fileName || "Untitled"
                color: Theme.textPrimary
                font.family: Theme.fontSans
                font.pixelSize: 11
                font.weight: Font.Medium
                anchors.verticalCenter: parent.verticalCenter
                elide: Text.ElideRight
                width: parent.width - badgeRect.width - 6
            }
        }
    }
    
    Item {
        id: mediaContainer
        anchors.top: headerLayout ? headerLayout.bottom : parent.top
        anchors.bottom: (debugHud.visible) ? debugHud.top : parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 6
        anchors.topMargin: 4
        visible: Boolean(previewRoot.hasThumbnail || previewRoot.isStaticImage || previewRoot.isAnimatedGif)
        z: 10

        Image {
            id: previewImg
            objectName: "previewImg"
            anchors.fill: parent
            fillMode: isPdf ? Image.PreserveAspectCrop : Image.PreserveAspectFit
            verticalAlignment: isPdf ? Image.AlignTop : Image.AlignVCenter
            horizontalAlignment: Image.AlignHCenter
            asynchronous: true
            smooth: true
            mipmap: true
            clip: true
            visible: (isStaticImage || isPdf || hasThumbnail) && !isAnimatedGif
            source: mediaContainer.visible && previewRoot.previewUrl ? previewRoot.previewUrl : ""
            opacity: 1.0
            z: 11

            onStatusChanged: {
                if (status === Image.Error) {
                    console.warn("Image preview failed to load:", source)
                }
            }
        }

        AnimatedImage {
            id: gifImg
            objectName: "gifImg"
            anchors.fill: parent
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            visible: isAnimatedGif
            source: mediaContainer.visible && isAnimatedGif && previewRoot.previewUrl ? previewRoot.previewUrl : ""
            opacity: 1.0
            z: 11
        }
    }

    Item {
        id: textContentContainer
        anchors.top: headerLayout ? headerLayout.bottom : parent.top
        anchors.topMargin: 8
        anchors.bottom: (debugHud.visible) ? debugHud.top : parent.bottom
        anchors.bottomMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        visible: !previewRoot.isAnimatedGif && (!mediaContainer.visible || previewImg.status === Image.Error)
        z: 10

        // Archive Manifest Tree View
        Column {
            id: archiveLayout
            anchors.fill: parent
            spacing: 8
            visible: previewRoot.isArchive
            z: 6

            Rectangle {
                id: archiveSummaryPill
                width: Math.min(parent.width, summaryRow.implicitWidth + 16)
                height: 20
                radius: 4
                color: Theme.surfaceButton
                border.color: Theme.borderSubtle
                border.width: 1

                Row {
                    id: summaryRow
                    anchors.centerIn: parent
                    spacing: 6

                    Text {
                        id: archiveSummaryText
                        text: previewRoot.archiveSummaryString
                        color: Theme.badgeArchive
                        font.family: Theme.fontCode
                        font.pixelSize: 9
                        font.bold: true
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            Item {
                width: parent.width
                height: Math.max(0, parent.height - archiveSummaryPill.height - parent.spacing)
                clip: true

                Text {
                    id: archiveManifestText
                    anchors.fill: parent
                    verticalAlignment: Text.AlignTop
                    text: previewRoot.archiveManifestString
                    color: Theme.textSecondary
                    font.family: Theme.fontCode
                    font.pixelSize: 10
                    lineHeight: 1.3
                    wrapMode: Text.NoWrap
                    elide: Text.ElideRight
                }
            }
        }

        Column {
            id: csvTable
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: 2
            visible: !previewRoot.isArchive && previewRoot.isCsv && csvRows.length > 0

            readonly property var csvRows: previewRoot.getCsvRows(previewRoot.snippetText)

            Repeater {
                model: csvTable.csvRows
                delegate: Rectangle {
                    id: rowRect
                    readonly property int rowIndex: index
                    readonly property var cellData: modelData
                    width: csvTable.width
                    height: rowIndex === 0 ? 18 : 16
                    radius: 3
                    color: rowIndex === 0 ? Theme.surfaceBorder : (rowIndex % 2 === 1 ? Theme.surfaceBackground : "transparent")

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        anchors.rightMargin: 6

                        Repeater {
                            model: rowRect.cellData
                            delegate: Item {
                                width: (rowRect.width - 12) / Math.max(1, rowRect.cellData.length)
                                height: parent.height
                                clip: true

                                Text {
                                    anchors.fill: parent
                                    anchors.rightMargin: 8
                                    verticalAlignment: Text.AlignVCenter
                                    text: modelData
                                    font.family: Theme.fontCode
                                    font.pixelSize: 9
                                    font.weight: rowRect.rowIndex === 0 ? Font.Medium : Font.Normal
                                    color: rowRect.rowIndex === 0 ? Theme.textMuted : Theme.textPrimary
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }

        Text {
            visible: !previewRoot.isArchive && previewRoot.isTabular && (!previewRoot.isCsv || !csvTable.visible)
            anchors.fill: parent
            verticalAlignment: Text.AlignTop
            text: previewRoot.cleanSnippetText
            color: Theme.textMuted
            font.family: Theme.fontCode
            font.pixelSize: 10
            lineHeight: 1.3
            wrapMode: Text.NoWrap
            elide: Text.ElideRight
            textFormat: previewRoot.isHtmlSnippet ? Text.RichText : Text.PlainText
            z: 5
        }

        Text {
            visible: !previewRoot.isArchive && !previewRoot.isTabular
            anchors.fill: parent
            verticalAlignment: Text.AlignTop
            text: previewRoot.cleanSnippetText
            color: Theme.textMuted
            font.family: Theme.fontSans
            font.pixelSize: 11
            lineHeight: 1.3
            wrapMode: Text.Wrap
            elide: Text.ElideRight
            textFormat: previewRoot.isHtmlSnippet ? Text.RichText : (previewRoot.fileExt === ".md" ? Text.MarkdownText : Text.PlainText)
            z: 5
        }
    }

    Rectangle {
        id: debugHud
        visible: (typeof canvasRoot !== "undefined" && canvasRoot && canvasRoot.showDiagnostics) || false
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 36
        color: "#CC111827"
        border.color: "#38BDF8"
        border.width: 1
        z: 9999

        Column {
            anchors.fill: parent
            anchors.margins: 4
            spacing: 2

            Text {
                text: "Arch: " + previewRoot.archetype + " | isImg: " + isStaticImage + " | isPdf: " + isPdf + " | Status: " + (previewRoot.isAnimatedGif ? gifImg.status : previewImg.status)
                color: "#38BDF8"
                font.pixelSize: 9
                font.family: "monospace"
            }
            Text {
                text: "Src: " + (previewRoot.isAnimatedGif ? (gifImg.source || "NONE") : (previewImg.source || "NONE"))
                color: (previewRoot.isAnimatedGif ? gifImg.status : previewImg.status) === Image.Error ? "#EF4444" : "#A7F3D0"
                font.pixelSize: 8
                font.family: "monospace"
                elide: Text.ElideMiddle
                width: parent.width
            }
        }
    }
}
