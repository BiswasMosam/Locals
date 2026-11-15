import QtQuick

Rectangle {
    id: btn
    property string text: ""
    property bool strong: false   // the one thing to do next; amber
    signal pressed()
    implicitWidth: label.implicitWidth + 28
    implicitHeight: 32
    radius: 3
    color: strong ? (hover.hovered ? Qt.lighter(Theme.light, 1.08) : Theme.light)
                  : (hover.hovered ? Theme.line : Theme.dark)
    Behavior on color { ColorAnimation { duration: 90 } }
    activeFocusOnTab: true
    border.width: activeFocus ? 1 : 0
    border.color: Theme.ink
    Keys.onReturnPressed: btn.pressed()
    Keys.onSpacePressed: btn.pressed()

    T {
        id: label
        anchors.centerIn: parent
        text: btn.text
        font.pixelSize: 13
        font.weight: Font.DemiBold
        color: btn.strong ? Theme.night : Theme.ink
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: btn.pressed() }
}
