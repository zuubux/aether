import QtQuick
import QtQuick.Controls
import QtMultimedia
import ".."

FocusScope {
    id: root
    focus: true

    readonly property real screenHeight: (typeof rootWindow !== "undefined" && rootWindow && rootWindow.height > 0) ? rootWindow.height : (Screen.height > 0 ? Screen.height : 1080)
    readonly property real screenWidth: (typeof rootWindow !== "undefined" && rootWindow && rootWindow.width > 0) ? rootWindow.width : (Screen.width > 0 ? Screen.width : 1920)

    readonly property real targetSlateWidth: Math.min(screenWidth * 0.80, 960.0)
    readonly property real targetSlateHeight: Math.min(screenHeight * 0.70, 540.0)

    width: targetSlateWidth
    height: targetSlateHeight

    property int nodeId: 0
    property string filePath: ""
    property string fileName: filePath ? filePath.split('/').pop() : ""
    property string displayTitle: fileName ? fileName.replace(/\.[^/.]+$/, "") : ""
    property string sizeFormatted: "0 KB"
    property string archetype: "VIDEO"
    property color accentColor: Theme.badgeVideo
    property bool isSelected: false

    property var bridge: null
    property Item viewportContainer: null
    property string snippet: ""

    property string posterUrl: ""
    property bool isFillCrop: false

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

    function loadPoster() {
        var b = getBridge();
        if (b && filePath) {
            posterUrl = b.get_video_poster(filePath);
        }
    }

    onFilePathChanged: {
        loadPoster();
    }

    onIsSelectedChanged: {
        if (!isSelected) {
            player.stop();
        }
    }

    Component.onCompleted: {
        root.forceActiveFocus();
        loadPoster();
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
        videoOutput: videoOut
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
        id: container
        anchors.fill: parent
        radius: 12
        color: Theme.surfaceBackground
        border.color: root.isSelected ? Theme.borderHover : Theme.surfaceBorder
        border.width: 1
        antialiasing: true

        MouseArea {
            id: videoHoverArea
            anchors.fill: parent
            hoverEnabled: true

            VideoOutput {
                id: videoOut
                anchors.fill: parent
                fillMode: root.isFillCrop ? VideoOutput.PreserveAspectCrop : VideoOutput.PreserveAspectFit
            }

            Image {
                id: posterFallback
                anchors.fill: parent
                fillMode: Image.PreserveAspectFit
                source: root.posterUrl
                visible: opacity > 0.01
                opacity: (player.playbackState === MediaPlayer.StoppedState && player.mediaStatus !== MediaPlayer.BufferedMedia) ? 1.0 : 0.0

                Behavior on opacity {
                    NumberAnimation { duration: 250 }
                }
            }

            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 50
                color: Qt.rgba(11 / 255, 15 / 255, 25 / 255, 0.85)
                opacity: (videoHoverArea.containsMouse || player.playbackState !== MediaPlayer.PlayingState) ? 1.0 : 0.0
                z: 10

                Behavior on opacity {
                    NumberAnimation { duration: 200 }
                }

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
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
                            text: "VIDEO"
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
                            text: root.displayTitle || root.fileName || "Video Track"
                            color: Theme.textPrimary
                            font.family: Theme.fontSans
                            font.pixelSize: 14
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
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 52
                color: Qt.rgba(11 / 255, 15 / 255, 25 / 255, 0.88)
                opacity: (videoHoverArea.containsMouse || player.playbackState !== MediaPlayer.PlayingState) ? 1.0 : 0.0
                z: 10

                Behavior on opacity {
                    NumberAnimation { duration: 200 }
                }

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
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
                    Slider {
                        id: positionSlider
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 340
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

                    Rectangle {
                        width: 32
                        height: 32
                        radius: 6
                        color: root.isFillCrop ? Theme.accentFocus : Theme.surfaceButton
                        border.color: Theme.borderSubtle
                        border.width: 1
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "⛶"
                            color: root.isFillCrop ? "#0B0F19" : Theme.textPrimary
                            font.pixelSize: 14
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.isFillCrop = !root.isFillCrop
                        }
                    }
                    }
                }
            }
        }
    }
}