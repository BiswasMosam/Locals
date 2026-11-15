"""What the town can tell whoever is showing it: who lives here, what can be run, this machine, and the days kept in runs/."""
import json
import re
from datetime import date
from pathlib import Path

from . import machine, people, tasks, year
from .people import ROOT
from .session import RUNS

TALK_ID = re.compile(r"\d{4}-\d{2}-\d{2}_\d{6}_[a-z]+")


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


def rooms(folk):
    """The rooms a talk can be given in, with who sits in each. folk: the town's people by id, each with a name and a job."""
    from . import grade, room
    out = []
    for r in room.rooms().values():
        rubric = grade.rubrics().get(r.get("rubric") or "")
        out.append({"id": r["id"], "name": r["name"], "about": r.get("about", ""), "where": r.get("where", ""),
                    "when": r.get("when", ""), "minutes": r.get("minutes", 0), "point_by": r.get("point_by", 0),
                    "rubric": rubric["name"] if rubric else "", "out_of": rubric["out_of"] if rubric else 0,
                    "seats": [{"id": s["local"], "name": folk.get(s["local"], {}).get("name", s["local"]),
                               "job": folk.get(s["local"], {}).get("job", ""), "grader": s["role"] == "grader", "why": s["why"]}
                              for s in r["seats"]]})
    return out


def talks(runs=RUNS, limit=40):
    """The talks kept in runs/rooms, newest first, each as its room.json with its folder's name under "talk"."""
    out = []
    for path in sorted((Path(runs) / "rooms").glob("*/room.json"), reverse=True):
        if not TALK_ID.fullmatch(path.parent.name):
            continue
        try:
            out.append({**json.loads(path.read_text(encoding="utf-8")), "talk": path.parent.name})
        except (OSError, ValueError):
            continue  # a file somebody cut short is not a talk to list
        if len(out) >= limit:
            break
    return out


def talk_log(talk_id, runs=RUNS):
    if not TALK_ID.fullmatch(talk_id):
        raise ValueError(f"{talk_id} is not a talk.")
    return json.loads((Path(runs) / "rooms" / talk_id / "room.json").read_text(encoding="utf-8"))
