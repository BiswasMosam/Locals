<p align="center">
  <img src="brand/banner.svg" alt="A building at night whose lit windows spell Locals" width="100%">
</p>

<p align="center">
  <b>Locals</b> is a small town of AI users that lives on your own machine.<br>
  Each local has a job, a workday and a reason to open your app.<br>
  They use it the way real people would, get stuck where real people would,<br>
  and tell you where it happened and what they did instead.
</p>

<p align="center">
  <a href="#run-it"><img alt="Runs locally" src="https://img.shields.io/badge/runs-locally-ffc94d?style=flat-square&labelColor=0c0e13"></a>
  <a href="study/README.md"><img alt="Study first" src="https://img.shields.io/badge/study-first-ffc94d?style=flat-square&labelColor=0c0e13"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-8a8f9c?style=flat-square&labelColor=0c0e13"></a>
</p>

<br>

## The town

<p align="center">
  <img src="brand/dashboard-town.png" alt="The Locals dashboard during a real day. Pixel art town at night: Sunil stands at the Chinese stall with a thinking bubble and his phone lit, Kavita waits at the court, Neha at the law firm. The feed on the right shows his first step." width="100%">
</p>

A hundred and fourteen locals live here: cooks, shop owners, lawyers, photographers, engineers, nurses, teachers, students and more. One at a time they try your website or Android app, thinking out loud, while the feed on the right shows every step and the exact screen they saw.

## A real run

Rohit is a junior advocate in a court corridor with an old phone. He reads the first six words of anything. His task: make a photo smaller in [PixelShift](https://github.com/BiswasMosam/PixelShift).

```
   1  tap "IMAGE CONVERTER"        Need to upload photo.png first.
   2  tap "JPG Small"              Change to JPG / Small to reduce size
   3  tap "QUALITY"                Lower quality to make file smaller
   4  tap "QUALITY"                Lower quality to shrink file size, so it fits
   5  tap "QUALITY"                Lower the quality to shrink the file size
  STUCK   Kept landing on the same screen; nothing they tried changed it.
   6  set "QUALITY" to 20          Lower quality to reduce file size
   7  set "QUALITY" again          Lower quality to reduce file size. Try 10%.
   8  tap "Convert and download"   Try converting after lowering quality.
  DONE    photo.jpg, 0.7 MB · 8 steps · 45 seconds
```

Locals report **what they did, not what they wish for**. Where they got stuck and what they did instead is your feature request.

## What it has noticed so far

- **Pops:** shop owners opened the Book tab to add a customer, reading it as booking a visit.
- **Biswas Fabricators site:** people who wanted to call gave up; the call buttons scroll the page or show a pop up instead of opening the dialler.
- **Fill.ai:** a student never found it; nothing on the page says it is there.
- **PixelShift:** on Ganesh Chaturthi a rushed cook hit BMP instead of JPG, the button next to it, twice, and gave up.

Signals to check with real users, not verdicts.

## A year in the town

<p align="center">
  <img src="brand/dashboard-monsoon.png" alt="A real day in the dashboard: Wednesday 1 July 2026, heavy rain falling over the pixel city. The feed shows Sunil's day: wet hands and drops on the screen, roads flooded, trains stopped." width="100%">
</p>

Pick any date and the day changes things: festivals, exams, tax deadlines, monsoon rain, even a lockdown. Festivals change the city, never a person's faith.

## Give a talk

Give the town your slides, script or recording, pick a room (a class, an interview, a boardroom, a pitch, a crowd) and see who stays with you. The same talk told as engineers tell it:

```
  SUNIL      ▅▄▃▂▂▂zz   asleep: not what they came for
  PRAKASH    ▅▅▄▄▄▃▃▃   phone out: too technical
  ROHIT      ▅▄▃▂▂▁zz   asleep: not what they came for
  ISHAAN     ▅▅▆▆▆▆▆▇   never drifted
```

Told again with a story and a demonstration, nobody drifted and all eight remembered the point. Then the room marks you, like a professor or an interview panel would.

## When it works

<p align="center">
  <img src="brand/dashboard-celebration.png" alt="End of a real day: a band reads PIXELSHIFT IS GREAT, 3 of 3 locals got it done, 100%. Fireworks burst over the skyline and confetti falls while three locals with green ticks stand outside their workplaces." width="100%">
</p>

When nine in ten get it done, the town celebrates your app by name.

## Why trust it

An AI left alone is far too patient and too accurate to stand in for a person. So code, not the AI, makes each local human, with limits from studies of real people: typos, missed taps, how much they read, age, walking. Every local is drawn from a [study](study/README.md) of their job and stays a draft until someone in that job checks it. How close they get to real people, and where they fall short, is in the [validity study](study/validity.md).

## Run it

Runs on one laptop (built on an RTX 4060 with 8 GB), free and private: your app's data never leaves your machine. You need Python 3.11+, Google Chrome and [Ollama](https://ollama.com); Android apps also need the Android emulator.

```bash
git clone https://github.com/BiswasMosam/Locals
cd Locals
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # macOS or Linux: .venv/bin/pip
ollama pull qwen3:4b-instruct

python -m town dashboard
```

Everything else: `python -m town --help`.

## Leave a review

- **Do one of these jobs?** [Correct a profile](../../issues/new?template=correct-a-profile.yml) and tell us what your day really looks like.
- **Thinking of using it?** [Leave a review](../../issues/new?template=review.yml).

<br>

<p align="center">
  Made by <a href="https://mosambiswas.com">Mosam Biswas</a> · <a href="LICENSE">MIT</a>
</p>
