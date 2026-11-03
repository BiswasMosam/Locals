# Their take: what a local's job lets them see

A lawyer who uses an app notices a word that means something exact in law used loosely. A photographer notices that "Small" quietly threw away the colour profile. A software engineer notices the console filling with errors. People who know a field see things in an app that nobody else does. This study is about giving that to the locals without giving them a licence to make things up.

**Status:** first version. Every finding is tagged like the profiles (`[D]` data or a published study, `[A]` a first hand account, `[G]` a guess).

## What the research says

| Finding | What it means for Locals |
|---|---|
| **People who know the field find more.** Usability specialists who also knew the kind of interface being evaluated, "double experts", found more problems than usability specialists alone, who found more than novices `[D]` [1]. | A local's job is worth asking about. |
| **Work-domain experts find fewer problems, but worse ones.** Experts in the users' own work found fewer issues than usability experts, but theirs were rated more severe and developers gave them higher priority `[D]` [2]. Their findings were as valid, if less thorough; two of them matched one usability expert `[D]` [3]. | Expect few remarks per local, worth more each. A panel of several locals covers more than one. |
| **A persona does not add knowledge.** Across 162 personas and 2,410 factual questions, telling a model "you are a (role)" did not make it more accurate than no persona at all; the effect was largely random `[D]` [4]. | Saying "you are a lawyer" does not make the model know law. Expertise has to come from somewhere else. |
| **Models invent law.** Asked verifiable questions about real court cases, language models hallucinated at least 58% of the time, could not tell when they were doing it, and went along with users' wrong legal assumptions `[D]` [5]. Locals run on a 4B model, far smaller than the ones tested. | A local may never state a law, rule or standard from the model's memory. Only facts written into this study, with a source, can be cited. |
| **Models can critique interfaces, and also invent violations.** GPT-4 feedback on UI mockups was useful for catching subtle errors and improving text, but it can flag guideline violations that are not there `[D]` [6]; a dataset of real critiques improved model feedback by 55%, still short of human evaluators `[D]` [7]. | Every remark has to point at something real on the screen or in a measurement, and code checks that it does. |
| **AI users are too good** (from the [study](README.md)). | Takes come after the run and never change what happened in it. Behaviour stays the finding; a take explains it. |

## The rules

1. **Expertise changes what they notice and the words they use, never what they know.** What a local knows about their field comes from this study: a short list of facts with sources, per family, in [expertise/lenses.toml](../expertise/lenses.toml).
2. **Expert eyes are instruments, not imagination.** A software engineer gets measurements a sighted user would not: console errors, failed requests, how long the page took to settle, controls with no name, tap targets below the size standards. A photographer gets the facts of the file they saved: real format, size, quality, colour profile, location data. A lawyer gets every claim and consent line on the screens they saw, and whether a file was sent anywhere. Code measures; the local only reads the numbers.
3. **Every remark points at evidence.** A line they saw on screen, a measurement, a word from their job's glossary, or a moment in their own run. A remark without valid evidence is dropped by code before anyone sees it.
4. **Field facts must be cited, and must apply.** A remark that relies on a law, standard or rule names one of the facts in its lens. It may say what the rule asks and what the evidence shows, never that the app breaks the law: a run cannot show that. A fact that only applies in some cases says so, and code drops it when the run shows it does not apply. Anything uncited is shown as their view, not as fact.
5. **No wishlists.** A remark is about something that was there (or plainly missing, like a privacy notice on a screen that takes files). Features nobody needed in this run are not remarks.
6. **"Nothing in my field here" is an answer.** An advocate converting a photo may have nothing legal to say. Most remarks should come from people whose field the app touches.
7. **Their words, no act.** Remarks use their field's vocabulary (a CA says "challan", an engineer says "LCP"), never an accent, a caricature or a comparison to their work; code drops similes.
8. **A panel, not a chorus.** When several locals point at the same evidence, it is one remark with a count of who raised it, so three lawyers saying one thing is not three findings.

## The lenses

| Family | What their work makes them notice | Instruments |
|---|---|---|
| Ring one (fabricator, food stall) | Words their trade uses differently, what slowed them down | Glossary from their profile, their own run |
| Law | Claims an app makes, consent and notice, loose use of exact words | Claims and consent on screen, uploads during the run |
| Media | What happened to the picture: format, size, quality, colour, location data | The saved file's facts |
| Engineering, software | Errors, slowness, unnamed controls, small targets, honest naming of what a setting does | Console, network, page timing, accessible names, target sizes |
| Engineering, other fields | Units, precision, whether the result matches what was asked | The saved file's facts, sizes and units on screen |
| Finance | Amounts, number grouping, currency, dates, and whether a result is small enough for portals | Numbers and dates on screen, the saved file's size |
| Health | Whether personal data leaves the device, clarity under time pressure | Claims and consent on screen, uploads during the run |
| Education | How plainly instructions are written, which languages are offered | Sentence lengths and scripts on screen |

Every local also gets the glossary from their own profile (section 7, "Their words"): when the app uses the word the profile says an app might use instead of theirs, that is evidence they can point at.

## How a take is made

```
the run  →  evidence: screens seen, run moments, glossary hits, measurements  →  one model call in the local's voice
         →  code checks every remark  →  one revision round for what was dropped, told why
         →  TAKE and EXPERT in the feed  →  the day's panel
```

