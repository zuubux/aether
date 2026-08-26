import QtQuick
import QtQuick.Controls

FocusScope {
    id: root
    focus: true
    
    // Use Window or Screen dimensions to avoid uninitialized 0/undefined layout values
    readonly property real screenHeight: (typeof rootWindow !== "undefined" && rootWindow && rootWindow.height > 0) ? rootWindow.height : (Screen.height > 0 ? Screen.height : 1080)
    readonly property real screenWidth: (typeof rootWindow !== "undefined" && rootWindow && rootWindow.width > 0) ? rootWindow.width : (Screen.width > 0 ? Screen.width : 1920)

    // Target ~78% of available screen height for comfortable reading
    readonly property real targetSlateHeight: screenHeight * 0.78
    readonly property real docAspect: (imgElement.naturalWidth > 0 && imgElement.naturalHeight > 0) ? (imgElement.naturalWidth / imgElement.naturalHeight) : (8.5 / 11.0)

    width: targetSlateHeight * docAspect
    height: targetSlateHeight

    property int nodeId: 0
    property string filePath: ""
    property string fileName: filePath ? filePath.split('/').pop() : ""
    property string sizeFormatted: "0 KB"
    property string archetype: "document"
    property color accentColor: "#ef4444" // Crimson/Red for PDF
    property bool isSelected: false

    property int currentPageIndex: 0
    property int pageCount: 0

    property real zoomLevel: 1.0
    property bool isFitted: true // Defaults to fit-width to load legibly
    property bool aspectSized: false
    property Item viewportContainer: null
    property var bridge: null

    function getBridge() {
        if (root.bridge) return root.bridge;
        if (typeof canvasBridge !== "undefined" && canvasBridge) return canvasBridge;
        return null;
    }

    property string snippet: ""
    property string initialText: ""
    property int referenceCount: 0

    property string renderedPageSource: ""
    property bool isLoading: false

    readonly property bool hasError: pageCount <= 0 || imgElement.status === Image.Error || (root.filePath !== "" && getBridge() !== null && renderedPageSource === "" && !isLoading)

    Keys.onPressed: (event) => {
        if (event.modifiers & Qt.ControlModifier && event.key === Qt.Key_C) {
            var b = getBridge()
            if (b) {
                if (b.copy_pdf_page_to_clipboard(root.filePath, root.currentPageIndex)) {
                    toast.show("Copied Page to Clipboard")
                }
            }
            event.accepted = true
        } else if (event.key === Qt.Key_Left || event.key === Qt.Key_PageUp || event.key === Qt.Key_K) {
            if (root.currentPageIndex > 0) {
                root.currentPageIndex--
            }
            event.accepted = true
        } else if (event.key === Qt.Key_Right || event.key === Qt.Key_PageDown || event.key === Qt.Key_J) {
            if (root.currentPageIndex < root.pageCount - 1) {
                root.currentPageIndex++
            }
            event.accepted = true
        } else if (event.key === Qt.Key_Z || event.key === Qt.Key_1) {
            root.toggleZoomFit()
            event.accepted = true
        } else {
            event.accepted = false
        }
    }

    function applyAspectSizing() {
        if (aspectSized) return

        var targetHeight = screenHeight * 0.78
        var targetWidth = targetHeight * docAspect

        // Ensure safe reading boundaries (unbounded by hard maximums)
        targetWidth = Math.max(480.0, targetWidth)
        targetHeight = Math.max(640.0, targetHeight)

        aspectSized = true

        var bDim = getBridge()
        if (bDim) {
            bDim.set_workbench_dimensions(targetWidth, targetHeight)
        }
    }

    Connections {
        target: getBridge()
        function onPdfPageReady(fPath, pIndex, imagePath) {
            if (fPath === root.filePath && pIndex === root.currentPageIndex) {
                root.renderedPageSource = imagePath
                root.isLoading = false
            }
        }
        function onPdfCountReady(fPath, count) {
            if (fPath === root.filePath) {
                root.pageCount = count
                requestCurrentPage()
            }
        }
        function onMediaError(fPath, errorMsg) {
            if (fPath === root.filePath) {
                root.isLoading = false
                console.error("Media error:", errorMsg)
            }
        }
    }

    function requestCurrentPage() {
        var b = getBridge()
        if (b && filePath && pageCount > 0) {
            isLoading = true
            b.request_pdf_page(filePath, currentPageIndex, 1200)
        }
    }

    onFilePathChanged: {
        currentPageIndex = 0
        pageCount = 0
        aspectSized = false
        var b = getBridge()
        if (b && filePath) {
            isLoading = true
            b.request_pdf_page_count(filePath)
        }
        applyAspectSizing()
    }

    function toggleZoomFit() {
        root.isFitted = !root.isFitted
        root.zoomLevel = 1.0
        if (root.isFitted) {
            viewport.contentX = 0
            viewport.contentY = 0
        } else {
            viewport.contentX = Math.max(0, (viewport.contentWidth - viewport.width) / 2)
            viewport.contentY = Math.max(0, (viewport.contentHeight - viewport.height) / 2)
        }
    }

    onCurrentPageIndexChanged: {
        requestCurrentPage()
    }

    Component.onCompleted: {
        root.forceActiveFocus()
        var b = getBridge()
        if (b && filePath) {
            isLoading = true
            b.request_pdf_page_count(filePath)
        }
        applyAspectSizing()
    }

    Rectangle {
        anchors.fill: parent
        radius: 12
        color: "#0d1117"
        border.color: "#30363d"
        border.width: 1
        antialiasing: true
        smooth: true
        opacity: 1.0

        MouseArea {
            anchors.fill: parent
            z: -1
            // Consume all clicks inside the slate bounding box so they don't leak to canvas dismiss handlers
            onClicked: (mouse) => { mouse.accepted = true }
            onPressed: (mouse) => { mouse.accepted = true }
        }

        // Header
        Rectangle {
            id: header
            width: parent.width
            height: 40
            color: "transparent"
            border.width: 0
            anchors.top: parent.top
            clip: true

            Row {
                id: headerActions
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                // Prev
                Rectangle {
                    id: prevBtn
                    width: 45
                    height: 24
                    radius: 4
                    color: root.currentPageIndex > 0 ? Theme.surfaceButton : "transparent"
                    border.color: root.currentPageIndex > 0 ? Theme.borderSubtle : "transparent"
                    border.width: 1
                    opacity: root.currentPageIndex > 0 ? 1.0 : 0.4

                    Text {
                        anchors.centerIn: parent
                        text: "Prev"
                        color: root.currentPageIndex > 0 ? Theme.textSecondary : Theme.textMuted
                        font.family: Theme.fontCode
                        font.pixelSize: 10
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: root.currentPageIndex > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                        hoverEnabled: true
                        onEntered: if (root.currentPageIndex > 0) prevBtn.color = Theme.surfaceButtonHover
                        onExited: prevBtn.color = root.currentPageIndex > 0 ? Theme.surfaceButton : "transparent"
                        onPressed: (mouse) => { mouse.accepted = true }
                        onClicked: (mouse) => {
                            mouse.accepted = true
                            if (root.currentPageIndex > 0) {
                                root.currentPageIndex--
                            }
                        }
                    }
                }

                // Page count indicator
                Text {
                    text: "Page " + (root.pageCount > 0 ? (root.currentPageIndex + 1) : 0) + " / " + root.pageCount
                    color: Theme.textMuted
                    font.family: Theme.fontCode
                    font.pixelSize: 10
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Next
                Rectangle {
                    id: nextBtn
                    width: 45
                    height: 24
                    radius: 4
                    color: root.currentPageIndex < root.pageCount - 1 ? Theme.surfaceButton : "transparent"
                    border.color: root.currentPageIndex < root.pageCount - 1 ? Theme.borderSubtle : "transparent"
                    border.width: 1
                    opacity: root.currentPageIndex < root.pageCount - 1 ? 1.0 : 0.4

                    Text {
                        anchors.centerIn: parent
                        text: "Next"
                        color: root.currentPageIndex < root.pageCount - 1 ? Theme.textSecondary : Theme.textMuted
                        font.family: Theme.fontCode
                        font.pixelSize: 10
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: root.currentPageIndex < root.pageCount - 1 ? Qt.PointingHandCursor : Qt.ArrowCursor
                        hoverEnabled: true
                        onEntered: if (root.currentPageIndex < root.pageCount - 1) nextBtn.color = Theme.surfaceButtonHover
                        onExited: nextBtn.color = root.currentPageIndex < root.pageCount - 1 ? Theme.surfaceButton : "transparent"
                        onPressed: (mouse) => { mouse.accepted = true }
                        onClicked: (mouse) => {
                            mouse.accepted = true
                            if (root.currentPageIndex < root.pageCount - 1) {
                                root.currentPageIndex++
                            }
                        }
                    }
                }

                // Fit Width vs 1:1 view
                Rectangle {
                    id: fitBtn
                    width: 80
                    height: 24
                    radius: 4
                    color: Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: root.isFitted ? "Fit Width" : "1:1 View"
                        color: Theme.textMuted
                        font.family: Theme.fontCode
                        font.pixelSize: 10
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: fitBtn.color = Theme.surfaceButtonHover
                        onExited: fitBtn.color = Theme.surfaceButton
                        onClicked: {
                            root.toggleZoomFit()
                        }
                    }
                }

                // Copy Page
                Rectangle {
                    id: copyBtn
                    width: 80
                    height: 24
                    radius: 4
                    color: Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "Copy Page"
                        color: Theme.textMuted
                        font.family: Theme.fontCode
                        font.pixelSize: 10
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: copyBtn.color = Theme.surfaceButtonHover
                        onExited: copyBtn.color = Theme.surfaceButton
                        onClicked: {
                            var b = getBridge()
                            if (b) {
                                if (b.copy_pdf_page_to_clipboard(root.filePath, root.currentPageIndex)) {
                                    toast.show("Copied Page to Clipboard")
                                }
                            }
                        }
                    }
                }

                // Reveal File
                Rectangle {
                    id: revealBtn
                    width: 80
                    height: 24
                    radius: 4
                    color: Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1

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
                            var b = getBridge()
                            if (b) {
                                b.open_in_file_manager(root.filePath)
                            } else {
                                Qt.openUrlExternally("file://" + root.filePath)
                            }
                        }
                    }
                }

                // Open
                Rectangle {
                    id: openBtn
                    width: 100
                    height: 24
                    radius: 4
                    color: Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1

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
                            var b = getBridge()
                            if (b) {
                                b.open_in_external_editor(root.filePath)
                            } else {
                                Qt.openUrlExternally("file://" + root.filePath)
                            }
                        }
                    }
                }
            }

            Row {
                id: leftHeader
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.right: headerActions.left
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                clip: true

                Rectangle {
                    width: 20
                    height: 20
                    radius: 4
                    color: "transparent"
                    border.color: root.accentColor
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "P"
                        color: root.accentColor
                        font.family: Theme.fontCode
                        font.pixelSize: 10
                        font.bold: true
                    }
                }

                Text {
                    id: titleText
                    text: root.fileName
                    color: Theme.textPrimary
                    font.family: Theme.fontCode
                    font.pixelSize: 12
                    font.bold: true
                    elide: Text.ElideRight
                    width: Math.max(40, Math.min(implicitWidth, leftHeader.width - (20 + 8 + 5 + 8 + metadataText.implicitWidth + 16)))
                    anchors.verticalCenter: parent.verticalCenter
                }

                Rectangle {
                    width: 5
                    height: 5
                    radius: 2.5
                    anchors.verticalCenter: parent.verticalCenter
                    color: root.accentColor
                    opacity: 0.3
                }

                Text {
                    id: metadataText
                    text: (imgElement.naturalWidth > 0 ? Math.round(imgElement.naturalWidth) : 1200) + "x" + (imgElement.naturalHeight > 0 ? Math.round(imgElement.naturalHeight) : 1600) + " | " + root.sizeFormatted
                    color: Theme.textDimmed
                    font.family: Theme.fontCode
                    font.pixelSize: 10
                    elide: Text.ElideMiddle
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

        // Viewport
        Rectangle {
            id: viewportContainerRect
            anchors.top: header.bottom
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 12
            color: "#0d1117"
            opacity: 1.0

            Flickable {
                id: viewport
                anchors.fill: parent
                clip: true
                visible: !root.hasError
                interactive: !root.isFitted
                contentWidth: root.isFitted ? width : Math.max(imgElement.width * root.zoomLevel, width)
                contentHeight: root.isFitted ? height : Math.max(imgElement.height * root.zoomLevel, height)

                Image {
                    id: imgElement
                    objectName: "imgElement"
                    property real naturalWidth: (sourceSize.width > 0) ? sourceSize.width : ((implicitWidth > 0) ? implicitWidth : 1200)
                    property real naturalHeight: (sourceSize.height > 0) ? sourceSize.height : ((implicitHeight > 0) ? implicitHeight : 1600)
                    visible: status === Image.Ready
                    cache: true
                    asynchronous: true
                    source: root.renderedPageSource
                    fillMode: Image.PreserveAspectFit
                    smooth: true

                    width: root.isFitted ? viewport.width : naturalWidth
                    height: root.isFitted ? viewport.height : naturalHeight
                    
                    transform: Scale {
                        origin.x: 0
                        origin.y: 0
                        xScale: root.isFitted ? 1.0 : root.zoomLevel
                        yScale: root.isFitted ? 1.0 : root.zoomLevel
                    }

                    x: root.isFitted ? 0 : Math.max((viewport.width - width * root.zoomLevel) / 2, 0)
                    y: root.isFitted ? 0 : Math.max((viewport.height - height * root.zoomLevel) / 2, 0)

                    onStatusChanged: {
                        if (status === Image.Ready) {
                            root.aspectSized = false
                            if (root && typeof root.applyAspectSizing === "function") {
                                root.applyAspectSizing()
                            }
                        }
                    }

                    onSourceSizeChanged: {
                        if (root && typeof root.applyAspectSizing === "function") {
                            root.applyAspectSizing()
                        }
                    }
                }

                TapHandler {
                    acceptedButtons: Qt.LeftButton
                    onDoubleTapped: {
                        root.toggleZoomFit()
                    }
                }

                WheelHandler {
                    onWheel: (wheel) => {
                        if (root.isFitted) {
                            wheel.accepted = false
                            return
                        }
                        
                        wheel.accepted = true
                        var zoomFactor = wheel.angleDelta.y > 0 ? 1.1 : 0.9
                        var newZoom = Math.max(0.1, Math.min(8.0, root.zoomLevel * zoomFactor))
                        
                        var contentX = viewport.contentX
                        var contentY = viewport.contentY
                        var mouseX = wheel.point.position.x
                        var mouseY = wheel.point.position.y

                        root.zoomLevel = newZoom

                        viewport.contentX = Math.max(0, mouseX * zoomFactor - (mouseX - contentX))
                        viewport.contentY = Math.max(0, mouseY * zoomFactor - (mouseY - contentY))
                    }
                }
            }

            // Error Fallback Overlay
            Rectangle {
                visible: root.hasError
                anchors.fill: parent
                color: "#0d1117"
                z: 10

                Column {
                    anchors.centerIn: parent
                    spacing: 16
                    width: parent.width - 32

                    Row {
                        spacing: 16
                        anchors.horizontalCenter: parent.horizontalCenter

                        // File Icon badge
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
                                    text: "PDF"
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
                                    width: Math.min(180, parent.parent.width - 76)
                                }

                                Text {
                                    text: "Format decoder not available"
                                    color: "#f87171"
                                    font.family: Theme.fontCode
                                    font.pixelSize: 10
                                }
                            }
                        }

                        // Open in External App action button
                        Rectangle {
                            id: extOpenBtn
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
                                onEntered: extOpenBtn.color = Theme.surfaceButtonHover
                                onExited: extOpenBtn.color = Theme.surfaceButton
                            onClicked: {
                                var b = getBridge()
                                if (b) {
                                    b.open_in_external_editor(root.filePath)
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

    // Toast Notification Overlay
    Rectangle {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        height: 32
        radius: 16
        color: Theme.surfaceButton
        border.color: Theme.borderSubtle
        border.width: 1
        opacity: 0.0
        z: 100
        
        width: toastText.implicitWidth + 32

        Text {
            id: toastText
            anchors.centerIn: parent
            text: ""
            color: "#ef4444" // Crimson matching the accent Color
            font.family: Theme.fontCode
            font.pixelSize: 11
            font.bold: true
        }

        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }

        Timer {
            id: toastTimer
            interval: 2000
            onTriggered: toast.opacity = 0.0
        }

        function show(msg) {
            toastText.text = msg
            toast.opacity = 0.95
            toastTimer.restart()
        }
    }
}
