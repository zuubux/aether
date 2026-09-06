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