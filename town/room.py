"""A room: locals listen to a talk part by part, and code keeps track of who is still with you.

The model puts into words what goes through a listener's head, says which of the talk's terms they would not know
and whether a part matters for why they came. Code checks those answers against the talk and moves each listener's
attention by the study's rules: time without a break, terms they do not know, words faster than they can follow,
more on a slide than they can read while listening, a part that is not what they came for, and a story, an example
or a question that brings them back. Hooked, drifting, phone out and asleep are code's thresholds on that attention,
never the model's say so. Every number and its source: study/rooms.md.
"""
import json
import random
import re
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache

from . import derive, mind, people
from .expertise import SIMILE
from .feed import BOLD, DIM, RESET
from .limits import skim
from .people import ROOT
from .talk import clock, measure, sentences

ROOMS = ROOT / "rooms"

# Attention is the share of the time a listener is with the talk, so 100 less a room's average is the share of probes at
# which minds wandered. Fitted to two measured lectures (town/roomfit.py, study/rooms.md): Farley, Risko and Kingstone
# 2013 for how fast attention falls and that the fall does not speed up; Szpunar, Khan and Schacter 2013 for where it
# starts (41% wandering over 21 minutes) and what a question to the room is worth (19% with three short tests).
START = {"grader": 85, "audience": 64}       # attention as the talk begins; a grader is there to listen (a guess)
LOW = {"grader": ("checking email", "stopped listening"), "audience": ("phone out", "asleep")}
DRIFT = 0.5                                   # points a minute, at the same pace however long it runs (fitted)
DRIFT_GROWS, DRIFT_MAX = None, 4.0            # a speed up the longer since a break: the fit found none (None turns it off)
# Minds wander less with age: young adults on 41% of probes, older adults on 28% (Maillet and others 2018), so from 30
# to 60 the drift falls to 0.7 of a young adult's.
OLDER = 0.7
JARGON, JARGON_CAP = 2, 8                     # points for each term they do not know in a part, at most 8 a part
PACE = {"fluent": 250, "slow": 150}           # words a minute a listener follows without losing the thread
READ_SHARE = 0.5                              # share of the time a slide is up that a listener can spend reading it
TEXT_CAP, PACE_CAP = 12, 12
MATTERS = {"yes": 4, "somewhat": 0, "no": -4}
BREAK, SPARK = 15, 5                          # a question to the room (fitted to the tests), and so a story, example or
                                              # demonstration (a guess); a surprising number or a joke (a guess)
WAITING = 8                                   # each part that goes by after point_by without the point
ASLEEP_AFTER = 8                              # minutes: nobody nods off in a short talk, whatever it is; they reach for the phone
FLOOR = 5
ACTIVE = ("story", "example", "demonstration", "question to the room")
SPARKS = ("surprising number", "joke")
WAKES = ("question to the room", "demonstration", "joke")  # these reach even someone who has stopped listening
# How soon interviewers make up their minds: of 600+ real interviews, 4.9% within the first minute, 25.5% within
# five, 59.9% within fifteen (Frieder, Van Iddekinge and Raymark 2016).
DECIDED = [(0.049, 1), (0.255, 5), (0.599, 15)]

