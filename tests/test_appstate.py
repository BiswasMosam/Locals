"""What the window knows, with no window: where it opens, and where the day has got to.

This machine has a second monitor standing on end to the left of the main one, at x = -1080. AMINAL's neural
map once opened in a corner, mostly off the screen, and a window remembered on a monitor that has since been
unplugged cannot be dragged back by anyone. The day's state is here because the window shows a local as at
work, and a remark they make after they have finished (their take) must not light their window again.
"""
import unittest

from town import appstate, people

MAIN, LEFT = (0, 0, 1920, 1080), (-1080, -371, 1080, 1920)


class PlaceTests(unittest.TestCase):
    def test_it_opens_where_it_was_closed(self):
        saved = {"x": 200, "y": 120, "w": 1200, "h": 800, "maximised": True}
        self.assertEqual(appstate.place(saved, [MAIN, LEFT]), saved)

    def test_the_monitor_on_the_left_is_a_real_place(self):
        saved = {"x": -1000, "y": 100, "w": 900, "h": 700}
        self.assertEqual(appstate.place(saved, [MAIN, LEFT])["x"], -1000)

    def test_a_window_left_on_a_monitor_that_is_gone_opens_on_the_main_one(self):
        spot = appstate.place({"x": -1000, "y": 100, "w": 900, "h": 700}, [MAIN])
        self.assertTrue(0 <= spot["x"] and spot["x"] + spot["w"] <= 1920 and 0 <= spot["y"])

    def test_a_title_bar_above_the_screen_cannot_be_reached(self):
        spot = appstate.place({"x": 300, "y": -200, "w": 900, "h": 700}, [MAIN])
        self.assertGreaterEqual(spot["y"], 0)

    def test_nonsense_in_the_file_is_not_a_place(self):
        for saved in (None, {}, {"x": "left"}, {"x": 0, "y": 0, "w": 10, "h": 10}):
            spot = appstate.place(saved, [MAIN])
            self.assertEqual((spot["w"], spot["h"], spot["maximised"]), (1360, 860, False))

    def test_a_small_screen_gets_a_window_that_fits_it(self):
        spot = appstate.place(None, [(0, 0, 1280, 720)])
        self.assertTrue(spot["w"] <= 1280 and spot["h"] <= 720)


def day(*who):
    return {"type": "day", "phase": "start", "day": "2026-01-01_000000", "task": "Test: save", "locals": list(who), "index": [1, 1]}


class LiveTests(unittest.TestCase):
    def test_a_day_from_start_to_end(self):
        live = appstate.Live()
        live.start()
        for e in ({"type": "year", "phase": "start", "task": "Test: save"}, day("neha", "sunil"),
                  {"type": "event", "local": "neha", "kind": "START", "says": "on a laptop"},
                  {"type": "step", "local": "neha", "step": 1, "line": "tap [B]", "thought": "Save it."}):
            live.hear(e)
        v = live.view()
        self.assertEqual((v["who"], v["step"], v["states"]), ("neha", 1, {"neha": "work", "sunil": "out"}))
        live.hear({"type": "event", "local": "neha", "kind": "DONE", "says": "1 step"})
        self.assertEqual((live.view()["who"], live.view()["finished"]), ("", 1))
        live.hear({"type": "year", "phase": "end", "task": "Test: save", "days": []})
        self.assertFalse(live.view()["running"])
        self.assertEqual(live.view()["states"]["neha"], "DONE")  # the windows keep the day's result until the next day

    def test_their_take_afterwards_does_not_send_them_back_to_work(self):
        live = appstate.Live()
        for e in (day("neha"), {"type": "event", "local": "neha", "kind": "GAVE UP", "says": "Gave up on the app."},
                  {"type": "event", "local": "neha", "kind": "TAKE", "says": "The button was not where I looked."}):
            live.hear(e)
        self.assertEqual((live.view()["states"]["neha"], live.view()["who"]), ("GAVE UP", ""))

    def test_a_day_the_session_had_to_end_is_over_and_says_why(self):
        live = appstate.Live()
        live.start()
        live.stopping = True
        live.hear({"type": "year", "phase": "end", "task": "", "days": [], "error": "The engine stopped by itself (exit 1)."})
        v = live.view()
        self.assertEqual((v["running"], v["stopping"], v["error"]), (False, False, "The engine stopped by itself (exit 1)."))


def step(who, n, line="tap [A]"):
    return {"type": "step", "local": who, "step": n, "line": line, "thought": "trying", "at": f"{n}s", "secs": 1.5, "shot": f"runs/x/{who}/step-{n:02d}.png"}


def event(who, kind, says=""):
    return {"type": "event", "local": who, "kind": kind, "says": says, "at": "9s", "shot": None}


