pragma Singleton
import QtQuick

// One idea drives the look: a town at night, where a lit window is a local who is awake.
// Amber means awake or wants your attention, and nothing else is amber.
QtObject {
    readonly property color night: "#0c0e13"
    readonly property color rail: "#090b0f"
    readonly property color panel: "#10131a"
    readonly property color slab: "#161a24"
    readonly property color dark: "#1d2231"     // a window with nobody up
    readonly property color line: "#262c3b"
    readonly property color light: "#ffc94d"
    readonly property color waiting: "#6e5c2f"  // out today, not yet at work
    readonly property color ink: "#ebe7dc"
    readonly property color dim: "#8a8f9c"
    readonly property color faint: "#5a6070"
    readonly property color good: "#8fcf7a"
    readonly property color bad: "#d9826e"

    readonly property string text: "Segoe UI Variable Text"
    readonly property string display: "Segoe UI Variable Display"
    readonly property string small: "Segoe UI Variable Small"
    readonly property string mono: "Cascadia Mono"

    readonly property int gutter: 44

    function stateColor(s) {
        switch (s) {
        case "work": return light
        case "out": return waiting
        case "DONE": case "SAYS DONE": return good
        case "GAVE UP": case "ERROR": case "WRONG DONE": return bad
        case "ASKED": case "STOPPED": return dim
        default: return dark
        }
    }
    function stateWords(s) {
        switch (s) {
        case "work": return "at work now"
        case "out": return "going out today"
        case "DONE": return "got it done"
        case "SAYS DONE": return "says it is done"
        case "WRONG DONE": return "thought it was done, and it was not"
        case "GAVE UP": return "gave up"
        case "ASKED": return "asked someone for help"
        case "STOPPED": return "was stopped"
        case "ERROR": return "hit an error"
        default: return ""
        }
    }
}
