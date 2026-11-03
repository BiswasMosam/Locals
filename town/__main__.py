"""python -m town dashboard | people | run <app:task> <local ...|all> | watch <app:task> --golden|--for <local> | calibrate <local>
| rooms | room <room> <files> | grade <room> <files>"""
import argparse
import re
import sys
from collections import Counter
from datetime import date, datetime

from . import day, mind, people, tasks, year
from .people import ROOT


def main():
    if hasattr(sys.stdout, "reconfigure"):
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
    run.add_argument("--no-take", action="store_true", help="skip asking each local what their job let them notice")
    see = sub.add_parser("watch", help="record a real person doing a task: you for the golden path, or someone standing in for a local")
    see.add_argument("task", help="app:task, for example pixelshift:small-jpg")
    who = see.add_mutually_exclusive_group(required=True)
    who.add_argument("--golden", action="store_true", help="you, doing it the way it is meant to be done")
    who.add_argument("--for", dest="local", help="the local this person stands in for, for example prakash")
    see.add_argument("--device", choices=["phone", "laptop"], help="screen size for a web app (default: the local's, or phone)")
    see.add_argument("--minutes", type=int, default=15, help="stop recording after this long")
    ask = sub.add_parser("take", help="ask the locals of a past day again what their jobs let them notice")
    ask.add_argument("day", help="the day's folder in runs/, for example 2026-11-03_144319")
    ask.add_argument("locals", nargs="*", help="local ids (default: everyone that day)")
    sub.add_parser("report", help="how the town is doing across every saved day, against real people's benchmark")
    abl = sub.add_parser("ablate", help="run locals as themselves and again with no limits, to see what the limits change")
    abl.add_argument("task", help="app:task, for example pixelshift:small-jpg")
    abl.add_argument("locals", nargs="+", help="local ids, or all")
    abl.add_argument("--seed", type=int, default=7)
    der = sub.add_parser("derive", help="set reading, slips and typos from published studies and each local's traits")
    der.add_argument("--apply", action="store_true", help="write the traits and numbers into everyone's file")
    sub.add_parser("rooms", help="the rooms a talk can be given in, and who sits in each")
    for name, text in (("room", "give a talk to a room of locals: who stays with you, who drifts, who falls asleep"),
                       ("grade", "give a talk to a room, then let its graders mark it")):
        talk = sub.add_parser(name, help=text)
        talk.add_argument("room", help="class, review, interview, boardroom, pitch or crowd")
        talk.add_argument("files", nargs="+", help="a deck (.pdf or .pptx), a speech (.txt, .md or a recording like .m4a), or one of each")
        talk.add_argument("--minutes", type=float, help="how long the talk runs, when there is no recording to time it")
        talk.add_argument("--point", help="the one thing you want them to take away (default: read from the talk)")
        talk.add_argument("--about", help="what the talk is for, like the role you are interviewing for")
        talk.add_argument("--seed", type=int, default=7)
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

    if args.cmd == "take":
        import json
        from . import expertise
        folder = ROOT / "runs" / args.day
        if not (folder / "day.json").exists():
            raise SystemExit(f"No day called {args.day} in runs/")
        meta = json.loads((folder / "day.json").read_text(encoding="utf-8"))
        task = tasks.load(meta["ref"])
        for local_id in args.locals or meta["locals"]:
            expertise.retake(folder, people.load(local_id), task)
        board = expertise.panel(folder, args.locals or meta["locals"])
        print(f"\n{board['kept']} of {board['proposed']} remarks kept by the checks")
        meta["panel"] = board
        (folder / "day.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return

    if args.cmd == "ablate":
        import json
        task = tasks.load(args.task)
        who = people.everyone() if args.locals == ["all"] else [people.load(i) for i in args.locals]
        mind_name = re.sub(r"[^a-z0-9.]+", "-", f"{mind.MODEL}-{mind.STAGES}stage".lower())
        folder = ROOT / "runs" / "ablation" / f"{datetime.now():%Y-%m-%d_%H%M%S}_{mind_name}"  # kept out of the town's report
        both = {}
        for name, crowd in (("as themselves", who), ("no limits", [day.unlimited(l) for l in who])):
            print(f"\n==== {name.upper()} ====")
            day.run_day(task, crowd, folder / name.replace(" ", "-"), seed=args.seed, take=False)
            both[name] = {l.id: json.loads((folder / name.replace(" ", "-") / l.id / "run.json").read_text(encoding="utf-8")) for l in who}
        lines = [f"\n{'':<12}{'as themselves':<24}{'no limits':<24}"]
        for l in who:
            a, b = both["as themselves"][l.id], both["no limits"][l.id]
            lines.append(f"{l.id:<12}{a['outcome'] + ' in ' + str(a['steps']):<24}{b['outcome'] + ' in ' + str(b['steps']):<24}")
        for name, runs in both.items():
            done = [r for r in runs.values() if r["outcome"] in ("DONE", "SAYS DONE")]
            lines.append(f"{name:<14} finished {len(done)} of {len(runs)}, {sum(r['steps'] for r in runs.values()) / len(runs):.1f} steps on average")
        (folder / "summary.json").write_text(json.dumps(both, indent=1), encoding="utf-8")
        print("\n".join(lines) + f"\n\nSaved in {folder.relative_to(ROOT)}")
        return

    if args.cmd == "report":
        from .report import report
        print(report(ROOT / "runs"))
        return

    if args.cmd == "derive":
        from . import derive
        print(f"{'':<14}{'education':<10} {'conditions':<30} read  slip  typo   (was)")
        for l in people.everyone():
            t = derive.traits(l)
            v = derive.derive(l, t)
            was = f"{l.limits.read_words} {l.limits.slip_rate:.2f} {l.limits.typo_rate:.2f}"
            print(f"{l.number:02d} {l.id:<10} {t['education']:<10} {', '.join(t['conditions']) or '-':<30} "
                  f"{v['read_words']:>4}  {v['slip_rate']:.2f}  {v['typo_rate']:.2f}   ({was})")
            if args.apply:
                derive.write(l, t, v)
        print("\nWritten into people/." if args.apply else "\nTo write these into people/: python -m town derive --apply")
        return

    if args.cmd == "rooms":
        from .room import rooms
        for r in rooms().values():
            seats = ", ".join(f"{s['local']}{' (grades)' if s['role'] == 'grader' else ''}" for s in r["seats"])
            print(f"{r['id']:<10} {r['name']:<24} {r.get('minutes', '?'):>3} min  {r.get('rubric') or 'no marks':<19} {seats}")
        return

    if args.cmd in ("room", "grade"):
        import json
        from . import room as rooms, talk as talks
        place = rooms.load(args.room)
        talk = talks.load(args.files, args.minutes)
        out = rooms.folder(place["id"])
        result, listeners = rooms.listen(place, talk, args.about or "", args.point or "", args.seed, out)
        if args.cmd == "grade":
            from .grade import grade
            result["grade"] = grade(place, result, listeners, talk.recorded, args.about or "", args.seed)
            (out / "room.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved in {out.relative_to(ROOT)}")
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
        summary = day.run_year(task, who, days, ROOT / "runs", args.watch, args.seed, pandemic=args.pandemic, take=not args.no_take)
        results = Counter(k for d in summary for k in d["results"].values())
        for d in summary:
            print(f"  {d['label']:<60} {', '.join(d['results'].values())}")
        print(f"\n{', '.join(f'{v} {k.lower()}' for k, v in results.items())} · replay in runs/")
        return
    folder = ROOT / "runs" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    results = Counter(day.run_day(task, who, folder, args.watch, args.seed, take=not args.no_take).values())
    print(f"\n{', '.join(f'{v} {k.lower()}' for k, v in results.items())} · replay in {folder.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
