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
    width: projWidth * 2.6
    height: projHeight * 2.6

    Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutSine } }
    Behavior on y { NumberAnimation { duration: 160; easing.type: Easing.OutSine } }
    Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
    Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    // Depth Stacking (Distant nebulae render behind foreground elements)
    z: Math.round((1.0 - depthZ) * 200)

    // =========================================================================
    // Aperture & Density Gating with Atmospheric Depth Attenuation
    // =========================================================================
    // Macro Gating: Smooth ramp between 35% and 20% zoom
    readonly property real apertureRamp: {
        if (isFocalCluster || currentAperture > 0.35) return 0.0
        return Math.min(1.0, (0.35 - currentAperture) / 0.15)
    }

    property real densityWeight: 1.0

    // Population Scaling: Soft whisper for 3 nodes, rich celestial nebula for 8+
    readonly property real populationWeight: Math.min(1.0, Math.max(0.40, rootHalo.nodeCount / 8.0))

    // Atmospheric Haze Factor
    readonly property real depthAttenuation: 1.0 - (depthZ * 0.35)

    opacity: apertureRamp * populationWeight * depthAttenuation * densityWeight
    visible: opacity > 0.005

    Behavior on opacity {
        NumberAnimation { duration: 260; easing.type: Easing.OutCubic }
    }

    // =========================================================================
    // Activity-Based Drift Speed (Biological Respiration vs Active Surge)
    // =========================================================================
    property real lastCenterX: centerX
    property real lastCenterY: centerY
    property real activityLevel: 0.0
    property real timeDrift: 0.0

    Timer {
        interval: 16
        running: rootHalo.visible
        repeat: true
        onTriggered: {
            // Calculate spatial displacement to infer "active movement"
            let dx = rootHalo.centerX - rootHalo.lastCenterX
            let dy = rootHalo.centerY - rootHalo.lastCenterY
            let dist = Math.sqrt(dx * dx + dy * dy)

            if (dist > 0.5) {
                // Surge activity quickly when moving
                rootHalo.activityLevel = Math.min(1.0, rootHalo.activityLevel + 0.1)
            } else {
                // Settle gently into biological respiration cadence
                rootHalo.activityLevel = Math.max(0.0, rootHalo.activityLevel - 0.01)
            }

            // Drift speed logic
            let baseSpeed = 0.05
            let surgeSpeed = 0.5
            let currentSpeed = baseSpeed + (rootHalo.activityLevel * surgeSpeed)

            // Increment timeDrift. Using interval / 1000.0 as approximate delta time
            rootHalo.timeDrift += (16.0 / 1000.0) * currentSpeed

            rootHalo.lastCenterX = rootHalo.centerX
            rootHalo.lastCenterY = rootHalo.centerY
        }
    }

    // =========================================================================
    // Atmospheric Celestial Nebula Membrane (Volumetric SDF)
    // =========================================================================

    ShaderEffect {
        id: nebulaShader
        anchors.fill: parent

        // Uniforms bound to QML properties automatically
        // width and height are provided by the ShaderEffect Item itself
        property real time: rootHalo.timeDrift
        property color haloColor: rootHalo.haloColor
        
        // Load the compiled Qt Shader Baker file
        fragmentShader: "halo.frag.qsb"
    }
}
