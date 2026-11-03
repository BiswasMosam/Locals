// The dashboard: setup, the town and the feed. Talks to `python -m town dashboard` on this machine.
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const getJSON = async url => (await fetch(url)).json();
const OUTCOMES = new Set(['DONE', 'SAYS DONE', 'WRONG DONE', 'GAVE UP', 'ASKED', 'STOPPED', 'ERROR']);

const ICONS = {
  mark: ['X....', 'X....', 'X....', 'X....', 'X....', 'X....', 'XXXXX'],
  town: ['...X...', '..XXX..', '.XXXXX.', 'XXXXXXX', '.X...X.', '.X.X.X.', '.X.X.X.'],
  setup: ['.X.....', 'XXXXXXX', '.X.....', '.....X.', 'XXXXXXX', '.....X.', '.......'],
  days: ['XXXXXXX', 'X.....X', 'XXXXXXX', 'X.X.X.X', 'XXXXXXX', 'X.X.X.X', 'XXXXXXX'],
};
const icon = map => `<svg viewBox="0 0 ${map[0].length} ${map.length}" shape-rendering="crispEdges" fill="currentColor">` +
  map.flatMap((row, y) => [...row].map((c, x) => c === 'X' ? `<rect x="${x}" y="${y}" width="1" height="1"/>` : '')).join('') + '</svg>';
document.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(ICONS[el.dataset.icon]); });

const S = {
  info: null, people: new Map(), groups: [], counts: {}, kind: 'saved', files: [], when: { mode: 'one', date: null, pandemic: '' },
  entries: [], results: {}, day: null, running: false, filter: null, showSteps: true, replay: null,
};

// ---------- Views ----------

function setView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === `view-${name}`));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.view === name));
  if (name === 'setup') refreshMachine();
  if (name === 'days') loadDays();
}
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => setView(t.dataset.view)));
$('#hud-setup').addEventListener('click', () => setView('setup'));

// ---------- Live events ----------

function connect() {
  const es = new EventSource('/api/events');
  es.onmessage = m => handle(JSON.parse(m.data));
}

const fresh = e => e.ended_at && Date.now() / 1000 - e.ended_at < 30;

function handle(e) {
  if (e.type === 'year' && e.phase === 'start') {
    S.running = true;
    $('#verdict').hidden = true;
  } else if (e.type === 'year' && e.phase === 'end') {
    S.running = false;
    if (e.days.length > 1 && fresh(e)) yearVerdict(e);
  } else if (e.type === 'day' && e.phase === 'start') {
    S.day = e; S.running = true; S.entries = []; S.results = {}; S.filter = null;
    TownView.startDay(e.locals); TownView.setScene(e.scene || null); TownView.select(null);
    renderWho(); renderFeed();
  } else if (e.type === 'day' && e.phase === 'end') {
    S.results = e.results;
    $('#now').hidden = true;
    if (!(e.index && e.index[1] > 1)) { S.running = false; if (fresh(e)) verdict(e); }
  } else {
    S.entries.push(e);
    if (e.type === 'event') {
      TownView.event(e);
      if (OUTCOMES.has(e.kind)) S.results[e.local] = e.kind;
    } else {
      TownView.step(e);
      showNow(e);
    }
    appendEntry(e);
  }
  hud();
}

function who(id) {
  const p = S.people.get(id);
  return p ? `${String(p.number).padStart(2, '0')} ${p.name.toUpperCase()}` : id;
}

function hud() {
  const d = S.day;
  $('#live').hidden = !S.running;
  $('#feed-foot').hidden = !S.running;
  $('#hud-setup').hidden = S.running;
  if (!d) return;
  const finished = Object.keys(S.results).length, many = d.index && d.index[1] > 1;
  $('#hud-day').textContent = `${many ? `DAY ${d.index[0]} OF ${d.index[1]}` : 'DAY'} · ${d.task}`.toUpperCase();
  $('#hud-sub').textContent = [d.today, `${finished} of ${d.locals.length} finished`, d.model, S.running ? '' : 'the day is over']
    .filter(Boolean).join(' · ');
}

