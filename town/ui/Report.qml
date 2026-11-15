import QtQuick

// The town so far: of every run that was kept, how many got it done, set against real people, by task and by family.
Item {
    id: page
    objectName: "report"
    readonly property var r: town.report

    // One count as a line: a name, a bar with real people's mark on it, and the count in numbers.
    component Line: Item {
        id: line
        property var row: ({})
        property bool mark: true
        property real nameWidth: 190
        height: 30
        T { width: line.nameWidth - 14; anchors.verticalCenter: parent.verticalCenter; text: line.row.name || ""; color: Theme.dim }
        Item {
            id: bar
            anchors { left: parent.left; leftMargin: line.nameWidth; right: count.left; rightMargin: 16; verticalCenter: parent.verticalCenter }
            height: 14
            Rectangle { y: 4; width: parent.width; height: 6; color: Theme.dark }
            Rectangle { y: 4; height: 6; width: parent.width * (line.row.part || 0); color: Theme.dim
                        Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } } }
            Rectangle { visible: line.mark; x: Math.round(parent.width * page.r.benchmark); width: 1; height: parent.height; color: Theme.ink }
        }
        T { id: count; anchors { right: pct.left; rightMargin: 12; verticalCenter: parent.verticalCenter }
            width: 76; horizontalAlignment: Text.AlignRight
            text: line.row.of ? line.row.done + " of " + line.row.of : ""; font.family: Theme.mono; font.pixelSize: 12; color: Theme.dim }
        T { id: pct; anchors { right: parent.right; verticalCenter: parent.verticalCenter }
            width: 44; horizontalAlignment: Text.AlignRight
            text: line.row.pct || ""; font.family: Theme.mono; font.pixelSize: 13 }
    }

    // ---------- left: the count ----------
    Item {
        id: left
        x: Theme.gutter; y: 38
        width: Math.min(560, (parent.width - Theme.gutter * 2 - 72) * 0.44)
        height: parent.height - 38 - 28

        Heading { id: over; text: "The town so far" }
        Text {
            id: head
            anchors.top: over.bottom; anchors.topMargin: 10
            width: parent.width
            text: page.r.head
            font.family: Theme.display; font.pixelSize: 40; font.weight: Font.DemiBold
            color: Theme.ink
            wrapMode: Text.Wrap; maximumLineCount: 2
        }
        T { id: sub; anchors.top: head.bottom; anchors.topMargin: 8; width: parent.width; text: page.r.sub
            font.pixelSize: 16; color: Theme.dim; wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.25 }

        Column {
            id: against
            anchors.top: sub.bottom; anchors.topMargin: 34
            width: parent.width
            visible: page.r.any
            Line { width: parent.width; nameWidth: 120; mark: false; row: page.r.all }
            Line { width: parent.width; nameWidth: 120; mark: false; row: ({ name: "Real people", part: page.r.benchmark, pct: page.r.bench, of: 0, done: 0 }) }
            T { width: parent.width; topPadding: 8; font.pixelSize: 12; color: Theme.faint; wrapMode: Text.Wrap; maximumLineCount: 2; lineHeight: 1.2
                text: "Real people: the average task completion across 1,189 tasks in 115 usability tests (Sauro)." }
        }

        Column {
            id: mistakes
            anchors.top: against.bottom; anchors.topMargin: 34
            width: parent.width
            visible: page.r.checked
            Heading { text: "The model's own mistakes"; bottomPadding: 10 }
            T { width: parent.width; bottomPadding: 8; color: Theme.dim; font.pixelSize: 13; wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.2
                text: "Counted on the " + page.r.checked_runs + " newer runs. A mistake here is the model's, not the local's: an answer no person could give. It is asked again, up to twice." }
            Line { width: parent.width; nameWidth: 220; mark: false; row: Object.assign({}, page.r.clean, { name: "No mistake cost a step" }) }
            Line { width: parent.width; nameWidth: 220; mark: false; visible: page.r.cost.of > 0; row: Object.assign({}, page.r.cost, { name: "A mistake cost a step" }) }
            Item {
                width: parent.width; height: 30
                T { anchors.verticalCenter: parent.verticalCenter; text: "Answers the model gave again"; color: Theme.dim }
                T { anchors { right: parent.right; verticalCenter: parent.verticalCenter } text: page.r.retries; font.family: Theme.mono; font.pixelSize: 13 }
            }
        }

        T {
            anchors.bottom: parent.bottom
            width: parent.width
            visible: page.r.any
            color: Theme.faint; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.2
            text: "Days that were stopped or hit an error are left out. These counts are signals to check with real users, not verdicts."
        }
    }

    // ---------- right: by task, by family ----------
    Flickable {
        id: scroll
        anchors { left: left.right; leftMargin: 72; right: parent.right; rightMargin: Theme.gutter; top: parent.top; topMargin: 38; bottom: parent.bottom }
        visible: page.r.any
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentHeight: lists.height + 28
        Column {
            id: lists
            width: scroll.width - 14
            Heading { text: "By task"; bottomPadding: 8 }
            Repeater { model: page.r.by_task; Line { required property var modelData; width: lists.width; nameWidth: Math.min(280, lists.width * 0.42); row: modelData } }
            Heading { text: "By family"; topPadding: 30; bottomPadding: 8 }
            Repeater { model: page.r.by_family; Line { required property var modelData; width: lists.width; nameWidth: Math.min(280, lists.width * 0.42); row: modelData } }
            T { width: lists.width; topPadding: 14; font.pixelSize: 12; color: Theme.faint; text: "The line on each bar is where real people finish." }
        }
    }
    Rectangle {
        visible: scroll.visible && scroll.contentHeight > scroll.height
        anchors.right: parent.right; anchors.rightMargin: 14
        width: 3; radius: 1.5; color: Theme.line
        y: scroll.y + scroll.visibleArea.yPosition * scroll.height
        height: Math.max(24, scroll.visibleArea.heightRatio * scroll.height)
    }
}
