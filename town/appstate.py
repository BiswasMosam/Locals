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


def scene_view(scene):
    """What a day does to the look of the town (year.Today.scene), with every key there for the page."""
    scene = scene or {}
    return {key: scene.get(key) or "" for key in ("rain", "lights", "pandemic", "label")}


class Live:
    """The day on the page: the one that is running, or a kept one that was opened. Built from the entries
    a session sends, which are the same entries a kept day has in its feed files."""

    def __init__(self, names=None, patience=None):
        self.names, self.patience = names or {}, patience or {}
        self.running = self.stopping = self.kept = False
        self.task = self.today = self.error = self.day = ""
        self.index, self.locals, self.states, self.moments = [1, 1], [], {}, []
        self.who, self.began, self.verdict, self.scene = "", 0.0, None, {}

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
        self.scene = e.get("scene") or {}

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
                "scene": scene_view(self.scene),
                "step": last["step"] if last and last["kind"] == "STEP" and last["local"] == self.who else 0,
                "line": (last["title"] if last["kind"] == "STEP" else f"{last['title']}. {last['text']}") if last else "",
                "thought": last["text"] if last and last["kind"] == "STEP" else "",
                "finished": sum(v in OUTCOMES for v in self.states.values()),
                "verdict": self.verdict or {"win": False, "head": "", "sub": "", "note": ""}}


# ---------- a talk in a room ----------

LIT = {"hooked": "hooked", "with you": "with", "drifting": "drift", "phone out": "low", "checking email": "low"}
DEPTH = ["ASLEEP", "STOPPED LISTENING", "PHONE OUT", "CHECKING EMAIL", "DRIFTING"]
GOOD_MARKS = ("hooked till the end", "brought them back")
BAD_MARKS = ("lost the room", "the room fell asleep", "over time")
UNSEEN = "Not marked: it cannot be judged from a file."


def clock(seconds):
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def _listener(l, parts):
    """One listener as the page shows them: a window for every part heard, lit by how far they were with the talk."""
    from .room import band_of
    trail = l.get("trail") or []
    ends = [(p["start"] + p["seconds"]) / 60 for p in parts]
    bands = [band_of(l["role"], a, ends[i] if i < len(ends) else 99) for i, a in enumerate(trail)]
    inner = l.get("inner")
    if inner is None:  # talks kept before each thought was filed under its part
        thoughts = l.get("thoughts") or []
        inner = thoughts if len(thoughts) == len(trail) else [""] * len(trail)
    low = sorted((e for e in l.get("events") or [] if e["kind"] in DEPTH), key=lambda e: DEPTH.index(e["kind"]))
    note = (f"{low[0]['kind'].capitalize()} at {low[0]['part']}" + (f": {low[0]['why']}" if low[0].get("why") else "")
            if low else "Never drifted" if trail else "")
    recall = l.get("recall") or {}
    began = l.get("began", trail[0] if trail else 0)
    return {"id": l["id"], "name": l["name"], "number": int(l.get("number") or 0), "job": l.get("job", ""),
            "grader": l["role"] == "grader", "why": l.get("why", ""),
            "cells": [{"tone": LIT.get(b, "out"), "band": b, "attention": round(a), "inner": str(inner[i] if i < len(inner) else "")}
                      for i, (a, b) in enumerate(zip(trail, bands))],
            "attention": round(trail[-1] if trail else began), "band": bands[-1] if bands else band_of(l["role"], began, 0),
            "note": note, "decided": l.get("decided") or "", "same": recall.get("same", ""),
            "point": recall.get("point") or recall.get("why", ""), "question": recall.get("question", ""),
            "unknown": ", ".join(list(dict.fromkeys(l.get("unknown") or []))[:8])}


def _marks(grade):
    """The graders' marks as the page shows them. Every key is always there."""
    out = {"has": bool(grade), "rubric": "", "out_of": 0, "mean": "", "spread": "", "verdict": "", "graders": []}
    if not grade or not grade.get("rubric"):
        return out
    from .grade import rubrics
    rubric = rubrics().get(grade["rubric"]) or {"name": grade["rubric"], "criterion": []}
    top = len(rubric["criterion"][0]["levels"]) if rubric["criterion"] else 0
    out.update(rubric=rubric["name"], out_of=grade.get("out_of", 0), verdict=grade.get("verdict", ""))
    if grade.get("mean") is not None:
        out["mean"] = f"{grade['mean']:g}"
        out["spread"] = f"from {grade['low']:g} to {grade['high']:g}" if grade.get("low") != grade.get("high") else ""
    for g in grade.get("graders") or []:
        lines = []
        for c in rubric["criterion"]:
            m = g["marks"].get(c["id"])
            lines.append({"name": c["name"], "level": m["level"] if m else 0, "top": top,
                          "reason": m["reason"] if m else UNSEEN if c["id"] in g.get("not marked", {}) else
                          "" if g.get("timed_out") else "No mark held up against the evidence.",
                          "about": ", ".join(m["about"]) if m else ""})
        head = (f"{g['total']:g} of {grade.get('out_of', 0)}" if g.get("total") is not None
                else "No answer in time" if g.get("timed_out") else "No mark held up")
        out["graders"].append({"name": g["name"], "job": g.get("job", ""), "head": head, "verdict": g.get("verdict", ""),
                               "overall": g.get("overall", ""), "marks": lines, "dropped": len(g.get("dropped") or []),
                               "bonus": [f"{'+' if v > 0 else ''}{v:g} {k}" for k, v in g.get("markers") or []]})
    return out


