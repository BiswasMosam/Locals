import QtQuick

// Every day that was kept, newest first. Two of them can be set side by side.
Item {
    id: page
    objectName: "days"
    signal opened()
    property string picked: ""        // the first of two days to compare
    property string pickedTask: ""
    readonly property bool comparing: !!town.comparison.rows

    function choose(day) {
        if (picked === day.day) { picked = ""; return }
        if (picked === "") { picked = day.day; pickedTask = day.task; return }
        town.compare(picked, day.day)
        picked = ""
    }

    Item {
        anchors.fill: parent
        visible: opacity > 0
        opacity: page.comparing ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: 140 } }

        Heading { id: over; x: Theme.gutter; y: 38; text: "Days" }
        Text {
            id: head
            x: Theme.gutter
            anchors.top: over.bottom; anchors.topMargin: 10
            text: page.picked !== "" ? "Which day goes beside it?"
                : town.days.length ? town.days.length + (town.days.length === 1 ? " day kept." : " days kept.") : "No day has been run yet."
            font.family: Theme.display; font.pixelSize: 40; font.weight: Font.DemiBold
            color: Theme.ink
        }
        T {
            id: sub
            x: Theme.gutter
            anchors.top: head.bottom; anchors.topMargin: 6
            font.pixelSize: 16; color: Theme.dim
            text: page.picked !== "" ? "Days of the same task are the ones worth comparing: before a change to the app, and after."
                                     : "Open a day to read it again, or set two of the same task side by side."
        }
        ListView {
            id: list
            anchors { left: parent.left; right: parent.right; top: sub.bottom; bottom: parent.bottom
                      leftMargin: Theme.gutter; rightMargin: Theme.gutter; topMargin: 20 }
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: town.days
            delegate: DayRow {
                long: true
                picked: page.picked
                pickedTask: page.pickedTask
                onOpened: page.opened()
                onCompare: page.choose(modelData)
            }
        }
        // Where you are in the list, shown only while there is more than fits.
        Rectangle {
            visible: list.contentHeight > list.height
            anchors.right: parent.right; anchors.rightMargin: 14
            width: 3; radius: 1.5
            color: Theme.line
            y: list.y + list.visibleArea.yPosition * list.height
            height: Math.max(24, list.visibleArea.heightRatio * list.height)
        }
    }

    Compare {
        anchors.fill: parent
        visible: opacity > 0
        opacity: page.comparing ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 140 } }
    }
}
