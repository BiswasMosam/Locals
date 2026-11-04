"""Seeing pixels: what the screenshot shows that the page's words cannot (study/pixels.md).

Two measurements, both taken from the screenshot a local is looking at, never from the page's own styles, so they
also work on Android apps and on pictures of text:

- What is really there. A control whose words or symbol leave no mark on the screenshot (a loading screen covers it,
  or it has not been drawn yet) is not shown to the local: a person cannot tap what they cannot see.
- Contrast. Inside each control, the most common colour is the background and the colour farthest from it in
  brightness is the text or symbol; their ratio is WCAG's contrast ratio. Below 4.5:1 for normal text, or 3:1 for large
  text and for symbols, WCAG calls it too faint, and the control is marked faint for the local and for the experts.
  A control that is a picture (many colours, none of them most of the box) is not measured.
- What stands out, on a laptop. A saliency model of colour and brightness against the surroundings predicts where
  people first look on web pages (Still and Masciocchi 2010, after Itti and Koch). On phones it does not: in eye
  tracking on mobile app screens, bright and large elements did not draw the eye; text, pictures and the top left did
  (Leiva and others 2020). So the ranking is made for laptop screens only, and phones keep their reading order.
"""
import numpy as np
from PIL import Image

NORMAL, LARGE = 4.5, 3.0     # WCAG 1.4.3 and 1.4.11: normal text; large text (24 px, or 18.66 px bold) and symbols
PICTURE = 0.25               # a box whose most common colour covers less than this share is a picture, not a label
STANDS_OUT = 3               # how many things a laptop screen's ranking names
SALIENT = 12.0               # colour difference (CIE Lab) below which nothing on the screen stands out at all
BLANK = 1.0                  # the contrast of a box with nothing drawn in it
SAME = 3.0                   # a colour difference (CIE Lab) too small to notice: about one just noticeable difference


