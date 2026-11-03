"""Their take: after a run, a local says what their job let them notice, pointing at evidence.

The model only puts the take into words. What a local can point at is gathered by code (the screens they
saw, moments in their run, their job's words, measurements), what they may cite comes from the study, and
code drops any remark whose evidence or citation does not exist. Rules and sources: study/expertise.md.
"""
import json
import re
import tomllib
import zipfile
from functools import cache
from pathlib import Path

from . import mind
from .people import ROOT

LENSES = ROOT / "expertise" / "lenses.toml"
TAG = re.compile(r"`?\[[IODAPG]\]`?")
KINDS = ["wrong word", "error in my field", "claim", "technical", "the result", "unclear"]
BASIS = {"S": "seen", "R": "their run", "W": "their words", "M": "measured"}

TAKE = {
    "type": "object",
    "properties": {
        "take": {"type": "string"},
        "remarks": {"type": "array", "maxItems": 3, "items": {
            "type": "object",
            "properties": {
                "about": {"type": "array", "items": {"type": "string"}},
                "kind": {"type": "string", "enum": KINDS},
                "remark": {"type": "string"},
                "cites": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["about", "kind", "remark", "cites"],
        }},
    },
    "required": ["take", "remarks"],
}


@cache
def data():
    return tomllib.loads(LENSES.read_text(encoding="utf-8"))


def lens_for(local):
    group = Path(local.profile).stem
    return next((l for l in data()["lens"] if group in l["who"]), None)


def references(lens):
    refs = {r["id"]: r for r in data()["reference"]}
    return [refs[i] for i in lens["cites"]]


def glossary(local):
    """Section 7 of the local's profile: (what they say, what an app might say instead)."""
    path = ROOT / local.profile
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    part = re.search(r"## 7\. Their words\n(.*?)(\n## |\Z)", text, re.S)
    pairs = []
    for row in (part.group(1) if part else "").splitlines():
        cells = [TAG.sub("", c).strip() for c in row.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0] and not set(cells[0]) <= set("-") and cells[0] != "They say":
            pairs.append((cells[0], cells[1]))
    return pairs


# ---------- Evidence ----------

def read_jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8")] if path.exists() else []


def screens_seen(steps):
    """Every line of text on the screens they looked at, once each: where it first appeared and what it was."""
    lines = {}
    for s in steps:
        screen = s["screen"]
        found = [(b, "text") for b in screen["blocks"]]
        for i in screen["items"]:
            if i["text"]:
                found += [(line, f"on a {i['role']}") for line in i.get("lines") or [i["text"]]]
            elif i["hint"]:
                found.append((i["hint"], f"the hidden name of a {i['role']} with no visible words"))
        for line, what in found:
            line = " ".join((line or "").split())[:160]
            if line and line not in lines:
                lines[line] = {"step": s["step"], "what": what}
    return lines


def file_facts(path, inputs):
    """What a photographer would check about a saved file. Pillow reads it; nothing is guessed."""
    from PIL import Image, JpegImagePlugin
    facts, size = [], path.stat().st_size
    original = min((p.stat().st_size for p in inputs), default=0)
    share = f", {size / original:.0%} of the original {original / 1_048_576:.1f} MB" if original else ""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
        kinds = sorted({Path(n).suffix.lower().lstrip(".") for n in names})
        return [f"Saved {path.name}: a ZIP of {len(names)} files ({', '.join(kinds)}), {size / 1_048_576:.1f} MB{share}."]
    try:
        im = Image.open(path)
    except Exception:
        return [f"Saved {path.name}, {size / 1_048_576:.2f} MB{share}; not an image."]
    real = (im.format or "?").upper().replace("JPEG", "JPG")
    ext = path.suffix.lower().lstrip(".").upper().replace("JPEG", "JPG")
    facts.append(f"Saved {path.name}: really a {real} file{'' if real == ext else f', though named .{ext.lower()}'},"
                 f" {im.width} x {im.height} pixels, {size / 1_048_576:.2f} MB{share}.")
    source = next((Image.open(p) for p in inputs if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".heic", ".tif", ".tiff")), None)
    if source and (source.width, source.height) != (im.width, im.height):
        facts.append(f"The picture was resized from {source.width} x {source.height} to {im.width} x {im.height}.")
    if real == "JPG":
        q = jpeg_quality(im)
        sampling = {0: "4:4:4", 1: "4:2:2", 2: "4:2:0"}.get(JpegImagePlugin.get_sampling(im), "unknown")
        facts.append(f"JPG quality about {q}, colour subsampling {sampling}." if q else f"JPG colour subsampling {sampling}.")
    exif = im.getexif()
    had = source is not None and (len(source.getexif()) or "icc_profile" in source.info)
    facts.append(("It keeps EXIF data" + (", including a GPS location" if 34853 in exif else "") if len(exif) else "It has no EXIF data")
                 + ("; a colour profile is embedded." if "icc_profile" in im.info else "; no colour profile is embedded.")
                 + ("" if had else " (The original had neither.)"))
    return facts


