import QtQuick
import QtQuick.Dialogs

// Rooms: give a talk to a room of locals. With no talk on the page it is where one is set up; with one, it is
// that talk: a window for every listener in every part, lit while they are with you and dark once they are gone.
Item {
    id: page
    objectName: "rooms"
    readonly property var talk: town.talk
    readonly property bool open: talk.open || talk.running

    // ---------- what was chosen ----------
    property string roomId: town.rooms.length ? town.rooms[0].id : ""
    readonly property var room: town.rooms.find(r => r.id === roomId) || null
    property var deck: null
    property var speech: null
    property bool grade: true
    property string error: ""
    readonly property string blocked: town.busy ? town.busyWith : town.modelProblem
    readonly property bool ready: (!!deck || !!speech) && !!room && blocked === ""

    function add(url) {
        const kept = town.keepFile(url)
        if (kept.error) { error = kept.error; return }
        const name = kept.name.toLowerCase()
        if (/\.(pdf|pptx)$/.test(name)) deck = kept
        else if (/\.(txt|md|wav|mp3|m4a|ogg|flac|webm|aac|mp4)$/.test(name)) speech = kept
        else { error = "That is not a deck (.pdf or .pptx), a script (.txt or .md) or a recording."; return }
        error = ""
    }
    function start() {
        const files = []
        if (deck) files.push(deck.path)
        if (speech) files.push(speech.path)
        error = town.startTalk({ room: roomId, files: files, minutes: minutesField.text.trim(), point: pointField.text.trim(),
                                 about: aboutField.text.trim(), grade: grade })
    }

    // ---------- the talk on the page ----------
    property int sel: -1                      // a part somebody picked; -1 follows the newest
    readonly property string talkId: talk.talk
    onTalkIdChanged: sel = -1
    readonly property int shown: sel >= 0 && sel < talk.parts.length ? sel : talk.running ? talk.at : talk.parts.length - 1
    readonly property var part: shown >= 0 && shown < talk.parts.length ? talk.parts[shown] : null
    property var looking: null                // the listener the pointer is on

    function lit(tone) {
        return tone === "hooked" ? Theme.light : tone === "with" ? Theme.waiting : tone === "drift" ? Theme.step
             : tone === "low" ? Theme.dark : "transparent"
    }
    function sameColor(s) { return s === "yes" ? Theme.good : s === "partly" ? Theme.dim : s === "no" ? Theme.bad : Theme.faint }
    function sameWords(s) { return s === "yes" ? "has your point" : s === "partly" ? "has part of it" : s === "no" ? "does not have it" : "" }

    FileDialog { id: pick; title: "The talk: a deck, a script or a recording"; fileMode: FileDialog.OpenFiles
                 nameFilters: ["Talks (*.pdf *.pptx *.txt *.md *.wav *.mp3 *.m4a *.ogg *.flac *.webm *.aac *.mp4)"]
                 onAccepted: { for (const f of selectedFiles) page.add(f.toString()) } }

    // ================= setting one up =================
    Item {
        id: setup
        anchors.fill: parent
        visible: opacity > 0
        opacity: page.open ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: 140 } }
        readonly property real col: (width - Theme.gutter * 2 - 2 * 56) / 3

        // ---- the room ----
        Item {
            id: where
            x: Theme.gutter; y: 38
            width: setup.col; height: parent.height - 38 - 28

            Heading { id: whereHead; text: "The room" }
            Column {
                id: roomList
                anchors.top: whereHead.bottom; anchors.topMargin: 14
                width: parent.width
                Repeater {
                    model: town.rooms
                    Item {
                        id: card
                        required property var modelData
                        readonly property bool on: page.roomId === modelData.id
                        width: roomList.width; height: 34
                        Rectangle { anchors.fill: parent; radius: 3; color: card.on ? Theme.dark : hov.hovered ? Theme.panel : "transparent" }
                        T { x: 10; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 90; text: card.modelData.name; color: card.on ? Theme.ink : Theme.dim }
                        T { anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                            text: card.modelData.minutes + " min"; font.family: Theme.mono; font.pixelSize: 12; color: card.on ? Theme.dim : Theme.faint }
                        HoverHandler { id: hov; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: page.roomId = card.modelData.id }
                    }
                }
            }
            Column {
                id: roomWords
                anchors { top: roomList.bottom; topMargin: 18 }
                width: parent.width
                spacing: 6
                T { width: parent.width; text: page.room ? page.room.about + "." : ""; wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.25 }
                T { width: parent.width; color: Theme.dim; wrapMode: Text.Wrap; maximumLineCount: 4; lineHeight: 1.25
                    text: page.room ? page.room.where + ". " + page.room.when + "." : "" }
                T { width: parent.width; color: Theme.dim; wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.25
                    text: !page.room ? "" : (page.room.rubric ? "Marked on " + page.room.rubric.toLowerCase() + ", out of " + page.room.out_of + "." : "A crowd gives no marks.")
                          + (page.room.point_by ? " This room expects your point within " + page.room.point_by + (page.room.point_by === 1 ? " minute." : " minutes.") : "") }
            }
            Heading { id: seatsHead; anchors { top: roomWords.bottom; topMargin: 24 } text: "Who sits there" }
            ListView {
                anchors { top: seatsHead.bottom; topMargin: 8; bottom: parent.bottom; left: parent.left; right: parent.right }
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: page.room ? page.room.seats : []
                delegate: Item {
                    id: seat
                    required property var modelData
                    width: ListView.view.width; height: 46
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width
                        spacing: 1
                        T { width: parent.width; text: seat.modelData.name + (seat.modelData.grader ? "  ·  marks" : "") + (seat.modelData.job ? "  ·  " + seat.modelData.job : "") }
                        T { width: parent.width; font.pixelSize: 12; color: Theme.faint; text: seat.modelData.why + "." }
                    }
                }
            }
        }

        // ---- the talk ----
        Column {
            id: what
            x: where.x + setup.col + 56; y: 38
            width: setup.col
            spacing: 8

            Heading { text: "The talk"; bottomPadding: 8 }
            Rectangle {
                width: parent.width; height: 96; radius: 3
                color: drop.containsDrag ? Theme.dark : Theme.panel
                border.width: 1; border.color: drop.containsDrag ? Theme.dim : Theme.line
                Column {
                    anchors { left: parent.left; right: parent.right; margins: 14; verticalCenter: parent.verticalCenter }
                    spacing: 5
                    T { width: parent.width; visible: !page.deck && !page.speech; text: "Drop the talk here, or choose it" }
                    T { width: parent.width; visible: !page.deck && !page.speech; color: Theme.dim; font.pixelSize: 13; wrapMode: Text.Wrap; maximumLineCount: 2
                        text: "A deck (.pdf or .pptx), what is said (.txt, .md or a recording), or one of each." }
                    T { width: parent.width; visible: !!page.deck; text: page.deck ? "Slides   " + page.deck.name : "" }
                    T { width: parent.width; visible: !!page.speech; text: page.speech ? "Said   " + page.speech.name : "" }
                    T { width: parent.width; visible: (!!page.deck) !== (!!page.speech); color: Theme.faint; font.pixelSize: 12
                        text: page.deck ? "No script: what is said comes from the speaker notes, if the deck has them." : "No deck: the room only hears you." }
                }
                DropArea { id: drop; anchors.fill: parent; onDropped: (d) => { for (const u of d.urls) page.add(u.toString()) } }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: pick.open() }
            }
            Chip { visible: !!page.deck || !!page.speech; on: true; text: "Clear"; onToggled: { page.deck = null; page.speech = null; page.error = "" } }

            T { topPadding: 8; text: "How long it runs, in minutes"; color: Theme.dim; font.pixelSize: 13 }
            Field { id: minutesField; width: 120; mono: true; hint: page.room ? String(page.room.minutes) : "" }
            T { width: parent.width; color: Theme.faint; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2
                text: "Left empty, a script is timed at 150 words a minute. A recording times itself." }

            T { topPadding: 8; text: "The one thing they should take away"; color: Theme.dim; font.pixelSize: 13 }
            Field { id: pointField; width: parent.width; tall: true; hint: "Left empty, it is read from the talk." }

            T { topPadding: 8; text: "What the talk is for"; color: Theme.dim; font.pixelSize: 13 }
            Field { id: aboutField; width: parent.width; hint: "The role you are interviewing for" }

            Chip { visible: !!page.room && page.room.rubric !== ""
                   text: (page.grade ? "●  " : "○  ") + "Let the graders mark it"; on: page.grade; onToggled: page.grade = !page.grade }
            T {
                width: parent.width; topPadding: 6
                visible: text !== ""
                text: page.error || page.blocked
                color: Theme.bad; wrapMode: Text.Wrap; maximumLineCount: 4
            }
            Btn {
                width: parent.width; height: 46
                strong: page.ready
                opacity: page.ready ? 1 : 0.6
                text: !page.deck && !page.speech ? "Choose the talk" : page.room ? "Give the talk to " + page.room.seats.length : "Choose a room"
                onPressed: if (page.ready) page.start()
            }
        }

        // ---- kept talks ----
        Item {
            x: what.x + setup.col + 56; y: 38
            width: setup.col; height: parent.height - 38

            Heading { id: keptHead; text: "Kept talks" }
            T { anchors { top: keptHead.bottom; topMargin: 14 } visible: town.talks.length === 0; color: Theme.faint; text: "No talk has been given yet." }
            ListView {
                id: kept
                anchors { top: keptHead.bottom; topMargin: 8; bottom: parent.bottom; left: parent.left; right: parent.right }
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: town.talks
                delegate: Item {
                    id: row
                    required property var modelData
                    width: kept.width; height: 58
                    Rectangle { anchors.fill: parent; anchors.leftMargin: -12; anchors.rightMargin: -12; radius: 3; color: over.hovered && !town.busy ? Theme.panel : "transparent" }
                    Column {
                        id: when
                        anchors.verticalCenter: parent.verticalCenter
                        width: 70
                        T { text: Qt.formatDate(new Date(row.modelData.date + "T12:00:00"), "d MMM"); color: Theme.dim; font.pixelSize: 13 }
                        T { text: row.modelData.time; color: Theme.faint; font.pixelSize: 12; font.family: Theme.mono }
                    }
                    Column {
                        anchors { left: when.right; right: parent.right; verticalCenter: parent.verticalCenter }
                        spacing: 3
                        Item {
                            width: parent.width; height: 19
                            T { width: parent.width - result.width - 12; text: row.modelData.name }
                            T { id: result; anchors.right: parent.right; text: row.modelData.mark || row.modelData.got
                                font.pixelSize: 13; color: row.modelData.mark ? Theme.ink : Theme.dim }
                        }
                        T { width: parent.width; color: Theme.dim; font.pixelSize: 13; text: row.modelData.source + "  ·  " + row.modelData.clock }
                        Row {
                            spacing: 4
                            Repeater {
                                model: row.modelData.lit
                                Rectangle { required property string modelData; width: 7; height: 9; color: page.lit(modelData)
                                            border.width: modelData === "out" ? 1 : 0; border.color: Theme.dark }
                            }
                        }
                    }
                    HoverHandler { id: over; cursorShape: town.busy ? Qt.ArrowCursor : Qt.PointingHandCursor }
                    TapHandler { enabled: !town.busy; onTapped: town.openTalk(row.modelData.talk) }
                }
            }
        }
    }

    // ================= the talk =================
    Item {
        id: view
        anchors.fill: parent
        visible: opacity > 0
        opacity: page.open ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 140 } }

        // ---------- left: the room, part by part ----------
        Item {
            id: left
            anchors { left: parent.left; right: side.left; top: parent.top; bottom: parent.bottom
                      leftMargin: Theme.gutter; rightMargin: Theme.gutter; topMargin: 38; bottomMargin: 32 }

            Heading { id: over2; text: page.talk.name + (page.talk.source ? "  ·  " + page.talk.source : "") + (page.talk.parts.length ? "  ·  " + page.talk.clock : "") }
            Text {
                id: head
                anchors.top: over2.bottom; anchors.topMargin: 10
                width: parent.width
                text: page.talk.head
                font.family: Theme.display; font.pixelSize: 30; font.weight: Font.DemiBold
                color: Theme.ink
                elide: Text.ElideRight
            }
            T { id: sub; anchors.top: head.bottom; anchors.topMargin: 6; width: parent.width; text: page.talk.sub; color: Theme.dim }

            Column {
                id: pointBlock
                anchors.top: sub.bottom; anchors.topMargin: 26
                width: parent.width
                spacing: 5
                visible: page.talk.point !== ""
                Heading { text: "Your point" }
                T { width: parent.width; text: page.talk.point; font.pixelSize: 16; wrapMode: Text.Wrap; maximumLineCount: 2 }
                T { width: parent.width; text: page.talk.stated; color: Theme.dim; font.pixelSize: 13 }
            }

            // A row for each listener, a window for each part.
            Item {
                id: grid
                anchors { top: pointBlock.visible ? pointBlock.bottom : sub.bottom; topMargin: 28; bottom: foot.top; bottomMargin: 16 }
                width: parent.width
                visible: page.talk.listeners.length > 0
                readonly property real nameWidth: 132
                readonly property int n: Math.max(1, page.talk.parts.length)
                readonly property int cell: Math.max(6, Math.min(34, Math.floor((width * 0.5 - nameWidth) / n) - 3))
                readonly property real cellsWidth: n * (cell + 3)

                Row {
                    id: heads
                    x: grid.nameWidth
                    spacing: 3
                    Repeater {
                        model: page.talk.parts
                        Item {
                            required property var modelData
                            required property int index
                            width: grid.cell; height: 18
                            T { anchors.horizontalCenter: parent.horizontalCenter; visible: grid.cell >= 16 || index === page.shown
                                text: index + 1; font.pixelSize: 11; font.family: Theme.mono; elide: Text.ElideNone
                                color: index === page.shown ? Theme.ink : Theme.faint }
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: page.sel = index }
                        }
                    }
                }
                ListView {
                    id: rows
                    anchors { top: heads.bottom; topMargin: 4; bottom: parent.bottom; left: parent.left; right: parent.right }
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: page.talk.listeners
                    delegate: Item {
                        id: who
                        required property var modelData
                        readonly property var at: page.shown >= 0 && page.shown < modelData.cells.length ? modelData.cells[page.shown] : null
                        width: rows.width; height: 40
                        Rectangle { anchors.fill: parent; anchors.leftMargin: -10; radius: 3; color: onRow.hovered ? Theme.panel : "transparent" }
                        T { width: grid.nameWidth - 12; anchors.verticalCenter: parent.verticalCenter
                            text: who.modelData.name + (who.modelData.grader ? "  ·  marks" : ""); color: onRow.hovered ? Theme.ink : Theme.dim }
                        Row {
                            x: grid.nameWidth
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 3
                            Repeater {
                                model: page.talk.parts.length
                                Rectangle {
                                    required property int index
                                    readonly property var c: index < who.modelData.cells.length ? who.modelData.cells[index] : null
                                    width: grid.cell; height: 26
                                    color: c ? page.lit(c.tone) : "transparent"
                                    border.width: index === page.shown && c ? 1 : c && c.tone === "out" ? 1 : 0
                                    border.color: index === page.shown ? Theme.ink : Theme.dark
                                    Rectangle { visible: !parent.c; anchors.bottom: parent.bottom; width: parent.width; height: 2; color: Theme.line }
                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                    TapHandler { onTapped: page.sel = parent.index }
                                }
                            }
                        }
                        T { id: number; x: grid.nameWidth + grid.cellsWidth + 14; width: 30; anchors.verticalCenter: parent.verticalCenter
                            text: who.at ? who.at.attention : ""; font.family: Theme.mono; font.pixelSize: 12; color: Theme.faint }
                        T { anchors { left: number.right; leftMargin: 10; right: parent.right; verticalCenter: parent.verticalCenter }
                            text: !who.at ? "" : who.at.inner !== "" ? who.at.inner : who.at.tone === "low" || who.at.tone === "out" ? who.at.band : ""
                            color: who.at && who.at.inner !== "" ? Theme.ink : Theme.faint; font.pixelSize: 13 }
                        HoverHandler { id: onRow; onHoveredChanged: page.looking = hovered ? who.modelData : (page.looking === who.modelData ? null : page.looking) }
                    }
                }
            }

            // The part on show and the listener the pointer is on, in a fixed place so nothing jumps.
            Item {
                id: foot
                anchors.bottom: parent.bottom
                width: parent.width; height: 66
                visible: page.talk.parts.length > 0
                Rectangle { width: parent.width; height: 1; color: Theme.line }
                T { y: 14; width: parent.width
                    text: page.part ? "Part " + (page.shown + 1) + " of " + page.talk.parts.length + "  ·  " + page.part.at + "  ·  " + page.part.title
                                      + (page.part.moments ? "  ·  " + page.part.moments : "") : "" }
                T { y: 38; width: parent.width; color: Theme.dim; font.pixelSize: 13
                    visible: !!page.looking
                    text: page.looking ? [page.looking.name + (page.looking.job ? ", " + page.looking.job : ""), page.looking.note,
                                          page.looking.unknown ? "did not know: " + page.looking.unknown : "",
                                          page.looking.decided ? "made up their mind at " + page.looking.decided : ""].filter(x => x).join("  ·  ") : "" }
                Row {
                    y: 40; spacing: 14
                    visible: !page.looking
                    Repeater {
                        model: [["hooked", "hooked"], ["with", "with you"], ["drift", "drifting"], ["low", "looking away"], ["out", "gone"]]
                        Row {
                            required property var modelData
                            spacing: 6
                            Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 9; height: 11; color: page.lit(modelData[0])
                                        border.width: modelData[0] === "out" ? 1 : 0; border.color: Theme.dark }
                            T { text: modelData[1]; color: Theme.faint; font.pixelSize: 12 }
                        }
                    }
                }
            }
        }

        // ---------- right: what came of it ----------
        Item {
            id: side
            anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
            width: Math.max(340, Math.min(440, view.width * 0.33))
            readonly property real pad: 32
            Rectangle { width: 1; height: parent.height; color: Theme.line }

            Heading { id: sideHead; x: side.pad; y: 38; text: page.talk.kept ? "A kept talk" : "The talk" }
            Btn {
                anchors { right: parent.right; rightMargin: side.pad; verticalCenter: sideHead.verticalCenter }
                visible: !page.talk.running
                text: "Close the talk"
                onPressed: town.closeTalk()
            }
            Flickable {
                id: scroll
                anchors { top: sideHead.bottom; topMargin: 18; bottom: parent.bottom; left: parent.left; right: parent.right }
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentHeight: results.height + 32
                Column {
                    id: results
                    x: side.pad
                    width: scroll.width - side.pad * 2
                    spacing: 6

                    T {
                        width: parent.width
                        visible: page.talk.running && page.talk.markers.length === 0
                        color: Theme.faint; wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.25; bottomPadding: 16
                        text: "What they took away, and the marks, come when the talk is over."
                    }

                    // ---- the marks ----
                    Heading { visible: page.talk.marks.rubric !== ""; text: page.talk.marks.rubric + ", out of " + page.talk.marks.out_of }
                    Repeater {
                        model: page.talk.marks.graders
                        Column {
                            id: grader
                            required property var modelData
                            width: results.width
                            spacing: 5
                            bottomPadding: 14
                            Item {
                                width: parent.width; height: 26
                                T { anchors.bottom: parent.bottom; width: parent.width - 110; text: grader.modelData.name; font.weight: Font.DemiBold }
                                T { anchors { right: parent.right; bottom: parent.bottom } text: grader.modelData.head; font.family: Theme.mono; font.pixelSize: 13 }
                            }
                            T { width: parent.width; visible: text !== ""; text: grader.modelData.verdict; color: Theme.dim; font.pixelSize: 13 }
                            Repeater {
                                model: grader.modelData.marks
                                Column {
                                    required property var modelData
                                    width: grader.width
                                    spacing: 1
                                    Item {
                                        width: parent.width; height: 20
                                        T { width: parent.width - 70; anchors.verticalCenter: parent.verticalCenter; text: modelData.name; font.pixelSize: 13
                                            color: modelData.level ? Theme.ink : Theme.faint }
                                        T { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: modelData.level > 0
                                            text: modelData.level + " of " + modelData.top
                                            font.family: Theme.mono; font.pixelSize: 12; color: Theme.dim }
                                    }
                                    T { width: parent.width; visible: text !== ""; text: modelData.reason + (modelData.about ? "  (" + modelData.about + ")" : "")
                                        font.pixelSize: 12; color: Theme.faint; wrapMode: Text.Wrap; maximumLineCount: 4; lineHeight: 1.2 }
                                }
                            }
                            T { width: parent.width; visible: text !== ""; text: grader.modelData.bonus.join("  ·  "); font.pixelSize: 13; color: Theme.dim }
                            T { width: parent.width; visible: grader.modelData.overall !== ""; text: "“" + grader.modelData.overall + "”"
                                font.pixelSize: 13; wrapMode: Text.Wrap; maximumLineCount: 5; lineHeight: 1.2; topPadding: 4 }
                            T { width: parent.width; visible: grader.modelData.dropped > 0; font.pixelSize: 12; color: Theme.faint
                                text: grader.modelData.dropped + (grader.modelData.dropped === 1 ? " mark was" : " marks were") + " dropped by the checks." }
                        }
                    }
                    T { width: parent.width; visible: page.talk.marks.graders.length > 0; font.pixelSize: 12; color: Theme.faint
                        wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.2; bottomPadding: 16
                        text: "A small model marks kindly. Read the reasons before the number, and check with real listeners." }

                    // ---- the room as a whole ----
                    Heading { visible: page.talk.markers.length > 0; text: "The room"; bottomPadding: 4 }
                    Repeater {
                        model: page.talk.markers
                        T { required property var modelData; width: results.width; text: modelData.says + (modelData.says.endsWith(".") ? "" : ".")
                            color: modelData.tone === "good" ? Theme.good : modelData.tone === "bad" ? Theme.bad : Theme.ink
                            font.pixelSize: 13; wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.2 }
                    }

                    // ---- what each took away ----
                    Heading { visible: page.talk.listeners.some(l => l.same !== ""); text: "What they say it was about"; topPadding: 18; bottomPadding: 4 }
                    Repeater {
                        model: page.talk.listeners.filter(l => l.same !== "")
                        Column {
                            required property var modelData
                            width: results.width
                            spacing: 1
                            bottomPadding: 8
                            T { width: parent.width; font.pixelSize: 12; color: page.sameColor(modelData.same); text: modelData.name + "  ·  " + page.sameWords(modelData.same) }
                            T { width: parent.width; visible: text !== ""; text: modelData.point; font.pixelSize: 13; wrapMode: Text.Wrap; maximumLineCount: 4; lineHeight: 1.2 }
                        }
                    }

                    Heading { visible: page.talk.listeners.some(l => l.question !== ""); text: "What they would ask"; topPadding: 18; bottomPadding: 4 }
                    Repeater {
                        model: page.talk.listeners.filter(l => l.question !== "")
                        Column {
                            required property var modelData
                            width: results.width
                            spacing: 1
                            bottomPadding: 8
                            T { width: parent.width; font.pixelSize: 12; color: Theme.faint; text: modelData.name }
                            T { width: parent.width; text: modelData.question; font.pixelSize: 13; wrapMode: Text.Wrap; maximumLineCount: 4; lineHeight: 1.2 }
                        }
                    }

                    // ---- what code counted ----
                    Heading { visible: page.talk.measured.length + page.talk.notes.length > 0; text: "Measured"; topPadding: 18; bottomPadding: 4 }
                    Repeater {
                        model: page.talk.measured
                        T { required property string modelData; width: results.width; text: modelData + "."; font.pixelSize: 13; color: Theme.dim
                            wrapMode: Text.Wrap; maximumLineCount: 4; lineHeight: 1.2 }
                    }
                    Repeater {
                        model: page.talk.notes
                        T { required property string modelData; width: results.width; text: modelData; font.pixelSize: 12; color: Theme.faint
                            wrapMode: Text.Wrap; maximumLineCount: 4; lineHeight: 1.2 }
                    }
                }
            }
            Rectangle {
                visible: scroll.contentHeight > scroll.height
                anchors.right: parent.right; anchors.rightMargin: 10
                width: 3; radius: 1.5; color: Theme.line
                y: scroll.y + scroll.visibleArea.yPosition * scroll.height
                height: Math.max(24, scroll.visibleArea.heightRatio * scroll.height)
            }
        }
    }
}
