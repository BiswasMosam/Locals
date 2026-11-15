import QtQuick

// The town: every local is a window, every family a building. A lit window is someone awake.
Item {
    id: sky
    property var states: ({})        // local id -> where they are in the day
    property string only: ""         // the one local the feed is narrowed to, if any
    property var looking: null       // the local under the pointer
    signal picked(string id)

    readonly property int count: Math.max(1, town.families.length)
    readonly property int cols: 3
    readonly property int tallest: Math.ceil(town.families.reduce((n, f) => Math.max(n, f.people.length), 1) / cols)
    // Every family gets the same share of the street; one size for every window, as big as that
    // share and the tallest building allow.
    readonly property real slot: Math.floor(width / count)
    readonly property real unit: Math.max(5, Math.min(26,
        slot * 0.86 / (cols * 1.36 + 0.36),
        (height - 46) / (tallest * 1.62 + 0.36)))
    readonly property real gap: Math.max(2, Math.round(unit * 0.36))
    readonly property real win: Math.round(unit)
    readonly property real tall: Math.round(unit * 1.26)

    // When the app is great, the lights of the whole town come on in a wave, left to right, twice.
    property real wave: -1
    function celebrate() { party.restart() }
    SequentialAnimation {
        id: party
        loops: 2
        NumberAnimation { target: sky; property: "wave"; from: -0.2; to: 1.2; duration: 1700; easing.type: Easing.InOutSine }
        onFinished: sky.wave = -1
    }

    Row {
        anchors.bottom: parent.bottom
        Repeater {
            model: town.families
            Column {
                id: building
                required property var modelData
                required property int index
                readonly property real place: (index + 0.5) / sky.count
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
                            readonly property string where: sky.states[modelData.id] || ""
                            readonly property bool swept: sky.wave >= 0 && Math.abs(sky.wave - building.place) < 0.11
                            x: sky.gap + (index % sky.cols) * (sky.win + sky.gap)
                            // From the ground up, so a floor that is not full is the top one.
                            y: parent.height - (Math.floor(index / sky.cols) + 1) * (sky.tall + sky.gap)
                            width: sky.win; height: sky.tall
                            color: swept ? Theme.light : Theme.stateColor(where)
                            Behavior on color { ColorAnimation { duration: 320 } }
                            border.width: point.hovered || sky.only === modelData.id ? 1 : 0
                            border.color: Theme.ink
                            // Someone at work: the light is steady, with the slow waver of a lamp.
                            SequentialAnimation on opacity {
                                running: pane.where === "work"
                                loops: Animation.Infinite
                                alwaysRunToEnd: true
                                NumberAnimation { to: 0.72; duration: 900; easing.type: Easing.InOutSine }
                                NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
                            }
                            HoverHandler {
                                id: point
                                cursorShape: pane.where ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onHoveredChanged: {
                                    if (hovered) sky.looking = pane.modelData
                                    else if (sky.looking === pane.modelData) sky.looking = null
                                }
                            }
                            TapHandler { enabled: pane.where !== ""; onTapped: sky.picked(pane.modelData.id) }
                        }
                    }
                }
                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 1
                    T { anchors.horizontalCenter: parent.horizontalCenter; width: Math.min(implicitWidth, sky.slot - 4)
                        text: building.modelData.family; font.pixelSize: sky.slot < 76 ? 10 : 12; color: Theme.dim }
                    T { anchors.horizontalCenter: parent.horizontalCenter; text: building.modelData.people.length
                        font.pixelSize: 12; color: Theme.faint; font.family: Theme.mono }
                }
            }
        }
    }
}
