"""The marks: the graders in a room score the talk on the room's rubric, each from what reached them.

A mark is only worth what it rests on, so every mark points at evidence: the parts of the talk that grader took in,
facts code measured, and moments in the room. A mark is dropped when its evidence does not exist, when its reason
does not talk about that evidence, or when it guesses; what a file cannot show (posture, gestures, eye contact) is
not marked at all. The room's own markers (hooked till the end, the room fell asleep, over time) then add or take
away the points the rubric gives them. Rules and sources: study/rooms.md.
"""
import re
import tomllib
from functools import cache

from . import mind
from .expertise import GUESS, short, tokens
from .feed import BOLD, DIM, RESET
from .limits import skim
from .room import ROOMS, system, told

UNSEEN = "posture, gestures and eye contact cannot be seen in a file, and the voice needs a recording"


@cache
def rubrics():
    return {r["id"]: r for r in tomllib.loads((ROOMS / "rubrics.toml").read_text(encoding="utf-8"))["rubric"]}


def schema(criteria, top):
    # Every string has a length: left open, a reason can loop ("This is a 4. The ask is clear. This is a 4...") until
    # the reply is cut off unread. An enum or a range on the criterion or the level can make the model run on too, so
    # those are checked by code instead.
    return {
        "type": "object",
        "properties": {
            "marks": {"type": "array", "maxItems": len(criteria), "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string", "maxLength": 60},
                    "level": {"type": "integer"},
                    "reason": {"type": "string", "maxLength": 300},
                    "about": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 8}},
                },
                "required": ["criterion", "level", "reason", "about"],
            }},
            "overall": {"type": "string", "maxLength": 400},
        },
        "required": ["marks", "overall"],
    }


def evidence(l, result):
    """What this grader can point at: the parts as they took them in, the measured facts, the room's moments."""
    ev = []
    parts = {p["id"]: p for p in result["parts"]}
    for t in l.took:
        p = parts[t["part"]]
        after = l.decided and int(t["part"][1:]) > int(l.decided[1:])
        if t["how"] == "not taking anything in":
            text = "they were not listening"
        elif t["how"] == "only glancing up":
            text = f'they only glanced up at the slide "{t["title"]}"'
        else:
            text = told({**t, "said": skim(t["said"], 90)}).replace("\n", " / ")
            text += f" ({t['how']})" if t["how"] != "listening" else ""
        if after:
            text += " (after they had made up their mind)"
        ev.append({"id": t["part"], "text": f"{text}", "at": p["start"]})
    ev += [{"id": i, "text": t} for i, t in result["measured"]]
    room_lines = [m["says"] for m in result["markers"]]
    room_lines += [f"{l.local.name} {e['kind'].lower()} at {e['part']}" + (f": {e['why']}" if e["why"] else "") for e in l.events]
    ev += [{"id": f"R{i}", "text": t} for i, t in enumerate(room_lines, 1)]
    return ev


def check(reply, criteria, ev, top):
    """Keeps a mark only if its criterion is one asked for, its level is on the scale, its evidence exists and its
    reason talks about that evidence without guessing. Returns (kept by criterion, dropped with the reason)."""
    ids = {e["id"]: e for e in ev}
    names = {k.lower(): c["id"] for c in criteria for k in (c["id"], c.get("name", c["id"]))}
    kept, dropped = {}, []
    for m in reply.get("marks", []):
        about = [str(a).strip("[] ").upper() for a in m.get("about", []) if str(a).strip("[] ")]
        reason = " ".join(str(m.get("reason", "")).split())
        level = m.get("level")
        m = {**m, "criterion": names.get(str(m.get("criterion", "")).strip().lower(), m.get("criterion"))}
        problem = ("is not a criterion here" if m["criterion"] not in names.values()
                   else "was already marked" if m["criterion"] in kept
                   else "is off the scale" if not isinstance(level, int) or not 1 <= level <= top
                   else "has no evidence" if not about or any(a not in ids for a in about)
                   else "guesses at what was not seen" if GUESS.search(reason)
                   else "does not talk about its evidence" if not tokens(reason) & set().union(*(tokens(ids[a]["text"]) for a in about))
                   else None)
        if problem:
            dropped.append({"criterion": m.get("criterion"), "reason": reason[:240], "why": problem})
            continue
        kept[m["criterion"]] = {"level": level, "reason": reason[:300], "about": about}
    return kept, dropped