class StripTests(unittest.TestCase):
    """A local's strip is read at a glance, so an amber cell has to sit on the step that went wrong. The engine
    reports a slip just before the step it spoiled, and being stuck just after the step that got nowhere."""

    def live(self):
        return appstate.Live({"neha": "Neha", "sunil": "Sunil"}, {"neha": 10, "sunil": 4})

    def test_a_slip_marks_the_step_after_it_and_stuck_the_step_before(self):
        live = self.live()
        for e in (day("sunil"), step("sunil", 1), event("sunil", "SLIP"), step("sunil", 2), step("sunil", 3),
                  event("sunil", "STUCK"), event("sunil", "GAVE UP"), event("sunil", "TAKE", "It never changed.")):
            live.hear(e)
        row = live.strips()[0]
        self.assertEqual([c["tone"] for c in row["cells"]], ["step", "warn", "warn"])
        self.assertEqual((row["outcome"], row["left"]), ("GAVE UP", 0))  # patience spent is not patience left
        self.assertEqual(live.moments[row["end"]]["kind"], "GAVE UP")
        self.assertEqual(live.moments[row["cells"][1]["i"]]["step"], 2)  # a cell leads back to its own moment

    def test_patience_left_is_shown_while_they_work_and_when_they_finish(self):
        live = self.live()
        for e in (day("neha", "sunil"), step("neha", 1), step("neha", 2)):
            live.hear(e)
        neha, sunil = live.strips()
        self.assertEqual((len(neha["cells"]), neha["left"], sunil["cells"], sunil["left"]), (2, 8, [], 4))
        live.hear(event("neha", "DONE"))
        self.assertEqual(live.strips()[0]["left"], 8)

    def test_every_moment_has_every_key_whatever_the_entry_left_out(self):
        bare = appstate.moment({"type": "event", "local": "neha", "kind": "ERROR"}, 0, {})
        full = appstate.moment(step("neha", 1), 1, {"neha": "Neha"})
        self.assertEqual(sorted(bare), sorted(full))
        self.assertEqual([type(bare[k]) for k in sorted(bare)], [type(full[k]) for k in sorted(full)])
        self.assertEqual((bare["shot"], bare["tone"], full["name"]), ("", "bad", "Neha"))

    def test_a_kept_day_opens_as_it_ended(self):
        live = self.live()
        meta = {"day": "2026-11-03_145536", "task": "PixelShift: small-jpg", "locals": ["neha", "sunil"],
                "results": {"neha": "DONE", "sunil": "GAVE UP"}}
        live.load(meta, [step("neha", 1), event("neha", "DONE"), step("sunil", 1), event("sunil", "GAVE UP")])
        v = live.view()
        self.assertEqual((v["kept"], v["running"], v["open"], v["who"]), (True, False, True, ""))
        self.assertEqual((v["states"], v["verdict"]["head"]), ({"neha": "DONE", "sunil": "GAVE UP"}, "1 of 2 got it done."))
        live.clear()
        self.assertFalse(live.view()["open"])


class VerdictTests(unittest.TestCase):
    def test_nine_in_ten_of_at_least_three_is_great_by_name(self):
        v = appstate.verdict("PixelShift: small-jpg", [{"results": {"a": "DONE", "b": "DONE", "c": "SAYS DONE"}}])
        self.assertEqual((v["win"], v["head"]), (True, "PixelShift is great."))

    def test_two_locals_are_not_enough_to_celebrate(self):
        v = appstate.verdict("PixelShift: small-jpg", [{"results": {"a": "DONE", "b": "DONE"}}])
        self.assertEqual((v["win"], v["head"]), (False, "2 of 2 got it done."))

    def test_a_plain_count_says_what_else_happened(self):
        v = appstate.verdict("localhost-5173: sign-up", [{"results": {"a": "DONE", "b": "GAVE UP", "c": "GAVE UP", "d": "ASKED"}}])
        self.assertEqual((v["win"], v["sub"]), (False, "25% · 2 gave up · 1 asked for help"))

    def test_a_stopped_day_has_no_verdict(self):
        self.assertIsNone(appstate.verdict("PixelShift: small-jpg", [{"results": {"a": "DONE", "b": "STOPPED"}}]))
        self.assertIsNone(appstate.verdict("PixelShift: small-jpg", [{"results": {}}]))

    def test_a_year_names_its_hardest_day(self):
        days = [{"label": "Mon 2 Feb", "results": {"a": "DONE", "b": "DONE"}}, {"label": "Wed 1 Jul, heavy rain", "results": {"a": "DONE", "b": "GAVE UP"}}]
        v = appstate.verdict("PixelShift: small-jpg", days)
        self.assertEqual((v["win"], v["head"], v["note"]), (False, "3 of 4 local days done.", "Hardest day: Wed 1 Jul, heavy rain, 1 of 2 done."))
        self.assertEqual(appstate.verdict("a.example: x", [{"results": {"a": "DONE", "b": "DONE"}}] * 2)["head"], "Your site is great all year.")


