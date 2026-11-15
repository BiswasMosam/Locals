import QtQuick

// A small switch made of a word: lit when on.
Item {
    id: chip
    property string text: ""
    property bool on: false
    signal toggled()
    implicitWidth: word.implicitWidth + 10
    implicitHeight: 22
    activeFocusOnTab: true
    Keys.onSpacePressed: chip.toggled()
    Keys.onReturnPressed: chip.toggled()
    Accessible.role: Accessible.CheckBox
    Accessible.name: text
    Accessible.checked: on

    Rectangle { anchors.fill: parent; radius: 3; color: over.hovered || chip.activeFocus ? Theme.dark : "transparent" }
    T { id: word; anchors.centerIn: parent; text: chip.text; font.pixelSize: 12; color: chip.on ? Theme.ink : Theme.faint }
    HoverHandler { id: over; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: chip.toggled() }
}
