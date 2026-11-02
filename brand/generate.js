// Build the README's pixel art: the wordmark banner, the town view and the setup screen.
// Fonts are embedded as base64 woff2 so they render inside GitHub's <img> sandbox.
// Run from this folder: node generate.js
const fs = require('fs');
const path = require('path');

const b64 = (f) => fs.readFileSync(path.join(__dirname, 'fonts', f)).toString('base64');
const fontFaces = `
  @font-face { font-family: 'VT323'; src: url(data:font/woff2;base64,${b64('vt323.woff2')}) format('woff2'); }
  @font-face { font-family: 'Silkscreen'; src: url(data:font/woff2;base64,${b64('silkscreen.woff2')}) format('woff2'); }
`;

// One idea drives the palette: a town at night, where a lit window is a local who is awake.
const NIGHT = '#0c0e13';
const RAIL = '#090b0f';
const PANEL = '#10131a';
const SLAB = '#161a24';
const SLAB2 = '#1d2231';
const STONE = '#2b3244';
const DARK_WIN = '#232938';
const LIGHT = '#ffc94d';
const DIM_LIGHT = '#6e5c2f';
const INK = '#ebe7dc';
const DIM = '#8a8f9c';
const LINE = '#262c3b';
const STAR = '#3b4255';
const WALK = '#1a1f2b';
const STREET = '#12151c';
const SKIN = '#b27b55';
const HAIR = '#1d1916';

const rect = (x, y, w, h, fill, extra = '') =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"${extra}/>`;

const text = (x, y, str, { font = 'VT323', size = 24, fill = INK, anchor = 'start', spacing = 0 } = {}) =>
  `<text x="${x}" y="${y}" font-family="${font}" font-size="${size}" fill="${fill}" text-anchor="${anchor}"` +
  (spacing ? ` letter-spacing="${spacing}"` : '') + `>${str}</text>`;

// Draws a pixel map, one character per pixel ('.' is empty), merging runs into single rects.
function sprite(rows, x, y, p, palette) {
  let out = '';
  rows.forEach((row, j) => {
    let i = 0;
    while (i < row.length) {
      const ch = row[i];
      let k = i;
      while (k < row.length && row[k] === ch) k++;
      if (palette[ch]) out += rect(x + i * p, y + j * p, (k - i) * p, p, palette[ch]);
      i = k;
    }
  });
  return out;
}

// Small deterministic random so every build draws the same town.
function rng(seed) {
  return () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };
}

const svg = (w, h, css, body) => `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" shape-rendering="crispEdges">
<style>${fontFaces}${css}
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
</style>
${body}
</svg>
`;

// ---------- Wordmark glyphs: 5 x 7, lit windows spell the name ----------

const GLYPHS = {
  L: ['X....', 'X....', 'X....', 'X....', 'X....', 'X....', 'XXXXX'],
  o: ['.....', '.....', '.XXX.', 'X...X', 'X...X', 'X...X', '.XXX.'],
  c: ['.....', '.....', '.XXXX', 'X....', 'X....', 'X....', '.XXXX'],
  a: ['.....', '.....', '.XXX.', '....X', '.XXXX', 'X...X', '.XXXX'],
  l: ['.XX..', '..X..', '..X..', '..X..', '..X..', '..X..', '.XXX.'],
  s: ['.....', '.....', '.XXXX', 'X....', '.XXX.', '....X', 'XXXX.'],
};

// ---------- Banner: a building at night whose lit windows spell Locals ----------

