# The study

Before a single local is built, we study the people they stand for. A local is only as real as the evidence behind it, so this folder comes first and the code comes second.

## What the research on AI personas says

Five findings shape every rule below.

| Finding | What it means for Locals |
|---|---|
| **Interviews beat demographics.** Agents built from two hour interviews matched real people's survey answers at 85% of the consistency people show with themselves two weeks later. Agents built from demographics alone reached about 74%. [1] | A profile is built from what people do and say, never from age, job and city. |
| **Identity prompts flatten people.** A model told "you are a (group)" answers the way outsiders see that group and blurs the differences inside it. [2] | Describe the situation, not the identity: hands busy, customer on the line, forty seconds to spare. Every job gets at least three different people. |
| **Personas turn into caricatures.** Models exaggerate whatever the persona says about someone. [3] | A trait may only change behaviour where the evidence says it should. |
| **Simulated users are too good.** The best of 31 simulators scored 76.0 for human likeness where real people scored 92.9: too cooperative, too uniform, never frustrated. [4] LLM walkthroughs finished more tasks on cleaner paths and found fewer failure points than people did. [5] GPT's first clicks differed significantly from 3,431 real participants in 53% of tasks, and adding personas or step by step reasoning mostly made the answers more believable, not more accurate. [6] Models also give suspiciously perfect answers where real people guess. [7] | Human limits are enforced by code, not requested in the prompt: a patience budget, a reading budget, a slip rate and give up rules, each with a number that comes from this study. |
| **Realistic personas can be learned.** Persona programs tuned against real conversations were judged human 80.4% of the time, nearly twice the usual simulators. [8] | Later, once we have real people's runs, we tune a local's settings against them instead of guessing by hand. |

## Rules of the study

1. **Every claim carries a source tag.**

   | Tag | Source |
   |---|---|
   | `[I]` | Interview with someone in the job |
   | `[O]` | Observed: watched them work or use the app |
   | `[D]` | Data or a published study |
   | `[A]` | A first hand account online (forum post, video, article by someone in the job) |
   | `[P]` | Known from building one of our apps for a real user |
   | `[G]` | A guess. Every guess must have a matching open question. |

2. **No guess reaches a local.** A `[G]` line is either confirmed by an interview or left out.
3. **Real people are never named.** Interview notes live in `study/interviews/`, which git ignores. Profiles describe composites.
4. **A profile is finished when someone in that job has read it and corrected it.**

## Who lives in the town

**Ring one: people our apps already serve.** There are real people we can check these locals against, so they come first. A local we can compare with a real person teaches us how to build every other one.

| Job | App it tests | Real person to check against | Profile |
|---|---|---|---|
| Fabrication shop owner | Pops | Yes | [Draft](profiles/fabricator.md) |
| Food stall counter | Order Control | Yes | [Draft](profiles/food-stall.md) |
| Homeowner hiring a fabricator | Biswas Fabricators site | Through the shop | Planned |
| Fresh graduate applying for jobs | Fill.ai | Yes | Planned |
| Photographer | PixelShift | Yes | Planned |
| Toy car collector | Peghunt | To find | Planned |
| Recruiter | Portfolio | To find | Planned |

**Ring two: the wider town.** Jobs our apps do not serve yet, so the town is more than our own customers. Each family is split into types by **how differently their day runs**; practice areas and specialities become the different people inside a type.

**[Law](profiles/law/README.md)**

| Type | The day in one line | Profile |
|---|---|---|
| Trial court advocate | Ruled by the cause list and the next date | [Draft](profiles/law/trial-advocate.md) |
| Junior advocate | Sent from courtroom to registry, reporting every date | [Draft](profiles/law/junior-advocate.md) |
| Law firm associate | Partners, redlines and timesheets | [Draft](profiles/law/firm-associate.md) |
| In-house counsel | Colleagues who need it signed today | [Draft](profiles/law/in-house-counsel.md) |

**Engineering**

| Type | The day in one line | Profile |
|---|---|---|
| Software engineer, product company | Deep work broken by meetings and alerts | Next |
| Software engineer, IT services | A client's project, a client's hours, timesheets | Planned |
| Mechanical, plant maintenance | Shop floor, shifts, breakdowns, gloves on | Planned |
| Mechanical, design | CAD workstation, drawings and revisions | Planned |
| Civil, site engineer | Construction site, contractors, sun on the screen | Planned |
| Civil, structural and planning | Drawings, approvals, coordination | Planned |
| Electrical, maintenance | Shifts, safety permits, field calls | Planned |
| Electronics, embedded | Lab bench, firmware, test equipment | Planned |

**Later families**

| Family | Types |
|---|---|
| Finance | Chartered accountant in practice, article assistant, accounts executive |
| Health | Clinic doctor, resident doctor, nurse, pharmacist |
| Education | School teacher, college professor, tuition teacher |

## How a profile becomes a local

```
profile  →  three different people  →  task cards  →  limits in numbers  →  a local  →  checked against a real person
```

The [template](profile-template.md) defines what every profile must cover. The [interview guide](interview-guide.md) is how the guesses become facts.

## Sources

1. Park et al., *Generative Agent Simulations of 1,000 People*, 2024. [arXiv:2411.10109](https://arxiv.org/abs/2411.10109)
2. Wang, Morgenstern, Dickerson, *Large language models that replace human participants can harmfully misportray and flatten identity groups*. [arXiv:2402.01908](https://arxiv.org/abs/2402.01908)
3. Cheng, Piccardi, Yang, *CoMPosT: Characterizing and Evaluating Caricature in LLM Simulations*, 2023. [arXiv:2310.11501](https://arxiv.org/abs/2310.11501)
4. *Mind the Sim2Real Gap in User Simulation for Agentic Tasks*, 2026. [arXiv:2603.11245](https://arxiv.org/abs/2603.11245)
5. Zhong, McDonald, Hsieh, *Synthetic Cognitive Walkthrough*, 2025. [arXiv:2512.03568](https://arxiv.org/abs/2512.03568)
6. Kuric, Demcak, Krajcovic, *What Would GPT Click*, 2026. [arXiv:2605.18302](https://arxiv.org/abs/2605.18302)
7. Aher, Arriaga, Kalai, *Using Large Language Models to Simulate Multiple Humans and Replicate Human Subject Studies*, ICML 2023. [PMLR](https://proceedings.mlr.press/v202/aher23a.html)
8. Chopra et al., *Beyond Cooperative Simulators: Generating Realistic User Personas for Robust Evaluation of LLM Agents*, 2026. [arXiv:2605.12894](https://arxiv.org/abs/2605.12894)
9. Lu et al., *UXAgent: An LLM Agent-Based Usability Testing Framework for Web Design*, 2025. [arXiv:2502.12561](https://arxiv.org/abs/2502.12561)
10. PayNearby, *MSME Digital Index*, 2024 and 2025 editions: WhatsApp used by 97% of surveyed small businesses, UPI the top digital payment method.
