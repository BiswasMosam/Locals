// The pixel town: flats on the left, workplaces along one street, locals walking between them.
// A lit window is a local who is awake; a lit phone in hand is a local at work in your app.
const TownView = (() => {
  const C = {
    night: '#0c0e13', slab: '#161a24', slab2: '#1d2231', stone: '#2b3244', dark: '#232938', light: '#ffc94d',
    dimLight: '#6e5c2f', ink: '#ebe7dc', line: '#262c3b', star: '#3b4255', walk: '#1a1f2b', street: '#12151c',
    skin: '#b27b55', hair: '#1d1916', legs: '#2a2f3d', feet: '#14171e', moon: '#d9d3c2',
  };
  const SHIRTS = ['#5b8def', '#e06c75', '#98c379', '#c678dd', '#d19a66', '#56b6c2', '#e5c07b', '#ebe7dc'];
  const WORKPLACE = { 'fabricator': 'fab', 'food-stall': 'stall', 'trial-advocate': 'court', 'junior-advocate': 'court',
    'firm-associate': 'firm', 'in-house-counsel': 'office' };
  const PERSON = {
    a: ['.HHH.', '.SSS.', '.SSS.', 'BBBBB', 'BBBBB', '.BBB.', '.L.L.', 'L...L', 'F...F'],
    b: ['.HHH.', '.SSS.', '.SSS.', 'BBBBB', 'BBBBB', '.BBB.', '.L.L.', '.L.L.', '.F.F.'],
  };
  const BUBBLE = ['.XXXXXXXXX.', 'XXXXXXXXXXX', 'XXXXXXXXXXX', 'XXXXXXXXXXX', 'XXXXXXXXXXX', 'XXXXXXXXXXX', '.XXXXXXXXX.', '...XX......', '...X.......'];
  // Marks inside a bubble as [row, col] pixels, with the colour each one is drawn in.
  const MARKS = {
    stuck: { color: '#c8851b', px: [[1, 5], [2, 5], [3, 5], [5, 5]] },
    wrong: { color: '#c8851b', px: [[1, 5], [2, 5], [3, 5], [5, 5]] },
    asked: { color: '#4a5068', px: [[1, 4], [1, 5], [1, 6], [2, 6], [3, 5], [5, 5]] },
    done: { color: '#3f8a3a', px: [[3, 2], [4, 3], [5, 4], [4, 5], [3, 6], [2, 7], [1, 8]] },
    says: { color: '#7a9a72', px: [[3, 2], [4, 3], [5, 4], [4, 5], [3, 6], [2, 7], [1, 8]] },
    gave: { color: '#b0493a', px: [[1, 3], [2, 4], [3, 5], [4, 6], [5, 7], [1, 7], [2, 6], [4, 4], [5, 3]] },
    stopped: { color: '#4a5068', px: [[2, 4], [2, 5], [2, 6], [3, 4], [3, 5], [3, 6], [4, 4], [4, 5], [4, 6]] },
  };
  const OUTCOME = { 'DONE': 'done', 'SAYS DONE': 'says', 'WRONG DONE': 'wrong', 'GAVE UP': 'gave', 'ASKED': 'asked',
    'STOPPED': 'stopped', 'ERROR': 'gave' };

  let cv, ctx, p = 6, oy = 0, cols = 0, rows = 120;
  let stars = [], buildings = [], lamps = [], lit = {};
  let people = new Map(), locals = new Map(), order = [], selected = null, onPick = () => {};
  const now = () => performance.now();

  function rng(seed) {
    return () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
  }

  // Unit coordinates to device pixels, rounded so neighbouring blocks never leave seams.
  function R(x, y, w, h, color) {
    const x0 = Math.round(x * p), y0 = Math.round(oy + y * p);
    ctx.fillStyle = color;
    ctx.fillRect(x0, y0, Math.round((x + w) * p) - x0, Math.round(oy + (y + h) * p) - y0);
  }
  function sprite(map, x, y, palette) {
    map.forEach((row, j) => [...row].forEach((ch, i) => { if (palette[ch]) R(x + i, y + j, 1, 1, palette[ch]); }));
  }
  function label(text, x, y, size, color, align = 'center') {
    ctx.font = `${Math.max(8, Math.round(p * size))}px Silkscreen, monospace`;
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.textBaseline = 'middle';
    ctx.fillText(text, Math.round(x * p), Math.round(oy + y * p));
  }

  function resize() {
    const dpr = window.devicePixelRatio || 1, r = cv.getBoundingClientRect();
    cv.width = Math.max(1, Math.round(r.width * dpr));
    cv.height = Math.max(1, Math.round(r.height * dpr));
    p = Math.max(2, Math.min(Math.floor(cv.height / 128), Math.floor(cv.width / 176))); // the whole street always fits
    cols = Math.ceil(cv.width / p);
    oy = cv.height - rows * p; // the street sits on the bottom edge; extra height becomes sky
    const top = -Math.floor(oy / p), rand = rng(21);
    stars = Array.from({ length: Math.round(cols * 0.3) }, () => [Math.floor(rand() * cols), top + 14 + Math.floor(rand() * (60 - top))]);
    layout();
  }

  function layout() {
    const defs = [['home', 30], ['fab', 24], ['stall', 22], ['court', 28], ['firm', 24], ['office', 24]];
    const total = defs.reduce((s, d) => s + d[1], 0);
    const gap = Math.max(3, Math.floor((cols - total) / (defs.length + 1)));
    let x = Math.max(2, Math.floor((cols - total - gap * (defs.length - 1)) / 2));
    buildings = defs.map(([key, w]) => { const b = { key, w, x, door: x + Math.floor(w / 2) }; x += w + gap; return b; });
    lamps = buildings.slice(0, -1).map((b, i) => Math.round((b.x + b.w + buildings[i + 1].x) / 2));
    const rand = rng(5);
    lit = { firm: Array.from({ length: 24 }, () => rand() < 0.3), office: Array.from({ length: 40 }, () => rand() < 0.3) };
    for (const l of locals.values()) {
      l.tx = slot(l);
      if (l.mode !== 'walk' && l.mode !== 'home') l.x = l.tx;
      if (l.mode === 'home') l.x = building('home').door;
    }
  }

  const building = key => buildings.find(b => b.key === key) || buildings[buildings.length - 1];

  function slot(l) {
    const same = order.filter(id => locals.get(id)?.place === l.place);
    const k = same.indexOf(l.id), b = building(l.place);
    return Math.round(b.door - (same.length - 1) * 3.5 + k * 7);
  }

  // ---------- Drawing ----------

  function drawSky(t) {
    R(0, -Math.ceil(oy / p), cols, rows + Math.ceil(oy / p), C.night);
    for (const [x, y] of stars) R(x, y, 1, 1, C.star);
    sprite(['..XXXX..', '.XXXXXX.', 'XXXXXXXX', 'XXXXXXXX', 'XXXXXXXX', 'XXXXXXXX', '.XXXXXX.', '..XXXX..'],
      Math.round(cols * 0.6), Math.max(-Math.floor(oy / p) + 8, 4), { X: C.moon });
  }

  function sign(x, y, w, text) {
    R(x, y, w, 5, C.slab2);
    label(text, x + w / 2, y + 2.6, 2.1, C.ink);
  }

  function drawBuildings() {
    for (const b of buildings) {
      const { x, w } = b;
      if (b.key === 'home') {
        R(x - 1, 26, w + 2, 2, C.slab2); R(x + 18, 22, 6, 4, C.slab2); R(x, 28, w, 62, C.slab);
        // Eighteen windows, one per local: lit while they are home and awake, dim once they have gone out.
        for (let i = 0; i < 18; i++) {
          const col = i % 3, row = Math.floor(i / 3);
          const who = [...locals.values()].find(l => l.info.number === i + 1);
          const color = !who ? C.dark : who.mode === 'home' ? C.light : C.dimLight;
          R(x + 3 + col * 9, 32 + row * 8, 6, 4, color);
        }
        R(b.door - 3, 82, 6, 8, C.slab2);
      } else if (b.key === 'fab') {
        R(x, 60, w, 30, C.slab); sign(x + 1, 62, w - 2, 'FABRICATION');
        R(x + 3, 70, w - 6, 20, C.dimLight);
        for (let i = 0; i < 5; i++) R(x + 3, 70 + i * 2, w - 6, 1, i % 2 ? C.line : C.slab2);
      } else if (b.key === 'stall') {
        R(x, 64, w, 26, C.slab); sign(x + 1, 66, w - 2, 'CHINESE');
        for (let i = 0; i < 11; i++) R(x + i * 2, 72, 2, 4, i % 2 ? C.dark : C.ink);
        R(x + 3, 77, w - 6, 7, C.dimLight); R(x + 2, 84, w - 4, 6, C.slab2);
      } else if (b.key === 'court') {
        [[12, 4], [9, 10], [6, 16], [3, 22], [0, 28]].forEach(([dx, sw], i) => R(x + dx, 46 + i, sw, 1, C.slab2));
        R(x, 51, w, 39, C.slab); sign(x + 2, 53, w - 4, 'COURT');
        for (let i = 0; i < 5; i++) R(x + 3 + i * 5, 60, 2, 28, C.stone);
        R(x - 1, 88, w + 2, 2, C.slab2);
      } else {
        const tall = b.key === 'office', top = tall ? 20 : 34, rowsN = tall ? 9 : 6;
        R(x, top, w, 90 - top, C.slab);
        for (let r = 0; r < rowsN; r++) for (let c = 0; c < 4; c++) {
          R(x + 3 + c * 5, top + 4 + r * 5, 3, 3, lit[b.key][r * 4 + c] ? C.light : C.dark);
        }
        sign(x + 1, tall ? 70 : 68, w - 2, tall ? 'OFFICE' : 'LAW FIRM');
        R(b.door - 3, 80, 6, 10, C.dimLight);
      }
    }
  }

  function drawStreet() {
    R(0, 90, cols, 10, C.walk); R(0, 100, cols, 1, C.line); R(0, 101, cols, 40, C.street);
    for (let x = 2; x < cols; x += 12) R(x, 110, 6, 1, C.stone);
    for (const x of lamps) { R(x, 74, 1, 16, C.star); R(x - 1, 72, 3, 2, C.light); }
  }

  function drawLocal(l, t) {
    if (l.mode === 'home') return;
    const shake = t < l.shake ? (Math.floor(t / 60) % 2 ? 1 : -1) : 0;
    const x = Math.round(l.x) - 2 + shake, frame = l.mode === 'walk' && Math.floor(t / 250) % 2 ? PERSON.a : PERSON.b;
    sprite(frame, x, 89, { H: C.hair, S: C.skin, B: SHIRTS[l.info.number % SHIRTS.length], L: C.legs, F: C.feet });
    if (l.active && l.mode !== 'walk') R(x + 4, 93, 1, 2, C.light); // the phone in hand, lit while they work
    label(String(l.info.number).padStart(2, '0'), x + 7.5, 90, 1.7, l.active ? C.light : '#8a8f9c', 'left');

    let mark = l.badge;
    if (!mark && l.bubble === 'stuck' && t < l.until) mark = 'stuck';
    if (mark || (l.active && l.mode !== 'walk')) {
      const bx = x - 3, by = 79;
      sprite(BUBBLE, bx, by, { X: C.ink });
      if (mark) {
        if (mark !== 'stuck' || Math.floor(t / 500) % 3) for (const [r, c] of MARKS[mark].px) R(bx + c, by + r, 1, 1, MARKS[mark].color);
      } else {
        const dots = Math.floor(t / 350) % 4;
        for (let i = 0; i < dots; i++) R(bx + 2 + i * 3, by + 3, 1, 1, '#3b4255');
      }
    }
    if (selected === l.id) { R(x + 1, 75, 3, 1, C.light); R(x + 2, 76, 1, 1, C.light); }
  }

  function update(dt, t) {
    for (const l of locals.values()) {
      if (l.mode === 'home' && t >= l.leaveAt) l.mode = 'walk';
      if (l.mode === 'walk') {
        const d = l.tx - l.x, step = 14 * dt;
        if (Math.abs(d) <= step) { l.x = l.tx; l.mode = 'wait'; } else l.x += Math.sign(d) * step;
      }
    }
  }

  let last = now();
  function frame() {
    const t = now(), dt = Math.min(0.1, (t - last) / 1000);
    last = t;
    update(dt, t);
    ctx.imageSmoothingEnabled = false;
    drawSky(t); drawBuildings(); drawStreet();
    [...locals.values()].sort((a, b) => a.x - b.x).forEach(l => drawLocal(l, t));
    requestAnimationFrame(frame);
  }

  // ---------- What the dashboard calls ----------

  function init(canvas, options) {
    cv = canvas; ctx = cv.getContext('2d');
    people = options.people; onPick = options.onPick || onPick;
    new ResizeObserver(resize).observe(cv);
    cv.addEventListener('click', e => {
      const r = cv.getBoundingClientRect(), dpr = cv.width / r.width;
      const ux = (e.clientX - r.left) * dpr / p, uy = ((e.clientY - r.top) * dpr - oy) / p;
      const hit = [...locals.values()].find(l => l.mode !== 'home' && ux >= l.x - 4 && ux <= l.x + 7 && uy >= 78 && uy <= 99);
      onPick(hit ? hit.id : null);
    });
    cv.addEventListener('mousemove', e => {
      const r = cv.getBoundingClientRect(), dpr = cv.width / r.width;
      const ux = (e.clientX - r.left) * dpr / p, uy = ((e.clientY - r.top) * dpr - oy) / p;
      cv.style.cursor = [...locals.values()].some(l => l.mode !== 'home' && ux >= l.x - 4 && ux <= l.x + 7 && uy >= 78 && uy <= 99) ? 'pointer' : 'default';
    });
    document.fonts.load('12px Silkscreen');
    resize();
    requestAnimationFrame(frame);
  }

  function startDay(ids, settled = false) {
    locals.clear();
    order = ids.filter(id => people.has(id));
    const t = now(), home = building('home').door;
    order.forEach((id, i) => {
      const info = people.get(id);
      locals.set(id, { id, info, place: WORKPLACE[info.group] || 'office', x: home, tx: home, mode: settled ? 'wait' : 'home',
        leaveAt: t + 400 + i * 700, active: false, bubble: null, until: 0, badge: null, shake: 0 });
    });
    for (const l of locals.values()) { l.tx = slot(l); if (settled) l.x = l.tx; }
  }

  function event(e) {
    const l = locals.get(e.local);
    if (!l) return;
    const t = now();
    if (e.kind === 'START') { l.active = true; if (l.mode === 'home') l.leaveAt = t; }
    else if (e.kind === 'STUCK') { l.bubble = 'stuck'; l.until = t + 4000; }
    else if (e.kind === 'SLIP') l.shake = t + 500;
    else if (OUTCOME[e.kind]) { l.badge = OUTCOME[e.kind]; l.active = false; }
  }

  function step(e) {
    const l = locals.get(e.local);
    if (l) l.active = true;
  }

  function select(id) { selected = id; }

  return { init, startDay, event, step, select };
})();
