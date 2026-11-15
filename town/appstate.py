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


def roster(groups):
    """Everyone by family and then by job, for choosing who goes out: so many of each job, first in the file first."""
    out = {}
    for g in groups:
        fam = out.setdefault(g["family"], {"family": g["family"], "jobs": []})
        fam["jobs"].append({"key": g["key"], "label": g["label"],
                            "people": [{"id": p["id"], "name": p["name"], "patience": p["limits"]["patience_steps"]} for p in g["people"]]})
    return list(out.values())


def spell(seconds):
    if seconds < 90:
        return f"{round(seconds)} seconds"
    if seconds < 5400:
        return f"{round(seconds / 60)} minutes"
    return f"{seconds / 3600:.1f} hours"


def estimate(machine, patience, days, kind="saved", has_apk=True):
    """What a day with these locals will cost this machine, and the one thing that stops it starting, if anything.
    patience is each chosen local's steps of patience. More locals take more time, not more GPU memory: they
    share one model and take turns."""
    model, gpu, pace = machine.get("model") or {}, machine.get("gpu"), machine.get("pace") or {}
    secs, usual = pace.get("secs_per_step", 6.0), pace.get("steps_per_task", 6.0)
    typical = days * sum(min(p, usual) * secs for p in patience)
    worst = days * sum(p * secs for p in patience)
    n = len(patience)
    out = {"time": f"About {spell(typical)}" if n else "Nobody yet", "typical": typical, "worst": worst,
           "note": (f"{n} local{'' if n == 1 else 's'}{f' on {days} days' if days > 1 else ''}, one at a time. "
                    f"Up to {spell(worst)} if everyone uses all their patience. "
                    + (f"{secs} seconds a step, measured on this machine." if pace.get("measured")
                       else "Reckoned at 6 seconds a step until a day has run here.")) if n else "Choose who goes out.",
           "gpu": "", "gpu_part": -1.0, "gpu_tight": False}
    if gpu:
        need = (model.get("size_gb") or 2.5) + 0.4
        other = max(0.0, gpu["used_gb"] - (model.get("vram_gb", 0) if model.get("loaded") else 0))
        tight = other + need > gpu["total_gb"]
        out.update(gpu_part=(other + need) / gpu["total_gb"], gpu_tight=tight,
                   gpu=("Not enough free GPU memory, so part of the model runs on the processor. Slower, but it works."
                        if tight else f"The model needs about {need:.1f} GB of the GPU's {gpu['total_gb']:.0f}; "
                                      f"other things are using {other:.1f}."))
    else:
        out["gpu"] = "No NVIDIA GPU found, so the model runs on the processor. Slower, but it works."
    android = machine.get("android") or {}
    out["problem"] = ("Ollama is not running. Start it, then come back." if not model.get("reachable")
                      else f"The model is not downloaded yet. Run: ollama pull {model.get('name', '')}" if not model.get("installed")
                      else "Start an Android emulator or connect a phone first." if kind == "apk" and not android.get("devices")
                      else "Choose the app's APK file first." if kind == "apk" and not has_apk
                      else "")
    return out


def _side(log, names):
    """One day, per local: how it ended, in how many steps, and how often they were stuck or slipped."""
    meta, out = log["meta"], {}
    for i in meta.get("locals", []):
        mine = [e for e in log["entries"] if e.get("local") == i]
        run = (meta.get("runs") or {}).get(i) or {}
        outcome = (meta.get("results") or {}).get(i, "")
        if not outcome:
            continue  # the day ended before their turn
        out[i] = {"name": names.get(i, i), "outcome": outcome,
                  "steps": run.get("steps", sum(e.get("type") == "step" for e in mine)),
                  "stuck": sum(e.get("kind") == "STUCK" for e in mine), "slips": sum(e.get("kind") == "SLIP" for e in mine)}
    return out


def compare(before, after, names):
    """Two kept days side by side, the earlier first: who did better, who did worse, and the count each way.
    Meant for the same task before and after a change to the app; it says so when the tasks differ."""
    if before["meta"]["day"] > after["meta"]["day"]:
        before, after = after, before
    a, b = _side(before, names), _side(after, names)
    rows, tally = [], {"better": 0, "worse": 0}
    for i in [*a, *(k for k in b if k not in a)]:
        x, y = a.get(i), b.get(i)
        if x and y:
            was, now = x["outcome"] in FINISHED, y["outcome"] in FINISHED
            change = ("better" if now and not was else "worse" if was and not now
                      else "quicker" if now and y["steps"] < x["steps"] else "slower" if now and y["steps"] > x["steps"] else "same")
        else:
            change = "only after" if y else "only before"
        if change in tally:
            tally[change] += 1
        rows.append({"id": i, "name": (x or y)["name"], "before": x or {}, "after": y or {}, "change": change})
    count = lambda side: f"{sum(v['outcome'] in FINISHED for v in side.values())} of {len(side)}"
    both = [r for r in rows if r["before"] and r["after"]]
    note = (f"{tally['better']} did better and {tally['worse']} did worse, of the {len(both)} who went out both days."
            if both else "Nobody went out on both days, so there is no one to compare.")
    return {"head": f"{count(a)} got it done, then {count(b)}.", "note": note, "rows": rows,
            "same_task": before["meta"].get("task") == after["meta"].get("task"),
            "before": {"day": before["meta"]["day"], "task": before["meta"].get("task", ""), "today": before["meta"].get("today", "")},
            "after": {"day": after["meta"]["day"], "task": after["meta"].get("task", ""), "today": after["meta"].get("today", "")}}