def jpeg_quality(im):
    """Estimates the encoder's quality setting from the luminance quantisation table (IJG scaling)."""
    STD = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29,
           51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92, 49, 64, 78, 87, 103, 121,
           120, 101, 72, 92, 95, 98, 112, 100, 103, 99]
    tables = getattr(im, "quantization", None) or {}
    if 0 not in tables:
        return None
    scale = 100 * sum(tables[0]) / sum(STD)
    q = (200 - scale) / 2 if scale <= 100 else 5000 / scale
    return max(1, min(100, round(q)))


CLAIM = re.compile(r"\b(nothing leaves|never leaves|leaves your device|on your device|in your browser|no uploads?|not uploaded|"
                   r"private|privacy|secure|guarantee\w*|100 ?%|free|we (?:do not|don't) (?:store|keep|share))\b", re.I)
POLICY = re.compile(r"\b(privacy|terms|policy|consent|cookies?|data protection|personal data)\b", re.I)
UNIT = re.compile(r"\b\d+(?:\.\d+)?\s?(?:MB|KB|GB|MiB|KiB|px|%|mm|cm|kg|ms|dpi)\b")
WESTERN = re.compile(r"\b\d{1,3}(?:,\d{3}){2,}\b")
INDIAN = re.compile(r"\b\d{1,2}(?:,\d{2})+,\d{3}\b")
DATE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
MONEY = re.compile(r"(\$|USD|US\$|₹|\bRs\.?|\bINR)\s?\d")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
DATA_CLAIM = re.compile(r"leave|upload|device|browser|private|privacy|store|keep|share", re.I)
LONG_SENTENCE = 20  # a line drawn for the reading measure, not a standard (study/expertise.md)
GENERIC = {"small", "large", "select", "review", "preview", "form", "message", "edit", "edits", "changes", "file", "files",
           "task", "update", "order", "item", "user", "document", "payment", "plan", "group", "notes", "system", "website",
           "admin", "upload", "download", "check in", "collection", "pack", "records", "team", "manager", "patient", "status"}


