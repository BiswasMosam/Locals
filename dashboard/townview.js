// The pixel city: a skyline behind, one long street in front, locals walking between home and work.
// A lit window is a local who is awake; a lit phone in hand is a local at work in your app.
const TownView = (() => {
  const C = {
    night: '#0c0e13', slab: '#161a24', slab2: '#1d2231', stone: '#2b3244', dark: '#232938', light: '#ffc94d',
    dimLight: '#6e5c2f', ink: '#ebe7dc', line: '#262c3b', star: '#3b4255', walk: '#1a1f2b', street: '#12151c',
    skin: '#b27b55', hair: '#1d1916', legs: '#2a2f3d', feet: '#14171e', moon: '#d9d3c2',
    far: '#10131b', farWin: '#3a3221', mid: '#13171f', midWin: '#54462a', midDark: '#191d28',
    glass: '#1c2634', tree: '#1d3124', tree2: '#25402e', trunk: '#2a2218', red: '#c04b3c', green: '#4f9a5c', yellow: '#e5c07b',
  };
  const SHIRTS = ['#5b8def', '#e06c75', '#98c379', '#c678dd', '#d19a66', '#56b6c2', '#e5c07b', '#ebe7dc'];
  const PARTY = ['#ffc94d', '#8fcf7a', '#5b8def', '#e06c75', '#c678dd', '#ebe7dc', '#56b6c2'];
  const WORKPLACE = { 'fabricator': 'fab', 'food-stall': 'stall', 'trial-advocate': 'court', 'junior-advocate': 'court',
    'firm-associate': 'firm', 'in-house-counsel': 'office', 'wedding-photographer': 'hall', 'videographer': 'hall',
    'product-photographer': 'studio', 'video-editor': 'studio', 'social-media-manager': 'itpark',
    'software-product': 'itpark', 'software-services': 'office', 'plant-maintenance': 'factory', 'mechanical-design': 'factory',
    'site-engineer': 'site', 'structural-planning': 'office', 'electrical-maintenance': 'factory', 'embedded-engineer': 'itpark',
    'ca-practice': 'ca', 'article-assistant': 'ca', 'accounts-executive': 'office', 'bank-branch': 'bank', 'insurance-agent': 'chai',
    'clinic-doctor': 'clinic', 'resident-doctor': 'hospital', 'staff-nurse': 'hospital', 'pharmacist': 'medical', 'asha-worker': 'home2', // ASHAs work at people's doors
    'govt-school-teacher': 'school', 'private-school-teacher': 'school', 'college-lecturer': 'college', 'coaching-teacher': 'classes',
    'founder-ceo': 'itpark', 'company-ceo': 'office', 'investor': 'office', 'hr-recruiter': 'office', 'hiring-manager': 'itpark',
    'engineering-student': 'college', 'commerce-student': 'college' };
  // The street from left to right: flats at both ends, every family's workplace in between.
  const STREET = [['home', 30], ['chai', 14], ['fab', 24], ['stall', 22], ['medical', 16], ['clinic', 18], ['court', 28], ['firm', 24],
    ['ca', 20], ['bank', 26], ['office', 24], ['itpark', 28], ['studio', 20], ['hall', 30], ['hospital', 26], ['school', 24], ['classes', 18],
    ['college', 30], ['factory', 28], ['site', 28], ['home2', 26], ['home3', 32], ['home4', 36], ['home5', 30]];
  // Locals 1 to 18 live in the first block of flats, 19 to 33 in the second, 34 to 57 in the third, 58 to 99 in the tower,
  // 100 to 117 in the newest block at the end of the street; one window each.
  const homeOf = number => (number <= 18 ? 'home' : number <= 33 ? 'home2' : number <= 57 ? 'home3' : number <= 99 ? 'home4' : 'home5');
  const TREES_AFTER = new Set(['chai', 'clinic', 'studio', 'school', 'college']);

  const PERSON = {
    a: ['.HHH.', '.SSS.', '.SSS.', 'BBBBB', 'BBBBB', '.BBB.', '.L.L.', 'L...L', 'F...F'],
    b: ['.HHH.', '.SSS.', '.SSS.', 'BBBBB', 'BBBBB', '.BBB.', '.L.L.', '.L.L.', '.F.F.'],
  };
  const VEHICLES = {
    auto: { speed: 11, rows: ['..YYYYYY.', '.YW.....Y', '.YW.....Y', 'YGGGGGGGG', 'GGGGGGGGH', '.O....O..'] },
    car: { speed: 15, rows: ['...BBBBB....', '..BWWBWWB...', 'BBBBBBBBBBBH', 'RBBBBBBBBBBB', '..O.....O...'] },
    bus: { speed: 8, rows: ['RRRRRRRRRRRRRRRRRRRRRR', 'RWWRWWRWWRWWRWWRWWRWWR', 'RWWRWWRWWRWWRWWRWWRWWR', 'RRRRRRRRRRRRRRRRRRRRRR',
      'RRRRRRRRRRRRRRRRRRRRRH', '..OO..........OO......'] },
  };
  const BUBBLE = ['.XXXXXXXXX.', 'XXXXXXXXXXX', 'XXXXXXXXXXX', 'XXXXXXXXXXX', 'XXXXXXXXXXX', 'XXXXXXXXXXX', '.XXXXXXXXX.', '...XX......', '...X.......'];
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

  let cv, ctx, p = 5, oy = 0, rows = 120, view = 0, width = 0, ox = 0;
  let cam = 0, camTarget = 0, manualUntil = 0, drag = null;
  let stars = [], far = [], mid = [], buildings = [], lamps = [], trees = [], cars = [], lit = {};
  let people = new Map(), locals = new Map(), order = [], selected = null, onPick = () => {};
  let confetti = [], sparks = [], rockets = [], partyUntil = 0, nextRocket = 0;
  let scene = null; // the day: rain, festival lights, a pandemic
  const STRINGS = {
    diwali: ['#ffc94d', '#ff9f43', '#ffe08a'], ganesh: ['#ff7a45', '#ffc94d', '#e85d5d'],
    navratri: ['#e06c75', '#98c379', '#5b8def', '#c678dd', '#ffc94d'], christmas: ['#e06c75', '#98c379', '#ebe7dc'],
    ramzan: ['#98c379', '#ebe7dc', '#ffc94d'], holi: ['#e06c75', '#c678dd', '#5b8def', '#98c379', '#ffc94d'],
  };
  const SHUT = new Set(['chai', 'fab', 'stall', 'classes']); // shops that close in a lockdown; the medical store and the bank stay open
  const now = () => performance.now();
  const calm = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function rng(seed) {
    return () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
  }

  // World units to device pixels for the current layer, rounded so neighbouring blocks never leave seams.
  function R(x, y, w, h, color) {
    const x0 = Math.round((x - ox) * p), x1 = Math.round((x + w - ox) * p);
    if (x1 < 0 || x0 > cv.width) return;
    const y0 = Math.round(oy + y * p);
    ctx.fillStyle = color;
    ctx.fillRect(x0, y0, x1 - x0, Math.round(oy + (y + h) * p) - y0);
  }
  function sprite(map, x, y, palette, flip = false) {
    map.forEach((row, j) => {
      const line = flip ? [...row].reverse() : [...row];
      line.forEach((ch, i) => { if (palette[ch]) R(x + i, y + j, 1, 1, palette[ch]); });
    });
  }
  function label(text, x, y, size, color, align = 'center') {
    ctx.font = `${Math.max(8, Math.round(p * size))}px Silkscreen, monospace`;
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.textBaseline = 'middle';
    ctx.fillText(text, Math.round((x - ox) * p), Math.round(oy + y * p));
  }

  // ---------- Building the city ----------

  function build() {
    let x = 4;
    buildings = [];
    trees = [];
    lamps = [];
    for (const [key, w] of STREET) {
      buildings.push({ key, w, x, door: x + Math.floor(w / 2) });
      x += w;
      if (TREES_AFTER.has(key)) { trees.push(x + 3); x += 7; } else { lamps.push(x + 2); x += 4; }
    }
    width = x;
    const rand = rng(11);
    const towers = (factor, minW, maxW, minH, maxH) => {
      const out = [];
      for (let tx = -10; tx < width * factor + 900;) {
        const w = minW + Math.floor(rand() * (maxW - minW)), h = minH + Math.floor(rand() * (maxH - minH));
        const wins = [];
        for (let wy = 90 - h + 3; wy < 88; wy += 3) for (let wx = 2; wx < w - 1; wx += 3) wins.push([wx, wy, rand()]);
        out.push({ x: tx, w, h, wins });
        tx += w + Math.floor(rand() * 3);
      }
      return out;
    };
    far = towers(0.35, 8, 18, 40, 115);
    mid = towers(0.65, 12, 24, 30, 75);
    lit = {};
    for (const key of ['firm', 'office', 'itpark', 'hospital', 'ca', 'bank', 'college']) lit[key] = Array.from({ length: 60 }, () => rand());
    cars = [['auto', 30, 1], ['car', 120, -1], ['bus', 200, 1], ['auto', 260, -1], ['car', 340, 1]]
      .map(([kind, cx, dir]) => ({ kind, x: cx, dir }));
  }

  function resize() {
    const dpr = window.devicePixelRatio || 1, r = cv.getBoundingClientRect();
    cv.width = Math.max(1, Math.round(r.width * dpr));
    cv.height = Math.max(1, Math.round(r.height * dpr));
    p = Math.max(3, Math.min(Math.floor(cv.height / 128), Math.floor(cv.width / 230)));
    view = cv.width / p;
    oy = cv.height - rows * p; // the street sits on the bottom edge; extra height becomes sky
    const top = -Math.ceil(oy / p), rand = rng(21);
    stars = Array.from({ length: Math.round(view * 0.5) }, () => [rand() * view, top + 4 + Math.floor(rand() * (70 - top))]);
    cam = camTarget = clampCam(cam);
    for (const l of locals.values()) {
      l.tx = slot(l);
      if (l.mode === 'home') l.x = building(homeOf(l.info.number)).door;
      else if (l.mode !== 'walk') l.x = l.tx;
    }
  }

  const clampCam = c => width <= view ? (width - view) / 2 : Math.max(0, Math.min(width - view, c));
  const building = key => buildings.find(b => b.key === key) || buildings.find(b => b.key === 'office');

  function slot(l) {
    const same = order.filter(id => locals.get(id)?.place === l.place);
    const k = same.indexOf(l.id), b = building(l.place);
    return Math.round(b.door - (same.length - 1) * 5 + k * 10); // room for each number tag
  }

  // ---------- Drawing ----------

  function drawSky() {
    ox = 0;
    R(0, -Math.ceil(oy / p), view + 1, rows + Math.ceil(oy / p), C.night);
    for (const [x, y] of stars) R(Math.floor(x), y, 1, 1, C.star);
    const moon = scene?.lights === 'ramzan'
      ? ['..XXX...', '.XXX....', 'XXX.....', 'XXX.....', 'XXX.....', 'XXX.....', '.XXX....', '..XXX...'] // a crescent in Ramzan
      : ['..XXXX..', '.XXXXXX.', 'XXXXXXXX', 'XXXXXXXX', 'XXXXXXXX', 'XXXXXXXX', '.XXXXXX.', '..XXXX..'];
    sprite(moon, Math.round(view * 0.72), 8 - Math.floor(oy / p), { X: C.moon });
  }

  function drawSkyline(list, factor, body, win, dark, size) {
    ox = cam * factor;
    for (const t of list) {
      if ((t.x + t.w - ox) * p < 0 || (t.x - ox) * p > cv.width) continue;
      R(t.x, 90 - t.h, t.w, t.h, body);
      for (const [wx, wy, chance] of t.wins) if (chance < 0.22) R(t.x + wx, wy, size, size, chance < 0.12 ? win : dark);
    }
  }

  function sign(x, y, w, text, size = 2.1) {
    R(x, y, w, 5, C.slab2);
    label(text, x + w / 2, y + 2.6, size, C.ink);
  }

  function grid(b, top, colsN, rowsN, cell, gapX, gapY, key, chance, color = C.light, off = C.dark) {
    const startX = b.x + Math.floor((b.w - (colsN * cell + (colsN - 1) * gapX)) / 2);
    for (let r = 0; r < rowsN; r++) for (let c = 0; c < colsN; c++) {
      const on = lit[key] ? lit[key][(r * colsN + c) % 60] < chance : false;
      R(startX + c * (cell + gapX), top + r * (cell + gapY), cell, cell, on ? color : off);
    }
  }

  // A local's window: lit while they are home and awake, dim once they have gone out, dark if they are not in town today.
  function windowLight(number) {
    const who = [...locals.values()].find(l => l.info.number === number);
    return !who ? C.dark : who.mode === 'home' ? C.light : C.dimLight;
  }

  function drawBuilding(b, t) {
    const { x, w, door } = b;
    switch (b.key) {
      case 'home': {
        R(x - 1, 26, w + 2, 2, C.slab2); R(x + 18, 22, 6, 4, C.slab2); R(x, 28, w, 62, C.slab);
        for (let i = 0; i < 18; i++) R(x + 3 + (i % 3) * 9, 32 + Math.floor(i / 3) * 8, 6, 4, windowLight(i + 1));
        R(door - 3, 82, 6, 8, C.slab2);
        break;
      }
      case 'home2':
        R(x, 40, w, 50, C.slab); R(x - 1, 38, w + 2, 2, C.slab2);
        for (let i = 0; i < 15; i++) R(x + 3 + (i % 3) * 8, 44 + Math.floor(i / 3) * 8, 4, 4, windowLight(19 + i));
        for (let r = 0; r < 5; r++) R(x + 1, 49 + r * 8, w - 2, 1, C.line);
        R(door - 3, 82, 6, 8, C.slab2);
        break;
      case 'home3':
        R(x - 1, 28, w + 2, 2, C.slab2); R(x + 3, 24, 5, 4, C.slab2); R(x, 30, w, 60, C.slab);
        for (let i = 0; i < 24; i++) R(x + 3 + (i % 4) * 7, 34 + Math.floor(i / 4) * 7, 5, 4, windowLight(34 + i));
        R(door - 3, 82, 6, 8, C.slab2);
        break;
      case 'home4':
        // The tower: forty two windows for the finance, health and education families.
        R(x - 1, 22, w + 2, 2, C.slab2); R(x + w - 10, 17, 6, 5, C.slab2); R(x, 24, w, 66, C.slab);
        for (let i = 0; i < 42; i++) R(x + 4 + (i % 6) * 5, 28 + Math.floor(i / 6) * 7, 3, 4, windowLight(58 + i));
        for (let r = 1; r < 7; r++) R(x + 1, 26 + r * 7, w - 2, 1, C.line);
        R(door - 3, 80, 6, 10, C.slab2);
        break;
      case 'home5':
        // The newest block: eighteen windows for the business and student families, balconies on every floor.
        R(x, 34, w, 56, C.slab); R(x - 1, 32, w + 2, 2, C.slab2);
        for (let i = 0; i < 18; i++) R(x + 3 + (i % 3) * 9, 38 + Math.floor(i / 3) * 7, 6, 4, windowLight(100 + i));
        for (let r = 0; r < 6; r++) R(x, 43 + r * 7, w, 1, C.line);
        R(door - 3, 82, 6, 8, C.slab2);
        break;
      case 'clinic':
        R(x, 62, w, 28, C.slab); R(x - 1, 60, w + 2, 2, C.slab2);
        sign(x + 1, 64, w - 2, 'CLINIC', 1.9);
        R(x + 2, 71, 6, 8, C.ink); for (let i = 0; i < 3; i++) R(x + 3, 72 + i * 2, 4, 1, C.stone); // morning and evening timings
        R(x + 11, 71, w - 13, 9, C.dimLight);
        R(door - 2, 82, 4, 8, C.slab2);
        break;
      case 'ca':
        R(x, 30, w, 60, C.slab); R(x - 1, 28, w + 2, 2, C.slab2);
        grid(b, 34, 3, 6, 3, 2, 3, 'ca', 0.45); // lights on late before a due date
        sign(x + 1, 70, w - 2, 'CA', 2.1); R(door - 3, 80, 6, 10, C.dimLight);
        break;
      case 'bank':
        R(x, 50, w, 40, C.slab); R(x - 1, 48, w + 2, 2, C.slab2);
        sign(x + 2, 53, w - 4, 'BANK'); grid(b, 61, 4, 2, 3, 2, 2, 'bank', 0.5);
        R(x + 2, 72, w - 12, 18, C.glass);
        for (let i = 1; i < 3; i++) R(x + 2 + i * Math.floor((w - 12) / 3), 72, 1, 18, C.line);
        R(x + w - 9, 70, 7, 20, C.slab2); label('ATM', x + w - 5.5, 72.6, 1.3, C.light); // the ATM booth, lit all night
        R(x + w - 7, 76, 3, 3, C.light); R(x + w - 7, 80, 3, 1, C.dimLight);
        break;
      case 'classes':
        R(x, 52, w, 38, C.slab);
        sign(x + 1, 54, w - 2, 'CLASSES', 1.8);
        R(x + 2, 61, w - 4, 9, C.dimLight); R(x + 4, 62, w - 8, 6, '#2f4a3a'); // the evening batch, a board through the window
        R(x + 5, 63, 4, 1, C.ink); R(x + 5, 65, 7, 1, C.ink);
        R(x + 2, 72, w - 4, 4, C.yellow); label('JEE NEET', x + w / 2, 74.1, 1.2, C.night);
        R(door - 3, 80, 6, 10, C.slab2);
        break;
      case 'college': {
        R(door - 4, 30, 8, 20, C.slab2); R(door - 5, 28, 10, 2, C.stone); R(door - 2, 25, 4, 3, C.stone);
        sprite(['.XXX.', 'X.X.X', 'X.XXX', 'X...X', '.XXX.'], door - 2, 34, { X: C.moon }); // the clock tower
        R(x, 50, w, 40, C.slab); R(x - 1, 48, w + 2, 2, C.slab2);
        sign(x + 2, 52, w - 4, 'COLLEGE');
        for (let r = 0; r < 2; r++) for (let i = 0; i < 5; i++) {
          const on = lit.college[r * 5 + i] < 0.4 ? C.light : C.dark;
          R(x + 3 + i * 5, 61 + r * 9, 3, 6, on); R(x + 4 + i * 5, 60 + r * 9, 1, 1, on); // arched windows
        }
        R(door - 3, 80, 6, 10, C.dimLight);
        break;
      }
      case 'hall': {
        R(x, 58, w, 32, C.slab); R(x - 1, 56, w + 2, 2, C.slab2);
        const shift = calm() ? 0 : Math.floor(t / 500);
        for (let i = 0; i < w; i += 2) R(x + i, 55, 1, 1, ['#ff9fb2', C.light, '#ff9f43'][(i / 2 + shift) % 3]); // always a wedding somewhere
        sign(x + 2, 60, w - 4, 'BANQUET');
        for (let i = 0; i < 3; i++) { R(x + 3 + i * 9, 69, 6, 9, C.dimLight); R(x + 4 + i * 9, 68, 4, 1, C.dimLight); }
        R(door - 4, 80, 8, 10, C.dimLight);
        for (let i = 0; i < 8; i++) R(door - 4 + i, 79 + (i % 2), 1, 1, i % 2 ? '#ff9f43' : C.yellow); // marigold garland
        break;
      }
      case 'chai':
        R(x, 70, w, 20, C.slab); sign(x + 1, 71, w - 2, 'CHAI', 1.9);
        for (let i = 0; i < 7; i++) R(x + i * 2, 77, 2, 3, i % 2 ? C.dark : C.yellow);
        R(x + 2, 81, w - 4, 5, C.dimLight); R(x + 1, 86, w - 2, 4, C.slab2);
        if (!calm()) for (let i = 0; i < 3; i++) { const k = (t / 700 + i / 3) % 1; R(x + 5 + Math.round(Math.sin(k * 6 + i) * 1), 79 - Math.round(k * 8), 1, 1, C.star); }
        break;
      case 'fab':
        R(x, 60, w, 30, C.slab); sign(x + 1, 62, w - 2, 'FABRICATION');
        R(x + 3, 70, w - 6, 20, C.dimLight);
        for (let i = 0; i < 5; i++) R(x + 3, 70 + i * 2, w - 6, 1, i % 2 ? C.line : C.slab2);
        break;
      case 'stall':
        R(x, 64, w, 26, C.slab); sign(x + 1, 66, w - 2, 'CHINESE');
        for (let i = 0; i < 11; i++) R(x + i * 2, 72, 2, 4, i % 2 ? C.dark : C.ink);
        R(x + 3, 77, w - 6, 7, C.dimLight); R(x + 2, 84, w - 4, 6, C.slab2);
        break;
      case 'medical':
        R(x, 64, w, 26, C.slab);
        R(door - 1, 56, 3, 7, C.green); R(door - 3, 58, 7, 3, C.green);
        sign(x + 1, 66, w - 2, 'MEDICAL', 1.8);
        R(x + 2, 73, w - 4, 11, C.dimLight); R(x + 2, 84, w - 4, 6, C.slab2);
        break;
      case 'court':
        [[12, 4], [9, 10], [6, 16], [3, 22], [0, 28]].forEach(([dx, sw], i) => R(x + dx, 46 + i, sw, 1, C.slab2));
        R(x, 51, w, 39, C.slab); sign(x + 2, 53, w - 4, 'COURT');
        for (let i = 0; i < 5; i++) R(x + 3 + i * 5, 60, 2, 28, C.stone);
        R(x - 1, 88, w + 2, 2, C.slab2);
        break;
      case 'firm':
        R(x, 34, w, 56, C.slab); grid(b, 38, 4, 6, 3, 2, 2, 'firm', 0.3);
        sign(x + 1, 68, w - 2, 'LAW FIRM'); R(door - 3, 80, 6, 10, C.dimLight);
        break;
      case 'office':
        R(x, 20, w, 70, C.slab); grid(b, 24, 4, 9, 3, 2, 2, 'office', 0.3);
        sign(x + 1, 70, w - 2, 'OFFICE'); R(door - 3, 80, 6, 10, C.dimLight);
        break;
      case 'itpark':
        R(x + 4, 8, w - 8, 3, C.slab2); R(x, 11, w, 79, C.glass);
        grid(b, 14, 5, 11, 3, 2, 2, 'itpark', 0.38, C.light, '#243143');
        sign(x + 2, 70, w - 4, 'IT PARK'); R(door - 4, 80, 8, 10, C.dimLight);
        break;
      case 'studio':
        R(x, 56, w, 34, C.slab);
        sprite(['..XX....', 'XXXXXXX.', 'XX..XXXX', 'XX..XXXX', 'XXXXXXX.'], door - 4, 49, { X: C.stone });
        if (Math.floor(t / 900) % 2 || calm()) R(x + w - 4, 58, 2, 2, C.red);
        sign(x + 1, 62, w - 2, 'STUDIO'); R(x + 3, 70, w - 6, 12, C.dimLight); R(door - 2, 84, 4, 6, C.slab2);
        break;
      case 'hospital':
        R(x, 30, w, 60, C.slab2);
        R(door - 1, 32, 3, 8, C.red); R(door - 4, 35, 9, 2, C.red);
        grid(b, 44, 4, 4, 3, 3, 2, 'hospital', 0.6, C.moon);
        sign(x + 1, 66, w - 2, 'HOSPITAL', 1.9); R(x + 3, 74, w - 6, 2, C.stone); R(door - 4, 77, 8, 13, C.dimLight);
        break;
      case 'school':
        [[9, 6], [6, 12], [3, 18], [0, 24]].forEach(([dx, sw], i) => R(x + dx, 50 + i * 1, sw, 1, C.slab2));
        R(x, 54, w, 36, C.slab);
        sprite(['.XXX.', 'XX.XX', 'X.X.X', 'XX.XX', '.XXX.'], door - 2, 56, { X: C.moon });
        sign(x + 1, 63, w - 2, 'SCHOOL'); grid(b, 71, 4, 2, 3, 2, 3, 'none', 0, C.light, C.dark);
        R(door - 2, 82, 4, 8, C.slab2);
        break;
      case 'factory':
        R(x + 20, 34, 3, 24, C.stone);
        if (!calm()) for (let i = 0; i < 4; i++) { const k = (t / 1600 + i / 4) % 1; R(x + 21 + Math.round(k * 4), 33 - Math.round(k * 14), 2, 2, k < 0.5 ? '#3b4255' : '#2b3244'); }
        for (let i = 0; i < 4; i++) for (let s = 0; s < 5; s++) R(x + i * 7 + s, 58 - s, 7 - s, 1, C.slab2);
        R(x, 58, w, 32, C.slab); sign(x + 2, 62, w - 4, 'FACTORY'); R(x + 4, 72, w - 8, 18, C.slab2);
        for (let i = 0; i < 6; i++) R(x + 4, 72 + i * 3, w - 8, 1, C.line);
        break;
      case 'site': {
        for (let f = 0; f < 5; f++) R(x + 2, 46 + f * 9, 18, 1, C.stone);
        for (let c = 0; c < 4; c++) R(x + 2 + c * 6, 46, 1, 44, C.stone);
        for (let s = 0; s < 8; s++) R(x + 2 + ((s * 5) % 18), 47 + s * 5, 1, 1, C.dimLight);
        R(x + 22, 8, 1, 82, C.yellow); R(x, 8, w + 2, 1, C.yellow); R(x + 23, 9, 4, 2, C.stone);
        R(x + 8, 9, 1, 18, C.line); R(x + 7, 27, 3, 2, C.yellow);
        if (Math.floor(t / 700) % 2 || calm()) R(x + 22, 6, 1, 1, C.red);
        sign(x + 2, 82, 16, 'SITE', 1.9);
        break;
      }
    }
  }

  // ---------- The day: festival lights, lanterns, colour, rain ----------

  function drawFestival(t) {
    const colors = STRINGS[scene?.lights];
    if (!colors) return;
    const shift = calm() ? 0 : Math.floor(t / 600);
    // A string of lights sagging between each pair of lamp posts.
    const posts = [buildings[0].x - 2, ...lamps];
    for (let i = 0; i < posts.length - 1; i++) {
      const a = posts[i], b = posts[i + 1];
      for (let x = a + 1, k = 0; x < b; x += 3, k++) {
        const f = (x - a) / (b - a);
        R(x, 72 + Math.round(Math.sin(f * Math.PI) * 3), 1, 1, colors[(k + shift) % colors.length]);
      }
    }
    if (scene.lights === 'diwali') {
      // Akash kandils hanging from the flats.
      for (const b of buildings.filter(b => b.key.startsWith('home'))) {
        for (const dx of [2, b.w - 5]) {
          R(b.x + dx + 1, 28, 1, 3, C.line);
          sprite(['.X.', 'XXX', 'XYX', 'XXX', '.X.'], b.x + dx, 31, { X: '#ff9f43', Y: C.light });
        }
      }
    }
    if (scene.lights === 'christmas') {
      const o = buildings.find(b => b.key === 'office');
      sprite(['..X..', '.XXX.', 'XXXXX', '.XXX.', '.X.X.'], o.door - 2, 14, { X: C.light });
    }
    if (scene.lights === 'holi') {
      const rand = rng(3);
      for (let i = 0; i < Math.round(width / 3); i++) R(Math.floor(rand() * width), 91 + Math.floor(rand() * 9), 1, 1, colors[i % colors.length]);
    }
  }

  function drawRain(t) {
    if (!scene?.rain || calm()) return;
    const heavy = scene.rain === 'heavy', drops = heavy ? 320 : 140, fall = cv.height * (heavy ? 1.6 : 1.1);
    ctx.fillStyle = heavy ? '#6a7488' : '#4c5568';
    ctx.globalAlpha = heavy ? 0.7 : 0.5;
    const w = Math.max(1, Math.round(p / 3)), h = p * (heavy ? 3 : 2);
    for (let i = 0; i < drops; i++) {
      const y = ((t / 1000) * fall + i * 137.7) % (cv.height + 40) - 20;
      const x = (((i * 0.6180339) % 1) * (cv.width + 60) - y * 0.12) % (cv.width + 60);
      ctx.fillRect(Math.round(x), Math.round(y), w, h);
    }
    ctx.globalAlpha = 1;
  }

  function drawStreet(t) {
    ox = cam;
    R(cam - 1, 90, view + 2, 10, C.walk); R(cam - 1, 100, view + 2, 1, C.line); R(cam - 1, 101, view + 2, 40, C.street);
    for (let x = Math.floor(cam / 12) * 12 + 2; x < cam + view + 12; x += 12) R(x, 110, 6, 1, C.stone);
    const court = building('court');
    for (let i = 0; i < 5; i++) R(court.door - 9, 102 + i * 4, 18, 2, '#222733'); // zebra crossing outside the court
    for (const x of lamps) { R(x, 74, 1, 16, C.star); R(x - 1, 72, 3, 2, C.light); }
    for (const x of trees) {
      R(x, 80, 1, 10, C.trunk);
      sprite(['..XXX..', '.XXYXX.', 'XXYXXXX', 'XXXXYXX', '.XXXXX.'], x - 3, 72, { X: C.tree, Y: C.tree2 });
    }
  }

  function drawCars(dt) {
    const shown = scene?.pandemic === 'lockdown' ? [] : scene?.pandemic === 'reopening' ? cars.slice(0, 2) : cars;
    for (const c of shown) {
      const v = VEHICLES[c.kind];
      c.x += c.dir * v.speed * dt;
      if (c.dir > 0 && c.x > width + 20) c.x = -30;
      if (c.dir < 0 && c.x < -30) c.x = width + 20;
      const y = (c.dir > 0 ? 109 : 117) - v.rows.length;
      sprite(v.rows, Math.round(c.x), y, { Y: C.yellow, G: '#2f3a2e', W: '#2a3446', O: '#0a0b0f', H: C.light, R: c.kind === 'bus' ? C.red : '#7a2f2a',
        B: c.kind === 'car' ? '#3b4a6b' : C.red }, c.dir < 0);
    }
  }

  function drawLocal(l, t) {
    if (l.mode === 'home') return;
    const shake = t < l.shake ? (Math.floor(t / 60) % 2 ? 1 : -1) : 0;
    const hop = t < partyUntil && (l.badge === 'done' || l.badge === 'says') && !calm() ? -Math.round(Math.abs(Math.sin(t / 170 + l.info.number)) * 3) : 0;
    const x = Math.round(l.x) - 2 + shake, frame = l.mode === 'walk' && Math.floor(t / 250) % 2 ? PERSON.a : PERSON.b;
    sprite(frame, x, 89 + hop, { H: C.hair, S: C.skin, B: SHIRTS[l.info.number % SHIRTS.length], L: C.legs, F: C.feet });
    if (scene?.pandemic) R(x + 1, 91 + hop, 3, 1, '#c9d3dc'); // a mask
    if (l.active && l.mode !== 'walk') R(x + 4, 93 + hop, 1, 2, C.light); // the phone in hand, lit while they work
    label(String(l.info.number).padStart(2, '0'), x + 7.5, 90, 1.7, l.active ? C.light : '#8a8f9c', 'left');

    let mark = l.badge;
    if (!mark && l.bubble === 'stuck' && t < l.until) mark = 'stuck';
    if (mark || (l.active && l.mode !== 'walk')) {
      const bx = x - 3, by = 79 + hop;
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

  // ---------- Celebration: fireworks over the skyline, confetti over everything ----------

  function party(dt, t) {
    if (t < partyUntil - 2500 && t > nextRocket) {
      nextRocket = t + 380 + Math.random() * 420;
      rockets.push({ x: cv.width * (0.08 + Math.random() * 0.84), y: oy + 90 * p, vy: -cv.height * (0.75 + Math.random() * 0.3),
        top: cv.height * (0.12 + Math.random() * 0.3), color: PARTY[Math.floor(Math.random() * PARTY.length)] });
    }
    const u = p;
    for (const r of rockets) {
      r.y += r.vy * dt;
      ctx.fillStyle = C.light;
      ctx.fillRect(Math.round(r.x / u) * u, Math.round(r.y / u) * u, u, u * 2);
      if (r.y <= r.top) {
        r.done = true;
        for (let i = 0; i < 28; i++) {
          const a = (i / 28) * Math.PI * 2, s = cv.height * (0.12 + Math.random() * 0.12);
          sparks.push({ x: r.x, y: r.y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: 1, color: i % 4 ? r.color : C.ink });
        }
      }
    }
    rockets = rockets.filter(r => !r.done);
    for (const s of sparks) {
      s.vy += cv.height * 0.18 * dt; s.x += s.vx * dt; s.y += s.vy * dt; s.life -= dt * 0.8;
      ctx.globalAlpha = Math.max(0, s.life);
      ctx.fillStyle = s.color;
      ctx.fillRect(Math.round(s.x / u) * u, Math.round(s.y / u) * u, u, u);
    }
    ctx.globalAlpha = 1;
    sparks = sparks.filter(s => s.life > 0);
    for (const c of confetti) {
      if (t < c.born) continue;
      c.y += c.vy * dt; c.x += c.vx * dt + Math.sin(t / 300 + c.phase) * u * 0.6;
      ctx.fillStyle = c.color;
      ctx.fillRect(Math.round(c.x / u) * u, Math.round(c.y / u) * u, u * c.size, u);
    }
    confetti = confetti.filter(c => c.y < cv.height + 10);
  }

  function celebrate() {
    partyUntil = now() + 9000;
    if (calm()) return;
    const t = now();
    confetti = Array.from({ length: 180 }, (_, i) => ({
      x: Math.random() * cv.width, y: -Math.random() * cv.height * 0.2 - 10, vx: (Math.random() - 0.5) * p * 8,
      vy: cv.height * (0.12 + Math.random() * 0.16), color: PARTY[i % PARTY.length], born: t + Math.random() * 3500,
      phase: Math.random() * 6, size: 1 + (i % 2),
    }));
  }

  // ---------- The loop ----------

  function update(dt, t) {
    for (const l of locals.values()) {
      if (l.mode === 'home' && t >= l.leaveAt) l.mode = 'walk';
      if (l.mode === 'walk') {
        const d = l.tx - l.x, step = 16 * dt;
        if (Math.abs(d) <= step) { l.x = l.tx; l.mode = 'wait'; } else l.x += Math.sign(d) * step;
      }
    }
    // The camera follows whoever is working, or whoever is walking, unless you are looking around yourself.
    if (t > manualUntil && !drag) {
      const list = [...locals.values()], active = list.find(l => l.active), walkers = list.filter(l => l.mode === 'walk');
      const focus = active ? active.x : walkers.length ? walkers.reduce((s, l) => s + l.x, 0) / walkers.length : null;
      if (focus !== null) camTarget = clampCam(focus - view / 2);
    }
    cam += (camTarget - cam) * Math.min(1, dt * 2.5);
  }

  let last = now();
  function frame() {
    const t = now(), dt = Math.min(0.1, (t - last) / 1000);
    last = t;
    update(dt, t);
    ctx.imageSmoothingEnabled = false;
    drawSky();
    drawSkyline(far, 0.35, C.far, C.farWin, C.far, 1);
    drawSkyline(mid, 0.65, C.mid, C.midWin, C.midDark, 2);
    ox = cam;
    for (const b of buildings) {
      if ((b.x + b.w + 6 - cam) * p < 0 || (b.x - 6 - cam) * p > cv.width) continue;
      drawBuilding(b, t);
      if (scene?.pandemic === 'lockdown' && SHUT.has(b.key)) {
        for (let y = 76; y < 90; y += 2) R(b.x + 2, y, b.w - 4, 1, C.slab2); // shutters down
        R(b.x + 2, 77, b.w - 4, 13, 'rgba(12,14,19,0.55)');
      }
    }
    drawStreet(t);
    drawFestival(t);
    drawCars(dt);
    ox = cam;
    [...locals.values()].sort((a, b) => a.x - b.x).forEach(l => drawLocal(l, t));
    drawRain(t);
    if (t < partyUntil + 4000 || sparks.length || confetti.length) party(dt, t);
    requestAnimationFrame(frame);
  }

  // ---------- Pointer: drag or scroll to look around, click a local to follow them ----------

  const toWorld = e => {
    const r = cv.getBoundingClientRect(), dpr = cv.width / r.width;
    return [(e.clientX - r.left) * dpr / p + cam, ((e.clientY - r.top) * dpr - oy) / p];
  };
  const localAt = e => {
    const [ux, uy] = toWorld(e);
    return [...locals.values()].find(l => l.mode !== 'home' && ux >= l.x - 4 && ux <= l.x + 7 && uy >= 78 && uy <= 99);
  };

  function init(canvas, options) {
    cv = canvas; ctx = cv.getContext('2d');
    people = options.people; onPick = options.onPick || onPick;
    build();
    new ResizeObserver(resize).observe(cv);
    cv.addEventListener('pointerdown', e => { drag = { x: e.clientX, cam, moved: false }; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove', e => {
      if (drag) {
        const dpr = cv.width / cv.getBoundingClientRect().width, dx = e.clientX - drag.x;
        if (Math.abs(dx) > 3) drag.moved = true;
        if (drag.moved) { cam = camTarget = clampCam(drag.cam - dx * dpr / p); manualUntil = now() + 10000; }
      }
      cv.style.cursor = drag?.moved ? 'grabbing' : localAt(e) ? 'pointer' : 'grab';
    });
    cv.addEventListener('pointerup', e => {
      if (drag && !drag.moved) { const hit = localAt(e); onPick(hit ? hit.id : null); }
      drag = null;
    });
    cv.addEventListener('wheel', e => {
      e.preventDefault();
      const dpr = cv.width / cv.getBoundingClientRect().width;
      camTarget = clampCam(camTarget + (e.deltaX || e.deltaY) * dpr / p * 0.6);
      manualUntil = now() + 10000;
    }, { passive: false });
    document.fonts.load('12px Silkscreen');
    resize();
    requestAnimationFrame(frame);
  }

  function startDay(ids, settled = false) {
    locals.clear();
    partyUntil = 0; confetti = []; sparks = []; rockets = [];
    order = ids.filter(id => people.has(id));
    const t = now(), home = building('home').door;
    order.forEach((id, i) => {
      const info = people.get(id), door = building(homeOf(info.number)).door;
      locals.set(id, { id, info, place: WORKPLACE[info.group] || 'office', x: door, tx: door, mode: settled ? 'wait' : 'home',
        leaveAt: t + 400 + i * 700, active: false, bubble: null, until: 0, badge: null, shake: 0 });
    });
    for (const l of locals.values()) { l.tx = slot(l); if (settled) l.x = l.tx; }
    manualUntil = 0;
    camTarget = clampCam(settled && order.length ? locals.get(order[0]).x - view / 3 : home - view / 4);
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
  function setScene(s) { scene = s; }

  return { init, startDay, event, step, select, celebrate, setScene };
})();
