import QtQuick

Item {
    id: auraRoot
    anchors.fill: parent

    // Public Interface Contract
    property bool isNew: false
    property bool isDeleted: false
    property color accentColor: "#00E5FF"
    property real radius: 8

    // Spawn pop-in & neon border decay animation logic
    // Delete pop-out / fade-out animation logic
    property real spawnScaleMultiplier: 0.2
    property real spawnOpacityMultiplier: 0.0
    property real deleteScaleMultiplier: 1.0
    property real deleteOpacityMultiplier: 1.0
    property real spawnGlowOpacity: 1.0

    readonly property bool isSpawnActive: spawnAnimation.running
    readonly property bool isDeleteActive: deleteAnimation.running

    ParallelAnimation {
        id: spawnAnimation
        running: true
        NumberAnimation {
            target: auraRoot
            property: "spawnScaleMultiplier"
            from: 0.2
            to: 1.0
            duration: 350
            easing.type: Easing.OutBack
        }
        NumberAnimation {
            target: auraRoot
            property: "spawnOpacityMultiplier"
            from: 0.0
            to: 1.0
            duration: 250
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: auraRoot
            property: "spawnGlowOpacity"
            from: 1.0
            to: 0.0
            duration: 3000
            easing.type: Easing.OutQuad
        }
    }

    ParallelAnimation {
        id: deleteAnimation
        running: auraRoot.isDeleted
        NumberAnimation {
            target: auraRoot
            property: "deleteScaleMultiplier"
            from: 1.0
            to: 0.0
            duration: 250
            easing.type: Easing.InBack
        }
        NumberAnimation {
            target: auraRoot
            property: "deleteOpacityMultiplier"
            from: 1.0
            to: 0.0
            duration: 250
            easing.type: Easing.OutCubic
        }
    }

    // Vibrant neon aura border overlay
    Rectangle {
        anchors.fill: parent
        radius: auraRoot.radius
        color: "transparent"
        border.color: auraRoot.accentColor
        border.width: 3.0
        opacity: auraRoot.spawnGlowOpacity
        visible: opacity > 0.01
        antialiasing: true
    }
}
