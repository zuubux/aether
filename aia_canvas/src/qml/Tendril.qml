import QtQuick
import QtQuick.Shapes

Item {
    id: rootTendril

    property Item sourceNode: null
    property Item targetNode: null
    property int sourceId: 0
    property int targetId: 0
    property int selectedNodeId: 0
    property int hoveredNodeId: 0
    property string edgeType: "explicit"
    property real weight: 1.0
    property real currentAperture: 1.0

    // Relational Context
    readonly property bool isFirstDegree: selectedNodeId > 0 && (sourceId === selectedNodeId || targetId === selectedNodeId)
    readonly property bool isHoverBloomed: hoveredNodeId > 0 && (sourceId === hoveredNodeId || targetId === hoveredNodeId)
    readonly property bool isSecondDegree: {
        if (isFirstDegree || selectedNodeId <= 0) return false
        var sFocus = sourceNode ? (sourceNode.focusWeight !== undefined ? sourceNode.focusWeight : (sourceNode.nodeModel ? sourceNode.nodeModel.focus : 0)) : 0
        var tFocus = targetNode ? (targetNode.focusWeight !== undefined ? targetNode.focusWeight : (targetNode.nodeModel ? targetNode.nodeModel.focus : 0)) : 0
        return (sFocus > 0.55 && tFocus > 0.35) || (tFocus > 0.55 && sFocus > 0.35)
    }
    readonly property bool isVoidMode: selectedNodeId <= 0

    // Intra-Cluster Detection
    readonly property int sourceClusterId: {
        if (!sourceNode) return -1
        if (sourceNode.nodeModel && sourceNode.nodeModel.clusterId !== undefined) return sourceNode.nodeModel.clusterId
        if (sourceNode.clusterId !== undefined) return sourceNode.clusterId
        return -1
    }
    readonly property int targetClusterId: {
        if (!targetNode) return -1
        if (targetNode.nodeModel && targetNode.nodeModel.clusterId !== undefined) return targetNode.nodeModel.clusterId
        if (targetNode.clusterId !== undefined) return targetNode.clusterId
        return -1
    }
    readonly property bool isIntraCluster: (sourceClusterId >= 0 && targetClusterId >= 0 && sourceClusterId === targetClusterId)
    readonly property bool shouldCullIntra: isIntraCluster && isVoidMode && !isHoverBloomed && (currentAperture <= 0.48)

    // Dynamic Endpoints & Geometry
    readonly property real sCx: sourceNode ? (sourceNode.cardCenterX !== undefined ? sourceNode.cardCenterX : (sourceNode.nodeModel ? sourceNode.nodeModel.x : sourceNode.x)) : 0
    readonly property real sCy: sourceNode ? (sourceNode.cardCenterY !== undefined ? sourceNode.cardCenterY : (sourceNode.nodeModel ? sourceNode.nodeModel.y : sourceNode.y)) : 0
    readonly property real sW: sourceNode ? (sourceNode.cardWidth !== undefined ? sourceNode.cardWidth : 280) : 280
    readonly property real sH: sourceNode ? (sourceNode.cardHeight !== undefined ? sourceNode.cardHeight : 120) : 120

    readonly property real tCx: targetNode ? (targetNode.cardCenterX !== undefined ? targetNode.cardCenterX : (targetNode.nodeModel ? targetNode.nodeModel.x : targetNode.x)) : 0
    readonly property real tCy: targetNode ? (targetNode.cardCenterY !== undefined ? targetNode.cardCenterY : (targetNode.nodeModel ? targetNode.nodeModel.y : targetNode.y)) : 0
    readonly property real tW: targetNode ? (targetNode.cardWidth !== undefined ? targetNode.cardWidth : 280) : 280
    readonly property real tH: targetNode ? (targetNode.cardHeight !== undefined ? targetNode.cardHeight : 120) : 120

    readonly property real jitterSeed: ((sourceId * 37 + targetId * 19) % 16) - 8

    function calculateSynapticPoint(cx, cy, w, h, targetX, targetY, jitter) {
        var dx = targetX - cx
        var dy = targetY - cy
        if (dx === 0 && dy === 0) return Qt.point(cx, cy)

        var halfW = w / 2
        var halfH = h / 2

        if (Math.abs(dx) * halfH > Math.abs(dy) * halfW) {
            var signX = dx > 0 ? 1 : -1
            var clampedJitter = Math.max(-halfH + 12, Math.min(halfH - 12, jitter))
            return Qt.point(cx + (signX * halfW), cy + (dy / Math.abs(dx)) * halfW + clampedJitter)
        } else {
            var signY = dy > 0 ? 1 : -1
            var clampedJitter = Math.max(-halfH + 12, Math.min(halfH - 12, jitter))
            return Qt.point(cx + (dx / Math.abs(dy)) * halfH + clampedJitter, cy + (signY * halfH))
        }
    }

    readonly property point startPt: (sourceNode && targetNode) ?
        calculateSynapticPoint(sCx, sCy, sW, sH, tCx, tCy, jitterSeed) : Qt.point(0, 0)

    readonly property point endPt: (sourceNode && targetNode) ?
        calculateSynapticPoint(tCx, tCy, tW, tH, sCx, sCy, -jitterSeed) : Qt.point(0, 0)

    // =========================================================================
    // Neutral-Buoyancy Fluid Geometry (Perpendicular Normal Deflection)
    // =========================================================================
    readonly property real deltaX: endPt.x - startPt.x
    readonly property real deltaY: endPt.y - startPt.y
    readonly property real spanDist: Math.max(1.0, Math.sqrt(deltaX * deltaX + deltaY * deltaY))

    // Unit Chord & Normal Vectors
    readonly property real dirX: deltaX / spanDist
    readonly property real dirY: deltaY / spanDist
    readonly property real normX: -dirY
    readonly property real normY: dirX

    // Tangent Projection Length
    readonly property real tangentLength: Math.min(spanDist * 0.35, 160.0)

    // Edge-Specific Chirality & Fluid Arc Amplitude
    readonly property real strandChirality: ((sourceId * 31 + targetId * 17) % 2 === 0) ? 1.0 : -1.0
    readonly property real fluidBaseAmp: Math.min(24.0, Math.max(8.0, spanDist * 0.09))
    
    // Slow Fluid Micro-Sway (Tied to Respiration Phase)
    readonly property real fluidSway: Math.sin(pulsePhase * 6.28318 + (sourceId % 7)) * 4.0
    readonly property real normalOffset: (fluidBaseAmp * strandChirality) + fluidSway

    // Workbench Egress Projection (Gently kicks straight outward from lens walls)
    readonly property real focalBiasX: {
        if (!isFirstDegree || !sourceNode) return 0.0
        var fcx = sourceId === selectedNodeId ? sCx : tCx
        var ptX = sourceId === selectedNodeId ? startPt.x : endPt.x
        return (ptX - fcx) > 0 ? 1.0 : -1.0
    }
    readonly property real emergenceKick: isFirstDegree ? Math.min(32.0, spanDist * 0.18) : 0.0

    // Fluid Spline Control Points
    readonly property real cp1X: startPt.x + (dirX * tangentLength) + (normX * normalOffset) + (sourceId === selectedNodeId ? focalBiasX * emergenceKick : 0.0)
    readonly property real cp1Y: startPt.y + (dirY * tangentLength) + (normY * normalOffset)
    readonly property real cp2X: endPt.x - (dirX * tangentLength) + (normX * normalOffset * 0.6) + (targetId === selectedNodeId ? focalBiasX * emergenceKick : 0.0)
    readonly property real cp2Y: endPt.y - (dirY * tangentLength) + (normY * normalOffset * 0.6)

    // =========================================================================
    // Bioluminescent Respiration Wave (Continuous Calm Biological Breathing)
    // =========================================================================
    property real pulsePhase: 0.0

    SequentialAnimation on pulsePhase {
        loops: Animation.Infinite
        running: true  // Keep breathing continuously across all view modes

        PauseAnimation { duration: ((rootTendril.sourceId * 137 + rootTendril.targetId * 79) % 3500) + 500 }
        NumberAnimation { to: 1.0; duration: 2400; easing.type: Easing.InOutSine }
        PauseAnimation { duration: 400 }
        NumberAnimation { to: 0.0; duration: 3200; easing.type: Easing.InOutSine }
        PauseAnimation { duration: 1800 }
    }

    // =========================================================================
    // Dynamic Opacity & Attenuation
    // =========================================================================
    // Massively increased to span the new 1500px+ donut hole
    readonly property real ambientSpanLimit: 2800.0 

    readonly property real proximityFactor: {
        if (!isVoidMode) {
            return (spanDist >= 2800.0) ? 0.25 : (1.0 - ((spanDist - 400.0) / 2400.0) * 0.75)
        }
        if (spanDist >= ambientSpanLimit) return 0.0
        // Gives lines a solid burn for the first 800px before slowly fading out
        if (spanDist <= 800.0) return 1.0 
        return 1.0 - ((spanDist - 800.0) / (ambientSpanLimit - 800.0))
    }

    readonly property real avgDepth: {
        var sDepth = (sourceNode && sourceNode.depthZ !== undefined) ? sourceNode.depthZ : 0.5
        var tDepth = (targetNode && targetNode.depthZ !== undefined) ? targetNode.depthZ : 0.5
        return (sDepth + tDepth) / 2.0
    }

    readonly property real depthAttenuation: 1.0 - (avgDepth * 0.40)

    readonly property real ambientOpacity: {
        if (!isVoidMode || proximityFactor <= 0.001 || shouldCullIntra) return 0.0

        var base = 0.0
        if (edgeType === "explicit") {
            // Drops completely to 0.0 when breathing out
            base = Math.pow(pulsePhase, 1.4) * 0.42 * proximityFactor * Math.max(0.4, weight)
        } else if (edgeType === "temporal") {
            base = Math.pow(pulsePhase, 1.2) * 0.55 * proximityFactor * Math.max(0.5, weight)
        } else {
            base = Math.pow(pulsePhase, 1.6) * 0.35 * proximityFactor * Math.max(0.4, weight)
        }
        return base * depthAttenuation
    }

    readonly property real targetOpacity: {
        if (isHoverBloomed) {
            return 1.0
        } else if (isFirstDegree) {
            var scaledWeight = Math.max(0.0, Math.min(1.0, rootTendril.weight))
            return Math.max(0.18, 0.20 + 0.78 * Math.pow(scaledWeight, 1.4))
        } else if (isSecondDegree) {
            return 0.18 * Math.max(0.3, rootTendril.weight)
        } else if (isVoidMode) {
            return ambientOpacity
        } else {
            return 0.03
        }
    }

    opacity: targetOpacity
    visible: sourceNode !== null && targetNode !== null && opacity > 0.005

    Behavior on opacity {
        NumberAnimation { duration: 240; easing.type: Easing.OutCubic }
    }

    readonly property color filamentColor: {
        if (isHoverBloomed) {
            if (edgeType === "temporal") return "#fef08a"
            if (edgeType === "explicit") return "#7dd3fc"
            return "#e9d5ff"
        }
        if (edgeType === "explicit") return "#38bdf8"
        if (edgeType === "temporal") return "#fde047"
        return "#c084fc"
    }

    // =========================================================================
    // Core Synaptic Filament
    // =========================================================================
    Shape {
        anchors.fill: parent
        asynchronous: true
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: rootTendril.filamentColor
            strokeWidth: {
                if (rootTendril.isHoverBloomed) return 1.8
                if (rootTendril.isFirstDegree) return Math.max(0.65, 0.50 + 1.15 * rootTendril.weight)
                return rootTendril.edgeType === "temporal" ? 1.0 : 0.8
            }
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap

            startX: rootTendril.startPt.x
            startY: rootTendril.startPt.y

            PathCubic {
                x: rootTendril.endPt.x
                y: rootTendril.endPt.y
                control1X: rootTendril.cp1X
                control1Y: rootTendril.cp1Y
                control2X: rootTendril.cp2X
                control2Y: rootTendril.cp2Y
            }
        }
    }

    // Outer Aura Bloom
    Shape {
        anchors.fill: parent
        asynchronous: true
        preferredRendererType: Shape.CurveRenderer
        visible: rootTendril.isHoverBloomed || (rootTendril.isFirstDegree && rootTendril.weight >= 0.55) || (rootTendril.isVoidMode && rootTendril.pulsePhase > 0.80)
        opacity: rootTendril.isHoverBloomed ? 0.65 : (rootTendril.isVoidMode ? 0.18 : Math.max(0.15, rootTendril.weight * 0.40))

        ShapePath {
            strokeColor: rootTendril.filamentColor
            strokeWidth: Math.max(2.2, rootTendril.weight * 3.4)
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap

            startX: rootTendril.startPt.x
            startY: rootTendril.startPt.y

            PathCubic {
                x: rootTendril.endPt.x
                y: rootTendril.endPt.y
                control1X: rootTendril.cp1X
                control1Y: rootTendril.cp1Y
                control2X: rootTendril.cp2X
                control2Y: rootTendril.cp2Y
            }
        }
    }

    // =========================================================================
    // Diffuse Bioluminescent Synaptic Port Component
    // =========================================================================
    component SynapticGlowPort: Item {
        id: portRoot
        property color glowColor: "#38bdf8"
        property bool isFocalLens: false
        property real edgeWeight: 1.0

        readonly property real glowSize: isFocalLens ? (14 + 10 * edgeWeight) : (8 + 6 * edgeWeight)
        width: glowSize
        height: glowSize
        opacity: Math.max(0.20, Math.min(1.0, edgeWeight))

        Rectangle {
            anchors.centerIn: parent
            width: parent.width
            height: parent.height
            radius: width / 2
            color: portRoot.glowColor
            opacity: portRoot.isFocalLens ? (0.10 + 0.15 * portRoot.edgeWeight) : 0.12
        }

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.55
            height: parent.height * 0.55
            radius: width / 2
            color: portRoot.glowColor
            opacity: portRoot.isFocalLens ? (0.25 + 0.35 * portRoot.edgeWeight) : 0.28
        }

        Rectangle {
            visible: portRoot.edgeWeight >= 0.35
            anchors.centerIn: parent
            width: portRoot.isFocalLens ? (2.5 + 2.0 * portRoot.edgeWeight) : 2.5
            height: width
            radius: width / 2
            color: "#ffffff"
            opacity: 0.85
        }
    }

    // Source Synaptic Port
    SynapticGlowPort {
        visible: (rootTendril.isFirstDegree || rootTendril.isHoverBloomed) && rootTendril.weight >= 0.25
        x: rootTendril.startPt.x - width / 2
        y: rootTendril.startPt.y - height / 2
        glowColor: rootTendril.filamentColor
        isFocalLens: rootTendril.sourceId === rootTendril.selectedNodeId
        edgeWeight: rootTendril.weight
        z: 9500
    }

    // Target Synaptic Port
    SynapticGlowPort {
        visible: (rootTendril.isFirstDegree || rootTendril.isHoverBloomed) && rootTendril.weight >= 0.25
        x: rootTendril.endPt.x - width / 2
        y: rootTendril.endPt.y - height / 2
        glowColor: rootTendril.filamentColor
        isFocalLens: rootTendril.targetId === rootTendril.selectedNodeId
        edgeWeight: rootTendril.weight
        z: 9500
    }
}