def measure(instruments, seen, observed, downloads, inputs, task, steps):
    """The measurements this local's expertise gives them, as plain sentences."""
    text, out = list(seen), []
    if "claims" in instruments:
        sent = None
        if observed.get("platform") == "web" and task.files:
            ups = observed.get("uploads", [])
            sent = (f"{len(ups)} request(s) carried a file or large body off the device, to {', '.join(sorted({u['host'] for u in ups}))}."
                    if ups else "No request carried a file off the device during the run (every request was checked).")
        # A claim about data is shown next to what the network actually did, so it is judged on facts.
        for t in [t for t in text if CLAIM.search(t)][:3]:
            out.append(f'Claim on screen: "{t}".' + (f" {sent}" if sent and DATA_CLAIM.search(t) else ""))
        takes_data = bool(task.files) or any(i["role"] == "text box" for s in steps for i in s["screen"]["items"])
        if takes_data and not any(POLICY.search(t) for t in text):
            out.append("No privacy notice, terms or consent text on any screen they saw, though the app took their "
                       + ("files." if task.files else "typing."))
        if sent:
            out.append(sent)
    if "file" in instruments:
        for d in downloads:
            out += file_facts(d, inputs)
        if task.files and not downloads:
            out.append("No file was saved on the device.")
    if "web" in instruments:
        if observed.get("platform") == "web":
            errors = observed.get("console", []) + observed.get("errors", [])
            out.append(f"{len(errors)} error(s) in the browser console" + (f', first: "{errors[0][:100]}".' if errors else "."))
            failed = observed.get("failed", [])
            if failed:
                out.append(f"{len(failed)} request(s) failed, first: {failed[0]['url'][:80]} ({failed[0]['why']}).")
            if observed.get("lcp") is not None:
                out.append(f"Largest content appeared after {observed['lcp'] / 1000:.1f} s; layout shift {observed.get('cls', 0):.2f};"
                           f" {observed.get('bytes', 0) / 1024:.0f} KB transferred on the last page.")
        unit = "dp" if observed.get("platform") == "android" else "CSS px"
        floor = 48 if unit == "dp" else 24
        items = {}
        for s in steps:
            for i in s["screen"]["items"]:
                items.setdefault(i["text"] or i["hint"] or f"({i['x']},{i['y']})", i)
        # On Android an unlabelled control's "hint" is only where it sits, which no screen reader can say.
        unnamed = [n for n, i in items.items() if not i["text"] and i["role"] != "text box"
                   and not (i["hint"] and observed.get("platform") == "web")]
        if unnamed:
            out.append(f"{len(unnamed)} control(s) with no name a screen reader could read" + (f", at {unnamed[0]}." if unnamed[0] else "."))
        small = [(n, i) for n, i in items.items() if "w" in i and min(i["w"], i["h"]) < floor]
        if small:
            n, i = small[0]
            out.append(f"{len(small)} control(s) smaller than {floor} x {floor} {unit}; first: \"{n[:40]}\" at {i['w']} x {i['h']} {unit}.")
    if "units" in instruments:
        found = sorted({m.group(0) for t in text for m in UNIT.finditer(t)})
        if found:
            out.append(f"Sizes and units on screen: {', '.join(found[:6])}.")
    if "numbers" in instruments:
        west = sorted({m.group(0) for t in text for m in WESTERN.finditer(t)})
        indian = sorted({m.group(0) for t in text for m in INDIAN.finditer(t)})
        dates = sorted({m.group(0) for t in text for m in DATE.finditer(t)})
        money = sorted({m.group(1) for t in text for m in MONEY.finditer(t)})
        if west:
            out.append(f"Large numbers grouped in thousands: {', '.join(west[:3])}.")
        if indian:
            out.append(f"Large numbers grouped in lakhs: {', '.join(indian[:3])}.")
        if dates:
            out.append(f"Dates written with numbers only: {', '.join(dates[:3])}.")
        if money:
            out.append(f"Currency shown as: {', '.join(money)}.")
        if not (west or indian or dates or money):
            out.append("No amounts, currency or dates on any screen they saw.")
    if "reading" in instruments:
        # Sentences are words; a line of formats joined by dots is a list, not a sentence.
        sentences = [s.strip() for t in text for s in re.split(r"(?<=[.!?])\s+", t)
                     if len(s.split()) >= 5 and "·" not in s and sum(w.strip(".,!?").isalpha() for w in s.split()) >= 0.7 * len(s.split())]
        long = [s for s in sentences if len(s.split()) > LONG_SENTENCE]
        if long:
            longest = max(long, key=lambda s: len(s.split()))
            out.append(f"{len(long)} sentence(s) on screen longer than {LONG_SENTENCE} words; longest, {len(longest.split())} words: \"{longest[:120]}\".")
        elif sentences:
            out.append(f"No sentence on screen is longer than {LONG_SENTENCE} words.")
        if not any(DEVANAGARI.search(t) for t in text) and not any(re.search(r"\b(hindi|marathi|language|भाषा)\b", t, re.I) for t in text):
            out.append("Every screen was in English only; no Hindi, Marathi or other language was offered.")
    return out