# Who knows a term is code's call, not the model's: asked which terms a cook would not know, a 4B model ticks nearly
# all of them for everyone, a backend engineer's "timeout" included. So the model only sorts the talk's terms into the
# field they belong to, and a listener knows a term when it is everyday, in one of their fields, or one of their words.
FIELDS = ["everyday", "software", "engineering", "science", "finance", "business", "law", "medicine", "education", "media", "trade"]
KNOWS = {  # the fields each job works in, by profile; a local's [habits] knows = [...] adds more
    "software": {"software-product", "software-services", "embedded-engineer"},
    "engineering": {"software-product", "software-services", "embedded-engineer", "plant-maintenance", "mechanical-design",
                    "site-engineer", "structural-planning", "electrical-maintenance", "engineering-student"},
    "science": {"clinic-doctor", "resident-doctor", "coaching-teacher", "embedded-engineer"},
    "finance": {"ca-practice", "article-assistant", "accounts-executive", "bank-branch", "insurance-agent", "founder-ceo",
                "company-ceo", "investor", "commerce-student"},
    "business": {"ca-practice", "accounts-executive", "bank-branch", "insurance-agent", "founder-ceo", "company-ceo", "investor",
                 "hr-recruiter", "hiring-manager", "commerce-student", "social-media-manager", "in-house-counsel", "fabricator"},
    "law": {"trial-advocate", "junior-advocate", "firm-associate", "in-house-counsel"},
    "medicine": {"clinic-doctor", "resident-doctor", "staff-nurse", "pharmacist", "asha-worker"},
    "education": {"govt-school-teacher", "private-school-teacher", "college-lecturer", "coaching-teacher"},
    "media": {"wedding-photographer", "product-photographer", "videographer", "video-editor", "social-media-manager"},
    "trade": {"fabricator", "food-stall"},
}
def text(n):
    """A string with a length: left open, a small model can loop inside one until the reply is cut off unread."""
    return {"type": "string", "maxLength": n}


# The field is free text, not a list to pick from: held to a list, the model can want a word that is not on it
# ("technology") and write blank space until it runs out. Code maps the words it uses onto the fields.
FIELD = {
    "type": "object",
    "properties": {"terms": {"type": "array", "maxItems": 25, "items": {
        "type": "object",
        "properties": {"term": text(60), "field": text(30)},
        "required": ["term", "field"],
    }}},
    "required": ["terms"],
}
SAME_FIELD = {
    "software": r"software|tech|\bit\b|comput|program|web|internet|digital|data|\bapps?\b|coding|developer|cloud|network",
    "engineering": r"engineer|mechanic|electric|electronic|civil|manufactur|industr",
    "science": r"scien|physic|chemi|biolog|math|statist|research",
    "finance": r"financ|account|bank|econom|tax|invest|insur",
    "business": r"business|marketing|sales|manage|commerce|startup|corporate|\bhr\b|human resource",
    "law": r"law|legal|court",
    "medicine": r"medic|health|clinic|nurs|pharma",
    "education": r"educat|teach|school|academ",
    "media": r"media|photo|video|film|design|journal",
    "trade": r"trade|shop|retail|workshop|craft",
    "everyday": r"everyday|general|common|daily|everyone",
}


def field_of(word):
    """The town's field for whatever word the model used; a field it cannot place is a specialist's, known to nobody."""
    w = str(word).lower().strip()
    return next((f for f in FIELDS if w == f), None) or next((f for f, p in SAME_FIELD.items() if re.search(p, w)), "other")

PART = {
    "type": "object",
    "properties": {
        "terms": {"type": "array", "maxItems": 20, "items": text(60)},
        "moments": {"type": "array", "maxItems": 6, "items": {
            "type": "object",
            "properties": {"kind": text(30), "quote": text(200)},  # free text, mapped by code (see FIELD)
            "required": ["kind", "quote"],
        }},
    },
    "required": ["terms", "moments"],
}
KIND = [("question to the room", r"question|ask|poll|show of hands|raise"), ("demonstration", r"demo|show|live"),
        ("story", r"story|anecdote|narrat"), ("example", r"example|case|instance"),
        ("surprising number", r"number|statistic|figure|data|percent"), ("joke", r"joke|humou?r|funny")]


def kind_of(word):
    w = str(word).lower()
    return next((k for k, p in KIND if w == k or re.search(p, w)), None)
HEAR = {
    "type": "object",
    "properties": {
        "inner": text(240),
        "matters": {"type": "string", "enum": ["yes", "somewhat", "no"]},
    },
    "required": ["inner", "matters"],
}
POINT = {"type": "object", "properties": {"point": text(200)}, "required": ["point"]}
RECALL = {"type": "object", "properties": {"point": text(240), "remember": text(200), "question": text(240)},
          "required": ["point", "remember", "question"]}
SAME = {"type": "object", "properties": {"same": {"type": "string", "enum": ["yes", "partly", "no"]}}, "required": ["same"]}


@cache
def rooms():
    return {r["id"]: r for r in tomllib.loads((ROOMS / "rooms.toml").read_text(encoding="utf-8"))["room"]}


