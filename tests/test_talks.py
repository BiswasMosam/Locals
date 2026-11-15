"""A talk given from the window, and the town's report as the window shows it.

A talk calls the model for minutes, so it runs in the session's worker like a day does, and Stop has to end it
the same way. What is different is what is left behind: a day that is stopped is still a day worth keeping, but
a talk asks who remembered the point and for the marks only at the end, so a stopped talk keeps nothing, and no
half-written room.json may turn up in the list of kept talks. The page shows a talk being given and a kept talk
with one piece of code, so the two must come out the same: these tests give a talk through the real worker's
code with the model scripted, and read it back both ways.
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path
from unittest import mock

from tests.test_room import SLIDES, deck, scripted
from tests.test_session import SessionTests
from town import appstate, records, report, room, session
from town.people import ROOT

TALK_OPENING = """
import json, os, subprocess, sys, time
spec = json.loads(open(sys.argv[-1], encoding="utf-8").read())
def say(**entry):
    print(json.dumps(entry), flush=True)
say(type="talk", phase="reading", talk="2026-01-01_000000_class", room="class", name="A college class", files=["t.pptx"])
say(type="talk", phase="heard", part="P1", local="vandana", attention=80, inner="", unknown=[], events=[])
"""
TALK_ENDS_WHEN_ASKED = TALK_OPENING + """
while not os.path.exists(spec["stop"]):
    time.sleep(0.05)
