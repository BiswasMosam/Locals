"""How the town is doing across every saved day: completion against real people's benchmark, and how much
of the struggle was the model's own mistakes rather than the locals' (study/limits.md)."""
import json
from collections import defaultdict
from functools import cache
from pathlib import Path

from . import people

BENCHMARK = 0.78  # average task completion across 1,189 tasks in 115 usability tests (Sauro)
FINISHED = ("DONE", "SAYS DONE")


def rows(runs_dir):
    out = []
    for meta_path in sorted(Path(runs_dir).glob("*/day.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for local_id, outcome in meta["results"].items():
            run = meta.get("runs", {}).get(local_id)
            if run is None and (meta_path.parent / local_id / "run.json").exists():
                run = json.loads((meta_path.parent / local_id / "run.json").read_text(encoding="utf-8"))
            out.append({"day": meta["day"], "task": meta["task"], "local": local_id, "outcome": outcome,
                        "retries": run["retries"] if run else None, "unfixed": run["unfixed"] if run else None})
    return out


@cache
def family(local_id):
    try:
        folder = Path(people.load(local_id).profile).parent.name
    except SystemExit:
        return "gone"
    return "ring one" if folder == "profiles" else folder


def tally(rs):
    return {"done": sum(r["outcome"] in FINISHED for r in rs), "of": len(rs)}


def rate(t):
    return f"{t['done']} of {t['of']}".ljust(10) + (f"{t['done'] / t['of']:>4.0%}" if t["of"] else "   -")


def summary(runs_dir):
    """The numbers behind the report, for whoever shows them: the command line below, or the window."""
    counted = [r for r in rows(runs_dir) if r["outcome"] not in ("STOPPED", "ERROR")]
    measured = [r for r in counted if r["unfixed"] is not None]
    out = {"runs": len(counted), "tasks": len({r["task"] for r in counted}), "all": tally(counted), "benchmark": BENCHMARK,
           "checked": None, "by": {}}
    if measured:
        out["checked"] = {"runs": len(measured), "clean": tally([r for r in measured if r["unfixed"] == 0]),
                          "cost": tally([r for r in measured if r["unfixed"]]), "retries": sum(r["retries"] for r in measured)}
    for title, key in (("task", lambda r: r["task"]), ("family", lambda r: family(r["local"]))):
        groups = defaultdict(list)
        for r in counted:
            groups[key(r)].append(r)
        out["by"][title] = [{"name": name, **tally(rs)} for name, rs in sorted(groups.items())]
    return out


def report(runs_dir):
    s = summary(runs_dir)
    if not s["runs"]:
        return "No finished runs yet. Run a day first: python -m town run pixelshift:small-jpg rohit sunil"
    lines = [f"THE TOWN SO FAR · {s['runs']} runs on {s['tasks']} task(s)", "",
             f"  finished                     {rate(s['all'])}   real people in usability tests: {BENCHMARK:.0%}"]
    if s["checked"]:
        c = s["checked"]
        lines += [f"  runs checked for model mistakes ({c['runs']}, the newer ones):",
                  f"    clean, no mistake cost a step  {rate(c['clean'])}",
                  f"    a mistake cost a step          {rate(c['cost'])}",
                  f"    answers the model gave again   {c['retries']}"]
    for title in ("task", "family"):
        lines += ["", f"  by {title}"] + [f"    {g['name'][:28]:<28} {rate(g)}" for g in s["by"][title]]
    return "\n".join(lines)
