"""Watching a real person do a task: the same app, device and files a local gets, but a human's hands.

Record yourself once and it becomes the task's golden path: a local who leaves it was misled by the UI.
Record someone who does the job, standing in for one local, and `python -m town calibrate` turns their
misses, corrections and give up point into that local's limits. People are never named in a recording.
"""
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from . import tasks
from .people import ROOT
from .tasks import TASKS
from .web import Web

OBSERVED = ROOT / "study" / "observed"  # recordings of real people; git ignores this folder

# Runs inside the page: reports every tap, key and change with the control's visible words, named
# exactly the way a local sees it (town/web.py), so a person's path and a local's path can be compared.
RECORD = r"""(() => {
  if (window.__localsWatching) return;
  window.__localsWatching = true;
  const CONTROLS = 'a[href],button,input,select,textarea,[role=button],[role=link],[role=checkbox],[role=tab],[role=menuitem],[role=switch],[contenteditable=true]';
  const LOOSE = 'label,summary,[onclick],[tabindex]';
  const roleOf = el => {
    const tag = el.tagName.toLowerCase(), type = (el.type || '').toLowerCase();
    let role = el.getAttribute('role') || {a: 'link', button: 'button', select: 'dropdown', textarea: 'text box'}[tag] || tag;
    if (tag === 'input') role = {checkbox: 'checkbox', radio: 'radio', range: 'slider', file: 'file picker', submit: 'button', button: 'button'}[type] || 'text box';
    return role;
  };
  const named = el => {
    const type = (el.type || '').toLowerCase();
    const lines = (el.innerText || (type === 'submit' || type === 'button' ? el.value : '') || '')
      .split('\n').map(s => s.trim().replace(/\s+/g, ' ')).filter(Boolean);
    let hint = el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('placeholder') || '';
    if (!hint && el.labels && el.labels.length) hint = el.labels[0].innerText.trim();
    return { role: roleOf(el), text: lines.join(' ').slice(0, 300), hint: hint.slice(0, 160) };
  };
  // A tap counts as hitting something when it lands on a control, a label, or anything showing a hand cursor.
  const hit = target => {
    const el = target.closest(CONTROLS) || target.closest(LOOSE);
    if (el) return el;
    for (let n = target; n && n !== document.body; n = n.parentElement) if (getComputedStyle(n).cursor === 'pointer') return n;
    return null;
  };
  const send = e => { try { window.localsRecord(e); } catch (_) {} };
  document.addEventListener('pointerdown', e => {
    const el = hit(e.target);
    send({ kind: 'tap', control: !!el, ...(el ? named(el) : { role: '', text: '', hint: '' }), x: Math.round(e.clientX), y: Math.round(e.clientY) });
  }, true);
  document.addEventListener('keydown', e => {
    if (e.key === 'Backspace' || e.key === 'Delete') send({ kind: 'erase' });
    else if (e.key.length === 1) send({ kind: 'key' });
  }, true);
  document.addEventListener('change', e => {
    const el = e.target.closest(CONTROLS);
    if (el && ['dropdown', 'slider', 'checkbox', 'radio'].includes(roleOf(el))) send({ kind: 'set', control: true, ...named(el), value: String(el.value || '') });
  }, true);
  let lastScroll = 0;
  addEventListener('scroll', () => { const t = Date.now(); if (t - lastScroll > 1200) { lastScroll = t; send({ kind: 'scroll' }); } }, true);
})();"""


def norm(text):
    """A control's words as a comparable key: lower case, letters and digits only, the first six words."""
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower())[:6])


def name_of(item):
    return item.get("text") or item.get("hint") or ""


def golden_file(task):
    app_id, _, task_id = task.ref.partition(":")
    folder = TASKS / "mine" / "golden" if app_id.startswith("mine/") else TASKS / "golden"
    return folder / f"{app_id.removeprefix('mine/')}.{task_id}.json"


def golden_path(task):
    """The controls you used, in order, when you did the task yourself; None if you have not recorded it."""
    path = golden_file(task)
    if not path.exists():
        return None
    run = json.loads(path.read_text(encoding="utf-8"))
    steps = []
    for e in run["events"]:
        key = norm(name_of(e)) if e["kind"] in ("tap", "set") and e.get("control") else ""
        if key and (not steps or steps[-1][0] != key):  # tapping the same thing twice is one step
            steps.append((key, name_of(e)))
    return steps