def kept(day_id, results, steps, task="PixelShift: small-jpg", stuck=()):
    """A kept day as records.day_log returns it."""
    entries = [step(i, n + 1) for i, count in steps.items() for n in range(count)] + [event(i, "STUCK") for i in stuck]
    return {"meta": {"day": day_id, "task": task, "locals": list(steps), "results": results,
                     "runs": {i: {"steps": n} for i, n in steps.items() if i in results}}, "entries": entries}


class CompareTests(unittest.TestCase):
    """Two days of one task, before and after a change to the app, is the question the days are kept for."""

    def test_the_earlier_day_is_first_whichever_was_picked_first(self):
        old = kept("2026-11-03_145536", {"rohit": "DONE", "rashmi": "GAVE UP", "anil": "DONE", "meera": "DONE"},
                   {"rohit": 10, "rashmi": 9, "anil": 7, "meera": 4}, stuck=["rashmi", "rashmi"])
        new = kept("2026-11-03_153643", {"rohit": "GAVE UP", "rashmi": "DONE", "anil": "DONE", "sunil": "DONE"},
                   {"rohit": 12, "rashmi": 4, "anil": 5, "sunil": 3})
        c = appstate.compare(new, old, {"rohit": "Rohit"})
        self.assertEqual((c["before"]["day"], c["after"]["day"], c["same_task"]), ("2026-11-03_145536", "2026-11-03_153643", True))
        self.assertEqual(c["head"], "3 of 4 got it done, then 3 of 4.")
        self.assertEqual({r["id"]: r["change"] for r in c["rows"]},
                         {"rohit": "worse", "rashmi": "better", "anil": "quicker", "meera": "only before", "sunil": "only after"})
        self.assertEqual(c["note"], "1 did better and 1 did worse, of the 3 who went out both days.")
        rashmi = next(r for r in c["rows"] if r["id"] == "rashmi")
        self.assertEqual((rashmi["before"]["stuck"], rashmi["before"]["steps"], rashmi["after"]["steps"]), (2, 9, 4))
        self.assertEqual(c["rows"][0]["name"], "Rohit")

    def test_someone_the_day_ended_before_is_not_counted_as_having_gone(self):
        stopped = kept("2026-11-15_025439", {"rohit": "STOPPED"}, {"rohit": 1, "sunil": 0})
        later = kept("2026-11-15_063444", {"sunil": "DONE"}, {"sunil": 3})
        c = appstate.compare(stopped, later, {})
        self.assertEqual(c["head"], "0 of 1 got it done, then 1 of 1.")
        self.assertEqual(c["note"], "Nobody went out on both days, so there is no one to compare.")

    def test_two_different_tasks_are_said_to_be_different(self):
        c = appstate.compare(kept("2026-11-03_145536", {"a": "DONE"}, {"a": 2}),
                             kept("2026-11-04_182107", {"a": "DONE"}, {"a": 2}, task="Fill.ai: fill-job-form"), {})
        self.assertFalse(c["same_task"])
        self.assertEqual(c["rows"][0]["change"], "same")


class EstimateTests(unittest.TestCase):
    MACHINE = {"gpu": {"name": "RTX 4060", "total_gb": 8.0, "used_gb": 2.0},
               "model": {"name": "qwen3:4b-instruct", "reachable": True, "installed": True, "size_gb": 2.3, "loaded": False, "vram_gb": 0},
               "pace": {"secs_per_step": 8.0, "steps_per_task": 5.0, "measured": True}, "android": {"adb": True, "devices": []}}

    def test_more_locals_and_more_days_take_more_time(self):
        one = appstate.estimate(self.MACHINE, [10], 1)
        self.assertEqual((one["typical"], one["worst"], one["time"], one["problem"]), (40.0, 80.0, "About 40 seconds", ""))
        year = appstate.estimate(self.MACHINE, [10, 3], 12)
        self.assertEqual((year["typical"], year["worst"]), (12 * (40 + 24), 12 * (80 + 24)))  # nobody takes more steps than their patience
        self.assertIn("2 locals on 12 days", year["note"])

    def test_what_stops_a_day_is_said_before_it_is_started(self):
        down = {**self.MACHINE, "model": {"reachable": False}}
        self.assertIn("Ollama is not running", appstate.estimate(down, [10], 1)["problem"])
        missing = {**self.MACHINE, "model": {**self.MACHINE["model"], "installed": False}}
        self.assertIn("ollama pull qwen3:4b-instruct", appstate.estimate(missing, [10], 1)["problem"])
        self.assertIn("emulator", appstate.estimate(self.MACHINE, [10], 1, "apk")["problem"])
        ready = {**self.MACHINE, "android": {"adb": True, "devices": ["emulator-5554"]}}
        self.assertIn("APK", appstate.estimate(ready, [10], 1, "apk", has_apk=False)["problem"])
        self.assertEqual(appstate.estimate(ready, [10], 1, "apk")["problem"], "")

    def test_a_full_gpu_is_a_warning_and_not_a_refusal(self):
        full = {**self.MACHINE, "gpu": {"name": "RTX 4060", "total_gb": 8.0, "used_gb": 7.0}}
        e = appstate.estimate(full, [10], 1)
        self.assertTrue(e["gpu_tight"])
        self.assertEqual(e["problem"], "")
        self.assertEqual(appstate.estimate({**self.MACHINE, "gpu": None}, [], 1)["time"], "Nobody yet")


