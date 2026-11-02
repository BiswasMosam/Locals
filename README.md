# Locals

**People who live with your app.**

Locals is a small town of AI users that runs on your own machine. Each local has a job (shop owner, engineer, lawyer, fabricator), a workday, and a reason to open your app. They use it the way real people would, get stuck where real people would, and at the end of the day you get a report of where it happened and why.

## Why it runs locally

- **Free per run.** A local can come back to your app on simulated day 3 and day 20, the way real people do. That many steps would cost real money on a cloud API; here it costs electricity.
- **Your data stays home.** Apps with real customers and real orders never leave the machine.
- **Repeatable.** Fixed model weights and settings mean the same run gives the same result, so when a number changes you know it was your fix.

## How it works (the plan)

| Part | What it does |
|---|---|
| **The town** | A workday hands each local tasks with real pressure and interruptions: a call mid form, a dropped connection, a killed app. |
| **The locals** | One model, many people. A local is a prompt: job, tech comfort, patience, device, language. |
| **Eyes** | Locals read the app's accessibility tree, not pixels. Icon only buttons show up unlabelled, so a local is as puzzled as a person would be. Screenshots are the fallback. |
| **The ruler** | Code measures time per task, backtracks, dead ends and tap target sizes. The model only chooses the next action and says what it was thinking. |
| **The golden path** | You do each task once while it is recorded. Wherever a local leaves your path, the UI misled it. |
| **Proof** | A task counts as done only when the app's real state says so, never on the local's word. |

What Locals reports is behaviour, not wishlists. When a local cannot do something and does something else instead, that workaround is the feature request.

## Built for

One laptop: an RTX 4060 with 8 GB, [Ollama](https://ollama.com), and small models such as `qwen3:4b-instruct`. Long runs go overnight.

## Status

Day 0. The first test is one local doing one real task in [Pops](https://github.com/BiswasMosam/Pops), a Flutter Android app, on the emulator. If a 4B model can finish a real task in a real app, everything else builds on that.
