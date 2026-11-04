"""Tasks: saved cards in tasks/*.toml, your own sites in tasks/mine/, and the files a local starts with."""
import json
import os
import re
import shutil
import struct
import tomllib
import zlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks"
MINE = TASKS / "mine"  # sites you add from the dashboard; git ignores this folder


@dataclass
class Task:
    ref: str
    app: str
    url: str
    id: str
    story: str
    files: list
    done: dict
    platform: str = "web"   # web, or android for an app on an emulator or phone
    package: str = ""       # the Android app's package name
    apk: Path | None = None # installed before each local starts, if given
    device: str = ""        # phone or laptop when the app only runs on one (a desktop browser extension); else the local's
    extension: Path | None = None  # an unpacked browser extension loaded for the run
    seed: Path | None = None       # what the extension already knows (JSON for its storage), as if set up before
    toolbar: str = ""              # the extension's toolbar button, named as a person who installed it knows it
    toolbar_call: str = ""         # the function in the extension that its toolbar button runs
    serve: Path | None = None      # a folder of pages served on this machine for the task; url is then a path in it


def _path(app_id):
    if not re.fullmatch(r"(mine/)?[a-z0-9][a-z0-9_-]*", app_id):
        raise SystemExit(f"Not a task name: {app_id!r}")
    return TASKS / f"{app_id}.toml"


def load(ref):
    """ref looks like 'pixelshift:small-jpg' or 'mine/localhost-5173:sign-up'."""
    app_id, _, task_id = ref.partition(":")
    path = _path(app_id)
    if not path.exists():
        raise SystemExit(f"No task file tasks/{app_id}.toml")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    apk = (ROOT / data["apk"]).resolve() if data.get("apk") else None
    if apk and not apk.exists():
        raise SystemExit(f"The APK for {data['app']} is not at {apk}. Build it or fix the path in tasks/{app_id}.toml")
    near = lambda key, where=data: (ROOT / where[key]).resolve() if where.get(key) else None
    for t in data["task"]:
        if t["id"] == task_id:
            for key in ("extension", "serve"):
                if near(key) and not near(key).exists():
                    raise SystemExit(f"tasks/{app_id}.toml: {key} {near(key)} does not exist. Build it or fix the path.")
            return Task(ref=ref, app=data["app"], url=t.get("url", data.get("url", "")), id=t["id"], story=t["story"].strip(),
                        files=t.get("files", []), done=t.get("done", {}), platform=data.get("platform", "web"),
                        package=data.get("package", ""), apk=apk, device=data.get("device", ""), extension=near("extension"),
                        seed=near("seed", t), toolbar=data.get("toolbar", ""), toolbar_call=data.get("toolbar_call", ""),
                        serve=near("serve"))
    raise SystemExit(f"No task {task_id!r} in tasks/{app_id}.toml")


def catalogue():
    out = []
    for path in sorted(TASKS.glob("*.toml")) + sorted(MINE.glob("*.toml")):
        prefix = "mine/" if path.parent == MINE else ""
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        for t in data["task"]:
            out.append({"ref": f"{prefix}{path.stem}:{t['id']}", "app": data["app"], "url": t.get("url", data.get("url", "")),
                        "platform": data.get("platform", "web"), "story": t["story"].strip(),
                        "check": describe_check(t.get("done", {})), "mine": bool(prefix)})
    return out


def describe_check(done):
    if "page_text" in done:
        return f'the page shows "{done["page_text"]}"'
    if "url_contains" in done:
        return f'the address contains "{done["url_contains"]}"'
    if "download_ext" in done:
        return "a " + " or ".join(done["download_ext"]).upper() + " file is saved" + (", smaller than the original" if done.get("smaller_than_input") else "")
    if done.get("download"):
        return "a file is saved"
    if done.get("called"):
        return "they tapped a link that calls or messages"
    if "filled" in done:
        return f"at least {done['filled']} fields of the form hold an answer"
    if "extension_has" in done:
        return f"the extension has saved {done['extension_has']}"
    return "nothing: we take their word, marked as unchecked"


def slug(text, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40].strip("-") or fallback