def talk_row(r):
    """One kept talk as the list shows it."""
    talk_id, grade = r["talk"], r.get("grade") or {}
    people = [_listener(l, r.get("parts") or []) for l in r.get("listeners") or []]
    got = sum(p["same"] in ("yes", "partly") for p in people)
    return {"talk": talk_id, "date": talk_id[:10], "time": f"{talk_id[11:13]}:{talk_id[13:15]}", "name": r.get("name", ""),
            "source": r.get("source", ""), "clock": clock(r.get("seconds") or 0),
            "mark": f"{grade['mean']:g} of {grade['out_of']}" if grade.get("mean") is not None else "",
            "got": f"{got} of {len(people)} got the point",
            "lit": [p["cells"][-1]["tone"] if p["cells"] else "out" for p in people]}


class Hall:
    """The talk on the page: the one being given, or a kept one that was opened. A talk that is running is built
    up from what the session sends into the same shape a kept talk has in its room.json, so both are shown one way."""

    def __init__(self):
        self.clear()

    def clear(self):
        self.running = self.stopping = self.kept = self.stopped = False
        self.stage = self.error = self.talk = ""
        self.began, self.result, self.studied, self.at = 0.0, None, [0, 0], -1

    def start(self):
        """A talk was asked for; nothing has been heard from it yet."""
        self.clear()
        self.running, self.began, self.stage = True, time.time(), "reading"

    def load(self, talk_id, result):
        """A kept talk, opened to be read."""
        self.clear()
        self.kept, self.talk, self.result, self.stage = True, talk_id, result, "over"

    def _who(self, local_id):
        return next(l for l in self.result["listeners"] if l["id"] == local_id)

    def hear(self, e):
        phase, r = e.get("phase"), self.result
        if phase == "reading":
            self.running, self.stage, self.talk = True, "reading", e.get("talk", "")
            self.began = self.began or time.time()
            self.result = {"room": e["room"], "name": e["name"], "source": " + ".join(e.get("files", [])), "parts": [],
                           "listeners": [], "markers": [], "notes": [], "point": "", "stated": None, "seconds": 0}
        elif phase == "end":
            self.running = self.stopping = False
            self.stopped, self.error, self.stage = bool(e.get("stopped")), e.get("error", ""), "over"
        elif r is None:
            return
        elif phase == "start":
            r.update({k: e[k] for k in ("source", "kind", "seconds", "notes", "measured") if k in e})
            r["parts"] = [{**p, "moments": []} for p in e["parts"]]
            r["listeners"] = [{**l, "trail": [], "inner": [], "events": [], "unknown": [], "recall": {}, "decided": ""}
                              for l in e["listeners"]]
            self.stage = "studying"
        elif phase == "point":
            r["point"], r["stated"] = e.get("point", ""), e.get("stated")
        elif phase == "study":
            self.studied = [e["done"], e["of"]]
        elif phase == "sorting":
            self.stage = "sorting"
        elif phase == "part":
            self.stage, self.at = "listening", e["index"]
            r["parts"][e["index"]]["moments"] = e.get("moments", [])
        elif phase == "heard":
            l = self._who(e["local"])
            l["trail"].append(e["attention"])
            l["inner"].append(e.get("inner", ""))
            l["events"] += e.get("events", [])
            l["unknown"] += e.get("unknown", [])
            if any(x["kind"] == "MADE UP THEIR MIND" for x in e.get("events", [])):
                l["decided"] = e["part"]
        elif phase == "recalling":
            self.stage = "asking"
        elif phase == "recall":
            self._who(e["local"])["recall"] = e["recall"]
        elif phase == "room":
            r["markers"] = e["markers"]
        elif phase == "marking":
            self.stage = "marking"
            r["grade"] = {"rubric": e["rubric"], "out_of": e["out_of"], "graders": [], "expected": e.get("graders", 0)}
        elif phase == "marks":
            r["grade"]["graders"].append(e["grader"])
        elif phase == "marked":
            r["grade"] = e["grade"]

    def view(self):
        """Everything the rooms page reads. Every key is always there, with the same kind of value."""
        r = self.result or {}
        parts = r.get("parts") or []
        people = [_listener(l, parts) for l in r.get("listeners") or []]
        grade, n = r.get("grade") or {}, len(people)
        marks = _marks(grade)
        with_you = sum(p["band"] in ("hooked", "with you") for p in people)
        got = sum(p["same"] in ("yes", "partly") for p in people)
        stayed = sum(bool(p["cells"]) and min(c["attention"] for c in p["cells"]) >= 50 for p in people)
        stated = r.get("stated")
        head = sub = ""
        if self.stopping:
            head, sub = "Stopping the talk.", "What they are in the middle of is finished first."
        elif self.running and self.stage == "reading":
            head, sub = "Reading the talk.", r.get("source", "")
        elif self.running and self.stage == "studying":
            head = "Reading the talk."
            sub = (f"{self.studied[0]} of {self.studied[1]} parts read for their terms, stories and questions."
                   if self.studied[1] else "Finding its point.")
        elif self.running and self.stage == "sorting":
            head, sub = "Reading the talk.", "Sorting its terms by the field they belong to. This is the slow part."
        elif self.running and self.stage == "listening":
            head = f"{with_you} of {n} are with you."
            sub = f"{parts[self.at]['id']} of {len(parts)}  ·  {parts[self.at]['title']}" if 0 <= self.at < len(parts) else ""
        elif self.running and self.stage == "asking":
            head, sub = "The talk is over.", "Each of them is asked what the point was."
        elif self.running:
            head = "The graders are marking."
            sub = f"{len(grade.get('graders') or [])} of {grade.get('expected', 0)} done."
        elif self.stopped:
            head, sub = "The talk was stopped.", "Nothing of it was kept."
        elif r:
            if marks["mean"]:
                head = f"{marks['mean']} of {marks['out_of']}."
                sub = "  ·  ".join(x for x in (marks["verdict"], marks["spread"], f"{got} of {n} could say your point") if x)
            elif marks["rubric"]:
                head, sub = "No mark held up.", f"{got} of {n} could say your point."
            else:
                head, sub = f"{got} of {n} could say your point.", f"{stayed} of {n} stayed with you all the way."
        return {"open": bool(r), "running": self.running, "stopping": self.stopping, "kept": self.kept, "stopped": self.stopped,
                "stage": self.stage, "talk": self.talk, "began": self.began, "at": self.at,
                "room": r.get("room", ""), "name": r.get("name", ""), "source": r.get("source", ""), "kind": r.get("kind", ""),
                "clock": clock(r.get("seconds") or 0), "head": head, "sub": sub, "point": r.get("point", ""),
                "stated": (f"Said in so many words in {stated}." if stated else "Never said in so many words.") if r.get("point") else "",
                "notes": list(r.get("notes") or []), "measured": [t for _, t in r.get("measured") or []],
                "parts": [{"id": p["id"], "title": p["title"], "at": clock(p["start"]),
                           "moments": ", ".join(dict.fromkeys(m["kind"] for m in p.get("moments") or []))} for p in parts],
                "listeners": people,
                "markers": [{"kind": m["kind"], "says": m["says"],
                             "tone": "good" if m["kind"] in GOOD_MARKS else "bad" if m["kind"] in BAD_MARKS else "plain"}
                            for m in r.get("markers") or []],
                "marks": marks}