def evidence(local, task, out, observed, downloads, inputs, lens):
    steps, feed = read_jsonl(out / "steps.jsonl"), read_jsonl(out / "feed.jsonl")
    seen = screens_seen(steps)
    ev = []
    for line, where in list(seen.items())[:24]:
        ev.append({"kind": "S", "text": f'"{line}" ({where["what"]}, step {where["step"]})'})
    for e in feed:
        if e.get("type") == "event" and e["kind"] in ("STUCK", "SLIP", "OFF PATH", "DONE", "GAVE UP", "ASKED", "WRONG DONE", "SAYS DONE"):
            ev.append({"kind": "R", "text": f"{e['kind'].capitalize()}: {e['says'][:160]}"})
    # Their job's word against the app's, only on short labels and never for everyday interface words,
    # so "JPG Small" does not become a food stall's "half or full".
    labels = " | ".join(t.lower() for t in seen if len(t.split()) <= 4)
    for theirs, app in glossary(local):
        for word in (w.strip() for w in re.split(r",| or ", app)):
            if word and word.lower() not in GENERIC and re.search(rf"\b{re.escape(word.lower())}\b", labels):
                ev.append({"kind": "W", "text": f'The app says "{word}"; at work they say "{theirs}".'})
    for m in measure(lens["instruments"], seen, observed, downloads, inputs, task, steps):
        ev.append({"kind": "M", "text": m})
    counts = {}
    for e in ev:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
        e["id"] = f"{e['kind']}{counts[e['kind']]}"
    return ev


# ---------- The take ----------

ENDINGS = {"DONE": "you got it done", "SAYS DONE": "you believe you got it done (nobody checked)",
           "WRONG DONE": "you thought you were done, but you were not", "GAVE UP": "you gave up without getting it done",
           "ASKED": "you gave up and would hand the phone to someone else"}


def prompt(local, task, lens, ev, refs, today, ending):
    s = local.situation
    system = f"""You are {local.name}, {local.age}, {local.job}. You just tried a task in an app, and now someone asks what you made of it.
Where you were: {s['place']}. {today or ''}
The task was: {' '.join(task.story.split())}
How it ended: {ENDINGS.get(ending, 'it was cut short')}. Your take must match this.

Your work as {lens['field']} makes you notice: {lens['notices']}
How you talk: {lens['voice']} Plain voice, no accent, no acting, and no comparisons to your work: talk about the app as it is.

Rules:
- "take" is one or two short sentences, under 35 words, in your own voice about how it went for you.
- "remarks" are at most three things someone in your field would notice in this app. Each one names the evidence it is about, by id, in "about" (for example ["M2"] or ["S4", "R1"]), and says in plain words what that evidence shows; do not write the ids in the remark itself.
- Only talk about what the evidence shows. Measurements (M) are checked facts: never contradict them, and never guess what the app does out of sight.
- You may state a law, rule or standard only if it is one of the facts under "What you know for sure", and then put its id in "cites". Say what the rule asks and what the evidence shows; never conclude that the app breaks a law, because a run cannot show that.
- No wishlists: do not ask for features nobody needed in this task.
- If nothing in your field stands out, give no remarks. That is a fine answer."""
    lines = ["Evidence:"] + [f"[{e['id']}] {e['text']}" for e in ev]
    if refs:
        lines += ["", "What you know for sure:"] + [f"[{r['id']}] {r['says']}" for r in refs]
    return system, "\n".join(lines)


