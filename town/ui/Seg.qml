import QtQuick

// One of a few choices that sit side by side; the chosen one is filled.
Rectangle {
    id: seg
    property string text: ""
    property bool on: false
    signal chosen()
    implicitWidth: word.implicitWidth + 22
    implicitHeight: 30
    radius: 3
    color: on ? Theme.step : over.hovered ? Theme.dark : Theme.panel
    Behavior on color { ColorAnimation { duration: 90 } }
    border.width: activeFocus ? 1 : 0
    border.color: Theme.dim
    activeFocusOnTab: true
    Keys.onSpacePressed: seg.chosen()
    Keys.onReturnPressed: seg.chosen()
    Accessible.role: Accessible.RadioButton
    Accessible.name: text
    Accessible.checked: on

    T { id: word; anchors.centerIn: parent; text: seg.text; font.pixelSize: 13; color: seg.on ? Theme.ink : Theme.dim }
    HoverHandler { id: over; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: seg.chosen() }
}