// The end of a day: 90% or more, with at least three locals, is a celebration; anything else is a plain count.
const WORDS = { 'GAVE UP': 'gave up', 'ASKED': 'asked for help', 'WRONG DONE': 'thought they were done but were not', 'ERROR': 'hit an error' };

const succeeded = k => k === 'DONE' || k === 'SAYS DONE';
const appName = task => { const app = task.split(':')[0].trim(); return /[.:]/.test(app) ? 'YOUR SITE' : app.toUpperCase(); };

function showVerdict(win, head, sub, note) {
  const box = $('#verdict');
  box.classList.toggle('win', win);
  $('#v-head').textContent = head;
  $('#v-sub').textContent = sub;
  $('#v-note').textContent = note;
  box.hidden = false;
  if (win) TownView.celebrate();
}

function verdict(e) {
  const results = Object.values(e.results || {}), total = results.length;
  if (!total || results.includes('STOPPED')) return;
  const ok = results.filter(succeeded).length, pct = Math.round(ok / total * 100);
  const others = Object.entries(WORDS).map(([k, w]) => [results.filter(r => r === k).length, w]).filter(([n]) => n).map(([n, w]) => `${n} ${w}`);
  if (pct >= 90 && total >= 3) {
    showVerdict(true, `${appName(e.task)} IS GREAT`, `${ok} of ${total} locals got it done in their real day · ${pct}%`,
      'Busy hands, small screens, no patience to spare, and it still worked.');
  } else {
    showVerdict(false, `${ok} OF ${total} GOT IT DONE`, [`${pct}%`, ...others].join(' · '),
      pct >= 90 ? 'Send at least three locals to earn the fireworks.' : 'Click a local in the town to see where they got stuck.');
  }
}

// A year: every local on every day counts once; the hardest day is named so you know where to look.
function yearVerdict(e) {
  const all = e.days.flatMap(d => Object.values(d.results)), total = all.length;
  if (!total || all.includes('STOPPED')) return;
  const ok = all.filter(succeeded).length, pct = Math.round(ok / total * 100);
  const rate = d => { const r = Object.values(d.results); return r.filter(succeeded).length / r.length; };
  const hardest = e.days.reduce((a, d) => (rate(d) < rate(a) ? d : a));
  const hard = Object.values(hardest.results);
  const note = rate(hardest) < 1 ? `Hardest day: ${hardest.label}, ${hard.filter(succeeded).length} of ${hard.length} done.` : 'Every single day went well.';
  if (pct >= 90 && total >= 3) showVerdict(true, `${appName(e.task)} IS GREAT ALL YEAR`, `${ok} of ${total} local days done across ${e.days.length} days · ${pct}%`, note);
  else showVerdict(false, `${ok} OF ${total} LOCAL DAYS DONE`, `${pct}% across ${e.days.length} days`, note);
}
$('#v-close').addEventListener('click', () => { $('#verdict').hidden = true; });

function showNow(e) {
  const el = $('#now');
  el.hidden = false;
  el.innerHTML = `<b>${esc(who(e.local))}</b><span class="act">${esc(e.line)}</span><span class="thought">${esc(e.thought)}</span>`;
}

// ---------- Feed ----------

const visible = e => (!S.filter || e.local === S.filter) && (S.showSteps || e.type !== 'step');

function entryEl(e) {
  const li = document.createElement('li');
  if (e.type === 'step') {
    li.className = 'step';
    li.innerHTML = `<div class="row"><span class="meta">${esc(who(e.local))} · STEP ${e.step}</span><span class="meta">${esc(e.at)}</span></div>` +
      `<p class="says"><span class="act">${esc(e.line)}</span> ${esc(e.thought)}</p>`;
  } else {
    li.className = 'ev k-' + e.kind.replace(/ /g, '-');
    li.innerHTML = `<div class="row"><span class="tag">${esc(e.kind)}</span><span class="meta">${esc(who(e.local))} · ${esc(e.at)}</span></div>` +
      `<p class="says">${esc(e.says)}</p>`;
  }
  if (e.shot) {
    li.classList.add('click');
    li.title = 'See the screen they were looking at';
    li.addEventListener('click', () => openReplay(e));
  }
  return li;
}

