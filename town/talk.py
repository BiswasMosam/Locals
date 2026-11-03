"""A talk as a room takes it in: slides from a PDF or PowerPoint, words from a script or a recording, cut into parts.

Code reads the files and measures them (how long each part runs, how fast the words come, how much is on each
slide, how small its text is, the pauses and fillers in a recording); no number here is a model's opinion.
Every number and its source: study/rooms.md.
"""
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

PACE = 150          # words a minute: the usual pace of English speech, used when there is no recording to time
SLIDE_SECONDS = 60  # how long a slide is up when nothing else says
PAUSE = 2.0         # seconds of silence a listener notices as a pause
SLIDE_HEIGHT = 540  # points: text sizes are given as if on a standard slide 7.5 inches tall
SMALL_TEXT = 24     # points: the usual floor for text read from the back of a room (study/rooms.md)
AUDIO = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".aac", ".mp4"}
SCRIPT = {".txt", ".md"}
DECK = {".pdf", ".pptx"}
# [slide 3], Slide 3:, part 3 on a line of its own; or a line of three dashes between parts.
MARK = re.compile(r"^[ \t]*\[?[ \t]*(?:slide|part)[ \t]*(\d+)[ \t]*\]?[ \t]*[:.)]?[ \t]*$|^[ \t]*-{3,}[ \t]*$", re.I | re.M)
# The fillers the AAC&U rubric names ("um", "uh", "like", "you know"); "like" only when set off by commas.
FILLER = re.compile(r"\b(?:u+m+|u+h+m*|e+r+m+|hmm+)\b|\byou know\b|,\s*like\s*,", re.I)
# Whisper tidies fillers away unless its prompt already has some (a known trick); recordings still undercount them.
KEEP_FILLERS = "Umm, let me think, like, hmm... Okay, here's what I'm, like, thinking. Uh, so, you know."


@dataclass
class Part:
    id: str
    title: str
    shown: list = field(default_factory=list)   # the lines on the slide, when there is a slide
    said: str = ""                              # what is said while this part is up
    seconds: float = 0.0
    start: float = 0.0
    timed: bool = False                         # the seconds come from a recording, not an estimate
    fonts: list = field(default_factory=list)   # text sizes on the slide, in points on a standard slide
    pictures: int = 0                           # pictures, charts and tables on the slide
    pauses: list = field(default_factory=list)  # silences of PAUSE seconds or more, from a recording
    slide: bool = False

    @property
    def words(self):
        return len(self.said.split())

    @property
    def slide_words(self):
        return sum(len(l.split()) for l in [self.title, *self.shown]) if self.slide else 0

    @property
    def wpm(self):
        return self.words / (self.seconds / 60) if self.said and self.seconds else 0.0

    @property
    def fillers(self):
        return len(FILLER.findall(self.said))

    @property
    def text(self):
        return "\n".join(x for x in [self.title, *self.shown, self.said] if x)


@dataclass
class Talk:
    source: str
    parts: list
    recorded: bool = False
    deck: bool = False
    speech: bool = False
    notes: list = field(default_factory=list)  # what had to be assumed, said to the user

    @property
    def seconds(self):
        return sum(p.seconds for p in self.parts)

    @property
    def kind(self):
        return " and ".join(k for k, on in (("slides", self.deck), ("a recording" if self.recorded else "a script", self.speech)) if on)


# ---------- Reading the files ----------

def read_pdf(path):
    from pypdf import PdfReader
    parts = []
    for n, page in enumerate(PdfReader(path).pages, 1):
        height = float(page.mediabox.height) or SLIDE_HEIGHT
        sizes = []

        def visit(text, cm, tm, font, size):
            if text.strip() and size:
                scale = (math.hypot(tm[2], tm[3]) or 1) * (math.hypot(cm[2], cm[3]) or 1)
                sizes.append(round(size * scale * SLIDE_HEIGHT / height, 1))

        lines = [" ".join(l.split()) for l in (page.extract_text(visitor_text=visit) or "").splitlines() if l.strip()]
        try:
            pictures = len(page.images)
        except Exception:  # an image pypdf cannot decode is still an image on the slide, but we cannot count it
            pictures = 0
        parts.append(Part(id=f"P{n}", title=lines[0] if lines else f"Slide {n}", shown=lines[1:], fonts=sizes,
                          pictures=pictures, slide=True))
    return parts