# A run can show what an app says and does; it cannot show that it breaks a law, or what it does out of sight.
CONCLUSION = re.compile(r"\b(violat\w*|illegal|unlawful|non.?complian\w*|not complian\w*|breach\w*|contraven\w*|infring\w*|offence|liable"
                        r"|break\w* the law|against the law|constitut\w+|amounts? to|fails? to (comply|meet|satisfy)|fails? the"
                        r"|failure to|failing to|legal requirement"
                        r"|does not (satisfy|comply|meet)|not in (line|accordance) with)\b", re.I)
GUESS = re.compile(r"\b(may|might|could|probably|likely|possibly|perhaps|presumably)\b", re.I)
# A job is what they notice, not a costume: "like I'd slice meat" is the caricature the persona research warns about.
SIMILE = re.compile(r"\b(like (a|an|i'?d|i would|we|how|when|the)|just like|as if|as though)\b", re.I)
FILLER = {"with", "that", "this", "from", "have", "were", "they", "their", "there", "which", "about", "into", "only", "also",
          "than", "then", "does", "step", "screen", "name", "hidden", "visible", "words", "link", "button", "text", "shows",
          "shown", "app's", "when", "what", "will", "would", "should", "more", "most", "very", "your", "user", "users"}


def tokens(text):
    return {t for t in re.findall(r"[a-z0-9][a-z0-9.×x]*", text.lower())
            if (len(t) >= 4 or any(c.isdigit() for c in t)) and t not in FILLER}


def core(e):
    """What a piece of evidence is about: the quoted words of a screen line, or the whole of anything else."""
    quoted = re.match(r'"(.*)" \(', e["text"]) if e["kind"] == "S" else None
    return quoted.group(1) if quoted else e["text"]


def check(reply, ev, refs, data_sent=None, kinds="SRWM"):
    """Keeps a remark only if its evidence exists, it talks about that evidence, its citations are facts from the
    study that apply here, and it neither concludes that a law is broken nor guesses at what the app does out of sight.
    data_sent is what the network showed: True, False, or None when it could not be watched (Android).
    Returns (kept, dropped with the reason)."""
    ids, refs_by = {e["id"]: e for e in ev}, {r["id"]: r for r in refs}
    known = set(refs_by)
    kept, dropped, seen_about = [], [], set()
    for r in reply.get("remarks", [])[:3]:
        about = [a.strip("[] ").upper() for a in r.get("about", []) if a.strip("[] ")]
        cites = [c.strip("[] ").lower() for c in r.get("cites", []) if c.strip("[] ")]
        text = re.sub(r"\s*\(?\b(?:as shown (?:by|in) |as in |per |see |in )?[SRWM]\d+\b\)?", "", " ".join(r.get("remark", "").split()))
        text = re.sub(r"\s+([.,;])", r"\1", re.sub(r",\s*\.", ".", text)).strip()
        why = ("has no evidence" if not text or not about or any(a not in ids for a in about)
               else "cites a fact that is not in the study" if any(c not in known for c in cites)
               else "cites a rule the measurements show does not apply" if data_sent is False and any(refs_by[c].get("needs") == "data-sent" for c in cites)
               else "points at evidence outside their field" if any(a[0] not in kinds for a in about)
               else "turns their job into a comparison" if SIMILE.search(text)
               else "concludes a law is broken" if CONCLUSION.search(text)
               else "guesses what the app does" if GUESS.search(text)
               else "does not talk about its evidence" if not tokens(text) & set().union(*(tokens(core(ids[a])) for a in about))
               else "says the same as another remark" if frozenset(about) in seen_about else None)
        if why:
            dropped.append({"remark": text[:300], "why": why})
            continue
        seen_about.add(frozenset(about))
        basis = BASIS[about[0][0]]
        kept.append({"kind": r.get("kind", ""), "remark": text[:300], "about": about, "cites": cites, "basis": basis,
                     "evidence": [ids[a]["text"] for a in about], "standing": "cited" if cites else "measured" if basis == "measured" else "their view"})
    return kept, dropped


def short(take):
    """A take is a sentence or two in plain words, not a report and not a performance."""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", " ".join(take.split())) if s and not SIMILE.search(s)]
    return " ".join(sentences[:2])[:280]