class Commands:
    """Lets whoever is watching say what happened, from the terminal: d done, g gave up, s stop."""

    def __init__(self):
        self.said = None
        if sys.stdin and sys.stdin.isatty():
            threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in sys.stdin:
            word = line.strip().lower()[:1]
            if word in ("d", "g", "s"):
                self.said = {"d": "SAYS DONE", "g": "GAVE UP", "s": "STOPPED"}[word]
                return


def watch_web(task, device, inputs, folder, minutes):
    events, start = [], time.time()
    stamp = lambda: round(time.time() - start, 2)
    web = Web(task, device, inputs, folder, watch=True)
    web.slow_mo = 0
    with web:
        page = web.page
        page.expose_binding("localsRecord", lambda source, e: events.append({**e, "t": stamp()}))
        page.on("framenavigated", lambda f: f == page.main_frame and events.append({"kind": "nav", "url": f.url, "t": stamp()}))
        page.add_init_script(RECORD)
        page.reload(wait_until="networkidle")
        start = time.time()
        events.clear()
        print("  Recording now. Hand it over.", flush=True)
        commands, shots, outcome = Commands(), 0, None
        try:
            while outcome is None:
                page.wait_for_timeout(400)
                web.collect()
                taps = sum(e["kind"] == "tap" for e in events)
                if taps > shots:  # a screenshot after every tap, for replay
                    shots = taps
                    web.snapshot(folder / f"step-{shots:02d}.png")
                ok, _ = tasks.check(task, web, inputs)
                outcome = "DONE" if ok and task.done else commands.said
                if outcome is None and time.time() - start > minutes * 60:
                    outcome = "STOPPED"
        except KeyboardInterrupt:
            outcome = "STOPPED"
        except PlaywrightError as e:
            if "closed" not in str(e).lower():
                raise
            outcome = "GAVE UP"  # they closed the browser before it was done
    return outcome, events, round(time.time() - start, 1)


# ---------- Android: touches read from the device's input events ----------

class Touches:
    """Fingers on an Android screen, read with getevent, in screen pixels. Taps typed on the on-screen
    keyboard are counted as keys; corrections there cannot be seen, only on a hardware keyboard."""
    TOUCH = re.compile(r"(EV_\w+)\s+(\w+)\s+(\w+)\s*$")

    def __init__(self, adb):
        self.adb, self.queue, self.lock = adb, [], threading.Lock()
        info = subprocess.run([adb, "shell", "getevent", "-lp"], capture_output=True, text=True, timeout=30).stdout
        self.max_x = self.max_y = None
        for block in info.split("add device")[1:]:
            mx = re.search(r"ABS_MT_POSITION_X\s*:.*?max (\d+)", block)
            my = re.search(r"ABS_MT_POSITION_Y\s*:.*?max (\d+)", block)
            if mx and my:
                self.max_x, self.max_y = int(mx.group(1)), int(my.group(1))
                break
        if self.max_x is None:
            raise RuntimeError("No touch screen found on the device.")
        size = subprocess.run([adb, "shell", "wm", "size"], capture_output=True, text=True, timeout=30).stdout
        sizes = re.findall(r"(\d+)x(\d+)", size)
        self.w, self.h = map(int, sizes[-1])  # an override size, if one is set, is what apps see
        self.proc = subprocess.Popen([adb, "shell", "getevent", "-lt"], stdout=subprocess.PIPE, text=True, errors="replace")
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        x = y = down = None
        finger = False
        for line in self.proc.stdout:
            m = self.TOUCH.search(line)
            if not m:
                continue
            kind, code, value = m.groups()
            now = time.time()
            if code == "ABS_MT_POSITION_X":
                x = int(value, 16) * self.w // (self.max_x + 1)
            elif code == "ABS_MT_POSITION_Y":
                y = int(value, 16) * self.h // (self.max_y + 1)
            elif kind == "EV_SYN" and down is None and x is not None and finger:
                down = (x, y, now)
            if code in ("BTN_TOUCH", "ABS_MT_TRACKING_ID"):
                lifted = value in ("UP", "ffffffff")
                finger = not lifted
                if lifted and down:
                    self._put({"kind": "touch", "x": down[0], "y": down[1], "x1": x, "y1": y, "secs": now - down[2]})
                    down = None
            elif kind == "EV_KEY" and value == "DOWN":
                if code == "KEY_BACK":
                    self._put({"kind": "back"})
                elif code in ("KEY_BACKSPACE", "KEY_DELETE"):
                    self._put({"kind": "erase"})
                elif re.fullmatch(r"KEY_([A-Z0-9]|SPACE|DOT|COMMA)", code):
                    self._put({"kind": "key"})

    def _put(self, e):
        with self.lock:
            self.queue.append(e)

    def take(self):
        with self.lock:
            out, self.queue = self.queue, []
        return out

    def close(self):
        self.proc.kill()