def day_row(meta, names):
    """One saved day as the list shows it."""
    results = meta.get("results") or {}
    day_id = meta["day"]
    return {"day": day_id, "date": day_id[:10], "time": f"{day_id[11:13]}:{day_id[13:15]}", "task": meta.get("task", ""),
            "today": meta.get("today", ""), "again": bool(meta.get("ref")),
            "locals": [{"id": i, "name": names.get(i, i), "outcome": results.get(i, "")} for i in meta.get("locals", [])]}


WARN = {"STUCK", "SLIP", "OFF PATH", "WRONG DONE", "ASKED"}
TONE = {**{k: "warn" for k in WARN}, "DONE": "good", "SAYS DONE": "good", "GAVE UP": "bad", "ERROR": "bad",
        "TAKE": "calm", "EXPERT": "calm", "MODEL": "faint", "STOPPED": "faint"}
FINISHED = ("DONE", "SAYS DONE")
WORDS = {"GAVE UP": "gave up", "ASKED": "asked for help", "WRONG DONE": "thought they were done but were not",
         "ERROR": "hit an error"}


def moment(e, i, names):
    """One entry of the feed as the pages show it. Every key is always there, with the same kind of value."""
    step = e.get("type") == "step"
    kind = "STEP" if step else e.get("kind", "")
    return {"i": i, "local": e.get("local", ""), "name": names.get(e.get("local"), e.get("local", "")), "kind": kind,
            "tone": "step" if step else TONE.get(kind, "plain"), "step": int(e.get("step") or 0),
            "title": e.get("line", "") if step else kind.capitalize(), "text": e.get("thought", "") if step else e.get("says", ""),
            "at": str(e.get("at") or ""), "secs": float(e.get("secs") or 0), "shot": e.get("shot") or ""}


def app_name(task):
    app = task.split(":")[0].strip()
    return "Your site" if "." in app else app


def verdict(task, days):
    """What a day, or a year of days, came to. Nine in ten done, with at least three locals, and the app is great by name;
    anything else is a plain count. days is a list of {label, results}. None when it was stopped or nothing ran."""
    every = [k for d in days for k in d["results"].values()]
    if not every or "STOPPED" in every:
        return None
    ok, total, year = sum(k in FINISHED for k in every), len(every), len(days) > 1
    pct = round(ok / total * 100)
    win = pct >= 90 and total >= 3
    if year:
        def rate(d):
            return sum(k in FINISHED for k in d["results"].values()) / max(1, len(d["results"]))
        hardest = min(days, key=rate)
        note = (f"Hardest day: {hardest.get('label') or hardest.get('date')}, "
                f"{sum(k in FINISHED for k in hardest['results'].values())} of {len(hardest['results'])} done."
                if rate(hardest) < 1 else "Every single day went well.")
        head = f"{app_name(task)} is great all year." if win else f"{ok} of {total} local days done."
        return {"win": win, "head": head, "sub": f"{pct}% across {len(days)} days", "note": note}
    if win:
        return {"win": True, "head": f"{app_name(task)} is great.",
                "sub": f"{ok} of {total} locals got it done in their real day, {pct}%",
                "note": "Busy hands, small screens, no patience to spare, and it still worked."}
    others = [f"{n} {w}" for k, w in WORDS.items() if (n := every.count(k))]
    return {"win": False, "head": f"{ok} of {total} got it done.", "sub": " · ".join([f"{pct}%", *others]),
            "note": "Send at least three locals for the town to celebrate." if pct >= 90 else ""}


