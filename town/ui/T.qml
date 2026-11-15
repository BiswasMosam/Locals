import QtQuick

// Body text everywhere.
Text {
    font.family: Theme.text
    font.pixelSize: 14
    color: Theme.ink
    renderType: Text.NativeRendering
    elide: Text.ElideRight
}
