"""The window: Locals as an application of its own.

    python -m town                         # what opens it
    python -m town app --demo              # a scripted day, with no model and no browser
    python -m town app --snapshot DIR      # offscreen: each page as a PNG in DIR, then quit

It holds a Session (town/session.py) in the same program, so there is no server and no port: the day runs in
its worker, and what the worker reports arrives here as signals. This file is the join between that and the
pages in town/ui/; what the window knows is worked out in town/appstate.py, which needs no Qt.

A normal window: a title bar to move it, edges to size it, the maximise button with Windows' snap layouts.
It opens where and as big as it was last closed, if that place is still on a monitor.
"""
import json
import os
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon, QImage, QPainter, QColor, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401  (without it the window arrives as a plain QWindow, which cannot be grabbed)

from . import appstate, mind, records, session

UI = Path(__file__).resolve().parent / "ui"
NIGHT = "#0c0e13"
MARK = ["X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"]  # the L of the banner, as lit windows


class Town(QObject):
    """Everything the pages can read and ask for."""
    changed = Signal()       # who lives here, this machine, the saved days
    liveChanged = Signal()   # the running day moved on
    heard = Signal("QVariantMap")  # each moment of the day as it arrives, for the feed
    dayReset = Signal()      # the feed began again: a day started, or a kept one was opened or closed
    noticeChanged = Signal()
    _arrived = Signal(object)
    _loaded = Signal(object)

    def __init__(self, runs=session.RUNS):
        super().__init__()
        self.session = session.Session(runs)
        self.runs = Path(runs)
        self.live = appstate.Live()
        self._info, self._families, self._days, self._meta, self._notice = {}, [], [], {}, ""
        self._names, self._asked = {}, 0.0
        self.ran = False  # whether this window has run a day, and so may have left the model loaded
        self._arrived.connect(self._hear)
        self._loaded.connect(self._take)
        self._take(self._read())
        q, _ = self.session.watch()
        threading.Thread(target=self._pump, args=(q,), daemon=True).start()

    # The session reports on its own thread; a signal carries each entry over to the window's.
    def _pump(self, q):
        while True:
            self._arrived.emit(q.get())

    def _hear(self, entry):
        again, moment = self.live.hear(entry)
        if again:
            self.dayReset.emit()
        self.liveChanged.emit()
        if moment:
            self.heard.emit(moment)
        if entry.get("type") == "year" and entry.get("phase") == "end":
            if self.live.error:
                self._say(self.live.error)
            self.refresh()

    def _read(self):
        return {"info": records.town_info(self.session), "days": records.days(self.runs)}

    def _take(self, got):
        self._info = got["info"]
        self._families = appstate.families(self._info["groups"])
        self._names = {p["id"]: p["name"] for f in self._families for p in f["people"]}
        self.live.names = self._names
        self.live.patience = {p["id"]: p["patience"] for f in self._families for p in f["people"]}
        self._meta = {d["day"]: d for d in got["days"]}
        self._days = [appstate.day_row(d, self._names) for d in got["days"]]
        self.changed.emit()

    def _say(self, words):
        self._notice = words
        self.noticeChanged.emit()

    @Property("QVariantList", notify=changed)
    def families(self):
        return self._families

    @Property("QVariantMap", notify=changed)
    def machine(self):
        return self._info.get("machine", {})

    @Property(int, notify=changed)
    def taskCount(self):
        return len(self._info.get("tasks", []))

    @Property("QVariantList", notify=changed)
    def days(self):
        return self._days

    @Property("QVariantMap", notify=liveChanged)
    def now(self):
        return self.live.view()

    @Property(bool, notify=liveChanged)
    def busy(self):
        return self.live.running

    @Property("QVariantList", notify=liveChanged)
    def strips(self):
        return self.live.strips()

    @Property("QVariantList", notify=dayReset)
    def moments(self):
        """The whole feed so far, for a page that has just been told it began again."""
        return list(self.live.moments)

    @Property(str, constant=True)
    def root(self):
        """Where a moment's screenshot lives: its path is kept relative to the project."""
        return QUrl.fromLocalFile(str(session.ROOT)).toString() + "/"

    @Slot(str)
    def openDay(self, day_id):
        """Puts a kept day on the page to be read. Not while a day is running: that one is on the page."""
        if self.live.running or day_id not in self._meta:
            return
        try:
            log = records.day_log(day_id, self.runs)
        except (OSError, ValueError, KeyError) as e:
            return self._say(f"That day could not be read: {e}")
        self.live.load(log["meta"], log["entries"])
        self.dayReset.emit()
        self.liveChanged.emit()

    @Slot()
    def closeDay(self):
        if not self.live.running:
            self.live.clear()
            self.dayReset.emit()
            self.liveChanged.emit()

    @Property(str, notify=noticeChanged)
    def notice(self):
        return self._notice

    @Slot()
    def dismiss(self):
        self._say("")

    @Slot()
    def refresh(self):
        """Reads the machine and the saved days again, off the window's thread: asking the GPU and adb can take seconds."""
        if time.time() - self._asked < 1:
            return
        self._asked = time.time()
        threading.Thread(target=lambda: self._loaded.emit(self._read()), daemon=True).start()

    @Slot(str)
    def runAgain(self, day_id):
        meta = self._meta.get(day_id)
        if meta is None or self.live.running:
            return
        try:
            spec = session.plan(appstate.spec_again(meta))
            self.live.start()
            self.dayReset.emit()
            self.session.start(spec)
            self.ran = True
        except (ValueError, session.Busy, OSError) as e:
            self.live.running = False
            self._say(str(e))
        self.liveChanged.emit()

    @Slot()
    def stop(self):
        if self.live.running and not self.live.stopping:
            self.live.stopping = True
            self.session.stop()
            self.liveChanged.emit()

    def demo(self, finish=False):
        """A scripted day for looking at the window without a model: the same entries a worker sends.
        finish: carry it through to everyone done, to see the town celebrate."""
        who = ["rohit", "sunil", "neha"]
        day = {"day": "2026-01-01_000000", "task": "PixelShift: small-jpg", "ref": "pixelshift:small-jpg", "locals": who,
               "index": [1, 1], "today": "Wed 1 Jul 2026 · heavy rain"}
        script = [{"type": "year", "phase": "start", "task": day["task"]}, {"type": "day", "phase": "start", **day},
                  {"type": "event", "local": "rohit", "kind": "START", "says": "Junior advocate, on a phone"},
                  {"type": "step", "local": "rohit", "step": 1, "line": 'tap [D] "IMAGE CONVERTER"', "thought": "Need to upload photo.png first."},
                  {"type": "step", "local": "rohit", "step": 2, "line": 'tap [G] "JPG Small"', "thought": "Change to JPG, small, so the file fits."},
                  {"type": "event", "local": "rohit", "kind": "DONE", "says": "photo.jpg, 0.5 MB · 4 steps · 28s"},
                  {"type": "event", "local": "sunil", "kind": "START", "says": "Runs a Chinese food stall, on a phone"},
                  {"type": "step", "local": "sunil", "step": 1, "line": 'tap [F] "BMP"', "thought": "This one says picture, must be it."},
                  {"type": "event", "local": "sunil", "kind": "SLIP", "says": 'Meant to tap [E] "JPG", hit [F] "BMP".'},
                  {"type": "step", "local": "sunil", "step": 2, "line": 'tap [F] "BMP"', "thought": "JPG, the one the customer asked for."},
                  {"type": "event", "local": "sunil", "kind": "STUCK", "says": "Kept landing on the same screen; nothing they tried changed it."},
                  {"type": "event", "local": "sunil", "kind": "DONE" if finish else "GAVE UP", "says": "photo.jpg, 0.6 MB" if finish else "Gave up on the app."},
                  {"type": "event", "local": "neha", "kind": "START", "says": "Associate at a law firm, on a laptop"},
                  {"type": "step", "local": "neha", "step": 3, "line": 'set [L] "QUALITY" = 30', "thought": "Lower quality should make it smaller."}]
        self.live.start()
        for entry in script:
            self._hear(entry)
        if finish:
            for entry in ({"type": "event", "local": "neha", "kind": "DONE", "says": "photo.jpg, 0.4 MB · 5 steps · 31s"},
                          {"type": "day", "phase": "end", **day, "results": {"rohit": "DONE", "sunil": "DONE", "neha": "DONE"}},
                          {"type": "year", "phase": "end", "task": day["task"], "days": []}):
                self._hear(entry)


