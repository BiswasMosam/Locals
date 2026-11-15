"""What the town can tell whoever is showing it: who lives here, what can be run, this machine, and the days kept in runs/."""
import json
from datetime import date
from pathlib import Path

from . import machine, people, tasks, year
from .people import ROOT
from .session import RUNS


def profile_title(profile):
    path = ROOT / profile
    first = path.read_text(encoding="utf-8").splitlines()[0] if path.exists() else ""
    return first.lstrip("# ").strip() or Path(profile).stem


def family(profile):
    """The family a job belongs to: its folder in study/profiles, or ring one for the jobs our apps already serve."""
    folder = Path(profile).parent.name
    return "Ring one" if folder == "profiles" else folder.capitalize()


def town_info(session):
    groups = {}
    for l in people.everyone():
        key = Path(l.profile).stem
        group = groups.setdefault(key, {"key": key, "label": profile_title(l.profile), "profile": l.profile,
                                        "family": family(l.profile), "people": []})
        group["people"].append({"id": l.id, "number": l.number, "name": l.name, "age": l.age, "job": l.job,
                                "status": l.status, "situation": l.situation, "habits": l.habits, "limits": vars(l.limits)})
    years = year.years()
    now = date.today()
    calendar = {"years": years, "picks": year.picks(years[-1]) if years else [],
                "sample": [d.isoformat() for d in year.sample(years[-1])] if years else [],
                "default": (now if now.year in years else date(years[-1], 2, 10)).isoformat() if years else None}
    return {"groups": list(groups.values()), "tasks": tasks.catalogue(), "busy": session.busy(), "day": session.day,
            "calendar": calendar,
            "machine": {"gpu": machine.gpu(), "memory": machine.memory(), "model": machine.model(), "pace": machine.pace(),
                        "android": machine.android()}}


def days(runs=RUNS, limit=40):
    out = []
    for meta in sorted(Path(runs).glob("*/day.json"), reverse=True)[:limit]:
        out.append(json.loads(meta.read_text(encoding="utf-8")))
    return out


def day_log(day_id, runs=RUNS):
    folder = Path(runs) / day_id
    meta = json.loads((folder / "day.json").read_text(encoding="utf-8"))
    entries = []
    for local_id in meta["locals"]:
        feed = folder / local_id / "feed.jsonl"
        if feed.exists():
            entries += [e for e in map(json.loads, feed.open(encoding="utf-8")) if "type" in e]
    return {"meta": meta, "entries": entries}
