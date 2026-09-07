import QtQuick
import QtQuick.Controls
import ".."
import "."

Item {
    id: root
    objectName: "workspaceSlates"

    readonly property var workingSetCtrl: {
        var b = (typeof bridge !== "undefined" && bridge) ? bridge : ((typeof canvasBridge !== "undefined" && canvasBridge) ? canvasBridge : null);
        if (b && b.workingSetCtrl) return b.workingSetCtrl;
        if (b && b.workingSet) return b.workingSet;
        return null;
    }

    readonly property int activeCount: workingSetCtrl && workingSetCtrl.activeSlates ? workingSetCtrl.activeSlates.length : 0
    readonly property real densityScale: Math.max(0.30, 1.0 - (activeCount * 0.08))

    function dismissSlate(nodeId) {
        if (workingSetCtrl) {
            if (typeof workingSetCtrl.dismissSlate === "function") {
                workingSetCtrl.dismissSlate(nodeId);
            } else if (typeof workingSetCtrl.dismiss_slate === "function") {
                workingSetCtrl.dismiss_slate(nodeId);
            }
        }
    }

    function promoteToFocal(nodeId) {
        if (workingSetCtrl) {
            if (typeof workingSetCtrl.promoteToFocal === "function") {
                workingSetCtrl.promoteToFocal(nodeId);
            } else if (typeof workingSetCtrl.promote_to_focal === "function") {
                workingSetCtrl.promote_to_focal(nodeId);
            }
        }
    }

    Repeater {
        id: slateRepeater
        objectName: "slateRepeater"
        model: (typeof bridge !== "undefined" && bridge && bridge.workingSetCtrl) ? bridge.workingSetCtrl.activeSlates : (workingSetCtrl ? workingSetCtrl.activeSlates : [])

        delegate: SlateFrame {
            id: satelliteFrame
            objectName: "satelliteSlateFrame"
            required property var modelData
            required property int index

            tierState: "TIER_1_25_SATELLITE"
            resizable: false
            titleText: (modelData && modelData.title) ? modelData.title : ("Node " + (modelData ? modelData.nodeId : ""))
            subtitleText: (modelData && modelData.archetype) ? modelData.archetype : "document"
            accentColor: Theme.getBadgeColor("", (modelData && modelData.archetype) ? modelData.archetype : "")

            readonly property bool isLeftFlank: (index % 2 === 0)
            readonly property int flankRank: Math.floor(index / 2)

            targetWidth: Math.round(Math.min(624, (root.width > 0 ? root.width * 0.42 : 624)) * root.densityScale)
            targetHeight: Math.round(Math.min(492, (root.height > 0 ? root.height * 0.48 : 492)) * root.densityScale)
            width: targetWidth
            height: targetHeight

            readonly property real flankXOffset: flankRank * 24 * root.densityScale
            readonly property real targetFlankX: isLeftFlank
                ? Math.round(root.width * 0.03 + flankXOffset)
                : Math.round(root.width - width - (root.width * 0.03) - flankXOffset)

            readonly property real startY: root.height * 0.08
            readonly property real cascadeStepY: height * 0.52 + 20
            readonly property real targetFlankY: Math.round(Math.min(root.height - height - 32, Math.max(32, startY + (flankRank * cascadeStepY))))

            x: targetFlankX
            y: targetFlankY
            z: 50 + index

            Behavior on x {
                NumberAnimation {
                    duration: Theme.animDuration
                    easing.type: Theme.animEasing
                }
            }
            Behavior on y {
                NumberAnimation {
                    duration: Theme.animDuration
                    easing.type: Theme.animEasing
                }
            }
            Behavior on width {
                NumberAnimation {
                    duration: Theme.animDuration
                    easing.type: Theme.animEasing
                }
            }
            Behavior on height {
                NumberAnimation {
                    duration: Theme.animDuration
                    easing.type: Theme.animEasing
                }
            }
            headerRightContent: [
                Rectangle {
                    id: dismissBtn
                    objectName: "dismissButton"
                    width: 28
                    height: 28
                    radius: 6
                    color: dismissMouseArea.containsMouse ? Theme.surfaceButtonHover : "transparent"

                    MouseArea {
                        id: dismissMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.dismissSlate(modelData.nodeId);
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.pixelSize: 13
                        font.family: Theme.fontSans
                        color: dismissMouseArea.containsMouse ? Theme.textPrimary : Theme.textMuted
                    }
                }
            ]

            Item {
                id: contentSlotArea
                objectName: "slateContentArea"
                anchors.fill: parent

                MouseArea {
                    id: contentMouseArea
                    objectName: "contentClickArea"
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    onClicked: {
                        root.promoteToFocal(modelData.nodeId);
                    }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 12
                    width: Math.min(parent.width - 32, 280)

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 44
                        height: 44
                        radius: 10
                        color: Qt.rgba(1, 1, 1, 0.04)

                        Text {
                            anchors.centerIn: parent
                            text: "✦"
                            font.pixelSize: 18
                            color: Theme.getBadgeColor("", (modelData && modelData.archetype) ? modelData.archetype : "")
                            opacity: 0.8
                        }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: (modelData && modelData.title) ? modelData.title : ("Node " + (modelData ? modelData.nodeId : ""))
                        font.pixelSize: 14
                        font.weight: Font.Medium
                        color: Theme.textPrimary
                        elide: Text.ElideMiddle
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Click to focus"
                        font.pixelSize: 11
                        color: contentMouseArea.containsMouse ? Theme.accentFocus : Theme.textMuted
                        opacity: contentMouseArea.containsMouse ? 1.0 : 0.6
                    }
                }
            }
        }
    }
}