def pages_of(window):
    """The names of the window's pages. A list kept in QML arrives wrapped, and the wrapper cannot be walked."""
    pages = window.property("pages")
    return list(pages.toVariant() if hasattr(pages, "toVariant") else pages)


def icon():
    """The mark as the window's icon: drawn here, so there is no image file to keep in step with the banner."""
    image = QImage(64, 64, QImage.Format_ARGB32)
    image.fill(QColor(NIGHT))
    p = QPainter(image)
    for y, row in enumerate(MARK):
        for x, c in enumerate(row):
            if c == "X":
                p.fillRect(17 + x * 6, 11 + y * 6, 6, 6, QColor("#ffc94d"))
    p.end()
    return QIcon(QPixmap.fromImage(image))


def dark_title_bar(window):
    """Windows draws the title bar; ask it for the night's colour so the window is one surface."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd, dwm = int(window.winId()), ctypes.windll.dwmapi
        r, g, b = (int(NIGHT[i:i + 2], 16) for i in (1, 3, 5))
        for attribute, value in ((20, 1), (35, r | g << 8 | b << 16), (34, r | g << 8 | b << 16)):  # dark, caption, border
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(ctypes.c_int(value)), 4)
    except Exception:
        pass  # an older Windows keeps its own title bar; nothing else depends on this


def main(demo=False, snapshot=None, size=None, open_day=None, finish=False):
    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("Locals")
    app.setWindowIcon(icon())
    town = Town()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("town", town)
    engine.load(QUrl.fromLocalFile(str(UI / "Main.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]

    remembered = appstate.window_file(town.runs)
    try:
        saved = json.loads(remembered.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = None
    screens = sorted(app.screens(), key=lambda s: s is not app.primaryScreen())
    spot = appstate.place(saved, [s.geometry().getRect() for s in screens])
    if size:
        spot.update(w=size[0], h=size[1], maximised=False)
    if snapshot:
        # A real window, so the real fonts, but see-through and off the taskbar: nothing appears on anyone's
        # screen. Qt's own offscreen mode has no fonts on Windows (every letter came out as a box), and a
        # window parked beyond the monitors is never laid out (its content stayed 0 by 0).
        from PySide6.QtCore import Qt
        window.setOpacity(0)
        window.setFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
    normal = dict(spot)
    window.setGeometry(spot["x"], spot["y"], spot["w"], spot["h"])

    def moved():
        if window.visibility() == window.Visibility.Windowed:  # where it sits when it is not maximised
            normal.update(x=window.x(), y=window.y(), w=window.width(), h=window.height())

    for signal in (window.xChanged, window.yChanged, window.widthChanged, window.heightChanged):
        signal.connect(moved)

    def leave():
        normal["maximised"] = window.visibility() == window.Visibility.Maximized
        if not snapshot:
            try:
                remembered.parent.mkdir(parents=True, exist_ok=True)
                remembered.write_text(json.dumps(normal), encoding="utf-8")
            except OSError:
                pass
        town.session.close()
        if town.ran:
            mind.unload()

    app.aboutToQuit.connect(leave)
    if demo:
        town.demo(finish)
    if open_day:
        town.openDay(open_day)
    if snapshot:
        out, pages = Path(snapshot), pages_of(window)
        out.mkdir(parents=True, exist_ok=True)
        window.show()

        def shoot(i=0):
            try:
                if i:
                    window.grabWindow().save(str(out / f"{pages[i - 1]}.png"))
                if i < len(pages):
                    window.setProperty("page", pages[i])
                    return QTimer.singleShot(500, lambda: shoot(i + 1))
            except Exception as e:  # a snapshot that cannot be taken must still end, not sit there unseen
                print(f"No snapshot: {type(e).__name__}: {e}", file=sys.stderr)
            app.exit(0)  # not quit(): that asks the window first, and with the demo's day running it says no

        QTimer.singleShot(300, shoot)
    else:
        window.showMaximized() if spot["maximised"] else window.show()
        dark_title_bar(window)
    return app.exec()
