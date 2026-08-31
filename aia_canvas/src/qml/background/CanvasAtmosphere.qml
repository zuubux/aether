import QtQuick

Item {
    id: rootAtmosphere
    objectName: "canvasAtmosphere"
    anchors.fill: parent
    z: -100

    property real cameraX: 0.0
    property real cameraY: 0.0
    property real parallaxFactor: 0.12

    property color centerColor: "#07111E"
    property color midColor: "#030712"
    property color outerColor: "#000000"

    ShaderEffect {
        id: atmosphereShader
        objectName: "atmosphereShader"
        anchors.fill: parent

        property real cameraX: rootAtmosphere.cameraX
        property real cameraY: rootAtmosphere.cameraY
        property real parallaxFactor: rootAtmosphere.parallaxFactor
        property real _pad: 0.0

        property color centerColor: rootAtmosphere.centerColor
        property color midColor: rootAtmosphere.midColor
        property color outerColor: rootAtmosphere.outerColor

        fragmentShader: "atmosphere.frag.qsb"
    }
}

