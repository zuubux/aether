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

    visible: sourceNode !== null && targetNode !== null

    // Relationship Tiers
    readonly property bool isFirstDegree: selectedNodeId > 0 && (sourceId === selectedNodeId || targetId === selectedNodeId)
    readonly property bool isHoverBloomed: hoveredNodeId > 0 && (sourceId === hoveredNodeId || targetId === hoveredNodeId)
    readonly property bool isSecondDegree: {
        if (isFirstDegree || selectedNodeId <= 0) return false
        var sFocus = sourceNode ? sourceNode.focusWeight : 0
        var tFocus = targetNode ? targetNode.focusWeight : 0
        return (sFocus > 0.55 && tFocus > 0.35) || (tFocus > 0.55 && sFocus > 0.35)
    }
    readonly property bool isVoidMode: selectedNodeId <= 0

    // Progressive Disclosure Opacity
    readonly property real targetOpacity: {
        if (isHoverBloomed) {
            return 0.88                                 // Hover-Peek Bloom
        } else if (isFirstDegree) {
            return Math.max(0.80, weight)               // 1st-Degree Active Beam
        } else if (isSecondDegree) {
            return 0.18                                 // 2nd-Degree Echo
        } else if (isVoidMode) {
            return Math.max(0.16, weight * 0.28)        // Luminous Ambient Network
        } else {
            return 0.04                                 // Background Whisper
        }
    }

    opacity: targetOpacity
    Behavior on opacity {
        NumberAnimation { duration: 240; easing.type: Easing.OutCubic }
    }

    readonly property color filamentColor: {
        if (isHoverBloomed) return "#67e8f9"
        if (edgeType === "explicit") return "#38bdf8"
        if (edgeType === "temporal") return "#fbbf24"
        return "#a78bfa"
    }

    // Dynamic Endpoints & Geometry
    readonly property real sCx: sourceNode ? (sourceNode.cardCenterX !== undefined ? sourceNode.cardCenterX : sourceNode.x) : 0
    readonly property real sCy: sourceNode ? (sourceNode.cardCenterY !== undefined ? sourceNode.cardCenterY : sourceNode.y) : 0
    readonly property real sW: sourceNode ? (sourceNode.cardWidth !== undefined ? sourceNode.cardWidth : 280) : 280
    readonly property real sH: sourceNode ? (sourceNode.cardHeight !== undefined ? sourceNode.cardHeight : 120) : 120

    readonly property real tCx: targetNode ? (targetNode.cardCenterX !== undefined ? targetNode.cardCenterX : targetNode.x) : 0
    readonly property real tCy: targetNode ? (targetNode.cardCenterY !== undefined ? targetNode.cardCenterY : targetNode.y) : 0
    readonly property real tW: targetNode ? (targetNode.cardWidth !== undefined ? targetNode.cardWidth : 280) : 280
    readonly property real tH: targetNode ? (targetNode.cardHeight !== undefined ? targetNode.cardHeight : 120) : 120

    readonly property real jitterSeed: ((sourceId * 37 + targetId * 19) % 20) - 10

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
            var clampedJitter = Math.max(-halfW + 12, Math.min(halfW - 12, jitter))
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

    readonly property real gravitationalSlack: (spanDist < 120) ? 0 :
        Math.max(0, Math.sin(Math.min(1.0, (spanDist - 120) / 450) * Math.PI) * 35.0)

    readonly property real cpOffset: Math.min(Math.abs(deltaX) * 0.4, 120)

    readonly property real cp1X: startPt.x + (deltaX >= 0 ? cpOffset : -cpOffset)
    readonly property real cp1Y: startPt.y + gravitationalSlack
    readonly property real cp2X: endPt.x - (deltaX >= 0 ? cpOffset : -cpOffset)
    readonly property real cp2Y: endPt.y + gravitationalSlack

    // Core Filament
    Shape {
        anchors.fill: parent
        asynchronous: true
        layer.enabled: true
        layer.smooth: true

        ShapePath {
            strokeColor: rootTendril.filamentColor
            strokeWidth: (rootTendril.isFirstDegree || rootTendril.isHoverBloomed) ? Math.max(1.3, rootTendril.weight * 1.8) : 0.85
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

    // Outer Glow Halo (Only for active primary beam or hovered bloom)
    Shape {
        anchors.fill: parent
        visible: rootTendril.isFirstDegree || rootTendril.isHoverBloomed
        opacity: rootTendril.isHoverBloomed ? 0.45 : Math.max(0.15, rootTendril.weight * 0.35)

        ShapePath {
            strokeColor: rootTendril.filamentColor
            strokeWidth: Math.max(2.5, rootTendril.weight * 4.5)
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