def take(local, task, out, say, observed, downloads, inputs, seed, today=""):
    """Asks the local for their take, checks it, says it (to the feed) and saves it as take.json."""
    lens = lens_for(local)
    if lens is None:
        return None
    refs = references(lens)
    ev = evidence(local, task, out, observed, downloads, inputs, lens)
    ending = next((e["kind"] for e in reversed(read_jsonl(out / "feed.jsonl")) if e.get("kind") in ENDINGS), None)
    system, user = prompt(local, task, lens, ev, refs, today, ending)
    reply = mind.chat(system, user, TAKE, seed, num_ctx=6144)
    data_sent = bool(observed.get("uploads")) if observed.get("platform") == "web" and task.files else None
    kinds = lens.get("evidence", "SRWM")
    remarks, dropped = check(reply, ev, refs, data_sent, kinds)
    proposed = len(reply.get("remarks", []))
    if dropped:
        # One chance to fix what the checks dropped, told why; a checker that only says no wastes a fixable remark.
        told = "\n".join(f'- "{d["remark"]}" was dropped because it {d["why"]}.' for d in dropped)
        again = mind.chat(system, f"{user}\n\nThe checks dropped some of your remarks:\n{told}\n"
                          "Give your remarks again, keeping to the rules, or leave out the ones you cannot fix.", TAKE, seed + 1, num_ctx=6144)
        more, dropped_again = check(again, ev, refs, data_sent, kinds)
        have = {frozenset(r["about"]) for r in remarks}
        remarks += [r for r in more if frozenset(r["about"]) not in have][:3 - len(remarks)]
        dropped += [{**d, "second try": True} for d in dropped_again]
        proposed += len(again.get("remarks", []))
    said = short(reply.get("take", ""))
    if said:
        say("TAKE", f'"{said}"')
    for r in remarks:
        why = r["evidence"][0][:110] + (" · " + ", ".join(r["cites"]) if r["cites"] else "")
        say("EXPERT", f"{r['remark']} [{r['standing']}: {why}]")
    result = {"local": local.id, "field": lens["field"], "take": said, "remarks": remarks, "dropped": dropped,
              "proposed": proposed, "kept": len(remarks), "evidence": ev}
    (out / "take.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def retake(folder, local, task, seed=7):
    """Asks again on a past day, from what was saved: the screens, the run, the files and the measurements."""
    out = folder / local.id
    names = {f["name"] for f in task.files}
    device = out / "device"
    inputs = [device / n for n in names if (device / n).exists()]
    downloads = sorted(p for p in device.iterdir() if p.name not in names) if device.exists() else []
    observed = json.loads((out / "observed.json").read_text(encoding="utf-8")) if (out / "observed.json").exists() else {}
    print(f"\n{local.tag}  {local.job}")
    return take(local, task, out, lambda kind, text: print(f"  {kind:<11}{text}"), observed, downloads, inputs, seed)


def panel(folder, ids):
    """The day's remarks grouped by the evidence they point at, with everyone who raised each, and how many
    remarks the checks kept: the grounding rate the study watches."""
    groups, proposed, kept = {}, 0, 0
    for local_id in ids:
        path = folder / local_id / "take.json"
        if not path.exists():
            continue
        t = json.loads(path.read_text(encoding="utf-8"))
        proposed, kept = proposed + t["proposed"], kept + t["kept"]
        for r in t["remarks"]:
            key = re.sub(r"\(.*?step \d+\)", "", r["evidence"][0]).strip().lower()
            g = groups.setdefault(key, {"evidence": r["evidence"][0], "remarks": [], "by": [], "fields": []})
            g["remarks"].append({"by": local_id, "field": t["field"], "remark": r["remark"], "standing": r["standing"]})
            g["by"].append(local_id)
            if t["field"] not in g["fields"]:
                g["fields"].append(t["field"])
    return {"proposed": proposed, "kept": kept, "points": sorted(groups.values(), key=lambda g: -len(g["by"]))}
