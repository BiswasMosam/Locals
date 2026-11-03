"""The parts that make a local human, shape their day and keep their take honest."""
import io
import random
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path

from PIL import Image

from town import derive, expertise, people, watch, year
from town.calibrate import measure
from town.limits import skim, slip, typo
from town.people import ROOT


def item(id, x, y, w=60, h=60):
    return {"id": id, "x": x, "y": y, "w": w, "h": h, "disabled": False}


class Limits(unittest.TestCase):
    def test_skimming_stops_at_the_reading_budget(self):
        self.assertEqual(skim("one two three four", 2), "one two …")
        self.assertEqual(skim("one two", 5), "one two")

    def test_a_slip_lands_on_the_nearest_control(self):
        items = [item("A", 0, 0), item("B", 0, 50), item("C", 0, 500)]
        self.assertEqual(slip(random.Random(1), 1.0, "A", items), "B")
        self.assertEqual(slip(random.Random(1), 0.0, "A", items), "A")

    def test_small_targets_are_missed_more(self):
        big = [item("A", 0, 0, 60, 60), item("B", 0, 80)]
        small = [item("A", 0, 0, 300, 16), item("B", 0, 80)]
        trials = lambda items: sum(slip(random.Random(i), 0.1, "A", items) != "A" for i in range(3000)) / 3000
        self.assertAlmostEqual(trials(big), 0.1, delta=0.02)
        self.assertAlmostEqual(trials(small), 0.3, delta=0.03)  # three times, the most a target's size can add
        self.assertAlmostEqual(sum(slip(random.Random(i), 0.1, "A", small, touch=False) != "A" for i in range(3000)) / 3000, 0.1, delta=0.02)

    def test_typos_only_touch_letters(self):
        self.assertEqual(typo(random.Random(1), 1.0, "12 34"), "12 34")
        self.assertNotEqual(typo(random.Random(1), 1.0, "sharma"), "sharma")


class Year(unittest.TestCase):
    def test_ganesh_chaturthi_is_a_holiday_in_its_festival(self):
        t = year.today(date(2026, 9, 14))
        self.assertEqual(t.holiday, "Ganesh Chaturthi")
        self.assertIn("festival:Ganeshotsav", t.keys())

    def test_days_that_come_back_every_month(self):
        self.assertIn("period:gst-due", year.today(date(2026, 5, 20)).keys())
        self.assertIn("period:month-start", year.today(date(2026, 8, 3)).keys())

    def test_the_same_date_always_has_the_same_weather(self):
        self.assertEqual(year.today(date(2026, 7, 20)).rain, year.today(date(2026, 7, 20)).rain)

    def test_period_names_follow_each_effect(self):
        _, text = year.shape(people.load("kavita"), year.today(date(2026, 5, 20)))
        self.assertIn("court summer vacation", text)
        _, text = year.shape(people.load("rashmi"), year.today(date(2026, 5, 20)))
        self.assertIn("school summer vacation", text)

    def test_a_lockdown_sends_nurses_to_work(self):
        nurse, _ = year.shape(people.load("mary"), year.today(date(2026, 4, 15), "lockdown"))
        self.assertIn("hospital", nurse.situation["place"].lower())

    def test_a_day_changes_patience_by_four_at_most(self):
        for d in year.sample(2026):
            for l in people.everyone()[::7]:
                shaped, _ = year.shape(l, year.today(d, "lockdown"))
                self.assertLessEqual(abs(shaped.limits.patience_steps - l.limits.patience_steps), 4)


