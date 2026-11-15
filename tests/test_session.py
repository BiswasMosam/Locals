"""The session: a day in a process of its own, and what is left on disk when that process is ended.

Before this, Stop was a flag the day read between steps. A model call that hung held the day for up to four
minutes, a stopped run could leave Python and Chrome children alive and still talking to Ollama, and a day
that never closed had no day.json, so it was missing from the list of past days. These tests stand a small
script in for the worker: one that ends when asked, one that ignores the request and has a child of its own,
and one that falls over. One test runs the real worker's code with the fake app and a scripted model, and the
last starts the real worker as a process, because the first real day hung before its first report while every
test above it was green: the worker waited on its input in a thread, and on Windows that held up everything else.
"""
import contextlib
import io
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from tests.test_day import FakeWeb, TASK, says
from town import day, session
from town.people import ROOT

# What every stand-in says first: a year of one day opens and Neha takes one step.
OPENING = """
import json, os, subprocess, sys, time
spec = json.loads(open(sys.argv[-1], encoding="utf-8").read())
def say(**entry):
    print(json.dumps(entry), flush=True)
say(type="year", phase="start", task="Test: save", dates=spec["dates"], locals=spec["locals"], pandemic=None)
say(type="day", phase="start", day="2026-01-01_000000", task="Test: save", ref="test:save", url="", locals=spec["locals"],
    model="none", index=[1, 1], date="2026-01-01", today="Thursday")
say(type="event", local="neha", kind="START", says="on a phone", at="0s", shot=None)
say(type="step", local="neha", step=1, line="tap [A]", thought="trying", at="1s", secs=1.0, shot="runs/x/step-01.png")
"""
ENDS_WHEN_ASKED = OPENING + """
while not os.path.exists(spec["stop"]):
    time.sleep(0.05)
say(type="event", local="neha", kind="STOPPED", says="The day was stopped.", at="2s", shot=None)
say(type="day", phase="end", day="2026-01-01_000000", task="Test: save", results={"neha": "STOPPED"}, panel=None, ended_at=time.time())
say(type="year", phase="end", task="Test: save", days=[{"day": "2026-01-01_000000", "results": {"neha": "STOPPED"}}], ended_at=time.time())
"""
DEAF_WITH_A_CHILD = OPENING + """
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
open(sys.argv[1], "w").write(str(child.pid))
time.sleep(120)
"""
FALLS_OVER = OPENING + """
raise RuntimeError("the browser went away")
"""
SPEC = {"ref": "test:save", "locals": ["neha"], "dates": ["2026-01-01"]}


def alive(pid):
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:  # ended but not yet collected by anyone still counts as gone
        return Path(f"/proc/{pid}/stat").read_text().split(")")[-1].split()[0] != "Z"
    except OSError:
        return True


class SessionTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runs").mkdir(exist_ok=True)
        self.runs = Path(tempfile.mkdtemp(dir=ROOT / "runs", prefix="_test-"))
        self.addCleanup(shutil.rmtree, self.runs, True)

    def session(self, script, *args, grace=0.5):
        path = self.runs / "worker.py"
        path.write_text(textwrap.dedent(script), encoding="utf-8")
        s = session.Session(self.runs, [sys.executable, str(path), *map(str, args)], grace)
        self.addCleanup(s.close, 0)
        return s

    def until(self, q, wanted, seconds=20):
        """Everything heard up to and including the first entry that wanted() accepts."""
        heard, deadline = [], time.time() + seconds
        while time.time() < deadline:
            try:
                heard.append(q.get(timeout=0.2))
            except queue.Empty:
                continue
            if wanted(heard[-1]):
                return heard
        self.fail(f"Never heard it. Heard: {heard}")

    def test_a_day_that_ends_when_asked_is_left_as_the_worker_wrote_it(self):
        s = self.session(ENDS_WHEN_ASKED, grace=15)
        q, _ = s.watch()
        s.start(SPEC)
        self.until(q, lambda e: e["type"] == "step")
        self.assertTrue(s.busy())
        s.stop()
        heard = self.until(q, lambda e: e["type"] == "year" and e["phase"] == "end")
        self.assertFalse(s.busy())  # by the time the end is heard, the next day can start
        self.assertEqual([e["kind"] for e in heard if e.get("kind") == "STOPPED"], ["STOPPED"])  # the worker's, not a second one
        self.assertFalse((self.runs / "2026-01-01_000000" / "day.json").exists())  # the stand-in wrote none, and nothing was mended

    def test_a_day_that_will_not_end_is_killed_with_its_children_and_still_kept(self):
        note = self.runs / "child.pid"
        s = self.session(DEAF_WITH_A_CHILD, note)
        q, _ = s.watch()
        s.start(SPEC)
        self.until(q, lambda e: e["type"] == "step")
        while not note.exists() or not note.read_text():
            time.sleep(0.05)
        child = int(note.read_text())
        self.assertTrue(alive(child))
        s.stop()
        heard = self.until(q, lambda e: e["type"] == "year" and e["phase"] == "end")
        self.assertFalse(s.busy())
        for _ in range(50):
            if not alive(child):
                break
            time.sleep(0.1)
        self.assertFalse(alive(child), "the worker's own child outlived the stop")
        saved = json.loads((self.runs / "2026-01-01_000000" / "day.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["results"], {"neha": "STOPPED"})
        self.assertEqual(saved["today"], "Thursday")  # what the day said about itself when it opened is kept
        feed = [json.loads(l) for l in (self.runs / "2026-01-01_000000" / "neha" / "feed.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual((feed[-1]["kind"], feed[-1]["shot"]), ("STOPPED", "runs/x/step-01.png"))
        self.assertEqual(heard[-1]["days"][0]["results"], {"neha": "STOPPED"})
        self.assertNotIn("error", heard[-1])

    def test_a_worker_that_falls_over_is_an_error_with_its_last_words(self):
        s = self.session(FALLS_OVER)
        q, _ = s.watch()
        s.start(SPEC)
        heard = self.until(q, lambda e: e["type"] == "year" and e["phase"] == "end")
        self.assertIn("the browser went away", heard[-1]["error"])
        saved = json.loads((self.runs / "2026-01-01_000000" / "day.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["results"], {"neha": "ERROR"})
        s.start(SPEC)  # and the town is not left believing a day is still running
        self.until(q, lambda e: e["type"] == "year" and e["phase"] == "end")

    def test_only_one_day_at_a_time(self):
        s = self.session(ENDS_WHEN_ASKED)
        s.start(SPEC)
        with self.assertRaises(session.Busy):
            s.start(SPEC)

    def test_someone_who_arrives_late_is_told_the_day_so_far(self):
        s = self.session(ENDS_WHEN_ASKED)
        first, _ = s.watch()
        s.start(SPEC)
        self.until(first, lambda e: e["type"] == "step")
        _, so_far = s.watch()
        self.assertEqual([e["type"] for e in so_far], ["year", "day", "event", "step"])

    def test_what_cannot_be_run_is_refused_in_a_sentence(self):
        for body, words in (({"locals": [], "task": "pixelshift:small-jpg"}, "at least one local"),
                            ({"locals": ["neha"], "task": "pixelshift:no-such-task"}, "No task"),
                            ({"locals": ["neha"], "task": "pixelshift:small-jpg", "dates": ["1800-01-01"]}, ""),
                            ({"locals": ["neha"], "app": {"apk": "../../somewhere/else.apk", "goal": "x", "check": "word"}}, "APK")):
            with self.assertRaises(ValueError) as refused:
                session.plan(body)
            self.assertIn(words, str(refused.exception))
        spec = session.plan({"locals": ["neha", "../etc", "nobody-by-this-name"], "task": "pixelshift:small-jpg",
                             "dates": ["2026-07-01"], "pandemic": "plague"})
        self.assertEqual((spec["locals"], spec["dates"], spec["pandemic"], spec["take"]), (["neha"], ["2026-07-01"], None, True))

    def test_the_real_worker_runs_a_day_and_reports_it(self):
        heard, stop = [], threading.Event()
        spec = {"ref": "test:save", "locals": ["neha"], "dates": ["2026-07-01"], "runs": str(self.runs), "take": False}
        with mock.patch.object(day, "Web", FakeWeb), mock.patch.object(day.mind, "STAGES", 1), \
                mock.patch.object(session.tasks, "load", return_value=TASK), \
                mock.patch.object(day.mind, "decide", side_effect=[says("tap", "B")]), contextlib.redirect_stdout(io.StringIO()):
            session.work(spec, heard.append, stop)
        self.assertEqual([(e["type"], e.get("phase")) for e in heard if e["type"] in ("year", "day")],
                         [("year", "start"), ("day", "start"), ("day", "end"), ("year", "end")])
        self.assertEqual(heard[-1]["days"][0]["results"], {"neha": "DONE"})
        json.dumps(heard)  # everything it reports must survive the trip down a pipe

    def test_the_real_worker_process_reports_before_it_does_anything_else(self):
        # No browser and no model: a task that is not there ends it at once. What matters is that it got that far.
        s = session.Session(self.runs, grace=0.5)
        self.addCleanup(s.close, 0)
        q, _ = s.watch()
        s.start({**SPEC, "ref": "pixelshift:no-such-task"})
        heard = self.until(q, lambda e: e["type"] == "year" and e["phase"] == "end", seconds=60)
        self.assertIn("No task", heard[-1]["error"])
        self.assertEqual([p.suffix for p in (self.runs / "_session").iterdir()], [".log"])  # only the transcript is left


if __name__ == "__main__":
    unittest.main()
