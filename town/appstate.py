"""What the window knows at any moment, worked out with no window: where it opens, and where the day has got to.

Kept apart from town/app.py so that it needs no Qt and the tests can run it anywhere.
"""
import time
from pathlib import Path

from .session import OUTCOMES

DEFAULT = (1360, 860)


def place(saved, screens, default=DEFAULT):
    """Where the window opens: where it was last closed, when its title bar would still be on a monitor.
    screens are (x, y, w, h) with the main one first; a monitor to the left has a negative x, and a monitor
    that was there last week may not be there today. A window nobody can reach to drag back is opened afresh."""
    if saved:
        try:
            x, y, w, h = (int(saved[k]) for k in ("x", "y", "w", "h"))
        except (KeyError, TypeError, ValueError):
            x = y = w = h = 0
        for sx, sy, sw, sh in screens:
            across = min(x + w, sx + sw) - max(x, sx)   # how much of the title bar this monitor shows
            down = min(y + 40, sy + sh) - max(y, sy)
            if w >= 640 and h >= 400 and across >= 160 and down >= 24:
                return {"x": x, "y": y, "w": w, "h": h, "maximised": bool(saved.get("maximised"))}
    sx, sy, sw, sh = screens[0] if screens else (0, 0, 1920, 1080)
    w, h = min(default[0], int(sw * 0.92)), min(default[1], int(sh * 0.88))
    return {"x": sx + (sw - w) // 2, "y": sy + (sh - h) // 2, "w": w, "h": h, "maximised": False}


def families(groups):
    """Everyone in town by family, in the order the families were built, for a wall of windows."""
    out = {}
    for g in groups:
        fam = out.setdefault(g["family"], {"family": g["family"], "people": []})
        for p in g["people"]:
            L = p["limits"]
            fam["people"].append({"id": p["id"], "number": p["number"], "name": p["name"], "age": p["age"], "job": p["job"],
                                  "device": L["device"], "reads": L["read_words"], "patience": L["patience_steps"],
                                  "slips": round(L["slip_rate"] * 100), "stuck": p["habits"].get("when_stuck", "")})
    return list(out.values())


def day_row(meta, names):
    """One saved day as the list shows it."""
    results = meta.get("results") or {}
    day_id = meta["day"]
    return {"day": day_id, "date": day_id[:10], "time": f"{day_id[11:13]}:{day_id[13:15]}", "task": meta.get("task", ""),
            "today": meta.get("today", ""), "again": bool(meta.get("ref")),
            "locals": [{"id": i, "name": names.get(i, i), "outcome": results.get(i, "")} for i in meta.get("locals", [])]}


class Live:
    """The day that is running, as the entries from a session tell it."""

    def __init__(self):
        self.running = self.stopping = False
        self.task = self.today = self.line = self.thought = self.error = ""
        self.index, self.locals, self.states = [1, 1], [], {}
        self.who, self.step, self.shot, self.began = "", 0, "", 0.0

    def start(self):
        """A day was asked for; nothing has been heard from it yet."""
        self.__init__()
        self.running, self.began = True, time.time()

    def hear(self, e):
        kind = e.get("type")
        if kind == "year":
            self.task = e.get("task", self.task)
            if e.get("phase") == "end":
                self.running = self.stopping = False
                self.error = e.get("error", "")
                self.who = ""
        elif kind == "day" and e.get("phase") == "start":
            self.running = True
            self.task, self.today, self.index = e.get("task", ""), e.get("today", ""), e.get("index") or [1, 1]
            self.locals = list(e.get("locals", []))
            self.states = {i: "out" for i in self.locals}
            self.who, self.step, self.line, self.thought = "", 0, "", ""
        elif kind == "day":
            for i, outcome in (e.get("results") or {}).items():
                self.states[i] = outcome
            self.who = ""
        elif "local" in e:
            who = e["local"]
            self.shot = e.get("shot") or self.shot
            if kind == "event" and e.get("kind") in OUTCOMES:
                self.states[who] = e["kind"]
                self.who, self.line, self.thought = "", f"{e['kind'].capitalize()}. {e.get('says', '')}", ""
            elif self.states.get(who) in (None, "out", "work"):  # their take, after an outcome, is not more work
                self.states[who], self.who = "work", who
                if kind == "step":
                    self.step, self.line, self.thought = e.get("step", 0), e.get("line", ""), e.get("thought", "")
                elif e.get("kind") == "START":
                    self.step, self.line, self.thought = 0, "Opening the app", e.get("says", "")

    def view(self):
        return {"running": self.running, "stopping": self.stopping, "task": self.task, "today": self.today,
                "index": self.index, "locals": self.locals, "states": dict(self.states), "who": self.who, "step": self.step,
                "line": self.line, "thought": self.thought, "error": self.error, "began": self.began,
                "finished": sum(v in OUTCOMES for v in self.states.values())}


def spec_again(meta):
    """What to ask the session for to run a saved day once more: same task, same people, same date in the calendar."""
    body = {"locals": list(meta.get("locals", [])), "task": meta.get("ref", ""), "take": True}
    if meta.get("date"):
        body["dates"] = [meta["date"]]
    return body


def window_file(runs):
    return Path(runs) / "_session" / "window.json"
