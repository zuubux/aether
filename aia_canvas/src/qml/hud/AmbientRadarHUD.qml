import QtQuick
import QtQuick as QtQuick
import QtQuick.Shapes
import ".."

Item {
    id: root
    property string engineState: "LATENT"
    property bool compact: false

    property real size: compact ? 20 : 32
    width: size
    height: size

    readonly property string runeState: {
        if (engineState === "WORKING" || engineState === "SYNTHESIZING") return "SYNTHESIZING";
        if (engineState === "DISTILLING") return "DISTILLING";
        if (engineState === "OFFLINE") return "OFFLINE";
        return "LATENT";
    }

    QtQuick.Canvas {
        id: canvas
        anchors.fill: parent

        property string runeState: root.runeState

        readonly property color targetColor: {
            if (runeState === "OFFLINE") return (Theme.runeColorOffline !== undefined ? Theme.runeColorOffline : "#EF4444");
            if (runeState === "DISTILLING") return (Theme.runeColorDistilling !== undefined ? Theme.runeColorDistilling : "#F59E0B");
            if (runeState === "SYNTHESIZING") return (Theme.runeColorSynthesizing !== undefined ? Theme.runeColorSynthesizing : Theme.accentAI);
            if (runeState === "LATENT") return (Theme.textMuted !== undefined ? Theme.textMuted : "#64748B");
            return (Theme.runeColorLatent !== undefined ? Theme.runeColorLatent : (Theme.textMuted !== undefined ? Theme.textMuted : "#64748B"));
        }
        property color activeColor: targetColor
        Behavior on activeColor { 
            ColorAnimation { 
                duration: (Theme.runeAnimColorDuration !== undefined ? Theme.runeAnimColorDuration : 300); 
                easing.type: Easing.OutCubic 
            } 
        }

        property real targetInnerRadius: {
            if (runeState === "SYNTHESIZING") return 5.7;
            if (runeState === "DISTILLING") return 6.0;
            return 6.2;
        }
        property real currentInnerRadius: targetInnerRadius
        Behavior on currentInnerRadius {
            NumberAnimation { 
                duration: (Theme.runeAnimIrisDuration !== undefined ? Theme.runeAnimIrisDuration : 320); 
                easing.type: Easing.OutBack; 
                easing.overshoot: 1.4 
            }
        }

        property real targetOuterRadius: {
            if (runeState === "SYNTHESIZING") return 10.4;
            if (runeState === "DISTILLING") return 10.1;
            if (runeState === "OFFLINE") return 9.4;
            return 9.6;
        }
        property real currentOuterRadius: targetOuterRadius
        Behavior on currentOuterRadius {
            NumberAnimation { 
                duration: (Theme.runeAnimIrisDuration !== undefined ? Theme.runeAnimIrisDuration : 320) + 40; 
                easing.type: Easing.OutBack; 
                easing.overshoot: 1.3 
            }
        }

        property real targetSweepInner: (runeState === "SYNTHESIZING") ? 75 : 62
        property real currentSweepInner: targetSweepInner
        Behavior on currentSweepInner {
            NumberAnimation { 
                duration: (Theme.runeAnimSweepDuration !== undefined ? Theme.runeAnimSweepDuration : 280); 
                easing.type: Easing.OutCubic 
            }
        }

        property real innerBaseAngle: 0
        property real outerBaseAngle: 0
        property real continuousInner: 0
        property real continuousOuter: 0
        property real coreScale: 1.0

        NumberAnimation on continuousInner {
            running: canvas.runeState === "SYNTHESIZING"
            from: 0; to: 360; duration: (Theme.runeSpinSynthInnerPeriod !== undefined ? Theme.runeSpinSynthInnerPeriod : 1400); loops: Animation.Infinite
        }
        NumberAnimation on continuousOuter {
            running: canvas.runeState === "SYNTHESIZING"
            from: 360; to: 0; duration: (Theme.runeSpinSynthOuterPeriod !== undefined ? Theme.runeSpinSynthOuterPeriod : 2200); loops: Animation.Infinite
        }
        NumberAnimation on continuousOuter {
            running: canvas.runeState === "DISTILLING"
            from: 0; to: 360; duration: (Theme.runeSpinDistillOuterPeriod !== undefined ? Theme.runeSpinDistillOuterPeriod : 4500); loops: Animation.Infinite
        }

        Behavior on innerBaseAngle {
            NumberAnimation { 
                duration: (Theme.runeAnimElasticDuration !== undefined ? Theme.runeAnimElasticDuration : 500); 
                easing.type: Easing.OutElastic; 
                easing.amplitude: 1.1; 
                easing.period: 0.35 
            }
        }
        Behavior on outerBaseAngle {
            NumberAnimation { 
                duration: (Theme.runeAnimElasticDuration !== undefined ? Theme.runeAnimElasticDuration : 500) + 50; 
                easing.type: Easing.OutElastic; 
                easing.amplitude: 1.2; 
                easing.period: 0.4 
            }
        }

        SequentialAnimation on coreScale {
            running: canvas.runeState === "DISTILLING"
            loops: Animation.Infinite
            NumberAnimation { to: 1.25; duration: (Theme.runePulseDistillPeriod !== undefined ? Theme.runePulseDistillPeriod : 1200); easing.type: Easing.InOutQuad }
            NumberAnimation { to: 0.85; duration: (Theme.runePulseDistillPeriod !== undefined ? Theme.runePulseDistillPeriod : 1200); easing.type: Easing.InOutQuad }
        }

        onRuneStateChanged: {
            if (runeState === "LATENT") {
                innerBaseAngle = 0;
                outerBaseAngle = 0;
                coreScale = 1.0;
            } else if (runeState === "OFFLINE") {
                innerBaseAngle = 18;
                outerBaseAngle = 42;
                coreScale = 0.9;
            } else if (runeState === "DISTILLING") {
                innerBaseAngle = 0;
            }
            canvas.requestPaint();
        }

        onContinuousInnerChanged: canvas.requestPaint()
        onContinuousOuterChanged: canvas.requestPaint()
        onCurrentInnerRadiusChanged: canvas.requestPaint()
        onCurrentOuterRadiusChanged: canvas.requestPaint()
        onCurrentSweepInnerChanged: canvas.requestPaint()
        onCoreScaleChanged: canvas.requestPaint()
        onActiveColorChanged: canvas.requestPaint()

        onPaint: {
            var ctx = canvas.getContext("2d");
            ctx.save();
            ctx.clearRect(0, 0, width, height);

            var cx = width * 0.5;
            var cy = height * 0.5;
            var scale = width / 24.0;

            ctx.save();
            ctx.translate(cx, cy);
            ctx.scale(coreScale, coreScale);
            ctx.beginPath();
            ctx.arc(0, 0, 1.8 * scale, 0, Math.PI * 2);
            ctx.fillStyle = activeColor;
            ctx.globalAlpha = (runeState === "LATENT") ? 0.25 : 1.0;
            ctx.fill();
            ctx.restore();

            var effInnerAngle = (runeState === "SYNTHESIZING") ? continuousInner : innerBaseAngle;
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate((effInnerAngle * Math.PI) / 180);
            ctx.lineWidth = 1.25 * scale;
            ctx.strokeStyle = activeColor;
            ctx.lineCap = "butt";
            ctx.globalAlpha = (runeState === "LATENT") ? 0.25 : 0.85;

            var arcSweep = (currentSweepInner * Math.PI) / 180;
            for (var i = 0; i < 3; i++) {
                var start = (i * 120 * Math.PI) / 180;
                ctx.beginPath();
                ctx.arc(0, 0, currentInnerRadius * scale, start, start + arcSweep);
                ctx.stroke();
            }
            ctx.restore();

            var effOuterAngle = (runeState === "SYNTHESIZING" || runeState === "DISTILLING") 
                                ? continuousOuter : outerBaseAngle;
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate((effOuterAngle * Math.PI) / 180);
            ctx.lineWidth = 1.0 * scale;
            ctx.strokeStyle = activeColor;
            ctx.lineCap = "butt";
            ctx.globalAlpha = (runeState === "LATENT") ? 0.25 : 0.75;

            var flankSweep = (74 * Math.PI) / 180;
            var flanks = [143 * Math.PI / 180, 323 * Math.PI / 180];
            for (var j = 0; j < flanks.length; j++) {
                ctx.beginPath();
                ctx.arc(0, 0, currentOuterRadius * scale, flanks[j], flanks[j] + flankSweep);
                ctx.stroke();
            }
            ctx.restore();

            ctx.restore();
        }
    }
}
