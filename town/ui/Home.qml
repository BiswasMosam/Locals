import QtQuick

// The town at a glance: every local is a window, every family a building. A lit window is someone awake.
Item {
    id: home
    readonly property var now: town.now
    readonly property int total: town.families.reduce((n, f) => n + f.people.length, 0)
    property var looking: null    // the local under the pointer

    function nameOf(id) {
        for (const f of town.families) for (const p of f.people) if (p.id === id) return p.name
        return id
    }
    readonly property string headline: {
        if (now.running && now.who) return nameOf(now.who) + " is out."
        if (now.running) return now.stopping ? "Calling everyone home." : "The day is starting."
        if (now.locals && now.locals.length) {
            if (now.locals.some(i => now.states[i] === "STOPPED")) return "The day was stopped."
            const done = now.locals.filter(i => now.states[i] === "DONE" || now.states[i] === "SAYS DONE").length
            return done + " of " + now.locals.length + " got it done."
        }
        return "Everyone is home."
    }
    readonly property string under: {
        if (now.running && now.who) return now.task + (now.step ? "  ·  step " + now.step : "")
        if (now.running) return now.task
        if (now.locals && now.locals.length) return now.task + (now.today ? "  ·  " + now.today : "")
        return total + " locals in " + town.families.length + " families.  " + town.taskCount + " tasks ready."
    }

    // ---------- left: the skyline ----------
    Item {
        id: left
        anchors { left: parent.left; right: side.left; top: parent.top; bottom: parent.bottom
                  leftMargin: Theme.gutter; rightMargin: Theme.gutter; topMargin: 38; bottomMargin: 32 }

        Heading { id: over; text: "The town" }
        Text {
            id: head
            anchors.top: over.bottom; anchors.topMargin: 10
            width: parent.width
            text: home.headline
            font.family: Theme.display; font.pixelSize: 40; font.weight: Font.DemiBold
            color: Theme.ink; elide: Text.ElideRight
        }
        T {
            id: sub
            anchors.top: head.bottom; anchors.topMargin: 6
            width: parent.width
            text: home.under
            font.pixelSize: 16; color: Theme.dim
        }

        // Who the pointer is on, in a fixed place so nothing jumps or covers the windows.
        Item {
            id: who
            anchors.bottom: parent.bottom
            width: parent.width; height: 44
            Rectangle { width: parent.width; height: 1; color: Theme.line }
            T {
                y: 14; width: parent.width
                visible: !!home.looking
                text: home.looking ? String(home.looking.number).padStart(2, "0") + "  " + home.looking.name + ", " + home.looking.age
                      + "  ·  " + home.looking.job + "  ·  on a " + home.looking.device
                      + "  ·  reads " + home.looking.reads + " words, " + home.looking.patience + " steps of patience"
                      + (Theme.stateWords(home.now.states[home.looking.id] || "") ? "  ·  " + Theme.stateWords(home.now.states[home.looking.id]) : "")
                      : ""
            }
            T { y: 14; visible: !home.looking; color: Theme.faint; text: "One window, one local." }
        }

        Item {
            id: sky
            anchors { top: sub.bottom; bottom: who.top; topMargin: 24; bottomMargin: 20 }
            width: parent.width
            readonly property int count: Math.max(1, town.families.length)
            readonly property int cols: 3
            readonly property int tallest: Math.ceil(town.families.reduce((n, f) => Math.max(n, f.people.length), 1) / cols)
            // Every family gets the same share of the street; one size for every window, as big as that
            // share and the tallest building allow.
            readonly property real slot: Math.floor(width / count)
            readonly property real unit: Math.max(7, Math.min(26,
                slot * 0.86 / (cols * 1.36 + 0.36),
                (height - 46) / (tallest * 1.62 + 0.36)))
            readonly property real gap: Math.round(unit * 0.36)
            readonly property real win: Math.round(unit)
            readonly property real tall: Math.round(unit * 1.26)

            Row {
                anchors.bottom: parent.bottom
                Repeater {
                    model: town.families
                    Column {
                        id: building
                        required property var modelData
                        anchors.bottom: parent.bottom
                        width: sky.slot
                        spacing: 10
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: sky.cols * (sky.win + sky.gap) + sky.gap
                            height: Math.ceil(building.modelData.people.length / sky.cols) * (sky.tall + sky.gap) + sky.gap
                            color: Theme.panel
                            Repeater {
                                model: building.modelData.people
                                Rectangle {
                                    id: pane
                                    required property var modelData
                                    required property int index
                                    readonly property string state_: home.now.states[modelData.id] || ""
                                    x: sky.gap + (index % sky.cols) * (sky.win + sky.gap)
                                    // From the ground up, so a floor that is not full is the top one.
                                    y: parent.height - (Math.floor(index / sky.cols) + 1) * (sky.tall + sky.gap)
                                    width: sky.win; height: sky.tall
                                    color: Theme.stateColor(state_)
                                    Behavior on color { ColorAnimation { duration: 320 } }
                                    border.width: point.hovered ? 1 : 0
                                    border.color: Theme.ink
                                    // Someone at work: the light is steady, with the slow waver of a lamp.
                                    SequentialAnimation on opacity {
                                        running: pane.state_ === "work"
                                        loops: Animation.Infinite
                                        alwaysRunToEnd: true
                                        NumberAnimation { to: 0.72; duration: 900; easing.type: Easing.InOutSine }
                                        NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
                                    }
                                    HoverHandler {
                                        id: point
                                        onHoveredChanged: {
                                            if (hovered) home.looking = pane.modelData
                                            else if (home.looking === pane.modelData) home.looking = null
                                        }
                                    }
                                }
                            }
                        }
                        Column {
                            anchors.horizontalCenter: parent.horizontalCenter
                            spacing: 1
                            T { anchors.horizontalCenter: parent.horizontalCenter; width: Math.min(implicitWidth, sky.slot - 4); text: building.modelData.family; font.pixelSize: sky.slot < 76 ? 10 : 12; color: Theme.dim }
                            T { anchors.horizontalCenter: parent.horizontalCenter; text: building.modelData.people.length; font.pixelSize: 12; color: Theme.faint; font.family: Theme.mono }
                        }
                    }
                }
            }
        }
    }

    // ---------- right: this machine, and the days kept ----------
    Rectangle {
        id: side
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: Math.max(320, Math.min(400, home.width * 0.3))
        color: Theme.night
        Rectangle { width: 1; height: parent.height; color: Theme.line }

        readonly property var m: town.machine
        readonly property var model: m.model || ({})

        Column {
            id: facts
            anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 32; rightMargin: 32; topMargin: 38 }
            spacing: 6
            Heading { text: "This machine"; bottomPadding: 10 }
            Meter {
                name: "Model"
                trouble: !side.model.reachable || !side.model.installed
                value: !side.model.reachable ? "Ollama is not running"
                     : !side.model.installed ? "Not downloaded: ollama pull " + side.model.name
                     : side.model.name + (side.model.loaded ? ", loaded" : "")
            }
            Meter {
                visible: !!side.m.gpu
                name: "GPU memory"
                value: side.m.gpu ? side.m.gpu.used_gb.toFixed(1) + " of " + side.m.gpu.total_gb.toFixed(0) + " GB in use" : ""
                part: side.m.gpu ? side.m.gpu.used_gb / side.m.gpu.total_gb : -1
            }
            Meter { visible: !side.m.gpu; name: "GPU"; value: "None found. The model runs on the processor." }
            Meter {
                visible: !!side.m.memory
                name: "Memory"
                value: side.m.memory ? side.m.memory.used_gb.toFixed(0) + " of " + side.m.memory.total_gb.toFixed(0) + " GB in use" : ""
                part: side.m.memory ? side.m.memory.used_gb / side.m.memory.total_gb : -1
            }
            Meter {
                name: "Pace"
                value: side.m.pace ? side.m.pace.secs_per_step + " s a step" + (side.m.pace.measured ? ", measured here" : ", a guess until a day runs") : ""
            }
            Meter {
                name: "Android"
                value: !side.m.android ? "" : !side.m.android.adb ? "adb not found" : side.m.android.devices.length ? side.m.android.devices.join(", ") : "Nothing connected"
            }
        }

        Heading { id: daysHead; anchors { left: facts.left; top: facts.bottom; topMargin: 34 } text: "Recent days" }
        T {
            anchors { left: facts.left; top: daysHead.bottom; topMargin: 14 }
            visible: town.days.length === 0
            color: Theme.faint
            text: "No day has been run yet."
        }
        ListView {
            anchors { left: facts.left; right: facts.right; top: daysHead.bottom; bottom: parent.bottom; topMargin: 8; bottomMargin: 16 }
            clip: true
            interactive: false
            model: town.days.slice(0, Math.max(0, Math.floor(height / 52)))
            delegate: DayRow {}
        }
    }
}
