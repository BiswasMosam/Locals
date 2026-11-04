# Is the town right?

Level one built a town of locals. Level two asks whether what they do is worth acting on. A finding from Locals is only useful if a real person in that job would have run into the same thing, so this study collects every check we can make without interviews, and says plainly what each one shows.

**Status:** started 3 November 2026; the first move score added 4 November 2026.

## 1. Model or person?

When a local fails, it can be the person they stand for, or the model playing them. A 4B model sometimes answers in ways no person could: it taps a letter that is not on the screen, or "sets" a slider without saying to what. Before level two those answers cost the local a step, so part of every "gave up" was the model's clumsiness, not the person's.

Now an answer no person could give is asked again, up to twice, and never costs a step; every run records how often (`run.json`) and `python -m town report` counts runs where a model mistake still cost a step apart from clean ones.

**What it changed.** On the first day with the change, four locals tried PixelShift's small JPG task. Three of them (a CA, a teacher and a doctor) had given up on the same task earlier the same day; now all three finished. The model was asked again five times, and none of those cost a step. Part of what looked like people struggling was the model.

## 2. Do the limits matter?

The limits (reading budget, slips, typos, patience) are what make a local human. If a local with no limits behaves the same as one with them, the limits are decoration. `python -m town ablate` runs the same locals twice on the same task, once as themselves and once reading everything, never slipping or mistyping, with endless patience.

**A short, easy task: they hardly matter.** Ten very different locals (a cook, a fabricator, two lawyers, a photographer, two engineers, an insurance agent, an ASHA worker and a teacher) made a small JPG in PixelShift:

| | Finished | Steps on average | Slips | Stuck |
|---|---|---|---|---|
| As themselves | 10 of 10 | 4.5 | 1 | 3 |
| With no limits | 10 of 10 | 4.9 | 0 | 0 |

The task is four taps on big buttons with short labels: there is little to skim, little to miss, and nobody's patience runs out in four steps. The same model decides in both runs, so it finds the same way through. On an easy screen, how a local behaves is mostly the model, and the limits only add a stumble here and there.

**A harder task: they change the outcome, the other way round.** Six locals turned five product photos into WEBP:

| | Finished | Steps on average | What happened |
|---|---|---|---|
| As themselves | 5 of 6 | 3.5 | 3 slips, 1 stuck, 1 handed the phone over |
| With no limits | 3 of 6 | 8.0 | 6 stuck, 2 handed the phone over, 1 went 30 steps and gave up |

Four of the six locals ended differently. But the locals with no limits did worse, not better. Reading everything means the model is handed PixelShift's whole wall of card text instead of the first words of each line, and a 4B model loses its way in it; with endless patience, one local circled for thirty steps. So "no limits" is not a perfect person, it is the same small model with more on its plate.

**What it means.**
- **The limits are real, and they only bite where an app is demanding:** long text, small or crowded targets, many steps. That is where real people struggle too, so it is the right place for them to bite.
- **On easy screens the town is the model's own competence.** Ten of ten is above the 78% real people reach across usability tests, so on easy screens locals are still a little too good.
- **The model is still the biggest factor.** Reading less helped the model more than reading everything helped "the person". Until the deciding part of a local is stronger, limits and model are tangled together, and what a local does on a hard screen says as much about a 4B model as about a fabricator.
- **Small numbers.** Ten and six locals, one seed each. These are first readings, not results; the tool is there to repeat them on every new task.

So the next step is the model's side of a local: a stronger model where the machine allows it, and a way of deciding that separates what a person would notice from what the model can hold in mind.

## 3. A stronger mind

If the model is the biggest factor, a better model, or a better way of deciding, should change how human the locals look. Every model here ran with its thinking switched off, so they are compared on equal terms, and each fits the 8 GB of the laptop's graphics card. Two ways of deciding are compared: one stage (the local sees the screen, after skimming, and acts), and two stages (first the local says what they actually notice, at most three to eight things depending on how they read; then they act on only those, and using something they never noticed counts as the model's mistake).

The same six locals (a cook, a fabricator, a wedding photographer, a plant engineer, an insurance agent and an ASHA worker) did both tasks, as themselves and with no limits, one seed each:

**Five photos to WEBP, the harder task**

| Mind | As themselves | With no limits |
|---|---|---|
| qwen3:4b-instruct, one stage | 5 of 6, 3.5 steps | 3 of 6, 8.0 steps |
| qwen3.5:4b, one stage | 4 of 6, 4.3 steps | 5 of 6, 4.8 steps |
| qwen3:8b, one stage | 0 of 6, 6.2 steps | 1 of 6, 23.3 steps |
| qwen3:8b, two stages | 3 of 6, 5.8 steps | 2 of 6, 24.3 steps |
| **qwen3:4b-instruct, two stages** | **5 of 6, 3.3 steps** | **6 of 6, 4.8 steps** |

**One small JPG, the easy task**

| Mind | As themselves | With no limits |
|---|---|---|
| qwen3:4b-instruct, one stage | 6 of 6, 3.8 steps | 6 of 6, 4.7 steps |
| qwen3:8b, one stage | 5 of 6, 3.7 steps | 6 of 6, 10.3 steps |
| **qwen3:4b-instruct, two stages** | **5 of 6, 4.7 steps** | **6 of 6, 4.8 steps** |

