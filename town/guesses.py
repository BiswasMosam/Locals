"""How much of each profile is still a guess: source tags counted, family by family (study/README.md, rule 1).

A guess is a line tagged [G]. The study's rule is that every guess has an open question; a profile with guesses and no
open questions breaks it, and is listed. A line that carries a source as well as [G] (`[D]` `[G]`) is part sourced, part
guessed, and still counts as a guess: the [G] says some of it has no source yet.
"""
import re
from collections import Counter

from .people import ROOT

PROFILES = ROOT / "study" / "profiles"
TAG = re.compile(r"`\[([IODAPG])\]`")


def profiles():
    return sorted(p for p in PROFILES.rglob("*.md") if p.name != "README.md")


def count(path):
    text = path.read_text(encoding="utf-8")
    tags = Counter(TAG.findall(text))
    section = text.split("## 12. Open questions", 1)
    asked = len(re.findall(r"(?:^|\s)\d+\.\s", section[1].split("\n## ", 1)[0], re.M)) if len(section) > 1 else 0
    return tags, asked


def family(path):
    rel = path.relative_to(PROFILES)
    return rel.parts[0] if len(rel.parts) > 1 else "ring one"


def report():
    rows, by_family = [], {}
    for p in profiles():
        tags, asked = count(p)
        sourced = sum(v for k, v in tags.items() if k != "G")
        rows.append((family(p), p.stem, tags["G"], sourced, asked))
        f = by_family.setdefault(family(p), Counter())
        f["G"] += tags["G"]
        f["sourced"] += sourced
        f["profiles"] += 1
    lines = [f"{'family':<12}{'profiles':>9}{'guesses':>9}{'sourced':>9}{'share sourced':>15}"]
    for f, c in sorted(by_family.items(), key=lambda kv: kv[1]["G"] / max(1, kv[1]["G"] + kv[1]["sourced"])):
        lines.append(f"{f:<12}{c['profiles']:>9}{c['G']:>9}{c['sourced']:>9}{100 * c['sourced'] / max(1, c['G'] + c['sourced']):>14.0f}%")
    total_g, total_s = sum(r[2] for r in rows), sum(r[3] for r in rows)
    lines.append(f"{'all':<12}{len(rows):>9}{total_g:>9}{total_s:>9}{100 * total_s / max(1, total_g + total_s):>14.0f}%")
    unasked = [f"{r[0]}/{r[1]}" for r in rows if r[2] and not r[4]]
    if unasked:
        lines.append("\nGuesses with no open questions (the study's rule 1): " + ", ".join(unasked))
    return "\n".join(lines), rows