def keyboard_up(droid):
    out = droid.sh("shell", "dumpsys", "input_method")
    return bool(re.search(r"mInputShown=true|mIsInputViewShown=true|isInputViewShown=true", out))


def watch_android(task, inputs, folder, minutes):
    from .android import Android
    events, outcome = [], None
    with Android(task, "phone", inputs, folder) as droid:
        touches = Touches(droid.adb)
        screen, keys_up = droid.see(look=False), False
        start, commands, shots = time.time(), Commands(), 0
        print("  Recording now. Hand it over.", flush=True)

        class Seen:  # the done check reads the last screen instead of dumping it again
            downloads = []
            text = staticmethod(lambda: droid.last_text)
            location = staticmethod(droid.location)
        try:
            while outcome is None:
                for e in touches.take():
                    e["t"] = round(time.time() - start, 2)
                    if e["kind"] != "touch":
                        events.append(e)
                        continue
                    dx, dy = abs(e["x1"] - e["x"]), abs(e["y1"] - e["y"])
                    if dx + dy > 0.06 * touches.h:
                        # A sideways swipe in from the edge is the back gesture; anything else scrolls.
                        edge = min(e["x"], touches.w - e["x"]) < 0.05 * touches.w and dx > dy
                        events.append({"kind": "back" if edge else "scroll", "t": e["t"]})
                        continue
                    item = next((i for i in screen["items"] if box_has(droid.crops[i["id"]], e["x"], e["y"])), None)
                    if item is None and keys_up and e["y"] > 0.55 * touches.h:
                        events.append({"kind": "key", "t": e["t"]})  # a key on the on-screen keyboard
                        continue
                    events.append({"kind": "tap", "control": item is not None, "t": e["t"], "x": e["x"], "y": e["y"],
                                   **({"role": item["role"], "text": item["text"], "hint": item["hint"]} if item else
                                      {"role": "", "text": "", "hint": ""})})
                    shots += 1
                    droid.snapshot(folder / f"step-{shots:02d}.png")
                screen, keys_up = droid.see(look=False), keyboard_up(droid)
                ok, _ = tasks.check(task, Seen, inputs)
                outcome = "DONE" if ok and task.done else commands.said
                if outcome is None and time.time() - start > minutes * 60:
                    outcome = "STOPPED"
        except KeyboardInterrupt:
            outcome = "STOPPED"
        finally:
            touches.close()
    return outcome, events, round(time.time() - start, 1)


def box_has(box, x, y):
    x0, y0, x1, y1 = box
    return x0 <= x <= x1 and y0 <= y <= y1


def watch(task, golden=False, local=None, device="phone", minutes=15):
    """Records one person doing the task, saves it, and returns (path, run)."""
    when = datetime.now()
    folder = ROOT / "runs" / "watched" / when.strftime("%Y-%m-%d_%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)
    inputs = tasks.make_files(task, folder / "device")
    who = "you, for the golden path" if golden else f"someone standing in for {local.name}" if local else "someone"
    print(f"WATCHING {who} · {task.app}: {task.id} · on a {device}")
    print(f"  The task: {' '.join(task.story.split())}")
    print("  Recording starts when the app opens. Type d (they say it is done), g (they gave up) or s (stop),"
          " then Enter." + (" Closing the browser counts as giving up." if task.platform != "android" else ""))
    if task.platform == "android":
        outcome, events, secs = watch_android(task, inputs, folder, minutes)
    else:
        outcome, events, secs = watch_web(task, device, inputs, folder, minutes)
    run = {"task": task.ref, "app": task.app, "platform": task.platform, "device": device,
           "for": local.id if local else None, "golden": golden, "when": when.isoformat(timespec="seconds"),
           "outcome": outcome, "secs": secs, "events": events}
    if golden:
        path = golden_file(task)
    else:
        path = OBSERVED / (local.id if local else "anyone") / f"{task.ref.replace('/', '_').replace(':', '.')}_{when:%Y-%m-%d_%H%M%S}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, indent=1), encoding="utf-8")
    return path, run
