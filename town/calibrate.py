"""From watching real people to a local's limits: what their recorded runs say, number by number.

A watched run stands in for one local (python -m town watch <task> --for <local>). Only what a
recording can show is measured: steps, taps that hit nothing, corrections while typing, repeated
tries and giving up. How much a person reads is not visible in taps, so read_words stays with the
interview.
"""
import json
import re
from datetime import date
from statistics import median

from .people import PEOPLE
from .watch import OBSERVED, name_of, norm

MIN_TAPS, MIN_KEYS = 10, 20  # below these, a rate is noise, so the draft number stays


def measure(run):
    """Counts from one recording. Typing a word is one step, as it is for a local."""
    steps = taps = missed = keys = erased = 0
    longest = streak = 0
    last_name, typing = None, False
    for e in run["events"]:
        kind = e["kind"]
        if kind in ("key", "erase"):
            keys += kind == "key"
            erased += kind == "erase"
            if not typing:
                steps += 1
                typing = True
            continue
        typing = False
        if kind == "nav":
            last_name, streak = None, 0
            continue
        steps += 1
        if kind == "tap":
            taps += 1
            missed += not e.get("control")
            name = norm(name_of(e)) if e.get("control") else None
            streak = streak + 1 if name and name == last_name else 1
            longest = max(longest, streak)
            last_name = name
    return {"outcome": run["outcome"], "steps": steps, "secs": run["secs"], "taps": taps, "missed": missed,
            "keys": keys, "erased": erased, "longest_repeat": longest}


def runs_for(local_id):
    folder = OBSERVED / local_id
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))] if folder.exists() else []


def suggest(local, measures):
    """New limits where the recordings say enough, with the reason for each; None where they do not."""
    out = {}
    counted = [m for m in measures if m["outcome"] in ("DONE", "SAYS DONE", "GAVE UP")]
    gave_up = [m["steps"] for m in counted if m["outcome"] == "GAVE UP"]
    finished = [m["steps"] for m in counted if m["outcome"] != "GAVE UP"]
    if gave_up:
        out["patience_steps"] = (int(median(gave_up)), f"gave up after {', '.join(map(str, gave_up))} steps")
    elif finished and max(finished) > local.limits.patience_steps:
        out["patience_steps"] = (max(finished), f"finished in up to {max(finished)} steps without giving up, so at least that")
    else:
        out["patience_steps"] = None
    # Someone who taps the same thing three times before trying anything else put up with two repeats.
    repeats = [m["longest_repeat"] for m in measures if m["taps"]]
    tries = f"tapped one control up to {max(repeats)} times in a row" if repeats and max(repeats) > 1 else "never tapped the same control twice in a row"
    out["repeat_before_stuck"] = (max(1, min(4, int(median(repeats)) - 1)), tries) if repeats else None
    taps, missed = sum(m["taps"] for m in measures), sum(m["missed"] for m in measures)
    out["slip_rate"] = (round(missed / taps, 2), f"{missed} of {taps} taps hit nothing") if taps >= MIN_TAPS else None
    keys, erased = sum(m["keys"] for m in measures), sum(m["erased"] for m in measures)
    out["typo_rate"] = (round(erased / keys, 2), f"{erased} corrections in {keys} keys") if keys >= MIN_KEYS else None
    out["read_words"] = None
    return out


def report(local):
    runs = runs_for(local.id)
    if not runs:
        return None, f"No watched runs for {local.name} yet. Record one: python -m town watch <task> --for {local.id}"
    measures = [measure(r) for r in runs]
    tally = {}
    for m in measures:
        tally[m["outcome"]] = tally.get(m["outcome"], 0) + 1
    lines = [f"{local.tag}  {local.job} · {len(runs)} watched run{'s' * (len(runs) != 1)} "
             f"({', '.join(f'{v} {k.lower()}' for k, v in tally.items())})", "",
             f"  {'':<20}{'draft':>7}{'measured':>10}   from"]
    out = suggest(local, measures)
    for key in ("read_words", "patience_steps", "repeat_before_stuck", "slip_rate", "typo_rate"):
        draft = getattr(local.limits, key)
        if out[key] is None:
            why = "not visible in taps; the interview sets it" if key == "read_words" else "not enough recorded yet"
            lines.append(f"  {key:<20}{draft:>7}{'':>10}   {why}")
        else:
            value, why = out[key]
            lines.append(f"  {key:<20}{draft:>7}{value:>10}   {why}")
    return out, "\n".join(lines)


def apply(local, out, n_runs):
    """Writes the measured numbers into the local's file; the rest keep their draft guesses."""
    path = PEOPLE / f"{local.id}.toml"
    text = path.read_text(encoding="utf-8")
    measured = [k for k, v in out.items() if v is not None]
    for key in measured:
        text = re.sub(rf"(?m)^{key} = .*$", f"{key} = {out[key][0]}", text)
    note = (f"# {', '.join(measured)} measured from {n_runs} watched run{'s' * (n_runs != 1)} on {date.today().isoformat()}; "
            f"the rest are draft guesses from the profile.")
    text = re.sub(r"(?m)^# (Draft numbers guessed|.* measured from \d+ watched run).*$", note, text)
    path.write_text(text, encoding="utf-8")
    return measured
