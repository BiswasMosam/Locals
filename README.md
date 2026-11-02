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
  <a href="#roadmap"><img alt="Status: day 1" src="https://img.shields.io/badge/status-day%201-ffc94d?style=flat-square&labelColor=0c0e13"></a>
  <a href="#why-it-runs-locally"><img alt="Runs locally" src="https://img.shields.io/badge/runs-locally-ffc94d?style=flat-square&labelColor=0c0e13"></a>
  <a href="study/README.md"><img alt="Study first" src="https://img.shields.io/badge/study-first-ffc94d?style=flat-square&labelColor=0c0e13"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-8a8f9c?style=flat-square&labelColor=0c0e13"></a>
</p>

> **Day 1.** Fifty seven draft locals live in the town and use web apps in a real browser, thinking with a small model on this laptop, and a dashboard shows them at work. They are built from the [study](study/README.md) of the people they stand for, and stay marked draft until real people in those jobs confirm their profiles. [Run them](#run-it), or [help get a profile right](#leave-a-review).

<br>

## The town

<p align="center">
  <img src="brand/dashboard-town.png" alt="The Locals dashboard during a real day. Pixel art town at night: Sunil stands at the Chinese stall with a thinking bubble and his phone lit, Kavita waits at the court, Neha at the law firm. The feed on the right shows his first step." width="100%">
</p>

This is the dashboard during a real day, not a mock up. Three quarters of the screen is the city: a skyline behind one long street of shops, a court, a law firm, offices, an IT park, a studio, a hospital, a school, a factory and a building site, with autos and buses going past. Each local walks out of their flat (their window dims as they leave) to their workplace and waits their turn. The one at work holds a lit phone and thinks in a bubble; a stuck local gets a blinking `!`; everyone ends the day with a mark for how it went. The view follows whoever is working; drag or scroll to look around. The bar along the bottom shows what the working local is doing right now.

The last quarter is the feed: every step and every thought, with STUCK, SLIP, DONE and GAVE UP called out. Click any line and you see the exact screen the local was looking at, then step through their run with PREV and NEXT. Click a local in the town to follow just them. Past days are kept and can be opened again.

## When it works

<p align="center">
  <img src="brand/dashboard-celebration.png" alt="End of a real day: a band reads PIXELSHIFT IS GREAT, 3 of 3 locals got it done, 100%. Fireworks burst over the skyline and confetti falls while three locals with green ticks stand outside their workplaces." width="100%">
</p>

At the end of every day the town gives a verdict. When at least three locals went out and 90% or more got the job done, the city celebrates your app by name with fireworks and confetti, and the locals jump. Anything less gets a plain count and a pointer to where people got stuck.

## A year in the town

<p align="center">
  <img src="brand/dashboard-monsoon.png" alt="A real day in the dashboard: Wednesday 1 July 2026, heavy rain falling over the pixel city. The feed shows Sunil's day: wet hands and drops on the screen, roads flooded, trains stopped." width="100%">
</p>

The same app meets a different person on a different day. Pick any day of the year in setup, or **a year in twelve days**, and the date decides what each local's day is like: weekdays and Sundays, the 24 public holidays of the year, festival seasons (Ramzan, Holi, Ganeshotsav, Navratri, Diwali, Christmas and New Year), court vacations, the end of the financial year, the monsoon with rain fixed by the date, and an optional pandemic in lockdown or reopening.

Each local gets a "Today" in their situation, and code changes their limits: Diwali week rushes the fabricator, a red alert downpour wets everyone's screen, a lockdown sends everyone home on a slow network. The town shows it too, with rain, festival lights, lanterns, a crescent moon in Ramzan, and an empty masked street in a lockdown. Festivals change the city, never a person's faith: no local's name decides what they observe.

It already found something. On Ganesh Chaturthi, Sunil, rushed by the crowd from the pandal next door, aimed for **JPG** in PixelShift twice and hit **BMP**, its neighbour on a phone, both times, and gave up. On an ordinary day he finishes in three steps. The calendar, its sources and every effect are in the [year study](study/year.md).

## A real run

Rohit is a junior advocate standing in a court corridor with files under one arm and an old phone in the other hand. He reads the first six words of anything. His task: turn a large photo into a smaller JPG in [PixelShift](https://github.com/BiswasMosam/PixelShift). This is his actual run on the live site, with his longer thoughts shortened:

```
10 ROHIT  Junior advocate · phone · PixelShift: small-jpg
   1  tap [4] "IMAGE CONVERTER 10 IN"    Need to upload photo.png first.
   2  tap [7] "JPG Small"                Change to JPG / Small to reduce size
   3  tap [12] "QUALITY"                 Lower quality to make file smaller
   4  tap [12] "QUALITY"                 Lower quality to shrink file size, so it fits
   5  tap [12] "QUALITY"                 Lower the quality to shrink the file size
  STUCK      Kept landing on the same screen; nothing they tried changed it.
   6  set [12] "QUALITY" = 20            Lower quality to reduce file size
   7  set [12] "QUALITY" =               Lower quality to reduce file size. Try 10%.
   8  tap [13] "Convert and download"    Try converting after lowering quality.
  DONE       photo.jpg, 0.7 MB · 8 steps · 45s · after being stuck
```

He tapped the quality slider three times expecting it to go down before finding another way. Sunil, a food stall cook who glances at three words at a time, did the same task in four steps. Every step is saved with a screenshot for replay.

## What a local tells you

Locals reports **behaviour, not wishlists**. Ask an AI what features it wants and you get a confident list of generic ideas. Watch it try to do a job and you get something better:

| | Example |
|---|---|
| **Stuck** | "Customer paid the advance. The new order form has no box for it." |
| **Workaround** | "Wrote the advance in Notes instead." |
| **Done** | "Three orders in 1:52. Every total right." |

When a local cannot do something and does something else instead, that workaround is the feature request.

## Why it runs locally

- **Free per run.** A local can come back on simulated day 3 and day 20, the way real people do. That many steps would cost real money on a cloud API; here it costs electricity.
- **Your data stays home.** Apps with real customers and real orders never leave your machine.
- **Repeatable.** Fixed model weights and settings mean the same run gives the same result, so when a number changes you know it was your fix.

## Fits your machine

<p align="center">
  <img src="brand/dashboard-setup.png" alt="The setup screen. Job types with tick boxes and counts on the left; meters for GPU memory, memory and time read from this machine on the right." width="100%">
</p>

Not everyone has a big GPU. Before a day you tick the jobs you want in town and set how many of each, and Locals reads your machine to show what it will spend: GPU memory (from your graphics card and the model in Ollama), memory, and time (from how fast earlier days ran on this machine).

All locals share one model and take turns, so **more locals cost more time, not more GPU memory**. A smaller machine still runs the whole town; it just takes longer. No NVIDIA card at all? The model runs on the processor, slower, and the meter says so.

## Test your own app

Pick **A SITE** in setup and paste an address: your live site, or the one on your machine while you build it (`http://localhost:5173` works, because the locals run on the same machine). Say in plain words what they should try to do, and how Locals can tell it worked: the page shows some text, the address changes, a file gets saved, or take their word for it, which is marked as unchecked rather than done. If the task needs something to upload, drop the files in and every local finds them on their phone.

For an Android app, pick **ANDROID APP** and drop the APK. Locals use it on an Android emulator, or a phone plugged in with USB debugging, and each one gets a fresh install. They read the screen through Android's accessibility tree, the same one screen readers use, so it works for Flutter apps without changing them. A button with no label still shows its symbol to a sighted person, so a small vision model (`qwen2.5vl:3b`) looks at it and names it: "a plus, round, bottom right".

The first Android runs were on [Pops](https://github.com/BiswasMosam/Pops), unchanged. Asked to add a new customer, the fabrication owners opened the **Book** tab first, again and again: they read it as booking a visit, while in Pops it is the ledger of finished jobs. The ones who found the plus then met an empty address book with societies, buildings and flats to create before any customer can be added. Both are questions for the real shop owner, which is exactly what a run is for.

## How it works

| Part | What it does |
|---|---|
| **The town** | A workday hands each local tasks with real pressure: a call in the middle of a form, a dropped connection, a killed app. |
| **The locals** | One model, many people. A local is a profile from the study turned into a prompt plus a set of limits. |
| **Eyes** | Locals see what a person sees: visible controls by their visible words, a big card line by line, the placeholder in an empty box, and the symbol on a button with no words. On the web this comes from a real Chrome on a phone sized or laptop sized screen; on Android from the accessibility tree of an emulator or phone. |
| **Limits** | Code, not the prompt, makes a local human: a patience budget, a reading budget, a slip rate, rules for giving up. Research shows a prompt alone leaves AI users far too patient and accurate. |
| **The golden path** | You do each task once while it is recorded. Wherever a local leaves your path, the UI misled it. |
| **Proof** | A task counts as done only when the app's real state says so, never on the local's word. |

## The study

AI users have a known problem: they are too good. Studies find them more cooperative, more accurate and more patient than real people, and a persona written as "you are a 50 year old shop owner" mostly makes their answers sound believable, not more true. People built from real interviews do far better.

So every local starts as a profile of a real job, built from interviews and published data, with every claim tagged by where it came from. [Read the method and the research behind it](study/README.md).

| Job | App it tests | Profile |
|---|---|---|
| Fabrication shop owner | Pops | [Draft](study/profiles/fabricator.md) |
| Food stall counter | Order Control | [Draft](study/profiles/food-stall.md) |
| Fresh graduate, photographer, collector, recruiter | Fill.ai, PixelShift, Peghunt, portfolio | Planned |
| [Law](study/profiles/law/README.md): trial court advocate, junior advocate, firm associate, in-house counsel | The wider town | Drafts |
| [Media](study/profiles/media/README.md): wedding photographer, product photographer, videographer, video editor, social media manager | PixelShift and the wider town | Drafts |
| [Engineering](study/profiles/engineering/README.md): software (product and services), mechanical (plant and design), civil (site and planning), electrical, embedded | The wider town | Drafts |
| Finance, health, education | The wider town | Planned |

## Run it

You need Python 3.11 or newer, Google Chrome and [Ollama](https://ollama.com). For Android apps, also the Android SDK with an emulator, and `ollama pull qwen2.5vl:3b` for reading icons.

```bash
git clone https://github.com/BiswasMosam/Locals
cd Locals
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # on macOS or Linux: .venv/bin/pip
ollama pull qwen3:4b-instruct

python -m town dashboard                                 # the town in your browser
python -m town people                                    # everyone who lives in the town
python -m town run pixelshift:small-jpg rohit sunil      # send two locals to a task
python -m town run pixelshift:small-jpg all --watch      # everyone, with the browser visible
python -m town run pixelshift:small-jpg sunil --date 2026-09-14   # Ganesh Chaturthi
python -m town run pixelshift:small-jpg rohit --year 2026        # a year in twelve days
python -m town run pops:new-order prakash nikhil                  # an Android app, on a running emulator
```

Each run lands in `runs/` with the feed, every step the local took, and a screenshot of each screen. Locals live in [people/](people), one file each; tasks live in [tasks/](tasks), one file per app. Set `LOCALS_MODEL` to try another model.

## Roadmap

- [x] Name, method and profile template
- [x] First two profiles drafted from a real business
- [x] Law family: four types of lawyer drafted
- [x] Eighteen draft locals that use web apps in a real browser
- [x] Dashboard: the town, the live feed, replay, setup with machine meters, your own sites
- [x] A whole city, and a celebration when 90% get it done
- [x] A simulated year: weekdays and weekends, monsoon, festivals across religions, a pandemic
- [x] Media family: photographers, videographers, video editors, social media teams (fifteen more locals, a banquet hall)
- [x] Engineering family: eight types, twenty four more locals
- [x] Locals on Android: drop an APK, first runs on Pops on the emulator
- [ ] Interviews with a real fabricator and a real food stall
- [ ] Limits set from watching real people do the same tasks
- [ ] Setup screen with the resource estimate
- [ ] The town view
- [ ] Profiles for the wider town

## Leave a review

Locals is built in the open and gets better when people who do these jobs tell us where we are wrong.

- **You do one of these jobs?** [Correct a profile](../../issues/new?template=correct-a-profile.yml). Tell us what your day really looks like.
- **Thinking of using it?** [Leave a review](../../issues/new?template=review.yml): what app you would test, what machine you have, what is missing.

## Built for

One laptop: an RTX 4060 with 8 GB, [Ollama](https://ollama.com), and small models such as `qwen3:4b-instruct`. Long runs go overnight.

<br>

<p align="center">
  Made by <a href="https://mosambiswas.com">Mosam Biswas</a> · <a href="LICENSE">MIT</a>
</p>
