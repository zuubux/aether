import QtQuick
import QtQuick.Controls

Item {
    id: root
    width: 600
    height: 60
    
    property bool active: false
    property Item searchShelf: null
    property var completionList: []
    property int completionIndex: -1
    property string lastTypedText: ""
    
    signal querySubmitted(string text)
    signal dismissed()
    signal cancelQuery()
    
    readonly property int textLength: inputField.text.length
    
    function clearTextAndCancel() {
        inputField.text = ""
        cancelQuery()
    }
    
    function open() {
        active = true
        inputField.forceActiveFocus()
    }
    
    function dismiss() {
        active = false
        inputField.text = ""
        inputField.focus = false
        if (root.parent) {
            root.parent.forceActiveFocus()
        }
        dismissed()
    }
    
    Timer {
        id: debounceTimer
        interval: 250
        repeat: false
        onTriggered: {
            var txt = inputField.text.trim()
            if (txt.length > 1) {
                if (!txt.startsWith("/") && !txt.startsWith(">") && !txt.startsWith("@")) {
                    console.log("[OmniBar] search-as-you-type querySubmitted: " + txt)
                    root.querySubmitted(txt)
                }
            }
        }
    }
    
    onActiveChanged: {
        if (active) {
            inputField.forceActiveFocus()
        } else {
            inputField.text = ""
            inputField.focus = false
            completionList = []
            completionIndex = -1
        }
    }
    
    Item {
        id: suggestionsStrip
        visible: inputField.activeFocus && root.completionList && root.completionList.length > 1
        anchors.bottom: parent.top
        anchors.bottomMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        height: 34

        ListView {
            id: suggestionsList
            anchors.fill: parent
            anchors.margins: 4
            orientation: ListView.Horizontal
            spacing: 6
            model: root.completionList
            currentIndex: root.completionIndex
            clip: false

            delegate: Rectangle {
                height: 24
                width: suggText.implicitWidth + 16
                radius: 6
                color: index === root.completionIndex ? Theme.accentSuccess : Theme.surfaceButton
                border.color: index === root.completionIndex ? Theme.accentSuccess : Theme.borderSubtle
                border.width: 1

                Text {
                    id: suggText
                    anchors.centerIn: parent
                    text: {
                        if (modelData.startsWith("/") && modelData.trim().indexOf(" ") === -1) {
                            return modelData.trim()
                        }
                        var stripped = modelData.replace(/^\/link\s+|^@|^>\s*|^&\s*/, "").trim()
                        return stripped.length > 0 ? stripped : modelData.trim()
                    }
                    font.pixelSize: 11
                    font.family: Theme.fontCode
                    color: index === root.completionIndex ? Theme.textPrimary : Theme.textSecondary
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.completionIndex = index
                        inputField.text = modelData
                        inputField.cursorPosition = modelData.length
                    }
                }
            }
        }
    }

    opacity: active ? 1.0 : 0.0
    visible: active || opacity > 0.0
    anchors.bottom: parent.bottom
    anchors.bottomMargin: 28
    anchors.horizontalCenter: parent.horizontalCenter
    
    Behavior on opacity {
        NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
    }
    
    Rectangle {
        anchors.fill: parent
        radius: 22
        color: Qt.rgba(20/255, 23/255, 29/255, 0.88)
        border.color: inputField.activeFocus ? Theme.accentFocus : Theme.borderSubtle
        border.width: inputField.activeFocus ? 2 : 1
        
        Behavior on border.color {
            ColorAnimation { duration: 150 }
        }
        
        TextInput {
            id: inputField
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            verticalAlignment: TextInput.AlignVCenter
            color: Theme.textPrimary
            font.pixelSize: 18
            font.family: Theme.fontCode
            selectionColor: Theme.accentFocus
            selectedTextColor: "#07080b"
            clip: true
            focus: true
            
            onTextEdited: {
                if (text.trim().length > 1) {
                    debounceTimer.restart()
                } else if (text.trim().length === 0) {
                    debounceTimer.stop()
                    root.cancelQuery()
                }
            }
            
            onTextChanged: {
                if (root.completionList === undefined) root.completionList = []
                var currentComp = (root.completionIndex >= 0 && root.completionIndex < root.completionList.length) ? root.completionList[root.completionIndex] : ""
                if (inputField.text !== currentComp) {
                    root.lastTypedText = inputField.text
                    root.completionList = canvasBridge.get_completions(inputField.text, inputField.cursorPosition)
                    root.completionIndex = -1
                }
            }

            Keys.priority: Keys.BeforeItem
            Keys.onPressed: (event) => {
                var isSearchShelfActive = (root.searchShelf && root.searchShelf.searchActive && root.searchShelf.topMatches && root.searchShelf.topMatches.length > 0)
                if (event.key === Qt.Key_Left) {
                    if (isSearchShelfActive) {
                        root.searchShelf.navigateLeft()
                        event.accepted = true
                    } else {
                        event.accepted = false
                    }
                } else if (event.key === Qt.Key_Right) {
                    if (isSearchShelfActive) {
                        root.searchShelf.navigateRight()
                        event.accepted = true
                    } else {
                        event.accepted = false
                    }
                } else if (event.key === Qt.Key_Tab) {
                    event.accepted = true
                    if (root.completionList && root.completionList.length > 1) {
                        root.completionIndex = (root.completionIndex + 1) % root.completionList.length
                        inputField.text = root.completionList[root.completionIndex]
                        inputField.cursorPosition = inputField.text.length
                    } else if (isSearchShelfActive) {
                        root.searchShelf.navigateRight()
                    } else {
                        if (!root.completionList || root.completionList.length === 0) {
                            root.completionList = canvasBridge.get_completions(inputField.text, inputField.cursorPosition)
                            root.completionIndex = -1
                        }
                        if (root.completionList && root.completionList.length > 0) {
                            root.completionIndex = (root.completionIndex + 1) % root.completionList.length
                            inputField.text = root.completionList[root.completionIndex]
                            inputField.cursorPosition = inputField.text.length
                        }
                    }
                } else if (event.key === Qt.Key_Backtab) {
                    event.accepted = true
                    if (root.completionList && root.completionList.length > 1) {
                        root.completionIndex = (root.completionIndex - 1 + root.completionList.length) % root.completionList.length
                        inputField.text = root.completionList[root.completionIndex]
                        inputField.cursorPosition = inputField.text.length
                    } else if (isSearchShelfActive) {
                        root.searchShelf.navigateLeft()
                    } else {
                        if (root.completionList && root.completionList.length > 0) {
                            root.completionIndex = (root.completionIndex - 1 + root.completionList.length) % root.completionList.length
                            inputField.text = root.completionList[root.completionIndex]
                            inputField.cursorPosition = inputField.text.length
                        }
                    }
                } else if (event.key === Qt.Key_Escape) {
                    if (isSearchShelfActive) {
                        if (canvasBridge) {
                            canvasBridge.clear_search()
                        }
                        root.dismiss()
                    } else if (inputField.text.length > 0) {
                        root.clearTextAndCancel()
                    } else {
                        root.dismiss()
                    }
                    event.accepted = true
                } else if (event.key === Qt.Key_Enter || event.key === Qt.Key_Return) {
                    debounceTimer.stop()
                    if (isSearchShelfActive) {
                        root.searchShelf.selectFocusedNode()
                        event.accepted = true
                    } else if (text.trim().length > 0) {
                        root.querySubmitted(text)
                        root.clearTextAndCancel()
                        root.dismiss()
                        event.accepted = true
                    } else {
                        event.accepted = false
                    }
                } else {
                    event.accepted = false
                }
            }
        }
    }
}
