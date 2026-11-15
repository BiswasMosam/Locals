"""The dashboard: setup, the town and the feed in your browser, served from this machine only."""
import json
import queue
import re
import secrets
import threading
import webbrowser
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import records, session, year
from .people import ROOT
from .session import RUNS

WEB = ROOT / "dashboard"
UPLOADS = RUNS / "_uploads"
FONTS = ROOT / "brand" / "fonts"
DAY_ID = re.compile(r"\d{4}-\d{2}-\d{2}_\d{6}")


SESSION = session.Session()


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
            return self.send_json(records.town_info(SESSION))
        if path == "/api/days":
            return self.send_json(records.days())
        if path.startswith("/api/days/"):
            day_id = path.rsplit("/", 1)[1]
            if not DAY_ID.fullmatch(day_id) or not (RUNS / day_id / "day.json").exists():
                return self.send_error(404)
            return self.send_json(records.day_log(day_id))
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
        q, backlog = SESSION.watch()
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
            SESSION.unwatch(q)

    def do_POST(self):
        parsed = urlparse(self.path)
        # A browser names the page a request came from. Without this, any site open in another tab could
        # start a day here and send the locals to an address of its choosing.
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            return self.send_error(403)
        length = int(self.headers.get("Content-Length") or 0)
        if parsed.path == "/api/files":
            return self.upload(parse_qs(parsed.query).get("name", ["file"])[0], self.rfile.read(length))
        body = json.loads(self.rfile.read(length) or b"{}")
        if parsed.path == "/api/stop":
            SESSION.stop()
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
        if SESSION.busy():
            return self.send_json({"error": "A day is already running."}, 409)
        try:
            spec = session.plan(body)
            SESSION.start(spec)
        except session.Busy as e:
            return self.send_json({"error": str(e)}, 409)
        except ValueError as e:
            return self.send_json({"error": str(e)}, 400)
        self.send_json({"ok": True, "ref": spec["ref"]})


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
        SESSION.close()
        server.server_close()
