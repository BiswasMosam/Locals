"""Locals on screens real people used: Android in the Wild (Rawles and others 2023, study/validity.md).

Each step of the dataset is a phone screen, the goal its demonstrator was given, and what they did next. A local gets
the same goal and the same screen, as the words and icons the dataset found on it, and says what they would do. The
answer is scored with the dataset's own rule (its paper and action_matching.py): a tap matches when it lands in the
same detected element as the human's, the element grown to 240% of its size, or within 14% of the screen of it; a
scroll matches a scroll on the same axis; anything else matches the same kind of action.

What it measures: whether a local goes where a person who knew the task went. The demonstrators were paid contractors
given written instructions, a video tutorial and test runs, working an emulator with a mouse, so the score is about
finding the way, not about stumbling the way a newcomer does. Slips are left out on purpose: the score is what a local
meant to tap.

The data is read straight from the dataset's files (gzipped TFRecords) without TensorFlow: a TFRecord is a length,
a checksum and a tf.train.Example, and an Example is a small protobuf, decoded here by hand.
"""
import gzip
import json
import math
import random
import struct
import time
import urllib.request
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from . import mind
from .android import code
from .people import ROOT

DATA = ROOT / "data" / "aitw"
BUCKET = "https://storage.googleapis.com/gresearch/android-in-the-wild"
SHARDS = {"general": ["general/general-00003-of-00321", "general/general-00004-of-00321"],
          "single": ["single/single-00001-of-00252"]}
KINDS = {3: "type", 4: "touch", 5: "back", 6: "home", 7: "enter", 10: "done", 11: "impossible"}
# The dataset's own matching rule (action_matching.py).
TAP_DISTANCE, SWIPE_DISTANCE, GROW = 0.14, 0.04, 2.4  # an element grown to 240% of its height and width


# ---- reading the files -------------------------------------------------------------------------------------------

def _varint(b, i):
    shift = out = 0
    while True:
        x = b[i]
        i += 1
        out |= (x & 0x7F) << shift
        shift += 7
        if x < 0x80:
            return out, i


def _fields(b):
    i = 0
    while i < len(b):
        key, i = _varint(b, i)
        no, wire = key >> 3, key & 7
        if wire == 0:
            v, i = _varint(b, i)
        elif wire == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif wire == 5:
            v, i = b[i:i + 4], i + 4
        elif wire == 1:
            v, i = b[i:i + 8], i + 8
        else:
            raise ValueError(f"protobuf wire type {wire}")
        yield no, wire, v


def _feature(b):
    for no, _, v in _fields(b):
        if no == 1:  # bytes_list
            return [x for _, _, x in _fields(v)]
        if no == 2:  # float_list, packed or not
            out = []
            for _, wire, x in _fields(v):
                out += struct.unpack(f"<{len(x) // 4}f", x) if wire == 2 else struct.unpack("<f", x)
            return out
        if no == 3:  # int64_list, packed or not
            out = []
            for _, wire, x in _fields(v):
                if wire == 2:
                    j = 0
                    while j < len(x):
                        y, j = _varint(x, j)
                        out.append(y)
                else:
                    out.append(x)
            return out
    return []


def example(b):
    """A tf.train.Example as {name: [values]}."""
    out = {}
    for _, _, features in _fields(b):
        for _, _, entry in _fields(features):
            name = value = None
            for no, _, x in _fields(entry):
                if no == 1:
                    name = x.decode()
                else:
                    value = _feature(x)
            out[name] = value
    return out


def records(path):
    with gzip.open(path, "rb") as f:
        while len(head := f.read(12)) == 12:
            data = f.read(struct.unpack("<Q", head[:8])[0])
            f.read(4)
            yield data


def fetch(shard):
    """Downloads one shard of the dataset into data/aitw/ once (git ignores data/)."""
    path = DATA / (shard.split("/")[-1] + ".gz")
    if not path.exists():
        DATA.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {shard} from the dataset's public bucket…", flush=True)
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(f"{BUCKET}/{shard}", tmp)
        tmp.rename(path)
    return path


def step(ex):
    s = lambda k: ex[k][0].decode("utf-8", errors="replace") if ex.get(k) else ""
    pos = ex.get("image/ui_annotations_positions", [])
    return {
        "episode": s("episode_id"), "step": ex["step_id"][0], "length": ex["episode_length"][0], "goal": s("goal_info"),
        "kind": KINDS.get(ex["results/action_type"][0], str(ex["results/action_type"][0])),
        "touch": list(ex["results/yx_touch"]), "lift": list(ex["results/yx_lift"]), "typed": s("results/type_action"),
        "texts": [t.decode("utf-8", errors="replace") for t in ex.get("image/ui_annotations_text", [])],
        "types": [t.decode() for t in ex.get("image/ui_annotations_ui_types", [])],
        "boxes": [pos[i:i + 4] for i in range(0, len(pos), 4)],  # y, x, height, width, all as a share of the screen
        "size": (ex["image/height"][0], ex["image/width"][0]), "app": s("current_activity").split("/")[0],
        "pixels": ex["image/encoded"][0],
    }


