import QtQuick

// Beside the town when no day is on the page: what this machine has to spend, and the days kept.
Item {
    id: side
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
