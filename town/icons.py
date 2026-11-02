"""Reading an icon that has no label, the way a sighted person would: a small vision model names the symbol."""
import base64
import hashlib
import io
import json
import os
import urllib.request

from PIL import Image

from .mind import OLLAMA

MODEL = os.environ.get("LOCALS_EYES_MODEL", "qwen2.5vl:3b")
ASK = ("This is one button from a phone app. Name the symbol on it in one to three plain words, "
       "for example: plus, back arrow, search, menu, camera, trash bin, share, pencil, three dots. "
       "Answer with the words only.")
_seen = {}


def name(png, box):
    """The words for the symbol inside box (x0, y0, x1, y1) of a screenshot, or "" if the model cannot say."""
    crop = Image.open(io.BytesIO(png)).convert("RGB").crop(box)
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    key = hashlib.sha1(buf.getvalue()).hexdigest()
    if key not in _seen:
        body = {"model": MODEL, "stream": False, "keep_alive": "10m", "options": {"temperature": 0},
                "messages": [{"role": "user", "content": ASK, "images": [base64.b64encode(buf.getvalue()).decode()]}]}
        try:
            req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                words = json.load(r)["message"]["content"].strip().strip(".").lower()
            _seen[key] = " ".join(words.split()[:3]) if len(words) < 40 else ""
        except (OSError, ValueError, KeyError):
            _seen[key] = ""
    return _seen[key]