def linear(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def luminance(rgb):
    """WCAG relative luminance of an array of RGB colours (..., 3)."""
    lin = linear(np.asarray(rgb, dtype=np.float64))
    return lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722


def ratio(a, b):
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def lab(rgb):
    """sRGB to CIE Lab (D65), for colour differences a person would see."""
    lin = linear(np.asarray(rgb, dtype=np.float64))
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def contrast(pixels):
    """Text or symbol against its background inside one box; 1.0 when the box is one flat colour (nothing on it can
    be seen, as when something covers it or it has not been drawn yet); None for a picture."""
    px = pixels.reshape(-1, 3)
    if len(px) < 16:
        return None
    quant = (px // 32).astype(np.int32)  # coarse enough that film grain or a soft gradient stays one background
    keys = quant[:, 0] * 64 + quant[:, 1] * 8 + quant[:, 2]
    values, counts = np.unique(keys, return_counts=True)
    top = values[counts.argmax()]
    if counts.max() / len(px) < PICTURE:
        return None
    bg = px[keys == top].mean(axis=0)
    lum, bg_lum = luminance(px), luminance(bg)
    far = np.abs(lum - bg_lum)
    if far.max() < 0.01:
        return BLANK
    # The ink: the pixels farthest from the background, past the soft edges of the letters.
    ink = px[far >= np.quantile(far, 0.97)]
    return round(ratio(float(bg_lum), float(luminance(ink.mean(axis=0)))), 2)


def large(item):
    size, weight = item.get("font", 0), item.get("weight", 400)
    return size >= 24 or (size >= 18.66 and weight >= 700)


def needs(item):
    """The contrast WCAG asks of this control."""
    return NORMAL if item.get("text") and not large(item) else LARGE


def clamp(box, w, h):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    return max(0, x0), max(0, y0), min(w, x1), min(h, y1)


def surround(arr, box):
    """How different a box looks from what is around it: CIE Lab difference of the average colours, or None."""
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = box
    inner = arr[y0:y1, x0:x1].reshape(-1, 3).astype(np.float64)
    pad = max(8, (x1 - x0) // 2, (y1 - y0) // 2)
    X0, Y0, X1, Y1 = clamp((x0 - pad, y0 - pad, x1 + pad, y1 + pad), w, h)
    ring = arr[Y0:Y1, X0:X1].reshape(-1, 3).astype(np.float64)
    n = len(ring) - len(inner)
    if n <= 0:
        return None
    return float(np.linalg.norm(lab(inner.mean(axis=0)) - lab((ring.sum(axis=0) - inner.sum(axis=0)) / n)))


def look(img, screen, box_of, device):
    """Marks each control with its measured contrast and whether it is faint, and on a laptop names what stands out.
    img: the screenshot (PIL); box_of(item): the control's box in the screenshot's pixels (x0, y0, x1, y1)."""
    arr = np.asarray(img.convert("RGB"))
    h, w = arr.shape[:2]
    scores = []
    for item in screen["items"]:
        x0, y0, x1, y1 = clamp(box_of(item), w, h)
        if x1 - x0 < 3 or y1 - y0 < 3:
            continue
        diff = surround(arr, (x0, y0, x1, y1))
        if item.get("runs"):
            # Text is measured run by run, so a faint line inside a big bright card is not hidden by the rest.
            measured = []
            for run in item["runs"]:
                rx0, ry0, rx1, ry1 = clamp(box_of(run), w, h)
                c = contrast(arr[ry0:ry1, rx0:rx1]) if rx1 - rx0 >= 3 and ry1 - ry0 >= 3 else None
                if c is not None:
                    measured.append((c, run))
            if measured and all(c == BLANK for c, _ in measured):
                item["unseen"] = True  # its words leave no mark on the screen: covered, or not drawn yet
                continue
            measured = [(c, r) for c, r in measured if c != BLANK]
            if measured:
                item["contrast"] = min(c for c, _ in measured)
                faint = [r["text"] for c, r in measured if c < (LARGE if large(r) else NORMAL)]
                if faint and not item.get("disabled"):  # WCAG leaves inactive controls out
                    item["faint_lines"] = faint
                    item["line_contrast"] = {r["text"]: c for c, r in measured if r["text"] in faint}
                    # The control reads as faint when its main words do: the biggest text in it, not a dim index number.
                    main = max(measured, key=lambda m: m[1].get("font", 0))[1]["text"]
                    item["faint"] = len(faint) == len(measured) or main in faint
        elif item.get("role") in ("text box", "dropdown"):
            pass  # a field's box holds its border, a caret or a value the page draws itself: not one label to measure
        else:
            c = contrast(arr[y0:y1, x0:x1])
            if c == BLANK and (diff is None or diff < SAME):
                item["unseen"] = True  # one flat colour, the same as around it: nothing there to see
                continue
            if c is not None and c != BLANK:
                item["contrast"] = c
                item["faint"] = not item.get("disabled") and c < needs(item)
        if device == "laptop" and diff is not None:
            area = (x1 - x0) * (y1 - y0) / (w * h)
            scores.append((diff * min(1.0, area * 40) ** 0.5, diff, item["id"]))
    if device == "laptop":
        ranked = sorted((s for s in scores if s[1] >= SALIENT), reverse=True)
        screen["stands_out"] = [i for _, _, i in ranked[:STANDS_OUT]]
    return screen


def words_for(contrast):
    """How a person would put it: under 3:1 (the floor for normal vision in ISO 9241-3) is hard to make out; between
    that and what WCAG asks, it is readable for most, but low contrast."""
    return "faint, hard to make out" if contrast < LARGE else "low contrast"


def look_file(path, screen, box_of, device):
    with Image.open(path) as img:
        return look(img, screen, box_of, device)


def visible_only(screen):
    """The screen without the controls the pixels show nothing of; returns how many were left out."""
    before = len(screen["items"])
    screen["items"] = [i for i in screen["items"] if not i.get("unseen")]
    screen["unseen"] = before - len(screen["items"])
    return screen["unseen"]


def faint_items(steps):
    """Every faint label or line across a run's screens, once each, lowest contrast first."""
    seen = {}
    for s in steps:
        for i in s["screen"]["items"]:
            names = i.get("faint_lines") or ([i["text"] or i["hint"] or i.get("looks") or "an icon"] if i.get("faint") else [])
            for name in names:
                if name not in seen or i["contrast"] < seen[name]["contrast"]:
                    seen[name] = i
    return sorted(seen.items(), key=lambda kv: kv[1]["contrast"])
