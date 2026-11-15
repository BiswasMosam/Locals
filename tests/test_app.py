"""The window's pages load, and what they read from the town is really there.

The pages are QML, which is only checked when it runs: a misspelt property or a call to something the town
does not have is silence in the editor and a warning (or a blank page) on the screen. The first time the
window was looked at, most of it was missing and nothing had failed. This loads the real pages with the demo
day, off the screen, and fails on any warning. It is skipped where PySide6 is not installed.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from town.people import ROOT

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
try:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
    from town import app
except ImportError as missing:  # PySide6 itself, or a system library it needs
    app = None
    WHY = str(missing)


@unittest.skipIf(app is None, "PySide6 is not installed here")
class WindowTests(unittest.TestCase):
    def test_every_page_loads_and_can_use_what_it_asks_the_town_for(self):
        (ROOT / "runs").mkdir(exist_ok=True)
        runs = Path(tempfile.mkdtemp(dir=ROOT / "runs", prefix="_test-"))
        self.addCleanup(shutil.rmtree, runs, True)
        qt = QGuiApplication.instance() or QGuiApplication([])
        town = app.Town(runs)
        engine, warnings = QQmlApplicationEngine(), []
        engine.warnings.connect(lambda found: warnings.extend(w.toString() for w in found))
        engine.rootContext().setContextProperty("town", town)
        engine.load(QUrl.fromLocalFile(str(app.UI / "Main.qml")))
        self.assertTrue(engine.rootObjects(), warnings)
        window = engine.rootObjects()[0]
        town.demo()
        self.assertEqual(app.pages_of(window), ["town", "days"])
        for page in app.pages_of(window):
            window.setProperty("page", page)
            qt.processEvents()
        # The same calls the buttons make, made the way the pages make them.
        for call in ("town.refresh()", "town.dismiss()", "town.runAgain('no-such-day')", "town.stop()",
                     "town.now.states['rohit']", "town.machine.model.name", "town.families[0].people[0].reads"):
            said = QQmlExpression(engine.rootContext(), window, call)
            said.evaluate()
            self.assertFalse(said.hasError(), f"{call}: {said.error().toString()}")
        qt.processEvents()
        self.assertEqual(warnings, [])
        self.assertEqual(town.now["states"]["rohit"], "DONE")
        del engine


if __name__ == "__main__":
    unittest.main()
