import QtQuick

// The slim rail on the left: the mark, then the places you can go.
Rectangle {
    id: rail
    property string page: "town"
    signal picked(string name)
    width: 64
    color: Theme.rail

    readonly property var places: [
        { name: "town", label: "Town", rows: ["...X...", "..XXX..", ".XXXXX.", "XXXXXXX", ".X...X.", ".X.X.X.", ".X.X.X."] },
        { name: "days", label: "Days", rows: ["XXXXXXX", "X.....X", "XXXXXXX", "X.X.X.X", "XXXXXXX", "X.X.X.X", "XXXXXXX"] }
    ]

    Pix {
        id: mark
        anchors.horizontalCenter: parent.horizontalCenter
        y: 22
        rows: ["X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"]
        color: Theme.light
    }

    Column {
        anchors.top: mark.bottom
        anchors.topMargin: 30
        width: parent.width
        spacing: 6
        Repeater {
            model: rail.places
            Item {
                id: place
                required property var modelData
                readonly property bool on: rail.page === modelData.name
                width: rail.width; height: 56
                activeFocusOnTab: true
                Keys.onReturnPressed: rail.picked(modelData.name)
                Accessible.role: Accessible.PageTab
                Accessible.name: modelData.label

                Rectangle {   // where you are
                    width: 2; height: place.on ? 28 : 0
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.light
                    Behavior on height { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                }
                Pix {
                    id: glyph
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 8
                    rows: place.modelData.rows
                    color: place.on ? Theme.light : (over.hovered || place.activeFocus ? Theme.ink : Theme.dim)
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: glyph.bottom
                    anchors.topMargin: 7
                    text: place.modelData.label
                    font.family: Theme.small
                    font.pixelSize: 10
                    renderType: Text.NativeRendering
                    color: glyph.color
                }
                HoverHandler { id: over; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: rail.picked(place.modelData.name) }
            }
        }
    }

    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.line }
}
