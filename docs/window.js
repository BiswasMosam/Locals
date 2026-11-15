// A working copy of the Locals window, in the browser. The pages follow town/ui/*.qml; what they show is
// worked out the way town/appstate.py works it out, from data.js. A day "runs" by playing a kept day back.
(function () {
  "use strict";
  const D = window.TOWN;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const store = {
    get(k, d) { try { const v = localStorage.getItem("locals-copy:" + k); return v === null ? d : JSON.parse(v); } catch (_) { return d; } },
    set(k, v) { try { localStorage.setItem("locals-copy:" + k, JSON.stringify(v)); } catch (_) {} },
  };
  const reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const people = D.families.flatMap((f) => f.people.map((p) => Object.assign({ family: f.family }, p)));
  const folk = Object.fromEntries(people.map((p) => [p.id, p]));
  const nameOf = (id) => (folk[id] ? folk[id].name : id);
  const total = people.length;

  // ---------- the window's words and colours (Theme.qml, appstate.py) ----------
  const OUTCOMES = new Set(["DONE", "SAYS DONE", "WRONG DONE", "GAVE UP", "ASKED", "STOPPED", "ERROR"]);
  const FINISHED = new Set(["DONE", "SAYS DONE"]);
  const WARN = new Set(["STUCK", "SLIP", "OFF PATH", "WRONG DONE", "ASKED"]);
  const TONE = { STUCK: "warn", SLIP: "warn", "OFF PATH": "warn", "WRONG DONE": "warn", ASKED: "warn", DONE: "good", "SAYS DONE": "good",
    "GAVE UP": "bad", ERROR: "bad", TAKE: "calm", EXPERT: "calm", MODEL: "faint", STOPPED: "faint" };
  function stateColor(s) {
    switch (s) {
      case "work": return "var(--light)"; case "out": return "var(--waiting)";
      case "DONE": case "SAYS DONE": return "var(--good)";
      case "GAVE UP": case "ERROR": case "WRONG DONE": return "var(--bad)";
      case "ASKED": case "STOPPED": return "var(--dim)";
      default: return "var(--dark)";
    }
  }
  function stateWords(s) {
    return { work: "at work now", out: "going out today", DONE: "got it done", "SAYS DONE": "says it is done",
      "WRONG DONE": "thought it was done, and it was not", "GAVE UP": "gave up", ASKED: "asked someone for help",
      STOPPED: "was stopped", ERROR: "hit an error" }[s] || "";
  }
  const toneColor = (t) => (t === "warn" ? "var(--light)" : t === "good" ? "var(--good)" : t === "bad" ? "var(--bad)" : "var(--faint)");
  const capital = (k) => k.charAt(0) + k.slice(1).toLowerCase();
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const dmon = (iso) => `${+iso.slice(8, 10)} ${MONTHS[+iso.slice(5, 7) - 1]}`;
  const clock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  function pix(rows) {
    const w = rows[0].length, h = rows.length, n = Math.max(w, h);
    let r = "";
    rows.forEach((row, y) => [...row].forEach((c, x) => { if (c === "X") r += `<rect x="${x + (n - w) / 2}" y="${y + (n - h) / 2}" width="1" height="1"/>`; }));
    return `<svg viewBox="0 0 ${n} ${n}" aria-hidden="true">${r}</svg>`;
  }

  // ---------- the rail (Rail.qml), and the guide's own two places ----------
  const PLACES = [
    { name: "town", label: "Town", rows: ["...X...", "..XXX..", ".XXXXX.", "XXXXXXX", ".X...X.", ".X.X.X.", ".X.X.X."] },
    { name: "setup", label: "Set up", rows: [".X.....", "XXXXXXX", ".X.....", ".....X.", "XXXXXXX", ".....X.", "......."] },
    { name: "days", label: "Days", rows: ["XXXXXXX", "X.....X", "XXXXXXX", "X.X.X.X", "XXXXXXX", "X.X.X.X", "XXXXXXX"] },
    { name: "rooms", label: "Rooms", rows: ["XXXXXXX", ".......", ".X.X.X.", ".......", "X.X.X.X", ".......", ".X.X.X."] },
    { name: "report", label: "Report", rows: ["......X", "......X", "...X..X", "...X..X", "X..X..X", "X..X..X", "XXXXXXX"] },
  ];
  const INSTALL = { name: "install", label: "Install", rows: ["...X...", "...X...", ".X.X.X.", "..XXX..", "...X...", ".......", "XXXXXXX"] };
  const GUIDE_ICON = [".XXXXX.", "X.....X", ".....X.", "...XX..", "...X...", ".......", "...X..."];

  // ---------- what the copy knows ----------
  const todayIso = (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; })();
  const S = {
    page: "town",
    kind: "saved", taskRef: D.tasks[0].ref, counts: {}, day: D.labels[todayIso] ? todayIso : "2026-02-10", wholeYear: false, pandemic: "",
    take: true, watch: false, site: { url: "", goal: "", check: "page_text", value: "" }, apk: null,
    live: null, notice: null, viewer: -1,
    roomId: D.rooms[0].id, deck: null, speech: null, grade: true, talk: null, talkSel: -1, looking: null,
    hover: null,
  };

  // ---------- a day on the page (appstate.Live) ----------
  function moment(e, i) {
    const step = e.type === "step", kind = step ? "STEP" : e.kind || "";
    return { i, local: e.local || "", name: nameOf(e.local || ""), kind, tone: step ? "step" : TONE[kind] || "plain", step: +(e.step || 0),
      title: step ? e.line || "" : capital(kind), text: step ? e.thought || "" : e.says || "", at: String(e.at || ""), secs: +(e.secs || 0), shot: e.shot || "" };
  }
  function newLive(meta) {
    return { day: meta.day, task: meta.task, ref: meta.ref, today: meta.today || "", index: meta.index || [1, 1], locals: meta.locals.slice(),
      scene: meta.scene || {}, states: Object.fromEntries(meta.locals.map((i) => [i, "out"])), moments: [], who: "", running: false,
      stopping: false, kept: false, verdict: null, sel: -1, newest: -1, only: "", steps: true, began: Date.now() };
  }
  function take(L, e) {
    const m = moment(e, L.moments.length);
    L.moments.push(m);
    if (e.type === "event" && OUTCOMES.has(e.kind)) { L.states[e.local] = e.kind; L.who = ""; }
    else if ([undefined, "out", "work"].includes(L.states[e.local])) { L.states[e.local] = "work"; L.who = e.local; }
    if (m.shot || L.newest < 0 || !L.moments[L.newest].shot) L.newest = m.i;
  }
  function strips(L) {
    const rows = {};
    L.locals.forEach((i) => (rows[i] = { id: i, name: nameOf(i), cells: [], outcome: "", end: -1, left: 0 }));
    const flag = new Set();
    for (const m of L.moments) {
      const row = rows[m.local];
      if (!row) continue;
      if (m.kind === "STEP") {
        const wrong = flag.has(m.local) || m.title === "stuck";
        flag.delete(m.local);
        row.cells.push({ i: m.i, tone: wrong ? "warn" : "step" });
      } else if (OUTCOMES.has(m.kind)) { row.outcome = m.kind; row.end = m.i; }
      else if (WARN.has(m.kind) && !row.outcome) {
        if (m.kind === "STUCK" && row.cells.length) row.cells[row.cells.length - 1].tone = "warn";
        else flag.add(m.local);
      }
    }
    return Object.values(rows).map((row) => {
      const st = L.states[row.id] || "";
      row.outcome = row.outcome || (OUTCOMES.has(st) ? st : "");
      if (!row.outcome || FINISHED.has(row.outcome)) row.left = Math.max(0, Math.min(30, folk[row.id] ? folk[row.id].patience : 0) - row.cells.length);
      return row;
    });
  }
  function openDay(id) {
    const log = D.logs[id];
    if (!log || (S.live && S.live.running)) return;
    const L = newLive(log.meta);
    L.kept = true;
    log.entries.forEach((e) => take(L, e));
    Object.assign(L.states, log.meta.results || {});
    L.who = "";
    L.verdict = log.verdict;
    S.live = L;
    go("town");
  }
  let timer = 0;
  function playDay(id) {
    const log = D.logs[id], L = newLive(log.meta);
    L.running = true;
    S.live = L; S.notice = null;
    let k = 0;
    const next = () => {
      if (S.live !== L) return;
      if (L.stopping || k >= log.entries.length) return finish(L, log);
      const e = log.entries[k++];
      take(L, e);
      const n = log.entries[k];
      const secs = (x) => parseFloat(x.at) || 0;
      const gap = !n ? 1.2 : n.local === e.local ? Math.max(0, secs(n) - secs(e)) : 2.4;
      timer = setTimeout(next, Math.max(500, Math.min(4200, (gap * 1000) / 1.6)));
      draw();
    };
    timer = setTimeout(next, 1400);
    go("town");
  }
  function finish(L, log) {
    clearTimeout(timer);
    if (L.stopping) {
      L.locals.forEach((i) => { if (!OUTCOMES.has(L.states[i])) L.states[i] = "STOPPED"; });
      L.verdict = null;
    } else {
      Object.assign(L.states, log.meta.results || {});
      L.verdict = log.verdict;
    }
    L.running = L.stopping = false;
    L.who = "";
    draw();
    if (L.verdict && L.verdict.win) celebrate();
  }
  function stopDay() {
    const L = S.live;
    if (!L || !L.running) return;
    L.stopping = true;
    clearTimeout(timer);
    draw();
    timer = setTimeout(() => finish(L, D.logs[L.day]), 900);
  }
  function lastView(L) {
    const last = L.moments[L.moments.length - 1];
    return {
      step: last && last.kind === "STEP" && last.local === L.who ? last.step : 0,
      line: last ? (last.kind === "STEP" ? last.title : `${last.title}. ${last.text}`) : "",
      thought: last && last.kind === "STEP" ? last.text : "",
      finished: Object.values(L.states).filter((v) => OUTCOMES.has(v)).length,
    };
  }

  // ---------- building the frame ----------
  const rail = $("#rail");
  rail.innerHTML = `<svg class="mark" viewBox="0 0 5 7" shape-rendering="crispEdges" aria-label="Locals"><rect x="0" y="0" width="1" height="7" fill="#ffc94d"/><rect x="0" y="6" width="5" height="1" fill="#ffc94d"/></svg>`
    + PLACES.map((p) => `<button class="place" data-act="page" data-v="${p.name}" data-coach="rail-${p.name}" aria-label="${p.label}">${pix(p.rows)}<span>${p.label}</span></button>`).join("")
    + `<span class="gap"></span>`
    + `<button class="place" data-act="page" data-v="install" data-coach="rail-install" aria-label="Install">${pix(INSTALL.rows)}<span>Install</span></button>`
    + `<button class="place guide" data-act="tour" aria-label="Walk me through it">${pix(GUIDE_ICON)}<span>Guide</span></button>`;

  function go(page) {
    S.page = page;
    if (page !== "town") S.viewer = -1;
    draw();
  }

  // ---------- Town ----------
  const townPage = $("#p-town");
  townPage.innerHTML = `<div class="town">
    <div class="left">
      <p class="h" id="t-over">The town</p>
      <div class="big" id="t-head" data-coach="head"></div>
      <p class="sub" id="t-sub"></p>
      <button class="btn strong setupbtn" id="t-setup" data-act="page" data-v="setup">Set up a day</button>
      <div class="moment" id="t-moment" data-coach="moment" hidden></div>
      <div class="skyline" id="sky" data-coach="skyline"><div class="row" id="sky-row"></div><canvas id="sky-canvas"></canvas></div>
      <div class="wholine" id="t-who"></div>
      <div class="viewer" id="viewer" hidden></div>
    </div>
    <div class="side" id="t-side"></div>
  </div>`;
  const sky = { slot: 0, wide: 0, foot: 44, roofs: [], ground: 0, t: 0, cars: [{ x: 0.12, dir: 1, speed: 46, long: 4 }, { x: 0.7, dir: -1, speed: 34, long: 6 }, { x: 0.45, dir: 1, speed: 28, long: 3 }],
    rockets: [], sparks: [], partyUntil: -1, nextRocket: 0, wave: -1, built: "" };
  function townHead() {
    const L = S.live, day = !!L;
    let head = "Everyone is home.", under = `${total} locals in ${D.families.length} families.  ${D.tasks.length} tasks ready.`;
    const when = L ? (L.index[1] > 1 ? `Day ${L.index[0]} of ${L.index[1]}  ·  ` : "") + L.task + (L.today ? "  ·  " + L.today : "") : "";
    if (L && L.running && L.who) head = nameOf(L.who) + " is out.";
    else if (L && L.running) head = L.stopping ? "Calling everyone home." : "The day is starting.";
    else if (L && L.verdict && L.verdict.head) head = L.verdict.head;
    else if (L) head = Object.values(L.states).includes("STOPPED") ? "The day was stopped." : "The day is over.";
    if (L && L.running) under = when;
    else if (L && L.verdict && L.verdict.head) under = L.verdict.sub + (L.verdict.note ? "  " + L.verdict.note : "");
    else if (L) under = when;
    $("#t-over").textContent = day && !L.running ? L.task + (L.today ? "  ·  " + L.today : "") : "The town";
    const h = $("#t-head");
    h.textContent = head;
    h.className = "big head" + (day ? " mid" : "") + (L && !L.running && !L.kept && L.verdict && L.verdict.win ? " won" : "");
    const s = $("#t-sub");
    s.textContent = under;
    s.style.fontSize = day ? "14px" : "16px";
    $("#t-setup").hidden = day;
  }
  function shownMoment(L) { return L.sel >= 0 ? L.sel : L.newest; }
  function townMoment() {
    const L = S.live, box = $("#t-moment");
    box.hidden = !L;
    if (!L) return;
    const m = L.moments[shownMoment(L)];
    const tone = !m ? "var(--dim)" : m.tone === "warn" ? "var(--light)" : m.tone === "good" ? "var(--good)" : m.tone === "bad" ? "var(--bad)" : "var(--dim)";
    const src = m && m.shot ? m.shot : "";
    const old = box.querySelector("img");
    const keep = old && old.getAttribute("src") === src;
    box.innerHTML = `<div class="frame" id="t-frame">${src ? `<img src="${esc(src)}" alt="The screen ${esc(m.name)} saw" data-act="enlarge">` : `<span class="faint">No screen yet</span>`}</div>
      <div class="words" ${m ? "" : "hidden"}>
        <p class="h" style="color:${tone}">${m ? esc(m.name) + "  ·  " + (m.kind === "STEP" ? "step " + m.step : esc(m.kind)) : ""}</p>
        ${m && m.kind === "STEP" ? `<div class="title">${esc(m.title)}</div>` : ""}
        <div class="text">${m ? esc(m.text) : ""}</div>
        ${m && m.at ? `<div class="at">${esc(m.at)} in${m.secs ? `, took ${m.secs.toFixed(1)} s to decide` : ""}</div>` : ""}
        ${L.sel >= 0 ? `<div><button class="btn" data-act="follow">${L.running ? "Back to now" : "Back to the end"}</button></div>` : ""}
      </div>`;
    const frame = $("#t-frame"), img = frame.querySelector("img");
    const size = () => {
      const h = frame.clientHeight || 300;
      const ratio = img && img.naturalWidth ? img.naturalWidth / img.naturalHeight : 0.5;
      frame.style.width = Math.min(box.clientWidth * 0.58, Math.round(h * ratio)) + "px";
    };
    if (img) { if (img.complete) size(); else img.addEventListener("load", size, { once: true }); } else size();
    if (keep) return;
  }
  function skyHeight() {
    const L = S.live, left = $("#p-town .left"), el = $("#sky");
    if (window.innerWidth <= 900) { el.style.flex = "none"; el.style.height = (L ? 150 : 260) + "px"; return; }
    if (L) { const hgt = left.clientHeight; const band = hgt < 520 ? 0 : Math.max(120, Math.min(190, hgt * 0.24)); el.style.flex = "none"; el.style.height = band + "px"; el.style.marginTop = "0"; }
    else { el.style.flex = "1"; el.style.height = "auto"; el.style.marginTop = "56px"; }
  }
  function skyline() {
    const el = $("#sky"), row = $("#sky-row"), w = el.clientWidth, h = el.clientHeight;
    const L = S.live, states = L ? L.states : {};
    const count = D.families.length, cols = 3;
    const tallest = Math.ceil(Math.max(...D.families.map((f) => f.people.length)) / cols);
    const slot = Math.floor(w / count);
    const unit = Math.max(5, Math.min(26, (slot * 0.86) / (cols * 1.36 + 0.36), (h - 46) / (tallest * 1.62 + 0.36)));
    const gap = Math.max(2, Math.round(unit * 0.36)), win = Math.round(unit), tall = Math.round(unit * 1.26);
    const wide = cols * (win + gap) + gap, high = (f) => Math.ceil(f.people.length / cols) * (tall + gap) + gap;
    const key = [w, h].join("x");
    if (sky.built !== key) {
      row.innerHTML = D.families.map((f) => `<div class="bld" style="width:${slot}px"><div class="house" style="width:${wide}px;height:${high(f)}px">`
        + f.people.map((p, i) => `<i class="w" data-id="${p.id}" style="left:${gap + (i % cols) * (win + gap)}px;top:${high(f) - (Math.floor(i / cols) + 1) * (tall + gap)}px;width:${win}px;height:${tall}px"></i>`).join("")
        + `</div><div class="nm" style="height:34px;max-width:${slot - 4}px"><span style="font-size:${slot < 76 ? 10 : 12}px">${esc(f.family)}</span><b>${f.people.length}</b></div></div>`).join("");
      sky.built = key;
      sky.slot = slot; sky.wide = wide;
      sky.ground = h - sky.foot;
      sky.roofs = D.families.map((f, i) => ({ x: i * slot + (slot - wide) / 2, y: h - sky.foot - high(f), w: wide }));
      const c = $("#sky-canvas"), r = Math.min(window.devicePixelRatio || 1, 2);
      c.width = Math.max(1, w * r); c.height = Math.max(1, h * r);
      c.getContext("2d").setTransform(r, 0, 0, r, 0, 0);
    }
    $$("#sky-row .w").forEach((x) => {
      const st = states[x.dataset.id] || "";
      x.style.background = stateColor(st);
      x.classList.toggle("work", st === "work");
      x.classList.toggle("can", !!st);
      x.classList.toggle("only", !!L && L.only === x.dataset.id);
    });
    paintSky();
  }
  // the wave of lights when an app is great: left to right, twice
  function celebrate() {
    sky.partyUntil = sky.t + 7000; sky.nextRocket = sky.t;
    if (reduced) return;
    const blds = $$("#sky-row .bld");
    blds.forEach((b, i) => (b.dataset.place = (i + 0.5) / blds.length));
    const t0 = performance.now();
    const step = (now) => {
      const t = (now - t0) / 1700;
      if (t >= 2) { sky.wave = -1; skyline(); return; }
      const f = t % 1, e = 0.5 - Math.cos(Math.PI * f) / 2;
      sky.wave = -0.2 + 1.4 * e;
      $$("#sky-row .bld").forEach((b) => {
        const lit = Math.abs(sky.wave - +b.dataset.place) < 0.11;
        b.querySelectorAll(".w").forEach((x) => { x.style.background = lit ? "var(--light)" : stateColor((S.live ? S.live.states : {})[x.dataset.id] || ""); });
      });
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
    skyRun();
  }
  // Sky.qml: stars, the street and its traffic, a festival's lights, rain, fireworks. Flat squares.
  const STRINGS = { diwali: ["#ffc94d", "#ff9f43", "#ffe08a"], ganesh: ["#ff7a45", "#ffc94d", "#e85d5d"],
    navratri: ["#e06c75", "#98c379", "#5b8def", "#c678dd", "#ffc94d"], christmas: ["#e06c75", "#98c379", "#ebe7dc"],
    ramzan: ["#98c379", "#ebe7dc", "#ffc94d"], holi: ["#e06c75", "#c678dd", "#5b8def", "#98c379", "#ffc94d"] };
  const PARTY = ["#ffc94d", "#8fcf7a", "#5b8def", "#e06c75", "#c678dd", "#ebe7dc", "#56b6c2"];
  const spot = (i, k) => { const v = Math.sin(i * k) * 43758.5453; return v - Math.floor(v); };
  function scene() {
    if (S.live) return S.live.scene || {};
    const l = D.labels[todayIso];
    return l ? { rain: l.rain, lights: l.lights, pandemic: "" } : {};
  }
  function skyMove(dt) {
    const el = $("#sky"), width = el.clientWidth, height = el.clientHeight, sc = scene();
    const traffic = sc.pandemic === "lockdown" ? 0 : sc.pandemic === "reopening" ? 1 : sky.cars.length;
    for (let i = 0; i < traffic; i++) { const c = sky.cars[i]; c.x += (c.dir * c.speed * dt) / Math.max(1, width); if (c.x > 1.05) c.x = -0.05; if (c.x < -0.05) c.x = 1.05; }
    if (sky.partyUntil < 0) return;
    if (sky.t < sky.partyUntil - 2200 && sky.t >= sky.nextRocket) {
      sky.nextRocket = sky.t + 380 + Math.random() * 420;
      sky.rockets.push({ x: width * (0.08 + Math.random() * 0.84), y: sky.ground, vy: -height * (0.9 + Math.random() * 0.3), top: Math.max(8, sky.ground * (0.08 + Math.random() * 0.3)), color: PARTY[Math.floor(Math.random() * PARTY.length)] });
    }
    for (const r of sky.rockets) {
      r.y += r.vy * dt;
      if (r.y <= r.top) {
        r.done = true;
        for (let i = 0; i < 24; i++) { const a = (i / 24) * Math.PI * 2, s = Math.max(60, height * (0.12 + Math.random() * 0.12)); sky.sparks.push({ x: r.x, y: r.y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: 1, color: i % 4 ? r.color : "#ebe7dc" }); }
      }
    }
    sky.rockets = sky.rockets.filter((r) => !r.done);
    for (const s of sky.sparks) { s.vy += height * 0.18 * dt; s.x += s.vx * dt; s.y += s.vy * dt; s.life -= dt * 0.8; }
    sky.sparks = sky.sparks.filter((s) => s.life > 0);
    if (sky.t > sky.partyUntil && !sky.rockets.length && !sky.sparks.length) sky.partyUntil = -1;
  }
  function paintSky() {
    const c = $("#sky-canvas"), ctx = c.getContext("2d"), el = $("#sky"), width = el.clientWidth, height = el.clientHeight, u = 3, sc = scene();
    const snap = (v) => Math.round(v / u) * u, ground = sky.ground;
    const roofAt = (x) => { for (const r of sky.roofs) if (x >= r.x - u && x <= r.x + r.w) return r.y; return ground; };
    ctx.clearRect(0, 0, width, height);
    if (!sc.rain) {
      ctx.fillStyle = "#3a4152";
      for (let i = 0; i < 46; i++) { const x = snap(spot(i + 1, 12.9898) * width), y = snap(spot(i + 1, 78.233) * ground * 0.8); if (y < roofAt(x) - 4 * u) ctx.fillRect(x, y, i % 7 ? 2 : u, i % 7 ? 2 : u); }
    }
    ctx.fillStyle = "#262c3b"; ctx.fillRect(0, ground + 5, width, 1);
    const traffic = sc.pandemic === "lockdown" ? 0 : sc.pandemic === "reopening" ? 1 : sky.cars.length;
    for (let i = 0; i < traffic; i++) {
      const car = sky.cars[i], x = snap(car.x * width), w = car.long * u;
      ctx.fillStyle = "#3a4152"; ctx.fillRect(x, ground + 1, w, u);
      ctx.fillStyle = "#ebe7dc"; ctx.fillRect(car.dir > 0 ? x + w : x - u, ground + 1, u, u);
      ctx.fillStyle = "#d9826e"; ctx.fillRect(car.dir > 0 ? x - 1 : x + w, ground + 1, 1, u);
    }
    const colors = STRINGS[sc.lights];
    if (colors) {
      const shift = Math.floor(sky.t / 600); let k = 0;
      for (let i = 0; i + 1 < sky.roofs.length; i++) {
        const a = sky.roofs[i], b = sky.roofs[i + 1], x0 = a.x + a.w, x1 = b.x, n = Math.max(2, Math.floor((x1 - x0) / (3 * u)));
        for (let j = 0; j <= n; j++, k++) { const f = j / n; ctx.fillStyle = colors[(k + shift) % colors.length]; ctx.fillRect(snap(x0 + (x1 - x0) * f), snap(a.y + (b.y - a.y) * f + Math.sin(f * Math.PI) * 4 * u) - u, u, u); }
      }
      for (const r of sky.roofs) for (let x = r.x + u; x < r.x + r.w - u; x += 3 * u, k++) { ctx.fillStyle = colors[(k + shift) % colors.length]; ctx.fillRect(snap(x), r.y - 2 * u, u, u); }
    }
    if (sc.rain) {
      const heavy = sc.rain === "heavy", drops = Math.round((heavy ? 320 : 140) * Math.min(1.5, (width * height) / 400000));
      const fall = height * (heavy ? 1.6 : 1.1), long = heavy ? 9 : 6;
      ctx.fillStyle = heavy ? "#6a7488" : "#4c5568"; ctx.globalAlpha = heavy ? 0.7 : 0.5;
      for (let i = 0; i < drops; i++) { const y = ((sky.t / 1000) * fall + i * 137.7) % (height + 40) - 20; const x = (spot(i + 1, 12.9898) * (width + 60) - y * 0.12 + width + 60) % (width + 60); ctx.fillRect(Math.round(x), Math.round(y), 1, long); }
      ctx.globalAlpha = 1;
    }
    ctx.fillStyle = "#ffc94d";
    for (const r of sky.rockets) ctx.fillRect(snap(r.x), snap(r.y), u, 2 * u);
    for (const s of sky.sparks) { ctx.globalAlpha = Math.max(0, s.life); ctx.fillStyle = s.color; ctx.fillRect(snap(s.x), snap(s.y), u, u); }
    ctx.globalAlpha = 1;
  }
  let skyTimer = 0;
  function skyRun() {
    clearInterval(skyTimer); skyTimer = 0;
    if (reduced || S.page !== "town" || document.hidden) return;
    skyTimer = setInterval(() => { sky.t += 40; skyMove(0.04); paintSky(); }, 40);
  }
  document.addEventListener("visibilitychange", skyRun);

  function townWho() {
    const L = S.live, p = S.hover, el = $("#t-who");
    if (p) {
      const st = L ? stateWords(L.states[p.id] || "") : "";
      el.innerHTML = `<span>${String(p.number).padStart(2, "0")}  ${esc(p.name)}, ${p.age}  ·  ${esc(p.job)}  ·  on a ${esc(p.device)}  ·  reads ${p.reads} words, ${p.patience} steps of patience${st ? "  ·  " + st : ""}</span>`;
    } else {
      const lbl = !L && D.labels[todayIso] ? D.labels[todayIso].none : "";
      el.innerHTML = `<span class="faint">One window, one local.</span>${lbl ? `<span class="faint">${esc(lbl)}</span>` : ""}`;
    }
  }
  function townSide() {
    const L = S.live, side = $("#t-side");
    if (!L) {
      side.innerHTML = `<div class="pad" style="padding-top:38px"><p class="h" style="padding-bottom:10px">This machine</p>
        <div class="meter"><span class="dim">Model</span><span>${esc(D.model.name)}</span></div>
        <div class="meter"><span class="dim">GPU memory</span><span>your own, shown in your window</span></div>
        <div class="meter"><span class="dim">Pace</span><span>6 s a step, a guess until a day runs</span></div>
        <div class="meter"><span class="dim">Android</span><span>Nothing connected</span></div>
        <p class="h" style="margin-top:34px">Recent days</p></div>
        <div class="pad scroll" style="flex:1;min-height:0;margin-top:8px">${D.days.slice(0, 8).map((d) => dayRow(d, false)).join("")}</div>`;
      return;
    }
    const rows = strips(L), shown = shownMoment(L);
    side.innerHTML = `<div class="top"><p class="h">${L.kept ? "A kept day" : "The day"}</p>${L.running ? "" : `<button class="btn" data-act="closeday">Close the day</button>`}</div>
      <div class="strips" data-coach="strips">${rows.map((r) => {
        const n = r.cells.length + r.left, cell = Math.max(3, Math.min(8, Math.floor((300 - 82 - 30) / Math.max(1, n)) - 2));
        return `<div class="srow"><span data-act="only" data-v="${r.id}" class="${L.only === r.id ? "only" : ""}">${esc(r.name)}</span><span class="cells">`
          + r.cells.map((c) => `<i data-act="pick" data-v="${c.i}" class="${shown === c.i ? "here" : ""}" style="width:${cell}px;background:${c.tone === "warn" ? "var(--light)" : "var(--step)"}"></i>`).join("")
          + (r.outcome ? `<i data-act="pick" data-v="${r.end}" class="${shown === r.end ? "here" : ""}" style="width:${cell * 2 + 2}px;background:${stateColor(r.outcome)}"></i>` : "")
          + `<i class="spare" style="width:${cell}px"></i>`.repeat(r.left) + `</span></div>`;
      }).join("")}</div>
      <div class="feedhead"><p class="h">Feed</p><span>${L.only ? `<button class="chip on" data-act="only" data-v="">Everyone</button>` : ""}<button class="chip ${L.steps ? "on" : ""}" data-act="steps">Steps</button></span></div>
      <div class="feed scroll" id="t-feed">${L.moments.filter((m) => (!L.only || L.only === m.local) && (L.steps || m.kind !== "STEP")).map((m) => {
        const st = m.kind === "STEP";
        return `<div class="line ${st ? "st" : "ev"} ${shown === m.i ? "here" : ""}" data-act="pick" data-v="${m.i}">
          <div class="k"><b style="color:${toneColor(m.tone)}">${esc(m.name)}  ·  ${st ? "step " + m.step : capital(m.kind)}</b><span>${esc(m.at)}</span></div>
          ${st ? `<div class="t1">${esc(m.title)}</div>` : ""}<div class="t2">${esc(m.text)}</div></div>`;
      }).join("") || '<p class="faint" style="padding:4px 32px">Nothing yet. The first local is on the way.</p>'}</div>`;
    const feed = $("#t-feed");
    if (L.sel < 0) feed.scrollTop = feed.scrollHeight;
    else { const here = feed.querySelector(".here"); if (here) here.scrollIntoView({ block: "nearest" }); }
  }
  function dayRow(d, long) {
    return `<div class="dayrow" data-act="openday" data-v="${d.day}" style="grid-template-columns:${long ? "120px" : "78px"} minmax(0,1fr) auto;height:${long ? 64 : 52}px">
      <div class="when"><span>${dmon(d.date)}</span><span>${d.time}</span></div>
      <div class="what"><div>${esc(d.task)}${long && d.today ? "   " + esc(d.today) : ""}</div>
        ${long ? `<div class="dim" style="font-size:13px;margin-top:3px">${d.locals.map((l) => esc(l.name) + (l.outcome ? " " + stateWords(l.outcome) : "")).join("  ·  ")}</div>`
               : `<div class="marks" style="margin-top:4px">${d.locals.map((l) => `<i style="width:7px;height:9px;background:${stateColor(l.outcome)}"></i>`).join("")}</div>`}</div>
      ${long ? `<div class="marks" style="padding-left:16px">${d.locals.map((l) => `<i style="width:9px;height:12px;background:${stateColor(l.outcome)}"></i>`).join("")}</div>` : "<span></span>"}
    </div>`;
  }
  function viewer() {
    const el = $("#viewer"), L = S.live;
    if (!L || S.viewer < 0) { el.hidden = true; return; }
    const shots = L.moments.filter((m) => m.shot), k = shots.findIndex((m) => m.i === S.viewer), m = shots[k];
    if (!m) { el.hidden = true; return; }
    el.hidden = false;
    el.innerHTML = `<div class="vt"><span>${esc(m.name)}  ·  ${m.kind === "STEP" ? "step " + m.step + "  ·  " + esc(m.title) : esc(m.kind)}</span><button class="btn" data-act="closeviewer">Close</button></div>
      <img src="${esc(m.shot)}" alt="The screen ${esc(m.name)} saw">
      <div class="vb"><button class="btn" data-act="viewer" data-v="${k > 0 ? shots[k - 1].i : m.i}" ${k > 0 ? "" : "disabled"}>‹</button><span class="dim" style="align-self:center">${k + 1} of ${shots.length}</span><button class="btn" data-act="viewer" data-v="${k < shots.length - 1 ? shots[k + 1].i : m.i}">›</button></div>`;
  }
  function drawTown() {
    townHead();
    skyHeight();
    townMoment();
    townSide();
    townWho();
    viewer();
    requestAnimationFrame(() => { skyline(); townMoment(); });
  }
  $("#sky").addEventListener("pointerover", (e) => { const w = e.target.closest(".w"); if (w) { S.hover = folk[w.dataset.id]; townWho(); } });
  $("#sky").addEventListener("pointerout", (e) => { if (e.target.closest(".w")) { S.hover = null; townWho(); } });

  // ---------- Set up ----------
  const setupPage = $("#p-setup");
  setupPage.innerHTML = `<div class="three"><div class="col" id="su-what"></div><div class="col" id="su-who"></div><div class="col scroll" id="su-when"></div></div>`;
  const going = () => { const out = []; for (const f of D.roster) for (const j of f.jobs) for (const p of j.people.slice(0, S.counts[j.key] || 0)) out.push(p); return out; };
  const task = () => D.tasks.find((t) => t.ref === S.taskRef);
  const dates = () => (S.wholeYear ? D.calendar.sample : [S.day]);
  function when() {
    if (S.wholeYear) return { ok: true, label: `${D.calendar.sample.length} days, one after another, from January to December.` };
    const l = D.labels[S.day];
    return l ? { ok: true, label: l[S.pandemic || "none"] } : { ok: false, label: "That day is not in the town's calendar. It covers " + D.calendar.years.join(", ") + "." };
  }
  function spell(s) { return s < 90 ? `${Math.round(s)} seconds` : s < 5400 ? `${Math.round(s / 60)} minutes` : `${(s / 3600).toFixed(1)} hours`; }
  function estimate() {
    const pat = going().map((p) => p.patience), n = pat.length, days = dates().length, secs = 6, usual = 6;
    const typical = days * pat.reduce((a, p) => a + Math.min(p, usual) * secs, 0), worst = days * pat.reduce((a, p) => a + p * secs, 0);
    return { time: n ? `About ${spell(typical)}` : "Nobody yet",
      note: n ? `${n} local${n === 1 ? "" : "s"}${days > 1 ? ` on ${days} days` : ""}, one at a time. Up to ${spell(worst)} if everyone uses all their patience. Reckoned at 6 seconds a step until a day has run here.` : "Choose who goes out.",
      gpu: `The model needs about ${(D.model.size_gb + 0.4).toFixed(1)} GB of graphics memory.` };
  }
  function suWhat() {
    const t = task();
    $("#su-what").innerHTML = `<p class="h">What they test</p>
      <div class="segs" style="margin-top:16px"><button class="seg ${S.kind === "saved" ? "on" : ""}" data-act="kind" data-v="saved">A saved task</button><button class="seg ${S.kind === "site" ? "on" : ""}" data-act="kind" data-v="site">A site</button><button class="seg ${S.kind === "apk" ? "on" : ""}" data-act="kind" data-v="apk">An Android app</button></div>
      ${S.kind === "saved" ? `<div class="tasklist scroll" style="margin-top:18px;max-height:55%">${D.tasks.map((x) => `<div class="t ${x.ref === S.taskRef ? "on" : ""}" data-act="task" data-v="${esc(x.ref)}" data-coach="task-${esc(x.ref)}"><span>${esc(x.app)}</span><span>${esc(x.ref.split(":")[1])}${x.platform === "android" ? "  ·  Android" : ""}</span></div>`).join("")}</div>
        <div class="story">${esc(t.story).replace(/\n/g, " ")}</div><p class="dim" style="margin:10px 0 0">Done when ${esc(t.check)}.</p>`
      : `<div style="margin-top:18px;display:flex;flex-direction:column;gap:8px">
        ${S.kind === "site" ? `<span class="label" style="margin:0">Address</span><input class="field mono" id="su-url" placeholder="http://localhost:5173 or https://your-site.com" value="${esc(S.site.url)}">`
          : `<label class="drop"><input type="file" id="su-apk" accept=".apk"><div>${S.apk ? esc(S.apk.name) + ", " + (S.apk.size / 1048576).toFixed(1) + " MB" : "Drop the app's APK here, or choose it"}</div><div class="dim" style="font-size:13px;margin-top:6px">No emulator or phone is connected yet.</div></label>`}
        <span class="label">What should they try to do</span><textarea class="field" id="su-goal" placeholder="Sign up, find the pricing page and choose the cheapest plan.">${esc(S.site.goal)}</textarea>
        <span class="label">How do we know it worked</span>
        <div class="segs"><button class="seg ${S.site.check === "page_text" ? "on" : ""}" data-act="check" data-v="page_text">The screen shows</button>${S.kind === "site" ? `<button class="seg ${S.site.check === "url_contains" ? "on" : ""}" data-act="check" data-v="url_contains">The address contains</button><button class="seg ${S.site.check === "download" ? "on" : ""}" data-act="check" data-v="download">A file is saved</button>` : ""}<button class="seg ${S.site.check === "word" ? "on" : ""}" data-act="check" data-v="word">Take their word</button></div>
        ${S.site.check === "page_text" || S.site.check === "url_contains" ? `<input class="field" id="su-value" placeholder="${S.site.check === "page_text" ? "Welcome aboard" : "/thank-you"}" value="${esc(S.site.value)}">` : ""}
        <span class="label">Files on their device</span><label class="drop" style="padding:16px 14px"><input type="file" multiple><span class="faint">Drop files here if the task needs something to upload</span></label>
      </div>`}`;
  }
  function suWho() {
    const g = going();
    $("#su-who").innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><p class="h">Who goes out</p><span><button class="chip on" data-act="everyone" data-v="1">One of each job</button><button class="chip on" data-act="everyone" data-v="0">Nobody</button></span></div>
      <div style="font:400 22px/1.2 var(--display);margin-top:14px;color:${g.length ? "var(--ink)" : "var(--dim)"}">${g.length ? g.length + " going out" : "Nobody yet. Add someone below."}</div>
      <div class="scroll" id="su-people" style="flex:1;min-height:0;margin-top:14px;padding-right:12px">${D.roster.map((f) => {
        const out = f.jobs.reduce((n, j) => n + (S.counts[j.key] || 0), 0);
        return `<div class="fam"><p class="h" style="color:${out ? "var(--dim)" : "var(--faint)"}">${esc(f.family)}${out ? "  ·  " + out : ""}</p><button class="chip on" data-act="family" data-v="${esc(f.family)}">${out ? "None" : "One of each"}</button></div>`
          + f.jobs.map((j) => { const n = S.counts[j.key] || 0;
            return `<div class="job"><div class="nm"><div style="color:${n ? "var(--ink)" : "var(--dim)"}">${esc(j.label)}</div><div>${n ? j.people.slice(0, n).map((p) => esc(p.name)).join(", ") : j.people.length + (j.people.length === 1 ? " person, at home" : " people, at home")}</div></div>
              <div class="stepper"><button class="btn sq" style="opacity:${n > 0 ? 1 : 0.35}" data-act="count" data-v="${j.key}" data-d="-1" aria-label="One fewer ${esc(j.label)}">−</button><b class="${n ? "n" : ""}">${n}</b><button class="btn sq" style="opacity:${n < j.people.length ? 1 : 0.35}" data-act="count" data-v="${j.key}" data-d="1" data-coach="plus-${j.key}" aria-label="One more ${esc(j.label)}">+</button></div></div>`; }).join("");
      }).join("")}</div>`;
  }
  function suWhen() {
    const w = when(), c = estimate(), g = going(), ready = g.length > 0 && w.ok;
    $("#su-when").innerHTML = `<p class="h" style="padding-bottom:8px">When</p>
      <div class="daypick" style="opacity:${S.wholeYear ? 0.45 : 1}"><button class="btn" data-act="shift" data-v="-1" aria-label="The day before">‹</button><input class="field mono" id="su-day" value="${esc(S.day)}" aria-label="The day"><button class="btn" data-act="shift" data-v="1" aria-label="The day after">›</button></div>
      <p style="margin:8px 0 0;line-height:1.2;color:${w.ok ? "var(--ink)" : "var(--bad)"}">${esc(w.label)}</p>
      <div class="segs" style="margin-top:12px">${D.calendar.picks.map((p) => `<button class="seg ${!S.wholeYear && S.day === p.date ? "on" : ""}" data-act="pick-day" data-v="${p.date}" data-coach="pick-${p.date}">${esc(p.label)}</button>`).join("")}<button class="seg ${S.wholeYear ? "on" : ""}" data-act="year">A year in ${D.calendar.sample.length} days</button></div>
      <div class="segs" style="margin-top:12px"><button class="seg ${!S.pandemic ? "on" : ""}" data-act="pandemic" data-v="">No pandemic</button><button class="seg ${S.pandemic === "lockdown" ? "on" : ""}" data-act="pandemic" data-v="lockdown">Lockdown</button><button class="seg ${S.pandemic === "reopening" ? "on" : ""}" data-act="pandemic" data-v="reopening">Reopening</button></div>
      <p class="h" style="margin-top:34px;padding-bottom:4px">It will take</p>
      <p class="cost" style="color:${g.length ? "var(--ink)" : "var(--dim)"}">${esc(c.time)}</p>
      <p class="dim" style="margin:8px 0 0;line-height:1.2">${esc(c.note)}</p>
      <p class="dim" style="margin:10px 0 0;font-size:13px">${esc(c.gpu)}</p>
      <div style="padding-top:18px;display:flex;flex-direction:column;align-items:flex-start"><button class="chip ${S.take ? "on" : ""}" data-act="take">${S.take ? "●" : "○"}  Ask what their job let them notice</button><button class="chip ${S.watch ? "on" : ""}" data-act="watch">${S.watch ? "●" : "○"}  Show the browser while they work</button></div>
      <div style="margin-top:14px"><button class="btn wide ${ready ? "strong" : "off"}" data-act="start" data-coach="start">${g.length ? "Start the day with " + g.length : "Choose who goes out"}</button></div>`;
  }
  function drawSetup() {
    const keep = $("#su-people") ? $("#su-people").scrollTop : 0;
    suWhat(); suWho(); suWhen();
    $("#su-people").scrollTop = keep;
  }
  function command() {
    const py = os === "win" ? ".venv\\Scripts\\python" : ".venv/bin/python";
    let line = `${py} -m town run ${S.taskRef} ${going().map((p) => p.id).join(" ")}`;
    if (S.wholeYear) line += ` --year ${D.calendar.years[0]}`; else if (S.day !== todayIso) line += ` --date ${S.day}`;
    if (S.pandemic) line += ` --pandemic ${S.pandemic}`;
    if (S.watch) line += " --watch";
    if (!S.take) line += " --no-take";
    return line;
  }
  function start() {
    const ids = going().map((p) => p.id).sort().join(" ");
    if (S.kind === "saved" && !S.wholeYear) {
      const kept = D.days.filter((d) => d.ref === S.taskRef && d.locals.map((l) => l.id).sort().join(" ") === ids && d.dates[0] === S.day && !d.locals.some((l) => l.outcome === "STOPPED") && D.logs[d.day]);
      if (kept.length) return playDay(kept[kept.length - 1].day);
    }
    const others = D.days.filter((d) => d.ref === S.taskRef);
    S.notice = {
      head: "This copy plays only days that really happened. In your window this one runs for real.",
      cmd: S.kind === "saved" ? command() : "",
      sub: S.kind === "saved" ? "" : "In your window, Start writes a task card for it in tasks/mine/ and sends them out.",
      days: S.kind === "saved" && others.length ? others.length : 0,
    };
    draw();
  }

  // ---------- Days ----------
  function drawDays() {
    $("#p-days").innerHTML = `<div style="position:absolute;inset:0;display:flex;flex-direction:column;padding:38px var(--gutter) 0">
      <p class="h">Days</p><div class="big">${D.days.length} days kept.</div><p class="sub">Open a day to read it again, or set two of the same task side by side.</p>
      <div class="scroll" style="flex:1;min-height:0;margin-top:20px;padding:0 12px;margin-left:-12px;margin-right:-12px" data-coach="dayrow-first">${D.days.map((d) => dayRow(d, true)).join("")}</div></div>`;
  }

  // ---------- Rooms ----------
  const lit = (tone) => (tone === "hooked" ? "var(--light)" : tone === "with" ? "var(--waiting)" : tone === "drift" ? "var(--step)" : tone === "low" ? "var(--dark)" : "transparent");
  const sameColor = (s) => (s === "yes" ? "var(--good)" : s === "partly" ? "var(--dim)" : s === "no" ? "var(--bad)" : "var(--faint)");
  const sameWords = (s) => (s === "yes" ? "has your point" : s === "partly" ? "has part of it" : s === "no" ? "does not have it" : "");
  function drawRooms() {
    const page = $("#p-rooms");
    if (S.talk) return drawTalk(page);
    const r = D.rooms.find((x) => x.id === S.roomId);
    page.innerHTML = `<div class="three">
      <div class="col"><p class="h">The room</p>
        <div style="margin-top:14px">${D.rooms.map((x) => `<div class="room-t ${x.id === S.roomId ? "on" : ""}" data-act="room" data-v="${x.id}"><span>${esc(x.name)}</span><span>${x.minutes} min</span></div>`).join("")}</div>
        <div style="margin-top:18px;display:flex;flex-direction:column;gap:6px;line-height:1.25"><div>${esc(r.about)}.</div><div class="dim">${esc(r.where)}. ${esc(r.when)}.</div>
          <div class="dim">${r.rubric ? `Marked on ${esc(r.rubric.toLowerCase())}, out of ${r.out_of}.` : "A crowd gives no marks."}${r.point_by ? ` This room expects your point within ${r.point_by} ${r.point_by === 1 ? "minute" : "minutes"}.` : ""}</div></div>
        <p class="h" style="margin-top:24px">Who sits there</p>
        <div class="scroll" style="flex:1;min-height:0;margin-top:8px">${r.seats.map((s) => `<div class="seat"><div>${esc(s.name)}${s.grader ? "  ·  marks" : ""}${s.job ? "  ·  " + esc(s.job) : ""}</div><div>${esc(s.why)}.</div></div>`).join("")}</div>
      </div>
      <div class="col"><p class="h" style="padding-bottom:8px">The talk</p>
        <label class="drop" style="min-height:96px"><input type="file" id="rm-files" multiple accept=".pdf,.pptx,.txt,.md,.wav,.mp3,.m4a,.ogg,.flac,.webm,.aac,.mp4">
          ${!S.deck && !S.speech ? `<div>Drop the talk here, or choose it</div><div class="dim" style="font-size:13px;margin-top:5px">A deck (.pdf or .pptx), what is said (.txt, .md or a recording), or one of each.</div>` : ""}
          ${S.deck ? `<div>Slides   ${esc(S.deck)}</div>` : ""}${S.speech ? `<div>Said   ${esc(S.speech)}</div>` : ""}
          ${!!S.deck !== !!S.speech ? `<div class="faint" style="font-size:12px;margin-top:5px">${S.deck ? "No script: what is said comes from the speaker notes, if the deck has them." : "No deck: the room only hears you."}</div>` : ""}</label>
        ${S.deck || S.speech ? `<div><button class="chip on" data-act="clear">Clear</button></div>` : ""}
        <span class="label" style="margin-top:16px">How long it runs, in minutes</span><input class="field mono" id="rm-min" style="width:120px;margin-top:8px" placeholder="${r.minutes}">
        <span class="faint" style="font-size:12px;margin-top:8px">Left empty, a script is timed at 150 words a minute. A recording times itself.</span>
        <span class="label" style="margin-top:16px">The one thing they should take away</span><textarea class="field" id="rm-point" style="margin-top:8px" placeholder="Left empty, it is read from the talk."></textarea>
        <span class="label" style="margin-top:16px">What the talk is for</span><input class="field" id="rm-about" style="margin-top:8px" placeholder="The role you are interviewing for">
        ${r.rubric ? `<div style="margin-top:8px"><button class="chip ${S.grade ? "on" : ""}" data-act="grade">${S.grade ? "●" : "○"}  Let the graders mark it</button></div>` : ""}
        <div style="margin-top:14px"><button class="btn wide ${S.deck || S.speech ? "strong" : "off"}" data-act="give">${!S.deck && !S.speech ? "Choose the talk" : "Give the talk to " + r.seats.length}</button></div>
      </div>
      <div class="col"><p class="h">Kept talks</p>
        <div class="scroll" style="flex:1;min-height:0;margin-top:8px;padding:0 12px;margin-left:-12px;margin-right:-12px" data-coach="talk-first">${D.talks.map((t) => `<div class="talkrow" data-act="opentalk" data-v="${t.talk}">
          <div><div class="dim" style="font-size:13px">${dmon(t.date)}</div><div class="faint mono" style="font-size:12px">${t.time}</div></div>
          <div style="min-width:0"><div class="r1"><span>${esc(t.name)}</span><span style="font-size:13px;color:${t.mark ? "var(--ink)" : "var(--dim)"}">${esc(t.mark || t.got)}</span></div>
            <div class="dim" style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(t.source)}  ·  ${esc(t.clock)}</div>
            <div class="marks" style="margin-top:3px">${t.lit.map((x) => `<i style="width:7px;height:9px;background:${lit(x)};${x === "out" ? "box-shadow:inset 0 0 0 1px var(--dark)" : ""}"></i>`).join("")}</div></div></div>`).join("")}</div>
      </div></div>`;
    const files = $("#rm-files");
    files.addEventListener("change", () => {
      for (const f of files.files) { if (/\.(pdf|pptx)$/i.test(f.name)) S.deck = f.name; else S.speech = f.name; }
      drawRooms(); coachPlace();
    });
  }
  function drawTalk(page) {
    const T = S.talk, n = Math.max(1, T.parts.length), shown = S.talkSel >= 0 && S.talkSel < T.parts.length ? S.talkSel : T.parts.length - 1, part = T.parts[shown];
    const width = Math.max(320, (page.clientWidth || 1000) - Math.max(340, Math.min(440, (page.clientWidth || 1000) * 0.33)) - 88);
    const nameWidth = window.innerWidth <= 900 ? 90 : 132, cell = Math.max(6, Math.min(34, Math.floor((width * 0.5 - nameWidth) / n) - 3));
    const lk = S.looking;
    const m = T.marks;
    page.innerHTML = `<div class="talk"><div class="left">
      <p class="h">${esc(T.name)}${T.source ? "  ·  " + esc(T.source) : ""}${T.parts.length ? "  ·  " + esc(T.clock) : ""}</p>
      <div class="big mid">${esc(T.head)}</div><p class="dim" style="margin:6px 0 0">${esc(T.sub)}</p>
      ${T.point ? `<div style="margin-top:26px"><p class="h">Your point</p><div style="font-size:16px;margin-top:5px">${esc(T.point)}</div><div class="dim" style="font-size:13px;margin-top:5px">${esc(T.stated)}</div></div>` : ""}
      <div class="grid" data-coach="grid">
        <div class="heads" style="padding-left:${nameWidth}px;gap:3px">${T.parts.map((p, i) => `<span class="${i === shown ? "on" : ""}" style="width:${cell}px" data-act="part" data-v="${i}">${cell >= 16 || i === shown ? i + 1 : ""}</span>`).join("")}</div>
        <div class="scroll" style="flex:1;min-height:0;margin-top:4px">${T.listeners.map((l, li) => { const at = l.cells[shown];
          return `<div class="lrow" data-li="${li}"><span class="who" style="width:${nameWidth}px">${esc(l.name)}${l.grader ? "  ·  marks" : ""}</span>
            <span style="display:flex;gap:3px">${T.parts.map((p, i) => { const c = l.cells[i];
              return `<i class="c" data-act="part" data-v="${i}" style="width:${cell}px;background:${c ? lit(c.tone) : "transparent"};${i === shown && c ? "box-shadow:inset 0 0 0 1px var(--ink)" : c && c.tone === "out" ? "box-shadow:inset 0 0 0 1px var(--dark)" : !c ? "border-bottom:2px solid var(--line)" : ""}"></i>`; }).join("")}</span>
            <span class="num">${at ? at.attention : ""}</span><span class="inner" style="color:${at && at.inner ? "var(--ink)" : "var(--faint)"}">${!at ? "" : at.inner ? esc(at.inner) : at.tone === "low" || at.tone === "out" ? esc(at.band) : ""}</span></div>`; }).join("")}</div>
      </div>
      <div class="foot">${part ? `<div>Part ${shown + 1} of ${T.parts.length}  ·  ${esc(part.at)}  ·  ${esc(part.title)}${part.moments ? "  ·  " + esc(part.moments) : ""}</div>` : ""}<div id="tk-foot">${footLine(lk)}</div></div>
    </div>
    <div class="side"><div class="top"><p class="h">${T.kept ? "A kept talk" : "The talk"}</p><button class="btn" data-act="closetalk">Close the talk</button></div>
      <div class="results scroll">
        ${m.rubric ? `<p class="h" style="margin-top:0">${esc(m.rubric)}, out of ${m.out_of}</p>` : ""}
        ${m.graders.map((g) => `<div class="grader"><div class="gname"><span>${esc(g.name)}</span><span>${esc(g.head)}</span></div>
          ${g.verdict ? `<div class="dim" style="font-size:13px">${esc(g.verdict)}</div>` : ""}
          ${g.marks.map((k) => `<div class="mk"><span style="color:${k.level ? "var(--ink)" : "var(--faint)"}">${esc(k.name)}</span><span>${k.level > 0 ? k.level + " of " + k.top : ""}</span></div>${k.reason ? `<div class="why">${esc(k.reason)}${k.about ? "  (" + esc(k.about) + ")" : ""}</div>` : ""}`).join("")}
          ${g.bonus && g.bonus.length ? `<p class="dim" style="margin-top:6px">${esc(g.bonus.join("  ·  "))}</p>` : ""}
          ${g.overall ? `<p style="margin-top:6px">“${esc(g.overall)}”</p>` : ""}
          ${g.dropped > 0 ? `<p class="faint" style="font-size:12px">${g.dropped} ${g.dropped === 1 ? "mark was" : "marks were"} dropped by the checks.</p>` : ""}</div>`).join("")}
        ${m.graders.length ? `<p class="faint" style="font-size:12px;padding-bottom:10px">A small model marks kindly. Read the reasons before the number, and check with real listeners.</p>` : ""}
        ${T.markers.length ? `<p class="h" style="margin-top:4px">The room</p>${T.markers.map((k) => `<p style="color:${k.tone === "good" ? "var(--good)" : k.tone === "bad" ? "var(--bad)" : "var(--ink)"}">${esc(k.says)}${k.says.endsWith(".") ? "" : "."}</p>`).join("")}` : ""}
        ${T.listeners.some((l) => l.same) ? `<p class="h">What they say it was about</p>${T.listeners.filter((l) => l.same).map((l) => `<div style="padding-bottom:8px"><div style="font-size:12px;color:${sameColor(l.same)}">${esc(l.name)}  ·  ${sameWords(l.same)}</div>${l.point ? `<p style="margin:1px 0 0">${esc(l.point)}</p>` : ""}</div>`).join("")}` : ""}
        ${T.listeners.some((l) => l.question) ? `<p class="h">What they would ask</p>${T.listeners.filter((l) => l.question).map((l) => `<div style="padding-bottom:8px"><div class="faint" style="font-size:12px">${esc(l.name)}</div><p style="margin:1px 0 0">${esc(l.question)}</p></div>`).join("")}` : ""}
        ${T.measured.length + T.notes.length ? `<p class="h">Measured</p>${T.measured.map((x) => `<p class="dim">${esc(x)}.</p>`).join("")}${T.notes.map((x) => `<p class="faint" style="font-size:12px">${esc(x)}</p>`).join("")}` : ""}
      </div></div></div>`;
    page.querySelectorAll(".lrow").forEach((row) => {
      row.addEventListener("pointerenter", () => { S.looking = T.listeners[+row.dataset.li]; $("#tk-foot").innerHTML = footLine(S.looking); });
      row.addEventListener("pointerleave", () => { S.looking = null; $("#tk-foot").innerHTML = footLine(null); });
    });
  }
  // under the grid: the listener the pointer is on, or what the colours mean
  function footLine(lk) {
    return lk ? `<div class="dim" style="font-size:13px;margin-top:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc([lk.name + (lk.job ? ", " + lk.job : ""), lk.note, lk.unknown ? "did not know: " + lk.unknown : "", lk.decided ? "made up their mind at " + lk.decided : ""].filter((x) => x).join("  ·  "))}</div>`
      : `<div class="legend">${[["hooked", "hooked"], ["with", "with you"], ["drift", "drifting"], ["low", "looking away"], ["out", "gone"]].map(([t, w]) => `<span><i style="background:${lit(t)};${t === "out" ? "box-shadow:inset 0 0 0 1px var(--dark)" : ""}"></i>${w}</span>`).join("")}</div>`;
  }

  // ---------- Report ----------
  function rline(row, nameWidth, mark) {
    const r = D.report;
    return `<div class="rline" style="grid-template-columns:${nameWidth}px minmax(0,1fr) auto auto"><span class="name">${esc(row.name || "")}</span>
      <span class="bar"><i style="width:${(row.part || 0) * 100}%"></i>${mark ? `<b style="left:${Math.round(r.benchmark * 100)}%"></b>` : ""}</span>
      <span class="n">${row.of ? row.done + " of " + row.of : ""}</span><span class="p">${esc(row.pct || "")}</span></div>`;
  }
  function drawReport() {
    const r = D.report;
    $("#p-report").innerHTML = `<div class="report"><div class="col" style="position:relative">
      <p class="h">The town so far</p><div class="big" data-coach="report-head">${esc(r.head)}</div><p class="sub" style="line-height:1.25;margin-top:8px">${esc(r.sub)}</p>
      <div style="margin-top:34px">${rline(r.all, 120, false)}${rline({ name: "Real people", part: r.benchmark, pct: r.bench, of: 0, done: 0 }, 120, false)}
        <p class="faint" style="font-size:12px;margin:8px 0 0">Real people: the average task completion across 1,189 tasks in 115 usability tests (Sauro).</p></div>
      ${r.checked ? `<div style="margin-top:34px"><p class="h" style="padding-bottom:10px">The model's own mistakes</p>
        <p class="dim" style="font-size:13px;margin:0 0 8px;line-height:1.2">Counted on the ${r.checked_runs} newer runs. A mistake here is the model's, not the local's: an answer no person could give. It is asked again, up to twice.</p>
        ${rline(Object.assign({}, r.clean, { name: "No mistake cost a step" }), 220, false)}${r.cost.of > 0 ? rline(Object.assign({}, r.cost, { name: "A mistake cost a step" }), 220, false) : ""}
        <div class="rline" style="grid-template-columns:1fr auto"><span class="dim">Answers the model gave again</span><span class="mono" style="font-size:13px">${r.retries}</span></div></div>` : ""}
      <p class="faint" style="font-size:12px;margin-top:auto;padding-top:24px;line-height:1.2">Days that were stopped or hit an error are left out. These counts are signals to check with real users, not verdicts.</p></div>
      <div class="col scroll"><p class="h" style="padding-bottom:8px">By task</p>${r.by_task.map((x) => rline(x, 280, true)).join("")}
        <p class="h" style="padding:30px 0 8px">By family</p>${r.by_family.map((x) => rline(x, 280, true)).join("")}
        <p class="faint" style="font-size:12px;padding-top:14px">The line on each bar is where real people finish.</p></div></div>`;
  }

  // ---------- Install: the guide's own page ----------
  let os = store.get("os", /Win/i.test(navigator.platform || navigator.userAgent) ? "win" : "nix");
  let done = new Set(store.get("done", []));
  let openStep = store.get("open", 0);
  const STEPS = [
    { t: "Have what it runs on", b: `<p>Python 3.11 or newer, Git, Google Chrome and Ollama (ollama.com). The locals use the Chrome you already have. A graphics card helps: Locals was built on one with 8 GB, and the model takes about 2.7 GB of it.</p>`, w: "python --version\ngit --version\nollama --version", n: "python3 --version\ngit --version\nollama --version" },
    { t: "Get the town", b: "", w: "git clone https://github.com/BiswasMosam/Locals\ncd Locals" },
    { t: "Give it its own Python", b: `<p>This brings the window (PySide6), the browser driver (Playwright) and the readers for decks and PDFs. There is no separate browser to download.</p>`, w: "python -m venv .venv\n.venv\\Scripts\\pip install -r requirements.txt", n: "python3 -m venv .venv\n.venv/bin/pip install -r requirements.txt" },
    { t: "Check it", b: `<p>Every test should pass, with no browser and no model. The second line lists all 114 locals.</p>`, w: ".venv\\Scripts\\python -m unittest discover -s tests -t .\n.venv\\Scripts\\python -m town people", n: ".venv/bin/python -m unittest discover -s tests -t .\n.venv/bin/python -m town people" },
    { t: "Open the window on a practice day", b: `<p>A scripted day with no model and no browser. Add <code>--finish</code> to see everyone done.</p>`, w: ".venv\\Scripts\\python -m town app --demo", n: ".venv/bin/python -m town app --demo" },
    { t: "Bring the model", b: `<p>Locals finds Ollama at 127.0.0.1:11434. Set <code>OLLAMA_HOST</code> or <code>LOCALS_MODEL</code> to change either.</p>`, w: "ollama pull qwen3:4b-instruct\nollama list" },
    { t: "Open the town", b: `<p>The real window opens on Town, the same as this copy.</p>`, w: ".venv\\Scripts\\python -m town", n: ".venv/bin/python -m town" },
  ];
  const EXTRA = [
    { t: "For Android apps", b: `<p>Install Android Studio and make a virtual device. Start it with the graphics card on, or Flutter screens come out blank. Then choose An Android app on Set up and drop the APK.</p>`, w: "emulator -avd Pixel_7 -gpu host\nadb devices" },
    { t: "For recorded talks", b: `<p>Turns a recording into words on the processor. Decks and scripts need nothing extra.</p>`, w: ".venv\\Scripts\\pip install faster-whisper", n: ".venv/bin/pip install faster-whisper" },
    { t: "If a day never gets past its first step", b: `<p>Ollama is not answering. It should list the model; if it runs elsewhere, set <code>OLLAMA_HOST</code>.</p>`, w: "ollama list" },
    { t: "If the graphics card is still full after a run", b: `<p>From the terminal the model stays loaded for ten minutes. The window unloads it when it closes.</p>`, w: "ollama stop qwen3:4b-instruct" },
  ];
  const cmdBox = (s) => { const text = os === "nix" && s.n ? s.n : s.w; return `<div class="cmd"><pre>${esc(text)}</pre><button class="copy" data-act="copy">Copy</button></div>`; };
  let town3d = null;
  function drawInstall() {
    const page = $("#p-install");
    if (!page.firstChild) {
      page.innerHTML = `<div class="install"><div class="left scroll" id="in-left"></div><div class="town3d" id="in-town"><canvas id="in-canvas" aria-label="The town in 3D"></canvas><div class="tags" id="in-tags"></div><div class="who3" id="in-who" hidden></div><div class="cap" id="in-cap"></div></div></div>`;
      try {
        if (!window.THREE || !window.LocalsTown) throw 0;
        town3d = window.LocalsTown($("#in-canvas"), D.families.map((f) => ({ family: f.family, jobs: [{ people: f.people }] })), { tags: $("#in-tags"), hover: who3 });
      } catch (_) { $("#in-town").innerHTML = '<div class="cap">The town needs WebGL to show here.</div>'; }
    }
    const left = $("#in-left"), keep = left.scrollTop;
    left.innerHTML = `<p class="h">Install</p><div class="big">Seven steps to a town.</div>
      <p class="sub">Everything in this copy is real data from the town. These steps put the real one on your machine.</p>
      <div class="segs" style="margin:22px 0 18px"><button class="seg ${os === "win" ? "on" : ""}" data-act="os" data-v="win">Windows</button><button class="seg ${os === "nix" ? "on" : ""}" data-act="os" data-v="nix">macOS or Linux</button></div>
      ${STEPS.map((s, i) => `<div class="istep ${done.has(i) ? "done" : ""} ${openStep === i ? "open" : ""}" data-coach="istep-${i}"><button data-act="istep" data-v="${i}"><b>${i + 1}</b><span>${esc(s.t)}</span><i></i></button>
        ${openStep === i ? `<div class="body">${s.b}${cmdBox(s)}<button class="btn ${done.has(i) ? "" : "strong"}" data-act="idone" data-v="${i}">${done.has(i) ? "Not done yet" : "Done"}</button></div>` : ""}</div>`).join("")}
      <p class="h" style="margin:30px 0 8px">Also</p>
      ${EXTRA.map((s, k) => { const i = 100 + k; return `<div class="istep ${openStep === i ? "open" : ""}"><button data-act="istep" data-v="${i}"><b></b><span>${esc(s.t)}</span><span></span></button>${openStep === i ? `<div class="body">${s.b}${cmdBox(s)}</div>` : ""}</div>`; }).join("")}`;
    left.scrollTop = keep;
    if (town3d) {
      const lit = Math.round((people.length * done.size) / STEPS.length);
      const order = installOrder();
      const on = new Set(order.slice(0, lit));
      town3d.setStates((p) => (on.has(p.id) ? "light" : "dark"));
      $("#in-cap").innerHTML = done.size === STEPS.length ? "<b>The whole town is up.</b>" : done.size ? `<b>${done.size} of ${STEPS.length}</b> steps done  ·  ${lit} awake` : `<b>${people.length} locals</b>, all asleep.`;
    }
  }
  let _order = null;
  function installOrder() {
    if (_order) return _order;
    const ids = people.map((p) => p.id);
    let s = 11;
    for (let i = ids.length - 1; i > 0; i--) { s = (s * 16807) % 2147483647; const j = s % (i + 1); [ids[i], ids[j]] = [ids[j], ids[i]]; }
    return (_order = ids);
  }
  function who3(p, x, y) {
    const el = $("#in-who");
    if (!p) { el.hidden = true; return; }
    const r = $("#in-town").getBoundingClientRect();
    el.innerHTML = `<div style="font:600 15px var(--display)">${esc(p.name)} <span class="dim" style="font:400 13px var(--text)">${p.age}</span></div><div>${esc(p.job)}</div><div class="dim" style="margin-top:4px">${esc(p.place || "")}</div><div class="mono dim" style="font-size:12px;margin-top:6px">reads ${p.reads} words · patience ${p.patience} steps · slips ${p.slips}%</div>`;
    el.style.left = Math.max(8, Math.min(x - r.left + 16, r.width - 270)) + "px";
    el.style.top = Math.max(8, Math.min(y - r.top + 16, r.height - 150)) + "px";
    el.hidden = false;
  }

  // ---------- the line along the bottom (Strip.qml) ----------
  let clockTimer = 0;
  function drawStrip() {
    const el = $("#strip"), L = S.live;
    clearInterval(clockTimer);
    if (L && L.running) {
      const v = lastView(L);
      el.className = "strip on";
      const paint = () => {
        const secs = Math.max(0, Math.round((Date.now() - L.began) / 1000));
        el.innerHTML = `<div><span class="lampy"></span><div class="txt"><div>${esc(L.task)}  ·  ${v.finished} of ${L.locals.length} finished</div>
          <div>${L.stopping ? "Stopping. A step that has begun is finished first." : L.who ? `${esc(nameOf(L.who))}${v.step ? ", step " + v.step : ""}:  ${esc(v.line)}${v.thought ? "   " + esc(v.thought) : ""}` : esc(v.line || "Waiting for the first local.")}</div></div>
          <span class="clock">${clock(secs)}</span>${L.stopping ? "" : `<button class="btn" data-act="stop" data-coach="stop">Stop the day</button>`}</div>`;
      };
      paint();
      clockTimer = setInterval(paint, 1000);
    } else if (S.notice) {
      const n = S.notice;
      el.className = "strip on" + (n.cmd ? " tall" : "");
      el.innerHTML = `<div><div class="txt"><div>${esc(n.head)}</div>${n.cmd ? `<pre>${esc(n.cmd)}</pre>` : `<div>${esc(n.sub)}</div>`}</div>
        ${n.days ? `<button class="btn" data-act="page" data-v="days">Kept days of this task</button>` : ""}<button class="btn" data-act="dismiss">Dismiss</button></div>`;
    } else { el.className = "strip"; el.innerHTML = ""; }
  }

  // ---------- drawing ----------
  function draw() {
    $$(".place").forEach((p) => p.classList.toggle("on", p.dataset.v === S.page));
    $$(".page").forEach((p) => p.classList.toggle("on", p.id === "p-" + S.page));
    document.documentElement.classList.toggle("nix", os === "nix");
    if (S.page === "town") drawTown();
    if (S.page === "setup") drawSetup();
    if (S.page === "days") drawDays();
    if (S.page === "rooms") drawRooms();
    if (S.page === "report") drawReport();
    if (S.page === "install") drawInstall();
    drawStrip();
    skyRun();
    tourCheck();
    requestAnimationFrame(coachPlace);
  }

  // ---------- every click ----------
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-act]");
    if (!t) return;
    const v = t.dataset.v, L = S.live;
    switch (t.dataset.act) {
      case "page": go(v); break;
      case "tour": tourStart(); break;
      case "closeday": if (L && !L.running) { S.live = null; draw(); } break;
      case "only": if (L) { L.only = v === "" || L.only === v ? "" : v; draw(); } break;
      case "steps": if (L) { L.steps = !L.steps; draw(); } break;
      case "pick": if (L) { L.sel = +v; draw(); } break;
      case "follow": if (L) { L.sel = -1; draw(); } break;
      case "enlarge": if (L) { S.viewer = shownMoment(L); draw(); } break;
      case "viewer": if (L) { S.viewer = +v; L.sel = +v; draw(); } break;
      case "closeviewer": S.viewer = -1; draw(); break;
      case "stop": stopDay(); break;
      case "openday": openDay(v); break;
      case "dismiss": S.notice = null; draw(); break;
      case "kind": S.kind = v; if (v === "apk" && (S.site.check === "url_contains" || S.site.check === "download")) S.site.check = "page_text"; draw(); break;
      case "task": S.taskRef = v; draw(); break;
      case "check": S.site.check = v; draw(); break;
      case "everyone": { const n = +v; S.counts = {}; if (n) for (const f of D.roster) for (const j of f.jobs) S.counts[j.key] = Math.min(n, j.people.length); draw(); break; }
      case "family": { const f = D.roster.find((x) => x.family === v), out = f.jobs.reduce((n, j) => n + (S.counts[j.key] || 0), 0); for (const j of f.jobs) S.counts[j.key] = out ? 0 : Math.min(1, j.people.length); draw(); break; }
      case "count": { const j = D.roster.flatMap((f) => f.jobs).find((x) => x.key === v); S.counts[v] = Math.max(0, Math.min(j.people.length, (S.counts[v] || 0) + +t.dataset.d)); draw(); break; }
      case "shift": if (!S.wholeYear) { const d = new Date(S.day + "T12:00:00"); if (!isNaN(d)) { d.setDate(d.getDate() + +v); S.day = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; draw(); } } break;
      case "pick-day": S.wholeYear = false; S.day = v; draw(); break;
      case "year": S.wholeYear = !S.wholeYear; draw(); break;
      case "pandemic": S.pandemic = v; draw(); break;
      case "take": S.take = !S.take; draw(); break;
      case "watch": S.watch = !S.watch; draw(); break;
      case "start": if (going().length && when().ok && !(L && L.running)) start(); break;
      case "room": S.roomId = v; draw(); break;
      case "clear": S.deck = S.speech = null; draw(); break;
      case "grade": S.grade = !S.grade; draw(); break;
      case "give": if (S.deck || S.speech) { const r = D.rooms.find((x) => x.id === S.roomId), py = os === "win" ? ".venv\\Scripts\\python" : ".venv/bin/python";
        const mins = ($("#rm-min") || {}).value, pt = (($("#rm-point") || {}).value || "").trim();
        S.notice = { head: "This copy cannot hear a talk. In your window the room hears it for real.", cmd: `${py} -m town ${r.rubric && S.grade ? "grade" : "room"} ${r.id} ${[S.deck, S.speech].filter(Boolean).map((f) => (/\s/.test(f) ? `"${f}"` : f)).join(" ")}${mins ? " --minutes " + mins : ""}${pt ? ` --point "${pt.replace(/"/g, "'")}"` : ""}`, days: 0 }; draw(); } break;
      case "opentalk": S.talk = D.talkViews[v]; S.talkSel = -1; S.looking = null; draw(); break;
      case "closetalk": S.talk = null; draw(); break;
      case "part": S.talkSel = +v; draw(); break;
      case "os": os = v; store.set("os", v); draw(); break;
      case "istep": openStep = openStep === +v ? -1 : +v; store.set("open", openStep); draw(); break;
      case "idone": { const i = +v, before = done.size; done.has(i) ? done.delete(i) : done.add(i); store.set("done", [...done]);
        if (done.has(i)) openStep = STEPS.findIndex((_, k) => !done.has(k)); store.set("open", openStep); draw();
        if (before < STEPS.length && done.size === STEPS.length && town3d) town3d.celebrate(); break; }
      case "copy": { const pre = t.parentNode.querySelector("pre"), text = pre.textContent;
        const ok = () => { t.textContent = "Copied"; setTimeout(() => (t.textContent = "Copy"), 1500); };
        const sel = () => { const r = document.createRange(); r.selectNodeContents(pre); const s = getSelection(); s.removeAllRanges(); s.addRange(r); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(ok, sel); else sel(); break; }
    }
  });
  document.addEventListener("input", (e) => {
    const id = e.target.id;
    if (id === "su-url") S.site.url = e.target.value;
    if (id === "su-goal") S.site.goal = e.target.value;
    if (id === "su-value") S.site.value = e.target.value;
    if (id === "su-day" && /^\d{4}-\d{2}-\d{2}$/.test(e.target.value)) { S.day = e.target.value; const f = document.activeElement; suWhen(); const d = $("#su-day"); if (f && f.id === "su-day") { d.focus(); d.setSelectionRange(d.value.length, d.value.length); } }
  });
  document.addEventListener("change", (e) => { if (e.target.id === "su-apk" && e.target.files[0]) { S.apk = { name: e.target.files[0].name, size: e.target.files[0].size }; draw(); } });
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey && /^[1-5]$/.test(e.key)) { e.preventDefault(); go(PLACES[+e.key - 1].name); }
    if (e.key === "Escape" && S.viewer >= 0) { S.viewer = -1; draw(); }
    if (S.viewer >= 0 && S.live && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
      const shots = S.live.moments.filter((m) => m.shot), k = shots.findIndex((m) => m.i === S.viewer), n = shots[k + (e.key === "ArrowRight" ? 1 : -1)];
      if (n) { S.viewer = n.i; S.live.sel = n.i; draw(); }
    }
  });
  let resizeT = 0;
  window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(() => { sky.built = ""; draw(); }, 80); });

  // ---------- the walk-through ----------
  const TOUR = [
    { page: "town", el: "skyline", text: "This is the town: a window for each of the 114 locals, a building for each family. Point at a window to meet who lives there.", next: true },
    { el: "rail-setup", text: "Choose Set up.", done: () => S.page === "setup" },
    { el: "task-pixelshift:small-jpg", text: "Choose PixelShift, small-jpg. What they are asked to do is written under the list.", done: () => S.taskRef === "pixelshift:small-jpg" },
    { el: "plus-food-stall", text: "Press + beside Food stall counter. Sunil, who cooks between two woks, goes out.", done: () => (S.counts["food-stall"] || 0) >= 1 },
    { el: "plus-junior-advocate", text: "Press + beside Junior advocate. Rohit, in a court corridor with an old phone, goes too.", done: () => (S.counts["junior-advocate"] || 0) >= 1 },
    { el: "pick-2026-09-14", text: "Choose Ganesh Chaturthi. The date changes the town: festival lights, jammed roads, a busier stall.", done: () => S.day === "2026-09-14" && !S.wholeYear },
    { el: "start", text: "Press Start the day with 2.", done: () => !!(S.live && S.live.running) },
    { el: "moment", text: "Each step: the exact screen they saw, what they did, and what they were thinking.", next: true },
    { el: "strips", text: "A strip for each local: a square per step, amber where something went wrong.", next: true },
    { el: "head", text: () => (S.live && S.live.running ? "Let the day run to its end. Stop the day is in the line along the bottom." : "1 of 2 got it done. Sunil hit BMP instead of JPG, twice, and gave up. Where a local got stuck is your feature request."), next: () => !!(S.live && !S.live.running) },
    { el: "rail-days", text: "Every day is kept. Choose Days.", done: () => S.page === "days" },
    { el: "dayrow-first", text: "Open any day to read it again, step by step, with every screen.", next: true },
    { el: "rail-rooms", text: "Locals also listen to talks. Choose Rooms.", done: () => S.page === "rooms" },
    { el: "talk-first", text: "Open a kept talk.", done: () => !!S.talk },
    { el: "grid", text: "A row for each listener, a window for each part of the talk: bright while they are hooked, dark once they are gone.", next: true },
    { el: "rail-report", text: "Choose Report.", done: () => S.page === "report" },
    { el: "report-head", text: "How the town has done on every kept day, against real people, who finish 78% of tasks.", next: true },
    { el: "rail-install", text: "That was a copy running on real data. Choose Install to get the real one.", done: () => S.page === "install" },
    { el: "istep-0", text: "Seven steps. Every one you finish lights windows in the town.", next: true },
  ];
  let tour = -1;
  const ring = document.createElement("div"), coach = document.createElement("div");
  ring.className = "ring"; coach.className = "coach";
  ring.hidden = coach.hidden = true;
  document.body.append(ring, coach);
  function tourStart() {
    clearTimeout(timer);
    S.live = null; S.talk = null; S.notice = null; S.counts = {}; S.taskRef = D.tasks[0].ref; S.day = D.labels[todayIso] ? todayIso : "2026-02-10"; S.wholeYear = false;
    tour = 0;
    go("town");
  }
  function tourEnd() { tour = -1; store.set("toured", true); coachPlace(); }
  function tourCheck() {
    let moved = false;
    while (tour >= 0 && tour < TOUR.length && TOUR[tour].done && TOUR[tour].done()) { tour++; moved = true; }
    if (tour >= TOUR.length) tourEnd();
    if (moved) requestAnimationFrame(() => { const el = target(); if (el) el.scrollIntoView({ block: "nearest" }); });
  }
  function target() {
    if (tour < 0) return null;
    const el = document.querySelector(`[data-coach="${TOUR[tour].el}"]`);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return r.width && r.height && el.closest(".page, .rail, .strip") && (!el.closest(".page") || el.closest(".page.on")) ? el : null;
  }
  function coachPlace() {
    if (tour < 0) { ring.hidden = coach.hidden = true; return; }
    const step = TOUR[tour], el = target();
    const text = typeof step.text === "function" ? step.text() : step.text;
    const canNext = typeof step.next === "function" ? step.next() : !!step.next;
    const last = tour === TOUR.length - 1;
    coach.innerHTML = `<div class="n"><span>${tour + 1} of ${TOUR.length}</span><button data-tour="skip">${last ? "Close" : "Skip the walk-through"}</button></div><p>${esc(text)}</p>${canNext ? `<div class="go"><button class="btn strong" data-tour="next">${last ? "Done" : "Next"}</button></div>` : ""}`;
    coach.hidden = false;
    if (!el) { ring.hidden = true; coach.style.left = window.innerWidth - 324 + "px"; coach.style.top = window.innerHeight - coach.offsetHeight - 24 + "px"; return; }
    const r = el.getBoundingClientRect(), pad = 4;
    ring.hidden = false;
    Object.assign(ring.style, { left: r.left - pad + "px", top: r.top - pad + "px", width: r.width + pad * 2 + "px", height: r.height + pad * 2 + "px" });
    const cw = 300, ch = coach.offsetHeight, W = window.innerWidth, H = window.innerHeight;
    let x = r.right + 16, y = r.top;
    if (x + cw > W - 12) x = r.left - cw - 16;
    if (x < 12) { x = Math.min(Math.max(12, r.left), W - cw - 12); y = r.bottom + 14; if (y + ch > H - 12) y = r.top - ch - 14; }
    y = Math.max(12, Math.min(y, H - ch - 12));
    coach.style.left = x + "px"; coach.style.top = y + "px";
  }
  coach.addEventListener("click", (e) => {
    const b = e.target.closest("[data-tour]");
    if (!b) return;
    if (b.dataset.tour === "skip") return tourEnd();
    tour++;
    if (tour >= TOUR.length) return tourEnd();
    draw();
    const el = target(); if (el) el.scrollIntoView({ block: "nearest" });
  });
  setInterval(() => { if (tour >= 0) { tourCheck(); coachPlace(); } }, 600);
  window.addEventListener("scroll", () => coachPlace(), true);

  draw();
  if (!store.get("toured", false)) tourStart();
})();
