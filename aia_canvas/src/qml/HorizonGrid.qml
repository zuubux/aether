import QtQuick
import QtQuick.Shapes

Item {
    id: rootGrid
    anchors.fill: parent
    z: 1

    readonly property real vpY: height * 0.20
    readonly property color gridColor: "#1e293b"

    // Horizon Atmospheric Fog Band
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        y: rootGrid.vpY - 40
        height: 120
        gradient: Gradient {
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.4; color: "#0d131f" }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.45
    }

    // Perspective Ground Plane Iso-Lines
    Shape {
        anchors.fill: parent
        asynchronous: true
        opacity: 0.22

        // Receding Depth Latitude Rings (Non-linear geometric progression)
        ShapePath {
            id: sp1
            strokeColor: rootGrid.gridColor
            strokeWidth: 1.0
            fillColor: "transparent"
            readonly property real lineY: rootGrid.vpY + (rootGrid.height - rootGrid.vpY) * 0.15
            startX: 0; startY: lineY
            PathLine { x: rootGrid.width; y: sp1.lineY }
        }
        ShapePath {
            id: sp2
            strokeColor: rootGrid.gridColor
            strokeWidth: 1.0
            fillColor: "transparent"
            readonly property real lineY: rootGrid.vpY + (rootGrid.height - rootGrid.vpY) * 0.28
            startX: 0; startY: lineY
            PathLine { x: rootGrid.width; y: sp2.lineY }
        }
        ShapePath {
            id: sp3
            strokeColor: rootGrid.gridColor
            strokeWidth: 1.0
            fillColor: "transparent"
            readonly property real lineY: rootGrid.vpY + (rootGrid.height - rootGrid.vpY) * 0.44
            startX: 0; startY: lineY
            PathLine { x: rootGrid.width; y: sp3.lineY }
        }
        ShapePath {
            id: sp4
            strokeColor: rootGrid.gridColor
            strokeWidth: 1.0
            fillColor: "transparent"
            readonly property real lineY: rootGrid.vpY + (rootGrid.height - rootGrid.vpY) * 0.62
            startX: 0; startY: lineY
            PathLine { x: rootGrid.width; y: sp4.lineY }
        }
        ShapePath {
            id: sp5
            strokeColor: rootGrid.gridColor
            strokeWidth: 1.0
            fillColor: "transparent"
            readonly property real lineY: rootGrid.vpY + (rootGrid.height - rootGrid.vpY) * 0.82
            startX: 0; startY: lineY
            PathLine { x: rootGrid.width; y: sp5.lineY }
        }
        ShapePath {
            id: sp6
            strokeColor: rootGrid.gridColor
            strokeWidth: 1.0
            fillColor: "transparent"
            readonly property real lineY: rootGrid.vpY + (rootGrid.height - rootGrid.vpY) * 1.0
            startX: 0; startY: lineY
            PathLine { x: rootGrid.width; y: sp6.lineY }
        }
    }
}