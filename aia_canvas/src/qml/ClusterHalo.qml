import QtQuick

Item {
    id: rootHalo

    property real centerX: 0
    property real centerY: 0
    property real haloWidth: 280   // Replacing haloRadius
    property real haloHeight: 280  // Replacing haloRadius
    property color haloColor: "#38bdf8"
    property bool isFocalCluster: false
    property int nodeCount: 3
    property real currentAperture: 1.0

    // =========================================================================
    // 2.5D Panoramic Projection Math
    // =========================================================================
    readonly property real vpX: parent ? parent.width / 2 : 1280
    readonly property real vpY: parent ? parent.height * 0.20 : 280

    readonly property real depthZ: Math.max(0.0, Math.min(1.0, 1.0 - (centerY / (parent ? parent.height : 1440))))
    readonly property real pScale: 1.0 / (1.0 + depthZ * 1.25)
    readonly property real xSpreadFactor: 0.85 + 0.15 * pScale

    readonly property real projX: vpX + (centerX - vpX) * xSpreadFactor
    readonly property real projY: vpY + (centerY - vpY) * pScale
    
    // Scale both width and height independently based on depth
    readonly property real projWidth: Math.max(56.0, haloWidth * pScale)
    readonly property real projHeight: Math.max(56.0, haloHeight * pScale)

    // Dynamic Horizon Geometry
    x: projX - width / 2
    y: projY - height / 2
    width: projWidth
    height: projHeight

    Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutSine } }
    Behavior on y { NumberAnimation { duration: 160; easing.type: Easing.OutSine } }
    Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
    Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    // Depth Stacking (Distant nebulae render behind foreground elements)
    z: Math.round((1.0 - depthZ) * 200)

    // =========================================================================
    // Aperture & Density Gating with Atmospheric Depth Attenuation
    // =========================================================================
    // Macro Gating: Smooth ramp between 40% and 25% zoom
    readonly property real apertureRamp: {
        if (isFocalCluster || currentAperture > 0.40) return 0.0
        return Math.min(1.0, (0.40 - currentAperture) / 0.15)
    }

    // Population Scaling: Soft whisper for 3 nodes, rich celestial nebula for 8+
    readonly property real populationWeight: Math.min(1.0, Math.max(0.40, rootHalo.nodeCount / 8.0))

    // Atmospheric Haze Factor
    readonly property real depthAttenuation: 1.0 - (depthZ * 0.35)

    opacity: apertureRamp * populationWeight * depthAttenuation
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
        // PERFECT PILL CAPSULE RADIUS
        radius: Math.min(width, height) / 2.0 
        color: rootHalo.haloColor
        opacity: 0.035
    }

    // 2. Outer Resonant Aura
    Rectangle {
        anchors.centerIn: parent
        width: parent.width + 12 * rootHalo.pScale
        height: parent.height + 12 * rootHalo.pScale
        // PERFECT PILL CAPSULE RADIUS
        radius: Math.min(width, height) / 2.0
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
        // PERFECT PILL CAPSULE RADIUS
        radius: Math.min(width, height) / 2.0
        color: "transparent"
        border.color: rootHalo.haloColor
        border.width: rootHalo.isFocalCluster ? 1.5 : 1.0
        opacity: rootHalo.isFocalCluster ? 0.45 : 0.28
    }
}