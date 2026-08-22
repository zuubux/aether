import QtQuick
import QtQuick.Controls

Item {
    id: root
    width: 600
    height: 60
    
    property bool active: false
    
    signal querySubmitted(string text)
    signal dismissed()
    signal cancelQuery()
    
    readonly property int textLength: inputField.text.length
    
    function clearTextAndCancel() {
        inputField.text = ""
        cancelQuery()
    }
    
    Timer {
        id: debounceTimer
        interval: 250
        repeat: false
        onTriggered: {
            if (inputField.text.trim().length > 1) {
                console.log("[OmniBar] search-as-you-type querySubmitted: " + inputField.text.trim())
                root.querySubmitted(inputField.text.trim())
            }
        }
    }
    
    onActiveChanged: {
        if (active) {
            inputField.forceActiveFocus()
        } else {
            inputField.text = ""
        }
    }
    
    opacity: active ? 1.0 : 0.0
    visible: active || opacity > 0.0
    y: active ? parent.height * 0.15 : parent.height * 0.10
    
    Behavior on opacity {
        NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
    }
    
    Behavior on y {
        SpringAnimation { spring: 2.5; damping: 0.7 }
    }
    
    Rectangle {
        anchors.fill: parent
        radius: 22
        color: Qt.rgba(20/255, 23/255, 29/255, 0.88)
        border.color: inputField.activeFocus ? "#64d2ff" : "#334155"
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
            color: "#f8fafc"
            font.pixelSize: 18
            font.family: "Monospace"
            selectionColor: "#38bdf8"
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

            Keys.onPressed: (event) => {
                if (event.key === Qt.Key_Escape) {
                    if (inputField.text.length > 0) {
                        root.clearTextAndCancel()
                    } else {
                        root.dismissed()
                    }
                    event.accepted = true
                } else if (event.key === Qt.Key_Enter || event.key === Qt.Key_Return) {
                    debounceTimer.stop()
                    if (text.trim().length > 0) {
                        root.querySubmitted(text)
                    }
                    event.accepted = true
                } else {
                    event.accepted = false
                }
            }
        }
    }
}
