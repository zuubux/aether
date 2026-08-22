import QtQuick

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

    implicitWidth: pillRow.implicitWidth
    implicitHeight: 32

    Row {
        id: pillRow
        anchors.centerIn: parent
        spacing: 6
        z: 2
        visible: !pillRoot.isBead
        opacity: pillRoot.isBead ? 0.0 : 1.0

        // Extension Badge
        Rectangle {
            width: 16
            height: 14
            radius: 3
            color: pillRoot.accentColor || "#00E5FF"
            anchors.verticalCenter: parent.verticalCenter
            Text {
                anchors.centerIn: parent
                text: (pillRoot.extensionStr || "md").replace(".", "").toUpperCase()
                font.pixelSize: 8
                font.bold: true
                color: "#0D1117"
            }
        }

        // File Name
        Text {
            text: pillRoot.fileName || ""
            font.pixelSize: 11
            font.weight: Font.DemiBold
            color: "#E6EDF3"
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
