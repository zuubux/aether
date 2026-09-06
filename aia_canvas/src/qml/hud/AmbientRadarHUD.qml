import QtQuick
import ".."

Item {
    id: root
    property string engineState: "LATENT"
    property bool compact: false

    implicitWidth: compact ? 20 : 32
    implicitHeight: compact ? 20 : 32
    width: implicitWidth
    height: implicitHeight

    // Pulse Burst Ring (active only in "WORKING" state)
    Rectangle {
        id: pulseBurstRing
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        radius: width / 2
        color: "transparent"
        border.color: Theme.accentAI
        border.width: root.compact ? 1.0 : 1.5
        visible: root.engineState === "WORKING"

        NumberAnimation on scale {
            running: root.engineState === "WORKING"
            loops: Animation.Infinite
            from: 0.6
            to: 1.4
            duration: 1000
            easing.type: Easing.OutQuad
        }
        NumberAnimation on opacity {
            running: root.engineState === "WORKING"
            loops: Animation.Infinite
            from: 0.8
            to: 0.0
            duration: 1000
            easing.type: Easing.OutQuad
        }
    }

    // Rotating Orbit Ring / Ticks
    Item {
        id: orbitContainer
        anchors.fill: parent

        RotationAnimation {
            id: orbitAnim
            target: orbitContainer
            property: "rotation"
            from: 0
            to: 360
            loops: Animation.Infinite
            running: root.engineState !== "OFFLINE"
            duration: {
                if (root.engineState === "WORKING") return 1000;
                if (root.engineState === "DISTILLING") return 3000;
                return 10000;
            }
        }

        // Orbit track ring
        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: "transparent"
            border.color: {
                if (root.engineState === "OFFLINE") return "#EF4444";
                if (root.engineState === "DISTILLING") return "#F59E0B";
                if (root.engineState === "WORKING") return Theme.accentAI;
                return Theme.accentCyan;
            }
            border.width: 1
            opacity: root.engineState === "OFFLINE" ? 0.2 : 0.4
        }

        // Radar tick / satellite node on the orbit
        Rectangle {
            width: root.compact ? 3 : 4
            height: root.compact ? 3 : 4
            radius: width / 2
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            color: {
                if (root.engineState === "OFFLINE") return "#EF4444";
                if (root.engineState === "DISTILLING") return "#F59E0B";
                if (root.engineState === "WORKING") return Theme.accentAI;
                return Theme.accentCyan;
            }
            opacity: root.engineState === "OFFLINE" ? 0.3 : 0.9
        }
    }

    // Center Dot
    Rectangle {
        id: centerDot
        anchors.centerIn: parent
        width: root.compact ? 6 : 10
        height: root.compact ? 6 : 10
        radius: width / 2
        color: {
            if (root.engineState === "OFFLINE") return "#EF4444";
            if (root.engineState === "DISTILLING") return "#F59E0B";
            if (root.engineState === "WORKING") return Theme.accentAI;
            return Theme.accentCyan;
        }
        opacity: (root.engineState === "WORKING") ? 1.0 : (root.engineState === "OFFLINE" ? 0.4 : 0.5)

        // LATENT: gentle breathe animation (opacity 0.3 -> 0.7, 2000ms)
        SequentialAnimation {
            id: latentBreathe
            running: root.engineState === "LATENT"
            loops: Animation.Infinite
            NumberAnimation { target: centerDot; property: "opacity"; from: 0.3; to: 0.7; duration: 1000; easing.type: Easing.InOutSine }
            NumberAnimation { target: centerDot; property: "opacity"; from: 0.7; to: 0.3; duration: 1000; easing.type: Easing.InOutSine }
        }

        // DISTILLING: steady pulse
        SequentialAnimation {
            id: distillingPulse
            running: root.engineState === "DISTILLING"
            loops: Animation.Infinite
            NumberAnimation { target: centerDot; property: "opacity"; from: 0.4; to: 1.0; duration: 500; easing.type: Easing.InOutSine }
            NumberAnimation { target: centerDot; property: "opacity"; from: 1.0; to: 0.4; duration: 500; easing.type: Easing.InOutSine }
        }
    }

    onEngineStateChanged: {
        if (engineState === "WORKING") {
            centerDot.opacity = 1.0;
        } else if (engineState === "OFFLINE") {
            centerDot.opacity = 0.4;
        } else if (engineState === "LATENT") {
            latentBreathe.restart();
        } else if (engineState === "DISTILLING") {
            distillingPulse.restart();
        }

        if (engineState !== "OFFLINE") {
            orbitAnim.restart();
        } else {
            orbitAnim.stop();
        }
    }
}
