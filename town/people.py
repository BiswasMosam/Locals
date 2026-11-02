"""The residents: one TOML file per local in people/, built from a study profile."""
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PEOPLE = ROOT / "people"


@dataclass
class Limits:
    """Human limits enforced by code, never left to the prompt."""
    read_words: int          # words read from any one label or paragraph before skimming on
    patience_steps: int      # actions before giving up on a task
    repeat_before_stuck: int # times the same screen comes back before they feel stuck
    slip_rate: float         # chance a tap lands on the nearest neighbour instead
    typo_rate: float         # chance per character of a typing mistake
    device: str              # phone or laptop


@dataclass
class Local:
    id: str
    number: int
    name: str
    age: int
    job: str
    profile: str
    status: str
    situation: dict
    habits: dict
    limits: Limits
    notes: list = field(default_factory=list)

    @property
    def tag(self):
        return f"{self.number:02d} {self.name.upper()}"


def load(local_id):
    path = PEOPLE / f"{local_id}.toml"
    if not path.exists():
        raise SystemExit(f"No local called {local_id!r}. Run: python -m town people")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Local(
        id=data["id"], number=data["number"], name=data["name"], age=data["age"], job=data["job"],
        profile=data["profile"], status=data["status"], situation=data["situation"],
        habits=data["habits"], limits=Limits(**data["limits"]), notes=data.get("notes", []),
    )


def everyone():
    return sorted((load(p.stem) for p in PEOPLE.glob("*.toml")), key=lambda l: l.number)
