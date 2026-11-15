import QtQuick

// The line along the bottom: the day that is running or the talk being given, something that went wrong,
// or a question before closing.
Rectangle {
    id: strip
    property bool asking: false   // the window was asked to close while a day runs
    signal leave()
    signal stay()
    readonly property var now: town.now
    readonly property var talk: town.talk
    readonly property bool busy: town.busy
    onBusyChanged: if (!busy) asking = false   // it ended by itself; there is nothing left to ask
    readonly property string mode: asking ? "ask" : town.notice ? "notice" : now.running ? "live" : talk.running ? "talk" : ""
    readonly property bool shown: mode !== ""
    height: shown ? 60 : 0
    clip: true
    color: Theme.panel
    Behavior on height { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    Rectangle { width: parent.width; height: 1; color: mode === "notice" ? Theme.bad : Theme.line }

    property int seconds: 0
    Timer {
        running: strip.mode === "live" || strip.mode === "talk"; interval: 1000; repeat: true; triggeredOnStart: true
        onTriggered: strip.seconds = Math.max(0, Math.round(Date.now() / 1000 - (strip.mode === "talk" ? strip.talk.began : strip.now.began)))
    }
    function clock(s) { return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0") }
    function nameOf(id) {
        for (const f of town.families) for (const p of f.people) if (p.id === id) return p.name
        return id
    }

    // ---------- a day is running ----------
    Item {
        anchors.fill: parent; anchors.leftMargin: Theme.gutter; anchors.rightMargin: Theme.gutter
        visible: strip.mode === "live"
        Rectangle {
            id: lamp
            anchors.verticalCenter: parent.verticalCenter
            width: 8; height: 10; color: Theme.light
            SequentialAnimation on opacity {
                running: strip.mode === "live"; loops: Animation.Infinite
                NumberAnimation { to: 0.35; duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1; duration: 900; easing.type: Easing.InOutSine }
            }
        }
        Column {
            anchors { left: lamp.right; leftMargin: 16; right: tail.left; rightMargin: 24; verticalCenter: parent.verticalCenter }
            spacing: 2
            T {
                width: parent.width
                font.weight: Font.DemiBold
                text: (strip.now.index[1] > 1 ? "Day " + strip.now.index[0] + " of " + strip.now.index[1] + "  ·  " : "")
                      + strip.now.task + (strip.now.locals.length ? "  ·  " + strip.now.finished + " of " + strip.now.locals.length + " finished" : "")
            }
            T {
                width: parent.width
                color: Theme.dim; font.pixelSize: 13
                text: strip.now.stopping ? "Stopping. A step that has begun is finished first."
                    : strip.now.who ? strip.nameOf(strip.now.who) + (strip.now.step ? ", step " + strip.now.step : "") + ":  " + strip.now.line + (strip.now.thought ? "   " + strip.now.thought : "")
                    : strip.now.line || "Waiting for the first local."
            }
        }
        Row {
            id: tail
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            spacing: 18
            T { anchors.verticalCenter: parent.verticalCenter; text: strip.clock(strip.seconds); font.family: Theme.mono; color: Theme.dim }
            Btn { text: "Stop the day"; visible: !strip.now.stopping; onPressed: town.stop() }
        }
    }

    // ---------- a talk is being given ----------
    Item {
        anchors.fill: parent; anchors.leftMargin: Theme.gutter; anchors.rightMargin: Theme.gutter
        visible: strip.mode === "talk"
        Rectangle {
            id: talkLamp
            anchors.verticalCenter: parent.verticalCenter
            width: 8; height: 10; color: Theme.light
            SequentialAnimation on opacity {
                running: strip.mode === "talk"; loops: Animation.Infinite
                NumberAnimation { to: 0.35; duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1; duration: 900; easing.type: Easing.InOutSine }
            }
        }
        Column {
            anchors { left: talkLamp.right; leftMargin: 16; right: talkTail.left; rightMargin: 24; verticalCenter: parent.verticalCenter }
            spacing: 2
            T { width: parent.width; font.weight: Font.DemiBold; text: strip.talk.name + (strip.talk.source ? "  ·  " + strip.talk.source : "") }
            T { width: parent.width; color: Theme.dim; font.pixelSize: 13; text: strip.talk.head + (strip.talk.sub ? "  " + strip.talk.sub : "") }
        }
        Row {
            id: talkTail
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            spacing: 18
            T { anchors.verticalCenter: parent.verticalCenter; text: strip.clock(strip.seconds); font.family: Theme.mono; color: Theme.dim }
            Btn { text: "Stop the talk"; visible: !strip.talk.stopping; onPressed: town.stop() }
        }
    }

    // ---------- something went wrong ----------
    Item {
        anchors.fill: parent; anchors.leftMargin: Theme.gutter; anchors.rightMargin: Theme.gutter
        visible: strip.mode === "notice"
        T { anchors { left: parent.left; right: ok.left; rightMargin: 24; verticalCenter: parent.verticalCenter } text: town.notice; color: Theme.bad }
        Btn { id: ok; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "Dismiss"; onPressed: town.dismiss() }
    }

    // ---------- closing with a day still running ----------
    Item {
        anchors.fill: parent; anchors.leftMargin: Theme.gutter; anchors.rightMargin: Theme.gutter
        visible: strip.mode === "ask"
        T { anchors { left: parent.left; right: answers.left; rightMargin: 24; verticalCenter: parent.verticalCenter }
            text: strip.talk.running ? "A talk is still being given. Closing the window stops it, and nothing of it is kept."
                                     : "A day is still running. Closing the window stops it." }
        Row {
            id: answers
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Btn { text: "Keep it running"; onPressed: strip.stay() }
            Btn { text: "Stop and close"; strong: true; onPressed: strip.leave() }
        }
    }
}
