import QtQuick

// One saved day. Short: when, what, and a window per local. Long: their names and how each one ended.
Item {
    id: row
    required property var modelData
    property bool long: false
    signal opened()
    width: parent ? parent.width : 0
    height: long ? 64 : 52

    Rectangle { anchors.fill: parent; anchors.leftMargin: -12; anchors.rightMargin: -12; radius: 3; color: over.hovered ? Theme.panel : "transparent" }

    Column {
        id: when
        anchors.verticalCenter: parent.verticalCenter
        width: row.long ? 120 : 78
        T { text: Qt.formatDate(new Date(row.modelData.date + "T12:00:00"), "d MMM"); color: Theme.dim; font.pixelSize: 13 }
        T { text: row.modelData.time; color: Theme.faint; font.pixelSize: 12; font.family: Theme.mono }
    }

    Column {
        anchors.left: when.right
        anchors.right: side.left
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 3
        T { width: parent.width; text: row.modelData.task }
        T {
            width: parent.width
            visible: row.long
            color: Theme.dim; font.pixelSize: 13
            text: row.modelData.locals.map(l => l.name + (l.outcome ? " " + Theme.stateWords(l.outcome) : "")).join("  ·  ")
        }
        Row {
            visible: !row.long
            spacing: 4
            Repeater {
                model: row.modelData.locals
                Rectangle { required property var modelData; width: 7; height: 9; color: Theme.stateColor(modelData.outcome) }
            }
        }
    }

    Item {
        id: side
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: again.visible ? again.width : (row.long ? marks.width : 0)
        height: 32
        Row {
            id: marks
            visible: row.long && !again.visible
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            Repeater {
                model: row.modelData.locals
                Rectangle { required property var modelData; width: 9; height: 12; color: Theme.stateColor(modelData.outcome) }
            }
        }
        Btn {
            id: again
            z: 1
            visible: (over.hovered || activeFocus) && row.modelData.again && !town.busy
            text: "Run again"
            onPressed: { town.runAgain(row.modelData.day); row.opened() }
        }
    }
    HoverHandler { id: over; cursorShape: town.busy ? Qt.ArrowCursor : Qt.PointingHandCursor }
    TapHandler { enabled: !town.busy; onTapped: { town.openDay(row.modelData.day); row.opened() } }
}