say(type="talk", phase="end", talk="2026-01-01_000000_class", stopped=True)
"""
TALK_DEAF = TALK_OPENING + """
time.sleep(120)
"""
TALK_FALLS_OVER = TALK_OPENING + """
raise RuntimeError("the model went away")
"""
SPEC = {"kind": "talk", "room": "class", "files": ["t.pptx"]}
over = lambda e: e["type"] == "talk" and e["phase"] == "end"


class TalkSessionTests(unittest.TestCase):
    """The session with a talk in its worker, set up the way the day's own tests set theirs up."""
    setUp, session, until = SessionTests.setUp, SessionTests.session, SessionTests.until

    def test_a_talk_that_ends_when_asked(self):
        s = self.session(TALK_ENDS_WHEN_ASKED, grace=15)
        q, _ = s.watch()
        s.start(SPEC)
        self.until(q, lambda e: e.get("phase") == "heard")
        self.assertTrue(s.busy())
        s.stop()
        heard = self.until(q, over)
        self.assertFalse(s.busy())
        self.assertTrue(heard[-1]["stopped"])

    def test_a_talk_that_will_not_end_is_killed_and_nothing_is_kept(self):
        s = self.session(TALK_DEAF)
        q, _ = s.watch()
        s.start(SPEC)
        self.until(q, lambda e: e.get("phase") == "heard")
        s.stop()
        heard = self.until(q, over)
        self.assertEqual((heard[-1]["talk"], heard[-1]["stopped"]), ("2026-01-01_000000_class", True))
        self.assertNotIn("error", heard[-1])
        self.assertFalse(list(self.runs.glob("**/room.json")))
        self.assertFalse(list(self.runs.glob("**/day.json")))  # and it is not written down as a day

    def test_a_talk_whose_worker_falls_over_says_why(self):
        s = self.session(TALK_FALLS_OVER)
        q, _ = s.watch()
        s.start(SPEC)
        heard = self.until(q, over)
        self.assertIn("the model went away", heard[-1]["error"])
        self.assertFalse(heard[-1]["stopped"])
        s.start(SPEC)  # and the town is not left believing a talk is still being given
        self.until(q, over)

    def give(self, stop=None, on=None, room_id="class"):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        deck(tmp / "t.pptx", SLIDES)
        heard, stop = [], stop or threading.Event()

        def send(entry):
            heard.append(entry)
            if on:
                on(entry, stop)

        spec = {"kind": "talk", "room": room_id, "files": [str(tmp / "t.pptx")], "runs": str(self.runs), "grade": True}
        with mock.patch.object(room.mind, "chat", side_effect=scripted), contextlib.redirect_stdout(io.StringIO()):
            session.work(spec, send, stop)
        return heard

    def test_the_real_worker_gives_a_talk_and_the_page_shows_it_as_it_shows_a_kept_one(self):
        heard = self.give()
        json.dumps(heard)  # everything it reports must survive the trip down a pipe
        self.assertEqual([e["phase"] for e in heard if e["phase"] not in ("heard", "study", "recall", "marks")],
                         ["reading", "start", "point", "sorting", "part", "part", "recalling", "room", "marking", "marked", "end"])
        self.assertEqual(sum(e["phase"] == "heard" for e in heard), 2 * 5)  # two parts, five in the class
        talk_id = heard[-1]["talk"]
        self.assertNotIn("stopped", heard[-1])
        saved = records.talk_log(talk_id, self.runs)
        self.assertEqual(saved["grade"]["graders"][0]["base"], 15.0)
        self.assertEqual(saved["listeners"][1]["inner"], ["That happened to me too."] * 2)  # a thought filed under each part
        self.assertEqual([t["talk"] for t in records.talks(self.runs)], [talk_id])

        live, kept = appstate.Hall(), appstate.Hall()
        live.start()
        for e in heard:
            live.hear(e)
        kept.load(talk_id, saved)
        a, b = live.view(), kept.view()
        self.assertFalse(a["running"])
        for key in ("head", "sub", "point", "stated", "parts", "listeners", "markers", "marks", "measured", "notes", "clock"):
            self.assertEqual(a[key], b[key], key)
        self.assertEqual(a["head"], "16 of 20.")  # 15 from the marks, and the rubric's point for a room hooked till the end
        self.assertEqual(a["listeners"][0]["cells"][0]["tone"], "hooked")
        row = appstate.talk_row({**saved, "talk": talk_id})
        self.assertEqual((row["mark"], row["name"], len(row["lit"])), ("16 of 20", "A college class", 5))

    def test_a_talk_stopped_part_way_keeps_nothing(self):
        def after_the_first(entry, stop):
            if entry["phase"] == "heard":
                stop.set()

        heard = self.give(on=after_the_first)
        self.assertEqual((heard[-1]["phase"], heard[-1]["stopped"]), ("end", True))
        self.assertEqual(sum(e["phase"] == "heard" for e in heard), 1)
        self.assertFalse((self.runs / "rooms").exists())
        hall = appstate.Hall()
        for e in heard:
            hall.hear(e)
        self.assertEqual((hall.view()["head"], hall.view()["sub"]), ("The talk was stopped.", "Nothing of it was kept."))

    def test_a_talk_stopped_while_it_is_marked_keeps_nothing_either(self):
        def at_the_marks(entry, stop):
            if entry["phase"] == "marking":
                stop.set()

        heard = self.give(on=at_the_marks)
        self.assertTrue(heard[-1]["stopped"])
        self.assertFalse((self.runs / "rooms").exists())

    def test_a_crowd_gives_no_marks_and_the_page_counts_who_got_the_point(self):
        heard = self.give(room_id="crowd")
        hall = appstate.Hall()
        for e in heard:
            hall.hear(e)
        v = hall.view()
        self.assertEqual((v["marks"]["rubric"], v["marks"]["graders"]), ("", []))
        self.assertRegex(v["head"], r"^\d of \d could say your point\.$")

    def test_a_file_that_is_not_a_talk_is_an_error_in_a_sentence(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "empty.txt").write_text("", encoding="utf-8")
        heard = []
        with contextlib.redirect_stdout(io.StringIO()):
            session.work({"kind": "talk", "room": "class", "files": [str(tmp / "empty.txt")], "runs": str(self.runs)},
                         heard.append, threading.Event())
        self.assertIn("empty", heard[-1]["error"])

    def test_what_cannot_be_given_is_refused_in_a_sentence(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        deck(tmp / "t.pptx", SLIDES)
        (tmp / "notes.txt").write_text("Hello.", encoding="utf-8")
        (tmp / "more.md").write_text("Hello again.", encoding="utf-8")
        kept = {}
        for name in ("t.pptx", "notes.txt", "more.md"):
            kept[name] = session.keep_file(tmp / name)["path"]
            self.addCleanup(shutil.rmtree, (ROOT / kept[name]).parent, True)
        for body, words in (({"room": "nowhere", "files": [kept["t.pptx"]]}, "Choose a room"),
                            ({"room": "class", "files": []}, "Drop the talk"),
                            ({"room": "class", "files": [str(tmp / "t.pptx")]}, "Drop the talk"),  # not a file the window kept
                            ({"room": "class", "files": ["runs/_uploads/0000abcd/../../../people/neha.toml"]}, "Drop the talk"),
                            ({"room": "class", "files": [kept["notes.txt"], kept["more.md"]]}, "one of each"),
                            ({"room": "class", "files": [kept["t.pptx"]], "minutes": "ten"}, "number of minutes")):
            with self.assertRaises(ValueError) as refused:
                session.plan_talk(body)
            self.assertIn(words, str(refused.exception))
        spec = session.plan_talk({"room": "class", "files": [kept["t.pptx"], kept["notes.txt"]], "minutes": " 8 ",
                                  "point": "  Save   first. ", "grade": False})
        self.assertEqual((spec["kind"], spec["minutes"], spec["point"], spec["grade"]), ("talk", 8.0, "Save first.", False))
        self.assertIsNone(session.plan_talk({"room": "class", "files": [kept["t.pptx"]], "minutes": ""})["minutes"])


class OldTalkTests(unittest.TestCase):
    def test_a_talk_kept_before_thoughts_were_filed_by_part_still_opens(self):
        # Their thoughts were one list with the silent parts left out, so a thought cannot be put back under its part.
        old = {"room": "class", "name": "A college class", "source": "t.pptx", "seconds": 120, "point": "Save first.", "stated": None,
               "parts": [{"id": "P1", "title": "One", "start": 0, "seconds": 60, "moments": []},
                         {"id": "P2", "title": "Two", "start": 60, "seconds": 60, "moments": []}],
               "markers": [{"kind": "lost the room", "part": "P2", "says": "1 of 1 had drifted by P2"}],
               "listeners": [{"id": "mohit", "name": "Mohit", "number": 1, "job": "Student", "role": "audience", "why": "", "trail": [60, 30.4],
                              "events": [{"kind": "PHONE OUT", "part": "P2", "why": "too technical: CRDT"}], "thoughts": ["Fine."],
                              "unknown": ["CRDT", "CRDT"], "recall": {"same": "no", "why": "took in nothing but slide titles"}, "decided": ""}]}
        hall = appstate.Hall()
        hall.load("2026-11-03_180652_class", old)
        v = hall.view()
        mohit = v["listeners"][0]
        self.assertEqual([c["tone"] for c in mohit["cells"]], ["with", "low"])
        self.assertEqual([c["inner"] for c in mohit["cells"]], ["", ""])
        self.assertEqual((mohit["note"], mohit["unknown"], mohit["point"]),
                         ("Phone out at P2: too technical: CRDT", "CRDT", "took in nothing but slide titles"))
        self.assertEqual((v["head"], v["stated"], v["markers"][0]["tone"], v["kept"]),
                         ("0 of 1 could say your point.", "Never said in so many words.", "bad", True))

    def test_nobody_is_asleep_in_the_first_minutes_but_a_grader_can_stop_listening(self):
        result = {"room": "class", "name": "x", "parts": [{"id": "P1", "title": "One", "start": 0, "seconds": 60}],
                  "listeners": [{"id": "a", "name": "A", "role": "audience", "trail": [10]}, {"id": "g", "name": "G", "role": "grader", "trail": [10]}]}
        hall = appstate.Hall()
        hall.load("2026-11-03_180652_class", result)
        self.assertEqual([p["cells"][0]["band"] for p in hall.view()["listeners"]], ["phone out", "stopped listening"])

    def test_an_empty_page_has_every_key(self):
        v = appstate.Hall().view()
        self.assertEqual((v["open"], v["running"], v["listeners"], v["marks"]["graders"], v["head"]), (False, False, [], [], ""))

    def test_a_name_that_is_not_a_talk_is_never_a_path(self):
        for name in ("../people", "2026-11-03_180652_class/../..", "_test-grade", ""):
            with self.assertRaises(ValueError):
                records.talk_log(name)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.runs = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.runs, True)

    def day(self, name, task, results, runs=None):
        (self.runs / name).mkdir()
        (self.runs / name / "day.json").write_text(json.dumps({"day": name, "task": task, "results": results, "runs": runs or {}}),
                                                   encoding="utf-8")

    def test_the_window_and_the_terminal_count_the_same_runs(self):
        self.day("2026-01-01_000000", "Test: save", {"neha": "DONE", "rohit": "GAVE UP", "sunil": "STOPPED"},
                 {"neha": {"retries": 2, "unfixed": 0}, "rohit": {"retries": 1, "unfixed": 1}})
        self.day("2026-01-02_000000", "Test: send", {"neha": "SAYS DONE", "nobody-by-this-name": "ERROR"})
        s = report.summary(self.runs)
        self.assertEqual((s["runs"], s["tasks"], s["all"]), (3, 2, {"done": 2, "of": 3}))  # the stopped and the error are left out
        self.assertEqual(s["checked"], {"runs": 2, "clean": {"done": 1, "of": 1}, "cost": {"done": 0, "of": 1}, "retries": 3})
        text = report.report(self.runs)
        self.assertIn("finished                     2 of 3     67%   real people in usability tests: 78%", text)
        self.assertIn("    Test: save                   1 of 2     50%", text)
        v = appstate.report_view(s)
        self.assertEqual((v["head"], v["all"]["pct"], v["bench"]), ("2 of 3 runs got it done.", "67%", "78%"))
        self.assertEqual([(r["name"], r["done"], r["of"], r["pct"]) for r in v["by_task"]],
                         [("Test: save", 1, 2, "50%"), ("Test: send", 1, 1, "100%")])
        self.assertEqual((v["checked"], v["checked_runs"], v["clean"]["pct"], v["cost"]["pct"], v["retries"]), (True, 2, "100%", "0%", 3))

    def test_a_town_with_no_runs_yet_says_so(self):
        v = appstate.report_view(report.summary(self.runs))
        self.assertEqual((v["any"], v["head"], v["by_task"], v["checked"]), (False, "No run has finished yet.", [], False))
        self.assertIn("No finished runs yet", report.report(self.runs))


del SessionTests  # borrowed for its helpers; left here, the loader would run the day's tests again from this file


if __name__ == "__main__":
    unittest.main()