def _shapes(shapes):
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    for s in shapes:
        if s.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _shapes(s.shapes)
        else:
            yield s


def read_pptx(path):
    """Slides with their speaker notes; the notes are what the speaker says, when the deck has them."""
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    deck = Presentation(path)
    inches = (deck.slide_height or 6858000) / 914400
    parts = []
    for n, slide in enumerate(deck.slides, 1):
        title_shape = slide.shapes.title
        title, lines, sizes, pictures = "", [], [], 0
        for shape in _shapes(slide.shapes):
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE or getattr(shape, "has_chart", False) or getattr(shape, "has_table", False):
                pictures += 1
            if getattr(shape, "has_table", False):
                lines += [" | ".join(c.text.strip() for c in row.cells) for row in shape.table.rows]
            if not shape.has_text_frame:
                continue
            for p in shape.text_frame.paragraphs:
                text = " ".join("".join(r.text for r in p.runs).split())
                sizes += [round(r.font.size.pt * 7.5 / inches, 1) for r in p.runs if r.font.size and r.text.strip()]
                if not text:
                    continue
                if title_shape is not None and shape.shape_id == title_shape.shape_id and not title:
                    title = text
                else:
                    lines.append(text)
        notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            notes = " ".join(slide.notes_slide.notes_text_frame.text.split())
        if not title and lines:
            title = lines.pop(0)
        parts.append(Part(id=f"P{n}", title=title or f"Slide {n}", shown=lines, said=notes, fonts=sizes,
                          pictures=pictures, slide=True))
    return parts


def read_script(path):
    """A script cut where it says which slide or part comes next, else into paragraphs about a minute long.
    Returns (pieces, numbered): numbered is True when the script named its slides."""
    text = path.read_text(encoding="utf-8", errors="replace")
    marks = list(MARK.finditer(text))
    if marks:
        pieces, numbered = [], any(m.group(1) for m in marks)
        lead = text[:marks[0].start()].strip()
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = " ".join(text[m.end():end].split())
            pieces.append((int(m.group(1)) if m.group(1) else len(pieces) + 1, body))
        if lead and numbered:  # words before the first [slide 1] belong with it
            pieces[0] = (pieces[0][0], f"{' '.join(lead.split())} {pieces[0][1]}".strip())
        elif lead:  # with --- between parts, what comes before the first is a part of its own
            pieces = [(n + 1, text) for n, (_, text) in enumerate([(0, " ".join(lead.split())), *pieces])]
        return [p for p in pieces if p[1]], numbered
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces, current = [], []
    for p in paragraphs:
        current.append(p)
        if sum(len(c.split()) for c in current) >= PACE:
            pieces.append(" ".join(current))
            current = []
    if current:
        pieces.append(" ".join(current))
    return list(enumerate(pieces, 1)), False


def decode(path):
    """A recording as 16 kHz mono samples. Done here, not by faster-whisper, whose own decoder breaks on newer PyAV."""
    import av
    import numpy as np
    chunks = []
    with av.open(str(path)) as container:
        resample = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in container.decode(audio=0):
            chunks += [f.to_ndarray().reshape(-1) for f in resample.resample(frame)]
        chunks += [f.to_ndarray().reshape(-1) for f in resample.resample(None)]
    return (np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16)).astype(np.float32) / 32768.0


