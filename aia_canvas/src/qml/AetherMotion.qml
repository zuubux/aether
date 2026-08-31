import QtQuick

Item {
    id: motionRoot
    objectName: "aetherMotion"

    property Item target: null
    property int duration: typeof Theme !== "undefined" && Theme.animCollapseDuration ? Theme.animCollapseDuration : 280
    property real fromScale: 0.92
    property real toScale: 1.0
    property real yGlideDistance: 2.0
    readonly property bool isAnimating: bloomAnimation.running

    onTargetChanged: {
        if (target) {
            if (!target.transform) {
                target.transform = [glideTranslate]
            } else {
                var arr = target.transform;
                if (arr.indexOf(glideTranslate) === -1) {
                    arr.push(glideTranslate);
                    target.transform = arr;
                }
            }
        }
    }

    onIsAnimatingChanged: {
        if (target) {
            target.layer.enabled = isAnimating
        }
    }

    Translate {
        id: glideTranslate
        y: 0
    }

    ParallelAnimation {
        id: bloomAnimation

        onStarted: {
            if (target) {
                target.layer.enabled = true
            }
        }

        onStopped: {
            if (target) {
                target.scale = motionRoot.toScale
                glideTranslate.y = 0
                target.layer.enabled = false
            }
        }

        SequentialAnimation {
            NumberAnimation {
                target: motionRoot.target
                property: "scale"
                from: motionRoot.fromScale
                to: motionRoot.fromScale < motionRoot.toScale ? motionRoot.toScale * 1.015 : motionRoot.toScale
                duration: Math.round(motionRoot.duration * 0.68)
                easing.type: Easing.OutQuint
            }
            NumberAnimation {
                target: motionRoot.target
                property: "scale"
                from: motionRoot.fromScale < motionRoot.toScale ? motionRoot.toScale * 1.015 : motionRoot.toScale
                to: motionRoot.toScale
                duration: motionRoot.duration - Math.round(motionRoot.duration * 0.68)
                easing.type: Easing.OutQuint
            }
        }

        NumberAnimation {
            target: glideTranslate
            property: "y"
            from: motionRoot.yGlideDistance
            to: 0
            duration: motionRoot.duration
            easing.type: Easing.OutQuint
        }
    }

    function bloom(fromScale, toScale, yOffset) {
        if (!target) return;
        if (bloomAnimation.running) {
            bloomAnimation.stop();
        }
        motionRoot.fromScale = (typeof fromScale === "number" && !isNaN(fromScale)) ? fromScale : 0.92;
        motionRoot.toScale = (typeof toScale === "number" && !isNaN(toScale)) ? toScale : 1.0;
        motionRoot.yGlideDistance = (typeof yOffset === "number" && !isNaN(yOffset)) ? yOffset : 2.0;

        bloomAnimation.start();
    }

    function triggerBloom(fromS, toS, gDist) {
        bloom(fromS, toS, gDist);
    }
}
