"""The calendar: what a date means for the city, and for each local's day. Data lives in year/."""
import hashlib
import tomllib
from dataclasses import dataclass, replace
from datetime import date, timedelta
from functools import cache
from pathlib import Path

from .people import ROOT

YEAR = ROOT / "year"
PANDEMIC = ("lockdown", "reopening")


@cache
def data(year):
    path = YEAR / f"{year}.toml"
    if not path.exists():
        raise ValueError(f"No calendar for {year}. Calendars exist for: {', '.join(map(str, years())) or 'none'}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


@cache
def effects():
    return tomllib.loads((YEAR / "effects.toml").read_text(encoding="utf-8"))["effect"]


def years():
    return sorted(int(p.stem) for p in YEAR.glob("[0-9][0-9][0-9][0-9].toml"))


def within(d, span):
    return date.fromisoformat(span["from"]) <= d <= date.fromisoformat(span["to"])


@dataclass
class Today:
    day: date
    holiday: str | None
    festivals: list
    lights: str | None
    periods: list
    season: str
    rain: str
    pandemic: str | None

    def keys(self):
        keys = {f"festival:{f}" for f in self.festivals} | {f"period:{p['key']}" for p in self.periods}
        if self.holiday:
            keys.add("holiday")  # a holiday on a Sunday is still one day off, not two
        elif self.day.weekday() == 6:
            keys.add("sunday")
        if self.rain == "heavy":
            keys |= {"rain", "heavy_rain"}
        elif self.rain == "rain":
            keys.add("rain")
        if self.season == "summer":
            keys.add("summer")
        if self.pandemic:
            keys.add(f"pandemic:{self.pandemic}")
        return keys

    def label(self):
        parts = [self.day.strftime("%a %d %b %Y").replace(" 0", " ")]
        parts += [self.holiday] if self.holiday else []
        parts += [f for f in self.festivals if f != self.holiday]
        parts += [p["name"] for p in self.periods]
        parts += {"rain": ["rain"], "heavy": ["heavy rain"]}.get(self.rain, [])
        parts += [f"pandemic: {self.pandemic}"] if self.pandemic else []
        return " · ".join(parts)

    def scene(self):
        """What the town should look like on this day."""
        return {"date": self.day.isoformat(), "label": self.label(), "rain": self.rain, "lights": self.lights,
                "pandemic": self.pandemic, "season": self.season}


def today(d, pandemic=None):
    cal = data(d.year)
    holidays = [name for when, name in cal["holidays"] if when == d.isoformat()]
    festivals = [f for f in cal.get("festival", []) if within(d, f)]
    periods = [p for p in cal.get("period", []) if within(d, p)]
    seasons = [s for s in cal.get("season", []) if within(d, s)]
    season = seasons[-1] if seasons else {}
    # Rain is fixed by the date, so the same day always has the same weather.
    roll = int(hashlib.sha1(f"rain-{d.isoformat()}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    rain = "heavy" if roll < season.get("heavy", 0) else "rain" if roll < season.get("rain", 0) else ""
    return Today(day=d, holiday=" and ".join(holidays) or None, festivals=[f["name"] for f in festivals],
                 lights=festivals[-1]["lights"] if festivals else None, periods=periods,
                 season=season.get("key", ""), rain=rain, pandemic=pandemic if pandemic in PANDEMIC else None)


def shape(local, t):
    """The local on this day: a "Today" paragraph, maybe a different place, and limits changed by code."""
    group, keys = Path(local.profile).stem, t.keys()
    lines, place, limits = [], None, replace(local.limits)
    fill = {"holiday": t.holiday or "the holiday", "festival": ", ".join(t.festivals),
            "period": t.periods[0]["name"] if t.periods else ""}
    patience = read = slip = 0
    for e in effects():
        if e["when"] in keys and ("*" in e["who"] or group in e["who"]):
            if e.get("says"):
                lines.append(e["says"].format(**fill))
            place = e.get("place", place)
            patience += e.get("patience", 0)
            read += e.get("read", 0)
            slip += e.get("slip", 0.0)
    # However many things happen on one day, a person is only so much calmer or more rushed.
    limits.patience_steps = max(3, limits.patience_steps + max(-4, min(4, patience)))
    limits.read_words = max(2, limits.read_words + max(-3, min(4, read)))
    limits.slip_rate = min(0.3, max(0.0, limits.slip_rate + min(0.1, slip)))
    situation = {**local.situation, "place": place} if place else local.situation
    text = f"It is {t.day.strftime('%A %d %B %Y').replace(' 0', ' ')}. " + " ".join(lines)
    return replace(local, limits=limits, situation=situation), text.strip()


def picks(year):
    """Days worth trying, plus the first heavy rain day of the monsoon, found from the weather."""
    out = [dict(p) for p in data(year).get("pick", [])]
    d = date(year, 7, 1)
    while d.year == year and d.month < 9:
        if today(d).rain == "heavy":
            out.append({"label": "Monsoon downpour", "date": d.isoformat()})
            break
        d += timedelta(days=1)
    return sorted(out, key=lambda p: p["date"])


def sample(year, n=12):
    """A year in n days: the chosen days first, then one ordinary weekday per month that has none."""
    chosen = {date.fromisoformat(p["date"]) for p in picks(year)}
    months = {d.month for d in chosen}
    for m in range(1, 13):
        if m not in months:
            d = date(year, m, 8)
            while d.weekday() != 2:  # a Wednesday, so nothing about the weekend leaks in
                d += timedelta(days=1)
            chosen.add(d)
    days = sorted(chosen)
    if len(days) > n:
        step = len(days) / n
        days = [days[int(i * step)] for i in range(n)]
    return days
