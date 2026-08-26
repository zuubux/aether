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
    readonly property real portRatio: (typeof modelData !== "undefined" && modelData && modelData.flankPortRatio !== undefined) ? modelData.flankPortRatio : 0.5
    property real flankPortRatio: modelData && modelData.flankPortRatio !== undefined ? modelData.flankPortRatio : 0
    property real portSpacing: 6.0

    property real driftTime: 0.0
    NumberAnimation on driftTime {
        from: 0; to: 6.28318
        duration: 12000
        loops: Animation.Infinite
        running: true
    }

    readonly property real organicPortRatio: {
        if (flankPortRatio <= 0) return 0.5;
        var phase = (sourceId * 1.618 + driftTime) % 6.28318
        return flankPortRatio + Math.sin(phase) * 0.03
    }

    readonly property bool isSibling: modelData !== undefined && modelData.isSiblingEdge !== undefined ? modelData.isSiblingEdge : false
    readonly property bool isHovered: hoveredNodeId > 0 && (sourceId === hoveredNodeId || targetId === hoveredNodeId)

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

    // Reactive properties that automatically recompute every frame as the node floats
    readonly property real sourceCurrentX: sourceNode ? sourceNode.x : 0
    readonly property real sourceCurrentY: sourceNode ? sourceNode.y : 0
    readonly property real sourceCurrentW: sourceNode ? (sourceNode.width > 0 ? sourceNode.width : sourceNode.implicitWidth) * sourceNode.scale : 280
    readonly property real sourceCurrentH: sourceNode ? (sourceNode.height > 0 ? sourceNode.height : sourceNode.implicitHeight) * sourceNode.scale : 120

    readonly property real targetCurrentX: targetNode ? targetNode.x : 0
    readonly property real targetCurrentY: targetNode ? targetNode.y : 0
    readonly property real targetCurrentW: targetNode ? (targetNode.width > 0 ? targetNode.width : targetNode.implicitWidth) * targetNode.scale : 280
    readonly property real targetCurrentH: targetNode ? (targetNode.height > 0 ? targetNode.height : targetNode.implicitHeight) * targetNode.scale : 120

    readonly property real rawSCx: sourceCurrentX + sourceCurrentW * 0.5
    readonly property real rawSCy: sourceCurrentY + sourceCurrentH * 0.5
    readonly property real rawSW: sourceCurrentW
    readonly property real rawSH: sourceCurrentH

    readonly property bool sourceIsWing: sourceNode ? (selectedNodeId > 0 && sourceId !== selectedNodeId && (sourceNode.focusWeight > 0.35 || (sourceNode.nodeModel && sourceNode.nodeModel.focus > 0.35))) : false
    readonly property bool targetIsWing: targetNode ? (selectedNodeId > 0 && targetId !== selectedNodeId && (targetNode.focusWeight > 0.35 || (targetNode.nodeModel && targetNode.nodeModel.focus > 0.35))) : false

    readonly property real sCx: (sClusterPt && !sourceIsSelected && !sourceIsWing) ? (rawSCx * (1 - centroidBlend) + sClusterPt.x * centroidBlend) : rawSCx
    readonly property real sCy: (sClusterPt && !sourceIsSelected && !sourceIsWing) ? (rawSCy * (1 - centroidBlend) + sClusterPt.y * centroidBlend) : rawSCy
    readonly property real sW: (sClusterPt && !sourceIsSelected && !sourceIsWing) ? (rawSW * (1 - centroidBlend) + sClusterPt.w * centroidBlend) : rawSW
    readonly property real sH: (sClusterPt && !sourceIsSelected && !sourceIsWing) ? (rawSH * (1 - centroidBlend) + sClusterPt.h * centroidBlend) : rawSH

    readonly property real rawTCx: targetCurrentX + targetCurrentW * 0.5
    readonly property real rawTCy: targetCurrentY + targetCurrentH * 0.5
    readonly property real rawTW: targetCurrentW
    readonly property real rawTH: targetCurrentH

    readonly property real tCx: (tClusterPt && targetId !== selectedNodeId && !targetIsWing) ? (rawTCx * (1 - centroidBlend) + tClusterPt.x * centroidBlend) : rawTCx
    readonly property real tCy: (tClusterPt && targetId !== selectedNodeId && !targetIsWing) ? (rawTCy * (1 - centroidBlend) + tClusterPt.y * centroidBlend) : rawTCy
    readonly property real tW: (tClusterPt && targetId !== selectedNodeId && !targetIsWing) ? (rawTW * (1 - centroidBlend) + tClusterPt.w * centroidBlend) : rawTW
    readonly property real tH: (tClusterPt && targetId !== selectedNodeId && !targetIsWing) ? (rawTH * (1 - centroidBlend) + tClusterPt.h * centroidBlend) : rawTH

    readonly property real jitterSeed: ((sourceId * 37 + targetId * 19) % 16) - 8

    readonly property bool sourceIsBead: sourceNode ? !!(sourceNode.isMacroBead || sourceNode.isHoverBloomed) : false
    readonly property bool targetIsBead: targetNode ? !!(targetNode.isMacroBead || targetNode.isHoverBloomed) : false

    function debugStartPt() {
        if (!sourceNode || !targetNode) return Qt.point(0, 0);
        if (sourceIsBead) return Qt.point(sCx, sCy);
        
        var isLeft = targetNode.x < sourceNode.x;
        if (sourceId === selectedNodeId && typeof sourceNode.getFlankSocket === "function") {
            return sourceNode.getFlankSocket(isLeft, organicPortRatio);
        }
        var dock = isLeft ? sourceNode.leftDock : sourceNode.rightDock;
        if (!dock) return Qt.point(sCx, sCy);
        return dock;
    }

    readonly property point rawStartPt: debugStartPt()

    function debugEndPt() {
        if (!sourceNode || !targetNode) return Qt.point(0, 0);
        if (targetIsBead) return Qt.point(tCx, tCy);
        
        var isLeft = sourceNode.x < targetNode.x;
        if (targetId === selectedNodeId && typeof targetNode.getFlankSocket === "function") {
            return targetNode.getFlankSocket(isLeft, organicPortRatio);
        }
        var dock = isLeft ? targetNode.leftDock : targetNode.rightDock;
        if (!dock) return Qt.point(tCx, tCy);
        return dock;
    }

    readonly property point rawEndPt: debugEndPt()

    readonly property real dx: rawEndPt.x - rawStartPt.x
    readonly property real dy: rawEndPt.y - rawStartPt.y
    readonly property real len: Math.max(1.0, Math.sqrt(dx * dx + dy * dy))
    readonly property real nx: -dy / len
    readonly property real ny: dx / len

    readonly property point startPt: rawStartPt
    readonly property point endPt: rawEndPt

    readonly property real startX: startPt.x
    readonly property real startY: startPt.y
    readonly property real endX: endPt.x
    readonly property real endY: endPt.y

    // Deterministic edge hash seed (values 0.0 to 1.0)
    readonly property int srcId: (typeof modelData !== "undefined" && modelData && modelData.sourceId !== undefined) ? modelData.sourceId : sourceId
    readonly property int tgtId: (typeof modelData !== "undefined" && modelData && modelData.targetId !== undefined) ? modelData.targetId : targetId
    readonly property int edgeHash: ((srcId * 7919) ^ (tgtId * 104729)) & 0xFFFF
    readonly property real rand1: ((edgeHash % 100) / 100.0) - 0.5        // -0.5 to +0.5
    readonly property real rand2: (((edgeHash >> 4) % 100) / 100.0) - 0.5  // -0.5 to +0.5

    // Organic Radial Arc Slack (proportional to distance, capped gracefully)
    readonly property real spanDist: Math.max(1.0, Math.sqrt(Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2)))

    // Dynamic asymmetric handle flare
    readonly property real maxFlare: Math.min(Math.max(spanDist * 0.22, 18.0), 65.0)
    readonly property real flare1: (rand1 * 2.0 * maxFlare)
    readonly property real flare2: (rand2 * 2.0 * maxFlare)

    // Asymmetric Control Points (CP1 and CP2 explore independent normal offsets)
    readonly property real cp1X: startX + ((endX - startX) * 0.30) + (nx * flare1)
    readonly property real cp1Y: startY + ((endY - startY) * 0.30) + (ny * flare1)
    readonly property real cp2X: startX + ((endX - startX) * 0.70) + (nx * flare2)
    readonly property real cp2Y: startY + ((endY - startY) * 0.70) + (ny * flare2)

    // =========================================================================
    // Bioluminescent Respiration Wave (Continuous Calm Biological Breathing)
    // =========================================================================
    property real pulsePhase: 0.0
    readonly property bool isShortIntra: isIntraCluster && spanDist <= 250.0
    readonly property real zoomPauseMultiplier: isShortIntra ? (1.0 + Math.max(0.0, currentAperture * 4.0)) : 1.0

    SequentialAnimation on pulsePhase {
        loops: Animation.Infinite
        running: true 

        // Massive random delay (6 to 24 seconds) so connections fire sparsely and randomly
        PauseAnimation { duration: (((rootTendril.sourceId * 313 + rootTendril.targetId * 107) % 18000) + 6000) * rootTendril.zoomPauseMultiplier }
        
        // Deep, slow biological inhale
        NumberAnimation { to: 1.0; duration: 8500; easing.type: Easing.InOutSine }
        PauseAnimation { duration: 1500 }
        
        // Long, soft exhale
        NumberAnimation { to: 0.0; duration: 9500; easing.type: Easing.InOutSine }
        
        // Long baseline rest before the next possible breath
        PauseAnimation { duration: 8000 * rootTendril.zoomPauseMultiplier }
    }

    // =========================================================================
    // Dynamic Opacity & Attenuation
    // =========================================================================
    // Reduced by ~40% so lines don't stretch infinitely across the cosmos
    readonly property real ambientSpanLimit: edgeType === "temporal" ? 900.0 : 1600.0 

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
        var basePeak = edgeType === "temporal" ? 0.06 : 0.20
        var peak = basePeak * proximityFactor * depthAttenuation * Math.max(0.4, weight)
        if (isShortIntra) {
            peak *= Math.max(0.2, 1.0 - currentAperture * 0.6)
        }
        return spark * peak
    }

    readonly property bool isConnectedToSelected: selectedNodeId > 0 && (sourceId === selectedNodeId || targetId === selectedNodeId)
    readonly property bool isConnectedToHovered: hoveredNodeId > 0 && (sourceId === hoveredNodeId || targetId === hoveredNodeId)

    readonly property real targetOpacity: {
        if (isHoverBloomed) return 1.0
        if (isSibling) return 0.22 // Subdued secondary background line
        if (isConnectedToSelected) {
            if (isFirstDegree) {
                return edgeType === "temporal" ? 0.45 : 0.85; // Primary radial spoke
            } else {
                return 0.25 // Subdued secondary edge opacity
            }
        } else if (isConnectedToHovered) {
            return 1.0
        } else {
            return ambientOpacity
        }
    }

    readonly property real macroOpacityFade: {
        if (isConnectedToSelected || isConnectedToHovered) return 1.0
        if (currentAperture >= 0.35) return 1.0
        if (!isIntraCluster) return 1.0
        return Math.max(0.0, (currentAperture - 0.20) / 0.15)
    }

    readonly property bool hasValidDocks: {
        if (!sourceNode || !targetNode) return false;
        if (rawStartPt.x === 0 && rawStartPt.y === 0) return false;
        if (rawEndPt.x === 0 && rawEndPt.y === 0) return false;
        return true;
    }

    opacity: targetOpacity * macroOpacityFade
    visible: sourceNode !== null && targetNode !== null && opacity > 0.005 && hasValidDocks

    Behavior on opacity {
        NumberAnimation { duration: 240; easing.type: Easing.OutCubic }
    }

    readonly property color edgeColor: {
        var et = (modelData !== undefined && modelData && modelData.edgeType !== undefined) ? modelData.edgeType : edgeType;
        switch (et) {
            case "explicit":  return Theme.tendrilExplicit;
            case "wikilink":  return Theme.tendrilWikilink;
            case "temporal":  return Theme.tendrilTemporal;
            case "semantic":  return Theme.tendrilSemantic;
            case "knn":       return Theme.tendrilSemantic;
            default:          return Theme.tendrilFallback;
        }
    }

    readonly property color filamentColor: edgeColor

    // =========================================================================
    // Core Synaptic Filament
    // =========================================================================
    Shape {
        anchors.fill: parent
        asynchronous: true
        preferredRendererType: Shape.CurveRenderer
        opacity: rootTendril.edgeType === "temporal" ? 0.38 : (rootTendril.edgeType === "explicit" || rootTendril.edgeType === "direct" || rootTendril.edgeType === "wikilink" ? 0.9 : 1.0)

        ShapePath {
            strokeColor: rootTendril.filamentColor
            strokeWidth: {
                if (rootTendril.isHoverBloomed) return Theme.tendrilStrokeHover;
                if (rootTendril.isSibling) return Theme.tendrilStrokeSibling;
                return rootTendril.edgeType === "explicit" || rootTendril.edgeType === "direct" || rootTendril.edgeType === "wikilink" ? Theme.tendrilStrokeExplicit : Theme.tendrilStrokeSemantic;
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
        opacity: rootTendril.isHoverBloomed ? 0.65 : (rootTendril.isVoidMode ? 0.18 : (rootTendril.isConnectedToSelected && !rootTendril.isFirstDegree ? 0.10 : Math.max(0.15, (rootTendril.edgeType === "semantic" ? Math.max(0.6, rootTendril.weight) : rootTendril.weight) * 0.40)))

        ShapePath {
            strokeColor: rootTendril.filamentColor
            strokeWidth: rootTendril.edgeType === "temporal" ? 3.0 : (rootTendril.edgeType === "explicit" || rootTendril.edgeType === "direct" || rootTendril.edgeType === "wikilink" ? 8.0 : Math.max(2.2, rootTendril.weight * 3.4))
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
        property bool isPreviewSlate: false
        property real edgeWeight: 1.0
        property real targetOpacity: 1.0
        property string pEdgeType: "explicit"

        readonly property real baseSize: isFocalLens ? (14 + 10 * edgeWeight) : (8 + 6 * edgeWeight)
        readonly property real glowSize: isPreviewSlate ? baseSize * 0.65 : baseSize
        width: glowSize
        height: glowSize
        opacity: pEdgeType === "temporal" ? targetOpacity * 0.4 : targetOpacity
        visible: targetOpacity > 0.005

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
            width: pEdgeType === "temporal" ? 2.5 : (portRoot.isFocalLens ? (2.5 + 2.0 * portRoot.edgeWeight) : 2.5)
            height: width
            radius: width / 2
            color: "#ffffff"
            opacity: pEdgeType === "temporal" ? 0.4 : 0.85
        }
    }

   // Helper properties to handle edge directionality gracefully
    readonly property bool sourceIsSelected: sourceId === selectedNodeId || (isHoverBloomed && sourceId === hoveredNodeId)
    readonly property point lensPoint: sourceIsSelected ? startPt : endPt
    readonly property point outerPoint: sourceIsSelected ? endPt : startPt

    // Lens Frame Synaptic Port (Fires on the lens for Tier 1, Tier 2, and Hover)
    SynapticGlowPort {
        x: lensPoint.x - width / 2
        y: lensPoint.y - height / 2
        glowColor: edgeType === "semantic" ? "#a78bfa" : filamentColor
        isFocalLens: true
        edgeWeight: edgeType === "semantic" ? Math.max(0.5, weight) : weight
        targetOpacity: rootTendril.opacity
        pEdgeType: rootTendril.edgeType
        z: 9500
    }

    // Outer Node Synaptic Port (ONLY fires on the outer node for Tier 1 and Hover)
    SynapticGlowPort {
        x: outerPoint.x - width / 2
        y: outerPoint.y - height / 2
        glowColor: edgeType === "semantic" ? "#a78bfa" : filamentColor
        isFocalLens: false
        isPreviewSlate: sourceIsSelected ? (targetNode && targetNode.showPreviewSlate === true) : (sourceNode && sourceNode.showPreviewSlate === true)
        edgeWeight: edgeType === "semantic" ? Math.max(0.5, weight) : weight
        targetOpacity: (isFirstDegree || isHoverBloomed) ? rootTendril.opacity : 0.0
        pEdgeType: rootTendril.edgeType
        z: 9500
    }

    // Terminal Bloom Socket at Node Dock Point (Start)
    Rectangle {
        x: startPt.x - width * 0.5
        y: startPt.y - height * 0.5
        width: 6
        height: 6
        radius: 3
        color: edgeColor
        opacity: rootTendril.opacity
        z: 20

        // Outer ambient glow ring
        Rectangle {
            anchors.centerIn: parent
            width: 14
            height: 14
            radius: 7
            color: "transparent"
            border.color: edgeColor
            border.width: 1
            opacity: 0.4
        }
    }

    // Terminal Bloom Socket at Node Dock Point (End)
    Rectangle {
        x: endPt.x - width * 0.5
        y: endPt.y - height * 0.5
        width: 6
        height: 6
        radius: 3
        color: edgeColor
        opacity: rootTendril.opacity
        z: 20

        // Outer ambient glow ring
        Rectangle {
            anchors.centerIn: parent
            width: 14
            height: 14
            radius: 7
            color: "transparent"
            border.color: edgeColor
            border.width: 1
            opacity: 0.4
        }
    }
}
