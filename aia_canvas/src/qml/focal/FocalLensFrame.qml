import QtQuick
import QtQuick.Controls
import ".."
import "../hud"
import "../bar"

Item {
    id: root
    objectName: "focalLensFrame"
    property bool active: false
    property real targetCenterY: lensContainer ? lensContainer.targetCenterY : Math.round((root.height - (lensContainer ? lensContainer.height : 0)) / 2)
    property string activeContext: ""
    property var turnHistory: []
    property string pendingStreamBuffer: ""
    property bool isStreamingActive: false
    property string pendingFinalText: ""
    property string engineState: {
        var convEngine = (typeof bridge !== "undefined" && bridge && bridge.conversation) ? bridge.conversation : (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.conversation ? canvasBridge.conversation : null);
        var s = (convEngine && convEngine.engineState !== undefined && convEngine.engineState !== "") ? convEngine.engineState : ((typeof bridge !== "undefined" && bridge && bridge.engineState !== undefined && bridge.engineState !== "") ? bridge.engineState : ((typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.engineState !== undefined && canvasBridge.engineState !== "") ? canvasBridge.engineState : "LATENT"));
        if (s === "STREAMING" || s === "WORKING" || s === "SYNTHESIZING") return "WORKING";
        if (s === "IDLE" || s === "LATENT") return "LATENT";
        if (s === "ERROR") return "OFFLINE";
        return s;
    }
    property var providerMeta: {
        var b = (typeof bridge !== "undefined" && bridge) ? bridge : ((typeof canvasBridge !== "undefined" && canvasBridge) ? canvasBridge : null);
        if (b && b.providerMetadata) return b.providerMetadata;
        var ce = b ? b.conversation : null;
        if (ce && ce.providerMetadata) return ce.providerMetadata;
        return { "id": "gemini_flash", "display_name": "Flash", "accent_color": "#38BDF8", "icon_glyph": "✦" };
    }

    anchors.fill: parent

    ListModel {
        id: conversationModel
    }

    Timer {
        id: streamDripTimer
        interval: 16 // 60fps cadence
        repeat: true
        running: root.pendingStreamBuffer.length > 0 || root.isStreamingActive
        onTriggered: {
            if (root.pendingStreamBuffer.length === 0) {
                if (!root.isStreamingActive) {
                    stop();
                    root.engineState = "LATENT";
                    if (conversationModel.count > 0 && root.pendingFinalText) {
                        var lastIdx = conversationModel.count - 1;
                        conversationModel.setProperty(lastIdx, "response", root.pendingFinalText);
                        root.pendingFinalText = "";
                    }
                    _syncTurnHistory();
                    slateListView.positionViewAtEnd();
                }
                return;
            }

            if (conversationModel.count === 0) return;

            // Dynamic drain rate: 2-3 chars normally, accelerate if queue backs up
            var burst = 2;
            if (root.pendingStreamBuffer.length > 80) {
                burst = 8;
            } else if (root.pendingStreamBuffer.length > 30) {
                burst = 4;
            }

            var slice = root.pendingStreamBuffer.substring(0, burst);
            root.pendingStreamBuffer = root.pendingStreamBuffer.substring(burst);

            var lastIdx = conversationModel.count - 1;
            var current = conversationModel.get(lastIdx).response || "";
            conversationModel.setProperty(lastIdx, "response", current + slice);
            slateListView.positionViewAtEnd();

            if (root.pendingStreamBuffer.length === 0 && !root.isStreamingActive) {
                stop();
                root.engineState = "LATENT";
                if (conversationModel.count > 0 && root.pendingFinalText) {
                    conversationModel.setProperty(lastIdx, "response", root.pendingFinalText);
                    root.pendingFinalText = "";
                }
                _syncTurnHistory();
            }
        }
    }

    MouseArea {
        id: backdropArea
        objectName: "lensBackdrop"
        anchors.fill: parent
        enabled: root.active || lensStateGroup.state === "opened"
        onClicked: root.close()
    }

    Rectangle {
        id: lensContainer
        objectName: "lensContainer"
        width: Math.min(1040, (parent && parent.width > 0) ? parent.width * 0.70 : 1040)
        height: Math.min(820, (parent && parent.height > 0) ? parent.height * 0.80 : 820)
        x: Math.round((root.width - width) / 2)
        property real targetCenterY: Math.round((root.height - height) / 2)
        y: targetCenterY
        
        scale: 0.88; opacity: 0.0; visible: false
        color: Theme.surfaceElevated; border.color: Theme.borderSubtle
        border.width: 1; radius: 12

        MouseArea {
            id: interiorAbsorber
            objectName: "interiorAbsorber"
            anchors.fill: parent
        }

        Rectangle {
            id: headerBar
            objectName: "headerBar"
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 52
            color: Theme.surfaceGlass
            topLeftRadius: 12
            topRightRadius: 12

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Theme.borderSubtle
            }

            Row {
                id: titleBreadcrumbRow
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: headerRightControls.verticalCenter
                anchors.right: headerRightControls.left
                anchors.rightMargin: 16
                spacing: 8

                Text {
                    text: "Aether — Conversation"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    color: Theme.accentCyan
                    opacity: 0.85
                }

                Text {
                    text: "—"
                    font.pixelSize: 12
                    color: Theme.textMuted
                    opacity: 0.5
                    visible: topicText.text.length > 0
                }

                Text {
                    id: topicText
                    text: root.activeContext && root.activeContext.length > 0 ? root.activeContext : ""
                    font.pixelSize: 12
                    font.italic: true
                    font.weight: Font.Normal
                    color: Theme.textMuted
                    elide: Text.ElideRight
                    width: Math.min(implicitWidth, parent.width - 200)
                }
            }

            Row {
                id: headerRightControls
                objectName: "headerRightControls"
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 14
                spacing: 8

                ProviderBadge {
                    id: modelIndicatorPill
                    objectName: "modelIndicatorPill"
                    anchors.verticalCenter: parent.verticalCenter
                    engineState: root.engineState
                    providerMeta: root.providerMeta
                    isConversationalMode: true
                    showDialogueOutput: true
                    showAscendAction: false
                }

                Rectangle {
                    id: pinBtn
                    objectName: "pinBtn"
                    width: 32; height: 32
                    anchors.verticalCenter: parent.verticalCenter
                    radius: 4
                    color: pinMouseArea.containsMouse ? Theme.surfaceHovered : "transparent"
                    border.color: pinMouseArea.containsMouse ? Theme.borderHover : "transparent"; border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "⚲"; font.pixelSize: 18
                        color: pinMouseArea.containsMouse ? Theme.accentCyan : Theme.textMuted
                    }

                    MouseArea {
                        id: pinMouseArea
                        anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof bridge !== "undefined" && bridge) bridge.pin_conversation(root.activeContext)
                            else if (typeof canvasBridge !== "undefined" && canvasBridge) canvasBridge.pin_conversation(root.activeContext)
                            root.close()
                        }
                    }
                }
            }
        }

        ScrollView {
            id: slateScrollView
            objectName: "slateScrollView"
            anchors.top: headerBar.bottom
            anchors.bottom: footerDock.top
            anchors.left: parent.left
            anchors.right: parent.right
            clip: true
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            ListView {
                id: slateListView
                objectName: "slateListView"
                width: parent.width
                topMargin: 16
                bottomMargin: 16
                model: conversationModel
                spacing: 16
                onCountChanged: { slateListView.positionViewAtEnd() }

                delegate: Item {
                    id: turnDelegate
                    width: slateListView.width
                    height: turnContentColumn.height + 24

                    readonly property string p: (typeof model !== "undefined" && model.prompt !== undefined) ? model.prompt : (typeof modelData !== "undefined" ? modelData.prompt : "")
                    readonly property string r: (typeof model !== "undefined" && model.response !== undefined) ? model.response : (typeof modelData !== "undefined" ? modelData.response : "")

                    visible: (turnDelegate.p && turnDelegate.p.trim().length > 0) || (turnDelegate.r && turnDelegate.r.trim().length > 0)

                    TextMetrics {
                        id: promptMetrics
                        font.pixelSize: 13
                        font.family: Theme.fontSans
                        text: (turnDelegate.p || "").replace(/^[\?\s]+/, "")
                    }

                    Column {
                        id: turnContentColumn
                        width: parent.width
                        spacing: 16

                        Column {
                            anchors.right: parent.right
                            anchors.rightMargin: 16
                            spacing: 4
                            visible: turnDelegate.p && turnDelegate.p.trim().length > 0

                            // External Right-Aligned Label
                            Text {
                                text: "User"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                color: Theme.accentCyan
                                opacity: 0.85
                                anchors.right: parent.right
                                anchors.rightMargin: 4
                            }

                            // User Message Bubble (contains ONLY the message)
                            Rectangle {
                                id: userBubble
                                anchors.right: parent.right
                                readonly property real maxAllowedWidth: (turnContentColumn ? turnContentColumn.width - 32 : parent.width - 32) * 0.60
                                width: Math.min(520, Math.min(maxAllowedWidth, Math.max(promptMetrics.boundingRect.width + 28, 60)))
                                height: promptText.implicitHeight + 18
                                radius: 12
                                color: Theme.chatBubbleUserBg
                                border.color: Theme.chatBubbleUserBorder
                                border.width: 1

                                Text {
                                    id: promptText
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 14
                                    text: promptMetrics.text
                                    font.pixelSize: 13
                                    font.family: Theme.fontSans
                                    color: Theme.textPrimary
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }

                        Column {
                            anchors.left: parent.left
                            anchors.leftMargin: 16
                            width: aetherBubble.width
                            spacing: 6
                            visible: turnDelegate.r && turnDelegate.r.trim().length > 0

                            // External Left-Aligned Label
                            Text {
                                text: "Aether"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                color: Theme.accentAI
                            }

                            // Aether Content Area in Glass Bubble
                            Rectangle {
                                id: aetherBubble
                                readonly property real maxAllowedWidth: turnContentColumn ? turnContentColumn.width - 32 : parent.width - 32
                                width: Math.min(720, Math.min(maxAllowedWidth, Math.max(100, (turnContentColumn ? turnContentColumn.width : parent.width) * 0.65)))
                                height: aetherText.implicitHeight + 24
                                radius: 12
                                color: Theme.chatBubbleAetherBg
                                border.color: Theme.chatBubbleAetherBorder
                                border.width: 1

                                Rectangle {
                                    id: accentBar
                                    width: 2
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    anchors.margins: 6
                                    color: Theme.accentAI
                                    radius: 1
                                }

                                Text {
                                    id: aetherText
                                    anchors.left: parent.left
                                    anchors.leftMargin: 16
                                    anchors.right: parent.right
                                    anchors.rightMargin: 14
                                    anchors.top: parent.top
                                    anchors.topMargin: 12
                                    text: turnDelegate.r || ""
                                    textFormat: Text.MarkdownText
                                    font.family: Theme.fontAiVoice
                                    font.weight: Font.Normal
                                    font.pixelSize: 13
                                    lineHeight: 1.45
                                    color: Theme.aiVoiceGlacial
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: footerDock
            objectName: "footerDock"
            height: 68
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            color: Theme.surfaceGlass
            bottomLeftRadius: 12
            bottomRightRadius: 12

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: Theme.borderSubtle
            }

            Rectangle {
                id: chatInputCapsule
                objectName: "chatInputCapsule"
                anchors.centerIn: parent
                width: parent.width - 32
                height: 42
                radius: 21
                color: Theme.surfaceHovered
                border.color: Theme.borderSubtle
                border.width: 1

                TextInput {
                    id: chatInput
                    objectName: "chatInput"
                    anchors.left: parent.left
                    anchors.leftMargin: 18
                    anchors.right: chatRadar.left
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.textPrimary
                    font.pixelSize: 13
                    font.family: Theme.fontSans
                    activeFocusOnTab: true
                    selectByMouse: true
                    clip: true

                    Text {
                        text: "Reply to Aether..."
                        color: Theme.textMuted
                        opacity: 0.6
                        visible: !parent.text && !parent.activeFocus
                        anchors.verticalCenter: parent.verticalCenter
                        font: parent.font
                    }

                    onAccepted: {
                        if (text.trim().length > 0) {
                            root.submitFollowUp(text.trim());
                            text = "";
                        }
                    }
                }

                AmbientRadarHUD {
                    id: chatRadar
                    objectName: "chatRadar"
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    compact: true
                    engineState: root.engineState
                }
            }
        }

        Item {
            id: resizeCorner
            objectName: "resizeCorner"
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: 24
            height: 24
            z: 100

            Item {
                id: resizeGrip
                objectName: "resizeGrip"
                anchors.fill: parent

                Rectangle {
                    width: 13
                    height: 1.5
                    rotation: -45
                    transformOrigin: Item.Center
                    x: 7; y: 15
                    color: (typeof Theme !== "undefined" && Theme.borderSubtle) ? Theme.borderSubtle : "#33FFFFFF"
                }

                Rectangle {
                    width: 7
                    height: 1.5
                    rotation: -45
                    transformOrigin: Item.Center
                    x: 14; y: 18
                    color: (typeof Theme !== "undefined" && Theme.borderSubtle) ? Theme.borderSubtle : "#33FFFFFF"
                }
            }

            MouseArea {
                id: resizeMouseArea
                objectName: "resizeMouseArea"
                anchors.fill: parent
                cursorShape: Qt.SizeFDiagCursor
                hoverEnabled: true

                property real startRootX: 0
                property real startRootY: 0
                property real startWidth: 0
                property real startHeight: 0

                onPressed: function(mouse) {
                    var pt = mapToItem(root, mouse.x, mouse.y);
                    startRootX = pt.x;
                    startRootY = pt.y;
                    startWidth = lensContainer.width;
                    startHeight = lensContainer.height;
                }

                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var pt = mapToItem(root, mouse.x, mouse.y);
                        var deltaX = pt.x - startRootX;
                        var deltaY = pt.y - startRootY;
                        var pw = (lensContainer.parent && lensContainer.parent.width > 0) ? lensContainer.parent.width : (root.width > 0 ? root.width : 1600);
                        var ph = (lensContainer.parent && lensContainer.parent.height > 0) ? lensContainer.parent.height : (root.height > 0 ? root.height : 1200);
                        var minW = 640;
                        var maxW = pw * 0.94;
                        var minH = 460;
                        var maxH = ph * 0.92;

                        lensContainer.width = Math.max(minW, Math.min(maxW, startWidth + deltaX));
                        lensContainer.height = Math.max(minH, Math.min(maxH, startHeight + deltaY));
                    }
                }
            }
        }

        StateGroup {
            id: lensStateGroup
            states: [
                State { name: "opened"; when: root.active; PropertyChanges { target: lensContainer; scale: 1.0; opacity: 1.0; y: lensContainer.targetCenterY; visible: true } },
                State { name: "closed"; when: !root.active; PropertyChanges { target: lensContainer; scale: 0.88; opacity: 0.0; y: root.targetCenterY + 32; visible: false } }
            ]
            transitions: [
                Transition {
                    from: "closed"; to: "opened"
                    SequentialAnimation {
                        PropertyAction { target: lensContainer; property: "visible"; value: true }
                        ParallelAnimation {
                            NumberAnimation { target: lensContainer; property: "opacity"; duration: Theme.animLensOpenDuration; easing.type: Theme.animLensOpenEasing }
                            NumberAnimation { target: lensContainer; property: "scale"; duration: Theme.animLensOpenDuration; easing.type: Theme.animLensOpenEasing }
                            NumberAnimation { target: lensContainer; property: "y"; duration: Theme.animLensOpenDuration; easing.type: Theme.animLensOpenEasing }
                        }
                    }
                },
                Transition {
                    from: "opened"; to: "closed"
                    SequentialAnimation {
                        ParallelAnimation {
                            NumberAnimation { target: lensContainer; property: "opacity"; duration: Theme.animLensCloseDuration; easing.type: Theme.animLensCloseEasing }
                            NumberAnimation { target: lensContainer; property: "scale"; duration: Theme.animLensCloseDuration; easing.type: Theme.animLensCloseEasing }
                            NumberAnimation { target: lensContainer; property: "y"; duration: Theme.animLensCloseDuration; easing.type: Theme.animLensCloseEasing }
                        }
                        PropertyAction { target: lensContainer; property: "visible"; value: false }
                    }
                }
            ]
        }
    }

    Connections {
        target: (typeof bridge !== "undefined" && bridge && bridge.conversation) ? bridge.conversation : (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.conversation ? canvasBridge.conversation : ((typeof bridge !== "undefined" && bridge) ? bridge : ((typeof canvasBridge !== "undefined" && canvasBridge) ? canvasBridge : null)))
        ignoreUnknownSignals: true
        function onEngineStateChanged(state) {
            if (state === "STREAMING" || state === "WORKING" || state === "SYNTHESIZING") {
                root.engineState = "WORKING";
            } else if (state === "IDLE" || state === "LATENT") {
                if (root.pendingStreamBuffer.length === 0) {
                    root.engineState = "LATENT";
                }
            } else if (state === "ERROR") {
                root.engineState = "OFFLINE";
            } else {
                root.engineState = state;
            }
        }
        function onTokenReceived(chunk) {
            root.isStreamingActive = true;
            root.engineState = "WORKING";
            root.pendingStreamBuffer += chunk;
            if (!streamDripTimer.running) streamDripTimer.start();
        }
        function onResponseFinished(fullText) {
            root.isStreamingActive = false;
            if (fullText) {
                root.pendingFinalText = fullText;
            }
            if (root.pendingStreamBuffer.length === 0) {
                root.engineState = "LATENT";
                if (conversationModel.count > 0 && root.pendingFinalText) {
                    var lastIdx = conversationModel.count - 1;
                    conversationModel.setProperty(lastIdx, "response", root.pendingFinalText);
                    root.pendingFinalText = "";
                }
                _syncTurnHistory();
                Qt.callLater(function() { slateListView.positionViewAtEnd(); });
            }
        }
    }

    function _syncTurnHistory() {
        var arr = [];
        for (var i = 0; i < conversationModel.count; i++) {
            var item = conversationModel.get(i);
            arr.push({
                "prompt": item.prompt || "",
                "response": item.response || ""
            });
        }
        root.turnHistory = arr;
    }

    function open(context, turns) {
        if (root.active && conversationModel.count > 0) {
            return;
        }
        root.pendingStreamBuffer = "";
        root.pendingFinalText = "";
        root.isStreamingActive = false;
        root.activeContext = context || "";
        conversationModel.clear();
        if (turns && turns.length > 0) {
            for (var i = 0; i < turns.length; i++) {
                conversationModel.append({
                    "prompt": turns[i].prompt || "",
                    "response": turns[i].response || ""
                });
            }
        }
        root.turnHistory = turns || [];
        root.active = true;
    }

    function close() { root.active = false; }

    function submitFollowUp(query) {
        if (!query || query.trim().length === 0) return;
        var q = query.trim();
        root.pendingStreamBuffer = "";
        root.pendingFinalText = "";
        root.isStreamingActive = false;
        conversationModel.append({ "prompt": q, "response": "" });
        _syncTurnHistory();
        root.engineState = "WORKING";
        Qt.callLater(function() { slateListView.positionViewAtEnd(); });

        var b = (typeof bridge !== "undefined" && bridge) ? bridge : ((typeof canvasBridge !== "undefined" && canvasBridge) ? canvasBridge : null);
        if (b) {
            if (typeof b.ask === "function") {
                b.ask(q, root.activeContext);
            } else if (b.conversation && typeof b.conversation.ask === "function") {
                b.conversation.ask(q, root.activeContext);
            } else if (b.conversation && typeof b.conversation.stream_prompt === "function") {
                b.conversation.stream_prompt(q, root.activeContext);
            }
        }
    }
}