def episodes(subset, seed=7, count=40):
    """Whole episodes from the subset's shards, a fixed random sample for a seed."""
    eps = {}
    for shard in SHARDS[subset]:
        for r in records(fetch(shard)):
            st = step(example(r))
            eps.setdefault(st["episode"], []).append(st)
    eps = [sorted(v, key=lambda s: s["step"]) for v in eps.values()]
    eps = [e for e in eps if [s["step"] for s in e] == list(range(len(e)))]  # only complete episodes
    rng = random.Random(f"aitw-{subset}-{seed}")
    rng.shuffle(eps)
    return eps[:count]


# ---- what a local sees -------------------------------------------------------------------------------------------

def swipe(st):
    (ty, tx), (ly, lx) = st["touch"], st["lift"]
    return math.dist((ty, tx), (ly, lx)) > SWIPE_DISTANCE


def human(st):
    """What the person did, in the town's words."""
    k = st["kind"]
    if k == "touch":
        if not swipe(st):
            return "tap"
        (ty, tx), (ly, lx) = st["touch"], st["lift"]
        return "scroll" if abs(ly - ty) >= abs(lx - tx) else "swipe"  # scrolls match on their axis alone
    return k


def screen(st):
    """The dataset's view of the screen (its OCR words and detected icons) as the items a local reads.
    Words on one line that sit close together are one label, as a person reads them."""
    h, w = st["size"]
    marks = []
    for text, kind, (y, x, bh, bw) in zip(st["texts"], st["types"], st["boxes"]):
        if kind == "TEXT" and not text.strip():
            continue
        marks.append({"text": text.strip() if kind == "TEXT" else "", "icon": "" if kind == "TEXT" else kind,
                      "y": y, "x": x, "h": bh, "w": bw})
    merged = []
    for m in sorted(marks, key=lambda m: (round(m["y"] + m["h"] / 2, 2), m["x"])):
        last = merged[-1] if merged else None
        if (last and m["text"] and last["text"] and not last["icon"]
                and abs((last["y"] + last["h"] / 2) - (m["y"] + m["h"] / 2)) < max(last["h"], m["h"]) * 0.5
                and 0 <= m["x"] - (last["x"] + last["w"]) < 0.04):
            right, bottom = max(last["x"] + last["w"], m["x"] + m["w"]), max(last["y"] + last["h"], m["y"] + m["h"])
            last["text"] += " " + m["text"]
            last["parts"].append(m)
            last["y"], last["x"] = min(last["y"], m["y"]), min(last["x"], m["x"])
            last["w"], last["h"] = right - last["x"], bottom - last["y"]
            continue
        merged.append({**m, "parts": [dict(m)]})
    items = []
    for m in merged:
        if m["icon"] in ("ICON_NAV_BAR_RECT", "ICON_NAV_BAR_CIRCLE", "ICON_V_BACKWARD"):
            continue  # the phone's own back and home keys: the town's back covers them, and home is not a town action
        looks = m["icon"].removeprefix("ICON_").replace("_", " ").lower()
        items.append({"id": code(len(items)), "role": "button", "text": m["text"][:300], "lines": [m["text"]] if m["text"] else [],
                      "hint": "", "looks": looks if m["icon"] else "", "disabled": False, "active": False, "checked": False,
                      "value": "", "x": round((m["x"] + m["w"] / 2) * w), "y": round((m["y"] + m["h"] / 2) * h),
                      "w": round(m["w"] * w), "h": round(m["h"] * h), "box": [m["y"], m["x"], m["h"], m["w"]]})
    return {"items": items, "blocks": [], "title": st["app"] or "Android", "url": f"aitw:{st['episode']}:{st['step']}",
            "scrollable": True, "at_bottom": False}


def story(st):
    return (f"{st['goal']}\nYou are on an Android phone. Do it the way you normally would.")


