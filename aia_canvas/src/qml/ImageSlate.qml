import QtQuick
import QtQuick.Controls

FocusScope {
    id: root
    focus: true
    width: Math.round(320)
    height: Math.round(220)

    Keys.onPressed: (event) => {
        if (event.modifiers & Qt.ControlModifier && event.key === Qt.Key_C) {
            var b = getBridge()
            if (b) {
                if (b.copy_image_to_clipboard(root.filePath)) {
                    toast.show("Copied to Clipboard")
                }
            }
            event.accepted = true
        } else if (event.key === Qt.Key_Z || event.key === Qt.Key_1) {
            root.isFitted = !root.isFitted
            root.zoomLevel = 1.0
            if (root.isFitted) {
                viewport.contentX = 0
                viewport.contentY = 0
            } else {
                viewport.contentX = Math.max(0, (viewport.contentWidth - viewport.width) / 2)
                viewport.contentY = Math.max(0, (viewport.contentHeight - viewport.height) / 2)
            }
            event.accepted = true
        } else {
            event.accepted = false
        }
    }

    property int nodeId: 0
    property string filePath: ""
    property string fileName: filePath ? filePath.split('/').pop() : ""
    property string sizeFormatted: "0 KB"
    property string archetype: "asset"
    property color accentColor: "#34d399"
    property bool isSelected: false

    property real zoomLevel: 1.0
    property bool isFitted: true
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

    property string imageSourceUrl: ""
    property bool isLoading: false

    readonly property bool hasError: imgElement.status === Image.Error || (root.filePath !== "" && getBridge() !== null && imageSourceUrl === "" && !isLoading)

    Connections {
        target: getBridge()
        function onImageReady(fPath, url) {
            if (fPath === root.filePath) {
                root.imageSourceUrl = url
                root.isLoading = false
            }
        }
        function onMediaError(fPath, errorMsg) {
            if (fPath === root.filePath) {
                root.isLoading = false
                console.error("Media error:", errorMsg)
            }
        }
    }

    function applyAspectSizing() {
        if (aspectSized) return

        var isFallback = hasError || 
                         (imgElement.status === Image.Ready && (imgElement.naturalWidth <= 48 || imgElement.naturalHeight <= 48));

        if (isFallback) {
            aspectSized = true
            var b = getBridge()
            if (b) {
                b.set_workbench_dimensions(520, 340)
            }
            return
        }

        if (imgElement.status !== Image.Ready) return

        var naturalW = imgElement.naturalWidth
        var naturalH = imgElement.naturalHeight

        if (naturalW <= 0 || naturalH <= 0) return

        var iw = naturalW
        var ih = naturalH

        var vpWidth = viewportContainer ? viewportContainer.width : 1920
        var vpHeight = viewportContainer ? viewportContainer.height : 1080

        var baseTargetWidth = Math.min(vpWidth * 0.65, 1280.0)
        var targetWidth = Math.max(800.0, baseTargetWidth)

        var headerHeight = 40.0
        var baseTargetHeight = targetWidth * (ih / iw) + headerHeight
        var maxH = Math.min(vpHeight * 0.75, 800.0)
        var targetHeight = Math.max(320.0, Math.min(maxH, baseTargetHeight))

        aspectSized = true

        var bDim = getBridge()
        if (bDim) {
            bDim.set_workbench_dimensions(targetWidth, targetHeight)
        }
    }

    function requestImage() {
        var b = getBridge()
        if (b && filePath) {
            isLoading = true
            b.request_image_source(filePath)
        }
    }

    onFilePathChanged: {
        aspectSized = false
        requestImage()
        applyAspectSizing()
    }

    Component.onCompleted: {
        root.forceActiveFocus()
        requestImage()
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

        // Header
        Rectangle {
            id: header
            width: parent.width
            height: 40
            color: "transparent"
            border.width: 0
            anchors.top: parent.top

            Row {
                id: headerActions
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                Rectangle {
                    id: copyBtn
                    width: 90
                    height: 24
                    radius: 4
                    color: Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "Copy Image"
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
                                if (b.copy_image_to_clipboard(root.filePath)) {
                                    toast.show("Copied to Clipboard")
                                }
                            }
                        }
                    }
                }

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
                        text: "I"
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
                    color: "#64d2ff"
                    opacity: 0.3
                }

                Text {
                    id: metadataText
                    text: (imgElement.naturalWidth > 0 ? imgElement.naturalWidth : 520) + "x" + (imgElement.naturalHeight > 0 ? imgElement.naturalHeight : 340) + " | " + root.sizeFormatted
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
                visible: imgElement.status !== Image.Error
                interactive: !root.isFitted
                contentWidth: root.isFitted ? width : Math.max(imgElement.width * root.zoomLevel, width)
                contentHeight: root.isFitted ? height : Math.max(imgElement.height * root.zoomLevel, height)

                Image {
                    id: svgNaturalSizeImage
                    source: {
                        if (!root.filePath) return "";
                        var pathLower = root.filePath.toLowerCase();
                        var isSvg = pathLower.endsWith(".svg") || pathLower.endsWith(".svgz");
                        return isSvg ? imgElement.source : "";
                    }
                    visible: false
                }

                AnimatedImage {
                    id: imgElement
                    objectName: "imgElement"
                    property real naturalWidth: (sourceSize.width > 0) ? sourceSize.width : ((implicitWidth > 0) ? implicitWidth : 520)
                    property real naturalHeight: (sourceSize.height > 0) ? sourceSize.height : ((implicitHeight > 0) ? implicitHeight : 340)
                    visible: status === Image.Ready
                    playing: true
                    paused: false
                    cache: true
                    asynchronous: true
                    source: {
                        if (!root.filePath) return "";
                        return root.imageSourceUrl !== "" ? root.imageSourceUrl : (root.filePath.startsWith("file://") ? root.filePath : "file://" + root.filePath);
                    }
                    fillMode: Image.PreserveAspectFit

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
                        root.isFitted = !root.isFitted
                        if (root.isFitted) {
                            root.zoomLevel = 1.0
                            viewport.contentX = 0
                            viewport.contentY = 0
                        } else {
                            root.zoomLevel = 1.0
                            viewport.contentX = Math.max(0, (viewport.contentWidth - viewport.width) / 2)
                            viewport.contentY = Math.max(0, (viewport.contentHeight - viewport.height) / 2)
                        }
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
            color: "#34d399"
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