class Town(unittest.TestCase):
    def test_ninety_nine_locals_with_unique_numbers(self):
        everyone = people.everyone()
        self.assertEqual([l.number for l in everyone], list(range(1, len(everyone) + 1)))

    def test_every_local_has_a_profile_a_lens_and_a_workplace(self):
        townview = (ROOT / "dashboard" / "townview.js").read_text(encoding="utf-8")
        for l in people.everyone():
            group = Path(l.profile).stem
            self.assertTrue((ROOT / l.profile).exists(), l.profile)
            self.assertIsNotNone(expertise.lens_for(l), group)
            self.assertIn(f"'{group}':", townview, f"{group} has no workplace in the town")

    def test_every_lens_cites_facts_that_exist(self):
        refs = {r["id"] for r in expertise.data()["reference"]}
        for lens in expertise.data()["lens"]:
            self.assertLessEqual(set(lens["cites"]), refs, lens["field"])

    def test_derived_numbers_match_the_files(self):
        for l in people.everyone():
            v = derive.derive(l, derive.traits(l))
            self.assertEqual((v["read_words"], v["slip_rate"], v["typo_rate"]),
                             (l.limits.read_words, l.limits.slip_rate, l.limits.typo_rate), l.id)

    def test_a_glove_taken_off_is_a_bare_hand(self):
        self.assertNotIn("gloves", derive.traits(people.load("ganesh"))["conditions"])


class Takes(unittest.TestCase):
    EV = [{"id": "S1", "kind": "S", "text": '"NOTHING LEAVES YOUR DEVICE" (on a button, step 1)'},
          {"id": "M1", "kind": "M", "text": "Largest content appeared after 0.2 s; layout shift 0.18; 87 KB transferred."}]
    REFS = [{"id": "web-vitals", "says": "..."}, {"id": "dpdp-notice", "says": "...", "needs": "data-sent"}]

    def why(self, remark, about=("M1",), cites=(), data_sent=None, kinds="SRWM"):
        kept, dropped = expertise.check({"remarks": [{"about": list(about), "kind": "technical", "remark": remark, "cites": list(cites)}]},
                                        self.EV, self.REFS, data_sent, kinds)
        return dropped[0]["why"] if dropped else "kept"

    def test_a_grounded_remark_is_kept(self):
        self.assertEqual(self.why("Layout shift is 0.18, over the 0.1 line.", cites=["web-vitals"]), "kept")

    def test_each_check(self):
        self.assertEqual(self.why("Layout shift is 0.18.", about=["M9"]), "has no evidence")
        self.assertEqual(self.why("Layout shift is 0.18.", cites=["made-up"]), "cites a fact that is not in the study")
        self.assertEqual(self.why("The device claim needs a notice.", about=["S1"], cites=["dpdp-notice"], data_sent=False),
                         "cites a rule the measurements show does not apply")
        self.assertEqual(self.why("Layout shift is 0.18.", kinds="WR"), "points at evidence outside their field")
        self.assertEqual(self.why("Layout shift 0.18 is like a wobbly table."), "turns their job into a comparison")
        self.assertEqual(self.why("Layout shift 0.18 violates the standard."), "concludes a law is broken")
        self.assertEqual(self.why("Layout shift 0.18 may come from fonts."), "guesses what the app does")
        self.assertEqual(self.why("The colours are pleasant overall."), "does not talk about its evidence")

    def test_a_take_drops_its_costume(self):
        self.assertEqual(expertise.short("I cut it like I'd slice meat. It worked."), "It worked.")

    def test_jpeg_quality_is_read_from_the_file(self):
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), "white").save(buf, "JPEG", quality=50)
        self.assertEqual(expertise.jpeg_quality(Image.open(buf)), 50)

    def test_glossary_comes_from_the_profile(self):
        self.assertIn(("Breakdown", "Incident"), expertise.glossary(people.load("ganesh")))


class Watching(unittest.TestCase):
    def test_names_compare_on_their_first_words(self):
        self.assertEqual(watch.norm("Convert and download!"), "convert and download")

    def test_a_recording_measures_misses_and_corrections(self):
        events = [{"kind": "tap", "control": False}, {"kind": "tap", "control": True, "text": "Save", "hint": ""},
                  {"kind": "tap", "control": True, "text": "Save", "hint": ""}, {"kind": "key"}, {"kind": "erase"}, {"kind": "key"}]
        m = measure({"outcome": "GAVE UP", "secs": 9, "events": events})
        self.assertEqual((m["steps"], m["taps"], m["missed"], m["keys"], m["erased"], m["longest_repeat"]), (4, 3, 1, 2, 1, 2))


if __name__ == "__main__":
    unittest.main()
