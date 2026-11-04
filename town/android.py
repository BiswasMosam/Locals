"""Eyes and hands for Android apps: an emulator or phone, driven over adb, read through the accessibility tree."""
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from . import icons

PICTURES = "/sdcard/Pictures/Locals"


def adb_path():
    found = shutil.which("adb")
    if found:
        return found
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk")
    exe = Path(sdk) / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
    if exe.exists():
        return str(exe)
    raise RuntimeError("adb not found. Install the Android SDK platform tools or put adb on PATH.")


def code(i):
    s, i = "", i + 1
    while i > 0:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def where(x, y, w, h):
    """Words for an unlabelled control's place on screen: what a sighted person goes by when there is no label."""
    across = "left" if x < w / 3 else "right" if x > 2 * w / 3 else "middle"
    down = "top" if y < h / 3 else "bottom" if y > 2 * h / 3 else "middle"
    return "centre" if across == down == "middle" else f"{down} {across}".replace("middle ", "").replace(" middle", "")


class Android:
    def __init__(self, task, device, files, out_dir, watch=False):
        self.task, self.files, self.out = task, [Path(f) for f in files], Path(out_dir)
        self.adb = adb_path()
        self.downloads, self.page = [], None

    def sh(self, *args, binary=False, check=False):
        r = subprocess.run([self.adb, *args], capture_output=True, timeout=60)
        if check and r.returncode != 0:
            raise RuntimeError(r.stderr.decode(errors="replace").strip() or f"adb {' '.join(args)} failed")
        return r.stdout if binary else r.stdout.decode("utf-8", errors="replace")

    def __enter__(self):
        if "\tdevice" not in self.sh("devices"):
            raise RuntimeError("No Android device or emulator is connected. Start one, then try again.")
        apk = self.task.apk
        if apk:
            self.sh("install", "-r", str(apk), check=True)
        # Every local starts with the app as a new user would find it.
        self.sh("shell", "pm", "clear", self.task.package)
        self.sh("shell", "rm", "-rf", PICTURES)
        for f in self.files:
            self.sh("push", str(f), f"{PICTURES}/{f.name}", check=True)
            self.sh("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{PICTURES}/{f.name}")
        self.sh("shell", "input", "keyevent", "KEYCODE_HOME")
        self.sh("shell", "monkey", "-p", self.task.package, "-c", "android.intent.category.LAUNCHER", "1")
        density = re.findall(r"\d+", self.sh("shell", "wm", "density"))
        self.density = int(density[-1]) if density else 420  # to give control sizes in dp, the unit Android's guidance uses
        time.sleep(4)
        return self

    def observe(self):
        return {"platform": "android"}

    def __exit__(self, *exc):
        self.sh("shell", "am", "force-stop", self.task.package)

    def dump(self):
        for _ in range(3):
            self.sh("shell", "uiautomator", "dump", "/sdcard/locals-ui.xml")
            xml = self.sh("shell", "cat", "/sdcard/locals-ui.xml")
            if "<hierarchy" in xml:
                return ET.fromstring(xml[xml.index("<hierarchy"):])
            time.sleep(1)
        raise RuntimeError("Could not read the screen from the device.")

    def see(self, look=True):
        """The screen as items and readable lines. look=False skips naming unlabelled icons with the vision model."""
        root = self.dump()
        nodes = list(root.iter("node"))
        bounds = lambda n: [int(v) for v in re.findall(r"\d+", n.get("bounds", "[0,0][0,0]"))]
        w = max((bounds(n)[2] for n in nodes), default=1080)
        h = max((bounds(n)[3] for n in nodes), default=2400)
        items, blocks, self.boxes, self.crops, scrollable = [], [], {}, {}, False

        def label(n):
            return (n.get("text") or n.get("content-desc") or "").strip()

        def walk(n, inside_control):
            nonlocal scrollable
            x0, y0, x1, y1 = bounds(n)
            if n.get("scrollable") == "true":
                scrollable = True
            control = n.get("clickable") == "true" or n.get("checkable") == "true" or "EditText" in n.get("class", "")
            visible = x1 > x0 and y1 > y0
            if control and visible and not inside_control:
                cls = n.get("class", "")
                role = "text box" if "EditText" in cls else "checkbox" if n.get("checkable") == "true" else "tab" if "Tab" in (n.get("content-desc") or "") else "button"
                text = label(n) or " ".join(label(c) for c in n.iter("node") if c is not n and label(c))
                lines = [s.strip() for s in text.split("\n") if s.strip()]
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                shape = "round " if abs((x1 - x0) - (y1 - y0)) < 0.2 * (x1 - x0) else ""
                item = {"id": code(len(items)), "role": role, "text": " ".join(lines)[:300], "lines": lines[:10],
                        "hint": (n.get("hint") or "") if role == "text box" else "" if lines else f"{shape}{where(cx, cy, w, h)}".replace("round ", "round, "),
                        "disabled": n.get("enabled") == "false", "active": n.get("selected") == "true",
                        "checked": n.get("checked") == "true", "value": n.get("text", "") if role == "text box" else "",
                        "x": cx, "y": cy, "w": round((x1 - x0) * 160 / self.density), "h": round((y1 - y0) * 160 / self.density),
                        "unit": "dp"}
                items.append(item)
                self.boxes[item["id"]] = (cx, cy, role)
                self.crops[item["id"]] = (x0, y0, x1, y1)
                for c in n:
                    walk(c, True)
                return
            if visible and not inside_control and label(n):
                blocks.extend(s.strip() for s in label(n).split("\n") if s.strip())
            for c in n:
                walk(c, inside_control)

        walk(root, False)
        # Icons with no words: a sighted person still sees the symbol, so look at it.
        blank = [i for i in items if not i["text"] and i["role"] != "text box"]
        if blank and look:
            png = self.sh("exec-out", "screencap", "-p", binary=True)
            for i in blank:
                looks = icons.name(png, self.crops[i["id"]])
                if looks:
                    i["looks"] = looks
        self.last_text = " ".join(blocks + [i["text"] for i in items])
        return {"items": items, "blocks": list(dict.fromkeys(blocks))[:30], "title": self.task.app,
                "url": f"android:{self.task.package}", "scrollable": scrollable, "at_bottom": not scrollable}

    def box_of(self, item):
        """A control's box in the screenshot's pixels (town/pixels.py)."""
        return self.crops.get(item["id"], (0, 0, 0, 0))

    def settle(self):
        time.sleep(1.2)

    def act(self, action, target=None, text=""):
        box = self.boxes.get(target)
        try:
            if action in ("tap", "set") and box:
                self.sh("shell", "input", "tap", str(box[0]), str(box[1]), check=True)
            elif action == "type" and box:
                self.sh("shell", "input", "tap", str(box[0]), str(box[1]), check=True)
                time.sleep(0.4)
                safe = re.sub(r"([\\&;()<>|*'\"`$!?#])", r"\\\1", text).replace(" ", "%s")
                self.sh("shell", "input", "text", safe, check=True)
            elif action == "scroll":
                self.sh("shell", "input", "swipe", "540", "1700", "540", "700", "300", check=True)
            elif action == "back":
                self.sh("shell", "input", "keyevent", "KEYCODE_BACK", check=True)
            elif action == "wait":
                time.sleep(2)
            elif target is not None and not box:
                return "nothing happened (not on screen)"
            result = "ok"
        except Exception as e:
            result = f"nothing happened ({type(e).__name__})"
        self.settle()
        return result

    def snapshot(self, path):
        Path(path).write_bytes(self.sh("exec-out", "screencap", "-p", binary=True))

    def text(self):
        self.see()
        return self.last_text

    def location(self):
        return f"android:{self.task.package}"
