"""One local, one task: see, think, act, until done, stuck or out of patience. A day is many of those."""
import hashlib
import json
import random
import time
from dataclasses import replace
from datetime import datetime

from . import expertise, mind, tasks, year
from .android import Android
from .feed import Feed
from .limits import slip, typo
from .people import ROOT
from .watch import golden_path, name_of, norm
from .web import Web


def signature(screen):
    parts = [screen["url"], screen["blocks"],
             [(i["text"], i["hint"], i["active"], i["checked"], i["value"], i["disabled"]) for i in screen["items"]]]
    return hashlib.sha1(json.dumps(parts).encode()).hexdigest()


def label(screen, target):
    item = next((i for i in screen["items"] if i["id"] == target), None)
    if item is None:
        return f"[{target}]"
    words = item["text"] or item["hint"] or "icon"
    return f'[{target}] "{" ".join(words.split()[:4])}"'


def is_button(screen, target):
    """Setting a button just presses it (town/web.py), so it needs no value."""
    item = next((i for i in screen["items"] if i["id"] == target), None)
    return item is not None and item["role"] not in ("slider", "dropdown", "text box")


def size(path):
    return f"{path.stat().st_size / 1_048_576:.1f} MB"


def run(local, task, out, watch=False, seed=7, listen=None, stop=None, today=None, take=True):
    told = ""
    if task.platform == "android":
        local = replace(local, limits=replace(local.limits, device="phone"))  # an app on a phone is used on a phone
    if today is not None:
        local, told = year.shape(local, today)
        seed += today.day.toordinal() % 997  # a different date is a different day, not a replay
    rng = random.Random(f"{seed}-{local.id}-{task.id}")
    out.mkdir(parents=True, exist_ok=True)
    inputs = tasks.make_files(task, out / "device")
    feed = Feed(out, local, task, listen)
    system = mind.system_prompt(local, task.story, inputs, told)
    limits, when_stuck = local.limits, local.habits["when_stuck"]
    history, seen, stuck_on, was_stuck, said_stuck_on = [], {}, set(), False, None
    outcome, thought = None, ""
    path, along, left_at = golden_path(task), 0, set()  # your own recorded run, and how far along it they are

    def finish(kind, says):
        nonlocal outcome
        outcome = kind
        feed.event(kind, says)

    driver = Android if task.platform == "android" else Web
    with driver(task, limits.device, inputs, out / "device", watch) as web:
        feed.event("START", f"{local.job}, on a {limits.device}" + (f" · {local.situation['place']}" if today else ""))
        if told:
            feed.event("TODAY", told)
        for n in range(1, limits.patience_steps + 1):
            if stop is not None and stop.is_set():
                finish("STOPPED", "The day was stopped.")
                break
            screen = web.see()
            shot = out / f"step-{n:02d}.png"
            web.snapshot(shot)
            feed.shot = shot.relative_to(ROOT).as_posix()

            sig = signature(screen)
            seen[sig] = seen.get(sig, 0) + 1
            notes = []
            if web.downloads:
                notes.append("Saved on their device: " + ", ".join(f"{d.name} ({size(d)})" for d in web.downloads))
            if seen[sig] > limits.repeat_before_stuck:
                notes.append("They have tried things on this screen and nothing changed. They are getting frustrated.")
                if sig not in stuck_on:
                    stuck_on.add(sig)
                    was_stuck = True
                    feed.event("STUCK", "Kept landing on the same screen; nothing they tried changed it.")
                    if when_stuck in ("quit", "ask"):
                        finish(*give_up(when_stuck))
                        break
            if n >= limits.patience_steps - 1:
                notes.append("They are running out of patience.")

            began = time.time()
            decision = mind.decide(system, mind.describe(screen, local, history, notes), seed + n)
            act, text = decision["action"], decision.get("text", "")
            target = str(decision.get("target") or "").strip("[] ").upper() or None
            thought = decision["thought"].strip()
            record = {"step": n, "screen": screen, "decision": decision}

            if act == "done":
                ok, file = tasks.check(task, web, inputs)
                feed.step(n, "done", thought, record, round(time.time() - began, 1))
                if not task.done:
                    finish("SAYS DONE", f'"{thought}" Nothing to check it against, so this is their word only.')
                elif ok:
                    finish("DONE", done_line(file, n, feed, was_stuck))
                else:
                    finish("WRONG DONE", f'Believed it was done ("{thought}") but nothing right was saved.')
                break

            if act == "stuck":
                was_stuck = True
                feed.step(n, "stuck", thought, record, round(time.time() - began, 1))
                if said_stuck_on != sig:  # once per screen; the steps still show every repeat
                    said_stuck_on = sig
                    feed.event("STUCK", f'"{thought}"')
                if when_stuck in ("quit", "ask"):
                    finish(*give_up(when_stuck))
                    break
                history.append(f"felt stuck: {thought}")
                continue

            ids = {i["id"] for i in screen["items"]}
            if act in ("type", "set") and not text.strip() and not (act == "set" and is_button(screen, target)):
                # A finger on a slider always leaves it somewhere; an empty value is the model's slip, not theirs.
                feed.step(n, f"{act} [{target}] nothing", thought, record, round(time.time() - began, 1))
                history.append(f"tried to {act} {label(screen, target)} but put nothing in \"text\", so nothing changed; "
                               f"the {'words' if act == 'type' else 'new value, like 30,'} must go in \"text\"")
                continue
            if act in ("tap", "type", "set") and target not in ids:
                feed.step(n, f"{act} [{target}]", thought, record, round(time.time() - began, 1))
                history.append(f"{act} on something that is not on the screen; nothing happened")
                continue

            if path and act in ("tap", "type", "set"):
                # What they meant to use, before any slip. Going back to a step of your path is a retry;
                # a control you never used on your way through is where the screen led them off it.
                item = next(i for i in screen["items"] if i["id"] == target)
                on_path = [k for k, (key, _) in enumerate(path) if key == norm(name_of(item))]
                if on_path:
                    along = max(along, next((k + 1 for k in on_path if k >= along), along))
                elif along < len(path) and along not in left_at:
                    left_at.add(along)
                    feed.event("OFF PATH", f'Your path goes to "{path[along][1]}" next; they went for {label(screen, target)}.')

            hit = target
            if act == "tap":
                hit = slip(rng, limits.slip_rate, target, screen["items"], touch=limits.device == "phone")
                if hit != target:
                    feed.event("SLIP", f"Meant to tap {label(screen, target)}, hit {label(screen, hit)}.")
            if act == "type":
                text = typo(rng, limits.typo_rate, text)

            result = web.act(act, hit, text)
            line = f"{act} {label(screen, hit)}" if act in ("tap", "type", "set") else act
            if act in ("type", "set"):
                line += f" = {text}"
            record.update(hit=hit, typed=text, result=result)
            feed.step(n, line, thought, record, round(time.time() - began, 1))
            history.append(f"{line} → {result}")

            ok, file = tasks.check(task, web, inputs)
            if ok:
                finish("DONE", done_line(file, n, feed, was_stuck))
                break
        else:
            finish("GAVE UP", f'Out of patience after {limits.patience_steps} steps. Last thought: "{thought}"')

        web.snapshot(out / "end.png")
        observed = web.observe()
        (out / "observed.json").write_text(json.dumps(observed, indent=1), encoding="utf-8")
    if take and outcome != "STOPPED":
        try:  # their take comes after the run and never changes what happened in it
            expertise.take(local, task, out, feed.event, observed, web.downloads, inputs, seed, told)
        except Exception as e:
            print(f"  no take: {type(e).__name__}: {e}"[:200], flush=True)
    feed.close()
    return outcome


