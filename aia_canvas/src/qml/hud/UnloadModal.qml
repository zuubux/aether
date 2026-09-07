import QtQuick
import QtQuick.Controls
import ".."

FocusScope {
    id: root
    anchors.fill: parent
    visible: isOpen
    focus: isOpen

    property bool isOpen: false

    signal cancelled()
    signal confirmed()

    onIsOpenChanged: {
        if (isOpen) {
            root.forceActiveFocus();
        }
    }

    function cancel() {
        if (!isOpen) return;
        isOpen = false;
        cancelled();
    }

    function confirm() {
        if (!isOpen) return;
        confirmed();
        Qt.quit();
    }

    Keys.onPressed: function(event) {
        if (!isOpen) return;
        if (event.key === Qt.Key_Escape) {
            event.accepted = true;
            cancel();
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            event.accepted = true;
            confirm();
        }
    }

    Keys.onEscapePressed: function(event) {
        event.accepted = true;
        cancel();
    }

    Keys.onReturnPressed: function(event) {
        event.accepted = true;
        confirm();
    }

    Keys.onEnterPressed: function(event) {
        event.accepted = true;
        confirm();
    }

    // Scrim background: Full-window Rectangle (#07080B) fading in to 0.75 opacity
    Rectangle {
        id: scrim
        anchors.fill: parent
        color: "#07080B"
        opacity: root.isOpen ? 0.75 : 0.0

        Behavior on opacity {
            NumberAnimation {
                duration: Theme.animFadeInDuration
                easing.type: Easing.OutCubic
            }
        }

        MouseArea {
            anchors.fill: parent
            preventStealing: true
            onClicked: root.cancel()
        }
    }

    // Elevated dialog container: Centered glass card matching Aether theme
    Rectangle {
        id: dialogCard
        anchors.centerIn: parent
        width: Math.min(460, (parent && parent.width > 0) ? parent.width - 48 : 460)
        height: 190
        radius: 12
        color: "#0C0E14"
        border.width: 1
        border.color: "#1E293B"

        // Prevent click-through to scrim
        MouseArea {
            anchors.fill: parent
        }

        Column {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 12

            Text {
                id: headerText
                text: "Unload Aether?"
                font.family: Theme.fontSans
                font.pixelSize: 18
                font.weight: Font.DemiBold
                color: "#F8FAFC"
            }

            Text {
                id: bodyText
                width: parent.width
                text: "Your session will be saved and the workspace closed."
                font.family: Theme.fontSans
                font.pixelSize: 13
                lineHeight: 1.4
                color: "#94A3B8"
                wrapMode: Text.WordWrap
            }

            Item {
                width: parent.width
                height: 6
            }

            Row {
                anchors.right: parent.right
                spacing: 12

                // Cancel Button
                Rectangle {
                    id: cancelBtn
                    width: cancelLabel.implicitWidth + 24
                    height: 34
                    radius: 6
                    color: cancelMouseArea.containsMouse ? "#263042" : "#161B22"
                    border.width: 0

                    Text {
                        id: cancelLabel
                        anchors.centerIn: parent
                        text: "Cancel"
                        font.family: Theme.fontSans
                        font.pixelSize: 12
                        font.weight: Font.Medium
                        color: "#C9D1D9"
                    }

                    MouseArea {
                        id: cancelMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.cancel()
                    }
                }

                // Unload Button
                Rectangle {
                    id: unloadBtn
                    width: unloadLabel.implicitWidth + 24
                    height: 34
                    radius: 6
                    color: unloadMouseArea.containsMouse ? "#DC2626" : "#B91C1C"
                    border.width: 0

                    Text {
                        id: unloadLabel
                        anchors.centerIn: parent
                        text: "Unload"
                        font.family: Theme.fontSans
                        font.pixelSize: 12
                        font.weight: Font.Medium
                        color: "#FFFFFF"
                    }

                    MouseArea {
                        id: unloadMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.confirm()
                    }
                }
            }
        }
    }
}
