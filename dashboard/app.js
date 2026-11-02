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
  info: null, people: new Map(), groups: [], counts: {}, kind: 'saved', files: [],
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

function handle(e) {
  if (e.type === 'day' && e.phase === 'start') {
    S.day = e; S.running = true; S.entries = []; S.results = {}; S.filter = null;
    TownView.startDay(e.locals); TownView.select(null);
    renderWho(); renderFeed();
  } else if (e.type === 'day' && e.phase === 'end') {
    S.running = false; S.results = e.results;
    $('#now').hidden = true;
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
  const finished = Object.keys(S.results).length;
  $('#hud-day').textContent = `DAY · ${d.task}`.toUpperCase();
  $('#hud-sub').textContent = `${finished} of ${d.locals.length} finished · ${d.model}` + (S.running ? '' : ' · the day is over');
}

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
  for (const g of S.groups) {
    if (!(g.key in S.counts)) S.counts[g.key] = 1;
    const li = document.createElement('li');
    li.className = 'group';
    li.innerHTML = `<input type="checkbox" class="check" aria-label="${esc(g.label)}">` +
      `<div><div class="label">${esc(g.label)}</div><div class="names"></div></div>` +
      `<div class="stepper"><button type="button" aria-label="One fewer">-</button><output></output><button type="button" aria-label="One more">+</button></div>`;
    const [minus, plus] = li.querySelectorAll('.stepper button');
    const set = n => { S.counts[g.key] = Math.max(0, Math.min(g.people.length, n)); paint(); renderMeters(); };
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
    groups.append(li);
  }
  renderMeters();
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
  $('#start').disabled = S.kind === 'apk' || S.running;
}));

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

  const pace = m.pace, typical = team.reduce((s, p) => s + Math.min(p.limits.patience_steps, pace.steps_per_task) * pace.secs_per_step, 0);
  const worst = team.reduce((s, p) => s + p.limits.patience_steps * pace.secs_per_step, 0);
  html += meter('TIME', team.length ? `ABOUT ${minutes(typical)}` : '0', [[typical, 'a'], [worst - typical, 'b']], Math.max(worst, 1),
    team.length ? `${team.length} local${team.length === 1 ? '' : 's'}, one at a time. Up to ${minutes(worst).toLowerCase()} if everyone uses all their patience. ` +
      (pace.measured ? `${pace.secs_per_step} seconds a step, measured on this machine.` : 'Estimated at 6 seconds a step until a day has run here.')
      : 'Choose who goes out.');
  $('#meters').innerHTML = html;

  const problem = !model.reachable ? 'Ollama is not running. Start it, then come back to this page.'
    : !model.installed ? `The model is not downloaded yet. Run: ollama pull ${model.name}` : '';
  setupError(problem);
  $('#start').disabled = S.running || S.kind === 'apk' || !team.length || !!problem;
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

$('#start').addEventListener('click', async () => {
  const body = { locals: chosen().map(p => p.id), watch: $('#watch').checked };
  if (S.kind === 'saved') body.task = $('#task-select').value;
  else body.site = { url: $('#site-url').value.trim(), goal: $('#site-goal').value.trim(), check: $('#site-check').value,
    value: $('#site-value').value.trim(), files: S.files };
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
      `<div><div class="t">${esc(d.task)}</div><div class="n">${d.locals.map(who).map(esc).join(' · ')}</div></div>` +
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
  TownView.startDay(meta.locals, true);
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
  renderFeed();
  connect();
})();