function banner() {
  const W = 1280, H = 372, cell = 20, win = 12, cols = 51, rows = 9;
  const left = (W - cols * cell) / 2, top = 58;
  const word = 'Locals';
  const startCol = Math.floor((cols - (word.length * 6 - 1)) / 2);

  const lit = new Set();
  [...word].forEach((ch, n) => {
    GLYPHS[ch].forEach((row, r) => {
      [...row].forEach((v, c) => { if (v === 'X') lit.add(`${startCol + n * 6 + c},${r + 1}`); });
    });
  });

  // Other locals awake behind the dark windows, kept clear of the word so no letter changes shape.
  const rand = rng(7);
  const awake = new Set();
  const endCol = startCol + word.length * 6 - 1;
  const picked = [];
  while (picked.length < 6) {
    const c = Math.floor(rand() * cols), r = Math.floor(rand() * rows);
    const clearOfWord = c < startCol - 3 || c > endCol + 3;
    const clearOfOthers = picked.every(([pc, pr]) => Math.max(Math.abs(pc - c), Math.abs(pr - r)) >= 3);
    if (clearOfWord && clearOfOthers) { picked.push([c, r]); awake.add(`${c},${r}`); }
  }

  let body = rect(0, 0, W, H, NIGHT);
  for (let i = 0; i < 40; i++) {
    const x = Math.floor(rand() * W / 4) * 4, y = Math.floor(rand() * 34 / 4) * 4 + 4;
    body += rect(x, y, 4, 4, STAR);
  }
  body += rect(left - 22, top - 22, cols * cell + 44, 8, SLAB2);
  body += rect(left - 14, top - 14, cols * cell + 28, rows * cell + 28, SLAB);
  body += rect(0, top + rows * cell + 14, W, 2, LINE);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const x = left + c * cell + (cell - win) / 2, y = top + r * cell + (cell - win) / 2;
      const key = `${c},${r}`;
      if (lit.has(key)) {
        body += rect(x, y, win, win, LIGHT, ` class="on" style="animation-delay:${(c - startCol) * 40}ms"`);
      } else if (awake.has(key)) {
        body += rect(x, y, win, win, DIM_LIGHT, ` class="awake" style="animation-duration:${5 + Math.floor(rand() * 6)}s;animation-delay:-${Math.floor(rand() * 5)}s"`);
      } else {
        body += rect(x, y, win, win, DARK_WIN);
      }
    }
  }

  body += text(W / 2, 312, 'People who live with your app.', { font: 'Silkscreen', size: 28, anchor: 'middle' });
  body += text(W / 2, 346, 'A small town of AI users that runs on your own machine', { size: 28, fill: DIM, anchor: 'middle' });

  const css = `
  .on { animation: on 700ms steps(2) backwards; }
  @keyframes on { from { opacity: 0; } to { opacity: 1; } }
  .awake { animation: awake 7s steps(1) infinite; }
  @keyframes awake { 0%, 55% { fill: ${DIM_LIGHT}; } 56%, 100% { fill: ${LIGHT}; } }`;
  return svg(W, H, css, body);
}

// ---------- Shared pieces for the app screens ----------

const W2 = 1280, H2 = 720, RAIL_W = 56;

const ICONS = {
  town: ['...X...', '..XXX..', '.XXXXX.', 'XXXXXXX', '.X...X.', '.X.X.X.', '.X.X.X.'],
  feed: ['XXXXXXX', '.......', 'XXXXX..', '.......', 'XXXXXXX', '.......', 'XXXX...'],
  setup: ['.X.....', 'XXXXXXX', '.X.....', '.....X.', 'XXXXXXX', '.....X.', '.......'],
  report: ['.....X.', '.....X.', '..X..X.', '..X..X.', 'X.X..X.', 'X.X..X.', 'XXXXXXX'],
};

function rail(active) {
  let out = rect(0, 0, RAIL_W, H2, RAIL) + rect(RAIL_W - 2, 0, 2, H2, LINE);
  out += sprite(GLYPHS.L, 20, 24, 3, { X: LIGHT });
  ['town', 'setup', 'feed', 'report'].forEach((name, i) => {
    const y = 96 + i * 52;
    const on = name === active;
    if (on) out += rect(0, y - 8, 3, 37, LIGHT);
    out += sprite(ICONS[name], 18, y, 3, { X: on ? LIGHT : DIM });
  });
  return out;
}

// ---------- Town view: pixel town on the left 75%, feed on the right 25% ----------

const PERSON = {
  a: ['.HHH.', '.SSS.', '.SSS.', 'BBBBB', 'BBBBB', '.BBB.', '.L.L.', 'L...L', 'F...F'],
  b: ['.HHH.', '.SSS.', '.SSS.', 'BBBBB', 'BBBBB', '.BBB.', '.L.L.', '.L.L.', '.F.F.'],
};
const personPalette = (shirt) => ({ H: HAIR, S: SKIN, B: shirt, L: '#2a2f3d', F: '#14171e' });

const BUBBLE = [
  '.XXXXXXXX.', 'XXXXXXXXXX', 'XXXXXXXXXX', 'XXXXXXXXXX', 'XXXXXXXXXX', 'XXXXXXXXXX', '.XXXXXXXX.', '...XX.....', '...X......',
];
const MARKS = {
  '!': ['..........', '....XX....', '....XX....', '....XX....', '..........', '....XX....'],
  '?': ['..........', '...XXXX...', '......X...', '....XX....', '..........', '....XX....'],
};

