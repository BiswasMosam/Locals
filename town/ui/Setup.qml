import QtQuick
import QtQuick.Dialogs

// Setting up a day: what they test, who goes out, and when. Three columns, read left to right.
Item {
    id: setup
    objectName: "setup"
    signal started()

    // ---------- what was chosen ----------
    property string kind: "saved"            // saved, site or apk
    property string taskRef: town.tasks.length ? town.tasks[0].ref : ""
    property string check: "page_text"
    property var files: []                   // files the locals have on their device, for upload tasks
    property var apk: null
    property var counts: ({})                // job key -> how many of that job go out
    property string day: town.calendar.default || ""
    property bool wholeYear: false
    property string pandemic: ""
    property bool take: true
    property bool watch: false
    property string error: ""

    readonly property var task: town.tasks.find(t => t.ref === taskRef) || null
    readonly property var going: {
        const out = []
        for (const f of town.roster) for (const j of f.jobs) for (const p of j.people.slice(0, counts[j.key] || 0)) out.push(p)
        return out
    }
    readonly property var dates: wholeYear ? (town.calendar.sample || []) : [day]
    readonly property var when: wholeYear ? ({ ok: true, label: dates.length + " days, one after another, from January to December." })
                                          : town.today(day, pandemic)
    readonly property var cost: town.estimate(going.map(p => p.patience), dates.length, kind, !!apk)
    readonly property string blocked: town.busy ? "A day is already running." : !when.ok ? when.label : cost.problem

    function setCount(key, n, most) {
        const next = Object.assign({}, counts)
        next[key] = Math.max(0, Math.min(most, n))
        counts = next
    }
    function setFamily(fam, n) {
        const next = Object.assign({}, counts)
        for (const j of fam.jobs) next[j.key] = Math.min(n, j.people.length)
        counts = next
    }
    function setEveryone(n) {
        const next = {}
        for (const f of town.roster) for (const j of f.jobs) next[j.key] = Math.min(n, j.people.length)
        counts = next
    }
    function shift(days) {
        const d = new Date(day + "T12:00:00")
        if (isNaN(d)) return
        d.setDate(d.getDate() + days)
        day = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0")
    }
    function add(url, asApk) {
        const kept = town.keepFile(url)
        if (kept.error) { error = kept.error; return }
        if (asApk) {
            if (!kept.name.toLowerCase().endsWith(".apk")) { error = "That is not an APK file."; return }
            apk = kept
        } else files = files.concat([kept])
        error = ""
    }
    function start() {
        const body = { locals: going.map(p => p.id), watch: watch, take: take, dates: dates, pandemic: pandemic }
        const goal = { goal: goalField.text.trim(), check: check, value: valueField.text.trim(), files: files }
        if (kind === "saved") body.task = taskRef
        else if (kind === "apk") body.app = Object.assign({ apk: apk ? apk.path : "" }, goal)
        else body.site = Object.assign({ url: urlField.text.trim() }, goal)
        error = town.startDay(body)
        if (error === "") setup.started()
    }
    onKindChanged: if (kind === "apk" && (check === "url_contains" || check === "download")) check = "page_text"

    FileDialog { id: pickApk; title: "The app's APK file"; nameFilters: ["Android apps (*.apk)"]; onAccepted: setup.add(selectedFile.toString(), true) }
    FileDialog { id: pickFiles; title: "Files on their device"; fileMode: FileDialog.OpenFiles
                 onAccepted: { for (const f of selectedFiles) setup.add(f.toString(), false) } }

    readonly property real col: (width - Theme.gutter * 2 - 2 * 56) / 3

    // ================= what =================
    Item {
        id: what
        x: Theme.gutter; y: 38
        width: setup.col; height: parent.height - 38 - 28

        Heading { id: whatHead; text: "What they test" }
        Row {
            id: kinds
            anchors.top: whatHead.bottom; anchors.topMargin: 16
            spacing: 4
            Seg { text: "A saved task"; on: setup.kind === "saved"; onChosen: setup.kind = "saved" }
            Seg { text: "A site"; on: setup.kind === "site"; onChosen: setup.kind = "site" }
            Seg { text: "An Android app"; on: setup.kind === "apk"; onChosen: setup.kind = "apk" }
        }

        // ---- a saved task ----
        Item {
            anchors { top: kinds.bottom; topMargin: 18; bottom: parent.bottom; left: parent.left; right: parent.right }
            visible: setup.kind === "saved"
            ListView {
                id: taskList
                width: parent.width
                height: Math.min(contentHeight, parent.height * 0.55)
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: town.tasks
                delegate: Item {
                    id: card
                    required property var modelData
                    readonly property bool on: setup.taskRef === modelData.ref
                    width: taskList.width; height: 34
                    Rectangle { anchors.fill: parent; radius: 3; color: card.on ? Theme.dark : hov.hovered ? Theme.panel : "transparent" }
                    T { x: 10; anchors.verticalCenter: parent.verticalCenter; width: parent.width * 0.44; text: card.modelData.app; color: card.on ? Theme.ink : Theme.dim }
                    T { x: parent.width * 0.46 + 10; anchors.verticalCenter: parent.verticalCenter; width: parent.width * 0.54 - 20
                        text: card.modelData.ref.split(":")[1] + (card.modelData.platform === "android" ? "  ·  Android" : "") + (card.modelData.mine ? "  ·  yours" : "")
                        color: card.on ? Theme.ink : Theme.dim }
                    HoverHandler { id: hov; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: setup.taskRef = card.modelData.ref }
                }
            }
            T {
                id: story
                anchors { top: taskList.bottom; topMargin: 18 }
                width: parent.width
                text: setup.task ? setup.task.story : ""
                wrapMode: Text.Wrap; maximumLineCount: 9; lineHeight: 1.25
            }
            T {
                anchors { top: story.bottom; topMargin: 10 }
                width: parent.width
                text: setup.task ? "Done when " + setup.task.check + "." : ""
                color: Theme.dim; wrapMode: Text.Wrap; maximumLineCount: 3
            }
        }

        // ---- a site, or an app ----
        Column {
            anchors { top: kinds.bottom; topMargin: 18; left: parent.left; right: parent.right }
            visible: setup.kind !== "saved"
            spacing: 8

            T { visible: setup.kind === "site"; text: "Address"; color: Theme.dim; font.pixelSize: 13 }
            Field { id: urlField; visible: setup.kind === "site"; width: parent.width; mono: true; hint: "http://localhost:5173 or https://your-site.com" }

            Rectangle {
                visible: setup.kind === "apk"
                width: parent.width; height: 74; radius: 3
                color: apkDrop.containsDrag ? Theme.dark : Theme.panel
                border.width: 1; border.color: apkDrop.containsDrag ? Theme.dim : Theme.line
                T { x: 14; y: 14; width: parent.width - 28; text: setup.apk ? setup.apk.name + ", " + (setup.apk.size / 1048576).toFixed(1) + " MB" : "Drop the app's APK here, or choose it" }
                T { x: 14; y: 38; width: parent.width - 28; color: Theme.dim; font.pixelSize: 13
                    text: !town.machine.android || !town.machine.android.adb ? "adb was not found. Install the Android SDK platform tools."
                        : town.machine.android.devices.length ? "It is installed fresh for every local, on " + town.machine.android.devices.join(", ") + "."
                        : "No emulator or phone is connected yet." }
                DropArea { id: apkDrop; anchors.fill: parent; onDropped: (drop) => { if (drop.urls.length) setup.add(drop.urls[0].toString(), true) } }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: pickApk.open() }
            }

            T { topPadding: 8; text: "What should they try to do"; color: Theme.dim; font.pixelSize: 13 }
            Field { id: goalField; width: parent.width; tall: true; hint: "Sign up, find the pricing page and choose the cheapest plan." }

            T { topPadding: 8; text: "How do we know it worked"; color: Theme.dim; font.pixelSize: 13 }
            Flow {
                width: parent.width; spacing: 4
                Seg { text: "The screen shows"; on: setup.check === "page_text"; onChosen: setup.check = "page_text" }
                Seg { visible: setup.kind === "site"; text: "The address contains"; on: setup.check === "url_contains"; onChosen: setup.check = "url_contains" }
                Seg { visible: setup.kind === "site"; text: "A file is saved"; on: setup.check === "download"; onChosen: setup.check = "download" }
                Seg { text: "Take their word"; on: setup.check === "word"; onChosen: setup.check = "word" }
            }
            Field {
                id: valueField
                width: parent.width
                visible: setup.check === "page_text" || setup.check === "url_contains"
                hint: setup.check === "page_text" ? "Welcome aboard" : "/thank-you"
            }

            T { topPadding: 8; text: "Files on their device"; color: Theme.dim; font.pixelSize: 13 }
            Rectangle {
                width: parent.width; height: 52; radius: 3
                color: fileDrop.containsDrag ? Theme.dark : Theme.panel
                border.width: 1; border.color: fileDrop.containsDrag ? Theme.dim : Theme.line
                T { x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 28
                    color: setup.files.length ? Theme.ink : Theme.faint
                    text: setup.files.length ? setup.files.map(f => f.name).join(", ") : "Drop files here if the task needs something to upload" }
                DropArea { id: fileDrop; anchors.fill: parent; onDropped: (drop) => { for (const u of drop.urls) setup.add(u.toString(), false) } }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: pickFiles.open() }
            }
        }
    }

    // ================= who =================
    Item {
        id: who
        x: what.x + setup.col + 56; y: 38
        width: setup.col; height: parent.height - 38

        Heading { id: whoHead; text: "Who goes out" }
        Row {
            anchors { right: parent.right; verticalCenter: whoHead.verticalCenter }
            spacing: 2
            Chip { text: "One of each job"; on: true; onToggled: setup.setEveryone(1) }
            Chip { text: "Nobody"; on: true; onToggled: setup.setEveryone(0) }
        }
        T {
            id: whoCount
            anchors.top: whoHead.bottom; anchors.topMargin: 14
            text: setup.going.length ? setup.going.length + " going out" : "Nobody yet. Add someone below."
            font.family: Theme.display; font.pixelSize: 22
            color: setup.going.length ? Theme.ink : Theme.dim
        }
        Flickable {
            id: people
            anchors { top: whoCount.bottom; topMargin: 14; bottom: parent.bottom; left: parent.left; right: parent.right }
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentHeight: families.height + 28
            Column {
                id: families
                width: people.width - 12
                Repeater {
                    model: town.roster
                    Column {
                        id: fam
                        required property var modelData
                        readonly property int out: modelData.jobs.reduce((n, j) => n + (setup.counts[j.key] || 0), 0)
                        width: families.width
                        Item {
                            width: parent.width; height: 40
                            Heading { anchors.bottom: parent.bottom; anchors.bottomMargin: 8; text: fam.modelData.family + (fam.out ? "  ·  " + fam.out : ""); color: fam.out ? Theme.dim : Theme.faint }
                            Chip { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.bottomMargin: 3
                                   text: fam.out ? "None" : "One of each"; on: true; onToggled: setup.setFamily(fam.modelData, fam.out ? 0 : 1) }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                        }
                        Repeater {
                            model: fam.modelData.jobs
                            Item {
                                id: job
                                required property var modelData
                                readonly property int n: setup.counts[modelData.key] || 0
                                width: fam.width; height: 46
                                Column {
                                    anchors { left: parent.left; right: stepper.left; rightMargin: 12; verticalCenter: parent.verticalCenter }
                                    spacing: 1
                                    T { width: parent.width; text: job.modelData.label; color: job.n ? Theme.ink : Theme.dim }
                                    T { width: parent.width; font.pixelSize: 12; color: Theme.faint
                                        text: job.n ? job.modelData.people.slice(0, job.n).map(p => p.name).join(", ")
                                                    : job.modelData.people.length + (job.modelData.people.length === 1 ? " person, at home" : " people, at home") }
                                }
                                Row {
                                    id: stepper
                                    anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                                    spacing: 2
                                    Btn { width: 28; height: 28; text: "−"; opacity: job.n > 0 ? 1 : 0.35
                                          onPressed: setup.setCount(job.modelData.key, job.n - 1, job.modelData.people.length) }
                                    T { width: 26; height: 28; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                                        text: job.n; font.family: Theme.mono; color: job.n ? Theme.light : Theme.faint }
                                    Btn { width: 28; height: 28; text: "+"; opacity: job.n < job.modelData.people.length ? 1 : 0.35
                                          onPressed: setup.setCount(job.modelData.key, job.n + 1, job.modelData.people.length) }
                                }
                            }
                        }
                    }
                }
            }
        }
        Rectangle {
            visible: people.contentHeight > people.height
            anchors.right: parent.right
            width: 3; radius: 1.5; color: Theme.line
            y: people.y + people.visibleArea.yPosition * people.height
            height: Math.max(24, people.visibleArea.heightRatio * people.height)
        }
    }

    // ================= when, and what it will cost =================
    Column {
        id: last
        x: who.x + setup.col + 56; y: 38
        width: setup.col
        spacing: 8

        Heading { text: "When"; bottomPadding: 8 }
        Row {
            width: parent.width; spacing: 4
            Btn { width: 32; height: 36; text: "‹"; opacity: setup.wholeYear ? 0.35 : 1; onPressed: if (!setup.wholeYear) setup.shift(-1) }
            Field {
                id: dayField
                width: parent.width - 72; mono: true
                opacity: setup.wholeYear ? 0.45 : 1
                text: setup.day
                onEdited: if (/^\d{4}-\d{2}-\d{2}$/.test(text) && text !== setup.day) setup.day = text
                Connections { target: setup; function onDayChanged() { if (dayField.text !== setup.day) dayField.text = setup.day } }
            }
            Btn { width: 32; height: 36; text: "›"; opacity: setup.wholeYear ? 0.35 : 1; onPressed: if (!setup.wholeYear) setup.shift(1) }
        }
        T { width: parent.width; text: setup.when.label; color: setup.when.ok ? Theme.ink : Theme.bad; wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.2 }
        Flow {
            width: parent.width; spacing: 4; topPadding: 4
            Repeater {
                model: town.calendar.picks || []
                Seg { required property var modelData; text: modelData.label; on: !setup.wholeYear && setup.day === modelData.date
                      onChosen: { setup.wholeYear = false; setup.day = modelData.date } }
            }
            Seg { text: "A year in " + ((town.calendar.sample || []).length) + " days"; on: setup.wholeYear; onChosen: setup.wholeYear = !setup.wholeYear }
        }
        Row {
            spacing: 4; topPadding: 4
            Seg { text: "No pandemic"; on: setup.pandemic === ""; onChosen: setup.pandemic = "" }
            Seg { text: "Lockdown"; on: setup.pandemic === "lockdown"; onChosen: setup.pandemic = "lockdown" }
            Seg { text: "Reopening"; on: setup.pandemic === "reopening"; onChosen: setup.pandemic = "reopening" }
        }

        Heading { topPadding: 26; bottomPadding: 4; text: "It will take" }
        Text {
            width: parent.width
            text: setup.cost.time
            font.family: Theme.display; font.pixelSize: 30; font.weight: Font.DemiBold
            color: setup.going.length ? Theme.ink : Theme.dim
        }
        T { width: parent.width; text: setup.cost.note; color: Theme.dim; wrapMode: Text.Wrap; maximumLineCount: 4; lineHeight: 1.2 }
        Item {
            width: parent.width; height: 14
            visible: setup.cost.gpu_part >= 0
            Rectangle {
                y: 8; width: parent.width; height: 4; color: Theme.dark
                Rectangle { height: parent.height; width: parent.width * Math.min(1, setup.cost.gpu_part); color: setup.cost.gpu_tight ? Theme.bad : Theme.dim }
            }
        }
        T { width: parent.width; text: setup.cost.gpu; color: setup.cost.gpu_tight ? Theme.bad : Theme.dim; font.pixelSize: 13; wrapMode: Text.Wrap; maximumLineCount: 3; lineHeight: 1.2 }

        Column {
            topPadding: 18
            Chip { text: (setup.take ? "●  " : "○  ") + "Ask what their job let them notice"; on: setup.take; onToggled: setup.take = !setup.take }
            Chip { text: (setup.watch ? "●  " : "○  ") + "Show the browser while they work"; on: setup.watch; onToggled: setup.watch = !setup.watch }
        }
        T {
            width: parent.width; topPadding: 6
            visible: text !== ""
            text: setup.error || setup.blocked
            color: Theme.bad; wrapMode: Text.Wrap; maximumLineCount: 4
        }
        Btn {
            width: parent.width; height: 46
            readonly property bool ready: setup.going.length > 0 && setup.blocked === ""
            strong: ready
            opacity: ready ? 1 : 0.6
            text: !setup.going.length ? "Choose who goes out" : "Start the day with " + setup.going.length
            onPressed: if (ready) setup.start()
        }
    }
}
