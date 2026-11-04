"""Rooms against real audiences: the attention rules run on lectures that were measured, and fitted to them.

Two published lectures, rebuilt as talks with nothing in them but time (no terms, no slides, a pace anyone can
follow, a subject that is neither why they came nor beside the point), so only the rules for time, breaks and the
starting attention are at work. Attention is read as the share of the time a listener is with the talk, so a room's
average attention is 100 less the share of probes at which people reported their mind had wandered.

1. Farley, Risko and Kingstone 2013: a 40 minute video lecture, attention rated from 1 to 7 after every 5 minutes.
   The ratings give the shape: how fast attention falls, and whether the fall speeds up.
2. Szpunar, Khan and Schacter 2013: a 21 minute statistics lecture in four parts. Without tests between the parts,
   minds wandered at 41% of probes; with a short test after each of the first three parts, at 19%. These give the
   level the room starts at and what a question to the room is worth.

Every rule is driven through the room's own update(), so what is checked is the code the rooms run.
`python -m town rooms --check` prints the comparison; study/rooms.md has the fit and what it changed.
"""
import itertools
from contextlib import contextmanager
from types import SimpleNamespace

from . import room

# The room's rules before the fit (a5bfb3e), kept so the check can show what it changed.
FIRST_GUESS = {"DRIFT": 1.0, "DRIFT_GROWS": 5.0, "DRIFT_MAX": 4.0, "START": {"grader": 85, "audience": 70}, "BREAK": 10}
FARLEY = [6.0, 6.3, 5.9, 5.9, 5.4, 5.2, 5.2, 4.9]   # mean attention, 1 to 7, after minutes 5, 10, ... 40 (their Table 1)
SZPUNAR = {"no tests": 41, "tests": 19}              # % of probes with the mind wandering, 21 minutes, four parts
SZPUNAR_MINUTES, SZPUNAR_PARTS = 21.0, 4


def rescale(rating):
    """A 1 to 7 rating on the room's 0 to 100."""
    return (rating - 1) / 6 * 100


@contextmanager
def rules(**values):
    """The room's rule sizes, set for a while and put back."""
    old = {k: getattr(room, k) for k in values}
    for k, v in values.items():
        setattr(room, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(room, k, v)


def listener(age=20):
    local = SimpleNamespace(age=age, name="Student", limits=SimpleNamespace(read_words=99))
    return room.Listener(local=local, role="audience", why="", mood="", attention=room.START["audience"], pace=250, reading=250)


def lecture(minutes, tests_after=(), step=0.25, age=20):
    """A listener's attention every step minutes through a lecture of nothing but time, with a question to the room
    at each minute in tests_after. Returns [(minute, attention)]."""
    l, out, t = listener(age), [], 0.0
    tests = sorted(tests_after)
    while t < minutes - 1e-9:
        test = next((x for x in tests if t < x <= t + step + 1e-9), None)
        part = SimpleNamespace(seconds=step * 60, said="", wpm=0, slide=False, slide_words=0, shown=[], title="")
        l.took.append(room.take_in(l, part, t))
        moments = [{"kind": "question to the room", "quote": ""}] if test is not None else []
        room.update(l, part, {"terms": [], "moments": moments}, {"matters": "somewhat"}, t, False)
        t += step
        out.append((round(t, 2), l.attention))
    return out


def mean(trail, start=0.0, end=None):
    xs = [a for m, a in trail if m > start and (end is None or m <= end + 1e-9)]
    return sum(xs) / len(xs)


def measures():
    """What the room's current rules give on the two lectures, beside the published numbers."""
    farley = lecture(40)
    blocks = [mean(farley, 5 * i, 5 * (i + 1)) for i in range(8)]
    part = SZPUNAR_MINUTES / SZPUNAR_PARTS
    plain = lecture(SZPUNAR_MINUTES)
    tested = lecture(SZPUNAR_MINUTES, tests_after=[part, 2 * part, 3 * part])
    return {
        "farley": [(5 * (i + 1), rescale(r), round(b, 1)) for i, (r, b) in enumerate(zip(FARLEY, blocks))],
        "szpunar": {"no tests": (SZPUNAR["no tests"], round(100 - mean(plain), 1)),
                    "tests": (SZPUNAR["tests"], round(100 - mean(tested), 1))},
        "asleep_at": next((m for m, a in farley if room.band(SimpleNamespace(role="audience", attention=a), a, m) == "asleep"), None),
    }


def error(**values):
    """How far the rules are from both studies: the fall over Farley's blocks (shape only) and Szpunar's two levels."""
    with rules(**values):
        m = measures()
    published = [p for _, p, _ in m["farley"]]
    town = [t for _, _, t in m["farley"]]
    shape = sum(((t - town[0]) - (p - published[0])) ** 2 for p, t in zip(published, town)) / len(town)
    level = sum((p - t) ** 2 for p, t in m["szpunar"].values()) / 2
    return shape + level


def fit():
    """The rule sizes closest to both studies, by a search over a grid."""
    best = None
    for drift, grows, start, brk in itertools.product(
            [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0], [5.0, 10.0, 20.0, 40.0, None], [60, 62, 64, 65, 66, 68, 70, 72, 75],
            [8, 10, 12, 14, 15, 16, 18, 20, 24]):
        e = error(DRIFT=drift, DRIFT_GROWS=grows, DRIFT_MAX=4.0, START={**room.START, "audience": start}, BREAK=brk)
        if best is None or e < best[0]:
            best = (e, {"DRIFT": drift, "DRIFT_GROWS": grows, "START": start, "BREAK": brk})
    return best


def report(before=None):
    """The comparison as text: published numbers, the town now, and the town before (a dict of old rule sizes)."""
    now = measures()
    old = None
    if before:
        with rules(**before):
            old = measures()
    lines = ["Farley, Risko and Kingstone 2013 · 40 minute lecture · attention after each 5 minutes, on 0 to 100",
             f"  {'minute':<8}{'people':>8}{'town':>8}" + (f"{'before':>9}" if old else "")]
    for i, (minute, people, town) in enumerate(now["farley"]):
        lines.append(f"  {minute:<8}{people:>8.1f}{town:>8.1f}" + (f"{old['farley'][i][2]:>9.1f}" if old else ""))
    lines.append("  (the shape is fitted, not the level: the ratings are a different scale from probes)")
    lines.append("Szpunar, Khan and Schacter 2013 · 21 minute lecture · % of the time minds wandered")
    for k, (people, town) in now["szpunar"].items():
        lines.append(f"  {k:<10}{people:>8}{town:>8.1f}" + (f"{old['szpunar'][k][1]:>9.1f}" if old else ""))
    asleep = now["asleep_at"]
    lines.append(f"A plain 40 minute lecture puts a 20 year old to sleep at minute: {asleep if asleep else 'never'}"
                 + (f" (before: {old['asleep_at'] if old['asleep_at'] else 'never'})" if old else ""))
    return "\n".join(lines)