def load(room_id):
    if room_id not in rooms():
        raise SystemExit(f"No room called {room_id!r}. Rooms: {', '.join(rooms())}")
    return rooms()[room_id]


@dataclass
class Listener:
    local: object
    role: str
    why: str
    mood: str
    attention: float
    pace: int            # words a minute they follow
    reading: int         # words a minute they read
    fields: set = field(default_factory=lambda: {"everyday"})  # the fields whose terms they know
    since_break: float = 0.0
    decides_at: float = None  # the minute an interviewer makes up their mind, if within the talk
    decided: str = ""         # the part where they did
    trail: list = field(default_factory=list)     # attention after each part
    took: list = field(default_factory=list)      # what reached them of each part
    thoughts: list = field(default_factory=list)
    questions: list = field(default_factory=list)
    events: list = field(default_factory=list)
    causes: list = field(default_factory=list)    # what moved their attention in each part, {cause: points}
    unknown: list = field(default_factory=list)   # the talk's terms they did not know
    missed: list = field(default_factory=list)    # those terms, part by part
    recall: dict = field(default_factory=dict)


def fields_of(local):
    """Everyday words, their job's fields, and any their own file adds under [habits] as knows = [...]."""
    group = local.profile.rsplit("/", 1)[-1].removesuffix(".md")
    return {"everyday", *local.habits.get("knows", []), *(f for f, groups in KNOWS.items() if group in groups)}


def seat(s, rng=None):
    local = people.load(s["local"])
    t = derive.traits(local)
    english = "slow" if t.get("english") == "slow" else "fluent"
    l = Listener(local=local, role=s["role"], why=s["why"], mood=s.get("mood", ""), attention=START[s["role"]],
                 pace=PACE[english], reading=round(derive.WPM[t["education"]] * (derive.ENGLISH_SLOW if english == "slow" else 1)),
                 fields=fields_of(local))
    if rng is not None:
        u = rng.random()
        l.decides_at = next((m for p, m in DECIDED if u < p), None)
    return l


def band(l, a=None, minute=99):
    a = l.attention if a is None else a
    low, lowest = LOW[l.role]
    return ("hooked" if a >= 80 else "with you" if a >= 50 else "drifting" if a >= 35 else low if a >= 20
            else lowest if minute >= ASLEEP_AFTER or l.role == "grader" else low)


# ---------- What reaches them ----------

