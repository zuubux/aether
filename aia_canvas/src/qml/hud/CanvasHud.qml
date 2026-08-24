import QtQuick
import ".."

Row {
    id: bottomHud
    anchors.bottom: parent ? parent.bottom : undefined
    anchors.left: parent ? parent.left : undefined
    anchors.margins: 20
    spacing: 12
    z: 10

    // IPC Status Pill
    Rectangle {
        width: 130
        height: 30
        radius: 15
        color: Theme.surfaceButton
        border.color: (canvasBridge && canvasBridge.isConnected) ? Theme.accentSuccess : Theme.borderSubtle
        border.width: 1
        opacity: 0.85

        Row {
            anchors.centerIn: parent
            spacing: 8

            Rectangle {
                width: 7
                height: 7
                radius: 3.5
                color: (canvasBridge && canvasBridge.isConnected) ? Theme.accentSuccess : Theme.textDimmed
                anchors.verticalCenter: parent.verticalCenter

                SequentialAnimation on opacity {
                    running: canvasBridge ? canvasBridge.isConnected : false
                    loops: Animation.Infinite
                    PropertyAnimation { to: 0.4; duration: 1200; easing.type: Easing.InOutSine }
                    PropertyAnimation { to: 1.0; duration: 1200; easing.type: Easing.InOutSine }
                }
            }

            Text {
                text: (canvasBridge && canvasBridge.isConnected) ? "Weaver Live" : "Standalone"
                color: (canvasBridge && canvasBridge.isConnected) ? Theme.textPrimary : Theme.textMuted
                font.family: Theme.fontCode
                font.pixelSize: 10
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    // Aperture Gauge Pill
    Rectangle {
        width: 140
        height: 30
        radius: 15
        color: Theme.surfaceButton
        border.color: Theme.borderSubtle
        border.width: 1
        opacity: 0.85

        Row {
            anchors.centerIn: parent
            spacing: 8

            Text {
                text: "Aperture"
                color: Theme.textDimmed
                font.family: Theme.fontCode
                font.pixelSize: 10
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: Math.round((canvasBridge ? canvasBridge.aperture : 1.0) * 100) + "%"
                color: Theme.accentFocus
                font.family: Theme.fontCode
                font.pixelSize: 11
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
