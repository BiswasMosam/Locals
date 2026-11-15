"""A session: the one day that can run at a time, in a process of its own, and everyone watching it.

    python -m town.session        # the worker; what a Session starts, not something to type

The day used to run on a thread inside the web server of a dashboard in the browser, since removed. Stop was a flag the day read between
steps, so a model call that hung held the day for up to four minutes, and nothing could end the Chrome and
adb children a run leaves behind. Now the day is a worker process. Whoever shows it (the window, town/app.py)
holds a Session, which starts the worker, passes on what it reports, and can end it.

The worker reports on its standard output, one JSON object per line: the same entries the feed has always
written (town/feed.py) and the day and year markers from town/day.py. Everything the engine prints for a
person goes to a transcript in runs/_session/ instead. What to run is a small file beside that transcript,
and stop is another file appearing next to it. Stop was first a line down the worker's input, and the first
real day never began: on Windows a thread waiting to read a pipe held up the rest of the process, so the
worker hung before its first report with every test green (15 Nov 2026). The worker reads no pipe now.

Stop asks first, so a day that can end cleanly does, with every file written as before. If the worker has
not gone when the grace runs out, it and everything it started are killed, and the Session writes down
what the worker could not: the local who was at work is marked STOPPED, and the day is saved with the
results it had, so a stopped day is still in the list of past days.

A talk given to a room (town/room.py) runs the same way, as a spec of kind "talk": it calls the model for
minutes on end, so it needs the same Stop. Its entries have the type "talk". A talk that is stopped keeps
nothing: who remembered the point and the marks are asked at the end, and half a talk has neither.
"""
import contextlib
import importlib.util
import json
import os
import queue
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path

from . import people, tasks, year
from .people import ROOT

RUNS = ROOT / "runs"
OUTCOMES = {"DONE", "SAYS DONE", "WRONG DONE", "GAVE UP", "ASKED", "STOPPED", "ERROR"}
APK = re.compile(r"runs/_uploads/[0-9a-f]{8}/[A-Za-z0-9._-]+\.apk")
KEPT_FILE = re.compile(r"runs/_uploads/[0-9a-f]{8}/[A-Za-z0-9._-]+")
# The worker keeps a console of its own with no window, and its children inherit it: nothing flashes up
# behind a window, and Ctrl+C in the terminal that opened the window reaches the window only.
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


class Busy(RuntimeError):
    pass


def kill_tree(pid):
    """Ends a process and everything it started: the browser, its driver, adb."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def keep_file(source, runs=RUNS):
    """Copies a file somebody chose into runs/_uploads/, where a task card may point at it, and says where it went.
    The folder's name is random, so two files with one name never meet and a card cannot name a path outside it."""
    source = Path(source)
    if not source.is_file():
        raise ValueError(f"{source.name} is not a file that can be read.")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", source.name)[:80] or "file"
    folder = Path(runs) / "_uploads" / secrets.token_hex(4)
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, folder / name)
    return {"name": name, "path": (folder / name).relative_to(ROOT).as_posix(), "size": (folder / name).stat().st_size}


def parse_days(values):
    days = sorted({date.fromisoformat(v) for v in values})
    if not 1 <= len(days) <= 12:
        raise ValueError("Choose between one and twelve days.")
    for d in days:
        year.data(d.year)  # raises if there is no calendar for that year
    return days


def plan(body):
    """What somebody asked for in the setup screen, checked, as the spec a worker runs. Raises ValueError
    with a sentence for the person when it cannot be run. A new site or app is saved as a task card on the way."""
    ids = [i for i in body.get("locals", []) if re.fullmatch(r"[a-z0-9_-]+", i) and (people.PEOPLE / f"{i}.toml").exists()]
    if not ids:
        raise ValueError("Choose at least one local.")
    try:
        site, app = body.get("site"), body.get("app")
        if site:
            ref = tasks.add_site(site["url"], site["goal"], site["check"], site.get("value", ""), site.get("files", []))
        elif app:
            if not APK.fullmatch(app.get("apk", "")):
                raise ValueError("Drop the app's APK file first.")
            ref = tasks.add_app(app["apk"], app["goal"], app["check"], app.get("value", ""), app.get("files", []))
        else:
            ref = body["task"]
        tasks.load(ref)  # here, so a card that cannot be run is refused before a worker is started for it
        days = parse_days(body.get("dates") or [date.today().isoformat()])
    except KeyError as e:
        raise ValueError(f"Missing: {e.args[0]}") from None
    except SystemExit as e:
        raise ValueError(str(e)) from None
    return {"ref": ref, "locals": ids, "dates": [d.isoformat() for d in days], "watch": bool(body.get("watch")),
            "pandemic": body.get("pandemic") if body.get("pandemic") in year.PANDEMIC else None,
            "take": body.get("take", True) is not False, "seed": 7}