function renderFeed() {
  const list = $('#feed-list');
  list.innerHTML = '';
  const shown = S.entries.filter(visible);
  if (!shown.length) list.innerHTML = `<li class="empty">${S.day ? 'Nothing yet. The first local is on the way.' : 'Nothing has happened yet.'}</li>`;
  shown.forEach(e => list.append(entryEl(e)));
  list.scrollTop = list.scrollHeight;
}

function appendEntry(e) {
  if (!visible(e)) return;
  const list = $('#feed-list');
  list.querySelector('.empty')?.remove();
  const atBottom = list.scrollTop + list.clientHeight >= list.scrollHeight - 60;
  list.append(entryEl(e));
  if (atBottom) list.scrollTop = list.scrollHeight;
}

$('#show-steps').addEventListener('change', e => { S.showSteps = e.target.checked; renderFeed(); });
$('#stop').addEventListener('click', () => fetch('/api/stop', { method: 'POST', body: '{}' }));

function pick(id) {
  S.filter = id && id !== S.filter ? id : null;
  TownView.select(S.filter);
  renderWho();
  renderFeed();
}

function renderWho() {
  const box = $('#who'), p = S.people.get(S.filter);
  box.hidden = !p;
  if (!p) return;
  const L = p.limits;
  box.innerHTML = `<div class="name">${esc(who(p.id))}</div>` +
    `<p>${esc(p.job)}, ${p.age} · on a ${esc(L.device)}</p>` +
    `<p>${esc(p.situation.place)}. ${esc(p.situation.hands)}.</p>` +
    `<p class="limits">Reads ${L.read_words} words · ${L.patience_steps} steps of patience · slips ${Math.round(L.slip_rate * 100)}% · when stuck: ${esc(p.habits.when_stuck)}</p>` +
    `<button type="button" id="who-clear">SHOW EVERYONE</button>`;
  $('#who-clear').addEventListener('click', () => pick(null));
}

// ---------- Replay ----------

function openReplay(e) {
  const list = S.entries.filter(x => x.local === e.local && x.shot);
  S.replay = { list, i: Math.max(0, list.indexOf(e)) };
  $('#replay').hidden = false;
  showReplay();
}

function showReplay() {
  const { list, i } = S.replay, e = list[i];
  $('#replay-img').src = '/' + e.shot;
  $('#replay-who').textContent = `${who(e.local)} · ${e.type === 'step' ? 'STEP ' + e.step : e.kind}`;
  $('#replay-line').textContent = e.type === 'step' ? e.line : e.says;
  $('#replay-thought').textContent = e.type === 'step' ? e.thought : '';
  $('#replay-prev').disabled = i === 0;
  $('#replay-next').disabled = i === list.length - 1;
}

function moveReplay(d) {
  if (!S.replay) return;
  S.replay.i = Math.min(S.replay.list.length - 1, Math.max(0, S.replay.i + d));
  showReplay();
}
const closeReplay = () => { $('#replay').hidden = true; S.replay = null; };
$('#replay-prev').addEventListener('click', () => moveReplay(-1));
$('#replay-next').addEventListener('click', () => moveReplay(1));
$('#replay-close').addEventListener('click', closeReplay);
document.addEventListener('keydown', e => {
  if ($('#replay').hidden) return;
  if (e.key === 'Escape') closeReplay();
  if (e.key === 'ArrowLeft') moveReplay(-1);
  if (e.key === 'ArrowRight') moveReplay(1);
});

// ---------- Setup ----------