def report_view(s):
    """The town's report as the page shows it: how many runs finished, against real people, by task and by family."""
    def row(name, t):
        return {"name": name, "done": t["done"], "of": t["of"], "part": t["done"] / t["of"] if t["of"] else 0.0,
                "pct": f"{round(t['done'] / t['of'] * 100)}%" if t["of"] else ""}

    bench = round(s["benchmark"] * 100)
    out = {"any": bool(s["runs"]), "runs": s["runs"], "tasks": s["tasks"], "benchmark": s["benchmark"], "bench": f"{bench}%",
           "all": row("The town", s["all"]), "head": "No run has finished yet.", "sub": "Run a day, and the count starts here.",
           "checked": False, "checked_runs": 0, "clean": row("", {"done": 0, "of": 0}), "cost": row("", {"done": 0, "of": 0}),
           "retries": 0, "by_task": [row(g["name"], g) for g in s["by"].get("task", [])],
           "by_family": [row(g["name"].capitalize(), g) for g in s["by"].get("family", [])]}
    if s["runs"]:
        out["head"] = f"{s['all']['done']} of {s['runs']} runs got it done."
        out["sub"] = (f"{out['all']['pct']} across {s['tasks']} task{'' if s['tasks'] == 1 else 's'}. "
                      f"Real people in usability tests finish {bench}% of theirs.")
    if s["checked"]:
        c = s["checked"]
        out.update(checked=True, checked_runs=c["runs"], clean=row("", c["clean"]), cost=row("", c["cost"]), retries=c["retries"])
    return out


def spec_again(meta):
    """What to ask the session for to run a saved day once more: same task, same people, same date in the calendar."""
    body = {"locals": list(meta.get("locals", [])), "task": meta.get("ref", ""), "take": True}
    if meta.get("date"):
        body["dates"] = [meta["date"]]
    return body


def window_file(runs):
    return Path(runs) / "_session" / "window.json"