def give_up(when_stuck):
    if when_stuck == "quit":
        return "GAVE UP", "Gave up on the app."
    return "ASKED", "Would hand the device to someone else now."


def done_line(file, n, feed, was_stuck):
    saved = f"{file.name}, {size(file)} · " if file else ""
    return f"{saved}{n} steps · {feed.clock()}" + (" · after being stuck" if was_stuck else "")


def run_day(task, who, folder, watch=False, seed=7, listen=None, stop=None, today=None, index=None, take=True):
    """Sends each local to the task in turn; they share one model, so they take turns."""
    listen = listen or (lambda entry: None)
    ids = [l.id for l in who]
    meta = {"day": folder.name, "task": f"{task.app}: {task.id}", "ref": task.ref, "url": task.url,
            "locals": ids, "model": mind.MODEL, "index": index or [1, 1]}
    if today is not None:
        meta.update(date=today.day.isoformat(), today=today.label(), scene=today.scene())
    listen({"type": "day", "phase": "start", **meta})
    results = {}
    for local in who:
        if stop is not None and stop.is_set():
            break
        try:
            results[local.id] = run(local, task, folder / local.id, watch, seed, listen, stop, today, take)
        except Exception as e:
            results[local.id] = "ERROR"
            print(f"  ERROR      {type(e).__name__}: {e}", flush=True)
            entry = {"type": "event", "local": local.id, "kind": "ERROR", "says": f"{type(e).__name__}: {e}"[:300],
                     "at": "", "shot": None}
            (folder / local.id).mkdir(parents=True, exist_ok=True)
            with (folder / local.id / "feed.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            listen(entry)
    folder.mkdir(parents=True, exist_ok=True)
    board = expertise.panel(folder, list(results)) if take else None
    if board and board["points"]:
        print(f"\nWHAT THEIR JOBS LET THEM SEE · {board['kept']} of {board['proposed']} remarks kept by the checks")
        for g in board["points"][:8]:
            print(f"  {g['evidence'][:110]}")
            for r in g["remarks"]:
                print(f"    {r['by']}, {r['field']} ({r['standing']}): {r['remark']}")
    (folder / "day.json").write_text(json.dumps({**meta, "results": results, "panel": board}, indent=2), encoding="utf-8")
    listen({"type": "day", "phase": "end", **meta, "results": results, "panel": board, "ended_at": time.time()})
    return results


def run_year(task, who, days, runs, watch=False, seed=7, listen=None, stop=None, pandemic=None, take=True):
    """The same locals and task on several dates in one year, one day after another."""
    listen = listen or (lambda entry: None)
    listen({"type": "year", "phase": "start", "task": f"{task.app}: {task.id}", "dates": [d.isoformat() for d in days],
            "locals": [l.id for l in who], "pandemic": pandemic})
    summary = []
    for i, d in enumerate(days, 1):
        if stop is not None and stop.is_set():
            break
        folder = runs / datetime.now().strftime("%Y-%m-%d_%H%M%S")
        while folder.exists():
            time.sleep(1)
            folder = runs / datetime.now().strftime("%Y-%m-%d_%H%M%S")
        t = year.today(d, pandemic)
        results = run_day(task, who, folder, watch, seed, listen, stop, today=t, index=[i, len(days)], take=take)
        summary.append({"date": d.isoformat(), "label": t.label(), "day": folder.name, "results": results})
    listen({"type": "year", "phase": "end", "task": f"{task.app}: {task.id}", "days": summary, "ended_at": time.time()})
    return summary
