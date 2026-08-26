import QtQuick
import QtQuick.Controls
import QtMultimedia
import ".."

FocusScope {
    id: root
    focus: true

    readonly property real screenHeight: (typeof rootWindow !== "undefined" && rootWindow && rootWindow.height > 0) ? rootWindow.height : (Screen.height > 0 ? Screen.height : 1080)
    readonly property real screenWidth: (typeof rootWindow !== "undefined" && rootWindow && rootWindow.width > 0) ? rootWindow.width : (Screen.width > 0 ? Screen.width : 1920)

    readonly property real targetSlateWidth: Math.min(screenWidth * 0.75, 720.0)
    readonly property real targetSlateHeight: 380.0

    width: targetSlateWidth
    height: targetSlateHeight

    property int nodeId: 0
    property string filePath: ""
    property string fileName: filePath ? filePath.split('/').pop() : ""
    property string displayTitle: fileName ? fileName.replace(/\.[^/.]+$/, "") : ""
    property string sizeFormatted: "0 KB"
    property string archetype: "AUDIO"
    property color accentColor: Theme.badgeAudio
    property bool isSelected: false

    property var bridge: null
    property Item viewportContainer: null
    property string snippet: ""

    property var waveformData: []

    function getBridge() {
        if (root.bridge) return root.bridge;
        if (typeof canvasBridge !== "undefined" && canvasBridge) return canvasBridge;
        return null;
    }

    readonly property string mediaUrl: root.filePath ? (getBridge() ? getBridge().resolve_media_url(root.filePath) : "file://" + root.filePath) : ""

    function formatTime(ms) {
        if (!ms || ms <= 0 || isNaN(ms)) return "00:00";
        var totalSec = Math.floor(ms / 1000);
        var hrs = Math.floor(totalSec / 3600);
        var mins = Math.floor((totalSec % 3600) / 60);
        var secs = totalSec % 60;
        var pM = mins < 10 ? "0" + mins : "" + mins;
        var pS = secs < 10 ? "0" + secs : "" + secs;
        if (hrs > 0) {
            var pH = hrs < 10 ? "0" + hrs : "" + hrs;
            return pH + ":" + pM + ":" + pS;
        }
        return pM + ":" + pS;
    }

    function loadWaveform() {
        var b = getBridge();
        if (b && filePath) {
            var wf = b.get_audio_waveform(filePath);
            if (wf && wf.length > 0) {
                waveformData = wf;
            } else {
                waveformData = [];
            }
        }
    }

    onFilePathChanged: {
        loadWaveform();
    }

    onIsSelectedChanged: {
        if (!isSelected) {
            player.stop();
        }
    }

    Component.onCompleted: {
        root.forceActiveFocus();
        loadWaveform();
        var b = getBridge();
        if (b) {
            b.set_workbench_dimensions(targetSlateWidth, targetSlateHeight);
        }
    }

    Component.onDestruction: {
        player.stop();
    }

    MediaPlayer {
        id: player
        audioOutput: audioOut
        source: root.mediaUrl
    }

    AudioOutput {
        id: audioOut
        volume: 0.8
    }

    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Space) {
            if (player.playbackState === MediaPlayer.PlayingState) {
                player.pause();
            } else {
                player.play();
            }
            event.accepted = true;
        } else if (event.key === Qt.Key_Left) {
            player.position = Math.max(0, player.position - 5000);
            event.accepted = true;
        } else if (event.key === Qt.Key_Right) {
            player.position = Math.min(player.duration, player.position + 5000);
            event.accepted = true;
        } else if (event.key === Qt.Key_M) {
            audioOut.muted = !audioOut.muted;
            event.accepted = true;
        } else {
            event.accepted = false;
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: 12
        color: Theme.surfaceBackground
        border.color: root.isSelected ? Theme.borderHover : Theme.surfaceBorder
        border.width: 1
        antialiasing: true

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 16

            Row {
                width: parent.width
                height: 32
                spacing: 12

                Rectangle {
                    width: Math.max(48, badgeText.implicitWidth + 12)
                    height: 24
                    radius: 4
                    color: root.accentColor
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        id: badgeText
                        anchors.centerIn: parent
                        text: "AUDIO"
                        color: "#0B0F19"
                        font.family: Theme.fontCode
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 120

                    Text {
                        text: root.displayTitle || root.fileName || "Audio Track"
                        color: Theme.textPrimary
                        font.family: Theme.fontSans
                        font.pixelSize: 15
                        font.bold: true
                        elide: Text.ElideRight
                        width: parent.width
                    }

                    Text {
                        text: root.sizeFormatted + (root.snippet ? "  •  " + root.snippet.replace(/<[^>]*>/g, '') : "")
                        color: Theme.textMuted
                        font.family: Theme.fontCode
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        width: parent.width
                    }
                }
            }

            Rectangle {
                id: waveformContainer
                width: parent.width
                height: 180
                radius: 8
                color: Qt.rgba(22 / 255, 28 / 255, 40 / 255, 0.8)
                border.color: Theme.borderSubtle
                border.width: 1

                readonly property real progressRatio: (player.duration > 0) ? Math.min(1.0, Math.max(0.0, player.position / player.duration)) : 0.0

                Row {
                    id: barsRow
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    anchors.topMargin: 16
                    anchors.bottomMargin: 16
                    spacing: Math.max(1, (width - (64 * 3)) / 63)

                    Repeater {
                        model: 64

                        Item {
                            id: barWrapper
                            width: 3
                            height: barsRow.height

                            readonly property real amp: (root.waveformData && root.waveformData.length > index) ? root.waveformData[index] : 0.05
                            readonly property real barHeight: Math.max(4, amp * parent.height)
                            readonly property bool isPlayed: (index / 64.0) <= waveformContainer.progressRatio

                            Rectangle {
                                anchors.centerIn: parent
                                width: parent.width
                                height: barWrapper.barHeight
                                radius: 1.5
                                color: barWrapper.isPlayed ? Theme.accentFocus : Qt.rgba(148 / 255, 163 / 255, 184 / 255, 0.25)

                                Behavior on color {
                                    ColorAnimation { duration: 100 }
                                }
                            }
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor

                    function seekToMouse(mouseX) {
                        if (player.duration > 0) {
                            var frac = Math.max(0.0, Math.min(1.0, mouseX / width));
                            player.position = Math.round(frac * player.duration);
                        }
                    }

                    onClicked: (mouse) => seekToMouse(mouse.x)
                    onPositionChanged: (mouse) => {
                        if (pressed) seekToMouse(mouse.x);
                    }
                }
            }

            // Transport Control Bar
            Row {
                width: parent.width
                height: 40
                spacing: 16

                Rectangle {
                    width: 36
                    height: 36
                    radius: 18
                    color: playBtnArea.containsMouse ? Theme.accentFocus : Theme.surfaceButton
                    border.color: Theme.accentFocus
                    border.width: 1
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: player.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
                        color: playBtnArea.containsMouse ? "#0B0F19" : Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }

                    MouseArea {
                        id: playBtnArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (player.playbackState === MediaPlayer.PlayingState) {
                                player.pause();
                            } else {
                                player.play();
                            }
                        }
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: formatTime(player.position) + " / " + formatTime(player.duration)
                    color: Theme.textPrimary
                    font.family: Theme.fontCode
                    font.pixelSize: 12
                    font.bold: true
                    width: 120
                }

                Slider {
                    id: positionSlider
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 280
                    from: 0
                    to: Math.max(1, player.duration)
                    value: player.position
                    live: true

                    onMoved: {
                        player.position = positionSlider.value;
                    }

                    background: Rectangle {
                        x: positionSlider.leftPadding
                        y: positionSlider.topPadding + positionSlider.availableHeight / 2 - height / 2
                        implicitWidth: 200
                        implicitHeight: 4
                        width: positionSlider.availableWidth
                        height: implicitHeight
                        radius: 2
                        color: Qt.rgba(255, 255, 255, 0.1)

                        Rectangle {
                            width: positionSlider.visualPosition * parent.width
                            height: parent.height
                            color: Theme.accentFocus
                            radius: 2
                        }
                    }

                    handle: Rectangle {
                        x: positionSlider.leftPadding + positionSlider.visualPosition * (positionSlider.availableWidth - width)
                        y: positionSlider.topPadding + positionSlider.availableHeight / 2 - height / 2
                        implicitWidth: 12
                        implicitHeight: 12
                        radius: 6
                        color: positionSlider.pressed ? Theme.accentCyan : Theme.accentFocus
                    }
                }

                Rectangle {
                    width: 32
                    height: 32
                    radius: 6
                    color: Theme.surfaceButton
                    border.color: Theme.borderSubtle
                    border.width: 1
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: audioOut.muted ? "🔇" : "🔊"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: audioOut.muted = !audioOut.muted
                    }
                }
            }
        }
    }
}