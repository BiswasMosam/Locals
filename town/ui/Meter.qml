import QtQuick

// One fact about this machine: a name, a value, and a bar when the value is part of a whole.
Item {
    id: meter
    property string name: ""
    property string value: ""
    property real part: -1        // 0 to 1, or -1 for no bar
    property bool trouble: false
    implicitHeight: part >= 0 ? 44 : 30
    width: parent ? parent.width : 0

    T { text: meter.name; color: Theme.dim }
    T {
        anchors.right: parent.right
        width: parent.width * 0.68
        horizontalAlignment: Text.AlignRight
        text: meter.value
        color: meter.trouble ? Theme.bad : Theme.ink
    }
    Rectangle {
        visible: meter.part >= 0
        y: 28; width: parent.width; height: 4
        color: Theme.dark
        Rectangle {
            height: parent.height
            width: parent.width * Math.max(0, Math.min(1, meter.part))
            color: meter.part > 0.9 ? Theme.bad : Theme.dim
            Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
        }
    }
}