**What it showed.**
- **Bigger was worse.** qwen3:8b is built to reason before it answers; with that switched off (the only way it runs at the town's pace) it wandered. On the harder task it tapped PixelShift's home link and left the app in 4 of 6 runs as themselves and all 6 with no limits, and with no limits 12 of its answers could not be used even after asking again. It also took two to three times as long. Two stages helped it (3 of 6 instead of 0), but not enough.
- **Two stages fixed the paradox.** With one stage, the locals with no limits did worse than the locals as themselves, because the whole screen buried a 4B model. When a local first says what they notice and then acts only on that, the model is never buried: with no limits it finished 6 of 6 on both tasks. Now the limits cost something in the direction they should on both tasks: as themselves, 5 of 6 finished each time, with the slips and the looking around that real people show.
- **Closer to people, not perfect.** Two stages put the six locals at 10 of 12 (83%) across both tasks as themselves, against 78% for real people across many tasks [1]. Twelve runs is a first reading, and the benchmark is an average over different tasks, so this says the town is in the right range, not that it matches.
- **The cost is time.** Two stages ask the model twice a step, so a run takes about twice as long on the same machine.

So two stages on qwen3:4b-instruct are now the town's default (`LOCALS_STAGES=1` brings back the old way, `LOCALS_MODEL` tries another model), and the model and the person are less tangled: with no limits, the model now does the task; the limits are what make it harder.

## 4. Against real people

| Check | Real people | The town | What it says |
|---|---|---|---|
| Task completion | 78% average across 1,189 usability tasks [1] | `python -m town report` | Whether locals are too good or too poor overall |
| First action on the same screen | Android in the Wild: 715,000 recorded human runs of Android tasks, screens and actions [2] | `python -m town aitw`: 15% (below) | Whether locals go where people go |
| Typing, touch and reading | the studies in [limits](limits.md) | built into every local | Whether each local's numbers are human |

## 5. The first move, against people's

Android in the Wild records people doing tasks on Android phones: the goal they were given, every screen as an image with the words and icons a detector found on it, and what they did next. `python -m town aitw` puts a local on the same screen with the same goal and asks what they would do, the same two stages and the same prompt as a run, with slips left out so the score is what they meant to do. The answer is scored with the dataset's own rule: a tap matches when it lands in the same detected element as the human's, the element grown to 240% of its size, or within 14% of the screen of it; a scroll matches a scroll on the same axis; anything else matches the same kind of action [2]. The data is read straight from the dataset's public files, three of them (about 180 MB, from its general and single step parts), without TensorFlow.

**What was run.** The same six locals as before (a cook, a fabricator, a wedding photographer, a plant engineer, an insurance agent and an ASHA worker), each on 40 screens: the first move of 20 multi step tasks (after the demonstrator's habit of pressing home to start clean) and 20 single step tasks, as themselves and with no limits. Then the same model with no person at all, one stage, reading everything, the nearest thing to how the dataset's paper prompted PaLM 2.

| Who | Matched the human | Where a match was possible |
|---|---|---|
| The six locals, as themselves | 36 of 240 (15%) | 36 of 162 (22%) |
| The same six, no limits | 37 of 240 (15%) | 37 of 162 (23%) |
| The model, no person, one stage (two passes) | 12 of 80 (15%) | 12 of 54 (22%) |
| PaLM 2, the paper's prompt, every step [2] | 30.9% zero shot, 39.6% with five examples | 58% with five examples |

A match was possible on 27 of the 40 screens. On the rest the person did something a local cannot (pressed home or enter, swiped sideways) or tapped a place the detector found nothing at, like the empty part of a search bar; the paper reports the same gap, a third of its test episodes holding a tap on no detected element.

**What it showed.**
- **The locals are far from people on these screens, and the person they play is not why.** Fifteen per cent as themselves, fifteen with no limits, fifteen with no person at all. Playing a fabricator or an ASHA worker, reading less, deciding in two stages: none of it moved the score. What does is the model, on a screen given as scraps of detected text: a home screen's app icons arrive as "icon, shows a google", and a search bar with no words on it does not arrive at all.
- **Single step goals go better than first moves of long ones.** 22% on single step tasks, 8% on the first move of multi step ones, where the person's first move is often a tap on an unlabelled app icon or a swipe to the app drawer.
- **Some misses are sensible.** Locals never matched a person who typed (0 of 18): the person's keyboard was already in a search box the dataset does not mark, so the locals tapped the box first, or tapped a suggestion already on screen with the words they were about to type. The dataset's rule counts both as wrong.
- **Locals agree with each other.** On an average screen two thirds of the six locals gave the same answer. Different people, mostly the same move: the flattening the persona research warns about (see the [study](README.md#what-the-research-on-ai-personas-says)).
- **PaLM 2 did about twice as well**, on every step of a different split and a model many times larger. The paper's own trained agents reached 73%. A 4B model on a laptop is the starting point, and the number to beat.

**What it does not say.** The demonstrators were paid contractors with written instructions and a tutorial, working an emulator with a mouse [2]: the score is about finding the way, not about stumbling like a newcomer. The town's own runs read the accessibility tree, which names buttons and boxes that this dataset's screens only show as scraps of text, so locals see more in a run than here. Forty screens and six locals, one seed each.

**Next, if the score is to rise:** feed the screenshot itself to a vision model that fits in 8 GB, and give the town's own screens the same test with recorded people (`python -m town watch --for`).
## Sources

1. Sauro, *What Is A Good Task-Completion Rate?* [MeasuringU](https://measuringu.com/task-completion/)
2. Rawles et al., *Android in the Wild: A Large-Scale Dataset for Android Device Control*, NeurIPS 2023 Datasets and Benchmarks. [arXiv:2307.10088](https://arxiv.org/abs/2307.10088), [data](https://github.com/google-research/google-research/tree/master/android_in_the_wild)
3. Kuric, Demcak, Krajcovic, *What Would GPT Click: Practical Effects of Human-AI Behavioral Misalignment and the Cost of Synthetic Participants in User Experience*, 2026. [arXiv:2605.18302](https://arxiv.org/abs/2605.18302)
