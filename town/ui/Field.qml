import QtQuick

// A place to type: one line, or several when tall is set.
Rectangle {
    id: field
    property alias text: input.text
    property string hint: ""
    property bool tall: false
    property bool mono: false
    signal edited()
    implicitHeight: tall ? 84 : 36
    radius: 3
    color: Theme.panel
    border.width: 1
    border.color: input.activeFocus ? Theme.dim : Theme.line

    Flickable {
        id: flick
        anchors.fill: parent; anchors.margins: 9
        clip: true
        contentHeight: input.contentHeight
        TextEdit {
            id: input
            width: flick.width
            height: Math.max(flick.height, contentHeight)
            font.family: field.mono ? Theme.mono : Theme.text
            font.pixelSize: 14
            color: Theme.ink
            selectionColor: Theme.step
            selectedTextColor: Theme.ink
            selectByMouse: true
            wrapMode: field.tall ? TextEdit.Wrap : TextEdit.NoWrap
            activeFocusOnTab: true
            // One line means one line: Enter moves on, and a pasted paragraph is flattened.
            Keys.onReturnPressed: (e) => { if (field.tall) e.accepted = false; else nextItemInFocusChain().forceActiveFocus() }
            Keys.onTabPressed: nextItemInFocusChain().forceActiveFocus()
            Keys.onBacktabPressed: nextItemInFocusChain(false).forceActiveFocus()
            onTextChanged: {
                if (!field.tall && text.indexOf("\n") >= 0) text = text.replace(/\s*\n\s*/g, " ")
                field.edited()
            }
            onCursorRectangleChanged: {
                if (cursorRectangle.y < flick.contentY) flick.contentY = cursorRectangle.y
                else if (cursorRectangle.y + cursorRectangle.height > flick.contentY + flick.height)
                    flick.contentY = cursorRectangle.y + cursorRectangle.height - flick.height
            }
        }
    }
    T {
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 9 }
        visible: input.text === ""
        text: field.hint
        color: Theme.faint
        wrapMode: field.tall ? Text.Wrap : Text.NoWrap
    }
    HoverHandler { cursorShape: Qt.IBeamCursor }
}
