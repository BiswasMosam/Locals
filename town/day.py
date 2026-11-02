"""One local, one task: see, think, act, until done, stuck or out of patience."""
import hashlib
import json
import random

from . import mind, tasks
from .feed import Feed
from .limits import slip, typo
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


def run(local, task, out, watch=False, seed=7):
    rng = random.Random(f"{seed}-{local.id}-{task.id}")
    out.mkdir(parents=True, exist_ok=True)
    inputs = tasks.make_files(task, out / "device")
    feed = Feed(out, local, task)
    system = mind.system_prompt(local, task.story)
    limits, when_stuck = local.limits, local.habits["when_stuck"]
    history, seen, stuck_on, was_stuck = [], {}, set(), False
    outcome = None

    with Web(task.url, limits.device, inputs, out / "device", watch) as web:
        for n in range(1, limits.patience_steps + 1):
            screen = web.see()
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
                        outcome = "GAVE UP" if when_stuck == "quit" else "ASKED"
                        feed.event(outcome, "Gave up on the app." if when_stuck == "quit" else "Would hand the device to someone else now.")
                        break
            if n >= limits.patience_steps - 1:
                notes.append("They are running out of patience.")

            web.snapshot(out / f"step-{n:02d}.png")
            decision = mind.decide(system, mind.describe(screen, local, history, notes), seed + n)
            act, target, text = decision["action"], decision.get("target"), decision.get("text", "")
            thought = decision["thought"].strip()
            record = {"step": n, "screen": screen, "decision": decision}

            if act == "done":
                ok, file = tasks.check(task, web, inputs)
                feed.step(n, "done", thought, record)
                if ok:
                    outcome = "DONE"
                    feed.event("DONE", f"{file.name}, {size(file)} · {n} steps · {feed.clock()}" + (" · after being stuck" if was_stuck else ""))
                else:
                    outcome = "WRONG DONE"
                    feed.event("WRONG DONE", f'Believed it was done ("{thought}") but nothing right was saved.')
                break

            if act == "stuck":
                was_stuck = True
                feed.step(n, "stuck", thought, record)
                feed.event("STUCK", f'"{thought}"')
                if when_stuck in ("quit", "ask"):
                    outcome = "GAVE UP" if when_stuck == "quit" else "ASKED"
                    feed.event(outcome, "Gave up on the app." if when_stuck == "quit" else "Would hand the device to someone else now.")
                    break
                history.append(f"felt stuck: {thought}")
                continue

            ids = {i["id"] for i in screen["items"]}
            if act in ("tap", "type", "set") and target not in ids:
                feed.step(n, f"{act} [{target}]", thought, record)
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
            line = f"{act} {label(screen, hit)}" if hit is not None else act
            if act in ("type", "set"):
                line += f" = {text}"
            record.update(hit=hit, typed=text, result=result)
            feed.step(n, line, thought, record)
            history.append(f"{line} → {result}")

            ok, file = tasks.check(task, web, inputs)
            if ok:
                outcome = "DONE"
                feed.event("DONE", f"{file.name}, {size(file)} · {n} steps · {feed.clock()}" + (" · after being stuck" if was_stuck else ""))
                break
        else:
            outcome = "GAVE UP"
            feed.event("GAVE UP", f'Out of patience after {limits.patience_steps} steps. Last thought: "{thought}"')

        web.snapshot(out / "end.png")
    feed.close()
    return outcome
