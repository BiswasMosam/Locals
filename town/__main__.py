"""python -m town dashboard | python -m town people | python -m town run <app:task> <local ...|all> [--watch]"""
import argparse
import sys
from collections import Counter
from datetime import datetime

from . import day, mind, people, tasks
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
    args = ap.parse_args()

    if args.cmd == "dashboard":
        from .dashboard import serve
        return serve(args.port, not args.no_open)

    if args.cmd == "people":
        for l in people.everyone():
            print(f"{l.number:02d}  {l.id:<9} {f'{l.name}, {l.age}':<13} {l.job:<36} {l.limits.device:<7} {l.status}")
        return

    task = tasks.load(args.task)
    who = people.everyone() if args.locals == ["all"] else [people.load(i) for i in args.locals]
    folder = ROOT / "runs" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"DAY · {task.app} · {len(who)} local{'s' if len(who) != 1 else ''} · {mind.MODEL}")
    results = Counter(day.run_day(task, who, folder, args.watch, args.seed).values())
    print(f"\n{', '.join(f'{v} {k.lower()}' for k, v in results.items())} · replay in {folder.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
