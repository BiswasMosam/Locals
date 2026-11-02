"""One local, one task: see, think, act, until done, stuck or out of patience. A day is many of those."""
import hashlib
import json
import random
import time

from . import mind, tasks
from .feed import Feed
from .limits import slip, typo
from .people import ROOT
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


def size(path):
    return f"{path.stat().st_size / 1_048_576:.1f} MB"


def run(local, task, out, watch=False, seed=7, listen=None, stop=None):
    rng = random.Random(f"{seed}-{local.id}-{task.id}")
    out.mkdir(parents=True, exist_ok=True)
    inputs = tasks.make_files(task, out / "device")
    feed = Feed(out, local, task, listen)
    system = mind.system_prompt(local, task.story, inputs)
    limits, when_stuck = local.limits, local.habits["when_stuck"]
    history, seen, stuck_on, was_stuck, said_stuck_on = [], {}, set(), False, None
    outcome, thought = None, ""

    def finish(kind, says):
        nonlocal outcome
        outcome = kind
        feed.event(kind, says)

    with Web(task.url, limits.device, inputs, out / "device", watch) as web:
        feed.event("START", f"{local.job}, on a {limits.device}")
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
            act, target, text = decision["action"], decision.get("target"), decision.get("text", "")
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
            if act in ("tap", "type", "set") and target not in ids:
                feed.step(n, f"{act} [{target}]", thought, record, round(time.time() - began, 1))
                history.append(f"{act} on something that is not on the screen; nothing happened")
                continue

            hit = target
            if act == "tap":
                hit = slip(rng, limits.slip_rate, target, screen["items"])
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
    feed.close()
    return outcome


def give_up(when_stuck):
    if when_stuck == "quit":
        return "GAVE UP", "Gave up on the app."
    return "ASKED", "Would hand the device to someone else now."


def done_line(file, n, feed, was_stuck):
    saved = f"{file.name}, {size(file)} · " if file else ""
    return f"{saved}{n} steps · {feed.clock()}" + (" · after being stuck" if was_stuck else "")


def run_day(task, who, folder, watch=False, seed=7, listen=None, stop=None):
    """Sends each local to the task in turn; they share one model, so they take turns."""
    listen = listen or (lambda entry: None)
    ids = [l.id for l in who]
    meta = {"day": folder.name, "task": f"{task.app}: {task.id}", "ref": task.ref, "url": task.url,
            "locals": ids, "model": mind.MODEL}
    listen({"type": "day", "phase": "start", **meta})
    results = {}
    for local in who:
        if stop is not None and stop.is_set():
            break
        try:
            results[local.id] = run(local, task, folder / local.id, watch, seed, listen, stop)
        except Exception as e:
            results[local.id] = "ERROR"
            print(f"  ERROR      {type(e).__name__}: {e}")
            listen({"type": "event", "local": local.id, "kind": "ERROR", "says": f"{type(e).__name__}: {e}"[:300],
                    "at": "", "shot": None})
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "day.json").write_text(json.dumps({**meta, "results": results}, indent=2), encoding="utf-8")
    listen({"type": "day", "phase": "end", **meta, "results": results})
    return results