def prompt(l, room, rubric, criteria, ev, top, about):
    levels = lambda c: "\n".join(f"    {top - i}: {d}" for i, d in enumerate(c["levels"]))
    crit = "\n".join(f"- {c['id']} ({c['name']}):\n{levels(c)}" for c in criteria)
    lines = "\n".join(f"[{e['id']}] {e['text']}" for e in ev)
    return (system(l, room, about).split("\n\nRules:")[0] + "\n\nNow they mark the talk they just heard. Rules:\n"
            "- Mark only from the evidence below: what they took in, what was measured, what happened in the room. If they "
            "missed parts, they mark on what they took in.\n"
            '- For every criterion, choose the level that fits, and in "about" the ids of the evidence it rests on, like P3 or M1.\n'
            '- "reason": one sentence about that evidence, in their own plain words. Do not guess at what is not there.\n'
            '- "overall": one or two sentences they would say to the speaker.',
            f"The rubric, {rubric['name']}:\n{crit}\n\nThe evidence:\n{lines}")


def marks(l, room, rubric, result, recorded, about, seed):
    """One grader's marks, checked; asked once more about anything the checks dropped."""
    top = len(rubric["criterion"][0]["levels"])
    criteria = [c for c in rubric["criterion"] if c.get("needs", "talk") != "voice" or recorded]
    unseen = [c for c in rubric["criterion"] if c not in criteria]
    ev = evidence(l, result)
    sys, user = prompt(l, room, rubric, criteria, ev, top, about)
    if recorded and any(c.get("needs") == "voice" for c in criteria):
        user += "\n\nOnly the voice was heard, not seen: mark delivery on the voice alone (pace, pauses, fillers)."
    shape = schema(criteria, top)
    first = mind.chat(sys, user, shape, seed, num_ctx=8192, default={"marks": [], "overall": "", "timed_out": True})
    silent = bool(first.get("timed_out"))  # no answer in time is not the same as marks that did not hold up
    kept, dropped = check(first, criteria, ev, top)
    overall = short(first.get("overall", ""))
    missing = [c for c in criteria if c["id"] not in kept]
    if missing:
        why = "\n".join(f'- {d["criterion"]}: "{d["reason"]}" was dropped because it {d["why"]}.' for d in dropped) or "- (none given)"
        again = mind.chat(sys, f"{user}\n\nSome marks did not hold up:\n{why}\nMark these again, keeping to the rules: "
                          f"{', '.join(c['id'] for c in missing)}.", shape, seed + 1, num_ctx=8192, default={"marks": []})
        more, dropped_again = check(again, missing, ev, top)
        kept.update(more)
        dropped += [{**d, "second try": True} for d in dropped_again]
    weights = {c["id"]: c.get("weight", 1) for c in rubric["criterion"]}
    scored = [c for c in criteria if c["id"] in kept]
    if scored:
        share = sum(kept[c["id"]]["level"] / top * weights[c["id"]] for c in scored) / sum(weights[c["id"]] for c in scored)
        base = round(sum(kept[c["id"]]["level"] for c in scored) / len(scored), 1) if rubric.get("average") else round(share * rubric["out_of"], 1)
    else:
        share, base = None, None
    found = {m["kind"] for m in result["markers"]}
    bonus = [(k, v) for k, v in rubric.get("markers", {}).items() if k in found]
    total = None if base is None else round(min(rubric["out_of"], max(0, base + sum(v for _, v in bonus))), 1)
    verdict = next((words for floor, words in rubric.get("verdict", []) if total is not None and total / rubric["out_of"] >= floor), "")
    return {"grader": l.local.id, "name": l.local.name, "number": l.local.number, "job": l.local.job, "marks": kept,
            "not marked": {c["id"]: UNSEEN for c in unseen}, "unsupported": [c["id"] for c in criteria if c["id"] not in kept],
            "dropped": dropped, "base": base, "markers": bonus, "total": total, "verdict": verdict, "overall": overall,
            "timed_out": silent}


