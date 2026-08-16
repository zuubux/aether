import QtQuick

Item {
    id: rootHalo

    property real centerX: 0
    property real centerY: 0
    property real haloRadius: 140
    property color haloColor: "#38bdf8"
    property bool isFocalCluster: false
    property int nodeCount: 2
    property real currentAperture: 1.0

    x: centerX - width / 2
    y: centerY - height / 2
    width: haloRadius * 2
    height: haloRadius * 2

    Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutSine } }
    Behavior on y { NumberAnimation { duration: 140; easing.type: Easing.OutSine } }
    Behavior on width { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    Behavior on height { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

    z: 10

    // Macro Gating: Fades in smoothly as aperture dips below 60%
    readonly property real apertureRamp: {
        if (isFocalCluster || currentAperture >= 0.35) {
            return 0.0
        }
        return Math.max(0.0, Math.min(1.0, (0.35 - currentAperture) / 0.15))
    }

    opacity: apertureRamp
    visible: opacity > 0.005

    Behavior on opacity {
        NumberAnimation { duration: 240; easing.type: Easing.OutCubic }
    }

    // =========================================================================
    // Enterprise Shield Membrane
    // =========================================================================

    // 1. Soft Uniform Glass Interior Wash
    Rectangle {
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        radius: width / 2
        color: rootHalo.haloColor
        opacity: 0.035
    }

    // 2. Outer Resonant Aura (Faint secondary hairline)
    Rectangle {
        anchors.centerIn: parent
        width: parent.width + 8
        height: parent.height + 8
        radius: width / 2
        color: "transparent"
        border.color: rootHalo.haloColor
        border.width: 1
        opacity: 0.12
    }

    // 3. Primary Shield Perimeter (Crisp Glowing Boundary)
    Rectangle {
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        radius: width / 2
        color: "transparent"
        border.color: rootHalo.haloColor
        border.width: 1.5
        opacity: 0.38
    }
}