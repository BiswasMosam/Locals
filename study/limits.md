# Limits from published data

A local's limits are the numbers that make them human: how many words they take in before acting, how often a tap lands on the wrong thing, how often a letter comes out wrong. They used to be guesses, one per local, to be replaced by interviews. Live interviews are no longer planned; instead this study sets the numbers from published research on how real people type, tap and read, and from what each profile already says about the person.

**Status:** first version, 3 November 2026. Tags as in the profiles: `[D]` data or a published study, `[A]` a first hand account or a job's stated requirements, `[G]` a guess, kept visible so it can be replaced.

## What the research gives us

| Finding | Number |
|---|---|
| **Typing on phones.** 37,370 people typing on their own phones averaged 36.2 words a minute and left 2.3% of characters wrong `[D]` [1]. Teens were fastest (about 40 words a minute); people in their forties managed about 26 to 29 `[D]` [1]. | 2.3% of characters left wrong |
| **Older hands miss more.** Older adults made 32.17% errors selecting touch targets against 9.17% for younger adults, about 3.5 times as many, and the gap was widest on the smallest targets; errors fell significantly at 9.22 mm and above `[D]` [2]. | ×3.5 for older adults |
| **Target size.** For one handed thumb use, error rates stopped improving for targets above about 9.6 mm for single taps `[D]` [3]; Android asks for 48 dp `[D]` [4]; WCAG 2.2 sets a floor of 24 CSS pixels `[D]` [5]. | 48 is comfortable |
| **Walking.** Selecting targets while walking raised errors by 23% and time by 31% against standing `[D]` [6]. | ×1.23 |
| **Water.** Water on a touch screen causes false and missed touches; filtering them cut errors by 75.7%, so wet hands and screens are a large effect `[D]` [7]. | large, size guessed |
| **Reading.** In a naturalistic study of browsing, people had time to read at most 28% of the words on a page, more realistically 20%; the estimate assumes 250 words a minute `[D]` [8]. | 250 words a minute |
| **Task completion.** Across 1,189 tasks in 115 usability tests with 3,472 people, the average completion rate was 78% `[D]` [9]. | 78% |
| **Digital skills in India.** Only 7% of adults with primary schooling can send and receive email, against 76% with higher education `[D]` [10]; among 15 to 29 year olds, 61% in cities and 33% in villages can copy and paste `[D]` [11]. | skill follows schooling |

## A local's traits

Every local now has a `[traits]` table in their file, read from what their profile and situation already say (`python -m town derive` fills it; edit it and derive again to change a local):

- **Education** from what the job requires to enter it: a law, medicine, engineering, accounting, teaching or banking job needs a degree `[A]`; trades and small businesses are counted as secondary schooling `[G]`; ASHA workers as primary `[G]`.
- **Conditions** from the words of their situation: moving (in an auto, a train, walking the lanes), wet (oily, greasy, damp, sweat), gloves (unless the glove is off), one hand, rushed, tired.
- **Glance**, the seconds they give one label, from how the profile says they read: one second for "glances" or "two or three words", two for "skims" or "the first line", four for "properly", five for "carefully" or "word by word" `[G]`.
- **English**, slow when the profile says English slows them down.

## The numbers

| Limit | How it is set | Tags |
|---|---|---|
| **read_words** | reading speed × glance. 250 words a minute with a degree `[D]`, 200 with secondary schooling and 140 with primary `[G]`, × 0.6 when English is slow `[G]` | `[D]` `[G]` |
| **slip_rate** | 3% on a phone for a younger adult on a comfortable target `[G]`, anchored on the young adults above; 1% with a mouse `[G]`. × 1.8 from 45 `[G]`, × 3.5 from 60 `[D]`. × 1.23 moving `[D]`; × 2 wet, × 2 gloves, × 1.2 one hand, rushed or tired `[G]`; conditions together at most × 3 `[G]` | `[D]` `[G]` |
| **slip, per tap** | on a touch screen the rate grows as the target's short side falls below 48 (dp, or CSS pixels on the web), up to × 3 at 16 or less `[G]` in shape, anchored on [2], [3] and [4] | `[D]` `[G]` |
| **typo_rate** | 2.3% on a phone `[D]`, 1.5% on a laptop keyboard `[G]`; × 1.3 from 40, × 1.6 from 60 `[G]`; the same conditions, typing versions `[G]` | `[D]` `[G]` |
| **patience_steps, repeat_before_stuck** | still guesses from the profile `[G]`; see the check below | `[G]` |