def grade(room, result, listeners, recorded, about="", seed=7):
    """Every grader in the room marks the talk. Prints the marks and returns them."""
    if not room.get("rubric"):
        stayed = sum(min(l["trail"]) >= 50 for l in result["listeners"])
        got = sum(l["recall"].get("same") in ("yes", "partly") for l in result["listeners"])
        n = len(result["listeners"])
        print(f"\n{BOLD}MARKS{RESET}  A crowd gives no marks. {stayed} of {n} stayed with you all the way; {got} of {n} could say your point.")
        return {"rubric": None, "stayed": stayed, "remembered": got, "of": n}
    rubric = rubrics()[room["rubric"]]
    top = len(rubric["criterion"][0]["levels"])
    names = {c["id"]: c["name"] for c in rubric["criterion"]}
    print(f"\n{BOLD}MARKS{RESET}  {rubric['name']} · out of {rubric['out_of']} · {DIM}{rubric['source']}{RESET}")
    graders = [l for l in listeners if l.role == "grader"]
    out = []
    for i, l in enumerate(graders):
        g = marks(l, room, rubric, result, recorded, about, seed + 300 + i)
        out.append(g)
        head = (f"{g['total']:g} of {rubric['out_of']}" if g["total"] is not None else
                "no answer from the model in time: is something else using the graphics card? Run it again"
                if g["timed_out"] else "no mark held up")
        print(f"\n  {l.local.number:>3} {l.local.name.upper():<10} {BOLD}{head}{RESET}" + (f"  {g['verdict']}" if g["verdict"] else ""))
        for c in rubric["criterion"]:
            if c["id"] in g["marks"]:
                m = g["marks"][c["id"]]
                first = re.split(r"(?<=[.!?])\s+", m["reason"])[0]
                print(f"      {names[c['id']]:<34} {m['level']} of {top}  {DIM}{first[:170]}  [{', '.join(m['about'])}]{RESET}")
            elif c["id"] in g["not marked"]:
                print(f"      {names[c['id']]:<34} {DIM}not marked: {UNSEEN}{RESET}")
            elif not g["timed_out"]:
                print(f"      {names[c['id']]:<34} {DIM}no mark held up against the evidence{RESET}")
        for k, v in g["markers"]:
            print(f"      {('+' if v > 0 else '') + str(v):<4} {k}")
        if g["overall"]:
            print(f"      {DIM}\"{g['overall']}\"{RESET}")
        if g["dropped"]:
            print(f"      {DIM}{len(g['dropped'])} mark{'s' if len(g['dropped']) > 1 else ''} dropped by the checks{RESET}")
    totals = [g["total"] for g in out if g["total"] is not None]
    summary = {"rubric": rubric["id"], "out_of": rubric["out_of"], "graders": out}
    if totals:
        mean = round(sum(totals) / len(totals), 1)
        verdict = next((w for floor, w in rubric.get("verdict", []) if mean / rubric["out_of"] >= floor), "")
        spread = f" (from {min(totals):g} to {max(totals):g})" if len(totals) > 1 else ""
        print(f"\n  {BOLD}THE ROOM'S MARK{RESET}  {mean:g} of {rubric['out_of']}{spread}" + (f"  {verdict}" if verdict else ""))
        summary.update({"mean": mean, "low": min(totals), "high": max(totals), "verdict": verdict})
    return summary
