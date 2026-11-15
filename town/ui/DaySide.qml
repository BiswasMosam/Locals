import QtQuick

// Beside a day: a strip of steps for each local, and the feed.
Item {
    id: side
    property var feed: null       // the ListModel of moments
    property int sel: -1          // the moment somebody picked, or -1 while following
    property int shown: -1        // the moment on the left right now
    property string only: ""      // narrow the feed to this local
    property bool steps: true
    signal pick(int i)
    signal narrow(string id)

    readonly property var rows: town.strips
    // A moment picked from a strip or the viewer is brought into view in the feed, and the feed stops chasing the newest.
    onShownChanged: if (sel >= 0) { list.pinned = false; list.positionViewAtIndex(shown, ListView.Contain) }
    onSelChanged: if (sel < 0) { list.pinned = true; list.positionViewAtEnd() }
    readonly property real pad: 32

    Heading { id: head; x: side.pad; y: 38; text: town.now.kept ? "A kept day" : "The day" }
    Btn {
        anchors { right: parent.right; rightMargin: side.pad; verticalCenter: head.verticalCenter }
        visible: !town.busy
        text: "Close the day"
        onPressed: town.closeDay()
    }

    // ---------- a strip per local ----------
    ListView {
        id: strips
        anchors { left: parent.left; right: parent.right; top: head.bottom; leftMargin: side.pad; rightMargin: side.pad; topMargin: 18 }
        height: Math.min(contentHeight, side.height * 0.3)
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: side.rows
        delegate: Item {
            id: strip
            required property var modelData
            width: strips.width; height: 28
            readonly property int n: modelData.cells.length + modelData.left
            readonly property real room: width - who.width - 30
            readonly property int cell: Math.max(3, Math.min(8, Math.floor(room / Math.max(1, n)) - 2))

            T {
                id: who
                width: 82
                anchors.verticalCenter: parent.verticalCenter
                text: strip.modelData.name
                font.pixelSize: 13
                color: side.only === strip.modelData.id ? Theme.light : nameOver.hovered ? Theme.ink : Theme.dim
                HoverHandler { id: nameOver; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: side.narrow(strip.modelData.id) }
            }
            Row {
                anchors { left: who.right; verticalCenter: parent.verticalCenter }
                spacing: 2
                Repeater {
                    model: strip.modelData.cells
                    Rectangle {
                        required property var modelData
                        width: strip.cell; height: 14
                        color: modelData.tone === "warn" ? Theme.light : Theme.step
                        border.width: side.shown === modelData.i ? 1 : 0
                        border.color: Theme.ink
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: side.pick(parent.modelData.i) }
                    }
                }
                Rectangle {   // how it ended
                    visible: strip.modelData.outcome !== ""
                    width: strip.cell * 2 + 2; height: 14
                    color: Theme.stateColor(strip.modelData.outcome)
                    border.width: side.shown === strip.modelData.end ? 1 : 0
                    border.color: Theme.ink
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler { enabled: strip.modelData.end >= 0; onTapped: side.pick(strip.modelData.end) }
                }
                Repeater {    // the patience they had left
                    model: strip.modelData.left
                    Rectangle { width: strip.cell; height: 14; color: "transparent"; border.width: 1; border.color: Theme.dark }
                }
            }
        }
    }

    // ---------- the feed ----------
    Heading { id: feedHead; anchors { left: head.left; top: strips.bottom; topMargin: 26 } text: "Feed" }
    Row {
        anchors { right: parent.right; rightMargin: side.pad - 5; verticalCenter: feedHead.verticalCenter }
        spacing: 4
        Chip { visible: side.only !== ""; on: true; text: "Everyone"; onToggled: side.narrow("") }
        Chip { text: "Steps"; on: side.steps; onToggled: side.steps = !side.steps }
    }
    T {
        anchors { left: head.left; top: feedHead.bottom; topMargin: 14 }
        visible: !side.feed || side.feed.count === 0
        color: Theme.faint
        text: "Nothing yet. The first local is on the way."
    }
    ListView {
        id: list
        anchors { left: parent.left; right: parent.right; top: feedHead.bottom; bottom: parent.bottom; topMargin: 10 }
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: side.feed
        // Keep to the newest line while the reader is at the bottom; leave them alone once they scroll up.
        property bool pinned: true
        onMovementEnded: pinned = atYEnd
        // On the height, not the count: a line is counted before it has been measured, and the view stopped one short.
        onContentHeightChanged: if (pinned) Qt.callLater(positionViewAtEnd)
        onCountChanged: if (count === 0) pinned = true
        delegate: Item {
            id: line
            required property int i
            required property string local
            required property string name
            required property string kind
            required property string tone
            required property int step
            required property string title
            required property string text
            required property string at
            readonly property bool wanted: (side.only === "" || side.only === local) && (side.steps || kind !== "STEP")
            readonly property bool isStep: kind === "STEP"
            width: list.width
            height: wanted ? body.height + (isStep ? 12 : 20) : 0
            visible: wanted

            Rectangle { anchors.fill: parent; color: over.hovered ? Theme.panel : "transparent" }
            Rectangle { width: 2; height: parent.height; color: Theme.ink; visible: side.shown === line.i }
            Column {
                id: body
                anchors { left: parent.left; right: parent.right; leftMargin: side.pad; rightMargin: side.pad; verticalCenter: parent.verticalCenter }
                spacing: 2
                Item {
                    width: parent.width; height: 16
                    T {
                        font.pixelSize: 12
                        color: line.tone === "warn" ? Theme.light : line.tone === "good" ? Theme.good : line.tone === "bad" ? Theme.bad : Theme.faint
                        text: line.name + "  ·  " + (line.isStep ? "step " + line.step : line.kind.charAt(0) + line.kind.slice(1).toLowerCase())
                    }
                    T { anchors.right: parent.right; font.pixelSize: 11; font.family: Theme.mono; color: Theme.faint; text: line.at }
                }
                T {
                    width: parent.width
                    visible: line.isStep
                    text: line.title
                    font.pixelSize: 13; color: Theme.ink
                }
                T {
                    width: parent.width
                    text: line.text
                    font.pixelSize: 13
                    color: line.isStep ? Theme.dim : Theme.ink
                    wrapMode: Text.Wrap; maximumLineCount: line.isStep ? 2 : 6
                }
            }
            HoverHandler { id: over; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: side.pick(line.i) }
        }
    }
}
