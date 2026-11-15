import QtQuick

// A small picture made of squares, like the mark: each square is a window.
Item {
    id: pix
    property var rows: []
    property color color: Theme.ink
    property int cell: 3
    implicitWidth: rows.length ? rows[0].length * cell : 0
    implicitHeight: rows.length * cell

    Repeater {
        model: pix.rows.length ? pix.rows.length * pix.rows[0].length : 0
        Rectangle {
            required property int index
            readonly property int cols: pix.rows[0].length
            x: (index % cols) * pix.cell
            y: Math.floor(index / cols) * pix.cell
            width: pix.cell; height: pix.cell
            color: pix.color
            visible: pix.rows[Math.floor(index / cols)][index % cols] === "X"
        }
    }
}
