import QtQuick

Item {
    id: root
    transformOrigin: Item.Center

    property string tierState: "TIER_3"
    property bool isSelected: false
    property bool isDragging: false
    property bool isSettling: false
    property bool isHovered: false
    
    // Extensible dimensions for overrides
    property real targetWidth: {
        if (isSelected) return 380;
        if (tierState === "TIER_4") return Theme.tier4Width;
        if (tierState === "TIER_3") return Theme.tier3Width;
        if (tierState === "TIER_2") return Theme.tier2Width;
        if (tierState === "TIER_1_5") return Theme.tier1_5Width;
        return Theme.tier3Width;
    }
    
    property real targetHeight: {
        if (isSelected) return 280;
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
    clip: true

    Behavior on width { NumberAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing } }
    Behavior on height { NumberAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing } }
    Behavior on radius { NumberAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing } }

    readonly property point leftDock: Qt.point(parent ? parent.x : x, (parent ? parent.y : y) + height / 2)
    readonly property point rightDock: Qt.point((parent ? parent.x : x) + width, (parent ? parent.y : y) + height / 2)

    function getFlankPort(isLeft, index, totalPorts) {
        var total = totalPorts || 4;
        var step = height / (total + 1);
        var offsetY = (index + 1) * step;
        var localX = isLeft ? 0 : width;
        var localY = offsetY;
        return mapToItem(parent, localX, localY);
    }

    default property alias contentItem: contentContainer.data

    Rectangle {
        id: backgroundRect
        anchors.fill: parent
        z: 0
        color: Theme.surfaceBackground
        border.color: (root.isDragging || root.isSettling) ? Theme.accentCyan : (root.isHovered ? Theme.borderHover : Theme.surfaceBorder)
        border.width: (root.isDragging || root.isSettling) ? 2 : 1
        radius: parent.radius

        Behavior on border.color {
            ColorAnimation { duration: 300; easing.type: Easing.OutQuad }
        }
    }

    Item {
        id: contentContainer
        z: 10
        anchors.fill: parent
    }
}
