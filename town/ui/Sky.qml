import QtQuick

// What the day does to the town: stars on a clear night, rain in the monsoon, a string of lights from roof to roof
// in a festival, headlights on the street unless there is a lockdown, and fireworks when an app turns out great.
// All of it is small flat squares, like the windows. It is drawn over the buildings and takes no clicks.
Canvas {
    id: sky
    property var scene: ({ rain: "", lights: "", pandemic: "" })
    property var roofs: []          // each building's roof, left to right: { x, y, w }
    property real ground: height    // where the buildings stand
    readonly property int u: 3      // one square

    readonly property var strings: ({
        diwali: ["#ffc94d", "#ff9f43", "#ffe08a"], ganesh: ["#ff7a45", "#ffc94d", "#e85d5d"],
        navratri: ["#e06c75", "#98c379", "#5b8def", "#c678dd", "#ffc94d"], christmas: ["#e06c75", "#98c379", "#ebe7dc"],
        ramzan: ["#98c379", "#ebe7dc", "#ffc94d"], holi: ["#e06c75", "#c678dd", "#5b8def", "#98c379", "#ffc94d"] })
    readonly property var party: ["#ffc94d", "#8fcf7a", "#5b8def", "#e06c75", "#c678dd", "#ebe7dc", "#56b6c2"]

    property real t: 0              // milliseconds this sky has been awake
    property real partyUntil: -1
    property real nextRocket: 0
    property var rockets: []
    property var sparks: []
    property var cars: [{ x: 0.12, dir: 1, speed: 46, long: 4 }, { x: 0.7, dir: -1, speed: 34, long: 6 }, { x: 0.45, dir: 1, speed: 28, long: 3 }]
    readonly property int traffic: scene.pandemic === "lockdown" ? 0 : scene.pandemic === "reopening" ? 1 : cars.length

    function celebrate() { partyUntil = t + 7000; nextRocket = t }

    onSceneChanged: requestPaint()
    onRoofsChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    Timer {
        running: sky.visible && sky.width > 0
        interval: 40; repeat: true
        onTriggered: { sky.t += interval; sky.move(interval / 1000); sky.requestPaint() }
    }

    // A number between 0 and 1 that is always the same for the same i: where a star or a raindrop sits.
    function spot(i, k) { const v = Math.sin(i * k) * 43758.5453; return v - Math.floor(v) }

    function roofAt(x) {
        for (const r of roofs) if (x >= r.x - u && x <= r.x + r.w) return r.y
        return ground
    }

    function move(dt) {
        for (let i = 0; i < traffic; i++) {
            const c = cars[i]
            c.x += c.dir * c.speed * dt / Math.max(1, width)
            if (c.x > 1.05) c.x = -0.05
            if (c.x < -0.05) c.x = 1.05
        }
        if (partyUntil < 0) return
        if (t < partyUntil - 2200 && t >= nextRocket) {
            nextRocket = t + 380 + Math.random() * 420
            rockets.push({ x: width * (0.08 + Math.random() * 0.84), y: ground, vy: -height * (0.9 + Math.random() * 0.3),
                           top: Math.max(8, ground * (0.08 + Math.random() * 0.3)), color: party[Math.floor(Math.random() * party.length)] })
        }
        for (const r of rockets) {
            r.y += r.vy * dt
            if (r.y <= r.top) {
                r.done = true
                for (let i = 0; i < 24; i++) {
                    const a = i / 24 * Math.PI * 2, s = Math.max(60, height * (0.12 + Math.random() * 0.12))
                    sparks.push({ x: r.x, y: r.y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: 1, color: i % 4 ? r.color : "#ebe7dc" })
                }
            }
        }
        rockets = rockets.filter(r => !r.done)
        for (const s of sparks) { s.vy += height * 0.18 * dt; s.x += s.vx * dt; s.y += s.vy * dt; s.life -= dt * 0.8 }
        sparks = sparks.filter(s => s.life > 0)
        if (t > partyUntil && !rockets.length && !sparks.length) partyUntil = -1
    }

    onPaint: {
        const ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        const snap = v => Math.round(v / u) * u

        // Stars, on a night with no rain, only where there is sky.
        if (!scene.rain) {
            ctx.fillStyle = "#3a4152"
            for (let i = 0; i < 46; i++) {
                const x = snap(spot(i + 1, 12.9898) * width), y = snap(spot(i + 1, 78.233) * ground * 0.8)
                if (y < roofAt(x) - 4 * u) ctx.fillRect(x, y, i % 7 ? 2 : u, i % 7 ? 2 : u)
            }
        }

        // The street: one line the town stands on, and whoever is driving along it.
        ctx.fillStyle = "#262c3b"
        ctx.fillRect(0, ground + 5, width, 1)
        for (let i = 0; i < traffic; i++) {
            const c = cars[i], x = snap(c.x * width), w = c.long * u
            ctx.fillStyle = "#3a4152"
            ctx.fillRect(x, ground + 1, w, u)
            ctx.fillStyle = "#ebe7dc"
            ctx.fillRect(c.dir > 0 ? x + w : x - u, ground + 1, u, u)
            ctx.fillStyle = "#d9826e"
            ctx.fillRect(c.dir > 0 ? x - 1 : x + w, ground + 1, 1, u)
        }

        // A string of lights sagging from each roof to the next, in the festival's colours, chasing along.
        const colors = strings[scene.lights]
        if (colors) {
            const shift = Math.floor(t / 600)
            let k = 0
            for (let i = 0; i + 1 < roofs.length; i++) {
                const a = roofs[i], b = roofs[i + 1], x0 = a.x + a.w, x1 = b.x, n = Math.max(2, Math.floor((x1 - x0) / (3 * u)))
                for (let j = 0; j <= n; j++, k++) {
                    const f = j / n
                    ctx.fillStyle = colors[(k + shift) % colors.length]
                    ctx.fillRect(snap(x0 + (x1 - x0) * f), snap(a.y + (b.y - a.y) * f + Math.sin(f * Math.PI) * 4 * u) - u, u, u)
                }
            }
            for (const r of roofs)   // and along every roof
                for (let x = r.x + u; x < r.x + r.w - u; x += 3 * u, k++) {
                    ctx.fillStyle = colors[(k + shift) % colors.length]
                    ctx.fillRect(snap(x), r.y - 2 * u, u, u)
                }
        }

        // Rain: the same streaks falling the same way, more of them when it is heavy.
        if (scene.rain) {
            const heavy = scene.rain === "heavy", drops = Math.round((heavy ? 320 : 140) * Math.min(1.5, width * height / 400000))
            const fall = height * (heavy ? 1.6 : 1.1), long = heavy ? 9 : 6
            ctx.fillStyle = heavy ? "#6a7488" : "#4c5568"
            ctx.globalAlpha = heavy ? 0.7 : 0.5
            for (let i = 0; i < drops; i++) {
                const y = (t / 1000 * fall + i * 137.7) % (height + 40) - 20
                const x = (spot(i + 1, 12.9898) * (width + 60) - y * 0.12 + width + 60) % (width + 60)
                ctx.fillRect(Math.round(x), Math.round(y), 1, long)
            }
            ctx.globalAlpha = 1
        }

        // Fireworks.
        ctx.fillStyle = "#ffc94d"
        for (const r of rockets) ctx.fillRect(snap(r.x), snap(r.y), u, 2 * u)
        for (const s of sparks) {
            ctx.globalAlpha = Math.max(0, s.life)
            ctx.fillStyle = s.color
            ctx.fillRect(snap(s.x), snap(s.y), u, u)
        }
        ctx.globalAlpha = 1
    }
}
