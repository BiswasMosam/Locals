"""Task cards for apps, one TOML file per app in tasks/, plus the files a local starts with."""
import os
import struct
import tomllib
import zlib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks"


@dataclass
class Task:
    app: str
    url: str
    id: str
    story: str
    files: list
    done: dict


def load(ref):
    """ref looks like 'pixelshift:small-jpg'."""
    app_id, _, task_id = ref.partition(":")
    path = TASKS / f"{app_id}.toml"
    if not path.exists():
        raise SystemExit(f"No task file tasks/{app_id}.toml")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    for t in data["task"]:
        if t["id"] == task_id:
            return Task(app=data["app"], url=data["url"], id=t["id"], story=t["story"].strip(),
                        files=t.get("files", []), done=t["done"])
    raise SystemExit(f"No task {task_id!r} in tasks/{app_id}.toml")


def make_files(task, folder):
    """Creates the files the local has on their device before the task starts."""
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in task.files:
        path = folder / f["name"]
        if f["kind"] == "photo":
            write_png(path, f["width"], f["height"])
        paths.append(path)
    return paths


def write_png(path, width, height):
    """A large, camera sized PNG made with the standard library alone (noise does not compress, like a photo)."""
    raw = b"".join(b"\x00" + os.urandom(width * 3) for _ in range(height))
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 1)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def check(task, web, inputs):
    """Proof: done only when the app's real output says so, never on the local's word."""
    rule = task.done
    for d in web.downloads:
        if "download_ext" in rule and d.suffix.lower().lstrip(".") not in rule["download_ext"]:
            continue
        if rule.get("smaller_than_input") and inputs and d.stat().st_size >= min(p.stat().st_size for p in inputs):
            continue
        return True, d
    return False, None
