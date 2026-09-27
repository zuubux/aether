import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "components"
import "bar"

Window {
    id: mainRoot
    objectName: "mainCanvasView"
    visible: true
    title: "Aether // Workspace"
    color: Theme.surfaceBackground

    // Dynamic screen bounds — zero hardcoded window sizes
    property string liveDateText: Qt.formatDateTime(new Date(), "ddd, MMM d · h:mm AP")
    screen: Qt.application.screens[targetScreenIdx !== undefined ? targetScreenIdx : 0]
    visibility: (isFullscreen || isSpanAll) ? Window.FullScreen : Window.Windowed

    // If windowed, derive size proportionally from screen geometry
    width: screen ? Math.round(screen.width * 0.85) : 1920
    height: screen ? Math.round(screen.height * 0.85) : 1080

    Timer {
        id: clockTimer
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            mainRoot.liveDateText = Qt.formatDateTime(new Date(), "ddd, MMM d · h:mm AP")
        }
    }

    // =========================================================================
    // 1. MINIMAL HORIZON ANCHORS (Floating directly on root window)
    // Left: Ambient Weather & Location
    // Right: Date, Time & Persona Identity
    // =========================================================================
    Text {
        id: leftHorizonAnchor
        objectName: "leftHorizonAnchor"
        text: (typeof horizonController !== "undefined" && horizonController && horizonController.ambientStatus) ? horizonController.ambientStatus : ""
        visible: text.length > 0
        opacity: leftAnchorHover.containsMouse ? 0.80 : 0.35
        color: Theme.textPrimary
        font.family: Theme.fontSans
        font.pixelSize: 13
        font.weight: Font.Normal
        z: 90

        anchors.top: parent.top
        anchors.topMargin: 18
        anchors.left: parent.left
        anchors.leftMargin: 32

        Behavior on opacity {
            NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
        }

        MouseArea {
            id: leftAnchorHover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
        }
    }

    Text {
        id: rightHorizonAnchor
        objectName: "rightHorizonAnchor"
        text: mainRoot.liveDateText + ((typeof horizonController !== "undefined" && horizonController && horizonController.identity) ? (" // " + horizonController.identity) : "")
        opacity: rightAnchorHover.containsMouse ? 0.80 : 0.35
        color: Theme.textPrimary
        font.family: Theme.fontSans
        font.pixelSize: 13
        font.weight: Font.Normal
        z: 90

        anchors.top: parent.top
        anchors.topMargin: 18
        anchors.right: parent.right
        anchors.rightMargin: 32

        Behavior on opacity {
            NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
        }

        MouseArea {
            id: rightAnchorHover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
        }
    }
    // =========================================================================
    // 3. BOTTOM OMNIBAR SELF-MORPHING AMBIENT PILL & DYNAMIC DISPATCH
    // Self-morphs proportionally between an ambient pill and an expanded workspace.
    // =========================================================================
    AetherMotion {
        id: omniBarMotion
        target: omniBar
    }

    OmniBar {
        id: omniBar
        objectName: "omniBar"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Math.round(parent.height * 0.03)
        z: 100
    }

    Shortcut {
        sequence: "Ctrl+Space"
        onActivated: summonOmniBar()
    }

    Shortcut {
        sequence: "Escape"
        enabled: omniBar.isExpanded
        onActivated: {
            omniBar.dismiss();
        }
    }

    function summonOmniBar() {
        if (typeof searchController !== "undefined" && searchController) {
            searchController.set_search_active(true);
        }
        omniBar.open();
        omniBarMotion.bloom(0.94, 1.0, 4.0);
    }

    // =========================================================================
    // 2. ACTIVE STAGE (Plates Canvas)
    // Dynamic stage housing active plates, expanding across the display.
    // Clean void when vacant.
    // =========================================================================
    Item {
        id: stageContainer
        objectName: "stageContainer"

        anchors.top: parent.top
        anchors.topMargin: 64
        anchors.left: parent.left
        anchors.leftMargin: Math.max(24, Math.round(mainRoot.width * 0.02))
        anchors.right: parent.right
        anchors.rightMargin: Math.max(170, Math.round(mainRoot.width * 0.13))
        anchors.bottom: omniBar.top
        anchors.bottomMargin: Math.max(20, Math.round(mainRoot.height * 0.025))

        clip: true

        // Synchronize viewport dimensions with allocator backend
        onWidthChanged: syncDimensions()
        onHeightChanged: syncDimensions()
        Component.onCompleted: syncDimensions()

        function syncDimensions() {
            if (width > 0 && height > 0 && typeof plateCanvasController !== "undefined" && plateCanvasController) {
                plateCanvasController.setViewportDimensions(width, height);
            }
        }

        // Helper to locate resolved allocation for an active plate
        function findPlateAllocation(nodeId) {
            if (typeof plateCanvasController === "undefined" || !plateCanvasController || !plateCanvasController.bentoGeometry) {
                return null;
            }
            var geom = plateCanvasController.bentoGeometry;
            if (Array.isArray(geom) || (geom && geom.length !== undefined)) {
                for (var i = 0; i < geom.length; i++) {
                    var alloc = geom[i];
                    var allocId = alloc.node_id !== undefined ? alloc.node_id : alloc.nodeId;
                    if (allocId === nodeId) {
                        return alloc;
                    }
                }
            } else if (geom && typeof geom === "object") {
                if (geom[nodeId] !== undefined) return geom[nodeId];
                if (geom[String(nodeId)] !== undefined) return geom[String(nodeId)];
            }
            return null;
        }

        // Active Plates Instantiator
        Repeater {
            id: plateRepeater
            objectName: "plateRepeater"
            model: (typeof plateCanvasController !== "undefined" && plateCanvasController) ? plateCanvasController.activePlates : []

            delegate: PlateCard {
                id: plateCardInstance
                modelData: modelData
                bentoAlloc: stageContainer.findPlateAllocation(
                    modelData ? (modelData.node_id !== undefined ? modelData.node_id : (modelData.nodeId !== undefined ? modelData.nodeId : modelData.id)) : 0
                )
            }
        }
    }

    // =========================================================================
    // 3. PERIPHERAL FEED (Floating Semantic Chips on Right Perimeter)
    // Borderless and transparent column of floating semantic pill chips.
    // =========================================================================
    Item {
        id: peripheralFeedContainer
        objectName: "peripheralFeed"
        anchors.right: parent.right
        anchors.rightMargin: Math.max(20, Math.round(parent.width * 0.02))
        anchors.top: parent.top
        anchors.topMargin: Math.max(100, Math.round(parent.height * 0.30))
        width: Math.max(160, Math.round(parent.width * 0.12))
        height: childrenRect.height
        z: 85

        Column {
            id: anchorColumn
            anchors.right: parent.right
            spacing: 10

            Repeater {
                id: anchorRepeater
                objectName: "anchorRepeater"
                model: (typeof feedController !== "undefined" && feedController) ? feedController.headerAnchors : []
                delegate: FeedHeaderAnchor {
                    modelData: modelData
                    anchors.right: parent ? parent.right : undefined
                }
            }
        }
    }

}
