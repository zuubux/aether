import QtQuick
import QtQuick.Controls

FocusScope {
    id: root
    focus: true

    readonly property real screenHeight: (typeof rootWindow !== "undefined" && rootWindow && rootWindow.height > 0) ? rootWindow.height : (Screen.height > 0 ? Screen.height : 1080)
    readonly property real screenWidth: (typeof rootWindow !== "undefined" && rootWindow && rootWindow.width > 0) ? rootWindow.width : (Screen.width > 0 ? Screen.width : 1920)

    readonly property real targetSlateHeight: screenHeight * 0.78
    readonly property real targetSlateWidth: Math.min(screenWidth * 0.85, 1200.0)

    width: targetSlateWidth
    height: targetSlateHeight

    property int nodeId: 0
    property string filePath: ""
    property string fileName: filePath ? filePath.split('/').pop() : ""
    property string sizeFormatted: "0 KB"
    property string archetype: "document"
    property color accentColor: "#fb7185" // Warm rose for data
    property bool isSelected: false

    property var bridge: (typeof canvasBridge !== "undefined" ? canvasBridge : null)

    function getBridge() {
        if (root.bridge) return root.bridge;
        if (typeof canvasBridge !== "undefined" && canvasBridge) return canvasBridge;
        return null;
    }

    // CSV editing properties
    property string editingValue: ""
    property int editingRowIndex: -1
    property int editingColIndex: -1

    // Table Data State
    property var tableData: ({ "headers": [], "rows": [], "total_rows": 0, "total_cols": 0 })

    function loadData() {
        var b = getBridge()
        if (b && filePath) {
            var data = b.get_csv_data(filePath, 1000)
            if (data && data.headers && data.rows) {
                tableData = data
            } else {
                tableData = ({ "headers": [], "rows": [], "total_rows": 0, "total_cols": 0 })
            }
        }
    }

    onFilePathChanged: {
        loadData()
    }

    Component.onCompleted: {
        root.forceActiveFocus()
        loadData()
        
        var b = getBridge()
        if (b) {
            b.set_workbench_dimensions(targetSlateWidth, targetSlateHeight)
        }
    }

    // Keyboard controls
    Keys.onPressed: (event) => {
        if (event.modifiers & Qt.ControlModifier && event.key === Qt.Key_C) {
            var b = getBridge()
            if (b) {
                if (b.copy_csv_data(root.filePath)) {
                    if (typeof toast !== "undefined" && toast) {
                        toast.show("Copied Data to Clipboard")
                    }
                }
            }
            event.accepted = true
        } else {
            event.accepted = false
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: 12
        color: "#0d1117"
        border.color: "#30363d"
        border.width: 1
        antialiasing: true
        smooth: true

        MouseArea {
            anchors.fill: parent
            // Consume all clicks inside the slate bounding box so they don't leak to canvas dismiss handlers
            onClicked: (mouse) => { mouse.accepted = true }
            onPressed: (mouse) => { mouse.accepted = true }
        }

        // Header Bar
        Rectangle {
            id: header
            width: parent.width
            height: 48
            color: "#161b22"
            radius: 12
            anchors.top: parent.top

            // Prevent top corner radius clipping
            Rectangle {
                width: parent.width
                height: 12
                color: "#161b22"
                anchors.bottom: parent.bottom
            }

            Rectangle {
                width: parent.width
                height: 1
                color: "#30363d"
                anchors.bottom: parent.bottom
            }

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                // Icon indicator
                Rectangle {
                    width: 24
                    height: 24
                    radius: 4
                    color: Qt.alpha(root.accentColor, 0.1)
                    border.color: root.accentColor
                    border.width: 1
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "CSV"
                        color: root.accentColor
                        font.family: "JetBrains Mono, monospace"
                        font.pixelSize: 9
                        font.bold: true
                    }
                }

                Text {
                    text: root.fileName
                    color: "#f0f6fc"
                    font.family: "JetBrains Mono, monospace"
                    font.pixelSize: 13
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }

                Rectangle {
                    width: 1
                    height: 16
                    color: "#30363d"
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Metadata tag
                Text {
                    text: ((root.tableData && root.tableData.total_rows) ? root.tableData.total_rows : 0) + " rows × " + ((root.tableData && root.tableData.total_cols) ? root.tableData.total_cols : 0) + " cols"
                    color: "#8b949e"
                    font.family: "JetBrains Mono, monospace"
                    font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                // Copy All Button
                Rectangle {
                    id: copyBtn
                    width: 80
                    height: 24
                    radius: 4
                    color: "#161b22"
                    border.color: "#30363d"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "Copy All"
                        color: "#8b949e"
                        font.family: "Monospace"
                        font.pixelSize: 10
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: copyBtn.color = "#21262d"
                        onExited: copyBtn.color = "#161b22"
                        onClicked: {
                            var b = getBridge()
                            if (b && b.copy_csv_data(root.filePath)) {
                                if (typeof toast !== "undefined" && toast) {
                                    toast.show("Copied Data to Clipboard")
                                }
                            }
                        }
                    }
                }

                // Reveal File Button
                Rectangle {
                    id: revealBtn
                    width: 80
                    height: 24
                    radius: 4
                    color: "#161b22"
                    border.color: "#30363d"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "Reveal File"
                        color: "#8b949e"
                        font.family: "Monospace"
                        font.pixelSize: 10
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: revealBtn.color = "#21262d"
                        onExited: revealBtn.color = "#161b22"
                        onClicked: {
                            var b = getBridge()
                            if (b) {
                                b.open_in_file_manager(root.filePath)
                            }
                        }
                    }
                }

                // Open in Editor Button
                Rectangle {
                    id: openBtn
                    width: 100
                    height: 24
                    radius: 4
                    color: "#161b22"
                    border.color: "#30363d"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "Open in Editor"
                        color: "#8b949e"
                        font.family: "Monospace"
                        font.pixelSize: 10
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: openBtn.color = "#21262d"
                        onExited: openBtn.color = "#161b22"
                        onClicked: {
                            var b = getBridge()
                            if (b) {
                                b.open_in_external_editor(root.filePath)
                            }
                        }
                    }
                }
            }
        }

        // Table Viewport Area with support for both horizontal and vertical scrolling
        ScrollView {
            id: scrollArea
            anchors.top: header.bottom
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 1
            clip: true

            ScrollBar.horizontal.policy: ScrollBar.AsNeeded
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            Flickable {
                id: flickable
                anchors.fill: parent
                contentWidth: Math.max(scrollArea.width, columnHeadersRow.implicitWidth)
                contentHeight: columnHeadersRow.height + rowsColumn.implicitHeight
                clip: true

                // Header sticky layer (stays at top contentY but scrolls horizontally)
                Rectangle {
                    id: stickyHeaderBackground
                    width: Math.max(flickable.width, columnHeadersRow.implicitWidth)
                    height: 36
                    color: "#1f242c"
                    z: 5
                    y: flickable.contentY // Sticky effect on vertical scroll!

                    Row {
                        id: columnHeadersRow
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        spacing: 0

                        Repeater {
                            model: (root.tableData && root.tableData.headers) ? root.tableData.headers : []

                            delegate: Rectangle {
                                width: 150
                                height: parent.height
                                color: "transparent"
                                border.color: "#30363d"
                                border.width: 1

                                Text {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    text: modelData
                                    color: "#f0f6fc"
                                    font.family: "JetBrains Mono, monospace"
                                    font.pixelSize: 11
                                    font.bold: true
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: "#30363d"
                        anchors.bottom: parent.bottom
                    }
                }

                // Table Rows Column
                Column {
                    id: rowsColumn
                    anchors.top: stickyHeaderBackground.bottom
                    spacing: 0
                    width: Math.max(flickable.width, columnHeadersRow.implicitWidth)

                    Repeater {
                        model: (root.tableData && root.tableData.rows) ? root.tableData.rows : []

                        delegate: Rectangle {
                            id: rowRect
                            width: parent.width
                            height: 32
                            color: (index % 2 === 0) ? "#0d1117" : "#161b22"
                            readonly property int rowIndex: index

                            // Bottom border for cells
                            Rectangle {
                                width: parent.width
                                height: 1
                                color: "#21262d"
                                anchors.bottom: parent.bottom
                            }

                            Row {
                                anchors.fill: parent
                                spacing: 0

                                Repeater {
                                    model: modelData

                                    delegate: Rectangle {
                                        id: cellRect
                                        width: 150
                                        height: 32
                                        color: "transparent"
                                        border.color: (root.editingRowIndex === rowRect.rowIndex && root.editingColIndex === index) ? root.accentColor : "#21262d"
                                        border.width: 1
                                        
                                        readonly property int colIndex: index
                                        readonly property bool isEditing: root.editingRowIndex === rowRect.rowIndex && root.editingColIndex === colIndex

                                        Text {
                                            visible: !cellRect.isEditing
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 12
                                            text: modelData
                                            color: "#c9d1d9"
                                            font.family: "JetBrains Mono, monospace"
                                            font.pixelSize: 11
                                            verticalAlignment: Text.AlignVCenter
                                            elide: Text.ElideRight
                                        }

                                        TextInput {
                                            id: editInput
                                            visible: cellRect.isEditing
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 12
                                            text: cellRect.isEditing ? root.editingValue : ""
                                            color: "#ffffff"
                                            font.family: "JetBrains Mono, monospace"
                                            font.pixelSize: 11
                                            verticalAlignment: TextInput.AlignVCenter
                                            clip: true
                                            focus: cellRect.isEditing

                                            onVisibleChanged: {
                                                if (visible) {
                                                    forceActiveFocus()
                                                    selectAll()
                                                }
                                            }

                                             function commitEdit() {
                                                 try {
                                                     let rootObj = (typeof root !== "undefined" ? root : null);
                                                     if (rootObj && rootObj.editingRowIndex === rowRect.rowIndex && rootObj.editingColIndex === cellRect.colIndex) {
                                                         rootObj.editingValue = text;
                                                         
                                                         // Update in-memory cell value
                                                         if (rootObj.tableData && rootObj.tableData.rows && rootObj.tableData.rows[rootObj.editingRowIndex]) {
                                                             var updatedRows = rootObj.tableData.rows;
                                                             updatedRows[rootObj.editingRowIndex][rootObj.editingColIndex] = rootObj.editingValue;
                                                             // Trigger binding updates by re-assigning or making a shallow copy
                                                             rootObj.tableData = {
                                                                 "headers": rootObj.tableData.headers,
                                                                 "rows": updatedRows,
                                                                 "total_rows": rootObj.tableData.total_rows,
                                                                 "total_cols": rootObj.tableData.total_cols
                                                             };
                                                         }
                                                         
                                                         // Call python bridge safely
                                                         let b = (typeof root !== "undefined" ? root.bridge : null) || (typeof bridge !== "undefined" ? bridge : null);
                                                         if (b && b.update_csv_cell && rootObj.editingRowIndex >= 0 && rootObj.editingColIndex >= 0) {
                                                             b.update_csv_cell(rootObj.filePath, rootObj.editingRowIndex, rootObj.editingColIndex, rootObj.editingValue);
                                                         }
                                                     }
                                                 } catch (err) {
                                                     console.warn("[TableSlate] Failed to save cell edit:", err);
                                                 } finally {
                                                     if (typeof root !== "undefined") {
                                                         root.editingRowIndex = -1;
                                                         root.editingColIndex = -1;
                                                         root.forceActiveFocus();
                                                     }
                                                 }
                                             }

                                            onAccepted: {
                                                commitEdit()
                                            }

                                            onActiveFocusChanged: {
                                                if (!activeFocus && cellRect.isEditing) {
                                                    commitEdit()
                                                }
                                            }

                                            Keys.onPressed: (event) => {
                                                if (event.key === Qt.Key_Space && (event.modifiers & Qt.ControlModifier)) {
                                                    // Forward or allow Ctrl+Space to propagate up to the root window
                                                    event.accepted = false
                                                } else if (event.key === Qt.Key_Escape) {
                                                    // Cancel editing, revert
                                                    root.editingRowIndex = -1
                                                    root.editingColIndex = -1
                                                    root.forceActiveFocus()
                                                    event.accepted = true
                                                }
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            enabled: !cellRect.isEditing
                                            onDoubleClicked: {
                                                root.editingValue = modelData
                                                root.editingRowIndex = rowRect.rowIndex
                                                root.editingColIndex = cellRect.colIndex
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
    }
}
