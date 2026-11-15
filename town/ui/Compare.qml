import QtQuick

// Two kept days side by side, the earlier on the left: for the same task before and after a change to the app.
Item {
    id: page
    readonly property var c: town.comparison
    readonly property bool has: !!c.rows

    function when(d) {
        return d ? Qt.formatDate(new Date(d.day.slice(0, 10) + "T12:00:00"), "d MMM") + ", " + d.day.slice(11, 13) + ":" + d.day.slice(13, 15) : ""
    }
    function changeWords(k) {
        return { better: "got it done this time", worse: "no longer gets it done", quicker: "fewer steps", slower: "more steps",
                 same: "the same", "only before": "did not go the second time", "only after": "did not go the first time" }[k] || ""
    }
    function changeColor(k) { return k === "better" || k === "quicker" ? Theme.good : k === "worse" ? Theme.bad : k === "slower" ? Theme.light : Theme.faint }

    Heading { id: over; x: Theme.gutter; y: 38; text: page.has ? page.c.before.task + (page.c.same_task ? "" : "   against   " + page.c.after.task) : "" }
    Btn { anchors { right: parent.right; rightMargin: Theme.gutter; verticalCenter: over.verticalCenter } text: "Back to the days"; onPressed: town.endCompare() }
    Text {
        id: head
        x: Theme.gutter
        anchors.top: over.bottom; anchors.topMargin: 10
        text: page.has ? page.c.head : ""
        font.family: Theme.display; font.pixelSize: 40; font.weight: Font.DemiBold
        color: Theme.ink
    }
    T {
        id: sub
        x: Theme.gutter; width: parent.width - Theme.gutter * 2
        anchors.top: head.bottom; anchors.topMargin: 6
        text: page.has ? page.c.note + (page.c.same_task ? "" : "  These are two different tasks, so read it with care.") : ""
        font.pixelSize: 16; color: Theme.dim
    }

    // The two days, named once, over their columns.
    Item {
        id: cols
        anchors { top: sub.bottom; topMargin: 30; left: parent.left; right: parent.right; leftMargin: Theme.gutter; rightMargin: Theme.gutter }
        height: 40
        readonly property real name: 150
        readonly property real side: (width - name - 260) / 2
        T { x: cols.name; width: cols.side - 20; text: page.has ? page.when(page.c.before) + (page.c.before.today ? "  ·  " + page.c.before.today : "") : ""; color: Theme.dim; font.pixelSize: 13 }
        T { x: cols.name + cols.side; width: cols.side - 20; text: page.has ? page.when(page.c.after) + (page.c.after.today ? "  ·  " + page.c.after.today : "") : ""; color: Theme.dim; font.pixelSize: 13 }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
    }
    ListView {
        id: list
        anchors { top: cols.bottom; bottom: parent.bottom; left: cols.left; right: cols.right }
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: page.has ? page.c.rows : []
        delegate: Item {
            id: row
            required property var modelData
            width: list.width; height: 44
            T { width: cols.name - 16; anchors.verticalCenter: parent.verticalCenter; text: row.modelData.name }
            Repeater {
                model: [row.modelData.before, row.modelData.after]
                Item {
                    required property var modelData
                    required property int index
                    readonly property bool went: !!modelData.outcome
                    x: cols.name + index * cols.side; width: cols.side - 20; height: row.height
                    // As many cells as steps they took, then how it ended: the same picture as a day's strip.
                    Row {
                        id: cells
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        visible: parent.went
                        Repeater { model: Math.min(30, parent.parent.modelData.steps || 0); Rectangle { width: 5; height: 14; color: Theme.step } }
                        Rectangle { width: 12; height: 14; color: Theme.stateColor(parent.parent.modelData.outcome || "") }
                    }
                    T {
                        anchors { left: cells.right; leftMargin: 12; right: parent.right; verticalCenter: parent.verticalCenter }
                        visible: parent.went
                        font.pixelSize: 13; color: Theme.dim
                        text: parent.went ? Theme.stateWords(parent.modelData.outcome) + ", " + parent.modelData.steps + (parent.modelData.steps === 1 ? " step" : " steps")
                              + (parent.modelData.stuck ? ", stuck " + parent.modelData.stuck + (parent.modelData.stuck === 1 ? " time" : " times") : "") : ""
                    }
                    T { anchors.verticalCenter: parent.verticalCenter; visible: !parent.went; color: Theme.faint; font.pixelSize: 13; text: "stayed home" }
                }
            }
            T {
                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                width: 250; horizontalAlignment: Text.AlignRight
                text: page.changeWords(row.modelData.change)
                color: page.changeColor(row.modelData.change)
            }
        }
    }
}
