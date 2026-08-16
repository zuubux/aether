import QtQuick

Item {
    id: rootHalo

    property real centerX: 0
    property real centerY: 0
    property real haloRadius: 140
    property color haloColor: "#38bdf8"
    property bool isFocalCluster: false
    property int nodeCount: 3
    property real currentAperture: 1.0

    x: centerX - width / 2
    y: centerY - height / 2
    width: haloRadius * 2
    height: haloRadius * 2

    Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutSine } }
    Behavior on y { NumberAnimation { duration: 160; easing.type: Easing.OutSine } }
    Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
    Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    z: 10

    // Macro Gating: Smooth ramp between 40% and 25% zoom
    readonly property real apertureRamp: {
        if (isFocalCluster || currentAperture > 0.40) return 0.0
        return Math.min(1.0, (0.40 - currentAperture) / 0.15)
    }

    // Population Scaling: Soft whisper for 3 nodes, rich celestial nebula for 8+
    readonly property real populationWeight: Math.min(1.0, Math.max(0.40, rootHalo.nodeCount / 8.0))

    opacity: apertureRamp * populationWeight
    visible: opacity > 0.005

    Behavior on opacity {
        NumberAnimation { duration: 260; easing.type: Easing.OutCubic }
    }

    // =========================================================================
    // Atmospheric Celestial Nebula Membrane
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

    // 2. Outer Resonant Aura
    Rectangle {
        anchors.centerIn: parent
        width: parent.width + 12
        height: parent.height + 12
        radius: width / 2
        color: "transparent"
        border.color: rootHalo.haloColor
        border.width: 1
        opacity: 0.10
    }

    // 3. Primary Shield Perimeter (Refined Hairline)
    Rectangle {
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        radius: width / 2
        color: "transparent"
        border.color: rootHalo.haloColor
        border.width: 1.0
        opacity: 0.28
    }
}