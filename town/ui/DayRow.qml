import QtQuick

// One saved day. Short: when, what, and a window per local. Long: their names and how each one ended.
// A click opens the day. In the long list a day can also be set beside another one.
Item {
    id: row
    required property var modelData
    property bool long: false
    property string picked: ""        // the day already chosen to compare, if one is
    property string pickedTask: ""
    signal opened()
    signal compare()
    readonly property bool mine: picked === modelData.day
    readonly property bool matches: picked === "" || modelData.task === pickedTask
    width: parent ? parent.width : 0
    height: long ? 64 : 52
    opacity: matches ? 1 : 0.35
    Behavior on opacity { NumberAnimation { duration: 140 } }

    Rectangle { anchors.fill: parent; anchors.leftMargin: -12; anchors.rightMargin: -12; radius: 3
                color: row.mine ? Theme.dark : over.hovered ? Theme.panel : "transparent" }

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
        T { width: parent.width; text: row.modelData.task + (row.long && row.modelData.today ? "   " + row.modelData.today : "") }
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
        readonly property bool acting: (over.hovered || row.mine) && !town.busy
        width: acting ? acts.width : (row.long ? marks.width : 0)
        height: 32
        Row {
            id: marks
            visible: row.long && !side.acting
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            Repeater {
                model: row.modelData.locals
                Rectangle { required property var modelData; width: 9; height: 12; color: Theme.stateColor(modelData.outcome) }
            }
        }
        Row {
            id: acts
            visible: side.acting
            spacing: 6
            Btn {
                visible: row.long && row.matches
                text: row.mine ? "Cancel" : row.picked !== "" ? "Compare with this" : "Compare"
                strong: row.picked !== "" && !row.mine
                onPressed: row.compare()
            }
            Btn { visible: row.modelData.again && row.picked === ""; text: "Run again"; onPressed: { town.runAgain(row.modelData.day); row.opened() } }
            HoverHandler { id: onActs }
        }
    }
    HoverHandler { id: over; cursorShape: town.busy ? Qt.ArrowCursor : Qt.PointingHandCursor }
    // Not while the pointer is on a button: that click is the button's.
    TapHandler { enabled: !town.busy && !onActs.hovered && row.picked === ""; onTapped: { town.openDay(row.modelData.day); row.opened() } }
}