function buildSetup() {
  const select = $('#task-select'), current = select.value;
  select.innerHTML = S.info.tasks.map(t => `<option value="${esc(t.ref)}">${esc(t.app)} · ${esc(t.ref.split(':')[1])}${t.mine ? ' (yours)' : ''}</option>`).join('');
  if (current) select.value = current;
  showTask();

  const groups = $('#groups');
  groups.innerHTML = '';
  // Each family gets a heading whose tick sends the whole family out, or keeps it home.
  const families = new Map();
  for (const g of S.groups) {
    if (!families.has(g.family)) {
      const head = document.createElement('li');
      head.className = 'family';
      head.innerHTML = `<input type="checkbox" class="check" aria-label="Everyone in ${esc(g.family)}"><span class="label">${esc(g.family)}</span><span class="count"></span>`;
      families.set(g.family, { head, rows: [] });
      groups.append(head);
    }
    if (!(g.key in S.counts)) S.counts[g.key] = 1;
    const li = document.createElement('li');
    li.className = 'group';
    li.innerHTML = `<input type="checkbox" class="check" aria-label="${esc(g.label)}">` +
      `<div><div class="label">${esc(g.label)}</div><div class="names"></div></div>` +
      `<div class="stepper"><button type="button" aria-label="One fewer">-</button><output></output><button type="button" aria-label="One more">+</button></div>`;
    const [minus, plus] = li.querySelectorAll('.stepper button');
    const fam = families.get(g.family);
    const set = n => { S.counts[g.key] = Math.max(0, Math.min(g.people.length, n)); paint(); paintFamily(fam); renderMeters(); };
    const paint = () => {
      const n = S.counts[g.key];
      li.classList.toggle('off', n === 0);
      li.querySelector('.check').checked = n > 0;
      li.querySelector('output').textContent = n;
      li.querySelector('.names').textContent = n ? g.people.slice(0, n).map(p => `${p.name}, ${p.job.toLowerCase()}`).join(' · ') : `${g.people.length} people stay home`;
    };
    li.querySelector('.check').addEventListener('change', e => set(e.target.checked ? Math.max(1, g.last || 1) : (g.last = S.counts[g.key], 0)));
    minus.addEventListener('click', () => set(S.counts[g.key] - 1));
    plus.addEventListener('click', () => set(S.counts[g.key] + 1));
    paint();
    fam.rows.push({ g, set });
    groups.append(li);
  }
  for (const fam of families.values()) {
    fam.head.querySelector('.check').addEventListener('change', e => {
      const going = e.target.checked; // read once: each row repaints this box as it changes
      for (const { g, set } of fam.rows) {
        if (going) set(Math.max(1, g.last || 1));
        else { if (S.counts[g.key]) g.last = S.counts[g.key]; set(0); }
      }
    });
    paintFamily(fam);
  }
  renderMeters();
}

function paintFamily(fam) {
  const going = fam.rows.reduce((n, { g }) => n + (S.counts[g.key] || 0), 0);
  const on = fam.rows.filter(({ g }) => S.counts[g.key] > 0).length;
  const box = fam.head.querySelector('.check');
  box.checked = on > 0;
  box.indeterminate = on > 0 && on < fam.rows.length;
  fam.head.classList.toggle('off', on === 0);
  fam.head.querySelector('.count').textContent = going ? `${going} going` : 'staying home';
}

function showTask() {
  const t = S.info.tasks.find(x => x.ref === $('#task-select').value);
  $('#task-story').textContent = t ? t.story : '';
  $('#task-check').textContent = t ? `Done when ${t.check}.` : '';
}
$('#task-select').addEventListener('change', showTask);

document.querySelectorAll('.kind-btn').forEach(b => b.addEventListener('click', () => {
  S.kind = b.dataset.kind;
  document.querySelectorAll('.kind-btn').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('.kind-pane').forEach(x => x.classList.toggle('on', x.dataset.pane === S.kind));
  $('#goal-block').hidden = S.kind === 'saved';
  // An app has no address and saves no downloads, so only "the screen shows" and "their word" make sense.
  for (const o of $('#site-check').options) o.hidden = S.kind === 'apk' && ['url_contains', 'download'].includes(o.value);
  if (S.kind === 'apk' && $('#site-check').selectedOptions[0].hidden) { $('#site-check').value = 'page_text'; $('#site-check').dispatchEvent(new Event('change')); }
  renderMeters();
}));