def transcribe(path):
    """What was said in a recording, phrase by phrase with times: [(start, end, text)]."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("Reading a recording needs faster-whisper: .venv/Scripts/pip install faster-whisper")
    model = WhisperModel(os.environ.get("LOCALS_WHISPER", "small"), device=os.environ.get("LOCALS_WHISPER_DEVICE", "cpu"),
                         compute_type="int8")
    segments, _ = model.transcribe(decode(path), word_timestamps=True, initial_prompt=KEEP_FILLERS, vad_filter=False)
    phrases = []
    for s in segments:
        words = [(w.start, w.end, w.word) for w in (s.words or [])]
        phrases.append({"start": s.start, "end": s.end, "text": " ".join(s.text.split()),
                        "gaps": [(a[1], b[0]) for a, b in zip(words, words[1:]) if b[0] - a[1] >= PAUSE]})
    return phrases


# ---------- Putting slides and speech together ----------

def tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 4 or t.isdigit()}


def align(units, slides):
    """Which slide each piece of speech goes with: in order, preferring the slide whose words it shares, and
    otherwise spread evenly. units are texts; returns a slide index for each."""
    m, n = len(units), len(slides)
    if not m or not n:
        return []
    words = [tokens(s.text) for s in slides]
    score = [[len(tokens(u) & words[j]) - 2.0 * abs((i + 0.5) / m - (j + 0.5) / n) for j in range(n)] for i, u in enumerate(units)]
    best, back = [score[0][:]], []
    for i in range(1, m):
        row, came = [], []
        run, arg = -1e9, 0
        for j in range(n):  # stay on a slide or move forward, never back
            if best[-1][j] > run:
                run, arg = best[-1][j], j
            row.append(score[i][j] + run)
            came.append(arg)
        best.append(row)
        back.append(came)
    j = max(range(n), key=lambda k: best[-1][k])
    path = [j]
    for came in reversed(back):
        j = came[j]
        path.append(j)
    return path[::-1]


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def load(files, minutes=None):
    """A talk from one or two files: a deck (PDF or PowerPoint), a speech (a script or a recording), or both."""
    paths = [Path(f) for f in files]
    for p in paths:
        if not p.exists():
            raise SystemExit(f"No file at {p}")
    decks = [p for p in paths if p.suffix.lower() in DECK]
    speeches = [p for p in paths if p.suffix.lower() in AUDIO | SCRIPT]
    other = [p for p in paths if p not in decks and p not in speeches]
    if other or len(decks) > 1 or len(speeches) > 1 or not paths:
        raise SystemExit("Give a deck (.pdf or .pptx), a speech (.txt, .md or a recording like .mp3, .wav or .m4a), or one of each.")
    notes = []
    slides = (read_pdf if decks[0].suffix.lower() == ".pdf" else read_pptx)(decks[0]) if decks else []
    recorded = bool(speeches) and speeches[0].suffix.lower() in AUDIO
    talk = Talk(source=" + ".join(p.name for p in paths), parts=slides, recorded=recorded, deck=bool(slides),
                speech=bool(speeches) or any(s.said for s in slides), notes=notes)
    if not speeches:
        if slides and not any(s.said for s in slides):
            notes.append("Nothing said is known, so the room only has the slides: give a script or a recording to hear the talk.")
        elif slides:
            notes.append("What is said comes from the speaker notes.")
    elif recorded:
        phrases = transcribe(speeches[0])
        if not phrases:
            raise SystemExit(f"Nothing could be heard in {speeches[0].name}.")
        if slides:
            if any(s.said for s in slides):
                notes.append("The recording is what was said; the speaker notes are left out.")
            for s in slides:
                s.said = ""
            where = align([p["text"] for p in phrases], slides)
            notes.append("Which slide each sentence was said on is worked out from the words they share, in order.")
        else:
            where, slides = [], []
            for p in phrases:  # parts about a minute long, cut between phrases
                if not slides or p["start"] - slides[-1][0]["start"] >= 50:
                    slides.append([])
                slides[-1].append(p)
            where = [i for i, group in enumerate(slides) for _ in group]
            slides = [Part(id=f"P{i + 1}", title=sentences(group[0]["text"])[0][:80]) for i, group in enumerate(slides)]
        for p, j in zip(phrases, where):
            s = slides[j]
            s.said = f"{s.said} {p['text']}".strip()
            s.pauses += [round(b - a, 1) for a, b in p["gaps"]]
        first = {}
        for p, j in zip(phrases, where):
            first.setdefault(j, p["start"])
        end, spoken = phrases[-1]["end"], sorted(first)
        for j, s in enumerate(slides):  # a slide is up from its first words until the next slide's first words
            later = [first[k] for k in spoken if k > j]
            s.timed = True
            s.start = round(first.get(j, later[0] if later else end), 1)
            s.seconds = round((later[0] if later else end) - first[j], 1) if j in first else 0.0
        for i in range(1, len(phrases)):  # silences between phrases are pauses too
            gap = phrases[i]["start"] - phrases[i - 1]["end"]
            if gap >= PAUSE:
                slides[where[i]].pauses.append(round(gap, 1))
        talk.parts = slides
    else:
        pieces, numbered = read_script(speeches[0])
        if not pieces:
            raise SystemExit(f"{speeches[0].name} is empty.")
        if slides:
            if any(s.said for s in slides):
                notes.append("The script is what is said; the speaker notes are left out.")
            for s in slides:
                s.said = ""
            if numbered:
                for n, text in pieces:
                    s = slides[min(max(n, 1), len(slides)) - 1]
                    s.said = f"{s.said} {text}".strip()
            else:
                units = [u for _, text in pieces for u in sentences(text)]
                for u, j in zip(units, align(units, slides)):
                    slides[j].said = f"{slides[j].said} {u}".strip()
                notes.append("Which slide each sentence goes with is worked out from the words they share, in order; "
                             "mark them with [slide 2] lines in the script to place them yourself.")
        else:
            slides = [Part(id=f"P{i}", title=sentences(text)[0][:80], said=text) for i, (_, text) in enumerate(pieces, 1)]
        talk.parts = slides
    if not recorded:
        for s in talk.parts:
            s.seconds = round(max(10.0, s.words / PACE * 60), 1) if s.said else SLIDE_SECONDS
        if minutes:
            k = minutes * 60 / talk.seconds
            for s in talk.parts:
                s.seconds = round(s.seconds * k, 1)
            if talk.speech:
                notes.append(f"Timed to the {minutes:g} minutes you gave, about {round(sum(p.words for p in talk.parts) / minutes)} words a minute.")
        elif talk.speech:
            notes.append(f"Timed at {PACE} words a minute, the usual pace of speech; a recording would time it.")
        else:
            notes.append(f"Each slide is up for {SLIDE_SECONDS} seconds; give --minutes for how long the talk runs.")
        clock = 0.0
        for s in talk.parts:
            s.start, clock = clock, clock + s.seconds
    return talk


# ---------- Measuring it ----------

def clock(seconds):
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def measure(talk, limit_minutes=None):
    """Facts about the talk that code can count, for listeners and graders to point at. [(id, text)]"""
    facts = []
    secs = talk.seconds
    how = "from the recording" if talk.recorded else "estimated"
    line = f"The talk runs {clock(secs)} ({how})"
    if limit_minutes:
        over = secs - limit_minutes * 60
        line += f", against a limit of {limit_minutes} minutes: " + (f"{clock(over)} over" if over > 30 else f"{clock(-over)} to spare" if over < -30 else "on time")
    facts.append(line)
    spoken = [p for p in talk.parts if p.said]
    if talk.recorded and spoken:
        words = sum(p.words for p in spoken)
        pace = words / (sum(p.seconds for p in spoken) / 60)
        fastest = max(spoken, key=lambda p: p.wpm)
        facts.append(f"Pace: {round(pace)} words a minute on average; fastest {fastest.id} at {round(fastest.wpm)}")
        fillers = sum(p.fillers for p in talk.parts)
        facts.append(f"Fillers heard (um, uh, like, you know): {fillers}, {fillers / (secs / 60):.1f} a minute (a recording undercounts them)")
        pauses = [(x, p.id) for p in talk.parts for x in p.pauses]
        if pauses:
            longest = max(pauses)
            facts.append(f"Pauses of {PAUSE:.0f} seconds or more: {len(pauses)}; longest {longest[0]} s in {longest[1]}")
        else:
            facts.append(f"No pause of {PAUSE:.0f} seconds or more")
    if talk.deck:
        slides = [p for p in talk.parts if p.slide]
        busiest = max(slides, key=lambda p: p.slide_words)
        facts.append(f"Slides: {len(slides)}; words on the busiest slide: {busiest.slide_words} ({busiest.id}); "
                     f"{round(sum(p.slide_words for p in slides) / len(slides))} on average")
        sized = [(min(p.fonts), p.id) for p in slides if p.fonts]
        if sized:
            small = [p.id for p in slides if p.fonts and min(p.fonts) < SMALL_TEXT]
            smallest = min(sized)
            facts.append(f"Smallest text: {smallest[0]:g} pt in {smallest[1]} (on a standard slide); "
                         + (f"{len(small)} slide{'s have' if len(small) > 1 else ' has'} text under {SMALL_TEXT} pt" if small else f"none under {SMALL_TEXT} pt"))
        bare = [p.id for p in slides if not p.pictures]
        facts.append(f"Slides with no picture, chart or table: {len(bare)} of {len(slides)}" + (f" ({', '.join(bare[:8])}{'…' if len(bare) > 8 else ''})" if bare else ""))
    return [(f"M{i}", t) for i, t in enumerate(facts, 1)]