## What changed

| Limit | Before (guessed) | After (derived) | Locals changed |
|---|---|---|---|
| read_words | mean 8.6, median 8 | mean 11.0, median 8 | 82 of 99 |
| slip_rate | mean 0.046 | mean 0.032 | 92 of 99 |
| typo_rate | mean 0.039 | mean 0.027 | 77 of 99 |

The guesses made people clumsier than the studies do: the typing data alone says 2.3% of characters, where the guesses averaged 3.9%. Readers who are careful by their own profile now take in more, and the ones who glance still take in two to four words.

## The check on patience

Patience cannot be read from these studies, but the town as a whole can be checked against real people. Across every saved run so far, locals finished **26 of 53 tasks (49%)**, against **78%** for real people in usability tests [9]. Three things push the town low, and only the first is human: many of those runs were set on hard days (monsoon downpours, festival rushes, a lockdown); the 4B model sometimes forgets to give a value for a slider and loses steps to it; and PixelShift's quality slider sent locals in circles in nearly every run. The benchmark is a range, not a target: commercial software tested in labs is easier than a first visit to a new app. As more days are run on ordinary dates, this check says whether patience needs to rise.

## Open questions

1. How do error rates on phones change with age past 40, for typing rather than tapping?
2. How much do gloves and wet hands really raise touch errors? No study measured it in numbers.
3. What reading speed in English is typical for someone with secondary schooling in India?
4. What completion rate do first time users reach on simple Indian apps?

## Sources

1. Palin et al., *How do People Type on Mobile Devices? Observations from a Study with 37,000 Volunteers*, MobileHCI 2019. [PDF](https://www.pokristensson.com/pubs/PalinEtAlMobileHCI2019.pdf), [summary](https://www.technologyreview.com/2019/10/02/65245/the-fastest-texters-in-the-world-couldnt-care-less-about-texting/)
2. Sultana and Moffatt, *Effects of Aging on Small Target Selection with Touch Input*. [McGill](https://escholarship.mcgill.ca/downloads/6108vh322)
3. Parhi, Karlson, Bederson, *Target Size Study for One-Handed Thumb Use on Small Touchscreen Devices*, MobileHCI 2006. [Microsoft Research](https://www.microsoft.com/en-us/research/?p=155150)
4. Android, *Make apps more accessible*. [developer.android.com](https://developer.android.com/guide/topics/ui/accessibility/apps)
5. W3C, *Understanding SC 2.5.8: Target Size (Minimum)*. [w3.org](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
6. Schildbach and Rukzio, *Investigating selection and reading performance on a mobile phone while walking*, MobileHCI 2010. [PDF](https://www.uni-ulm.de/fileadmin/website_uni_ulm/iui.inst.100/institut/Papers/Prof_Rukzio/2010/SchildbachMobileHCI2010.pdf)
7. Tung et al., *RainCheck: Overcoming Capacitive Interference Caused by Rainwater on Smartphones*, ICMI 2018. [PDF](https://faculty.washington.edu/wobbrock/pubs/icmi-18.02.pdf)
8. Nielsen, *How Little Do Users Read?*, 2008. [NN/g](https://www.nngroup.com/articles/how-little-do-users-read/)
9. Sauro, *What Is A Good Task-Completion Rate?* [MeasuringU](https://measuringu.com/task-completion/)
10. MoSPI, Comprehensive Annual Modular Survey 2022-23, via [Data For India](https://www.dataforindia.com/ict-skills/)
11. NSS 78th round, Multiple Indicator Survey 2020-21, via [Factly](https://factly.in/data-nss-mis-report-highlights-the-stark-urban-rural-male-female-divide-in-ict-skills)