// The app to test: an APK dropped here is uploaded to this machine and installed on the emulator for each local.
const apkDrop = $('#apk-drop');
apkDrop.addEventListener('click', () => $('#apk-input').click());
apkDrop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') $('#apk-input').click(); });
apkDrop.addEventListener('dragover', e => { e.preventDefault(); apkDrop.classList.add('over'); });
apkDrop.addEventListener('dragleave', () => apkDrop.classList.remove('over'));
apkDrop.addEventListener('drop', e => { e.preventDefault(); apkDrop.classList.remove('over'); uploadApk(e.dataTransfer.files[0]); });
$('#apk-input').addEventListener('change', e => uploadApk(e.target.files[0]));

async function uploadApk(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.apk')) return setupError('That is not an APK file.');
  $('#apk-name').textContent = `Uploading ${file.name}…`;
  const r = await fetch(`/api/files?name=${encodeURIComponent(file.name)}`, { method: 'POST', body: file });
  S.apk = r.ok ? await r.json() : null;
  $('#apk-name').textContent = S.apk ? `${S.apk.name}, ${(S.apk.size / 1048576).toFixed(1)} MB, ready.` : 'The upload failed. Try again.';
  renderMeters();
}

function showDevice() {
  const a = S.info.machine.android;
  $('#apk-device').textContent = !a.adb ? 'adb was not found. Install the Android SDK platform tools.'
    : a.devices.length ? `Ready on ${a.devices.join(', ')}.` : 'No emulator or phone is connected. Start an emulator, or plug in a phone with USB debugging on.';
}

$('#site-check').addEventListener('change', e => {
  const v = $('#site-value'), needs = ['page_text', 'url_contains'].includes(e.target.value);
  v.disabled = !needs;
  v.placeholder = needs ? (e.target.value === 'page_text' ? 'Welcome aboard' : '/thank-you') : '';
});

const chosen = () => S.groups.flatMap(g => g.people.slice(0, S.counts[g.key] || 0));

function cells(parts, total) {
  const out = [];
  for (const [amount, cls] of parts) for (let i = 0; i < Math.round(Math.max(0, amount) / total * 24); i++) out.push(cls);
  return '<div class="cells">' + Array.from({ length: 24 }, (_, i) => `<i class="${out[i] || ''}"></i>`).join('') + '</div>';
}

function meter(label, value, parts, total, note) {
  return `<div class="meter"><div class="meter-head"><span>${label}</span><span class="v">${value}</span></div>${cells(parts, total)}<p>${note}</p></div>`;
}

const minutes = s => s < 90 ? `${Math.round(s)} SEC` : s < 5400 ? `${Math.round(s / 60)} MIN` : `${(s / 3600).toFixed(1)} H`;

