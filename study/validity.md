# Is the town right?

Level one built a town of locals. Level two asks whether what they do is worth acting on. A finding from Locals is only useful if a real person in that job would have run into the same thing, so this study collects every check we can make without interviews, and says plainly what each one shows.

**Status:** started 3 November 2026.

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

## 3. Against real people

| Check | Real people | The town | What it says |
|---|---|---|---|
| Task completion | 78% average across 1,189 usability tasks [1] | `python -m town report` | Whether locals are too good or too poor overall |
| First action on the same screen | Android in the Wild: 715,000 recorded human runs of Android tasks, screens and actions [2] | not yet | Whether locals go where people go |
| Typing, touch and reading | the studies in [limits](limits.md) | built into every local | Whether each local's numbers are human |

**Next: an accuracy score.** Put locals on screens from Android in the Wild, ask what they would tap first, and count how often they match the human. Two cautions: those humans were trained demonstrators who knew the task, not first time users, so the score measures whether locals find the right control, not whether they stumble like a newcomer; and a first-click study of real users found GPT's first clicks differed significantly from 3,431 people's in 53% of tasks [3], so a low score would be the expected starting point, and the number to beat.

## Sources

1. Sauro, *What Is A Good Task-Completion Rate?* [MeasuringU](https://measuringu.com/task-completion/)
2. Rawles et al., *Android in the Wild: A Large-Scale Dataset for Android Device Control*, NeurIPS 2023 Datasets and Benchmarks. [arXiv:2307.10088](https://arxiv.org/abs/2307.10088), [data](https://github.com/google-research/google-research/tree/master/android_in_the_wild)
3. Kuric, Demcak, Krajcovic, *What Would GPT Click: Practical Effects of Human-AI Behavioral Misalignment and the Cost of Synthetic Participants in User Experience*, 2026. [arXiv:2605.18302](https://arxiv.org/abs/2605.18302)
