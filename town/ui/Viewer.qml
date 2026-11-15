import QtQuick

// One local's screens at full size, one after another. Left and right move; Esc closes.
Rectangle {
    id: viewer
    property var feed: null
    property var steps: []     // feed indexes of this local's moments that have a screen
    property int at: 0
    readonly property var m: visible && steps.length ? feed.get(steps[at]) : null
    signal moved(int i)
    visible: false
    color: Theme.night

    function open(i) {
        const who = feed.get(i).local, found = []
        for (let k = 0; k < feed.count; k++) if (feed.get(k).local === who && feed.get(k).shot !== "") found.push(k)
        if (!found.length) return
        steps = found
        at = Math.max(0, found.indexOf(i))
        visible = true
        forceActiveFocus()
    }
    function go(d) {
        at = Math.max(0, Math.min(steps.length - 1, at + d))
        moved(steps[at])
    }
    Keys.onEscapePressed: visible = false
    Keys.onLeftPressed: go(-1)
    Keys.onRightPressed: go(1)
    TapHandler {}   // a click on the dark around the screen goes nowhere else

    Image {
        id: big
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 28 }
        width: Math.min(parent.width * 0.68, status === Image.Ready ? (parent.height - 56) * implicitWidth / Math.max(1, implicitHeight) : parent.width * 0.3)
        source: viewer.m ? town.root + viewer.m.shot : ""
        fillMode: Image.PreserveAspectFit
        horizontalAlignment: Image.AlignLeft
        asynchronous: true
        smooth: true; mipmap: true
    }
    Column {
        anchors { left: big.right; leftMargin: 36; right: parent.right; rightMargin: Theme.gutter; verticalCenter: parent.verticalCenter }
        spacing: 12
        Heading {
            text: viewer.m ? viewer.m.name + "  ·  " + (viewer.m.kind === "STEP" ? "step " + viewer.m.step : viewer.m.kind) : ""
            color: !viewer.m ? Theme.dim : viewer.m.tone === "warn" ? Theme.light : viewer.m.tone === "good" ? Theme.good : viewer.m.tone === "bad" ? Theme.bad : Theme.dim
        }
        T {
            width: parent.width
            visible: !!viewer.m && viewer.m.kind === "STEP"
            text: viewer.m ? viewer.m.title : ""
            font.family: Theme.mono; font.pixelSize: 13; color: Theme.dim
            wrapMode: Text.Wrap
        }
        Text {
            width: parent.width
            text: viewer.m ? viewer.m.text : ""
            font.family: Theme.display; font.pixelSize: 24; lineHeight: 1.18
            color: Theme.ink
            wrapMode: Text.Wrap
        }
        Row {
            topPadding: 14
            spacing: 8
            Btn { text: "Earlier"; opacity: viewer.at > 0 ? 1 : 0.4; onPressed: viewer.go(-1) }
            Btn { text: "Later"; opacity: viewer.at < viewer.steps.length - 1 ? 1 : 0.4; onPressed: viewer.go(1) }
            Btn { text: "Close"; onPressed: viewer.visible = false }
        }
        T { text: (viewer.at + 1) + " of " + viewer.steps.length; font.pixelSize: 12; color: Theme.faint; font.family: Theme.mono }
    }
}