function town() {
  const p = 6, ox = RAIL_W, TW = 918, fx = ox + TW, FW = W2 - fx;
  const u = (x) => ox + x * p, v = (y) => y * p;
  const rand = rng(21);
  let s = rect(ox, 0, TW, H2, NIGHT);

  for (let i = 0; i < 46; i++) s += rect(u(Math.floor(rand() * 150)), v(Math.floor(rand() * 36) + 14), p, p, STAR);
  s += sprite(['..XXXX..', '.XXXXXX.', 'XXXXXXXX', 'XXXXXXXX', 'XXXXXXXX', 'XXXXXXXX', '.XXXXXX.', '..XXXX..'], u(100), v(12), p, { X: '#d9d3c2' });

  const windows = (x, y, cols, rowsN, w, h, gx, gy, chance) => {
    let out = '';
    for (let r = 0; r < rowsN; r++) for (let c = 0; c < cols; c++) {
      out += rect(u(x + c * (w + gx)), v(y + r * (h + gy)), w * p, h * p, rand() < chance ? LIGHT : DARK_WIN);
    }
    return out;
  };
  const sign = (x, y, w, label) =>
    rect(u(x), v(y), w * p, 5 * p, SLAB2) + text(u(x + w / 2), v(y) + 22, label, { font: 'Silkscreen', size: 14, fill: INK, anchor: 'middle' });

  // Flats where the locals live.
  s += rect(u(3), v(26), 30 * p, 2 * p, SLAB2) + rect(u(22), v(22), 6 * p, 4 * p, SLAB2);
  s += rect(u(4), v(28), 28 * p, 62 * p, SLAB);
  s += windows(7, 32, 5, 9, 3, 3, 1.5, 3, 0.4);

  // Fabrication shop: shutter half up, warm inside.
  s += rect(u(36), v(60), 26 * p, 30 * p, SLAB);
  s += sign(37, 62, 24, 'FABRICATION');
  s += rect(u(39), v(70), 20 * p, 20 * p, DIM_LIGHT);
  for (let i = 0; i < 5; i++) s += rect(u(39), v(70 + i * 2), 20 * p, p, i % 2 ? LINE : SLAB2);

  // Chinese stall: striped awning over a lit counter.
  s += rect(u(66), v(64), 22 * p, 26 * p, SLAB);
  s += sign(67, 66, 20, 'CHINESE');
  for (let i = 0; i < 10; i++) s += rect(u(66 + i * 2.2), v(72), 2.2 * p, 4 * p, i % 2 ? DARK_WIN : INK);
  s += rect(u(69), v(77), 16 * p, 7 * p, DIM_LIGHT) + rect(u(68), v(84), 18 * p, 6 * p, SLAB2);

  // Court: stepped roof and columns.
  [[12, 4], [9, 10], [6, 16], [3, 22], [0, 28]].forEach(([dx, w], i) => { s += rect(u(92 + dx), v(46 + i), w * p, p, SLAB2); });
  s += rect(u(92), v(51), 28 * p, 39 * p, SLAB);
  s += sign(94, 53, 24, 'COURT');
  for (let i = 0; i < 5; i++) s += rect(u(95 + i * 5), v(60), 2 * p, 28 * p, STONE);
  s += rect(u(91), v(88), 30 * p, 2 * p, SLAB2);

  // Office tower with people still working late.
  s += rect(u(124), v(20), 26 * p, 70 * p, SLAB);
  s += windows(126, 23, 4, 9, 4, 3, 2, 2, 0.3);
  s += sign(126, 70, 22, 'OFFICE');
  s += rect(u(134), v(80), 6 * p, 10 * p, DIM_LIGHT);

  // Street: pavement, kerb, road and lamps.
  s += rect(ox, v(90), TW, 10 * p, WALK) + rect(ox, v(100), TW, p, LINE) + rect(ox, v(101), TW, H2 - v(101), STREET);
  for (let x = 2; x < 153; x += 12) s += rect(u(x), v(110), 6 * p, p, STONE);
  [34, 64, 90, 122].forEach((x) => { s += rect(u(x), v(74), p, 16 * p, STAR) + rect(u(x - 1), v(72), 3 * p, 2 * p, LIGHT); });

  // Two locals stuck in an app, each with a bubble and their number.
  const stuck = (x, shirt, mark, id) =>
    sprite(PERSON.b, u(x), v(89), p, personPalette(shirt)) +
    `<g class="pulse">${sprite(BUBBLE, u(x - 3), v(78), p, { X: INK })}${sprite(MARKS[mark], u(x - 3), v(78), p, { X: '#c8851b' })}</g>` +
    text(u(x + 8), v(82), id, { font: 'Silkscreen', size: 14, fill: LIGHT });
  s += stuck(46, '#5b8def', '!', '04');
  s += stuck(76, '#98c379', '?', '02');

  // Locals walking between home and work.
  let css = `
  .pulse { animation: pulse 1.4s steps(1) infinite; }
  @keyframes pulse { 0%, 70% { opacity: 1; } 71%, 100% { opacity: 0.35; } }
  .fa { animation: fa 0.5s steps(1) infinite; }
  .fb { animation: fb 0.5s steps(1) infinite; }
  @keyframes fa { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
  @keyframes fb { 0%, 49% { opacity: 0; } 50%, 100% { opacity: 1; } }`;
  const walkers = [
    { x: 18, shirt: '#e06c75', dir: 1, dur: 30, delay: 0 },
    { x: 110, shirt: '#c678dd', dir: -1, dur: 38, delay: -14 },
    { x: 60, shirt: INK, dir: 1, dur: 44, delay: -30 },
  ];
  walkers.forEach((w, i) => {
    const x0 = u(w.x), from = (w.dir > 0 ? ox - 40 : fx + 10) - x0, to = (w.dir > 0 ? fx + 10 : ox - 40) - x0;
    css += `
  .w${i} { animation: w${i} ${w.dur}s linear ${w.delay}s infinite; }
  @keyframes w${i} { from { transform: translateX(${from}px); } to { transform: translateX(${to}px); } }`;
    s += `<g class="w${i}"><g class="fa">${sprite(PERSON.a, x0, v(91), p, personPalette(w.shirt))}</g>` +
      `<g class="fb" opacity="0">${sprite(PERSON.b, x0, v(91), p, personPalette(w.shirt))}</g></g>`;
  });

  // The town's clock, top left.
  s += text(ox + 24, 40, 'DAY 3 · 21:40', { font: 'Silkscreen', size: 18 });
  s += text(ox + 24, 66, '5 locals · qwen3:4b · testing Pops', { size: 24, fill: DIM });

  // Feed.
  let f = rect(fx, 0, FW, H2, PANEL) + rect(fx, 0, 2, H2, LINE);
  f += text(fx + 22, 42, 'FEED', { font: 'Silkscreen', size: 18 });
  f += rect(W2 - 74, 30, 8, 8, LIGHT, ' class="pulse"') + text(W2 - 22, 42, 'LIVE', { font: 'Silkscreen', size: 14, fill: LIGHT, anchor: 'end' });
  f += rect(fx + 22, 60, FW - 44, 2, LINE);
  const entries = [
    { tag: 'STUCK', tone: LIGHT, who: '04 FABRICATOR', lines: ['Customer paid the', 'advance. The new order', 'form has no box for it.'] },
    { tag: 'WORKAROUND', tone: INK, who: '04 FABRICATOR', lines: ['Wrote the advance', 'in Notes instead.'] },
    { tag: 'STUCK', tone: LIGHT, who: '02 COUNTER', lines: ['Undo was gone before', 'I looked up from', 'the wok.'] },
    { tag: 'DONE', tone: DIM, who: '05 COUNTER', lines: ['Three orders in 1:52.', 'Every total right.'] },
  ];
  let y = 98;
  entries.forEach((e, i) => {
    f += text(fx + 22, y, e.tag, { font: 'Silkscreen', size: 14, fill: e.tone });
    f += text(W2 - 22, y, e.who, { font: 'Silkscreen', size: 12, fill: DIM, anchor: 'end' });
    e.lines.forEach((line, k) => { f += text(fx + 22, y + 30 + k * 25, line, { size: 26 }); });
    y += 30 + e.lines.length * 25 + 22;
    if (i < entries.length - 1) { f += rect(fx + 22, y - 18, FW - 44, 1, LINE); y += 16; }
  });
  f += text(fx + 22, H2 - 22, 'Concept view, example entries', { size: 22, fill: DIM });

  const clip = `<defs><clipPath id="townclip"><rect x="${ox}" y="0" width="${TW}" height="${H2}"/></clipPath></defs>`;
  return svg(W2, H2, css, rect(0, 0, W2, H2, NIGHT) + clip + `<g clip-path="url(#townclip)">${s}</g>` + f + rail('town'));
}