def said(st):
    """A step the person took, as it goes into the next screen's history."""
    k = human(st)
    if k == "tap":
        under = [(t.strip(), kind) for t, kind, (y, x, h, w) in zip(st["texts"], st["types"], st["boxes"])
                 if y <= st["touch"][0] <= y + h and x <= st["touch"][1] <= x + w]
        word = next((t for t, kind in under if kind == "TEXT" and t), "")
        icon = next((kind.removeprefix("ICON_").replace("_", " ").lower() for t, kind in under if kind != "TEXT"), "")
        return f'tapped "{word}"' if word else f"tapped the {icon} icon" if icon else "tapped the screen"
    return {"type": f'typed "{st["typed"]}"', "back": "went back", "home": "went to the home screen",
            "enter": "pressed enter", "scroll": "scrolled", "swipe": "swiped across the screen",
            "done": "said it was done", "impossible": "said it could not be done"}.get(k, k)


# ---- matching ----------------------------------------------------------------------------------------------------

def inside(point, box, grow=GROW):
    y, x, h, w = box
    cy, cx = y + h / 2, x + w / 2
    return abs(point[0] - cy) <= h * grow / 2 and abs(point[1] - cx) <= w * grow / 2


def matches(local_kind, point, st, boxes):
    """The dataset's rule: both taps land in the same grown element, or within 14% of the screen; a scroll matches a
    vertical scroll (the only way a local scrolls); other actions match on kind alone."""
    k = human(st)
    if local_kind == "tap":
        if k != "tap":
            return False
        touch = tuple(st["touch"])
        if math.dist(point, touch) <= TAP_DISTANCE:
            return True
        return any(inside(point, b) and inside(touch, b) for b in boxes)
    if local_kind == "scroll":
        return k == "scroll"
    return local_kind == k


TOWN = {"tap": "tap", "set": "tap", "type": "type", "scroll": "scroll", "back": "back", "done": "done",
        "stuck": "impossible", "wait": "wait"}


def ask(local, st, history, seed):
    """What a local would do on this screen: the town's two stages, the same prompt as a run, no slips."""
    sc = screen(st)
    system = mind.system_prompt(local, story(st))
    notes = []
    seen = mind.describe(sc, local, history, notes)
    noticed = None
    if mind.STAGES == 2:
        ids = {i["id"] for i in sc["items"]}
        noticed = [x for x in mind.notice(system, seen, local, seed + 500) if x in ids] or None
        if noticed:
            seen = mind.describe(sc, local, history, notes, only=set(noticed))
    from .day import misuse, read
    decision = mind.decide(system, seen, seed)
    act, text, target, thought = read(decision)
    retries = 0
    while (problem := misuse(act, text, target, sc, noticed)) and retries < 2:
        retries += 1
        decision = mind.decide(system, f"{seen}\n\nYour last answer could not be used: {problem}. Answer again.", seed + 1000 * retries)
        act, text, target, thought = read(decision)
    item = next((i for i in sc["items"] if i["id"] == target), None)
    point = (item["box"][0] + item["box"][2] / 2, item["box"][1] + item["box"][3] / 2) if item else None
    return {"act": act, "target": target, "text": text, "thought": thought, "noticed": noticed, "retries": retries,
            "unusable": bool(problem), "point": point, "label": (item["text"] or item["looks"]) if item else ""}


def judge(kind, point, unusable, st):
    """Whether a local's answer matches the human's, by the dataset's rule."""
    if unusable:
        return False
    if kind == "tap":
        return bool(point) and matches("tap", tuple(point), st, st["boxes"])
    return matches(kind, None, st, st["boxes"])


def reachable(st):
    """Whether any answer a local can give matches the human: their move exists in the town (no home, enter or
    sideways swipe) and, for a tap, lands near something the dataset detected on the screen."""
    k = human(st)
    if k in ("home", "enter", "swipe"):
        return False
    if k == "tap":
        return any(judge("tap", (i["box"][0] + i["box"][2] / 2, i["box"][1] + i["box"][3] / 2), False, st)
                   for i in screen(st)["items"])
    return True


def score(local, st, history, seed):
    a = ask(local, st, history, seed)
    kind = TOWN.get(a["act"], a["act"])
    return {**a, "kind": kind, "match": judge(kind, a["point"], a["unusable"], st)}


def save_png(st, path):
    """The dataset's screenshot (raw RGB) as a PNG, for looking at a miss."""
    from PIL import Image
    h, w = st["size"]
    Image.frombytes("RGB", (w, h), st["pixels"]).save(path)


