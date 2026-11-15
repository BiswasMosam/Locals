"""Rebuilds docs/data.js and docs/shots/days/ for the copy of the window in docs/ (the project's site), from what the
window itself knows, worked out by its own code (town/appstate.py, town/records.py). Run it after new kept days:

    .venv/Scripts/python docs/make_data.py      (macOS or Linux: .venv/bin/python)

Kept days of your own sites (tasks/mine) and Android days stay out, and so do interview talks: they are personal.
The report counts only days of the public tasks, so runs of your own sites stay out of its numbers as well."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402

from town import appstate, records, tasks, year  # noqa: E402
from town.report import summary  # noqa: E402

OUT = ROOT / "docs"
SHOTS = OUT / "shots" / "days"
RUNS = ROOT / "runs"

info = records.town_info(None)
fams = appstate.families(info["groups"])
names = {p["id"]: p["name"] for f in fams for p in f["people"]}
patience = {p["id"]: p["patience"] for f in fams for p in f["people"]}
folk = {p["id"]: p for f in fams for p in f["people"]}
# where each local is, for the line under the town (the window shows it from the profile)
for g in info["groups"]:
    for p in g["people"]:
        folk[p["id"]]["place"] = p["situation"].get("place", "")
for f in fams:
    for p in f["people"]:
        p["place"] = folk[p["id"]]["place"]

catalogue = [t for t in tasks.catalogue() if not t["mine"]]
public_refs = {t["ref"] for t in catalogue if t["platform"] == "web"}

# ---- the calendar: every day of every year it knows, as the window would label it ----
cal = info["calendar"]
labels = {}
for y in year.years():
    d = date(y, 1, 1)
    while d.year == y:
        row = {}
        for pan in ("", "lockdown", "reopening"):
            t = year.today(d, pan or None)
            row[pan or "none"] = t.label()
        sc = year.today(d).scene()
        row["rain"], row["lights"] = sc.get("rain") or "", sc.get("lights") or ""
        labels[d.isoformat()] = row
        d += timedelta(days=1)

# ---- kept days ----
days, logs, shot_count = [], {}, 0
for meta in records.days(RUNS, limit=200):
    if meta.get("ref") not in public_refs:
        continue
    log = records.day_log(meta["day"], RUNS)
    entries = []
    for e in log["entries"]:
        e = dict(e)
        if e.get("shot"):
            src = ROOT / e["shot"]
            if src.exists():
                dst = SHOTS / meta["day"] / (src.parent.name + "-" + src.stem + ".webp")
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    im = Image.open(src).convert("RGB")
                    w = 393 if im.width < im.height else 760
                    im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(dst, "WEBP", quality=74, method=6)
                    shot_count += 1
                e["shot"] = dst.relative_to(OUT).as_posix()
            else:
                e["shot"] = ""
        entries.append(e)
    live = appstate.Live(names, patience)
    live.load(log["meta"], entries)
    days.append(appstate.day_row(meta, names) | {"ref": meta.get("ref", ""), "dates": [meta.get("date", "")]})
    logs[meta["day"]] = {"meta": {k: log["meta"].get(k) for k in ("day", "task", "ref", "today", "index", "locals", "scene", "results", "date")},
                         "entries": entries, "verdict": live.view()["verdict"]}

# ---- talks, opened the way the window opens them ----
talk_rows, talk_views = [], {}
for t in records.talks(RUNS, limit=200):
    row = appstate.talk_row(t)
    if row["talk"].endswith("_interview"):
        continue  # his own interview script and recording: personal, so they stay on this machine
    hall = appstate.Hall()
    hall.load(row["talk"], records.talk_log(row["talk"], RUNS))
    talk_rows.append(row)
    talk_views[row["talk"]] = hall.view()

# ---- the town's report, worked out by the window's own summary() over the public tasks' days only ----
from town import report as town_report  # noqa: E402

public_tasks = {t["ref"] for t in catalogue}
shown_days = {m["day"] for m in records.days(RUNS, limit=10_000) if m.get("ref") in public_tasks}
every_row = town_report.rows
town_report.rows = lambda runs_dir: [r for r in every_row(runs_dir) if r["day"] in shown_days]

data = {
    "families": fams,
    "roster": appstate.roster(info["groups"]),
    "tasks": catalogue,
    "calendar": {"years": cal["years"], "picks": cal["picks"], "sample": cal["sample"]},
    "labels": labels,
    "days": days,
    "logs": logs,
    "rooms": records.rooms(folk),
    "talks": talk_rows,
    "talkViews": talk_views,
    "report": appstate.report_view(summary(RUNS)),
    "model": {"name": info["machine"]["model"].get("name", "qwen3:4b-instruct"), "size_gb": info["machine"]["model"].get("size_gb") or 2.5},
}
s = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
# no dashes on his pages, even in what the model wrote
import re  # noqa: E402
s = re.sub(r"(\d)\s*\u2013\s*(\d)", r"\1 to \2", s)
s = re.sub(r"\s*[\u2014\u2013]\s*", ": ", s)
(OUT / "data.js").write_text("// Made by the window's own code (town/appstate.py, town/records.py) from people/, rooms/, tasks/ and runs/.\n"
                             "window.TOWN = " + s + ";\n", encoding="utf-8")
print("days", len(days), "talks", len(talk_rows), "new shots", shot_count, "data.js KB", len(s.encode()) // 1024)
print("roster keys", [j["key"] for f in data["roster"] for j in f["jobs"]][:8])
print("days kept:", [(d["day"], d["task"]) for d in days][:6])