def plan_talk(body):
    """What somebody asked for on the rooms page, checked, as the spec a worker runs. Raises ValueError with a
    sentence for the person when the talk cannot be given."""
    from . import room as rooms, talk as talks
    place = rooms.rooms().get(body.get("room"))
    if place is None:
        raise ValueError("Choose a room.")
    files = [f for f in body.get("files") or [] if isinstance(f, str)]
    if not files or any(not KEPT_FILE.fullmatch(f) or not (ROOT / f).is_file() for f in files):
        raise ValueError("Drop the talk's files first: a deck, a script or a recording.")
    kinds = [Path(f).suffix.lower() for f in files]
    decks, speeches = sum(k in talks.DECK for k in kinds), sum(k in talks.AUDIO | talks.SCRIPT for k in kinds)
    if decks + speeches != len(files) or decks > 1 or speeches > 1:
        raise ValueError("Give a deck (.pdf or .pptx), a speech (.txt, .md or a recording like .m4a), or one of each.")
    if any(k in talks.AUDIO for k in kinds) and importlib.util.find_spec("faster_whisper") is None:
        raise ValueError("Reading a recording needs faster-whisper, which is not installed here. "
                         "Give the script as a .txt file, or run: pip install faster-whisper")
    try:
        minutes = float(body.get("minutes") or 0)
    except (TypeError, ValueError):
        minutes = -1
    if not 0 <= minutes <= 180:
        raise ValueError("How long the talk runs is a number of minutes, like 10.")
    words = lambda key: " ".join(str(body.get(key) or "").split())[:300]
    return {"kind": "talk", "room": place["id"], "files": files, "minutes": minutes or None, "point": words("point"),
            "about": words("about"), "grade": body.get("grade", True) is not False, "seed": 7}