The checks, in order: the evidence exists; cited facts are in the study; a cited rule applies to what the run showed; the evidence is of a kind their field covers; no comparison to their job; no conclusion that a law is broken; no guessing at what the app does out of sight; the remark talks about its evidence; no two remarks about the same evidence. Each dropped remark is saved with its reason in the run's `take.json`, so the grounding rate can be read for any day. `python -m town take <day>` asks a past day's locals again, to test a change to the study without running the day.

## What the first test showed

A photographer, a software engineer, a lawyer, a CA, a doctor and a teacher converted a photo in PixelShift on 3 November 2026 (a second lawyer joined for the last version), and their takes were asked again as the checks grew.

| Version | Kept | What went wrong |
|---|---|---|
| Evidence ids only | 14 shown; proposals were not counted yet | The lawyer found PixelShift "violating sections 5 and 6 of the DPDP Act" and "misleading under the Consumer Protection Act… may store your file", although the network log showed the file never left the device. The doctor said the photo "likely carries GPS location"; the file facts showed no EXIF at all. A teacher called a list of formats a 19 word sentence. |
| Plus: no legal conclusions, no guessing, the remark must talk about its evidence (same day, asked again) | 8 of 14 | Conclusions came back in other words: "constituting a misleading advertisement", "breaks the law", "does not satisfy the Act". Generic praise passed by sharing filler words with its evidence. |
| Plus: wider conclusion words, filler ignored, rules that state when they apply, one revision round with the reasons (a new day, seven locals) | 6 of 13 | Nothing wrong survived. |

**What the checks kept in the last version.** The software engineer measured a layout shift of 0.18 on PixelShift's first screen, over the 0.1 that Core Web Vitals calls good, and a quality slider only 18 CSS pixels tall, under WCAG 2.2's 24. The lawyer noted there was no privacy notice or terms on any screen while the app took a file, without claiming a breach. The teacher noted every screen was English only.

**What it means.**
- **A 4B model cannot be trusted with a field's rules on its own**, exactly as the persona and legal hallucination studies warned. With measurements and checks it can still point a field's eye at real things.
- **Applicability comes before obligation.** The DPDP notice duty is about personal data a business receives. A reference can say when it applies (`needs = "data-sent"`), and code drops a citation that the network log shows does not apply.
- **A checker that only says no wastes good remarks.** One revision round, told why a remark was dropped, recovered the engineer's two measured findings.
- **Most locals had nothing to add**, which is what Følstad's work-domain experts predict: few remarks, each worth more.
- **"Words of their trade" invited a costume.** Told to speak in his trade's words, Sunil the food stall cook said he "cut the photo down like I'd slice meat" and called a large file "a thick, heavy dish", the caricature the persona research warns about [CoMPosT, in the [study](README.md)]. Now the prompt forbids comparisons to their work, code drops any remark built on a simile and cuts simile sentences from a take, and a lens can limit which evidence its people may point at: the fabricator and the food stall speak only about their own trade's words and their own run. Asked again, Sunil said: "I did it. The file is smaller."

## How we will know it works

- **Grounding rate:** the share of remarks the model proposes that survive the evidence check. Low means the prompt or the model is inventing.
- **Spread:** whether three locals of one type say three different things, or the same thing three times.
- **Agreement:** whether someone in the field agrees with a remark. Readers can say so through the [correct a profile](../.github/ISSUE_TEMPLATE/correct-a-profile.yml) form; Mosam is himself a photographer and an engineer, the first judge for those families.

## Open questions

1. Do real lawyers care about an image converter's privacy claim, or is that a reach?
2. Which measurements would a software engineer actually look at first?
3. How many remarks per run feel useful rather than noisy?

## Sources

1. Nielsen, *Finding usability problems through heuristic evaluation*, CHI 1992. [PDF](https://course.khoury.northeastern.edu/is4300sp13/ssl/articles/p373-nielsen.pdf)
2. Følstad, *Work-domain experts as evaluators: usability inspection of domain-specific work-support systems*, IJHCI 2007. [SINTEF](https://www.sintef.no/en/publications/publication/1273848/)
3. Følstad, Anda, Sjøberg, *The usability inspection performance of work-domain experts: An empirical study*, Interacting with Computers 2010. [SINTEF](https://www.sintef.no/en/publications/publication/343140)
4. Zheng et al., *When "A Helpful Assistant" Is Not Really Helpful: Personas in System Prompts Do Not Improve Performances of Large Language Models*, Findings of EMNLP 2024. [arXiv:2311.10054](https://arxiv.org/abs/2311.10054)
5. Dahl, Magesh, Suzgun, Ho, *Large Legal Fictions: Profiling Legal Hallucinations in Large Language Models*, Journal of Legal Analysis 2024. [arXiv:2401.01301](https://arxiv.org/abs/2401.01301)
6. Duan, Warner, Li, Hartmann, *Generating Automatic Feedback on UI Mockups with Large Language Models*, CHI 2024. [arXiv:2403.13139](https://arxiv.org/abs/2403.13139)
7. Duan et al., *UICrit: Enhancing Automated Design Evaluation with a UICritique Dataset*, 2024. [arXiv:2407.08850](https://arxiv.org/abs/2407.08850)
