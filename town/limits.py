"""The code that makes a local human: skimming, slipping, typos.

Studies show a prompt alone leaves AI users too patient and too accurate,
so these limits are applied to what the local sees and does, not requested.
"""
import math


def skim(text, words):
    """What a person actually takes in from a label or paragraph."""
    parts = text.split()
    if len(parts) <= words:
        return text
    return " ".join(parts[:words]) + " …"


COMFORTABLE = 48  # dp or CSS px: Android's touch target guidance; below it, misses rise as the target shrinks


def slip(rng, rate, target, items, touch=True):
    """A tap that lands on the nearest other control instead. Returns the id actually hit.

    On a touch screen a small target is missed more often (study/limits.md): the rate grows as the
    target's short side falls below 48, up to three times at 16 or less."""
    aim = next((i for i in items if i["id"] == target), None)
    if aim is None:
        return target
    if touch and "w" in aim:
        rate = min(0.5, rate * max(1.0, min(3.0, COMFORTABLE / max(1, min(aim["w"], aim["h"])))))
    if rng.random() >= rate:
        return target
    others = [i for i in items if i["id"] != target and not i["disabled"]]
    if not others:
        return target
    nearest = min(others, key=lambda i: math.dist((i["x"], i["y"]), (aim["x"], aim["y"])))
    return nearest["id"]


NEIGHBOURS = "qwertyuiopasdfghjklzxcvbnm"


def typo(rng, rate, text):
    """Typing as it really happens on a small keyboard: a neighbouring key, a dropped letter."""
    out = []
    for ch in text:
        if ch.isalpha() and rng.random() < rate:
            if rng.random() < 0.5:
                continue
            i = NEIGHBOURS.find(ch.lower())
            out.append(NEIGHBOURS[(i + 1) % len(NEIGHBOURS)] if i >= 0 else ch)
        else:
            out.append(ch)
    return "".join(out)