function renderMeters() {
  const m = S.info.machine, team = chosen();
  const model = m.model, need = (model.size_gb || 2.5) + 0.4;
  $('#machine-name').textContent = [m.gpu ? m.gpu.name : 'No NVIDIA GPU found', m.memory ? `${Math.round(m.memory.total_gb)} GB memory` : ''].filter(Boolean).join(', ');
  let html = '';

  if (m.gpu) {
    const other = Math.max(0, m.gpu.used_gb - (model.loaded ? model.vram_gb : 0)), total = m.gpu.total_gb;
    const fits = other + need <= total;
    html += meter('GPU MEMORY', `${(other + need).toFixed(1)} / ${total.toFixed(0)} GB`, [[other, 'c'], [need, 'a']], total,
      fits ? `${esc(model.name)} needs about ${need.toFixed(1)} GB${model.loaded ? ' and is already loaded' : ''}. Other apps are using ${other.toFixed(1)} GB.`
        : `Not enough free GPU memory, so part of the model will run on the processor. Slower, but it works. Closing other GPU apps helps.`);
  } else {
    html += meter('GPU MEMORY', 'NONE', [], 1, 'No NVIDIA GPU found, so the model runs on the processor. Slower, but it works.');
  }

  if (m.memory) {
    const total = m.memory.total_gb, used = m.memory.used_gb, browser = team.length ? 0.6 : 0;
    html += meter('MEMORY', `${(used + browser).toFixed(1)} / ${total.toFixed(0)} GB`, [[used, 'c'], [browser, 'a']], total,
      team.length ? 'Chrome for the local who is working, about 0.6 GB. One at a time.' : 'Nothing extra until someone is chosen.');
  }

  const pace = m.pace, n = days().length;
  const typical = n * team.reduce((s, p) => s + Math.min(p.limits.patience_steps, pace.steps_per_task) * pace.secs_per_step, 0);
  const worst = n * team.reduce((s, p) => s + p.limits.patience_steps * pace.secs_per_step, 0);
  html += meter('TIME', team.length ? `ABOUT ${minutes(typical)}` : '0', [[typical, 'a'], [worst - typical, 'b']], Math.max(worst, 1),
    team.length ? `${team.length} local${team.length === 1 ? '' : 's'}${n > 1 ? ` on ${n} days` : ''}, one at a time. Up to ${minutes(worst).toLowerCase()} if everyone uses all their patience. ` +
      (pace.measured ? `${pace.secs_per_step} seconds a step, measured on this machine.` : 'Estimated at 6 seconds a step until a day has run here.')
      : 'Choose who goes out.');
  $('#meters').innerHTML = html;

  showDevice();
  const android = m.android || { adb: false, devices: [] };
  const problem = !model.reachable ? 'Ollama is not running. Start it, then come back to this page.'
    : !model.installed ? `The model is not downloaded yet. Run: ollama pull ${model.name}`
    : S.kind === 'apk' && !android.devices.length ? 'Start an Android emulator or connect a phone first.' : '';
  setupError(problem);
  $('#start').disabled = S.running || !team.length || !!problem || (S.kind === 'apk' && !S.apk);
  $('#start').textContent = S.running ? 'A DAY IS RUNNING' : team.length ? `START THE DAY WITH ${team.length}` : 'CHOOSE SOMEONE FIRST';
}

function setupError(text) {
  const el = $('#setup-error');
  el.hidden = !text;
  el.textContent = text;
}

async function refreshMachine() {
  S.info = await getJSON('/api/town');
  buildSetup();
  buildWhen();
}

// Files the locals keep on their phone for upload tasks.
const drop = $('#file-drop');
drop.addEventListener('click', () => $('#file-input').click());
drop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') $('#file-input').click(); });
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('over'); upload(e.dataTransfer.files); });
$('#file-input').addEventListener('change', e => upload(e.target.files));

async function upload(files) {
  for (const f of files) {
    const r = await fetch(`/api/files?name=${encodeURIComponent(f.name)}`, { method: 'POST', body: f });
    if (r.ok) S.files.push(await r.json());
  }
  $('#file-list').textContent = S.files.length ? S.files.map(f => f.name).join(', ') : 'Drop files here if the task needs something to upload.';
}

// ---------- When: one day, or a year in twelve days ----------

const days = () => S.when.mode === 'year' ? S.info.calendar.sample : [S.when.date];
const shortDate = iso => new Date(iso + 'T12:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short' });

function buildWhen() {
  const cal = S.info.calendar, input = $('#when-date');
  if (!cal.years.length) { $('#when-label').textContent = 'No calendar found in year/.'; return; }
  input.min = `${cal.years[0]}-01-01`;
  input.max = `${cal.years[cal.years.length - 1]}-12-31`;
  S.when.date = S.when.date || cal.default;
  input.value = S.when.date;
  const picks = $('#when-picks');
  picks.innerHTML = '';
  const add = (label, on, act) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'pick' + (on ? ' on' : ''); b.textContent = label.toUpperCase();
    b.addEventListener('click', act);
    picks.append(b);
  };
  for (const p of cal.picks) add(p.label, S.when.mode === 'one' && S.when.date === p.date, () => setWhen('one', p.date));
  add(`A year in ${cal.sample.length} days`, S.when.mode === 'year', () => setWhen(S.when.mode === 'year' ? 'one' : 'year'));
  input.disabled = S.when.mode === 'year';
  previewWhen();
}

