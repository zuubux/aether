import QtQuick
import ".."

Item {
    id: pillRoot
    anchors.fill: parent

    // Public Interface Contract
    property string fileName: ""
    property string extensionStr: ""
    property string archetype: ""
    property color accentColor: "#00E5FF"
    property real cardRadius: 6
    property bool isHovered: false
    property bool isSearchResult: false
    property bool isBead: (typeof rootItem !== "undefined" && rootItem.currentAperture < 0.40) && !(typeof rootItem !== "undefined" && rootItem.showPreviewSlate) && !(typeof rootItem !== "undefined" && rootItem.isHovered)

    readonly property string cleanTitle: {
        var name = pillRoot.fileName || "";
        return name.lastIndexOf(".") > 0 ? name.substring(0, name.lastIndexOf(".")) : name;
    }

    implicitHeight: 32

    // Extension Badge
    Rectangle {
        id: badge
        width: Math.max(18, badgeLabel.implicitWidth + 6)
        height: 14
        radius: 3
        color: Theme.getBadgeColor(pillRoot.extensionStr, pillRoot.archetype)
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        visible: !pillRoot.isBead
        opacity: pillRoot.isBead ? 0.0 : 1.0
        z: 2

        Text {
            id: badgeLabel
            anchors.centerIn: parent
            text: Theme.normalizeExt(pillRoot.extensionStr)
            font.pixelSize: 8
            font.family: Theme.fontCode
            font.bold: true
            color: "#0D1117"
        }
    }

    // File Name
    Text {
        id: label
        text: pillRoot.cleanTitle
        font.pixelSize: 10
        font.family: Theme.fontSans
        font.weight: Font.Normal
        color: Theme.textPrimary
        elide: Text.ElideRight
        anchors.left: badge.right
        anchors.leftMargin: 6
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        visible: !pillRoot.isBead
        opacity: pillRoot.isBead ? 0.0 : 1.0
        z: 2
    }
}