class Live:
    """The day on the page: the one that is running, or a kept one that was opened. Built from the entries
    a session sends, which are the same entries a kept day has in its feed files."""

    def __init__(self, names=None, patience=None):
        self.names, self.patience = names or {}, patience or {}
        self.running = self.stopping = self.kept = False
        self.task = self.today = self.error = self.day = ""
        self.index, self.locals, self.states, self.moments = [1, 1], [], {}, []
        self.who, self.began, self.verdict = "", 0.0, None

    def clear(self):
        self.__init__(self.names, self.patience)

    def start(self):
        """A day was asked for; nothing has been heard from it yet."""
        self.clear()
        self.running, self.began = True, time.time()

    def load(self, meta, entries):
        """A kept day, opened to be read."""
        self.clear()
        self.kept = True
        self._open(meta)
        for e in entries:
            self._entry(e)
        self.states.update(meta.get("results") or {})
        self.who = ""
        self.verdict = verdict(self.task, [{"results": meta.get("results") or {}}])

    def _open(self, e):
        self.task, self.today, self.index = e.get("task", ""), e.get("today", ""), e.get("index") or [1, 1]
        self.day, self.locals = e.get("day", ""), list(e.get("locals", []))
        self.states, self.moments, self.who = {i: "out" for i in self.locals}, [], ""

    def _entry(self, e):
        who, kind = e["local"], e.get("type")
        m = moment(e, len(self.moments), self.names)
        self.moments.append(m)
        if kind == "event" and e.get("kind") in OUTCOMES:
            self.states[who], self.who = e["kind"], ""
        elif self.states.get(who) in (None, "out", "work"):  # their take, after an outcome, is not more work
            self.states[who], self.who = "work", who
        return m

    def hear(self, e):
        """Takes one entry in. Returns (whether the feed began again, the moment added or None)."""
        kind = e.get("type")
        if kind == "year":
            self.task = e.get("task") or self.task
            if e.get("phase") == "end":
                self.running = self.stopping = False
                self.error, self.who = e.get("error", ""), ""
                if len(e.get("days") or []) > 1:
                    self.verdict = verdict(self.task, e["days"])
            return False, None
        if kind == "day" and e.get("phase") == "start":
            self.running, self.verdict, self.kept = True, None, False
            self._open(e)
            return True, None
        if kind == "day":
            self.states.update(e.get("results") or {})
            self.who = ""
            if self.index[1] == 1:
                self.verdict = verdict(self.task, [{"results": e.get("results") or {}}])
            return False, None
        if "local" in e:
            return False, self._entry(e)
        return False, None

    def strips(self):
        """A row per local: a cell for every step taken, amber where something went wrong at it, then how it ended,
        then the patience they had left."""
        rows = {i: {"id": i, "name": self.names.get(i, i), "cells": [], "outcome": "", "end": -1, "left": 0} for i in self.locals}
        flag = set()
        for m in self.moments:
            row = rows.get(m["local"])
            if row is None:
                continue
            if m["kind"] == "STEP":
                wrong = m["local"] in flag or m["title"] == "stuck"
                flag.discard(m["local"])
                row["cells"].append({"i": m["i"], "tone": "warn" if wrong else "step"})
            elif m["kind"] in OUTCOMES:
                row["outcome"], row["end"] = m["kind"], m["i"]
            elif m["kind"] in WARN and not row["outcome"]:
                # A slip is reported just before the step it spoiled; being stuck, just after the step that got nowhere.
                if m["kind"] == "STUCK" and row["cells"]:
                    row["cells"][-1]["tone"] = "warn"
                else:
                    flag.add(m["local"])
        for i, row in rows.items():
            state = self.states.get(i, "")
            row["outcome"] = row["outcome"] or (state if state in OUTCOMES else "")
            if not row["outcome"] or row["outcome"] in FINISHED:  # patience only means something while it was not spent
                row["left"] = max(0, min(30, self.patience.get(i, 0)) - len(row["cells"]))
        return list(rows.values())

    def view(self):
        last = self.moments[-1] if self.moments else None
        return {"running": self.running, "stopping": self.stopping, "kept": self.kept, "open": bool(self.locals),
                "day": self.day, "task": self.task, "today": self.today, "index": self.index, "locals": self.locals,
                "states": dict(self.states), "who": self.who, "error": self.error, "began": self.began,
                "step": last["step"] if last and last["kind"] == "STEP" and last["local"] == self.who else 0,
                "line": (last["title"] if last["kind"] == "STEP" else f"{last['title']}. {last['text']}") if last else "",
                "thought": last["text"] if last and last["kind"] == "STEP" else "",
                "finished": sum(v in OUTCOMES for v in self.states.values()),
                "verdict": self.verdict or {"win": False, "head": "", "sub": "", "note": ""}}


def spec_again(meta):
    """What to ask the session for to run a saved day once more: same task, same people, same date in the calendar."""
    body = {"locals": list(meta.get("locals", [])), "task": meta.get("ref", ""), "take": True}
    if meta.get("date"):
        body["dates"] = [meta["date"]]
    return body


def window_file(runs):
    return Path(runs) / "_session" / "window.json"
