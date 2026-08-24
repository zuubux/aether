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

    readonly property bool isImageFile: (filePath && typeof bridge !== "undefined" && bridge) ? bridge.is_image_file(filePath.toString()) : false
    readonly property bool isPdfFile: ext === ".pdf"
    readonly property bool isTableFile: ext === ".csv" || ext === ".tsv"

    property alias nodePill: nodePill
    property alias tokenView: tokenView
    property alias nodePreviewLoader: nodePreviewLoader
    property alias focalSlateLoader: focalSlateLoader

    // Star Bead Core Dot
    Rectangle {
        visible: root.isBeadMode
        anchors.centerIn: parent
        width: 6
        height: 6
        radius: 3
        color: "#ffffff"
        opacity: 0.85
    }

    // =====================================================================
    // TIER 3: Compact Capsule
    // =====================================================================
    NodePill {
        id: nodePill
        anchors.fill: parent
        fileName: root.nodeData ? root.nodeData.fileName : ""
        extensionStr: root.nodeData && root.nodeData.extension ? root.nodeData.extension : root.ext
        archetype: root.nodeData ? root.nodeData.archetype : ""
        accentColor: root.accentColor
        cardRadius: root.cardRadius
        isHovered: root.isHovered
        isSearchResult: root.isSearchResult
        visible: root.isCapsuleMode
        opacity: (root.isCapsuleMode ? 1.0 : 0.0) * root.searchRowOpacity
    }

    // =====================================================================
    // TIER 2: Orbital Horizon Token
    // =====================================================================
    Item {
        id: tokenView
        anchors.fill: parent
        visible: root.isSlateMode
        opacity: (root.isSlateMode ? 1.0 : 0.0) * root.searchRowOpacity

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
            text: root.nodeData ? root.nodeData.fileName : ""
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
        active: root.isPreviewMode
        asynchronous: true
        visible: root.isPreviewMode
        opacity: root.isPreviewMode ? 1.0 : 0.0
        source: Qt.resolvedUrl("node/NodePreview.qml")

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
    // TIER 1: Editor / Preview Slate
    // =====================================================================
    Loader {
        id: focalSlateLoader
        focus: root.isSelected
        anchors.centerIn: parent
        width: root.isSelected ? (parent.width - 24) : 230
        height: root.isSelected ? (parent.height - 24) : 170
        active: root.isSelected
        asynchronous: true
        visible: opacity > 0.01
        opacity: root.isSelected ? 1.0 : 0.0
        source: root.isImageFile ? "ImageSlate.qml" : (root.isPdfFile ? "PdfSlate.qml" : (root.isTableFile ? "TableSlate.qml" : "PreviewSlate.qml"))
        z: 10
        
        Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutQuad } }

        onLoaded: {
            if (item) {
                if (item.hasOwnProperty("width")) item.width = Qt.binding(function() { return focalSlateLoader.width });
                if (item.hasOwnProperty("height")) item.height = Qt.binding(function() { return focalSlateLoader.height });
            }
        }

        Binding { target: focalSlateLoader.item; property: "nodeId"; value: root.nodeId; restoreMode: Binding.RestoreBinding }
        Binding { target: focalSlateLoader.item; property: "isSelected"; value: root.isSelected; restoreMode: Binding.RestoreBinding }
        Binding {
            target: focalSlateLoader.item
            property: "viewportContainer"
            value: root.viewportContainer
            when: focalSlateLoader.item !== null && typeof focalSlateLoader.item.viewportContainer !== "undefined"
            restoreMode: Binding.RestoreBinding
        }
        Binding { target: focalSlateLoader.item; property: "archetype"; value: root.nodeData ? root.nodeData.archetype : "document"; restoreMode: Binding.RestoreBinding }
        Binding {
            target: focalSlateLoader.item
            property: "snippet"
            value: root.snippet
            when: !root.isImageFile && !root.isPdfFile && !root.isTableFile && focalSlateLoader.item !== null
            restoreMode: Binding.RestoreBinding
        }
        Binding {
            target: focalSlateLoader.item
            property: "initialText"
            value: root.initialText
            when: !root.isImageFile && !root.isPdfFile && !root.isTableFile && focalSlateLoader.item !== null
            restoreMode: Binding.RestoreBinding
        }
        Binding { target: focalSlateLoader.item; property: "fileName"; value: root.nodeData ? root.nodeData.fileName : ""; restoreMode: Binding.RestoreBinding }
        Binding { target: focalSlateLoader.item; property: "filePath"; value: root.nodeData ? root.nodeData.filePath : ""; restoreMode: Binding.RestoreBinding }
        Binding { target: focalSlateLoader.item; property: "sizeFormatted"; value: root.nodeData ? (root.nodeData.sizeBytes / 1024).toFixed(1) + " KB" : "0 KB"; restoreMode: Binding.RestoreBinding }
        Binding {
            target: focalSlateLoader.item
            property: "referenceCount"
            value: root.referenceCount
            when: !root.isImageFile && !root.isPdfFile && !root.isTableFile && focalSlateLoader.item !== null
            restoreMode: Binding.RestoreBinding
        }
        Binding { target: focalSlateLoader.item; property: "accentColor"; value: root.nodeAccentColor; restoreMode: Binding.RestoreBinding }
        Binding {
            target: focalSlateLoader.item
            property: "bridge"
            value: root.bridge
            when: focalSlateLoader.item !== null && ("bridge" in focalSlateLoader.item || typeof focalSlateLoader.item.bridge !== "undefined")
            restoreMode: Binding.RestoreBinding
        }
    }
}