// ---------- Setup: choose the locals, see what your machine will spend ----------

function setup() {
  const ox = RAIL_W + 40, colW = 560;
  let s = rect(0, 0, W2, H2, NIGHT);
  s += text(ox, 56, 'WHO LIVES IN TOWN TONIGHT', { font: 'Silkscreen', size: 20 });
  s += text(ox, 86, 'Tick the jobs, set how many of each.', { size: 26, fill: DIM });

  const jobs = [
    ['Fabrication shop owner', 2, true],
    ['Food stall counter', 2, true],
    ['Fresh graduate', 1, true],
    ['Lawyer', 0, false],
    ['Site engineer', 0, false],
    ['Clinic doctor', 0, false],
  ];
  jobs.forEach(([name, n, on], i) => {
    const y = 126 + i * 64;
    s += rect(ox, y, colW, 52, i % 2 ? NIGHT : PANEL);
    s += rect(ox + 18, y + 16, 20, 20, on ? LIGHT : 'none', on ? '' : ` stroke="${DIM}" stroke-width="2"`);
    if (on) s += sprite(['.....X', '....X.', 'X..X..', '.XX...'], ox + 20, y + 20, 3, { X: NIGHT });
    s += text(ox + 56, y + 34, name, { size: 28, fill: on ? INK : DIM });
    s += rect(ox + colW - 132, y + 12, 28, 28, SLAB2) + text(ox + colW - 118, y + 33, '-', { size: 28, fill: DIM, anchor: 'middle' });
    s += text(ox + colW - 76, y + 35, String(n), { font: 'Silkscreen', size: 20, fill: on ? LIGHT : DIM, anchor: 'middle' });
    s += rect(ox + colW - 48, y + 12, 28, 28, SLAB2) + text(ox + colW - 34, y + 33, '+', { size: 28, fill: DIM, anchor: 'middle' });
  });

  // Meters for this machine.
  const mx = ox + colW + 64, mw = W2 - mx - 48;
  s += text(mx, 56, 'YOUR MACHINE', { font: 'Silkscreen', size: 20 });
  s += text(mx, 86, 'RTX 4060 8 GB, 31 GB RAM', { size: 26, fill: DIM });
  const meter = (y, label, value, parts, total, note) => {
    let out = text(mx, y, label, { font: 'Silkscreen', size: 15 }) + text(mx + mw, y, value, { font: 'Silkscreen', size: 15, fill: LIGHT, anchor: 'end' });
    const cells = 24, cw = mw / cells;
    let filled = [];
    parts.forEach(([amount, color]) => { for (let i = 0; i < Math.round(amount / total * cells); i++) filled.push(color); });
    for (let i = 0; i < cells; i++) out += rect(mx + i * cw, y + 14, cw - 4, 22, filled[i] || DARK_WIN);
    return out + text(mx, y + 64, note, { size: 24, fill: DIM });
  };
  s += meter(146, 'GPU MEMORY', '3.1 / 8 GB', [[2.5, LIGHT], [0.6, DIM_LIGHT]], 8, 'Model 2.5 GB, room for 2 at once');
  s += meter(262, 'MEMORY', '6 / 31 GB', [[4, DIM_LIGHT], [2, LIGHT]], 31, 'Android emulator 4 GB, Locals 2 GB');
  s += meter(378, 'TIME', 'About 2 h', [[2, LIGHT]], 8, '5 locals, 3 tasks each, 2 at a time');
  s += rect(mx, 470, mw, 2, LINE);
  s += text(mx, 512, 'More locals take more time,', { size: 26 });
  s += text(mx, 540, 'not more GPU memory.', { size: 26 });
  s += text(mx, 580, 'They share one model and take turns.', { size: 24, fill: DIM });
  s += rect(mx, 618, 220, 52, LIGHT) + text(mx + 110, 652, 'START THE DAY', { font: 'Silkscreen', size: 17, fill: NIGHT, anchor: 'middle' });
  s += text(W2 - 48, 700, 'Concept view, example numbers', { size: 22, fill: DIM, anchor: 'end' });

  return svg(W2, H2, '', s + rail('setup'));
}

fs.writeFileSync(path.join(__dirname, 'banner.svg'), banner());
fs.writeFileSync(path.join(__dirname, 'town.svg'), town());
fs.writeFileSync(path.join(__dirname, 'setup.svg'), setup());
console.log('wrote banner.svg, town.svg, setup.svg');
