"""The feed: what each local reports, printed live and saved for replay."""
import json
import time

TONES = {"STUCK": "\033[33m", "SLIP": "\033[33m", "WRONG DONE": "\033[33m", "GAVE UP": "\033[33m", "ASKED": "\033[33m",
         "DONE": "\033[32m"}
DIM, BOLD, RESET = "\033[90m", "\033[1m", "\033[0m"


class Feed:
    def __init__(self, out, local, task):
        self.local, self.task = local, task
        self.file = (out / "feed.jsonl").open("a", encoding="utf-8")
        self.steps = (out / "steps.jsonl").open("a", encoding="utf-8")
        self.start = time.time()
        print(f"\n{BOLD}{local.tag}{RESET}  {local.job} · {local.limits.device} · {task.app}: {task.id}")

    def clock(self):
        return f"{int(time.time() - self.start)}s"

    def event(self, kind, says):
        print(f"  {TONES.get(kind, '')}{kind:<11}{RESET}{says}")
        self.file.write(json.dumps({"local": self.local.id, "task": f"{self.task.app}:{self.task.id}",
                                    "kind": kind, "says": says, "at": self.clock()}) + "\n")
        self.file.flush()

    def step(self, n, line, thought, record):
        print(f"  {DIM}{n:>2}  {line:<34} {thought}{RESET}")
        self.steps.write(json.dumps(record) + "\n")
        self.steps.flush()

    def close(self):
        self.file.close()
        self.steps.close()
