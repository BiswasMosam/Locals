"""What this machine has to spend: GPU memory, memory, and how fast past days ran."""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import urllib.request

from .mind import MODEL, OLLAMA
from .people import ROOT

GB = 1024 ** 3


def gpu():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout.strip().splitlines()
        name, total, used = (s.strip() for s in out[0].split(","))
        return {"name": name, "total_gb": int(total) / 1024, "used_gb": int(used) / 1024}
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def memory():
    if sys.platform == "win32":
        class Status(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                        ("avail", ctypes.c_ulonglong), ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                        ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong), ("avail_extended", ctypes.c_ulonglong)]
        s = Status()
        s.length = ctypes.sizeof(Status)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        return {"total_gb": s.total / GB, "used_gb": (s.total - s.avail) / GB}
    try:
        page = os.sysconf("SC_PAGE_SIZE")
        total, avail = page * os.sysconf("SC_PHYS_PAGES"), page * os.sysconf("SC_AVPHYS_PAGES")
        return {"total_gb": total / GB, "used_gb": (total - avail) / GB}
    except (ValueError, OSError, AttributeError):
        return None


def _get(path):
    with urllib.request.urlopen(f"{OLLAMA}{path}", timeout=3) as r:
        return json.load(r)


def model():
    info = {"name": MODEL, "reachable": False, "installed": False, "size_gb": None, "loaded": False, "vram_gb": 0}
    try:
        for m in _get("/api/tags").get("models", []):
            if m["name"] == MODEL:
                info.update(installed=True, size_gb=m["size"] / GB)
        info["reachable"] = True
        for m in _get("/api/ps").get("models", []):
            if m["name"] == MODEL:
                info.update(loaded=True, vram_gb=m.get("size_vram", 0) / GB)
    except (OSError, ValueError):
        pass
    return info


def pace():
    """Seconds per step and steps per task, measured from earlier days on this machine."""
    secs, lengths = [], []
    for feed in (ROOT / "runs").glob("*/*/feed.jsonl"):
        steps = 0
        for line in feed.open(encoding="utf-8"):
            entry = json.loads(line)
            if entry.get("type") == "step":
                steps += 1
                secs.append(entry.get("secs") or 0)
        if steps:
            lengths.append(steps)
    return {"secs_per_step": round(sum(secs) / len(secs), 1) if secs else 6.0,
            "steps_per_task": round(sum(lengths) / len(lengths), 1) if lengths else 6.0,
            "measured": bool(secs)}