def run(who, subsets=("general", "single"), count=20, seed=7, first_only=True, out=None):
    """Every local on the same screens; returns the folder with results.json."""
    from .day import unlimited
    out = out or ROOT / "runs" / "aitw" / f"{datetime.now():%Y-%m-%d_%H%M%S}"
    (out / "screens").mkdir(parents=True, exist_ok=True)
    cases = []
    for subset in subsets:
        for ep in episodes(subset, seed, count):
            # Demonstrators often pressed home first to start from a clean screen; their first move is what came after.
            first = next((s for s in ep if s["kind"] != "home"), None)
            for st in ([first] if first else []) if first_only else ep:
                history = [said(s) for s in ep[:st["step"]]]
                cases.append((subset, st, history))
    for subset, st, _ in cases:
        save_png(st, out / "screens" / f"{st['episode']}-{st['step']}.png")
    meta = {"model": mind.MODEL, "stages": mind.STAGES, "seed": seed, "first_only": first_only,
            "cases": [{"subset": s, "episode": st["episode"], "step": st["step"], "goal": st["goal"], "human": human(st),
                       "said": said(st), "app": st["app"]} for s, st, _ in cases]}
    results = []
    for local in who:
        for name, person in (("as themselves", local), ("no limits", unlimited(local))):
            for n, (subset, st, history) in enumerate(cases):
                began = time.time()
                r = score(person, st, history, seed + n)
                results.append({"local": local.id, "as": name, "subset": subset, "case": n, "human": human(st),
                                "secs": round(time.time() - began, 1), **r})
                mark = "MATCH" if r["match"] else "     "
                print(f"  {local.id:<10} {name:<14} {mark} human {said(st)[:40]:<40} local {r['act']} "
                      f"{('[' + str(r['target']) + '] ' + r['label'])[:34] if r['target'] else ''}", flush=True)
                (out / "results.json").write_text(json.dumps({**meta, "results": results}, indent=1), encoding="utf-8")
    return out


_all = {}


def lookup(subset, episode, number):
    if subset not in _all:
        _all[subset] = {(e[0]["episode"]): e for e in episodes(subset, 0, 10**6)}
    return _all[subset][episode][number]


def summary(folder):
    """The score of a saved run, matched again with the current rule, so a fix to the rule never needs a rerun."""
    path = Path(folder) / "results.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = [lookup(c["subset"], c["episode"], c["step"]) for c in data["cases"]]
    for c, st in zip(data["cases"], cases):
        c["human"], c["reachable"] = human(st), reachable(st)
    rows = data["results"]
    for r in rows:
        r["match"] = judge(r["kind"], r["point"], r["unusable"], cases[r["case"]])
        r["human"], r["reachable"] = data["cases"][r["case"]]["human"], data["cases"][r["case"]]["reachable"]
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    pct = lambda rs: f"{sum(r['match'] for r in rs)} of {len(rs)} ({100 * sum(r['match'] for r in rs) / max(1, len(rs)):.0f}%)"
    can = sum(c["reachable"] for c in data["cases"])
    lines = [f"{len(cases)} screens from Android in the Wild ({'every step' if not data['first_only'] else 'first moves'}) · "
             f"{data['model']}, {data['stages']} stage(s) · a local's answer can match the human on {can} of them"]
    for who in dict.fromkeys(r["local"] for r in rows):
        line = f"  {who:<12}"
        for name in ("as themselves", "no limits"):
            rs = [r for r in rows if r["local"] == who and r["as"] == name]
            line += f"{name}: {pct(rs):<18}" if rs else ""
        lines.append(line)
    for name in ("as themselves", "no limits"):
        rs = [r for r in rows if r["as"] == name]
        if rs:
            lines.append(f"  {'everyone':<12}{name}: {pct(rs)}; where a match was possible: {pct([r for r in rs if r['reachable']])}")
    lines.append("  by part of the dataset (as themselves, no limits):")
    for sub in dict.fromkeys(c["subset"] for c in data["cases"]):
        a = [r for r in rows if r["as"] == "as themselves" and r["subset"] == sub]
        b = [r for r in rows if r["as"] == "no limits" and r["subset"] == sub]
        lines.append(f"    {sub:<12}{pct(a):<18}{pct(b)}")
    lines.append("  by what the human did (as themselves, no limits):")
    for k in sorted({c["human"] for c in data["cases"]}):
        a = [r for r in rows if r["as"] == "as themselves" and r["human"] == k]
        b = [r for r in rows if r["as"] == "no limits" and r["human"] == k]
        lines.append(f"    {k:<12}{pct(a):<18}{pct(b)}")
    locals_did = {}
    for r in rows:
        locals_did[r["kind"]] = locals_did.get(r["kind"], 0) + 1
    lines.append("  what the locals did: " + ", ".join(f"{k} {v}" for k, v in sorted(locals_did.items(), key=lambda x: -x[1])))
    return "\n".join(lines)
