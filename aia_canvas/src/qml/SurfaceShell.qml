import QtQuick

Item {
    id: root
    transformOrigin: Item.Center

    property string tierState: "TIER_3"
    property bool isSelected: false
    property bool isDragging: false
    property bool isSettling: false
    property bool isHovered: false
    property bool isConstellationPeer: false
    property bool isPeerWarmed: isConstellationPeer
    property real peerLuminosityFactor: 0.0
    property color archetypeColor: typeof Theme !== "undefined" ? Theme.badgeDefault : "#94A3B8"
    
    // Extensible dimensions for overrides
    property real targetWidth: {
        if (tierState === "TIER_1") return Theme.tier1_5Width;
        if (tierState === "TIER_4") return Theme.tier4Width;
        if (tierState === "TIER_3") return Theme.tier3Width;
        if (tierState === "TIER_2") return Theme.tier2Width;
        if (tierState === "TIER_1_5") return Theme.tier1_5Width;
        return Theme.tier3Width;
    }
    
    property real targetHeight: {
        if (tierState === "TIER_1") return Theme.tier1_5Height;
        if (tierState === "TIER_4") return Theme.tier4Height;
        if (tierState === "TIER_3") return Theme.tier3Height;
        if (tierState === "TIER_2") return Theme.tier2Height;
        if (tierState === "TIER_1_5") return Theme.tier1_5Height;
        return Theme.tier3Height;
    }
    
    property real targetRadius: {
        if (tierState === "TIER_4") return Theme.tier4Radius;
        if (tierState === "TIER_3") return Theme.tier3Radius;
        if (tierState === "TIER_2") return Theme.tier2Radius;
        if (tierState === "TIER_1_5") return Theme.tier1_5Radius;
        return Theme.tier3Radius;
    }

    width: targetWidth
    height: targetHeight
    property real radius: targetRadius

    readonly property bool isCollapsing: targetWidth < width || targetHeight < height
    readonly property bool isMorphing: (widthAnim && widthAnim.running) || (heightAnim && heightAnim.running) || motionController.isAnimating

    layer.enabled: motionController.isAnimating

    Behavior on width {
        NumberAnimation {
            id: widthAnim
            duration: (root.tierState === "TIER_1_5" || root.tierState === "TIER_2") ? 0 : (Theme.animCollapseDuration ?? 160)
            easing.type: Theme.animCollapseEasing
        }
    }
    Behavior on height {
        NumberAnimation {
            id: heightAnim
            duration: (root.tierState === "TIER_1_5" || root.tierState === "TIER_2") ? 0 : (Theme.animCollapseDuration ?? 160)
            easing.type: Theme.animCollapseEasing
        }
    }
    Behavior on radius {
        NumberAnimation {
            id: radiusAnim
            duration: (root.tierState === "TIER_1_5" || root.tierState === "TIER_2") ? 0 : (Theme.animCollapseDuration ?? 160)
            easing.type: Theme.animCollapseEasing
        }
    }

    onTierStateChanged: {
        if (tierState === "TIER_2") {
            motionController.duration = Theme.animFadeInDuration ?? 160
            motionController.bloom(0.96, 1.0, 1.0)
        } else if (tierState === "TIER_1_5") {
            motionController.duration = Theme.animDuration ?? 300
            motionController.bloom(0.90, 1.0, 2.5)
        } else if (tierState === "TIER_3" || tierState === "TIER_4") {
            motionController.duration = Theme.animCollapseDuration ?? 160
            motionController.bloom(1.0, 1.0, 0.0)
        }
    }

    readonly property point leftDock: Qt.point(parent ? parent.x : x, (parent ? parent.y : y) + height / 2)
    readonly property point rightDock: Qt.point((parent ? parent.x : x) + width, (parent ? parent.y : y) + height / 2)

    readonly property color surfaceBorderColor: backgroundRect.border.color
    readonly property real surfaceBorderWidth: backgroundRect.border.width

    function getFlankPort(isLeft, index, totalPorts) {
        var total = totalPorts || 4;
        var step = height / (total + 1);
        var offsetY = 0;
        if (typeof index === "number" && index > 0 && index < 1) {
            offsetY = height * index;
        } else {
            var idx = (typeof index === "number" && !isNaN(index)) ? Math.floor(index) : 0;
            offsetY = (idx + 1) * step;
        }
        var localX = isLeft ? 0 : width;
        var parentX = parent ? parent.x : x;
        var parentY = parent ? parent.y : y;
        return Qt.point(parentX + localX, parentY + offsetY);
    }

    default property alias contentItem: contentContainer.data

    Rectangle {
        id: backgroundRect
        anchors.fill: parent
        z: 0
        color: root.tierState === "TIER_4" ? "transparent" : ((root.isConstellationPeer || root.isPeerWarmed) ? Qt.lighter(Theme.surfaceBackground, 1.12) : Theme.surfaceBackground)
        border.color: {
            if (root.isSelected || root.isDragging || root.isSettling) {
                return root.archetypeColor;
            }
            if (root.isHovered) {
                return Qt.lighter(root.archetypeColor, 1.25);
            }
            if (root.isConstellationPeer || root.isPeerWarmed) {
                return Qt.rgba(root.archetypeColor.r, root.archetypeColor.g, root.archetypeColor.b, 0.70);
            }
            return Theme.borderSubtle;
        }
        border.width: root.tierState === "TIER_4" ? 0 : ((root.isSelected || root.isDragging || root.isSettling || root.isHovered || root.isConstellationPeer || root.isPeerWarmed) ? 1.5 : 1.0)
        radius: parent.radius

        Behavior on border.color {
            ColorAnimation { duration: root.isIlluminatedPeer ? 350 : 300; easing.type: Theme.animCollapseEasing }
        }
        Behavior on color {
            ColorAnimation { duration: root.isIlluminatedPeer ? 350 : 300; easing.type: Theme.animCollapseEasing }
        }
    }

    Item {
        id: contentContainer
        z: 10
        anchors.fill: parent
    }

    AetherMotion {
        id: motionController
        objectName: "motionController"
        target: root
        duration: Theme.animCollapseDuration ?? 160
    }
}
