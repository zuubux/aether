import QtQuick
import QtQuick.Controls
import ".."

/**
 * OmniBar.qml
 * Central neural HUD combining low-latency fuzzy search, shell execution, and conversational AI.
 */
Item {
    id: root

    property bool active: false
    property Item searchShelf: null
    property var resultsList: []
    property int currentRibbonIndex: -1
    property real lastKeyPressTime: 0
    property real typingCadenceMs: 0.0
    property bool shelfExpanded: false
    property var tabCompletions: []
    property int tabCompletionIndex: -1
    property string tabLastQuery: ""
    property var shellHistory: []
    property int shellHistoryIndex: -1

    function getListLength(lst) {
        if (!lst) return 0;
        if (typeof lst.length === "number") return lst.length;
        if (typeof lst.count === "number") return lst.count;
        try {
            return Array.from(lst).length;
        } catch (e) {
            return 0;
        }
    }

    property string activeProvider: ""
    property string activeProviderName: ""
    property string activeProviderModel: ""
    property string lastExecutedPrompt: ""
    property string engineState: {
        var convEngine = (typeof bridge !== "undefined" && bridge && bridge.conversation) ? bridge.conversation : (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.conversation ? canvasBridge.conversation : null);
        if (convEngine && convEngine.engineState !== undefined && convEngine.engineState !== "") return convEngine.engineState;
        if (typeof bridge !== "undefined" && bridge && bridge.engineState !== undefined && bridge.engineState !== "") return bridge.engineState;
        if (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.engineState !== undefined && canvasBridge.engineState !== "") return canvasBridge.engineState;
        return "IDLE";
    }

    readonly property var providerMeta: {
        var b = (typeof bridge !== "undefined" && bridge) ? bridge : ((typeof canvasBridge !== "undefined" && canvasBridge) ? canvasBridge : null);
        if (b && b.providerMetadata) return b.providerMetadata;
        var ce = b ? b.conversation : null;
        if (ce && ce.providerMetadata) return ce.providerMetadata;
        return { "id": "gemini_flash", "display_name": "Flash", "accent_color": "#38BDF8", "icon_glyph": "✦" };
    }

    readonly property string effectiveProvider: activeProvider || (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.activeProvider ? canvasBridge.activeProvider : "")
    readonly property string effectiveProviderName: activeProviderName || (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.activeProviderName ? canvasBridge.activeProviderName : "Gemini")
    readonly property string effectiveProviderModel: activeProviderModel || (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.activeProviderModel ? canvasBridge.activeProviderModel : "gemini-2.5-flash")

    readonly property int textLength: inputCapsule.text.length
    readonly property string currentQuery: inputCapsule.text
    readonly property alias resultsModel: ribbonContainer.resultsModel
    readonly property int resultsCount: getListLength(resultsList)
    readonly property string modePrefix: inputCapsule.text ? (inputCapsule.text.trim().startsWith(">") ? ">" : (inputCapsule.text.trim().startsWith("?") ? "?" : (inputCapsule.text.trim().startsWith("/") ? "/" : ""))) : ""
    readonly property bool isShellMode: modePrefix === ">"
    readonly property bool isConversationalMode: modePrefix === "?"

    onModePrefixChanged: {
        resultsList = [];
        currentRibbonIndex = -1;
        shelfExpanded = false;
        shellHistoryIndex = -1;
        lastExecutedPrompt = "";
        if (typeof aiAutoSendTimer !== "undefined" && aiAutoSendTimer) aiAutoSendTimer.stop();
        if (typeof debounceTimer !== "undefined" && debounceTimer) debounceTimer.stop();
    }

    readonly property var systemStatusItem: {
        if (!isShellMode) return null;
        if (!resultsList || resultsList.length === 0) return null;
        for (var i = resultsList.length - 1; i >= 0; i--) {
            if (resultsList[i] && resultsList[i].stream === "system") {
                return resultsList[i];
            }
        }
        return null;
    }

    readonly property var shellOutputModel: {
        if (!isShellMode || !resultsList) return [];
        var ret = [];
        for (var i = 0; i < resultsList.length; i++) {
            if (resultsList[i] && resultsList[i].stream !== "system") {
                ret.push(resultsList[i]);
            }
        }
        return ret;
    }
    
    readonly property string dialogueFullText: {
        if (!isConversationalMode || !resultsList || resultsList.length === 0) return "";
        var parts = [];
        for (var i = 0; i < resultsList.length; i++) {
            var item = resultsList[i];
            if (!item) continue;
            if (typeof item === "object" && (item.stream || item.exit_code !== undefined || item.is_tui_warning)) continue;
            if (typeof item === "object" && (item.id === "llm_query" || item.category === "llm")) continue;
            if (typeof item === "string") {
                if (item.startsWith("Ask AI:")) continue;
                parts.push(item);
            } else if (typeof item === "object") {
                var t = item.title !== undefined ? item.title : (item.content !== undefined ? item.content : (item.text !== undefined ? item.text : (item.line !== undefined ? item.line : "")));
                if (typeof t === "string" && t.startsWith("Ask AI:")) continue;
                parts.push(t);
            }
        }
        return parts.join("");
    }

    readonly property bool showShellOutput: root.active && root.isShellMode && root.resultsCount > 0
    readonly property real maxShellOutputHeight: Math.min(460, parent ? parent.height * 0.55 : 460)
    readonly property real shellContentCalculatedHeight: 16 + (barShell.shellDrawer && barShell.shellDrawer.shellListView ? barShell.shellDrawer.shellListView.contentHeight : 0) + (systemStatusItem ? 26 : 0) + 12
    readonly property real shellDrawerHeight: showShellOutput ? Math.min(maxShellOutputHeight, Math.max(48, shellContentCalculatedHeight)) : 0

    readonly property bool showDialogueOutput: root.active && root.isConversationalMode && root.resultsCount > 0
    readonly property real maxDialogueOutputHeight: Math.min(460, parent ? parent.height * 0.55 : 460)
    readonly property real calculatedTextHeight: (barShell.dialogueDrawer && barShell.dialogueDrawer.dialogueTextDummy) ? barShell.dialogueDrawer.dialogueTextDummy.implicitHeight : 60
    readonly property real dialogueContentCalculatedHeight: calculatedTextHeight + 58
    readonly property real dialogueDrawerHeight: showDialogueOutput ? Math.min(maxDialogueOutputHeight, Math.max(64, dialogueContentCalculatedHeight)) : 0

    readonly property bool showOutputDrawer: showShellOutput || showDialogueOutput
    readonly property real outputDrawerHeight: root.isShellMode ? shellDrawerHeight : (root.isConversationalMode ? dialogueDrawerHeight : 0)

    signal querySubmitted(string text)
    signal dismissed()
    signal cancelQuery()

    width: (root.isShellMode || root.isConversationalMode) ? Math.min(860, parent ? parent.width * 0.82 : 860) : Math.min(680, parent ? parent.width * 0.85 : 680)
    height: outputDrawerHeight + (showOutputDrawer ? 1 : 0) + 48
    anchors.bottom: parent ? parent.bottom : undefined
    anchors.bottomMargin: 36
    anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
    opacity: active ? 1.0 : 0.0
    visible: opacity > 0.01

    Behavior on width { NumberAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing } }
    Behavior on height { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
    Behavior on opacity { NumberAnimation { duration: Theme.animDuration; easing.type: Theme.animEasing } }

    function open() { active = true; inputCapsule.inputField.forceActiveFocus(); }
    function dismiss() {
        active = false; inputCapsule.text = ""; inputCapsule.inputField.focus = false;
        resultsList = []; currentRibbonIndex = -1; shelfExpanded = false; shellHistoryIndex = -1;
        if (typeof aiAutoSendTimer !== "undefined" && aiAutoSendTimer) aiAutoSendTimer.stop();
        if (searchShelf) searchShelf.isSearchActiveExplicit = false;
        if (root.parent) root.parent.forceActiveFocus();
        dismissed();
    }

    function clearTextAndCancel() {
        inputCapsule.text = ""; resultsList = []; currentRibbonIndex = -1; shelfExpanded = false; shellHistoryIndex = -1;
        if (typeof aiAutoSendTimer !== "undefined" && aiAutoSendTimer) aiAutoSendTimer.stop();
        if (searchShelf) searchShelf.isSearchActiveExplicit = false;
        cancelQuery();
        if (typeof searchController !== "undefined" && searchController) searchController.clear_search();
        else if (canvasBridge) canvasBridge.search.clear_search();
    }

    function dispatchCurrentQuery() {
        var txt = inputCapsule.text.trim();
        var focusedId = (canvasBridge && canvasBridge.selectedNodeId > 0) ? String(canvasBridge.selectedNodeId) : "";
        if (typeof searchController !== "undefined" && searchController) {
            searchController.dispatch_omni(txt, typingCadenceMs, focusedId, []);
        } else if (canvasBridge && canvasBridge.search_ctrl) {
            canvasBridge.search_ctrl.dispatch_omni(txt, typingCadenceMs, focusedId, []);
        } else if (canvasBridge) {
            canvasBridge.search.submit_query(txt);
        }
    }

    function submitShellCommand() {
        var rawText = inputCapsule.text.trim();
        var cmd = rawText.startsWith(">") ? rawText.substring(1).trim() : rawText;
        if (cmd.length > 0) {
            dispatchCurrentQuery();

            var hist = shellHistory ? shellHistory.slice() : [];
            hist.push(rawText);
            shellHistory = hist;
            shellHistoryIndex = -1;

            inputCapsule.text = "> " + cmd;
            inputCapsule.inputField.select(2, inputCapsule.text.length);
        }
    }

    function submitConversationalQuery() {
        if (typeof aiAutoSendTimer !== "undefined" && aiAutoSendTimer) aiAutoSendTimer.stop();
        var rawText = inputCapsule.text.trim();
        if (rawText.length > 0) {
            if (rawText === root.lastExecutedPrompt && root.resultsList && root.resultsList.length > 0) return;
            root.lastExecutedPrompt = rawText;
            root.resultsList = [];
            var convEngine = (typeof bridge !== "undefined" && bridge && bridge.conversation) ? bridge.conversation : (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.conversation ? canvasBridge.conversation : null);
            if (convEngine && typeof convEngine.stream_prompt === "function") {
                convEngine.stream_prompt(rawText);
            } else {
                dispatchCurrentQuery();
            }
            querySubmitted(rawText);
        }
    }

    function handleShellTabCompletion() {
        var completionsLen = getListLength(tabCompletions);
        if (tabCompletions && completionsLen > 0 && inputCapsule.text === tabLastQuery) {
            tabCompletionIndex = (tabCompletionIndex + 1) % completionsLen;
            inputCapsule.text = tabCompletions[tabCompletionIndex];
            tabLastQuery = inputCapsule.text;
            inputCapsule.cursorPosition = inputCapsule.text.length;
            return;
        }

        var curPos = inputCapsule.cursorPosition;
        var matches = [];
        if (typeof canvasBridge !== "undefined" && canvasBridge) {
            matches = canvasBridge.get_completions(inputCapsule.text, curPos);
        }

        var matchesLen = getListLength(matches);
        if (!matches || matchesLen === 0) {
            tabCompletions = [];
            tabCompletionIndex = -1;
            tabLastQuery = "";
            return;
        }

        if (matchesLen === 1) {
            inputCapsule.text = matches[0];
            inputCapsule.cursorPosition = inputCapsule.text.length;
            tabCompletions = matches;
            tabCompletionIndex = 0;
            tabLastQuery = inputCapsule.text;
            return;
        }

        var lcp = matches[0];
        for (var i = 1; i < matchesLen; i++) {
            var m = matches[i];
            var j = 0;
            while (j < lcp.length && j < m.length && lcp.charAt(j) === m.charAt(j)) {
                j++;
            }
            lcp = lcp.substring(0, j);
        }

        if (lcp.length > inputCapsule.text.length) {
            inputCapsule.text = lcp;
            inputCapsule.cursorPosition = inputCapsule.text.length;
            tabCompletions = matches;
            tabCompletionIndex = -1;
            tabLastQuery = inputCapsule.text;
        } else {
            tabCompletionIndex = 0;
            inputCapsule.text = matches[0];
            inputCapsule.cursorPosition = inputCapsule.text.length;
            tabCompletions = matches;
            tabLastQuery = inputCapsule.text;
        }
    }

    function selectCurrentRibbonItem() {
        var len = getListLength(root.resultsList);
        if (root.currentRibbonIndex >= 0 && len > root.currentRibbonIndex) {
            var item = root.resultsList[root.currentRibbonIndex];
            var rawId = item.node_id !== undefined ? item.node_id : item.id;
            var nId = parseInt(rawId);
            if (!isNaN(nId) && nId > 0) {
                var vp = searchShelf ? searchShelf.viewport : (typeof canvasViewport !== "undefined" ? canvasViewport : null);
                if (vp) {
                    vp.isCameraCached = false;
                    if (typeof vp.steerCameraToNode === "function") {
                        vp.steerCameraToNode(nId, true);
                    }
                }
                if (canvasBridge) {
                    canvasBridge.node.select_node(nId);
                    canvasBridge.search.clear_search();
                }
                if (searchShelf) {
                    searchShelf.isSearchActiveExplicit = false;
                }
            }
            root.dismiss();
        }
    }

    onCurrentRibbonIndexChanged: {
        if (currentRibbonIndex >= 0) {
            if (resultsList && currentRibbonIndex < resultsList.length) {
                var item = resultsList[currentRibbonIndex];
                var rawId = item.node_id !== undefined ? item.node_id : item.id;
                var nId = parseInt(rawId);
                if (!isNaN(nId) && nId > 0) {
                    var vp = searchShelf ? searchShelf.viewport : (typeof canvasViewport !== "undefined" ? canvasViewport : null);
                    if (vp && typeof vp.steerCameraToNode === "function") {
                        vp.steerCameraToNode(nId);
                    }
                }
            }
        }
    }

    Connections {
        target: (typeof searchController !== "undefined" && searchController) ? searchController : ((typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.search_ctrl) ? canvasBridge.search_ctrl : null)
        ignoreUnknownSignals: true
        function onOmniResultsReceived(results) {
            root.resultsList = results || [];
            root.currentRibbonIndex = root.resultsList.length > 0 ? 0 : -1;
        }
    }

    SearchSuggestionRibbon {
        id: ribbonContainer
        objectName: "ribbonContainer"
        anchors.bottom: barShell.top
        anchors.bottomMargin: 14
        anchors.left: parent.left
        anchors.right: parent.right
        
        active: root.active
        isShellMode: root.isShellMode
        isConversationalMode: root.isConversationalMode
        shelfExpanded: root.shelfExpanded
        resultsList: root.resultsList
        currentRibbonIndex: root.currentRibbonIndex
        
        onRibbonItemHovered: function(index) {
            root.currentRibbonIndex = index;
        }
        onRibbonItemClicked: function(index) {
            root.currentRibbonIndex = index;
            root.selectCurrentRibbonItem();
        }
        onSelectCurrentRibbonItem: {
            root.selectCurrentRibbonItem();
        }
    }

    Rectangle {
        id: barShell
        objectName: "barShell"
        anchors.fill: parent
        radius: 12
        color: Theme.surfaceGlass
        border.width: 1
        border.color: root.isConversationalMode ? Theme.accentAI : (root.isShellMode ? Theme.accentShell : Theme.borderSubtle)
        readonly property color borderColor: border.color
        Behavior on border.color { ColorAnimation { duration: 200 } }

        property alias shellDrawer: shellDrawer
        property alias dialogueDrawer: dialogueDrawer

        Item {
            id: barShellViewport
            objectName: "barShellViewport"
            anchors.fill: parent
            anchors.margins: 1
            clip: true

            Column {
                anchors.fill: parent

                ShellOutputDrawer {
                    id: shellDrawer
                    objectName: "shellDrawer"
                    width: parent.width
                    height: root.shellDrawerHeight
                    showShellOutput: root.showShellOutput
                    shellOutputModel: root.shellOutputModel
                    systemStatusItem: root.systemStatusItem
                }

                DialogueDrawer {
                    id: dialogueDrawer
                    objectName: "dialogueDrawer"
                    width: parent.width
                    height: root.dialogueDrawerHeight
                    showDialogueOutput: root.showDialogueOutput
                    dialogueFullText: root.dialogueFullText
                    engineState: root.engineState
                    providerMeta: root.providerMeta
                    isConversationalMode: root.isConversationalMode
                }

                Rectangle {
                    id: internalDivider
                    objectName: "internalDivider"
                    width: parent.width
                    height: 1
                    color: Theme.borderSeamSubtle
                    visible: root.showOutputDrawer
                }

                OmniInputCapsule {
                    id: inputCapsule
                    objectName: "inputCapsule"
                    width: parent.width
                    height: 48
                    
                    modePrefix: root.modePrefix
                    effectiveProvider: root.effectiveProvider
                    borderColor: barShell.borderColor
                    active: root.active
                    isConversationalMode: root.isConversationalMode
                    isShellMode: root.isShellMode
                    shelfExpanded: root.shelfExpanded
                    
                    onInputTextChanged: {
                        if (inputCapsule.text !== root.tabLastQuery) {
                            root.tabCompletions = [];
                            root.tabCompletionIndex = -1;
                            root.tabLastQuery = "";
                        }
                        if (root.active && inputCapsule.text.length > 0) {
                            var now = Date.now();
                            if (root.lastKeyPressTime > 0) root.typingCadenceMs = now - root.lastKeyPressTime;
                            root.lastKeyPressTime = now;

                            var trimmedText = inputCapsule.text.trim();
                            var startsWithSpecial = trimmedText.startsWith("?") || trimmedText.startsWith(">");

                            if (startsWithSpecial || root.isConversationalMode || root.isShellMode) {
                                debounceTimer.stop();
                                if (typeof bridge !== "undefined" && bridge && bridge.searchController) bridge.searchController.clear_search();
                                else if (typeof searchController !== "undefined" && searchController) searchController.clear_search();
                                else if (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.searchController) canvasBridge.searchController.clear_search();
                                else if (typeof canvasBridge !== "undefined" && canvasBridge) canvasBridge.search.clear_search();
                            }

                            if (root.isConversationalMode || trimmedText.startsWith("?")) {
                                var rawText = trimmedText;
                                var promptText = rawText.startsWith("?") ? rawText.substring(1).trim() : rawText;
                                var words = promptText.length > 0 ? promptText.split(/\s+/).filter(function(w) { return w.length > 0; }) : [];
                                var lastChar = promptText.length > 0 ? promptText.charAt(promptText.length - 1) : "";
                                var endsWithPunct = (lastChar === "?" || lastChar === "." || lastChar === "!");

                                if (words.length >= 3 && endsWithPunct && rawText !== root.lastExecutedPrompt && promptText !== root.lastExecutedPrompt) {
                                    aiAutoSendTimer.restart();
                                } else {
                                    aiAutoSendTimer.stop();
                                }
                            } else if (!root.isShellMode && !trimmedText.startsWith(">")) {
                                aiAutoSendTimer.stop();
                                debounceTimer.restart();
                            } else {
                                aiAutoSendTimer.stop();
                            }
                        } else {
                            aiAutoSendTimer.stop();
                            debounceTimer.stop();
                            if (typeof bridge !== "undefined" && bridge && bridge.searchController) bridge.searchController.clear_search();
                            else if (typeof searchController !== "undefined" && searchController) searchController.clear_search();
                            else if (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.searchController) canvasBridge.searchController.clear_search();
                            else if (typeof canvasBridge !== "undefined" && canvasBridge) canvasBridge.search.clear_search();
                        }
                    }

                    onTabPressed: function(shiftModifier) {
                        var count = root.resultsList ? root.resultsList.length : 0;
                        var maxIdx = root.shelfExpanded ? (count - 1) : (Math.min(16, count) - 1);
                        if (!shiftModifier) {
                            if (root.isShellMode) {
                                root.handleShellTabCompletion();
                            } else if (count > 0) {
                                if (root.currentRibbonIndex < maxIdx) root.currentRibbonIndex++;
                                else root.currentRibbonIndex = 0;
                            }
                        } else {
                            if (count > 0) {
                                if (root.currentRibbonIndex > 0) root.currentRibbonIndex--;
                                else root.currentRibbonIndex = Math.max(0, maxIdx);
                            }
                        }
                    }

                    onLeftPressed: {
                        var count = root.resultsList ? root.resultsList.length : 0;
                        var maxIdx = root.shelfExpanded ? (count - 1) : (Math.min(16, count) - 1);
                        if (count > 0) {
                            if (root.currentRibbonIndex > 0) root.currentRibbonIndex--;
                            else root.currentRibbonIndex = Math.max(0, maxIdx);
                        }
                    }

                    onRightPressed: {
                        var count = root.resultsList ? root.resultsList.length : 0;
                        var maxIdx = root.shelfExpanded ? (count - 1) : (Math.min(16, count) - 1);
                        if (count > 0) {
                            if (root.currentRibbonIndex < maxIdx) root.currentRibbonIndex++;
                            else root.currentRibbonIndex = 0;
                        }
                    }

                    onUpPressed: {
                        if (root.isShellMode) {
                            var hLen = root.shellHistory ? root.shellHistory.length : 0;
                            if (hLen > 0) {
                                if (root.shellHistoryIndex === -1) {
                                    root.shellHistoryIndex = hLen - 1;
                                } else if (root.shellHistoryIndex > 0) {
                                    root.shellHistoryIndex--;
                                }
                                var hEntry = root.shellHistory[root.shellHistoryIndex];
                                if (hEntry) {
                                    var formatted = hEntry;
                                    if (!formatted.startsWith(">")) {
                                        formatted = "> " + formatted;
                                    } else if (!formatted.startsWith("> ")) {
                                        formatted = "> " + formatted.substring(1).trim();
                                    }
                                    inputCapsule.text = formatted;
                                    inputCapsule.cursorPosition = inputCapsule.text.length;
                                }
                            }
                        } else {
                            if (!root.shelfExpanded) {
                                root.shelfExpanded = true;
                            } else {
                                var cols = 4;
                                var count = root.resultsList ? root.resultsList.length : 0;
                                if (count > 0 && root.currentRibbonIndex >= cols) root.currentRibbonIndex -= cols;
                            }
                        }
                    }

                    onDownPressed: {
                        if (root.isShellMode) {
                            var hLen = root.shellHistory ? root.shellHistory.length : 0;
                            if (root.shellHistoryIndex !== -1) {
                                root.shellHistoryIndex++;
                                if (root.shellHistoryIndex >= hLen) {
                                    root.shellHistoryIndex = -1;
                                    inputCapsule.text = "> ";
                                    inputCapsule.cursorPosition = inputCapsule.text.length;
                                } else {
                                    var hEntry2 = root.shellHistory[root.shellHistoryIndex];
                                    if (hEntry2) {
                                        var formatted2 = hEntry2;
                                        if (!formatted2.startsWith(">")) {
                                            formatted2 = "> " + formatted2;
                                        } else if (!formatted2.startsWith("> ")) {
                                            formatted2 = "> " + formatted2.substring(1).trim();
                                        }
                                        inputCapsule.text = formatted2;
                                        inputCapsule.cursorPosition = inputCapsule.text.length;
                                    }
                                }
                            }
                        } else {
                            var count = root.resultsList ? root.resultsList.length : 0;
                            if (root.shelfExpanded) {
                                var cols = 4;
                                if (root.currentRibbonIndex + cols < count) {
                                    root.currentRibbonIndex += cols;
                                } else {
                                    root.shelfExpanded = false;
                                }
                            }
                        }
                    }

                    onEscapePressed: {
                        root.shelfExpanded = false;
                        if (inputCapsule.text.length > 0) root.clearTextAndCancel();
                        else root.dismiss();
                    }

                    onReturnPressed: {
                        var count = root.resultsList ? root.resultsList.length : 0;
                        debounceTimer.stop();
                        aiAutoSendTimer.stop();
                        if (root.isShellMode) {
                            root.submitShellCommand();
                        } else if (root.isConversationalMode) {
                            root.submitConversationalQuery();
                        } else if (root.currentRibbonIndex >= 0 && count > root.currentRibbonIndex) {
                            root.selectCurrentRibbonItem();
                        } else if (count > 0) {
                            root.currentRibbonIndex = 0;
                            root.selectCurrentRibbonItem();
                        } else if (inputCapsule.text.trim().length > 0) {
                            root.querySubmitted(inputCapsule.text.trim());
                            root.dismiss();
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: (typeof bridge !== "undefined" && bridge && bridge.conversation) ? bridge.conversation : (typeof canvasBridge !== "undefined" && canvasBridge && canvasBridge.conversation ? canvasBridge.conversation : null)
        ignoreUnknownSignals: true
        function onTokenReceived(chunk) {
            var currList = root.resultsList ? root.resultsList.slice() : [];
            currList.push({"title": chunk});
            root.resultsList = currList;
        }
        function onEngineStateChanged(state) {
            root.engineState = state;
        }
    }

    Timer {
        id: debounceTimer
        objectName: "debounceTimer"
        interval: 150
        repeat: false
        onTriggered: {
            if (!root.isShellMode && !root.isConversationalMode && !inputCapsule.text.trim().startsWith("?") && !inputCapsule.text.trim().startsWith(">")) {
                root.dispatchCurrentQuery();
            }
        }
    }

    Timer {
        id: aiAutoSendTimer
        objectName: "aiAutoSendTimer"
        interval: 1200
        repeat: false
        onTriggered: {
            if (root.isConversationalMode) {
                root.submitConversationalQuery();
            }
        }
    }
}
