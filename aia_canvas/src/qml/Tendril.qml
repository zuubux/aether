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
    readonly property bool isFirstDegree: {
        if (selectedNodeId <= 0 || (sourceId !== selectedNodeId && targetId !== selectedNodeId)) return false
        var otherNode = (sourceId === selectedNodeId) ? targetNode : sourceNode
        var otherFocus = otherNode ? (otherNode.focusWeight !== undefined ? otherNode.focusWeight : (otherNode.nodeModel ? otherNode.nodeModel.focus : 0)) : 0
        return otherFocus >= 0.60
    }
    readonly property bool isHoverBloomed: hoveredNodeId > 0 && (sourceId === hoveredNodeId || targetId === hoveredNodeId)
    readonly property bool isSecondDegree: {
        if (selectedNodeId <= 0) return false
        if (sourceId === selectedNodeId || targetId === selectedNodeId) {
            var otherNode = (sourceId === selectedNodeId) ? targetNode : sourceNode
            var otherFocus = otherNode ? (otherNode.focusWeight !== undefined ? otherNode.focusWeight : (otherNode.nodeModel ? otherNode.nodeModel.focus : 0)) : 0
            return otherFocus < 0.60 && otherFocus > 0.30
        }
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
    readonly property bool shouldCullIntra: isIntraCluster && isVoidMode && !isHoverBloomed && (currentAperture <= 0.40)

    // Dynamic Endpoints & Geometry
    readonly property real vpX: {
        if (typeof canvasBridge !== "undefined" && canvasBridge.selectedNodeId > 0) {
            return (parent ? (parent.width - canvasBridge.wingWidth) / 2.0 : 1280)
        }
        return parent ? parent.width / 2 : 1280
    }
    readonly property real vpY: parent ? parent.height * 0.20 : 280

    function getProjectedCentroid(clusterId) {
        if (typeof canvasBridge === "undefined" || clusterId < 0) return null;
        var halos = canvasBridge.clusterHalos;
        if (!halos) return null;
        for (var i = 0; i < halos.length; i++) {
            if (halos[i].id === "component_" + clusterId) {
                var cx = halos[i].centerX;
                var cy = halos[i].centerY;
                var hw = halos[i].width;
                var hh = halos[i].height;
                
                var depthZ = Math.max(0.0, Math.min(1.0, 1.0 - (cy / (parent ? parent.height : 1440))));
                var pScale = 1.0 / (1.0 + depthZ * 1.25);
                var xSpreadFactor = 0.85 + 0.15 * pScale;
                
                var projX = vpX + (cx - vpX) * xSpreadFactor;
                var projY = vpY + (cy - vpY) * pScale;
                
                return { x: projX, y: projY, w: Math.max(56.0, hw * pScale), h: Math.max(56.0, hh * pScale) };
            }
        }
        return null;
    }

    readonly property real centroidBlend: Math.max(0.0, Math.min(1.0, (0.25 - currentAperture) / 0.25))

    readonly property var sClusterPt: centroidBlend > 0 ? getProjectedCentroid(sourceClusterId) : null
    readonly property var tClusterPt: centroidBlend > 0 ? getProjectedCentroid(targetClusterId) : null

    readonly property real rawSCx: sourceNode ? (sourceNode.cardCenterX !== undefined ? sourceNode.cardCenterX : (sourceNode.nodeModel ? sourceNode.nodeModel.x : sourceNode.x)) : 0
    readonly property real rawSCy: sourceNode ? (sourceNode.cardCenterY !== undefined ? sourceNode.cardCenterY : (sourceNode.nodeModel ? sourceNode.nodeModel.y : sourceNode.y)) : 0
    readonly property real rawSW: sourceNode ? (sourceNode.cardWidth !== undefined ? sourceNode.cardWidth : 280) : 280
    readonly property real rawSH: sourceNode ? (sourceNode.cardHeight !== undefined ? sourceNode.cardHeight : 120) : 120

    readonly property bool sourceIsWing: sourceNode ? (selectedNodeId > 0 && sourceId !== selectedNodeId && (sourceNode.focusWeight > 0.35 || (sourceNode.nodeModel && sourceNode.nodeModel.focus > 0.35))) : false
    readonly property bool targetIsWing: targetNode ? (selectedNodeId > 0 && targetId !== selectedNodeId && (targetNode.focusWeight > 0.35 || (targetNode.nodeModel && targetNode.nodeModel.focus > 0.35))) : false

    readonly property real sCx: (sClusterPt && !sourceIsSelected && !sourceIsWing) ? (rawSCx * (1 - centroidBlend) + sClusterPt.x * centroidBlend) : rawSCx
    readonly property real sCy: (sClusterPt && !sourceIsSelected && !sourceIsWing) ? (rawSCy * (1 - centroidBlend) + sClusterPt.y * centroidBlend) : rawSCy
    readonly property real sW: (sClusterPt && !sourceIsSelected && !sourceIsWing) ? (rawSW * (1 - centroidBlend) + sClusterPt.w * centroidBlend) : rawSW
    readonly property real sH: (sClusterPt && !sourceIsSelected && !sourceIsWing) ? (rawSH * (1 - centroidBlend) + sClusterPt.h * centroidBlend) : rawSH

    readonly property real rawTCx: targetNode ? (targetNode.cardCenterX !== undefined ? targetNode.cardCenterX : (targetNode.nodeModel ? targetNode.nodeModel.x : targetNode.x)) : 0
    readonly property real rawTCy: targetNode ? (targetNode.cardCenterY !== undefined ? targetNode.cardCenterY : (targetNode.nodeModel ? targetNode.nodeModel.y : targetNode.y)) : 0
    readonly property real rawTW: targetNode ? (targetNode.cardWidth !== undefined ? targetNode.cardWidth : 280) : 280
    readonly property real rawTH: targetNode ? (targetNode.cardHeight !== undefined ? targetNode.cardHeight : 120) : 120

    readonly property real tCx: (tClusterPt && targetId !== selectedNodeId && !targetIsWing) ? (rawTCx * (1 - centroidBlend) + tClusterPt.x * centroidBlend) : rawTCx
    readonly property real tCy: (tClusterPt && targetId !== selectedNodeId && !targetIsWing) ? (rawTCy * (1 - centroidBlend) + tClusterPt.y * centroidBlend) : rawTCy
    readonly property real tW: (tClusterPt && targetId !== selectedNodeId && !targetIsWing) ? (rawTW * (1 - centroidBlend) + tClusterPt.w * centroidBlend) : rawTW
    readonly property real tH: (tClusterPt && targetId !== selectedNodeId && !targetIsWing) ? (rawTH * (1 - centroidBlend) + tClusterPt.h * centroidBlend) : rawTH

    readonly property real jitterSeed: ((sourceId * 37 + targetId * 19) % 16) - 8

    function calculateSynapticPoint(cx, cy, w, h, targetX, targetY, jitter) {
        var dx = targetX - cx
        var dy = targetY - cy
        if (dx === 0 && dy === 0) return Qt.point(cx, cy)

        if (w > h) {
            var r = h / 2
            var L = (w / 2) - r

            if (dy !== 0) {
                var t_flat = (dy > 0 ? r : -r) / dy
                if (t_flat > 0) {
                    var x_flat = cx + t_flat * dx
                    if (x_flat >= cx - L && x_flat <= cx + L) {
                        var clampedJitter = Math.max(-L + 12, Math.min(L - 12, jitter))
                        return Qt.point(x_flat + clampedJitter, cy + (dy > 0 ? r : -r))
                    }
                }
            }

            var A = dx * dx + dy * dy
            var signX = dx > 0 ? 1 : -1
            var B = -2 * L * dx * signX
            var C = L * L - r * r

            var disc = B * B - 4 * A * C
            if (disc >= 0) {
                var t = (-B + Math.sqrt(disc)) / (2 * A)
                if (t > 0) {
                    var px = cx + t * dx
                    var py = cy + t * dy
                    return Qt.point(px, py)
                }
            }
        }

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

    readonly property bool sourceIsBead: sourceNode ? (sourceNode.isMacroBead || sourceNode.isHoverBloomed) : false
    readonly property bool targetIsBead: targetNode ? (targetNode.isMacroBead || targetNode.isHoverBloomed) : false

    readonly property point startPt: (sourceNode && targetNode) ?
        (sourceIsBead ? Qt.point(sCx, sCy) : calculateSynapticPoint(sCx, sCy, sW, sH, tCx, tCy, jitterSeed)) : Qt.point(0, 0)

    readonly property point endPt: (sourceNode && targetNode) ?
        (targetIsBead ? Qt.point(tCx, tCy) : calculateSynapticPoint(tCx, tCy, tW, tH, sCx, sCy, -jitterSeed)) : Qt.point(0, 0)

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
        running: true 

        // Massive random delay (2 to 14 seconds) so connections fire sparsely and randomly
        PauseAnimation { duration: ((rootTendril.sourceId * 313 + rootTendril.targetId * 107) % 12000) + 2000 }
        
        // Deep, slow biological inhale
        NumberAnimation { to: 1.0; duration: 4500; easing.type: Easing.InOutSine }
        PauseAnimation { duration: 800 }
        
        // Long, soft exhale
        NumberAnimation { to: 0.0; duration: 5500; easing.type: Easing.InOutSine }
        
        // Long baseline rest before the next possible breath
        PauseAnimation { duration: 4000 }
    }

    // =========================================================================
    // Dynamic Opacity & Attenuation
    // =========================================================================
    // Reduced by ~40% so lines don't stretch infinitely across the cosmos
    readonly property real ambientSpanLimit: 1600.0 

    readonly property real proximityFactor: {
        if (!isVoidMode) {
            return (spanDist >= ambientSpanLimit) ? 0.25 : (1.0 - ((spanDist - 400.0) / (ambientSpanLimit - 400.0)) * 0.75)
        }
        if (spanDist >= ambientSpanLimit) return 0.0
        
        // Gives lines a solid burn for the first 500px before smoothly fading out
        if (spanDist <= 500.0) return 1.0 
        return 1.0 - ((spanDist - 500.0) / (ambientSpanLimit - 500.0))
    }

    readonly property real avgDepth: {
        var sDepth = (sourceNode && sourceNode.depthZ !== undefined) ? sourceNode.depthZ : 0.5
        var tDepth = (targetNode && targetNode.depthZ !== undefined) ? targetNode.depthZ : 0.5
        return (sDepth + tDepth) / 2.0
    }

    readonly property real depthAttenuation: 1.0 - (avgDepth * 0.40)

    readonly property real ambientOpacity: {
        if (proximityFactor <= 0.001 || shouldCullIntra) return 0.0

        // High-exponent power curve so edges stay dark for ~80% of their cycle, breathing up briefly to peak opacity of ~0.2
        var spark = Math.pow(Math.max(0.0, Math.sin(pulsePhase * Math.PI * 0.5)), 4.0)
        var peak = 0.20 * proximityFactor * depthAttenuation * Math.max(0.4, weight)
        return spark * peak
    }

    readonly property bool isConnectedToSelected: selectedNodeId > 0 && (sourceId === selectedNodeId || targetId === selectedNodeId)
    readonly property bool isConnectedToHovered: hoveredNodeId > 0 && (sourceId === hoveredNodeId || targetId === hoveredNodeId)

    readonly property real targetOpacity: {
        if (isConnectedToSelected) {
            if (isFirstDegree) {
                return 1.0
            } else {
                return 0.6
            }
        } else if (isConnectedToHovered) {
            return 0.6
        } else {
            return ambientOpacity
        }
    }

    readonly property real macroOpacityFade: {
        if (isConnectedToSelected || isConnectedToHovered) return 1.0
        if (currentAperture >= 0.35) return 1.0
        var isTrunk = !isIntraCluster && (edgeType === "explicit" || (edgeType === "semantic" && weight >= 0.45))
        if (isTrunk) return 1.0
        return Math.max(0.0, (currentAperture - 0.20) / 0.15)
    }

    opacity: targetOpacity * macroOpacityFade
    visible: sourceNode !== null && targetNode !== null && opacity > 0.005

    Behavior on opacity {
        NumberAnimation { duration: 240; easing.type: Easing.OutCubic }
    }

    readonly property color filamentColor: {
        if (isHoverBloomed) {
            if (edgeType === "temporal") return "#fef08a"
            if (edgeType === "explicit") return "#7dd3fc"
            if (edgeType === "semantic") return "#c084fc"
            return "#e9d5ff"
        }
        if (edgeType === "explicit") return "#38bdf8"
        if (edgeType === "temporal") return "#fde047"
        if (edgeType === "semantic") return "#a855f7"
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
                if (rootTendril.isFirstDegree) {
                    var w = rootTendril.edgeType === "semantic" ? Math.max(0.6, rootTendril.weight) : rootTendril.weight
                    return Math.max(0.65, 0.50 + 1.15 * w)
                }
                if (rootTendril.edgeType === "explicit" || rootTendril.edgeType === "semantic") return 0.8
                return 1.0 // temporal
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
        visible: rootTendril.isHoverBloomed || (rootTendril.isFirstDegree && (rootTendril.edgeType === "semantic" || rootTendril.weight >= 0.55)) || (rootTendril.isVoidMode && rootTendril.pulsePhase > 0.80)
        opacity: rootTendril.isHoverBloomed ? 0.65 : (rootTendril.isVoidMode ? 0.18 : Math.max(0.15, (rootTendril.edgeType === "semantic" ? Math.max(0.6, rootTendril.weight) : rootTendril.weight) * 0.40))

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

   // Helper properties to handle edge directionality gracefully
    readonly property bool sourceIsSelected: sourceId === selectedNodeId
    readonly property point lensPoint: sourceIsSelected ? startPt : endPt
    readonly property point outerPoint: sourceIsSelected ? endPt : startPt

    // Lens Frame Synaptic Port (Fires on the lens for Tier 1, Tier 2, and Hover)
    SynapticGlowPort {
        visible: (isFirstDegree || isSecondDegree || isHoverBloomed) && (sourceId === selectedNodeId || targetId === selectedNodeId) && (edgeType === "semantic" || weight >= 0.25)
        x: lensPoint.x - width / 2
        y: lensPoint.y - height / 2
        glowColor: edgeType === "semantic" ? "#a78bfa" : filamentColor
        isFocalLens: true
        edgeWeight: edgeType === "semantic" ? Math.max(0.5, weight) : weight
        z: 9500
    }

    // Outer Node Synaptic Port (ONLY fires on the outer node for Tier 1 and Hover)
    SynapticGlowPort {
        visible: (isFirstDegree || isHoverBloomed) && (sourceId === selectedNodeId || targetId === selectedNodeId) && (edgeType === "semantic" || weight >= 0.25)
        x: outerPoint.x - width / 2
        y: outerPoint.y - height / 2
        glowColor: edgeType === "semantic" ? "#a78bfa" : filamentColor
        isFocalLens: false
        edgeWeight: edgeType === "semantic" ? Math.max(0.5, weight) : weight
        z: 9500
    }
}