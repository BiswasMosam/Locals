"""What locals see in the pixels, and the benchmark against real people's moves on Android in the Wild."""
import gzip
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from PIL import Image, ImageDraw

from town import aitw, mind, people, pixels

# The Fill.ai task cards point at the extension's test build in a Fill.ai checkout beside this one.
FILLAI_BUILT = (people.ROOT.parent / "Fill.ai" / "dist-test").is_dir()
NO_FILLAI = "needs Fill.ai beside Locals, built with npm run build:test"


def card(fg, bg=(255, 255, 255), size=(200, 60)):
    """A box of background with a bar of 'ink' across it, like a line of text."""
    img = Image.new("RGB", size, bg)
    ImageDraw.Draw(img).rectangle([20, 22, 180, 38], fill=fg)
    return img


def control(id, text="", runs=None, x=100, y=30, w=200, h=60, disabled=False):
    return {"id": id, "role": "button", "text": text, "lines": [text] if text else [], "hint": "", "disabled": disabled,
            "active": False, "checked": False, "value": "", "x": x, "y": y, "w": w, "h": h, "runs": runs or []}


def box_of(i):
    if "x0" in i:
        return i["x0"], i["y0"], i["x1"], i["y1"]
    return i["x"] - i["w"] / 2, i["y"] - i["h"] / 2, i["x"] + i["w"] / 2, i["y"] + i["h"] / 2


def screen_of(*items):
    return {"items": list(items), "blocks": [], "title": "Test", "url": "", "scrollable": False, "at_bottom": True}


