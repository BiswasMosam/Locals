import QtQuick

// One moment of the day: the screen the local was looking at, and what they did and thought there.
Item {
    id: moment
    property var m: null          // a moment from the feed, or null before anything has happened
    property bool following: true // showing the newest moment as it arrives, not one somebody picked
    signal enlarge()
    signal follow()

    readonly property bool has: !!m
    readonly property color tone: !has ? Theme.dim
        : m.tone === "warn" ? Theme.light : m.tone === "good" ? Theme.good : m.tone === "bad" ? Theme.bad : Theme.dim

    Rectangle {
        id: frame
        height: parent.height
        // As wide as the screenshot is: a phone is narrow, a laptop wide. Before one arrives, a phone's shape.
        width: Math.min(moment.width * 0.58, shot.status === Image.Ready ? Math.round(height * shot.implicitWidth / Math.max(1, shot.implicitHeight))
                                                                     : Math.round(height * 0.5))
        color: Theme.panel
        Image {
            id: shot
            anchors.fill: parent
            source: moment.has && moment.m.shot ? town.root + moment.m.shot : ""
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            smooth: true; mipmap: true
        }
        T {
            anchors.centerIn: parent
            visible: shot.status !== Image.Ready
            color: Theme.faint
            text: shot.status === Image.Loading ? "" : "No screen yet"
        }
        Rectangle { anchors.fill: parent; color: "transparent"; border.width: 1; border.color: over.hovered && shot.status === Image.Ready ? Theme.dim : Theme.line }
        HoverHandler { id: over; cursorShape: shot.status === Image.Ready ? Qt.PointingHandCursor : Qt.ArrowCursor }
        TapHandler { enabled: shot.status === Image.Ready; onTapped: moment.enlarge() }
    }

    Column {
        anchors { left: frame.right; leftMargin: 28; right: parent.right; verticalCenter: parent.verticalCenter }
        spacing: 10
        visible: moment.has
        Heading {
            text: moment.has ? moment.m.name + "  ·  " + (moment.m.kind === "STEP" ? "step " + moment.m.step : moment.m.kind) : ""
            color: moment.tone
        }
        T {
            width: parent.width
            visible: moment.has && moment.m.kind === "STEP"
            text: moment.has ? moment.m.title : ""
            font.family: Theme.mono; font.pixelSize: 13; color: Theme.dim
            wrapMode: Text.Wrap; maximumLineCount: 2
        }
        Text {
            width: parent.width
            text: moment.has ? moment.m.text : ""
            font.family: Theme.display; font.pixelSize: width < 300 ? 19 : 24
            lineHeight: 1.18
            color: Theme.ink
            wrapMode: Text.Wrap; maximumLineCount: 6; elide: Text.ElideRight
        }
        T {
            visible: moment.has && moment.m.at !== ""
            text: moment.has ? moment.m.at + " in" + (moment.m.secs ? ", took " + moment.m.secs.toFixed(1) + " s to decide" : "") : ""
            font.pixelSize: 12; color: Theme.faint
        }
        Btn { visible: !moment.following; text: town.busy ? "Back to now" : "Back to the end"; onPressed: moment.follow() }
    }
}
