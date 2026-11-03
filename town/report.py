"""How the town is doing across every saved day: completion against real people's benchmark, and how much
of the struggle was the model's own mistakes rather than the locals' (study/limits.md)."""
import json
from collections import defaultdict
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


def family(local_id):
    try:
        folder = Path(people.load(local_id).profile).parent.name
    except SystemExit:
        return "gone"
    return "ring one" if folder == "profiles" else folder


def rate(rs):
    done = sum(r["outcome"] in FINISHED for r in rs)
    return f"{done} of {len(rs)}".ljust(10) + (f"{done / len(rs):>4.0%}" if rs else "   -")


def report(runs_dir):
    counted = [r for r in rows(runs_dir) if r["outcome"] not in ("STOPPED", "ERROR")]
    if not counted:
        return "No finished runs yet. Run a day first: python -m town run pixelshift:small-jpg rohit sunil"
    measured = [r for r in counted if r["unfixed"] is not None]
    clean = [r for r in measured if r["unfixed"] == 0]
    lines = [f"THE TOWN SO FAR · {len(counted)} runs on {len({r['task'] for r in counted})} task(s)", "",
             f"  finished                     {rate(counted)}   real people in usability tests: {BENCHMARK:.0%}"]
    if measured:
        lines += [f"  runs checked for model mistakes ({len(measured)}, the newer ones):",
                  f"    clean, no mistake cost a step  {rate(clean)}",
                  f"    a mistake cost a step          {rate([r for r in measured if r['unfixed']])}",
                  f"    answers the model gave again   {sum(r['retries'] for r in measured)}"]
    for title, key in (("by task", lambda r: r["task"]), ("by family", lambda r: family(r["local"]))):
        groups = defaultdict(list)
        for r in counted:
            groups[key(r)].append(r)
        lines += ["", f"  {title}"] + [f"    {name[:28]:<28} {rate(rs)}" for name, rs in sorted(groups.items())]
    return "\n".join(lines)
