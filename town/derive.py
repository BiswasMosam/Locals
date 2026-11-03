"""Limits from published data instead of guesses: a local's traits, and the studies, give their numbers.

Traits come from what the profile already says: education from the job's entry requirements, conditions
from where they are and what their hands are doing, reading pace from their reading habit. The numbers
come from studies of real people typing, tapping and reading. Every factor and its source: study/limits.md.
"""
import json
import math
import re
import tomllib
from pathlib import Path

from .people import PEOPLE

# Schooling a job needs, from its entry requirements (study/limits.md). Unlisted jobs: secondary.
EDUCATION = {
    "graduate": {"trial-advocate", "junior-advocate", "firm-associate", "in-house-counsel", "social-media-manager",
                 "software-product", "software-services", "plant-maintenance", "mechanical-design", "site-engineer",
                 "structural-planning", "electrical-maintenance", "embedded-engineer", "ca-practice", "article-assistant",
                 "accounts-executive", "bank-branch", "clinic-doctor", "resident-doctor", "staff-nurse", "pharmacist",
                 "govt-school-teacher", "private-school-teacher", "college-lecturer", "coaching-teacher",
                 "founder-ceo", "company-ceo", "investor", "hr-recruiter", "hiring-manager",
                 # College students are still studying for a degree, and they are the people most reading studies measured.
                 "engineering-student", "commerce-student"},
    "primary": {"asha-worker"},
}
WPM = {"graduate": 250, "secondary": 200, "primary": 140}  # reading speed, words a minute

CONDITIONS = {  # what their situation does to their hands and eyes, read from the profile's words
    "moving": r"\b(auto|train|walking|bus|bike|lanes?|in transit|on the road)\b",
    "wet": r"\b(wet|oily|oil|grease|greasy|damp|sweat|flour)\b",
    "gloves": r"\bgloves?\b",
    "one hand": r"\b(one hand|other hand|in one hand|arm's length|one glove off)\b",
    "rushed": r"\b(rush\w*|hurr\w*|waiting|deadline|queue|pressure|urgent|busiest|now)\b",
    "tired": r"\b(tired|exhausted|awake since|hour of duty|sleepy|night shift|worn out)\b",
}
GLANCE = [  # seconds they spend on one label or paragraph, from how the profile says they read; first match wins
    (1.0, r"two or three words|two words|glance|first word|scans fast|very little|goes by pictures"),
    (2.0, r"few words|first line|first few|skim|start of|over the train|picks out|a line|only what|what s?he needs|skips|quickly|scans for"),
    (5.0, r"carefully|fully|twice|word by word|slowly|closely|thoroughly|everything"),
    (4.0, r"properly"),
]
ENGLISH_SLOW = 0.6  # reading speed for someone the profile says English slows down

# Touch slips: a young adult on a big enough target, then what the studies say multiplies it.
SLIP_BASE = {"phone": 0.03, "laptop": 0.01}
SLIP = {"moving": 1.23, "wet": 2.0, "gloves": 2.0, "one hand": 1.2, "rushed": 1.2, "tired": 1.2}
# Typing: share of characters left wrong on a phone keyboard, and on a laptop's.
TYPO_BASE = {"phone": 0.023, "laptop": 0.015}
TYPO = {"moving": 1.23, "wet": 1.5, "gloves": 1.5, "one hand": 1.3, "rushed": 1.2, "tired": 1.2}


def slip_age(age):
    return 3.5 if age >= 60 else 1.8 if age >= 45 else 1.0


def typo_age(age):
    return 1.6 if age >= 60 else 1.3 if age >= 40 else 1.0


def traits(local):
    """Education, conditions and reading pace, from the profile; the local's own file wins where it says."""
    raw = tomllib.loads((PEOPLE / f"{local.id}.toml").read_text(encoding="utf-8")).get("traits", {})
    group = Path(local.profile).stem
    education = raw.get("education") or next((e for e, jobs in EDUCATION.items() if group in jobs), "secondary")
    s = local.situation
    text = " ".join([s["place"], s["hands"], s["time"], s["mood"]]).lower()
    conditions = raw.get("conditions") or [c for c, pattern in CONDITIONS.items() if re.search(pattern, text)
                                           and not (c == "gloves" and re.search(r"gloves? (just )?off", text))]  # a bare hand on the phone
    reads = local.habits["reads"].lower()
    glance = raw.get("glance") or next((secs for secs, pattern in GLANCE if re.search(pattern, reads)), 3.0)
    english = raw.get("english") or ("slow" if re.search(r"english", reads) and re.search(r"little|slow", reads) else "fluent")
    return {"education": education, "conditions": conditions, "glance": glance, "english": english}


def derive(local, t):
    device = local.limits.device
    touch = device == "phone"
    wpm = WPM[t["education"]] * (ENGLISH_SLOW if t.get("english") == "slow" else 1)
    read = max(2, round(wpm / 60 * t["glance"]))
    # Many hard conditions at once still leave a person only so clumsy: the combined factor stops at three.
    slips = min(3.0, math.prod(SLIP[c] for c in t["conditions"] if touch or c == "tired"))
    typos = min(3.0, math.prod(TYPO[c] for c in t["conditions"] if touch or c in ("rushed", "tired")))
    slip = SLIP_BASE[device] * (slip_age(local.age) if touch else 1) * slips
    typo = TYPO_BASE[device] * typo_age(local.age) * typos
    return {"read_words": read, "slip_rate": round(min(0.3, slip), 2), "typo_rate": round(min(0.12, typo), 2)}


def write(local, t, values):
    """Puts the traits and the derived numbers in the local's file; patience and repeats stay as they were."""
    path = PEOPLE / f"{local.id}.toml"
    text = path.read_text(encoding="utf-8")
    block = (f'[traits]\neducation = "{t["education"]}"\nconditions = [{", ".join(json.dumps(c) for c in t["conditions"])}]\n'
             f'glance = {t["glance"]}\nenglish = "{t["english"]}"\n\n')
    text = re.sub(r"(?ms)^\[traits\]\n.*?\n\n", "", text)
    note = ("# read_words, slip_rate and typo_rate are derived from published studies and the traits above (study/limits.md);"
            "\n# patience_steps and repeat_before_stuck are still guesses from the profile.")
    text = re.sub(r"(?m)^# (Draft numbers guessed|read_words, slip_rate and typo_rate are derived).*\n(# patience_steps.*\n)?", "", text)
    text = text.replace("[limits]\n", block + note + "\n[limits]\n", 1)
    for key, value in values.items():
        text = re.sub(rf"(?m)^{key} = .*$", f"{key} = {value}", text)
    path.write_text(text, encoding="utf-8")