class KeepTests(unittest.TestCase):
    def test_a_chosen_file_is_copied_where_a_task_card_may_point(self):
        import shutil
        import tempfile
        from pathlib import Path
        from town import session
        from town.people import ROOT
        (ROOT / "runs").mkdir(exist_ok=True)
        runs = Path(tempfile.mkdtemp(dir=ROOT / "runs", prefix="_test-"))
        self.addCleanup(shutil.rmtree, runs, True)
        source = runs / "my app (final).apk"
        source.write_bytes(b"12345")
        got = session.keep_file(source, runs)
        self.assertEqual((got["name"], got["size"]), ("my_app_final_.apk", 5))
        self.assertTrue((ROOT / got["path"]).is_file())
        self.assertRegex(got["path"], r"/_uploads/[0-9a-f]{8}/my_app_final_\.apk$")
        with self.assertRaises(ValueError):
            session.keep_file(runs / "not-there.apk", runs)


class SceneTests(unittest.TestCase):
    """The town in the window looks like the day: its rain, its festival, a lockdown. A day kept before days carried
    a scene, and the town with no day on it in a year with no calendar, must still give the page every key."""

    def test_the_day_on_the_page_carries_its_weather_and_its_festival(self):
        live = appstate.Live()
        live.hear({"type": "day", "phase": "start", "day": "2026-09-14_000000", "task": "T", "locals": ["sunil"],
                   "scene": {"date": "2026-09-14", "label": "Mon 14 Sep 2026", "rain": "heavy", "lights": "ganesh", "pandemic": None, "season": "monsoon"}})
        self.assertEqual(live.view()["scene"], {"rain": "heavy", "lights": "ganesh", "pandemic": "", "label": "Mon 14 Sep 2026"})
        live.clear()
        self.assertEqual(live.view()["scene"], {"rain": "", "lights": "", "pandemic": "", "label": ""})

    def test_a_day_kept_without_a_scene_is_a_clear_night(self):
        live = appstate.Live()
        live.load({"day": "2026-11-03_022611", "task": "T", "locals": ["rohit"], "results": {"rohit": "DONE"}}, [])
        self.assertEqual(live.view()["scene"]["rain"], "")
        self.assertEqual(appstate.scene_view(None), {"rain": "", "lights": "", "pandemic": "", "label": ""})


class RowsTests(unittest.TestCase):
    def test_the_roster_is_everyone_once_by_family_and_job(self):
        from town import records, session
        roster = appstate.roster(records.town_info(session.Session())["groups"])
        ids = [p["id"] for f in roster for j in f["jobs"] for p in j["people"]]
        self.assertEqual(sorted(ids), sorted(l.id for l in people.everyone()))
        self.assertTrue(all(p["patience"] > 0 for f in roster for j in f["jobs"] for p in j["people"]))

    def test_everyone_in_town_is_one_window_in_one_family(self):
        from town import records, session
        fams = appstate.families(records.town_info(session.Session())["groups"])
        ids = [p["id"] for f in fams for p in f["people"]]
        self.assertEqual(sorted(ids), sorted(l.id for l in people.everyone()))
        self.assertEqual(len(ids), len(set(ids)))

    def test_running_a_day_again_asks_for_the_same_day(self):
        meta = {"day": "2026-11-04_185046", "ref": "pixelshift:small-jpg", "locals": ["rohit"], "date": "2026-07-01"}
        self.assertEqual(appstate.spec_again(meta), {"locals": ["rohit"], "task": "pixelshift:small-jpg", "take": True, "dates": ["2026-07-01"]})
        old = appstate.day_row({"day": "2026-11-03_022611", "task": "PixelShift: small-jpg", "locals": ["rohit"], "results": {"rohit": "DONE"}}, {"rohit": "Rohit"})
        self.assertEqual((old["again"], old["time"], old["locals"]), (False, "02:26", [{"id": "rohit", "name": "Rohit", "outcome": "DONE"}]))


if __name__ == "__main__":
    unittest.main()