def add_site(url, goal, check, value, files):
    """Saves a site from the dashboard as a task card in tasks/mine/ and returns its ref."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("The address must start with http:// or https://")
    if not goal.strip():
        raise ValueError("Say what the locals should try to do.")
    done = {"page_text": {"page_text": value}, "url_contains": {"url_contains": value},
            "download": {"download": True}, "word": {}}.get(check)
    if done is None or (check in ("page_text", "url_contains") and not value.strip()):
        raise ValueError("Say how we know it worked.")
    app_id = slug(parsed.netloc, "site")
    task_id = slug(" ".join(goal.split()[:6]), "task")
    lines = [f"app = {json.dumps(parsed.netloc)}", f"url = {json.dumps(url)}", "", "[[task]]",
             f"id = {json.dumps(task_id)}", f"story = {json.dumps(goal.strip())}"]
    if files:
        lines.append("files = [" + ", ".join(
            "{ name = %s, kind = \"given\", path = %s }" % (json.dumps(f["name"]), json.dumps(f["path"])) for f in files) + "]")
    lines.append("done = { " + ", ".join(f"{k} = {json.dumps(v)}" for k, v in done.items()) + " }")
    MINE.mkdir(parents=True, exist_ok=True)
    (MINE / f"{app_id}.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"mine/{app_id}:{task_id}"


def read_apk(apk):
    """The package name and app name inside an APK, read with aapt from the Android SDK build tools."""
    import os
    import subprocess
    sdk = os.environ.get("ANDROID_HOME") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk")
    tools = sorted(Path(sdk, "build-tools").glob("*/aapt*"), reverse=True)
    if not tools:
        raise ValueError("aapt was not found in the Android SDK build tools, so the APK cannot be read.")
    out = subprocess.run([str(tools[0]), "dump", "badging", str(apk)], capture_output=True, text=True, timeout=60).stdout
    package = re.search(r"package: name='([^']+)'", out)
    label = re.search(r"application-label:'([^']*)'", out)
    if not package:
        raise ValueError("That file does not look like an Android app.")
    return package.group(1), (label.group(1) if label else package.group(1))


def add_app(apk, goal, check, value, files):
    """Saves a dropped APK as an Android task card in tasks/mine/ and returns its ref."""
    if not goal.strip():
        raise ValueError("Say what the locals should try to do.")
    done = {"page_text": {"page_text": value}, "word": {}}.get(check)
    if done is None or (check == "page_text" and not value.strip()):
        raise ValueError("For an app, say which words on screen mean it worked, or take their word for it.")
    package, label = read_apk(ROOT / apk)
    app_id, task_id = slug(package, "app"), slug(" ".join(goal.split()[:6]), "task")
    lines = [f"app = {json.dumps(label)}", 'platform = "android"', f"package = {json.dumps(package)}",
             f"apk = {json.dumps(apk)}", "", "[[task]]", f"id = {json.dumps(task_id)}", f"story = {json.dumps(goal.strip())}"]
    if files:
        lines.append("files = [" + ", ".join(
            "{ name = %s, kind = \"given\", path = %s }" % (json.dumps(f["name"]), json.dumps(f["path"])) for f in files) + "]")
    lines.append("done = { " + ", ".join(f"{k} = {json.dumps(v)}" for k, v in done.items()) + " }")
    MINE.mkdir(parents=True, exist_ok=True)
    (MINE / f"{app_id}.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"mine/{app_id}:{task_id}"


def make_files(task, folder):
    """Creates the files the local has on their device before the task starts."""
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in task.files:
        path = folder / f["name"]
        if f["kind"] == "photo":
            write_png(path, f["width"], f["height"])
        elif f["kind"] == "given":
            shutil.copyfile(ROOT / f["path"], path)
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
    """Proof: done only when the app's real state says so, never on the local's word."""
    rule = task.done
    if "page_text" in rule:
        try:
            body = web.text()
        except Exception:
            body = ""
        return " ".join(rule["page_text"].lower().split()) in " ".join(body.lower().split()), None
    if "url_contains" in rule:
        return rule["url_contains"] in web.location(), None
    if rule.get("called"):
        return bool(getattr(web, "called", [])), None
    if "filled" in rule:
        return web.filled() >= rule["filled"], None
    if "extension_has" in rule:
        value = web.knows(rule["extension_has"]) if hasattr(web, "knows") else None
        return bool(value and str(value).strip()), None
    if not rule:
        return False, None
    for d in web.downloads:
        if "download_ext" in rule and d.suffix.lower().lstrip(".") not in rule["download_ext"]:
            continue
        if rule.get("smaller_than_input") and inputs and d.stat().st_size >= min(p.stat().st_size for p in inputs):
            continue
        return True, d
    return False, None
