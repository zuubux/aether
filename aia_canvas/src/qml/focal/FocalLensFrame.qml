import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root
    objectName: "focalLensFrame"
    property bool active: false
    property real targetCenterY: 100
    property string activeContext: ""
    property var turnHistory: []

    anchors.fill: parent

    MouseArea {
        id: backdropArea
        objectName: "lensBackdrop"
        anchors.fill: parent
        enabled: root.active || lensStateGroup.state === "opened"
        onClicked: root.close()
    }

    Rectangle {
        id: lensContainer
        objectName: "lensContainer"
        width: 800; height: 600
        anchors.horizontalCenter: parent.horizontalCenter
        
        scale: 0.88; opacity: 0.0; y: root.targetCenterY + 32; visible: false
        color: Theme.surfaceElevated; border.color: Theme.borderSubtle
        border.width: 1; radius: 12

        MouseArea {
            id: interiorAbsorber
            objectName: "interiorAbsorber"
            anchors.fill: parent
        }

        Item {
            id: header
            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; height: 48

            Text {
                anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 20
                text: root.activeContext || "Focal Lens"
                color: Theme.textPrimary
            }

            Rectangle {
                id: pinBtn
                objectName: "pinBtn"
                width: 32; height: 32
                anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right; anchors.rightMargin: 12
                color: pinMouseArea.containsMouse ? Theme.surfaceHovered : "transparent"
                border.color: pinMouseArea.containsMouse ? Theme.borderHover : "transparent"; border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "⚲"; font.pixelSize: 18
                    color: pinMouseArea.containsMouse ? Theme.accentCyan : Theme.textMuted
                }

                MouseArea {
                    id: pinMouseArea
                    anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof bridge !== "undefined" && bridge) bridge.pin_conversation(root.activeContext)
                        else if (typeof canvasBridge !== "undefined" && canvasBridge) canvasBridge.pin_conversation(root.activeContext)
                        root.close()
                    }
                }
            }
        }

        ScrollView {
            id: slateScrollView
            objectName: "slateScrollView"
            anchors.top: header.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 16
            clip: true
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            ListView {
                id: slateListView
                objectName: "slateListView"
                width: parent.width
                model: root.turnHistory
                spacing: 16

                delegate: Column {
                    width: slateListView.width
                    spacing: 8
                    visible: (modelData.prompt && modelData.prompt.trim().length > 0) || (modelData.response && modelData.response.trim().length > 0)

                    Rectangle {
                        id: userBubble
                        width: parent.width
                        implicitHeight: userCol.implicitHeight + 20
                        height: implicitHeight
                        visible: modelData.prompt && modelData.prompt.trim().length > 0
                        color: Qt.rgba(30/255, 41/255, 59/255, 0.5)
                        radius: 8

                        Column {
                            id: userCol
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 10
                            spacing: 4

                            Text {
                                text: "User"
                                font.bold: true
                                font.pixelSize: 12
                                font.family: Theme.fontCode
                                color: Theme.accentCyan
                            }
                            Text {
                                width: parent.width
                                text: (modelData.prompt || "").replace(/^[\?\s]+/, "")
                                wrapMode: Text.Wrap
                                font.pixelSize: 14
                                color: Theme.textPrimary
                            }
                        }
                    }

                    Column {
                        id: aetherTurn
                        width: parent.width
                        spacing: 4
                        topPadding: 12
                        bottomPadding: 12
                        visible: modelData.response && modelData.response.trim().length > 0

                        Text {
                            text: "Aether"
                            font.bold: true
                            font.pixelSize: 12
                            font.family: Theme.fontCode
                            color: Theme.accentAI
                        }
                        Text {
                            width: parent.width
                            text: modelData.response || ""
                            wrapMode: Text.Wrap
                            textFormat: Text.MarkdownText
                            font.pixelSize: 14
                            color: Theme.textPrimary
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Theme.borderSubtle
                        opacity: 0.3
                    }
                }
            }
        }

        StateGroup {
            id: lensStateGroup
            states: [
                State { name: "opened"; when: root.active; PropertyChanges { target: lensContainer; scale: 1.0; opacity: 1.0; y: root.targetCenterY; visible: true } },
                State { name: "closed"; when: !root.active; PropertyChanges { target: lensContainer; scale: 0.88; opacity: 0.0; y: root.targetCenterY + 32; visible: false } }
            ]
            transitions: [
                Transition {
                    from: "closed"; to: "opened"
                    SequentialAnimation {
                        PropertyAction { target: lensContainer; property: "visible"; value: true }
                        ParallelAnimation {
                            NumberAnimation { target: lensContainer; property: "opacity"; duration: Theme.animLensOpenDuration; easing.type: Theme.animLensOpenEasing }
                            NumberAnimation { target: lensContainer; property: "scale"; duration: Theme.animLensOpenDuration; easing.type: Theme.animLensOpenEasing }
                            NumberAnimation { target: lensContainer; property: "y"; duration: Theme.animLensOpenDuration; easing.type: Theme.animLensOpenEasing }
                        }
                    }
                },
                Transition {
                    from: "opened"; to: "closed"
                    SequentialAnimation {
                        ParallelAnimation {
                            NumberAnimation { target: lensContainer; property: "opacity"; duration: Theme.animLensCloseDuration; easing.type: Theme.animLensCloseEasing }
                            NumberAnimation { target: lensContainer; property: "scale"; duration: Theme.animLensCloseDuration; easing.type: Theme.animLensCloseEasing }
                            NumberAnimation { target: lensContainer; property: "y"; duration: Theme.animLensCloseDuration; easing.type: Theme.animLensCloseEasing }
                        }
                        PropertyAction { target: lensContainer; property: "visible"; value: false }
                    }
                }
            ]
        }
    }

    function open(context, turns) {
        if (context) root.activeContext = context;
        if (turns) root.turnHistory = turns;
        root.active = true;
    }

    function close() { root.active = false; }
}