function setWhen(mode, date) {
  S.when.mode = mode;
  if (date) S.when.date = date;
  buildWhen();
  renderMeters();
}

async function previewWhen() {
  const label = $('#when-label');
  if (S.when.mode === 'year') {
    label.textContent = `${S.info.calendar.sample.length} days, one after another: ` + S.info.calendar.sample.map(shortDate).join(', ');
    return;
  }
  const r = await fetch(`/api/today?date=${S.when.date}&pandemic=${S.when.pandemic}`);
  const t = await r.json();
  label.textContent = r.ok ? t.label : t.error;
}

$('#when-date').addEventListener('change', e => { if (e.target.value) setWhen('one', e.target.value); });
$('#pandemic').addEventListener('change', e => { S.when.pandemic = e.target.value; previewWhen(); });

$('#start').addEventListener('click', async () => {
  const body = { locals: chosen().map(p => p.id), watch: $('#watch').checked, dates: days(), pandemic: S.when.pandemic };
  const goal = { goal: $('#site-goal').value.trim(), check: $('#site-check').value, value: $('#site-value').value.trim(), files: S.files };
  if (S.kind === 'saved') body.task = $('#task-select').value;
  else if (S.kind === 'apk') body.app = { apk: S.apk ? S.apk.path : '', ...goal };
  else body.site = { url: $('#site-url').value.trim(), ...goal };
  const r = await fetch('/api/run', { method: 'POST', body: JSON.stringify(body) });
  const reply = await r.json();
  if (!r.ok) return setupError(reply.error || 'That did not start.');
  setupError('');
  setView('town');
});

// ---------- Past days ----------

const when = id => {
  const [d, t] = id.split('_');
  const date = new Date(`${d}T${t.slice(0, 2)}:${t.slice(2, 4)}:00`);
  return date.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

async function loadDays() {
  const days = await getJSON('/api/days'), list = $('#day-list');
  $('#days-note').textContent = days.length ? 'Open a day to see where everyone ended up and replay any step.' : 'No days yet. Set one up and it will be kept here.';
  list.innerHTML = '';
  for (const d of days) {
    const counts = {};
    Object.values(d.results || {}).forEach(k => { counts[k] = (counts[k] || 0) + 1; });
    const li = document.createElement('li');
    li.className = 'day-item';
    li.tabIndex = 0;
    li.innerHTML = `<span class="day-when">${esc(when(d.day))}</span>` +
      `<div><div class="t">${esc(d.task)}</div>${d.today ? `<div class="n">${esc(d.today)}</div>` : ''}<div class="n">${d.locals.map(who).map(esc).join(' · ')}</div></div>` +
      `<div class="chips">${Object.entries(counts).map(([k, n]) => `<b class="${k.replace(/ /g, '-')}">${n} ${esc(k)}</b>`).join('') || '<span>NOTHING SAVED</span>'}</div>`;
    const open = () => openDay(d.day);
    li.addEventListener('click', open);
    li.addEventListener('keydown', e => { if (e.key === 'Enter') open(); });
    list.append(li);
  }
}

async function openDay(id) {
  if (S.running) return setView('town');
  const { meta, entries } = await getJSON(`/api/days/${id}`);
  S.day = meta; S.entries = entries; S.results = meta.results || {}; S.filter = null;
  $('#verdict').hidden = true;
  TownView.startDay(meta.locals, true);
  TownView.setScene(meta.scene || null);
  TownView.select(null);
  entries.filter(e => e.type === 'event').forEach(e => TownView.event(e));
  $('#now').hidden = true;
  renderWho(); renderFeed(); hud();
  setView('town');
}

// ---------- Start ----------

(async function boot() {
  S.info = await getJSON('/api/town');
  S.groups = S.info.groups;
  for (const g of S.groups) for (const p of g.people) S.people.set(p.id, { ...p, group: g.key });
  TownView.init($('#canvas'), { people: S.people, onPick: pick });
  buildSetup();
  buildWhen();
  renderFeed();
  connect();
})();