def norm(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def found(quote, text):
    """A quote is in the text when nearly all of its words are, in a quote of at least three words."""
    q, words = norm(quote), set(norm(text))
    return len(q) >= 3 and sum(w in words for w in q) >= 0.85 * len(q)


def has_term(term, text):
    t = " ".join(norm(term))
    return len(t) >= 2 and f" {t} " in f" {' '.join(norm(text))} "


def take_in(l, part, minute):
    """What reaches a listener of this part, by the attention they have as it starts."""
    shown = [skim(x, l.local.limits.read_words) for x in part.shown[:12]]
    b = band(l, minute=minute)
    if b in ("hooked", "with you"):
        return {"how": "listening", "title": part.title, "shown": shown, "said": part.said}
    if b == "drifting":
        return {"how": "half listening", "title": part.title, "shown": shown[:2], "said": " ".join(sentences(part.said)[:1])}
    if b == LOW[l.role][0]:
        return {"how": "only glancing up", "title": part.title, "shown": [], "said": ""}
    return {"how": "not taking anything in", "title": "", "shown": [], "said": ""}


def told(took):
    lines = []
    if took["title"]:
        lines.append(f'Slide: "{took["title"]}"')
        lines += [f"- {x}" for x in took["shown"]]
    if took["said"]:
        lines.append(f'The speaker says: "{took["said"]}"')
    return "\n".join(lines) or "(nothing)"


def system(l, room, about=""):
    loc = l.local
    lines = ["You act out one real person listening to a talk. Stay inside their situation and what they know.", "",
             f"{loc.name}, {loc.age}, works as: {loc.job}.", f"Where: {room['where']}", f"When: {room['when']}",
             f"Why they are here: {l.why}"]
    if l.mood:
        lines.append(f"Mood: {l.mood}")
    if about:
        lines.append(f"The talk is for: {about}")
    lines += ["", "Rules:",
              "- You only know what they took in of the talk, shown to you part by part. Never add to it.",
              "- Their job decides what they know, not what they think about. Do not bring up their job or compare the talk "
              "to it unless the talk is about their work.",
              "- When a part has terms they do not know, they do not understand those words; they do not guess what they mean.",
              '- "inner": one short sentence of what goes through their head right now, in their own plain words, about this part. '
              "Never repeat a thought they already had. No accent, no acting.",
              '- "matters": does this part matter for why they are here? yes, somewhat or no.']
    return "\n".join(lines)


# ---------- What code does with it ----------

def analyse(part, seed):
    """The terms and the moments in one part, each checked against the part's own words."""
    text = part.text
    reply = mind.chat("You read one part of a talk closely. Copy words exactly from it; never add anything that is not there.",
                      f"{text}\n\nIn \"terms\", every specialist word, acronym, tool or product name in this part that someone outside "
                      "the field might not know, copied exactly as written. In \"moments\", any story (something that happened to "
                      "someone), example (one concrete case), demonstration (showing something working), question to the room "
                      "(asking the audience something), surprising number, or joke, each with its exact words.", PART, seed,
                      temperature=0, default={"terms": [], "moments": []})
    terms, seen = [], set()
    for t in [*reply.get("terms", []), *re.findall(r"\b[A-Z][A-Z0-9]{1,6}s?\b", text)]:
        t = " ".join(str(t).split()).strip(".,;:()\"'")
        if t and t.lower() not in seen and has_term(t, text) and len(t) <= 40:
            seen.add(t.lower())
            terms.append(t)
    moments = [{"kind": kind_of(m.get("kind")), "quote": " ".join(str(m.get("quote", "")).split())[:200]} for m in reply.get("moments", [])
               if kind_of(m.get("kind")) and found(str(m.get("quote", "")), text)]
    return {"terms": terms[:15], "moments": moments}


def age_drift(age):
    return 1.0 if age < 30 else OLDER if age >= 60 else 1.0 - (1.0 - OLDER) * (age - 30) / 30


def own(l, term):
    """A term from their own work is never unknown to them."""
    mine = " ".join([l.local.job, *l.local.habits["words"]]).lower()
    return term.lower() in mine


def classify(terms, seed):
    """The field each of the talk's terms belongs to, read once for the whole talk at temperature 0. {term: field}
    A batch the model cannot answer is split in two and asked again."""
    out, batches = {}, [terms[i:i + 20] for i in range(0, len(terms), 20)]
    while batches:
        chunk = batches.pop(0)
        try:
            reply = mind.chat("You sort words by the field of work where people use them. Answer for every term listed.",
                              "For each term, the field where it is used: everyday (most adults in India would know it), "
                              "software, engineering, science, finance, business, law, medicine, education, media, or trade "
                              "(shops and workshops).\n\n" + "\n".join(chunk), FIELD, seed + len(out), temperature=0)
        except json.JSONDecodeError:
            if len(chunk) > 1:
                batches[:0] = [chunk[:len(chunk) // 2], chunk[len(chunk) // 2:]]
            continue
        asked = {t.lower() for t in chunk}
        for t in reply.get("terms", []):
            if str(t.get("term", "")).lower() in asked:
                out[t["term"].lower()] = field_of(t.get("field", ""))
    return out  # a term the model never placed counts as everyday: no listener is marked down on a guess


def unknown_to(l, terms, kinds, heard):
    """The terms in what reached them that are outside their fields and their own words."""
    return [t for t in terms if kinds.get(t.lower(), "everyday") not in l.fields and not own(l, t) and has_term(t, heard)]


def update(l, part, facts, reply, minute, point_late, kinds=None):
    """Moves a listener's attention for one part by the study's rules. Returns what moved it, {cause: points}, and the
    terms they did not know. kinds is the field of each term (classify)."""
    took = l.took[-1]
    listening = took["how"] in ("listening", "half listening")
    m = part.seconds / 60
    changes = {}
    if m:
        rate = min(DRIFT_MAX, DRIFT + (l.since_break / DRIFT_GROWS if DRIFT_GROWS else 0))
        changes["too long without a break"] = -rate * m * age_drift(l.local.age)
    unknown = unknown_to(l, facts["terms"], kinds or {}, told(took)) if listening else []
    if unknown:
        changes["too technical"] = -min(JARGON_CAP, JARGON * len(unknown))
    if listening and part.said and part.wpm > l.pace:
        changes["too fast"] = -min(PACE_CAP, (part.wpm - l.pace) / 5 * m)
    if listening and part.slide:
        over = part.slide_words - l.reading * m * READ_SHARE
        if over > 0:
            changes["too much to read on the slides"] = -min(TEXT_CAP, over / 4)
    if reply and MATTERS.get(reply.get("matters"), 0):
        changes["what they came for" if MATTERS[reply["matters"]] > 0 else "not what they came for"] = MATTERS[reply["matters"]]
    if point_late:
        changes["still waiting for the point"] = -WAITING
    kinds = [x["kind"] for x in facts["moments"]]
    lifts = [k for k in kinds if (listening and k in (*ACTIVE, *SPARKS)) or k in WAKES]
    if lifts:
        best = max(lifts, key=lambda k: BREAK if k in ACTIVE else SPARK)
        changes[f"the {best}"] = BREAK if best in ACTIVE else SPARK
    l.since_break = 0.0 if any(k in ACTIVE for k in lifts) else l.since_break + m
    l.attention = max(FLOOR, min(100, l.attention + sum(changes.values())))
    l.unknown += unknown
    return {k: round(v, 1) for k, v in changes.items()}, unknown


def why(window, terms, up):
    """The biggest cause behind a change of band, in words, added up over the parts that led to it."""
    total = {}
    for changes in window:
        for k, v in changes.items():
            if (v > 0) == up:
                total[k] = total.get(k, 0) + v
    if not total:
        return ""
    k = max(total, key=lambda c: abs(total[c]))
    terms = list(dict.fromkeys(terms))
    return f"{k}: {', '.join(terms[:4])}" if k == "too technical" and terms else k


def central(talk, given, seed):
    """The talk's point: the one the speaker gave, or as the model reads it; and the part that says it in so many words."""
    point = given or mind.chat(
        "You read a talk and say its main point: the one thing the speaker wants people to take away, in one short plain "
        "sentence of at most 20 words. Use only what the talk says.",
        "\n\n".join(f"{p.id}: {skim(p.text.replace(chr(10), ' '), 120)}" for p in talk.parts), POINT, seed, temperature=0,
        default={"point": ""}).get("point", "")
    point = skim(point, 30)
    want = {w for w in norm(point) if len(w) >= 4}
    need = max(2, round(0.4 * len(want)))
    stated = next((p for p in talk.parts if len(want & set(norm(p.text))) >= need), None)
    return " ".join(point.split()), stated


def grounded(question, text):
    """A question about something in the text: four words or more, sharing a real word with it."""
    q = question.strip()
    return len(q.split()) >= 4 and bool({w for w in norm(q) if len(w) >= 4} & set(norm(text)))


def remember(l, room, point, about, seed):
    """At the end: what they say the point was, from only what reached them, and whether it is the speaker's point."""
    heard = [f"{t['part']}: {told(t)}" for t in l.took if t["how"] != "not taking anything in"]
    if not any(t["how"] in ("listening", "half listening") for t in l.took):
        return {"point": "", "remember": "", "same": "no", "question": "", "why": "took in nothing but slide titles"}
    reply = mind.chat(system(l, room, about), "The talk is over. This is everything they took in of it, in order:\n\n" + "\n\n".join(heard)
                      + '\n\nIn "point", what they think the talk\'s main point was, in one sentence of their own words; if they did '
                      'not take in enough to know, say so. In "remember", the one thing that stuck with them most, or an empty string. '
                      'In "question", the one question they would ask the speaker now, about something the talk said, or an empty string.',
                      RECALL, seed, default={"point": "", "remember": "", "question": ""})
    said = " ".join(reply.get("point", "").split())
    took_text = "\n".join(told(t) for t in l.took)
    question = " ".join(str(reply.get("question", "")).split())
    asks_meaning = re.search(r"what (?:does|do|is|are) ['\"‘’“”]?(.+?)['\"‘’“”]? (?:mean|stand for)", question, re.I)
    if not grounded(question, took_text) or (asks_meaning and asks_meaning.group(1).lower() not in {t.lower() for t in l.unknown}):
        question = ""  # a question about nothing they heard, or about a word they know, is the model filling a box
    judge = mind.chat("You compare what two people said a talk was about. Answer only from the two sentences.",
                      f'The speaker\'s point: "{point}"\nWhat a listener says the point was: "{said}"\n\nIs it the same point? '
                      "yes if it is the same main idea in any words (leaving out technical names is fine), partly if it has "
                      "only part of the idea, no if it is a different idea or none.", SAME, seed + 1, temperature=0,
                      default={"same": "no"}).get("same", "no")
    if not said or re.search(r"\b(not sure|no idea|don'?t know|do not know|did not take in|didn'?t take in|can'?t say|cannot say)\b", said, re.I):
        judge = "no"  # saying they cannot tell is not knowing, however kind the judge
    return {"point": said, "remember": " ".join(reply.get("remember", "").split()), "same": judge, "question": question}


def markers(listeners, talk, room):
    """What happened in the room as a whole, by code: the bonuses and the warnings."""
    out, n = [], len(listeners)
    if n and all(min(l.trail) >= 60 and l.trail[-1] >= 70 for l in listeners):
        out.append({"kind": "hooked till the end", "says": f"All {n} stayed with you from start to finish."})
    for i, part in enumerate(talk.parts):
        low = [l for l in listeners if l.trail[i] < 50]
        if n >= 2 and len(low) * 2 >= n:
            causes = {}
            for l in low:
                for c in l.causes[max(0, i - 2):i + 1]:
                    for k, v in c.items():
                        if v < 0:
                            causes[k] = causes.get(k, 0) + v
            top = min(causes, key=causes.get) if causes else ""
            terms = list(dict.fromkeys(t for l in low for t in l.unknown))[:4] if top == "too technical" else []
            out.append({"kind": "lost the room", "part": part.id,
                        "says": f"{len(low)} of {n} had drifted by {part.id}" + (f": {top}" if top else "") + (f" ({', '.join(terms)})" if terms else "")})
            break
    audience = [l for l in listeners if l.role == "audience"]
    for i, part in enumerate(talk.parts):
        asleep = [l for l in audience if band(l, l.trail[i], (part.start + part.seconds) / 60) == "asleep"]
        if len(audience) >= 2 and len(asleep) >= max(2, len(audience) / 3):
            out.append({"kind": "the room fell asleep", "part": part.id,
                        "says": f"{len(asleep)} of {len(audience)} in the audience were asleep by {part.id}"})
            break
    backs = [e for l in listeners for e in l.events if e["kind"] == "BACK"]
    if backs:
        first = min(backs, key=lambda e: int(e["part"][1:]))
        out.append({"kind": "brought them back", "part": first["part"],
                    "says": f"{len(backs)} time{'s' if len(backs) > 1 else ''} someone came back; first at {first['part']} with {first['why']}"})
    if room.get("minutes") and talk.seconds > room["minutes"] * 60 + 30:
        out.append({"kind": "over time", "says": f"{clock(talk.seconds - room['minutes'] * 60)} over the {room['minutes']} minutes"})
    got = [l for l in listeners if l.recall.get("same") in ("yes", "partly")]
    if listeners:
        out.append({"kind": "remembered the point", "says": f"{len(got)} of {n} could say your point afterwards"})
    return out


# ---------- The room, from the first part to the last ----------

TONE = {"HOOKED": "\033[32m", "BACK": "\033[32m", "DRIFTING": "\033[33m", "PHONE OUT": "\033[33m", "CHECKING EMAIL": "\033[33m",
        "ASLEEP": "\033[31m", "STOPPED LISTENING": "\033[31m", "MADE UP THEIR MIND": "\033[36m"}
ORDER = ["asleep", "stopped listening", "phone out", "checking email", "drifting", "with you", "hooked"]


def change(before, after):
    """The event when a listener's band changes: hooked, back with you, or the band they fell into."""
    if after == before:
        return None
    if ORDER.index(after) > ORDER.index(before):
        return "HOOKED" if after == "hooked" else "BACK" if after == "with you" else None
    return None if after == "with you" else after.upper()


def spark(l, talk):
    bars = "▁▂▃▄▅▆▇█"
    return "".join("z" if band(l, a, (p.start + p.seconds) / 60) == "asleep" else bars[min(7, int(a / 12.5))] for a, p in zip(l.trail, talk.parts))


def listen(room, talk, about="", point="", seed=7, out=None):
    """Gives the talk to the room. Prints it as it happens and returns everything that happened."""
    rng = random.Random(seed)
    interview = room["id"] == "interview"
    listeners = [seat(s, rng if interview else None) for s in room["seats"]]
    facts_m = measure(talk, room.get("minutes"))
    print(f"\n{BOLD}ROOM{RESET}  {room['name']} · {talk.source} · {len(talk.parts)} parts · {clock(talk.seconds)} · {talk.kind} · {mind.MODEL}")
    for n in talk.notes:
        print(f"      {DIM}{n}{RESET}")
    point, stated = central(talk, point, seed)
    print(f"{BOLD}POINT{RESET} {point}" + (f"  {DIM}(said in so many words in {stated.id}){RESET}" if stated else f"  {DIM}(never said in so many words){RESET}"))
    every = [analyse(p, seed + 100 + i) for i, p in enumerate(talk.parts)]
    kinds = classify(list(dict.fromkeys(t for f in every for t in f["terms"])), seed + 90)
    parts = []
    for i, part in enumerate(talk.parts):
        minute = part.start / 60
        facts = every[i]
        end = (part.start + part.seconds) / 60
        late = bool(room.get("point_by")) and end > room["point_by"] and (stated is None or talk.parts.index(stated) > i)
        print(f"\n{BOLD}{part.id:<4}{clock(part.start):>6}{RESET}  {part.title[:70]}" + (f"  {DIM}{', '.join(m['kind'] for m in facts['moments'])}{RESET}" if facts["moments"] else ""))
        gone = []
        for j, l in enumerate(listeners):
            before = band(l, minute=minute)
            took = {"part": part.id, **take_in(l, part, minute)}
            l.took.append(took)
            reply = None
            if took["how"] != "not taking anything in":
                lost = unknown_to(l, facts["terms"], kinds, told(took)) if took["how"] != "only glancing up" else []
                user = (f"{clock(part.start)} into the talk, {part.id} of {len(talk.parts)}. They are {took['how']}.\n\n"
                        f"What they took in of this part:\n{told(took)}\n\n"
                        f"Terms here they do not know: {', '.join(lost) or 'none'}\n\n"
                        + ("What went through their head before:\n" + "\n".join(f"- {t}" for t in l.thoughts[-3:]) if l.thoughts else ""))
                reply = mind.chat(system(l, room, about), user, HEAR, seed + 1000 * (j + 1) + i, default={"inner": "", "matters": "somewhat"})
                # A comparison to their own life is the caricature the persona research warns about; it goes, whether it
                # is a sentence of its own or tacked on after a comma.
                inner = re.split(r",\s*(?:just )?(?:like|as if|as though)\b", " ".join(reply.get("inner", "").split()))[0].strip()
                inner = " ".join(s for s in re.split(r"(?<=[.!?])\s+", inner) if not SIMILE.search(s))
                inner = reply["inner"] = inner + ("." if inner and inner[-1] not in ".?!" else "")
                if inner:
                    l.thoughts.append(inner)
            changes, unknown = update(l, part, facts, reply, minute, late, kinds)
            l.causes.append(changes)
            l.trail.append(round(l.attention, 1))
            after = band(l, minute=end)
            if l.decides_at is not None and not l.decided and end >= l.decides_at:
                l.decided = part.id
                l.events.append({"kind": "MADE UP THEIR MIND", "part": part.id, "why": f"by minute {l.decides_at}"})
            l.missed.append(unknown)
            kind = change(before, after)
            if kind:
                up = kind in ("HOOKED", "BACK")
                # Falling is what built up since they were last with you; coming back is what this part did.
                since = max((k for k in range(i) if l.trail[k] >= 50), default=-1) + 1
                window = range(i, i + 1) if up else range(since, i + 1)
                l.events.append({"kind": kind, "part": part.id, "why": why([l.causes[k] for k in window],
                                                                        [t for k in window for t in l.missed[k]], up)})
            if reply is None and not kind:
                gone.append(l.local.name.upper())
                continue
            inner = (reply or {}).get("inner", "") if reply else "(not listening)"
            print(f"  {l.local.number:>3} {l.local.name.upper():<10} {round(l.attention):>3} {after:<17} {DIM}{inner[:150]}{RESET}")
            for e in l.events:
                if e["part"] == part.id:
                    print(f"  {' ' * 15}{TONE.get(e['kind'], '')}{e['kind']}{RESET}  {e['why']}")
        if gone:
            print(f"  {DIM}{'still asleep' if all(band(l, minute=end) == 'asleep' for l in listeners if l.local.name.upper() in gone) else 'not listening'}: {', '.join(gone)}{RESET}")
        parts.append({"id": part.id, "title": part.title, "start": part.start, "seconds": part.seconds, "words": part.words,
                      "slide_words": part.slide_words, "wpm": round(part.wpm), **facts})
    for j, l in enumerate(listeners):
        l.recall = remember(l, room, point, about, seed + 50 + j)
        if l.recall.get("question"):
            l.questions.append(l.recall["question"])
    marks = markers(listeners, talk, room)
    print(f"\n{BOLD}ATTENTION{RESET}  {DIM}one bar a part, z asleep{RESET}")
    depth = ["ASLEEP", "STOPPED LISTENING", "PHONE OUT", "CHECKING EMAIL", "DRIFTING"]
    for l in listeners:
        low = sorted((e for e in l.events if e["kind"] in depth), key=lambda e: depth.index(e["kind"]))
        note = f"{low[0]['kind'].lower()} at {low[0]['part']}: {low[0]['why']}" if low else "never drifted"
        print(f"  {l.local.number:>3} {l.local.name.upper():<10} {spark(l, talk)}  ends {round(l.attention)}  {DIM}{note}{RESET}")
    print(f"\n{BOLD}THE ROOM{RESET}")
    for m in marks:
        sign = "+" if m["kind"] in ("hooked till the end", "brought them back") else "-" if m["kind"] in ("lost the room", "the room fell asleep", "over time") else " "
        print(f"  {sign} {m['kind'].upper():<22} {m['says']}")
    print(f"\n{BOLD}WHAT THEY SAY IT WAS ABOUT{RESET}")
    for l in listeners:
        r = l.recall
        print(f"  {l.local.number:>3} {l.local.name.upper():<10} {r['same']:<7} {DIM}{r.get('point') or r.get('why', '')}{RESET}")
    asks = [(l, l.questions[-1]) for l in listeners if l.questions]
    if asks:
        print(f"\n{BOLD}WHAT THEY WOULD ASK{RESET}")
        for l, q in asks:
            print(f"  {l.local.number:>3} {l.local.name.upper():<10} {q}")
    result = {"room": room["id"], "name": room["name"], "source": talk.source, "kind": talk.kind, "model": mind.MODEL,
              "seconds": talk.seconds, "notes": talk.notes, "point": point, "stated": stated.id if stated else None, "fields": kinds,
              "measured": facts_m, "parts": parts, "markers": marks,
              "listeners": [{"id": l.local.id, "name": l.local.name, "number": l.local.number, "job": l.local.job, "role": l.role,
                             "why": l.why, "trail": l.trail, "events": l.events, "thoughts": l.thoughts, "questions": l.questions,
                             "took": l.took, "causes": l.causes, "unknown": list(dict.fromkeys(l.unknown)), "recall": l.recall,
                             "decided": l.decided} for l in listeners]}
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "room.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    return result, listeners


def folder(room_id):
    return ROOT / "runs" / "rooms" / f"{datetime.now():%Y-%m-%d_%H%M%S}_{room_id}"
