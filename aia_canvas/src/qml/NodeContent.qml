import QtQuick
import QtQuick.Controls
import Aether.Content 1.0
import "node"

Item {
    id: root
    anchors.fill: parent

    property string tierState: "TIER_3"
    property var nodeData: null
    property real activeLuminosity: 1.0

    // Dependencies from context
    property var bridge: null
    property var viewportContainer: null
    property bool isSelected: false
    property bool isSearchActive: false
    property bool isHovered: false
    property bool isSearchResult: false
    property string ext: ""
    property color accentColor: "#94a3b8"
    property color nodeAccentColor: "#94a3b8"
    property real cardRadius: 16
    property real searchRowOpacity: 1.0
    property string filePath: ""
    property string snippet: ""
    property string initialText: ""
    property int referenceCount: 0
    property int nodeId: 0
    property bool showPreviewSlate: false

    readonly property bool isPreviewMode: tierState === "TIER_1_5"
    readonly property bool isSlateMode: tierState === "TIER_2"
    readonly property bool isCapsuleMode: tierState === "TIER_3"
    readonly property bool isBeadMode: tierState === "TIER_4"

    readonly property string archetype: root.nodeData ? (root.nodeData.archetype || "") : ""
    readonly property bool isAudioFile: root.archetype.toUpperCase() === "AUDIO" || [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"].indexOf(ext.toLowerCase()) !== -1
    readonly property bool isVideoFile: root.archetype.toUpperCase() === "VIDEO" || [".mp4", ".mkv", ".webm", ".mov", ".avi"].indexOf(ext.toLowerCase()) !== -1
    readonly property bool isImageFile: (filePath && typeof bridge !== "undefined" && bridge) ? bridge.is_image_file(filePath.toString()) : false
    readonly property bool isPdfFile: ext === ".pdf"
    readonly property bool isTableFile: ext === ".csv" || ext === ".tsv"

    property alias nodePill: nodePill
    property alias tokenView: tokenView
    property alias nodePreviewLoader: nodePreviewLoader
    property alias focalSlateLoader: focalSlateLoader

    // TIER 4: Bioluminescent Star Bead / Ember (Multi-Layer Concentric Radial Bokeh Glow)
    Item {
        visible: opacity > 0.001
        opacity: root.isBeadMode ? 1.0 : 0.0
        anchors.centerIn: parent
        width: 10
        height: 10

        Behavior on opacity {
            NumberAnimation {
                duration: root.isBeadMode ? (typeof Theme !== "undefined" && Theme.animDuration ? Theme.animDuration : 400) : (typeof Theme !== "undefined" && Theme.animCollapseDuration ? Theme.animCollapseDuration : 280)
                easing.type: root.isBeadMode ? (typeof Theme !== "undefined" && Theme.animEasing ? Theme.animEasing : Easing.OutCubic) : (typeof Theme !== "undefined" && Theme.animCollapseEasing ? Theme.animCollapseEasing : Easing.InOutQuad)
            }
        }

        readonly property color emberColor: Theme.getBadgeColor(root.nodeData ? root.nodeData.extension : "", root.nodeData ? root.nodeData.archetype : "")

        // Outer soft halo / glow layer (10px diameter with soft edge falloff)
        Rectangle {
            anchors.centerIn: parent
            width: 10
            height: 10
            radius: 5
            color: parent.emberColor
            opacity: 0.15
            antialiasing: true
        }

        // Mid soft halo layer (8px diameter)
        Rectangle {
            anchors.centerIn: parent
            width: 8
            height: 8
            radius: 4
            color: parent.emberColor
            opacity: 0.30
            antialiasing: true
        }

        // Inner halo layer (5px diameter)
        Rectangle {
            anchors.centerIn: parent
            width: 5
            height: 5
            radius: 2.5
            color: parent.emberColor
            opacity: 0.55
            antialiasing: true
        }

        // Inner bright core (3px diameter, archetype color)
        Rectangle {
            anchors.centerIn: parent
            width: 3
            height: 3
            radius: 1.5
            color: parent.emberColor
            opacity: 1.0
            antialiasing: true
        }
    }

    // =====================================================================
    // TIER 3: Compact Capsule
    // =====================================================================
    NodePill {
        id: nodePill
        anchors.fill: parent
        fileName: root.nodeData ? root.nodeData.fileName : ""
        displayTitle: root.nodeData ? (root.nodeData.displayTitle || root.nodeData.display_title || "") : ""
        extensionStr: root.nodeData && root.nodeData.extension ? root.nodeData.extension : root.ext
        archetype: root.nodeData ? root.nodeData.archetype : ""
        accentColor: root.accentColor
        cardRadius: root.cardRadius
        isHovered: root.isHovered
        isSearchResult: root.isSearchResult
        visible: opacity > 0.001
        opacity: (root.isCapsuleMode ? 1.0 : 0.0) * root.searchRowOpacity

        Behavior on opacity {
            NumberAnimation {
                duration: root.isCapsuleMode ? (typeof Theme !== "undefined" && Theme.animDuration ? Theme.animDuration : 400) : (typeof Theme !== "undefined" && Theme.animCollapseDuration ? Theme.animCollapseDuration : 280)
                easing.type: root.isCapsuleMode ? (typeof Theme !== "undefined" && Theme.animEasing ? Theme.animEasing : Easing.OutCubic) : (typeof Theme !== "undefined" && Theme.animCollapseEasing ? Theme.animCollapseEasing : Easing.InOutQuad)
            }
        }
    }

    // =====================================================================
    // TIER 2: Orbital Horizon Token
    // =====================================================================
    Item {
        id: tokenView
        anchors.fill: parent
        visible: opacity > 0.001
        opacity: (root.isSlateMode ? 1.0 : 0.0) * root.searchRowOpacity

        Behavior on opacity {
            NumberAnimation {
                duration: root.isSlateMode ? (typeof Theme !== "undefined" && Theme.animDuration ? Theme.animDuration : 400) : (typeof Theme !== "undefined" && Theme.animCollapseDuration ? Theme.animCollapseDuration : 280)
                easing.type: root.isSlateMode ? (typeof Theme !== "undefined" && Theme.animEasing ? Theme.animEasing : Easing.OutCubic) : (typeof Theme !== "undefined" && Theme.animCollapseEasing ? Theme.animCollapseEasing : Easing.InOutQuad)
            }
        }

        Rectangle {
            id: iconBadge
            width: Math.max(20, iconBadgeText.implicitWidth + 8)
            height: 16
            radius: 3
            color: Theme.getBadgeColor(root.nodeData ? root.nodeData.extension : "", root.nodeData ? root.nodeData.archetype : "")
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: 10
            Text {
                id: iconBadgeText
                anchors.centerIn: parent
                text: Theme.normalizeExt(root.nodeData && root.nodeData.extension ? root.nodeData.extension : "md")
                font.pixelSize: 8
                font.family: Theme.fontCode
                font.bold: true
                color: "#0D1117"
            }
        }

        Text {
            id: titleLabel
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: iconBadge.right
            anchors.right: parent.right
            anchors.margins: 10
            text: root.nodeData ? (root.nodeData.fileName || root.nodeData.displayTitle) : ""
            font.pixelSize: 12
            font.family: Theme.fontSans
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            elide: Text.ElideMiddle
        }
    }

    // =====================================================================
    // TIER 1.5: Hover-Dwell Preview Card
    // =====================================================================
    Loader {
        id: nodePreviewLoader
        anchors.fill: parent
        z: 2
        active: root.isPreviewMode || opacity > 0.001
        asynchronous: true
        visible: opacity > 0.001
        opacity: (root.isPreviewMode ? 1.0 : 0.0) * root.searchRowOpacity
        source: Qt.resolvedUrl("node/NodePreview.qml")

        Behavior on opacity {
            NumberAnimation {
                duration: root.isPreviewMode ? (typeof Theme !== "undefined" && Theme.animDuration ? Theme.animDuration : 400) : (typeof Theme !== "undefined" && Theme.animCollapseDuration ? Theme.animCollapseDuration : 280)
                easing.type: root.isPreviewMode ? (typeof Theme !== "undefined" && Theme.animEasing ? Theme.animEasing : Easing.OutCubic) : (typeof Theme !== "undefined" && Theme.animCollapseEasing ? Theme.animCollapseEasing : Easing.InOutQuad)
            }
        }

        onStatusChanged: {
            if (status === Loader.Error) {
                console.error("[LOADER ERROR] Failed to load NodePreview:", sourceComponent ? sourceComponent.errorString() : "Unknown error");
            }
        }
        
        Binding {
            target: nodePreviewLoader.item
            property: "nodeData"
            value: root.nodeData
            when: nodePreviewLoader.status === Loader.Ready
        }
        Binding {
            target: nodePreviewLoader.item
            property: "path"
            value: root.filePath
            when: nodePreviewLoader.status === Loader.Ready && root.filePath !== ""
        }
        Binding {
            target: nodePreviewLoader.item
            property: "archetype"
            value: root.nodeData ? root.nodeData.archetype : "document"
            when: nodePreviewLoader.status === Loader.Ready
        }
    }

    // =====================================================================
    // TIER 1: Editor / Preview Slate (Legacy focal card - suppressed)
    // =====================================================================
    Loader {
        id: focalSlateLoader
        objectName: "focalSlateLoader"
        focus: false
        anchors.centerIn: parent
        width: 230
        height: 170
        active: false
        asynchronous: true
        visible: false
        opacity: 0.0
        source: ""
        z: 10
    }
}