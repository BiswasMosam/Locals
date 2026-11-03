"""The feed: what each local reports, printed live, saved for replay and sent to the dashboard."""
import json
import time

TONES = {"STUCK": "\033[33m", "SLIP": "\033[33m", "OFF PATH": "\033[33m", "TAKE": "\033[36m", "EXPERT": "\033[36m", "WRONG DONE": "\033[33m", "GAVE UP": "\033[33m", "ASKED": "\033[33m",
         "ERROR": "\033[31m", "DONE": "\033[32m"}
DIM, BOLD, RESET = "\033[90m", "\033[1m", "\033[0m"


class Feed:
    def __init__(self, out, local, task, listen=None):
        self.local, self.task = local, task
        self.listen = listen or (lambda entry: None)
        self.file = (out / "feed.jsonl").open("a", encoding="utf-8")
        self.steps = (out / "steps.jsonl").open("a", encoding="utf-8")
        self.start = time.time()
        self.shot = None  # the screenshot of the screen the local is looking at right now
        print(f"\n{BOLD}{local.tag}{RESET}  {local.job} · {local.limits.device} · {task.app}: {task.id}")

    def clock(self):
        return f"{int(time.time() - self.start)}s"

    def _send(self, entry):
        self.file.write(json.dumps(entry) + "\n")
        self.file.flush()
        self.listen(entry)

    def event(self, kind, says):
        print(f"  {TONES.get(kind, '')}{kind:<11}{RESET}{says}")
        self._send({"type": "event", "local": self.local.id, "kind": kind, "says": says,
                    "at": self.clock(), "shot": self.shot})

    def step(self, n, line, thought, record, secs):
        print(f"  {DIM}{n:>2}  {line:<34} {thought}{RESET}")
        record["secs"] = secs
        self.steps.write(json.dumps(record) + "\n")
        self.steps.flush()
        self._send({"type": "step", "local": self.local.id, "step": n, "line": line, "thought": thought,
                    "at": self.clock(), "secs": secs, "shot": self.shot})

    def close(self):
        self.file.close()
        self.steps.close()
