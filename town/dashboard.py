"""The dashboard: setup, the town and the feed in your browser, served from this machine only."""
import json
import queue
import re
import secrets
import threading
import webbrowser
from datetime import date, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import day, machine, mind, people, tasks, year
from .people import ROOT

WEB = ROOT / "dashboard"
RUNS = ROOT / "runs"
UPLOADS = RUNS / "_uploads"
FONTS = ROOT / "brand" / "fonts"
DAY_ID = re.compile(r"\d{4}-\d{2}-\d{2}_\d{6}")


class Town:
    """The one day that can run at a time, and everyone watching it."""

    def __init__(self):
        self.lock = threading.Lock()
        self.watchers, self.log = [], []
        self.thread, self.stop, self.day = None, threading.Event(), None

    def emit(self, entry):
        with self.lock:
            self.log.append(entry)
            for q in self.watchers:
                q.put(entry)

    def watch(self):
        q = queue.Queue()
        with self.lock:
            self.watchers.append(q)
            return q, list(self.log)

    def unwatch(self, q):
        with self.lock:
            if q in self.watchers:
                self.watchers.remove(q)

    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, task, who, watch, days, pandemic):
        with self.lock:
            self.log = []
        self.stop.clear()
        self.day = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.thread = threading.Thread(target=day.run_year, args=(task, who, days, RUNS, watch, 7, self.emit, self.stop, pandemic),
                                       daemon=True)
        self.thread.start()


TOWN = Town()


def profile_title(profile):
    path = ROOT / profile
    first = path.read_text(encoding="utf-8").splitlines()[0] if path.exists() else ""
    return first.lstrip("# ").strip() or Path(profile).stem


def town_info():
    groups = {}
    for l in people.everyone():
        key = Path(l.profile).stem
        group = groups.setdefault(key, {"key": key, "label": profile_title(l.profile), "profile": l.profile, "people": []})
        group["people"].append({"id": l.id, "number": l.number, "name": l.name, "age": l.age, "job": l.job,
                                "status": l.status, "situation": l.situation, "habits": l.habits, "limits": vars(l.limits)})
    years = year.years()
    now = date.today()
    calendar = {"years": years, "picks": year.picks(years[-1]) if years else [],
                "sample": [d.isoformat() for d in year.sample(years[-1])] if years else [],
                "default": (now if now.year in years else date(years[-1], 2, 10)).isoformat() if years else None}
    return {"groups": list(groups.values()), "tasks": tasks.catalogue(), "busy": TOWN.busy(), "day": TOWN.day,
            "calendar": calendar,
            "machine": {"gpu": machine.gpu(), "memory": machine.memory(), "model": machine.model(), "pace": machine.pace()}}


def parse_days(values):
    days = sorted({date.fromisoformat(v) for v in values})
    if not 1 <= len(days) <= 12:
        raise ValueError("Choose between one and twelve days.")
    for d in days:
        year.data(d.year)  # raises if there is no calendar for that year
    return days


def days():
    out = []
    for meta in sorted(RUNS.glob("*/day.json"), reverse=True)[:40]:
        out.append(json.loads(meta.read_text(encoding="utf-8")))
    return out


def day_log(day_id):
    folder = RUNS / day_id
    meta = json.loads((folder / "day.json").read_text(encoding="utf-8"))
    entries = []
    for local_id in meta["locals"]:
        feed = folder / local_id / "feed.jsonl"
        if feed.exists():
            entries += [e for e in map(json.loads, feed.open(encoding="utf-8")) if "type" in e]
    return {"meta": meta, "entries": entries}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, *args):
        pass

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, base, relative):
        path = (base / unquote(relative)).resolve()
        if not path.is_relative_to(base.resolve()) or not path.is_file():
            return self.send_error(404)
        kind = {".png": "image/png", ".woff2": "font/woff2", ".jpg": "image/jpeg"}.get(path.suffix, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/town":
            return self.send_json(town_info())
        if path == "/api/days":
            return self.send_json(days())
        if path.startswith("/api/days/"):
            day_id = path.rsplit("/", 1)[1]
            if not DAY_ID.fullmatch(day_id) or not (RUNS / day_id / "day.json").exists():
                return self.send_error(404)
            return self.send_json(day_log(day_id))
        if path == "/api/today":
            query = parse_qs(urlparse(self.path).query)
            try:
                t = year.today(date.fromisoformat(query.get("date", [""])[0]), query.get("pandemic", [""])[0] or None)
            except ValueError as e:
                return self.send_json({"error": str(e)}, 400)
            return self.send_json(t.scene())
        if path == "/api/events":
            return self.events()
        if path.startswith("/runs/"):
            return self.send_file(RUNS, path[len("/runs/"):])
        if path.startswith("/fonts/"):
            return self.send_file(FONTS, path[len("/fonts/"):])
        return super().do_GET()

    def events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        q, backlog = TOWN.watch()
        try:
            for entry in backlog:
                self.wfile.write(f"data: {json.dumps(entry)}\n\n".encode())
            self.wfile.flush()
            while True:
                try:
                    message = f"data: {json.dumps(q.get(timeout=15))}\n\n"
                except queue.Empty:
                    message = ": still here\n\n"
                self.wfile.write(message.encode())
                self.wfile.flush()
        except OSError:
            pass
        finally:
            TOWN.unwatch(q)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        if parsed.path == "/api/files":
            return self.upload(parse_qs(parsed.query).get("name", ["file"])[0], self.rfile.read(length))
        body = json.loads(self.rfile.read(length) or b"{}")
        if parsed.path == "/api/stop":
            TOWN.stop.set()
            return self.send_json({"ok": True})
        if parsed.path == "/api/run":
            return self.run_day(body)
        self.send_error(404)

    def upload(self, name, data):
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name)[:80] or "file"
        folder = UPLOADS / secrets.token_hex(4)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
        self.send_json({"name": name, "path": (folder / name).relative_to(ROOT).as_posix(), "size": len(data)})

    def run_day(self, body):
        if TOWN.busy():
            return self.send_json({"error": "A day is already running."}, 409)
        ids = [i for i in body.get("locals", []) if re.fullmatch(r"[a-z0-9_-]+", i) and (people.PEOPLE / f"{i}.toml").exists()]
        if not ids:
            return self.send_json({"error": "Choose at least one local."}, 400)
        try:
            site = body.get("site")
            ref = tasks.add_site(site["url"], site["goal"], site["check"], site.get("value", ""), site.get("files", [])) if site else body["task"]
            task = tasks.load(ref)
            days = parse_days(body.get("dates") or [date.today().isoformat()])
        except (ValueError, KeyError, SystemExit) as e:
            return self.send_json({"error": str(e)}, 400)
        pandemic = body.get("pandemic") if body.get("pandemic") in year.PANDEMIC else None
        TOWN.start(task, [people.load(i) for i in ids], bool(body.get("watch")), days, pandemic)
        self.send_json({"ok": True, "ref": ref})


def serve(port=7300, open_browser=True):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Locals dashboard on {url}  (Ctrl+C to close)")
    if open_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        TOWN.stop.set()
        server.server_close()
