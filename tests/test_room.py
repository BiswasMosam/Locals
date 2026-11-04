"""The rooms: reading a talk, the attention rules, the markers and the checks on every mark. No model, no Ollama."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pptx import Presentation
from pptx.util import Pt

from town import grade, room, talk
from town.people import ROOT


def deck(path, slides):
    d = Presentation()
    for title, lines, notes in slides:
        s = d.slides.add_slide(d.slide_layouts[1])
        s.shapes.title.text = title
        body = s.placeholders[1].text_frame
        for i, line in enumerate(lines):
            p = body.paragraphs[0] if i == 0 else body.add_paragraph()
            p.text = line
            p.runs[0].font.size = Pt(18)
        s.notes_slide.notes_text_frame.text = notes
    d.save(path)


SLIDES = [
    ("Why orders get lost", ["The signal drops in basements"], "Last month a shop owner lost an order in a basement when the signal dropped."),
    ("What we change", ["Save on the phone first", "Send when the signal returns"], "Every order is saved on the phone first and sent when the signal returns."),
]


class TalkTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_a_deck_with_notes_is_read_and_timed(self):
        deck(self.dir / "t.pptx", SLIDES)
        t = talk.load([self.dir / "t.pptx"])
        self.assertEqual([p.title for p in t.parts], ["Why orders get lost", "What we change"])
        self.assertEqual(t.parts[1].shown, ["Save on the phone first", "Send when the signal returns"])
        self.assertIn("basement", t.parts[0].said)
        self.assertEqual(t.parts[0].seconds, round(max(10.0, t.parts[0].words / talk.PACE * 60), 1))
        self.assertEqual(t.parts[1].start, t.parts[0].seconds)
        self.assertIn(18.0 * 7.5 / 7.5, t.parts[0].fonts)

    def test_minutes_stretch_the_talk(self):
        deck(self.dir / "t.pptx", SLIDES)
        self.assertAlmostEqual(talk.load([self.dir / "t.pptx"], minutes=4).seconds, 240, delta=1)

    def test_a_script_goes_where_it_says(self):
        deck(self.dir / "t.pptx", SLIDES)
        (self.dir / "s.txt").write_text("[slide 2]\nSecond things first.\n\n[slide 1]\nThen the first.", encoding="utf-8")
        t = talk.load([self.dir / "t.pptx", self.dir / "s.txt"])
        self.assertEqual([p.said for p in t.parts], ["Then the first.", "Second things first."])

    def test_an_unmarked_script_follows_the_slides_words(self):
        self.assertEqual(talk.align(["the signal drops in basements", "save it on the phone first"],
                                    [talk.Part("P1", "Lost orders", ["The signal drops in basements"], slide=True),
                                     talk.Part("P2", "The change", ["Save on the phone first"], slide=True)]), [0, 1])

    def test_a_script_alone_becomes_parts(self):
        (self.dir / "s.md").write_text("One.\n\n---\n\nTwo, about something else.", encoding="utf-8")
        t = talk.load([self.dir / "s.md"])
        self.assertEqual(len(t.parts), 2)
        self.assertFalse(t.deck)

    def test_a_recording_is_decoded_to_16_khz_mono(self):
        import math
        import wave
        with wave.open(str(self.dir / "tone.wav"), "wb") as w:  # one second of a tone, in stereo at 44.1 kHz
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"".join(int(8000 * math.sin(i / 10)).to_bytes(2, "little", signed=True) * 2 for i in range(44100)))
        samples = talk.decode(self.dir / "tone.wav")
        self.assertAlmostEqual(len(samples), 16000, delta=400)
        self.assertLess(abs(samples).max(), 1.0)

    def test_measure_counts_small_text_and_bare_slides(self):
        deck(self.dir / "t.pptx", SLIDES)
        facts = dict(talk.measure(talk.load([self.dir / "t.pptx"]), 10))
        self.assertIn("under 24 pt", facts["M3"])
        self.assertIn("2 of 2", facts["M4"])


def listener(age=25, role="audience", attention=70, words=("orders",), job="Cook", reading=250, pace=250):
    local = mock.Mock(age=age, job=job, habits={"words": list(words)}, number=1, limits=mock.Mock(read_words=8))
    local.name = "Test"
    return room.Listener(local=local, role=role, why="", mood="", attention=attention, pace=pace, reading=reading)


def part(said="", shown=(), seconds=60, slide=True):
    return talk.Part("P1", "A slide", list(shown), said=said, seconds=seconds, slide=slide)


class AttentionTests(unittest.TestCase):
    def hear(self, l, p, facts=None, reply=None, late=False, minute=0):
        l.took.append(room.take_in(l, p, minute))
        return room.update(l, p, facts or {"terms": [], "moments": []}, reply, minute, late)

    def test_drift_alone_is_half_a_point_a_minute_for_the_young(self):
        l = listener()
        changes, _ = self.hear(l, part())
        self.assertEqual(changes, {"too long without a break": -0.5})
        l.since_break = 30  # the fit found no speed up the longer a lecture runs without a break
        changes, _ = self.hear(l, part())
        self.assertEqual(changes, {"too long without a break": -0.5})

    def test_the_rules_reproduce_the_measured_lectures(self):
        from town import roomfit
        m = roomfit.measures()
        for name, (people, town) in m["szpunar"].items():
            self.assertAlmostEqual(town, people, delta=2, msg=name)  # minds wandering, % of probes
        self.assertIsNone(m["asleep_at"])  # time alone does not put a listener to sleep in 40 minutes
        fall = lambda xs: xs[0] - xs[-1]
        self.assertAlmostEqual(fall([t for _, _, t in m["farley"]]), fall([p for _, p, _ in m["farley"]]), delta=3)

    def test_older_minds_wander_less(self):
        self.assertEqual(room.age_drift(25), 1.0)
        self.assertEqual(room.age_drift(65), room.OLDER)
        self.assertAlmostEqual(room.age_drift(45), 0.85)

    def test_unknown_terms_cost_points_but_not_their_own_words_or_fields(self):
        l = listener(words=("API",))
        facts = {"terms": ["API", "Workbox", "IndexedDB", "invoice", "order"], "moments": []}
        kinds = {"api": "software", "workbox": "software", "indexeddb": "software", "invoice": "finance", "order": "everyday"}
        l.took.append(room.take_in(l, part("The API, Workbox and IndexedDB, then the invoice and the order."), 0))
        changes, unknown = room.update(l, part("The API, Workbox and IndexedDB, then the invoice and the order."), facts,
                                       {"matters": "somewhat"}, 0, False, kinds)
        self.assertEqual(unknown, ["Workbox", "IndexedDB", "invoice"])
        self.assertEqual(changes["too technical"], -3 * room.JARGON)
        l.fields = {"everyday", "software", "finance"}
        self.assertEqual(room.unknown_to(l, facts["terms"], kinds, "The API, Workbox and IndexedDB, then the invoice."), [])

    def test_a_term_they_never_heard_costs_nothing(self):
        l = listener()
        self.assertEqual(room.unknown_to(l, ["Workbox"], {"workbox": "software"}, "Only the title reached them."), [])

    def test_a_batch_the_model_runs_away_on_is_split_and_asked_again(self):
        def model(system, user, schema, seed, **kw):
            asked = user.split("\n\n")[-1].splitlines()
            if len(asked) > 2:
                raise json.JSONDecodeError("runaway", "", 0)
            return {"terms": [{"term": t, "field": "Technology"} for t in asked]}
        with mock.patch.object(room.mind, "chat", side_effect=model):
            kinds = room.classify(["Workbox", "TTL", "ETag", "Dexie", "UUID"], 1)
        self.assertEqual(kinds, {t: "software" for t in ("workbox", "ttl", "etag", "dexie", "uuid")})

    def test_fields_come_from_the_job_and_the_file(self):
        from town import people
        self.assertIn("software", room.fields_of(people.load("ishaan")))
        self.assertNotIn("software", room.fields_of(people.load("sunil")))
        self.assertIn("software", room.fields_of(people.load("kabir")))  # knows = ["software"] in his file

    def test_too_fast_only_beyond_their_pace(self):
        quick = " ".join(["word"] * 300)
        self.assertIn("too fast", self.hear(listener(pace=150), part(quick))[0])
        self.assertNotIn("too fast", self.hear(listener(pace=400), part(quick))[0])

    def test_a_wall_of_text_on_a_quick_slide(self):
        wall = [" ".join(["text"] * 20)] * 6
        changes, _ = self.hear(listener(reading=140), part(shown=wall, seconds=20))
        self.assertEqual(changes["too much to read on the slides"], -room.TEXT_CAP)

    def test_a_story_lifts_and_starts_the_drift_over(self):
        l = listener()
        l.since_break = 9
        changes, _ = self.hear(l, part("A story."), {"terms": [], "moments": [{"kind": "story", "quote": "x"}]})
        self.assertEqual(changes["the story"], room.BREAK)
        self.assertEqual(l.since_break, 0)

    def test_a_question_to_the_room_reaches_someone_asleep(self):
        l = listener(attention=10)
        changes, _ = self.hear(l, part(), {"terms": [], "moments": [{"kind": "question to the room", "quote": "x"}]}, minute=9)
        self.assertEqual(l.took[-1]["how"], "not taking anything in")
        self.assertIn("the question to the room", changes)

    def test_waiting_for_the_point(self):
        self.assertEqual(self.hear(listener(), part(), late=True)[0]["still waiting for the point"], -room.WAITING)

    def test_nobody_sleeps_early_and_graders_never_do(self):
        self.assertEqual(room.band(listener(attention=10), minute=3), "phone out")
        self.assertEqual(room.band(listener(attention=10), minute=9), "asleep")
        self.assertEqual(room.band(listener(attention=10, role="grader"), minute=1), "stopped listening")

    def test_band_changes_become_events(self):
        self.assertEqual(room.change("with you", "drifting"), "DRIFTING")
        self.assertEqual(room.change("phone out", "with you"), "BACK")
        self.assertEqual(room.change("with you", "hooked"), "HOOKED")
        self.assertIsNone(room.change("hooked", "with you"))
        self.assertIsNone(room.change("asleep", "phone out"))

    def test_quotes_and_terms_must_be_in_the_talk(self):
        self.assertTrue(room.found("lost the whole order", "He lost the whole order there."))
        self.assertFalse(room.found("a story about a dragon", "He lost the whole order there."))
        self.assertTrue(room.has_term("Service Worker", "the Service Worker lifecycle"))
        self.assertFalse(room.has_term("work", "the Service Worker lifecycle"))


class MarkerTests(unittest.TestCase):
    def crowd(self, trails, role="audience"):
        out = []
        for trail in trails:
            l = listener(role=role)
            l.trail, l.causes, l.unknown = trail, [{"too technical": -8}] * len(trail), ["Workbox"]
            l.recall = {"same": "yes"}
            out.append(l)
        return out

    def talk(self, n, seconds=60):
        return talk.Talk("t", [talk.Part(f"P{i + 1}", "x", seconds=seconds, start=i * seconds) for i in range(n)])

    def test_hooked_till_the_end(self):
        kinds = [m["kind"] for m in room.markers(self.crowd([[80, 75, 72], [70, 66, 71]]), self.talk(3), {"minutes": 10})]
        self.assertIn("hooked till the end", kinds)
        self.assertNotIn("lost the room", kinds)

    def test_lost_and_asleep_and_over_time(self):
        marks = room.markers(self.crowd([[60, 40, 10, 10], [55, 45, 12, 8], [70, 60, 40, 30]]), self.talk(4, 180), {"minutes": 10})
        found = {m["kind"]: m for m in marks}
        self.assertEqual(found["lost the room"]["part"], "P2")
        self.assertIn("too technical", found["lost the room"]["says"])
        self.assertEqual(found["the room fell asleep"]["part"], "P3")
        self.assertIn("over time", found)


EV = [{"id": "P1", "text": 'Slide: "Why orders get lost" / The speaker says: "a shop owner lost an order in a basement"'},
      {"id": "M1", "text": "The talk runs 2:00 (estimated), against a limit of 10 minutes: 8:00 to spare"}]
CRIT = [{"id": "organization"}, {"id": "message"}]


class MarkTests(unittest.TestCase):
    def test_a_mark_must_rest_on_evidence(self):
        reply = {"marks": [
            {"criterion": "organization", "level": 3, "reason": "It opened with the lost order in the basement.", "about": ["P1"]},
            {"criterion": "message", "level": 4, "reason": "Great energy throughout.", "about": ["P1"]},
        ]}
        kept, dropped = grade.check(reply, CRIT, EV, 4)
        self.assertEqual(list(kept), ["organization"])
        self.assertEqual(dropped[0]["why"], "does not talk about its evidence")

    def test_guesses_missing_evidence_and_the_scale(self):
        reply = {"marks": [
            {"criterion": "organization", "level": 3, "reason": "The order story might have been rehearsed.", "about": ["P1"]},
            {"criterion": "message", "level": 9, "reason": "The order story.", "about": ["P1"]},
            {"criterion": "message", "level": 2, "reason": "The order story.", "about": ["P7"]},
        ]}
        _, dropped = grade.check(reply, CRIT, EV, 4)
        self.assertEqual([d["why"] for d in dropped], ["guesses at what was not seen", "is off the scale", "has no evidence"])


def scripted(system, user, schema, seed, **options):
    """A stand in for the model that answers each kind of question in the shape it was asked for."""
    keys = set(schema["properties"])
    if keys == {"terms", "moments"}:
        return {"terms": ["basement"] if "basement" in user else [], "moments": [{"kind": "story", "quote": "lost an order in a basement"}]}
    if keys == {"terms"}:
        return {"terms": [{"term": "basement", "field": "everyday"}]}
    if keys == {"point"}:
        return {"point": "Orders should be saved on the phone first"}
    if keys == {"inner", "matters"}:
        return {"inner": "That happened to me too, like a broken gate.", "matters": "yes"}
    if keys == {"point", "remember", "question"}:
        return {"point": "Save orders on the phone first so none get lost.", "remember": "The basement.",
                "question": "How long does an order wait on the phone before it is sent?" if "Vandana" in system
                else "What does 'order' mean here?"}
    if keys == {"same"}:
        return {"same": "yes"}
    import re
    criteria = re.findall(r"^- (\w+) \(", user, re.M)
    named = {"organization": "Organization"}  # one mark comes back under the criterion's name, not its id
    return {"marks": [{"criterion": named.get(c, c), "level": 3, "reason": "The order was lost in a basement.", "about": ["P1"]}
                      for c in criteria], "overall": "Clear and short."}


class GradeRunTests(unittest.TestCase):
    """The whole command, from the files to the saved marks, with the model scripted."""

    def test_grade_command_end_to_end(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        deck(tmp / "t.pptx", SLIDES)
        out = ROOT / "runs" / "rooms" / "_test-grade"
        self.addCleanup(shutil.rmtree, out, True)
        argv = ["town", "grade", "class", str(tmp / "t.pptx")]
        buf = io.StringIO()
        with mock.patch.object(room.mind, "chat", side_effect=scripted), mock.patch.object(room, "folder", lambda _: out), \
                mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(buf):
            from town.__main__ import main
            main()
        saved = json.loads((out / "room.json").read_text(encoding="utf-8"))
        g = saved["grade"]["graders"][0]
        self.assertEqual(g["grader"], "vandana")
        self.assertIn("delivery", g["not marked"])  # no recording: the voice was never heard
        self.assertEqual(set(g["marks"]), {"organization", "language", "support", "message"})
        self.assertEqual(g["base"], 15.0)  # four criteria at 3 of 4, out of 20
        self.assertEqual(saved["listeners"][1]["thoughts"][0], "That happened to me too.")  # the tacked on comparison is cut
        self.assertEqual(saved["listeners"][0]["questions"], ["How long does an order wait on the phone before it is sent?"])
        self.assertEqual(saved["listeners"][1]["questions"], [])  # asking what an everyday word means is filling a box
        self.assertIn("THE ROOM'S MARK", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