class Contrast(unittest.TestCase):
    def test_black_on_white_is_twenty_one_to_one(self):
        self.assertAlmostEqual(pixels.contrast(__import__("numpy").asarray(card((0, 0, 0)))), 21.0, places=1)

    def test_the_ratio_matches_wcags_formula(self):
        # #777 on white is 4.48:1 by WCAG's formula: just under the 4.5 asked of normal text.
        self.assertAlmostEqual(pixels.contrast(__import__("numpy").asarray(card((0x77, 0x77, 0x77)))), 4.48, delta=0.02)

    def test_a_flat_box_has_nothing_on_it(self):
        self.assertEqual(pixels.contrast(__import__("numpy").asarray(Image.new("RGB", (50, 50), (30, 30, 30)))), pixels.BLANK)

    def test_a_picture_is_not_measured(self):
        noise = Image.frombytes("RGB", (64, 64), bytes((i * 37 + j * 91) % 256 for i in range(64 * 64) for j in range(3)))
        self.assertIsNone(pixels.contrast(__import__("numpy").asarray(noise)))

    def test_grey_text_is_faint_and_dark_text_is_not(self):
        img = Image.new("RGB", (400, 60), (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([20, 22, 180, 38], fill=(0xAA, 0xAA, 0xAA))     # 2.3:1
        d.rectangle([220, 22, 380, 38], fill=(0x22, 0x22, 0x22))    # 15.9:1
        screen = screen_of(control("A", "Light", x=100, w=200), control("B", "Dark", x=300, w=200))
        pixels.look(img, screen, box_of, "phone")
        a, b = screen["items"]
        self.assertTrue(a["faint"])
        self.assertFalse(b["faint"])
        self.assertIn("faint", mind.describe(screen, people.load("sunil"), [], []).split("[A]")[1].split("\n")[0])

    def test_a_faint_line_inside_a_bright_card_is_found(self):
        img = Image.new("RGB", (200, 100), (10, 10, 10))
        d = ImageDraw.Draw(img)
        d.rectangle([10, 10, 190, 30], fill=(240, 240, 240))
        d.rectangle([10, 60, 60, 75], fill=(70, 70, 70))  # the dim "In" label
        runs = [{"text": "Drop images", "x0": 5, "y0": 5, "x1": 195, "y1": 35, "font": 40, "weight": 700},
                {"text": "In", "x0": 5, "y0": 55, "x1": 65, "y1": 80, "font": 11, "weight": 400}]
        screen = screen_of(control("A", "Drop images In", runs, x=100, y=50, h=100))
        screen["items"][0]["lines"] = ["Drop images", "In"]
        pixels.look(img, screen, box_of, "phone")
        item = screen["items"][0]
        self.assertEqual(item["faint_lines"], ["In"])
        self.assertFalse(item["faint"])  # its first line is bright
        self.assertIn("In (faint)", mind.describe(screen, people.load("aarav"), [], []))

    def test_low_contrast_is_told_apart_from_hard_to_make_out(self):
        self.assertEqual(pixels.words_for(2.1), "faint, hard to make out")
        self.assertEqual(pixels.words_for(3.6), "low contrast")

    def test_greyed_out_controls_are_never_called_faint(self):
        screen = {"items": [control("A", "Send", disabled=True)]}
        pixels.look(card((0xCC, 0xCC, 0xCC)), screen, box_of, "phone")
        self.assertFalse(screen["items"][0]["faint"])

    def test_a_covered_control_is_left_out(self):
        # A loading screen paints over the page: the control is in the page, but nothing of it is on the screen.
        img = Image.new("RGB", (200, 60), (12, 12, 12))
        runs = [{"text": "Work", "x0": 20, "y0": 20, "x1": 120, "y1": 40, "font": 14, "weight": 400}]
        screen = {"items": [control("A", "Work", runs), control("B", "", x=100, y=30)]}
        pixels.look(img, screen, box_of, "phone")
        self.assertEqual(pixels.visible_only(screen), 2)
        self.assertEqual(screen["items"], [])


class StandsOut(unittest.TestCase):
    def test_a_filled_button_stands_out_on_a_laptop_and_not_on_a_phone(self):
        img = Image.new("RGB", (1000, 600), (250, 250, 250))
        d = ImageDraw.Draw(img)
        d.rectangle([400, 260, 600, 320], fill=(230, 80, 20))  # an orange button
        d.rectangle([100, 50, 200, 60], fill=(40, 40, 40))     # a text link
        items = [control("A", "Home", x=150, y=55, w=120, h=20), control("B", "Buy now", x=500, y=290, w=200, h=60)]
        laptop = pixels.look(img, {"items": [dict(i) for i in items]}, box_of, "laptop")
        self.assertEqual(laptop["stands_out"][0], "B")
        phone = pixels.look(img, {"items": [dict(i) for i in items]}, box_of, "phone")
        self.assertNotIn("stands_out", phone)  # on phones colour and size did not draw the eye (Leiva and others 2020)


def protobuf_example(features):
    """A tf.train.Example written by hand, the inverse of town/aitw.example."""
    def varint(n):
        out = b""
        while True:
            b, n = n & 0x7F, n >> 7
            out += bytes([b | (0x80 if n else 0)])
            if not n:
                return out
    field = lambda no, data: varint(no << 3 | 2) + varint(len(data)) + data
    entries = b""
    for name, value in features.items():
        if isinstance(value[0], bytes):
            inner = field(1, b"".join(field(1, v) for v in value))
        elif isinstance(value[0], float):
            inner = field(2, field(1, struct.pack(f"<{len(value)}f", *value)))
        else:
            inner = field(3, field(1, b"".join(varint(v) for v in value)))
        entries += field(1, field(1, name.encode()) + field(2, inner))
    return field(1, entries)


class AndroidInTheWild(unittest.TestCase):
    def step(self, **change):
        ex = {"episode_id": [b"42"], "step_id": [0], "episode_length": [2], "goal_info": [b"Open Gmail"],
              "results/action_type": [4], "results/yx_touch": [0.5, 0.5], "results/yx_lift": [0.5, 0.5],
              "results/type_action": [b""], "image/ui_annotations_text": [b"Gmail", b"Maps", b""],
              "image/ui_annotations_ui_types": [b"TEXT", b"TEXT", b"ICON_NAV_BAR_CIRCLE"],
              "image/ui_annotations_positions": [0.48, 0.4, 0.04, 0.2, 0.1, 0.1, 0.04, 0.2, 0.95, 0.45, 0.03, 0.1],
              "image/height": [10], "image/width": [6], "current_activity": [b"com.android.launcher/x"],
              "image/encoded": [bytes(180)]}
        ex.update(change)
        return ex

    def test_a_record_is_read_back_from_a_gzipped_tfrecord(self):
        data = protobuf_example(self.step())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shard.gz"
            with gzip.open(path, "wb") as f:
                f.write(struct.pack("<Q", len(data)) + b"\0" * 4 + data + b"\0" * 4)
            st = aitw.step(aitw.example(next(aitw.records(path))))
        self.assertEqual(st["goal"], "Open Gmail")
        self.assertEqual(st["texts"], ["Gmail", "Maps", ""])
        self.assertEqual(len(st["boxes"]), 3)
        self.assertAlmostEqual(st["touch"][0], 0.5, places=5)
        self.assertEqual(st["size"], (10, 6))

    def test_the_phone_keys_are_not_items(self):
        st = aitw.step(aitw.example(protobuf_example(self.step())))
        self.assertEqual([i["text"] for i in aitw.screen(st)["items"]], ["Maps", "Gmail"])  # top first

    def test_a_tap_on_the_same_element_matches(self):
        st = aitw.step(aitw.example(protobuf_example(self.step())))
        gmail = next(i for i in aitw.screen(st)["items"] if i["text"] == "Gmail")
        maps = next(i for i in aitw.screen(st)["items"] if i["text"] == "Maps")
        centre = lambda i: (i["box"][0] + i["box"][2] / 2, i["box"][1] + i["box"][3] / 2)
        self.assertTrue(aitw.judge("tap", centre(gmail), False, st))
        self.assertFalse(aitw.judge("tap", centre(maps), False, st))
        self.assertFalse(aitw.judge("back", None, False, st))
        self.assertFalse(aitw.judge("tap", centre(gmail), True, st))  # an answer no person could give never matches

    def test_scrolls_match_on_their_axis(self):
        down = aitw.step(aitw.example(protobuf_example(self.step(**{"results/yx_lift": [0.2, 0.5]}))))
        up = aitw.step(aitw.example(protobuf_example(self.step(**{"results/yx_lift": [0.8, 0.5]}))))
        sideways = aitw.step(aitw.example(protobuf_example(self.step(**{"results/yx_lift": [0.5, 0.9]}))))
        self.assertTrue(aitw.judge("scroll", None, False, down))
        self.assertTrue(aitw.judge("scroll", None, False, up))
        self.assertFalse(aitw.judge("scroll", None, False, sideways))
        self.assertFalse(aitw.reachable(sideways))

    def test_home_and_enter_are_out_of_reach(self):
        home = aitw.step(aitw.example(protobuf_example(self.step(**{"results/action_type": [6]}))))
        self.assertEqual(aitw.human(home), "home")
        self.assertFalse(aitw.reachable(home))


class LiveAppChecks(unittest.TestCase):
    """The checks the ring one tasks use: a call link tapped, a form filled, an extension that now knows them."""

    class FakeWeb:
        def __init__(self, called=(), filled=0, knows=None):
            self.called, self._filled, self._knows, self.downloads = list(called), filled, knows, []

        def filled(self):
            return self._filled

        def knows(self, path):
            return self._knows

    def test_the_new_task_cards_load_and_say_how_they_are_checked(self):
        from town import tasks
        for ref, words in (("biswas-fabricators:call-about-grills", "calls"), ("portfolio:resume", "resume"),
                           ("fillai:fill-job-form", "fields"), ("fillai:set-up", "extension")):
            with self.subTest(ref):
                if ref.startswith("fillai:") and not FILLAI_BUILT:
                    self.skipTest(NO_FILLAI)
                self.assertIn(words, tasks.describe_check(tasks.load(ref).done), ref)

    def test_a_call_link_proves_the_call(self):
        from town import tasks
        t = tasks.load("biswas-fabricators:call-about-grills")
        self.assertEqual(tasks.check(t, self.FakeWeb(), []), (False, None))
        self.assertEqual(tasks.check(t, self.FakeWeb(called=["tel:+910000000000"]), []), (True, None))

    @unittest.skipUnless(FILLAI_BUILT, NO_FILLAI)
    def test_a_form_counts_as_filled_from_eight_answers(self):
        from town import tasks
        t = tasks.load("fillai:fill-job-form")
        self.assertFalse(tasks.check(t, self.FakeWeb(filled=7), [])[0])
        self.assertTrue(tasks.check(t, self.FakeWeb(filled=10), [])[0])

    @unittest.skipUnless(FILLAI_BUILT, NO_FILLAI)
    def test_set_up_is_done_when_the_extension_has_a_name(self):
        from town import tasks
        t = tasks.load("fillai:set-up")
        self.assertFalse(tasks.check(t, self.FakeWeb(knows=None), [])[0])
        self.assertFalse(tasks.check(t, self.FakeWeb(knows="  "), [])[0])
        self.assertTrue(tasks.check(t, self.FakeWeb(knows="Asha Rani Verma"), [])[0])

    def test_a_box_with_no_label_is_read_by_the_words_above_it(self):
        box = {"id": "A", "role": "text box", "text": "", "lines": [], "hint": "Type your answer", "near": "Notice period",
               "disabled": False, "active": False, "checked": False, "value": "", "x": 10, "y": 10, "w": 100, "h": 30}
        seen = mind.describe(screen_of(box), people.load("aryan"), [], [])
        self.assertIn('[A] text box under "Notice period": empty, shows "Type your answer"', seen)


if __name__ == "__main__":
    unittest.main()
