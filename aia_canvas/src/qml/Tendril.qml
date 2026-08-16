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

    // Cull intra-cluster tendrils during macro zoom (<= 48%) unless hovered or focused
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
            var clampedJitter = Math.max(-halfW + 12, Math.min(halfH - 12, jitter))
            return Qt.point(cx + (dx / Math.abs(dy)) * halfH + clampedJitter, cy + (signY * halfH))
        }
    }

    readonly property point startPt: (sourceNode && targetNode) ?
        calculateSynapticPoint(sCx, sCy, sW, sH, tCx, tCy, jitterSeed) : Qt.point(0, 0)

    readonly property point endPt: (sourceNode && targetNode) ?
        calculateSynapticPoint(tCx, tCy, tW, tH, sCx, sCy, -jitterSeed) : Qt.point(0, 0)

    readonly property real deltaX: endPt.x - startPt.x
    readonly property real deltaY: endPt.y - startPt.y
    readonly property real spanDist: Math.sqrt(deltaX * deltaX + deltaY * deltaY)

    readonly property real gravitationalSlack: (spanDist < 140) ? 0 :
        Math.max(0, Math.sin(Math.min(1.0, (spanDist - 140) / 600) * Math.PI) * 14.0)

    readonly property real cpOffset: Math.min(Math.abs(deltaX) * 0.22, 45.0)

    readonly property real cp1X: startPt.x + (deltaX >= 0 ? cpOffset : -cpOffset)
    readonly property real cp1Y: startPt.y + gravitationalSlack
    readonly property real cp2X: endPt.x - (deltaX >= 0 ? cpOffset : -cpOffset)
    readonly property real cp2Y: endPt.y + gravitationalSlack

    // =========================================================================
    // Deep Bioluminescent Respiration
    // =========================================================================
    property real pulsePhase: 0.0

    SequentialAnimation on pulsePhase {
        loops: Animation.Infinite
        running: rootTendril.isVoidMode

        PauseAnimation { duration: ((rootTendril.sourceId * 149 + rootTendril.targetId * 97) % 5000) + 1000 }
        NumberAnimation { to: 1.0; duration: 4500; easing.type: Easing.InOutSine }
        PauseAnimation { duration: 800 }
        NumberAnimation { to: 0.0; duration: 5500; easing.type: Easing.InOutSine }
        PauseAnimation { duration: 2500 }
    }

    // =========================================================================
    // Strict Local Neighborhood Horizon (Max 550px)
    // =========================================================================
    readonly property real ambientSpanLimit: 550.0

    readonly property real proximityFactor: {
        if (!isVoidMode) {
            return (spanDist >= 2200.0) ? 0.25 : (1.0 - ((spanDist - 400.0) / 1800.0) * 0.75)
        }
        // Hard cutoff: Any ambient line longer than 550px is instantly culled
        if (spanDist >= ambientSpanLimit) return 0.0
        if (spanDist <= 240.0) return 1.0
        return 1.0 - ((spanDist - 240.0) / (ambientSpanLimit - 240.0))
    }

    readonly property real avgDepth: {
        var sDepth = (sourceNode && sourceNode.depthZ !== undefined) ? sourceNode.depthZ : 0.5
        var tDepth = (targetNode && targetNode.depthZ !== undefined) ? targetNode.depthZ : 0.5
        return (sDepth + tDepth) / 2.0
    }

    readonly property real depthAttenuation: 1.0 - (avgDepth * 0.50)

    readonly property real ambientOpacity: {
        if (!isVoidMode || proximityFactor <= 0.001 || shouldCullIntra) return 0.0

        var base = 0.0
        if (edgeType === "explicit") {
            base = (0.10 + 0.15 * pulsePhase) * proximityFactor * Math.max(0.5, weight)
        } else if (edgeType === "temporal") {
            base = (pulsePhase * 0.45 * Math.max(0.5, weight)) * proximityFactor
        } else {
            base = (0.05 + 0.20 * pulsePhase) * proximityFactor * Math.max(0.4, weight)
        }
        return base * depthAttenuation
    }

    readonly property real targetOpacity: {
        if (isHoverBloomed) {
            return 0.95
        } else if (isFirstDegree) {
            return Math.max(0.85, weight)
        } else if (isSecondDegree) {
            return 0.20
        } else if (isVoidMode) {
            return ambientOpacity
        } else {
            return 0.04
        }
    }

    opacity: targetOpacity
    visible: sourceNode !== null && targetNode !== null && opacity > 0.005

    Behavior on opacity {
        NumberAnimation { duration: 280; easing.type: Easing.OutCubic }
    }

    readonly property color filamentColor: {
        if (isHoverBloomed) {
            if (edgeType === "temporal") return "#fde047"
            if (edgeType === "explicit") return "#67e8f9"
            return "#c084fc"
        }
        if (edgeType === "explicit") return "#38bdf8"
        if (edgeType === "temporal") return "#fbbf24"
        return "#a78bfa"
    }

    // Core Synaptic Filament
    Shape {
        anchors.fill: parent
        asynchronous: true
        layer.enabled: true
        layer.smooth: true

        ShapePath {
            strokeColor: rootTendril.filamentColor
            strokeWidth: (rootTendril.isFirstDegree || rootTendril.isHoverBloomed) ? Math.max(1.8, rootTendril.weight * 2.2) : (rootTendril.edgeType === "temporal" ? 1.3 : 1.0)
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

    // Outer Glow Halo
    Shape {
        anchors.fill: parent
        visible: rootTendril.isFirstDegree || rootTendril.isHoverBloomed || (rootTendril.isVoidMode && rootTendril.pulsePhase > 0.8)
        opacity: rootTendril.isHoverBloomed ? 0.55 : (rootTendril.isVoidMode ? 0.15 : Math.max(0.18, rootTendril.weight * 0.35))

        ShapePath {
            strokeColor: rootTendril.filamentColor
            strokeWidth: Math.max(3.0, rootTendril.weight * 4.2)
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
}