class Session:
    def __init__(self, runs=RUNS, command=None, grace=12.0):
        self.runs = Path(runs)
        self.command = command or [sys.executable, "-m", "town.session"]
        self.grace = grace  # seconds a stopped day gets to end by itself; a step in progress is finished first
        self.lock = threading.Lock()
        self.watchers, self.log = [], []
        self.proc, self.running, self.stopping = None, False, False
        self.day, self.error, self.transcript, self._spec, self._stop = None, None, None, None, None
        self._forget()

    def _forget(self):
        self._open, self._results, self._at_work, self._shot = None, {}, None, None
        self._summary, self._task, self._last = [], "", None
        self._kind, self._talk = "day", ""

    # ---------- watching ----------

    def emit(self, entry):
        with self.lock:
            self.log.append(entry)
            for q in self.watchers:
                q.put(entry)

    def watch(self):
        """A queue of everything from now on, and everything this day has said so far."""
        q = queue.Queue()
        with self.lock:
            self.watchers.append(q)
            return q, list(self.log)

    def unwatch(self, q):
        with self.lock:
            if q in self.watchers:
                self.watchers.remove(q)

    def busy(self):
        return self.running

    # ---------- starting and stopping ----------

    def start(self, spec):
        with self.lock:
            if self.running:
                raise Busy("A day is already running.")
            self.running, self.stopping, self.error, self.log = True, False, None, []
            self._forget()
            self._kind = spec.get("kind", "day")
        try:
            folder = self.runs / "_session"
            folder.mkdir(parents=True, exist_ok=True)
            self.transcript = folder / f"{datetime.now():%Y-%m-%d_%H%M%S}.log"
            self._spec, self._stop = self.transcript.with_suffix(".json"), self.transcript.with_suffix(".stop")
            self._stop.unlink(missing_ok=True)
            self._spec.write_text(json.dumps({**spec, "runs": str(self.runs), "stop": str(self._stop), "keeper": os.getpid()}),
                                  encoding="utf-8")
            own = {"creationflags": NO_WINDOW} if sys.platform == "win32" else {"start_new_session": True}
            with self.transcript.open("w", encoding="utf-8") as words:
                proc = subprocess.Popen([*self.command, str(self._spec)], cwd=ROOT, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=words, text=True, encoding="utf-8", errors="replace",
                                        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}, **own)
        except OSError:
            self.running = False
            raise
        self.proc = proc
        threading.Thread(target=self._follow, args=(proc,), daemon=True).start()

    def stop(self, grace=None):
        """Asks the day to end, and ends it if it has not by the time the grace runs out."""
        with self.lock:
            proc = self.proc
            if not self.running or proc is None or self.stopping:
                return
            self.stopping = True
        with contextlib.suppress(OSError):
            self._stop.touch()
        threading.Thread(target=self._enforce, args=(proc, self.grace if grace is None else grace), daemon=True).start()

    def _enforce(self, proc, grace):
        try:
            proc.wait(grace)
        except subprocess.TimeoutExpired:
            kill_tree(proc.pid)

    def close(self, grace=3.0):
        """For when whoever holds the session is leaving: nothing is left running behind it."""
        self.stop(grace)
        proc = self.proc
        if proc is not None:
            try:
                proc.wait(grace + 10)
            except subprocess.TimeoutExpired:
                kill_tree(proc.pid)

    # ---------- following the worker ----------

    def _follow(self, proc):
        for line in proc.stdout:
            try:
                entry = json.loads(line)
            except ValueError:
                continue  # not ours: something wrote to the worker's output that was not the engine
            if not isinstance(entry, dict):
                continue
            if entry.get("type") in ("year", "talk") and entry.get("phase") == "end":
                # Held back until the worker has gone, so whoever hears that the day is over can start the next at once.
                self._last = entry
                break
            self._note(entry)
            self.emit(entry)
        try:
            proc.wait(10 if self._last else None)
        except subprocess.TimeoutExpired:
            kill_tree(proc.pid)  # finished, but something it started will not let it leave
            proc.wait()
        with contextlib.suppress(OSError):
            proc.stdout.close()
        for left in (self._spec, self._stop):
            with contextlib.suppress(OSError):
                left.unlink(missing_ok=True)
        if self._last is None:
            self._mend(proc)
        self.running = False
        self.emit(self._last)

    def _note(self, entry):
        """Keeps just enough of what went past to finish the record if the worker cannot."""
        kind = entry.get("type")
        if kind == "year":
            self._task = entry.get("task", "")
        elif kind == "day" and entry.get("phase") == "start":
            self._open = {k: v for k, v in entry.items() if k not in ("type", "phase")}
            self.day, self._results, self._at_work = entry.get("day"), {}, None
        elif kind == "day":
            self._open = None
            self._summary.append({"date": entry.get("date"), "label": entry.get("today"), "day": entry.get("day"),
                                  "results": entry.get("results", {})})
        elif kind == "talk":
            self._talk = entry.get("talk") or self._talk
        elif "local" in entry:
            self._shot = entry.get("shot")
            if kind == "event" and entry.get("kind") in OUTCOMES:
                self._results[entry["local"]] = entry["kind"]
                self._at_work = None
            elif entry["local"] not in self._results:  # what comes after an outcome is their take, not more work
                self._at_work = entry["local"]

    def _mend(self, proc):
        """The worker went without closing the day: it was killed after a stop it could not answer, or it fell over."""
        kind = "STOPPED" if self.stopping else "ERROR"
        if kind == "ERROR":
            self.error = f"The engine stopped by itself (exit {proc.returncode}). {self._last_words()}".strip()
        if self._kind == "talk":
            self._last = {"type": "talk", "phase": "end", "talk": self._talk, "stopped": self.stopping, "ended_at": time.time()}
            if self.error:
                self._last["error"] = self.error
            return
        meta = self._open
        if meta is not None:
            folder, results = self.runs / meta["day"], dict(self._results)
            who = self._at_work
            if who:
                entry = {"type": "event", "local": who, "kind": kind,
                         "says": "The day was stopped." if self.stopping else self.error, "at": "", "shot": self._shot}
                (folder / who).mkdir(parents=True, exist_ok=True)
                with (folder / who / "feed.jsonl").open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
                results[who] = kind
                self.emit(entry)
            runs = {}
            for i in results:
                try:
                    runs[i] = json.loads((folder / i / "run.json").read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    pass  # the local who was cut off has no summary of their run
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "day.json").write_text(json.dumps({**meta, "results": results, "runs": runs, "panel": None}, indent=2),
                                             encoding="utf-8")
            self.emit({"type": "day", "phase": "end", **meta, "results": results, "panel": None, "ended_at": time.time()})
            self._summary.append({"date": meta.get("date"), "label": meta.get("today"), "day": meta["day"], "results": results})
        self._last = {"type": "year", "phase": "end", "task": self._task, "days": self._summary, "ended_at": time.time()}
        if self.error:
            self._last["error"] = self.error

    def _last_words(self):
        try:
            lines = [l.strip() for l in self.transcript.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
        except OSError:
            return ""
        said = f"Its last words: {lines[-1][:200]} " if lines else ""
        return f"{said}(runs/_session/{self.transcript.name})"


# ---------- the worker ----------

def work(spec, send, stop):
    """Runs what a spec asks for, reporting through send, until it is over or stop is set."""
    if spec.get("kind") == "talk":
        return hear(spec, send, stop)
    from . import day
    task = tasks.load(spec["ref"])
    who = [people.load(i) for i in spec["locals"]]
    days = [date.fromisoformat(d) for d in spec["dates"]]
    return day.run_year(task, who, days, Path(spec["runs"]), spec.get("watch", False), spec.get("seed", 7), send, stop,
                        spec.get("pandemic"), spec.get("take", True))


def hear(spec, send, stop):
    """Gives the talk a spec asks for to its room, reporting through send. Nothing is written until it is all
    over, marks included, so a talk that was stopped leaves nothing behind."""
    from . import room as rooms, talk as talks
    place = rooms.load(spec["room"])
    files = [ROOT / f for f in spec["files"]]
    out = Path(spec["runs"]) / "rooms" / f"{datetime.now():%Y-%m-%d_%H%M%S}_{place['id']}"
    send({"type": "talk", "phase": "reading", "talk": out.name, "room": place["id"], "name": place["name"],
          "files": [f.name for f in files]})
    end = {"type": "talk", "phase": "end", "talk": out.name}
    try:
        talk = talks.load(files, spec.get("minutes"))
        about, seed = spec.get("about", ""), spec.get("seed", 7)
        result, listeners = rooms.listen(place, talk, about, spec.get("point", ""), seed, None, send, stop)
        if spec.get("grade", True):
            from .grade import grade
            result["grade"] = grade(place, result, listeners, talk.recorded, about, seed, send, stop)
        out.mkdir(parents=True, exist_ok=True)
        (out / "room.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    except rooms.Stopped:
        end["stopped"] = True
    except SystemExit as e:  # how the engine says a file cannot be read, in a sentence meant for a person
        end["error"] = str(e)
    send({**end, "ended_at": time.time()})


def gone(pid):
    """Whether a process has ended."""
    if sys.platform == "win32":
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE: only to ask whether it has ended
        if not handle:
            return True
        try:
            return kernel.WaitForSingleObject(handle, 0) == 0
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        pass
    return False


def main():
    reports = sys.stdout
    sys.stdout = sys.stderr  # the engine prints for a person; that belongs in the transcript, not among the reports
    for stream in (reports, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    stop, writing = threading.Event(), threading.Lock()

    def send(entry):
        try:
            with writing:
                reports.write(json.dumps(entry) + "\n")
                reports.flush()
        except (OSError, ValueError):
            stop.set()  # nobody is reading any more

    def listen():
        asked, keeper = Path(spec["stop"]), spec.get("keeper")
        while not asked.exists():
            if keeper and gone(keeper):
                # Whoever started us is gone and cannot end us. End the day cleanly if a minute is enough
                # for that, and otherwise leave nothing running on this machine.
                stop.set()
                time.sleep(60)
                kill_tree(os.getpid())
            time.sleep(0.25)
        stop.set()

    threading.Thread(target=listen, daemon=True).start()
    work(spec, send, stop)


if __name__ == "__main__":
    main()
