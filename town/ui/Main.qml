import QtQuick
import QtQuick.Window

// The window: a rail, the page you are on, and a line along the bottom when there is something to say.
Window {
    id: root
    title: "Locals"
    color: Theme.night
    minimumWidth: 980
    minimumHeight: 620

    readonly property var pages: ["town", "setup", "days", "rooms", "report"]
    property string page: "town"
    property bool leaving: false

    onActiveChanged: if (active) town.refresh()
    onClosing: (close) => {
        if (town.busy && !leaving) {
            close.accepted = false
            strip.asking = true
        }
    }

    Shortcut { sequence: "Ctrl+1"; onActivated: root.page = "town" }
    Shortcut { sequence: "Ctrl+2"; onActivated: root.page = "setup" }
    Shortcut { sequence: "Ctrl+3"; onActivated: root.page = "days" }
    Shortcut { sequence: "Ctrl+4"; onActivated: root.page = "rooms" }
    Shortcut { sequence: "Ctrl+5"; onActivated: root.page = "report" }
    Shortcut { sequence: "F5"; onActivated: town.refresh() }
    Shortcut { sequence: "F11"; onActivated: root.visibility = root.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen }

    Rail {
        id: rail
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        page: root.page
        onPicked: (name) => root.page = name
    }

    Item {
        id: stage
        anchors { left: rail.right; right: parent.right; top: parent.top; bottom: strip.top }
        Setup { onStarted: root.page = "town"; anchors.fill: parent; opacity: root.page === "setup" ? 1 : 0; visible: opacity > 0
                Behavior on opacity { NumberAnimation { duration: 140 } } }
        Home { onSetUp: root.page = "setup"; anchors.fill: parent; opacity: root.page === "town" ? 1 : 0; visible: opacity > 0
               Behavior on opacity { NumberAnimation { duration: 140 } } }
        Days { onOpened: root.page = "town"; anchors.fill: parent; opacity: root.page === "days" ? 1 : 0; visible: opacity > 0
               Behavior on opacity { NumberAnimation { duration: 140 } } }
        Rooms { anchors.fill: parent; opacity: root.page === "rooms" ? 1 : 0; visible: opacity > 0
                Behavior on opacity { NumberAnimation { duration: 140 } } }
        Report { anchors.fill: parent; opacity: root.page === "report" ? 1 : 0; visible: opacity > 0
                 Behavior on opacity { NumberAnimation { duration: 140 } } }
    }

    Strip {
        id: strip
        anchors { left: rail.right; right: parent.right; bottom: parent.bottom }
        onStay: asking = false
        onLeave: { root.leaving = true; root.close() }
    }
}
