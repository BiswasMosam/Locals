"""python -m town dashboard | people | run <app:task> <local ...|all> | watch <app:task> --golden|--for <local> | calibrate <local>"""
import argparse
import sys
from collections import Counter
from datetime import date, datetime

from . import day, mind, people, tasks, year
from .people import ROOT


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="python -m town", description="Locals: a small town of AI users that lives on your machine.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    board = sub.add_parser("dashboard", help="open the town in your browser")
    board.add_argument("--port", type=int, default=7300)
    board.add_argument("--no-open", action="store_true", help="do not open a browser tab")
    sub.add_parser("people", help="list everyone who lives in the town")
    run = sub.add_parser("run", help="send locals to do a task in an app")
    run.add_argument("task", help="app:task, for example pixelshift:small-jpg")
    run.add_argument("locals", nargs="+", help="local ids, or all")
    run.add_argument("--watch", action="store_true", help="show the browser while they work")
    run.add_argument("--seed", type=int, default=7, help="same seed, same run")
    run.add_argument("--date", action="append", default=[], help="a day in the calendar, like 2026-09-14; repeat for more")
    run.add_argument("--year", type=int, help="a year in twelve days, like 2026")
    run.add_argument("--pandemic", choices=["lockdown", "reopening"], help="run the days during a pandemic")
    see = sub.add_parser("watch", help="record a real person doing a task: you for the golden path, or someone standing in for a local")
    see.add_argument("task", help="app:task, for example pixelshift:small-jpg")
    who = see.add_mutually_exclusive_group(required=True)
    who.add_argument("--golden", action="store_true", help="you, doing it the way it is meant to be done")
    who.add_argument("--for", dest="local", help="the local this person stands in for, for example prakash")
    see.add_argument("--device", choices=["phone", "laptop"], help="screen size for a web app (default: the local's, or phone)")
    see.add_argument("--minutes", type=int, default=15, help="stop recording after this long")
    cal = sub.add_parser("calibrate", help="turn watched runs into a local's limits")
    cal.add_argument("local", help="local id, for example prakash")
    cal.add_argument("--apply", action="store_true", help="write the measured numbers into the local's file")
    args = ap.parse_args()

    if args.cmd == "dashboard":
        from .dashboard import serve
        return serve(args.port, not args.no_open)

    if args.cmd == "people":
        for l in people.everyone():
            print(f"{l.number:02d}  {l.id:<9} {f'{l.name}, {l.age}':<13} {l.job:<46} {l.limits.device:<7} {l.status}")
        return

    if args.cmd == "watch":
        from .watch import watch
        task, local = tasks.load(args.task), people.load(args.local) if args.local else None
        path, run = watch(task, args.golden, local, args.device or (local.limits.device if local else "phone"), args.minutes)
        steps = sum(e["kind"] in ("tap", "set", "scroll", "back") for e in run["events"])
        print(f"\n{run['outcome']} · {steps} taps and moves · {run['secs']}s · saved {path.relative_to(ROOT)}")
        if args.golden:
            print("Locals who leave this path will show OFF PATH in the feed.")
        elif local:
            print(f"See what it says about {local.name}: python -m town calibrate {local.id}")
        return

    if args.cmd == "calibrate":
        from . import calibrate
        local = people.load(args.local)
        out, text = calibrate.report(local)
        print(text)
        if out and args.apply:
            changed = calibrate.apply(local, out, len(calibrate.runs_for(local.id)))
            print(f"\nWrote {', '.join(changed)} into people/{local.id}.toml." if changed else "\nNothing measured well enough to write yet.")
        elif out:
            print(f"\nTo write these into people/{local.id}.toml: python -m town calibrate {local.id} --apply")
        return

    task = tasks.load(args.task)
    who = people.everyone() if args.locals == ["all"] else [people.load(i) for i in args.locals]
    print(f"DAY · {task.app} · {len(who)} local{'s' if len(who) != 1 else ''} · {mind.MODEL}")
    if args.date or args.year:
        days = year.sample(args.year) if args.year else sorted(date.fromisoformat(d) for d in args.date)
        summary = day.run_year(task, who, days, ROOT / "runs", args.watch, args.seed, pandemic=args.pandemic)
        results = Counter(k for d in summary for k in d["results"].values())
        for d in summary:
            print(f"  {d['label']:<60} {', '.join(d['results'].values())}")
        print(f"\n{', '.join(f'{v} {k.lower()}' for k, v in results.items())} · replay in runs/")
        return
    folder = ROOT / "runs" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    results = Counter(day.run_day(task, who, folder, args.watch, args.seed).values())
    print(f"\n{', '.join(f'{v} {k.lower()}' for k, v in results.items())} · replay in {folder.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
