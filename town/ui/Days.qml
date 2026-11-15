import QtQuick

// Every day that was kept, newest first.
Item {
    id: page
    signal opened()
    Heading { id: over; x: Theme.gutter; y: 38; text: "Days" }
    Text {
        id: head
        x: Theme.gutter
        anchors.top: over.bottom; anchors.topMargin: 10
        text: town.days.length ? town.days.length + (town.days.length === 1 ? " day kept." : " days kept.") : "No day has been run yet."
        font.family: Theme.display; font.pixelSize: 40; font.weight: Font.DemiBold
        color: Theme.ink
    }
    ListView {
        id: list
        anchors { left: parent.left; right: parent.right; top: head.bottom; bottom: parent.bottom
                  leftMargin: Theme.gutter; rightMargin: Theme.gutter; topMargin: 22 }
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: town.days
        delegate: DayRow { long: true; onOpened: page.opened() }
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
