import QtQuick

// The town. With no day on the page it is the town at a glance; with one, it is that day: the screen the
// local is looking at and what they think, the town below, and a strip and a feed beside it.
Item {
    id: home
    signal setUp()
    readonly property var now: town.now
    readonly property bool day: now.open
    readonly property int total: town.families.reduce((n, f) => n + f.people.length, 0)

    // The feed, and which moment of it is on the left.
    ListModel { id: feed }
    property int sel: -1                  // a moment somebody picked; -1 follows the newest
    property int newest: -1               // the newest moment with a screen, or just the newest
    readonly property int shown: sel >= 0 ? sel : newest
    property var current: null

    property string only: ""

    function show() { current = shown >= 0 && shown < feed.count ? feed.get(shown) : null }
    onShownChanged: show()
    function take(m) {
        feed.append(m)
        if (m.shot !== "" || newest < 0 || feed.get(newest).shot === "") newest = m.i
    }
    function restart() {
        feed.clear()
        sel = -1; newest = -1; only = ""
        viewer.visible = false
        for (const m of town.moments) take(m)
        show()
    }
    Connections {
        target: town
        function onDayReset() { home.restart() }
        function onHeard(m) { home.take(m) }
    }
    Component.onCompleted: restart()

    // The town celebrates a day that went well, once, when it ends; not a kept day opened later.
    readonly property bool won: !now.running && !now.kept && now.verdict.win
    onWonChanged: if (won) sky.celebrate()

    function nameOf(id) {
        for (const f of town.families) for (const p of f.people) if (p.id === id) return p.name
        return id
    }
    readonly property string headline: {
        if (now.running && now.who) return nameOf(now.who) + " is out."
        if (now.running) return now.stopping ? "Calling everyone home." : "The day is starting."
        if (day && now.verdict.head) return now.verdict.head
        if (day) return Object.values(now.states).some(s => s === "STOPPED") ? "The day was stopped." : "The day is over."
        return "Everyone is home."
    }
    readonly property string under: {
        const when = (now.index[1] > 1 ? "Day " + now.index[0] + " of " + now.index[1] + "  ·  " : "") + now.task + (now.today ? "  ·  " + now.today : "")
        if (now.running) return when
        if (day && now.verdict.head) return now.verdict.sub + (now.verdict.note ? "  " + now.verdict.note : "")
        if (day) return when
        return total + " locals in " + town.families.length + " families.  " + town.taskCount + " tasks ready."
    }

    // ---------- left ----------
    Item {
        id: left
        anchors { left: parent.left; right: side.left; top: parent.top; bottom: parent.bottom
                  leftMargin: Theme.gutter; rightMargin: Theme.gutter; topMargin: 38; bottomMargin: 32 }

        Heading { id: over; text: home.day && !home.now.running ? home.now.task + (home.now.today ? "  ·  " + home.now.today : "") : "The town" }
        Text {
            id: head
            anchors.top: over.bottom; anchors.topMargin: 10
            width: parent.width
            text: home.headline
            font.family: Theme.display; font.pixelSize: home.day ? 30 : 40; font.weight: Font.DemiBold
            color: home.won ? Theme.light : Theme.ink
            elide: Text.ElideRight
        }
        T {
            id: sub
            anchors.top: head.bottom; anchors.topMargin: 6
            width: parent.width
            text: home.under
            font.pixelSize: home.day ? 14 : 16; color: Theme.dim
        }

        Btn {
            anchors.top: sub.bottom; anchors.topMargin: 22
            visible: !home.day && !home.now.running
            strong: true
            text: "Set up a day"
            onPressed: home.setUp()
        }

        // Who the pointer is on, in a fixed place so nothing jumps or covers the windows.
        Item {
            id: who
            anchors.bottom: parent.bottom
            width: parent.width; height: 44
            readonly property var p: sky.looking
            Rectangle { width: parent.width; height: 1; color: Theme.line }
            T {
                y: 14; width: parent.width
                visible: !!who.p
                text: who.p ? String(who.p.number).padStart(2, "0") + "  " + who.p.name + ", " + who.p.age
                      + "  ·  " + who.p.job + "  ·  on a " + who.p.device
                      + "  ·  reads " + who.p.reads + " words, " + who.p.patience + " steps of patience"
                      + (Theme.stateWords(home.now.states[who.p.id] || "") ? "  ·  " + Theme.stateWords(home.now.states[who.p.id]) : "")
                      : ""
            }
            T { y: 14; visible: !who.p; color: Theme.faint; text: "One window, one local." }
        }

        Skyline {
            id: sky
            anchors { bottom: who.top; bottomMargin: 20 }
            width: parent.width
            // With a day on the page the town steps back to a band along the bottom, and off a short window altogether.
            readonly property real band: left.height < 520 ? 0 : Math.max(120, Math.min(190, left.height * 0.24))
            height: home.day ? band : Math.max(0, left.height - sub.y - sub.height - 78 - who.height - 20)
            visible: height > 0
            Behavior on height { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
            states: home.now.states
            only: home.only
            onPicked: (id) => home.only = home.only === id ? "" : id
        }

        Moment {
            anchors { top: sub.bottom; topMargin: 22; bottom: sky.visible ? sky.top : who.top; bottomMargin: 22 }
            width: parent.width
            visible: opacity > 0
            opacity: home.day ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 200 } }
            m: home.current
            following: home.sel < 0
            onFollow: home.sel = -1
            onEnlarge: viewer.open(home.shown)
        }
    }

    // ---------- right ----------
    Item {
        id: side
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: Math.max(320, Math.min(400, home.width * 0.3))
        Rectangle { width: 1; height: parent.height; color: Theme.line }
        MachineSide { anchors.fill: parent; visible: !home.day }
        DaySide {
            anchors.fill: parent
            visible: home.day
            feed: feed
            sel: home.sel
            shown: home.shown
            only: home.only
            onPick: (i) => home.sel = i
            onNarrow: (id) => home.only = (id === "" || home.only === id) ? "" : id
        }
    }

    Viewer {
        id: viewer
        anchors.fill: parent
        feed: feed
        onMoved: (i) => home.sel = i
    }
}
