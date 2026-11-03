"""The run loop end to end, with a fake app and a scripted model: no browser, no Ollama."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from town import day, expertise, people, tasks
from town.people import ROOT


def item(id, text, y):
    return {"id": id, "role": "button", "text": text, "lines": [text], "hint": "", "disabled": False, "active": False,
            "checked": False, "value": "", "x": 100, "y": y, "w": 120, "h": 48}


class FakeWeb:
    """A one screen form: tapping Save saves it; Settings changes nothing."""

    def __init__(self, task, device, files, out_dir, watch=False):
        self.downloads, self.saved = [], False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def see(self):
        return {"items": [item("A", "Settings", 100), item("B", "Save", 300)], "blocks": ["Saved" if self.saved else "Your form"],
                "title": "Test", "url": "https://test/", "scrollable": False, "at_bottom": True}

    def snapshot(self, path):
        Path(path).write_bytes(b"")

    def act(self, action, target=None, text=""):
        self.saved = self.saved or (action == "tap" and target == "B")
        return "ok"

    def text(self):
        return "Saved" if self.saved else "Your form"

    def location(self):
        return "https://test/"

    def observe(self):
        return {"platform": "web", "console": [], "errors": [], "failed": [], "uploads": []}


TASK = tasks.Task(ref="test:save", app="Test", url="https://test/", id="save", story="Save the form.", files=[],
                  done={"page_text": "Saved"})


def says(action, target="", text=""):
    return {"thought": "trying", "action": action, "target": target, "text": text, "feeling": "fine"}


class RunTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runs").mkdir(exist_ok=True)
        self.out = Path(tempfile.mkdtemp(dir=ROOT / "runs", prefix="_test-"))
        self.addCleanup(shutil.rmtree, self.out, True)
        for target, value in ((day, {"Web": FakeWeb}), (day.mind, {"STAGES": 1})):  # one stage unless a test says two
            for name, fake in value.items():
                patcher = mock.patch.object(target, name, fake)
                patcher.start()
                self.addCleanup(patcher.stop)

    def local(self, who="neha", **limits):
        l = people.load(who)
        return replace(l, limits=replace(l.limits, slip_rate=0.0, typo_rate=0.0, **limits))

    def run_with(self, answers, local=None, take=False):
        with mock.patch.object(day.mind, "decide", side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
            outcome = day.run(local or self.local(), TASK, self.out, take=take)
        feed = [json.loads(l) for l in (self.out / "feed.jsonl").open(encoding="utf-8")]
        return outcome, json.loads((self.out / "run.json").read_text(encoding="utf-8")), feed

    def test_tapping_save_is_done(self):
        outcome, run, _ = self.run_with([says("tap", "B")])
        self.assertEqual(outcome, "DONE")
        self.assertEqual((run["retries"], run["unfixed"]), (0, 0))

    def test_a_model_mistake_is_asked_again_and_costs_no_step(self):
        outcome, run, feed = self.run_with([says("tap", "Z"), says("tap", "B")])
        self.assertEqual(outcome, "DONE")
        self.assertEqual((run["steps"], run["retries"], run["unfixed"]), (1, 1, 0))
        self.assertIn("MODEL", [e.get("kind") for e in feed])

    def test_a_mistake_that_stays_costs_one_step(self):
        outcome, run, _ = self.run_with([says("tap", "Z"), says("tap", "Y"), says("tap", "X"), says("tap", "B")])
        self.assertEqual(outcome, "DONE")
        self.assertEqual((run["steps"], run["retries"], run["unfixed"]), (2, 2, 1))

    def test_an_empty_slider_value_is_the_models_mistake(self):
        self.assertIsNotNone(day.misuse("type", "", "A", FakeWeb(TASK, "phone", [], ".").see()))
        self.assertIsNone(day.misuse("set", "", "A", FakeWeb(TASK, "phone", [], ".").see()))  # setting a button presses it

    def test_the_same_screen_again_and_again_makes_a_quitter_give_up(self):
        quitter = self.local("sunil", repeat_before_stuck=1)
        outcome, _, feed = self.run_with([says("tap", "A")], local=quitter)
        self.assertEqual(outcome, "GAVE UP")
        self.assertIn("STUCK", [e.get("kind") for e in feed])

    def test_patience_runs_out(self):
        outcome, run, _ = self.run_with([says("tap", "A"), says("tap", "A")], local=self.local(patience_steps=2, repeat_before_stuck=9))
        self.assertEqual((outcome, run["steps"]), ("GAVE UP", 2))

    def test_saying_done_is_not_being_done(self):
        outcome, _, _ = self.run_with([says("done")])
        self.assertEqual(outcome, "WRONG DONE")

    def test_two_stages_refuse_what_they_never_noticed(self):
        screen = FakeWeb(TASK, "phone", [], ".").see()
        self.assertIsNotNone(day.misuse("tap", "", "B", screen, noticed=["A"]))
        self.assertIsNone(day.misuse("tap", "", "A", screen, noticed=["A"]))

    def test_two_stages_look_around_before_a_quitter_quits(self):
        quitter = self.local("sunil", repeat_before_stuck=5)
        with mock.patch.object(day.mind, "STAGES", 2), mock.patch.object(day.mind, "notice", side_effect=[["A"], ["A", "B"]]):
            outcome, run, feed = self.run_with([says("stuck"), says("tap", "B")], local=quitter)
        self.assertEqual((outcome, run["steps"]), ("DONE", 2))
        self.assertIn("look around", [e.get("line") for e in feed])

    def test_their_take_keeps_what_is_grounded_and_drops_a_verdict(self):
        reply = {"take": "It saved after one tap.", "remarks": [
            {"about": ["S1"], "kind": "unclear", "remark": "The heading \"Your form\" does not say what the form is for.", "cites": []},
            {"about": ["S2"], "kind": "error in my field", "remark": "The Settings screen violates the law.", "cites": []},
        ]}
        with mock.patch.object(expertise.mind, "chat", side_effect=[reply, {"take": "", "remarks": []}]):
            self.run_with([says("tap", "B")], take=True)
        t = json.loads((self.out / "take.json").read_text(encoding="utf-8"))
        self.assertEqual([r["about"] for r in t["remarks"]], [["S1"]])
        self.assertEqual(t["dropped"][0]["why"], "concludes a law is broken")


if __name__ == "__main__":
    unittest.main()
