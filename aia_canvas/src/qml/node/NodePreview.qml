import QtQuick 2.15
import ".."

Item {
    id: previewRoot
    anchors.fill: parent
    anchors.margins: 16

    property var nodeData: null
    property string fileName: (nodeData && (nodeData.fileName || nodeData.title)) ? (nodeData.fileName || nodeData.title) : ""
    property string filePath: (nodeData && (nodeData.filePath || nodeData.path)) ? (nodeData.filePath || nodeData.path) : ""
    property string snippetText: (nodeData && nodeData.snippet) ? nodeData.snippet : ""
    property string fileExt: (nodeData && nodeData.extension) ? nodeData.extension.toLowerCase() : ""
    property string mimeType: (nodeData && nodeData.mimeType) ? nodeData.mimeType : ""
    property string thumbnailUrl: (nodeData && nodeData.thumbnailUrl) ? nodeData.thumbnailUrl : ""
    readonly property bool hasThumbnail: nodeData && nodeData.thumbnailUrl && nodeData.thumbnailUrl.length > 0
    property bool isImage: fileExt === ".png" || fileExt === ".jpg" || fileExt === ".jpeg" || fileExt === ".webp" || fileExt === ".svg" || fileExt === ".ico" || mimeType.startsWith("image/") || mimeType === "image/x-icon" || mimeType === "image/vnd.microsoft.icon"
    property bool isHeavyImage: fileExt === ".png" || fileExt === ".jpg" || fileExt === ".jpeg" || fileExt === ".webp"
    property bool isIcon: fileExt === ".ico" || mimeType.includes("icon")
    property bool isGif: fileExt === ".gif"
    property bool isSvg: fileExt === ".svg"
    property bool isTabular: fileExt === ".csv" || fileExt === ".tsv" || fileExt === ".json" || fileExt === ".py" || fileExt === ".sh" || fileExt === ".yml"
    property bool isDocument: fileExt === ".md" || fileExt === ".txt" || fileExt === ".pdf" || fileExt === ".doc" || fileExt === ".docx"
    property bool isPdf: fileExt === ".pdf"
    property bool isCsv: fileExt === ".csv" || fileExt === ".tsv"

    function getCsvRows(snippet) {
        if (!snippet || snippet.indexOf(",") === -1) return [];
        var lines = snippet.trim().split(/\r?\n/);
        var table = [];
        var maxRows = Math.min(lines.length, 9);
        for (var r = 0; r < maxRows; r++) {
            var line = lines[r].trim();
            if (!line) continue;
            var rawCols = line.split(",");
            var row = [];
            var maxCols = Math.min(rawCols.length, 4);
            for (var c = 0; c < maxCols; c++) {
                row.push(rawCols[c].trim().replace(/^["']|["']$/g, ''));
            }
            table.push(row);
        }
        return table;
    }

    property string cleanSnippetText: {
        var txt = previewRoot.snippetText;
        if (!txt) return previewRoot.filePath;
        if (isPdf && (txt.startsWith("%PDF") || txt.indexOf("\\x") !== -1)) {
            var size = (nodeData && nodeData.size) ? nodeData.size + " bytes" : "Unknown size";
            return "PDF Document\nSize: " + size;
        }
        return txt;
    }

    Item {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 20
        
        Row {
            anchors.fill: parent
            spacing: 8
            
            Rectangle {
                width: 14
                height: 14
                radius: 3
                color: Theme.surfaceBorder
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    anchors.centerIn: parent
                    text: previewRoot.fileExt ? previewRoot.fileExt.replace(".", "").substring(0, 3).toUpperCase() : "DOC"
                    color: "#94A3B8"
                    font.pixelSize: 7
                    font.bold: true
                }
            }
            
            Text {
                text: previewRoot.fileName || "Untitled"
                color: "#F1F5F9"
                font.pixelSize: 11
                font.weight: Font.Medium
                anchors.verticalCenter: parent.verticalCenter
                elide: Text.ElideRight
                width: parent.width - 22
            }
        }
    }
    
    Item {
        id: bodyContent
        anchors.top: header.bottom
        anchors.bottom: footer.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: 4
        anchors.bottomMargin: 4
        clip: true
        
        Image {
            id: previewImg
            property bool isThumbnailValid: previewRoot.hasThumbnail && status !== Image.Error
            visible: (previewRoot.isHeavyImage && isThumbnailValid) || (previewRoot.isImage && !previewRoot.isHeavyImage && !previewRoot.isGif) || (previewRoot.isPdf && isThumbnailValid)
            anchors.centerIn: parent
            width: previewRoot.isIcon ? Math.min(implicitWidth, 64) : parent.width
            height: previewRoot.isIcon ? Math.min(implicitHeight, 64) : parent.height
            source: previewRoot.hasThumbnail ? (previewRoot.thumbnailUrl.startsWith("file://") ? previewRoot.thumbnailUrl : "file://" + previewRoot.thumbnailUrl) : ""
            fillMode: previewRoot.isPdf ? Image.PreserveAspectCrop : (previewRoot.isIcon ? Image.Pad : Image.PreserveAspectFit)
            smooth: !previewRoot.isIcon
            verticalAlignment: previewRoot.isPdf ? Image.AlignTop : Image.AlignVCenter
            horizontalAlignment: Image.AlignHCenter
            asynchronous: true
            sourceSize.width: previewRoot.isSvg ? 300 : 0
        }
        
        AnimatedImage {
            visible: previewRoot.isGif
            anchors.centerIn: parent
            width: parent.width
            height: parent.height
            source: previewRoot.isGif ? "file://" + previewRoot.filePath : ""
            fillMode: Image.PreserveAspectFit
            verticalAlignment: Image.AlignVCenter
            horizontalAlignment: Image.AlignHCenter
            asynchronous: true
        }
        
        Column {
            id: csvTable
            anchors.centerIn: parent
            width: parent.width - 12
            spacing: 2
            visible: previewRoot.isCsv && csvRows.length > 1

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
                                    font.family: "Monospace"
                                    font.pixelSize: 9
                                    font.weight: rowRect.rowIndex === 0 ? Font.Medium : Font.Normal
                                    color: rowRect.rowIndex === 0 ? "#94A3B8" : "#E2E8F0"
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }

        Text {
            visible: previewRoot.isTabular && (!previewRoot.isCsv || !csvTable.visible)
            anchors.fill: parent
            text: previewRoot.cleanSnippetText
            color: "#94A3B8"
            font.family: "Monospace"
            font.pixelSize: 10
            lineHeight: 1.3
            wrapMode: Text.NoWrap
            elide: Text.ElideRight
        }

        Text {
            visible: !previewRoot.isGif && !previewRoot.isTabular && previewImg.status !== Image.Ready
            anchors.fill: parent
            text: previewRoot.cleanSnippetText
            color: "#94A3B8"
            font.pixelSize: 11
            lineHeight: 1.3
            wrapMode: Text.Wrap
            elide: Text.ElideRight
            textFormat: previewRoot.fileExt === ".md" ? Text.MarkdownText : Text.AutoText
        }
    }
    
    Text {
        id: footer
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 12
        text: previewRoot.filePath
        color: Theme.surfaceBorder
        font.pixelSize: 8
        elide: Text.ElideMiddle
        verticalAlignment: Text.AlignBottom
    }
}