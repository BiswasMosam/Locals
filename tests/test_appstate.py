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


class RowsTests(unittest.TestCase):
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
