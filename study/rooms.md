# The rooms

Locals can sit in a room and listen to a talk: a class presentation, a project review, an interview panel, a leadership meeting, an investor pitch or a public talk. You give the talk as files, and the room tells you who stayed with you, who drifted and why, who reached for their phone or fell asleep, what they could say your point was afterwards, what they would ask, and, where the room gives marks, what each grader gave you and on what evidence.

A room is the same idea as the rest of the town turned to face a speaker: **the model plays the person, and code holds the limits.** A small model asked "how engaging was this talk?" will praise it; asked to play a cook at a talk on service workers, it will happily say he is fascinated. So the model is only asked what a person in that seat would think and whether a part matters for why they came, and, once for the whole talk, to sort its terms into the field each belongs to. Code checks each answer against the talk and moves their attention by the rules below. Being hooked, drifting, getting the phone out and falling asleep are thresholds on that number, never the model's say so.

**Who knows which terms is code's call.** The first version asked the model which of a part's terms each listener would not know. A 4B model ticked nearly every term for everyone, a backend engineer's "timeout" and "schema" included, and every listener fell asleep together. Now each job has its fields (a software engineer: software and engineering; a CA: finance and business; a cook: trade), a local's file can add more (`knows = ["software"]`), and a term counts against a listener only when it is outside their fields, is not one of their own work words, and was in what actually reached them. The same technical talk then lost the cook and the advocate by the third minute while the software engineer never drifted.

**Status:** first version, 3 November 2026. The direction of every rule comes from published research; most of the sizes are still guesses, marked `[G]`, until they can be checked against real audiences.

## What a talk is

| Input | What is read | What is measured |
|---|---|---|
| A deck, `.pptx` | Each slide's title, lines, tables and speaker notes | Words on the slide, text sizes the file sets, pictures, charts and tables |
| A deck, `.pdf` | Each page's text | Words on the page, text sizes, images |
| A script, `.txt` or `.md` | What is said, cut at `[slide 3]` lines or `---`, else into minute long parts | Words; time at 150 words a minute, the usual pace of English speech `[A]` [1], or the minutes you give |
| A recording, `.mp3`, `.m4a`, `.wav` and others | What is said, phrase by phrase, by Whisper on your own machine | Real time per part, pace, pauses of two seconds or more, fillers |

With a deck and a speech together, each sentence goes to the slide whose words it shares, in order, unless the script marks the slides itself. Recordings are transcribed on the processor by faster-whisper's small model, so the graphics card stays free for the locals. Text sizes are given as if on a standard slide 7.5 inches tall, and 24 points is used as the floor for text read from the back of a room, the minimum university accessibility guides most often give for slides, such as the University of Washington's and Newcastle University's [17] `[A]`. Whisper tidies fillers away unless its prompt already contains some, a known trick that is used here; even so, a recording undercounts them.

## How attention moves

Every listener starts a talk at 70 out of 100, or 85 if they are there to grade it `[G]`. Each part of the talk then moves it:

| Rule | What the research says | The size here |
|---|---|---|
| **Time without a break** | Mind wandering rises and memory falls the longer a lecture runs [2] [3]; lapses come more often as a lecture goes on [4] `[D]` | 1 point a minute, plus 1 more for every 5 minutes since the last break, at most 4 a minute `[G]` |
| **Age** | Young adults reported mind wandering on 41% of probes in daily life, older adults on 28% [5] `[D]` | Drift falls from 1 at 30 to 0.7 at 60 and over, the ratio of the two `[D]` |
| **Terms they do not know** | Jargon lowers engagement and makes people feel the subject is not for them, even when the terms are defined [6] `[D]` | 2 points for each term outside their fields that reached them in a part, at most 8 a part `[G]` |
| **Too fast** | Comprehension of speech holds up to about 250 to 275 words a minute for native listeners, then falls quickly [7] `[D]`; slower speech helped lower intermediate second language listeners [8] `[D]` | Beyond 250 words a minute when English is easy for them, 150 when it is slow `[G]` |
| **Too much to read** | Slides with a phrase headline and bullets led to worse comprehension and higher load than a sentence headline with visual evidence [9] `[D]`; reading the same words you are hearing gets in the way [10] `[D]` | A listener can read for half the time a slide is up, at their own reading speed; 1 point for every 4 words beyond that, at most 12 `[G]` |
| **Why they came** | A listener's own reasons decide what holds them `[G]` | The model says whether a part matters to them: 4 points if it does, 4 off if it does not `[G]` |
| **The point, late** | Chief executives spend 72% of their working time in meetings and say many could be a quarter of the length [11] `[D]` | In a boardroom or a pitch, 8 points off every part after the minute the room expects the point, until it comes `[G]` |
| **A break** | Demonstrations and questions to the class were followed by fewer lapses than lecture [4] `[D]`; stories raise interest and are easier to follow [12] `[D]` | A story, an example, a demonstration or a question to the room: 10 points, and the drift starts over; a surprising number or a joke: 5 `[G]` |
| **Something that wakes you** | | A question to the room, a demonstration or a joke reaches even someone who has stopped listening `[G]` |

What reaches a listener depends on where their attention is as a part begins. With you or hooked (50 and over), they hear it all and read each slide line as far as their reading budget goes. Drifting (35 to 50), they catch the title, two lines and the first sentence. Below that they only glance up at the title, and asleep, nothing. Graders never fall asleep; they check their email and then stop listening. Nobody falls asleep in the first 8 minutes of a talk, whatever it is: they reach for the phone instead `[G]`.

**Interviewers make up their minds.** Across more than 600 real interviews, 4.9% of interviewers decided in the first minute, 25.5% within five and 59.9% within fifteen [13] `[D]`. In the interview room each panelist draws when they decide from those shares, and what comes after that point is marked "after they had made up their mind" in their evidence.

## The room's markers

| Marker | When code calls it |
|---|---|
| **Hooked till the end** | Every listener stayed at 60 or above all the way and ended at 70 or above |
| **Lost the room** | The first part where half the room or more was below 50, with what put them there |
| **The room fell asleep** | A third or more of the audience (at least two people) asleep at once |
| **Brought them back** | Someone came back above 50, and the part that did it |
| **Over time** | More than 30 seconds past the room's limit |
| **Remembered the point** | How many could say your point afterwards |

## What they remember

When the talk ends, each listener is shown only what reached them, part by part, and asked what the talk's main point was in their own words, and the one question they would ask you now. A second, cold reading compares their point with yours: given with `--point`, or read from the talk. Someone who was on their phone for most of it can only remember what they caught; this is the link the lecture studies found between wandering and memory [2] [3]. A question is kept only if it is about something they heard, and a question asking what a word means only if it was a term they did not know; asked along the way, the model kept asking what "order" means.

## The marks

Graders mark the talk on the room's rubric, from what reached them. Every mark has to point at evidence: a part they took in (P3), a measured fact (M2), or a moment in the room (R1). A mark is dropped if its evidence does not exist, if its reason does not talk about that evidence, or if it guesses; graders are told why and asked once more. Delivery as the rubrics define it (posture, gestures, eye contact) cannot be seen in a file, so it is not marked at all without a recording, and with one it is marked on the voice alone. The room's markers then add or take away the points the rubric gives them.

| Rubric | Room | Where it comes from |
|---|---|---|
| Oral communication, out of 20 | A college class | Adapted, in our words, from the AAC&U Oral Communication VALUE rubric: organization, language, delivery, supporting material, central message, four levels each [14] `[D]`. AAC&U made it for assessing programmes, not for grading a student, and asks that it be translated for each campus; universities do adapt it for grading, as here |
| Project review, out of 50 | A project review | A house rubric: problem, method, results, limits, and the talk `[G]`. Replace it with your university's |
| Interview scorecard, 1 to 5 | A job interview panel | Each part on its own anchored scale, by each panelist, then combined, as structured interview research recommends [15] `[D]`; the parts are a house choice `[G]` |
| A proposal to leadership, out of 100 | A leadership meeting | A house rubric: the ask, why it matters, evidence, risks, next step `[G]` |
| An investor pitch, out of 100 | An investor pitch | Weighted by how many of 885 venture capitalists named each factor important: team 95%, business model 83%, product 74%, market 68% [16] `[D]`; the ask is a house addition `[G]` |

Rubrics live in [rooms/rubrics.toml](../rooms/rubrics.toml) and rooms in [rooms/rooms.toml](../rooms/rooms.toml); change either for your own class, panel or company. Verdicts such as "move forward" or "a second meeting" are house rules for what a score means, not research.

## What a room cannot tell you

- **How you look.** No posture, gestures, eye contact or slides on a real screen. A recording gives the voice; nothing gives the body.
- **A real room's mood.** Real audiences catch each other's boredom and laughter. Locals listen side by side, alone.
- **The sizes.** The direction of every rule is sourced; how many points each one moves is a first guess. Calibrating them needs real audiences reporting their attention through a talk, the way the clicker studies did [4].
- **The model's own taste.** A 4B model decides what matters to a lawyer and which field a term belongs to. The checks keep it to the talk's own words, but not to the truth of a person.
- **A kind grader.** Every mark must rest on evidence, but the level chosen is still the model's. On the first runs a professor gave a deliberately good talk 20 of 20 and a deliberately technical one 10.2; real professors seldom give full marks. Read a mark as where your talk stands between those two, not as the number a real professor would write.

## Open questions

1. How fast does attention really fall in an Indian college classroom after lunch?
2. How much does one unknown term cost a listener who is otherwise interested?
3. How do real panels in India mark a presentation round, and how much do they agree?

## Sources

1. Speaking rates for English, attributed to the National Center for Voice and Speech, summarised by [VirtualSpeech](https://virtualspeech.com/blog/average-speaking-rate-words-per-minute).
2. Risko, Anderson, Sarwal, Engelhardt and Kingstone, *Everyday Attention: Variation in Mind Wandering and Memory in a Lecture*, Applied Cognitive Psychology 26, 2012. [doi:10.1002/acp.1814](https://doi.org/10.1002/acp.1814)
3. Farley, Risko and Kingstone, *Everyday attention and lecture retention: the effects of time, fidgeting, and mind wandering*, Frontiers in Psychology, 2013. [Full text](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2013.00619/full)
4. Bunce, Flens and Neiles, *How Long Can Students Pay Attention in Class? A Study of Student Attention Decline Using Clickers*, Journal of Chemical Education 87, 2010. [doi:10.1021/ed100409p](https://doi.org/10.1021/ed100409p)
5. Maillet and others, *Age-related differences in mind-wandering in daily life*, Psychology and Aging 33, 2018. [PDF](https://beatylab.la.psu.edu/files/2020/08/2018_Maillet_PsycholAging.pdf)
6. Bullock, Colón Amill, Shulman and Dixon, *Jargon as a barrier to effective science communication: Evidence from metacognition*, Public Understanding of Science 28, 2019. [doi:10.1177/0963662519865687](https://doi.org/10.1177/0963662519865687)
7. Foulke, 1968, and Sticht, 1969, on comprehension of accelerated speech, reviewed in [DTIC AD0701150](https://apps.dtic.mil/sti/pdfs/AD0701150.pdf).
8. Griffiths, *Speech rate and listening comprehension: Further evidence of the relationship*, TESOL Quarterly 26, 1992; other studies found slowing down did not help intermediate and advanced listeners.
9. Garner and Alley, *How the Design of Presentation Slides Affects Audience Comprehension: A Case for the Assertion Evidence Approach*, International Journal of Engineering Education 29, 2013. [PDF](https://www.ijee.ie/articles/Vol29-6/23_ijee2791ns.pdf)
10. Mayer and Fiorella, on the redundancy principle in multimedia learning, *The Cambridge Handbook of Multimedia Learning*, 2014.
11. Porter and Nohria, *How CEOs Manage Time*, Harvard Business Review, July 2018; [CNBC summary](https://www.cnbc.com/2018/06/20/harvard-study-what-ceos-do-all-day.html).
12. Dahlstrom, *Using narratives and storytelling to communicate science with nonexpert audiences*, PNAS 111, 2014. [PMC4183170](https://pmc.ncbi.nlm.nih.gov/articles/PMC4183170)
13. Frieder, Van Iddekinge and Raymark, *How quickly do interviewers reach decisions?*, Journal of Occupational and Organizational Psychology, 2016; [BPS Research Digest](https://bps.org.uk/research-digest/do-interviewers-really-make-hiring-decision-first-four-minutes).
14. AAC&U, *Oral Communication VALUE Rubric*. [aacu.org/value](https://www.aacu.org/initiatives/value-initiative/value-rubrics)
15. Campion, Palmer and Campion, *A review of structure in the selection interview*, Personnel Psychology 50, 1997.
16. Gompers, Gornall, Kaplan and Strebulaev, *How Do Venture Capitalists Make Decisions?*, Journal of Financial Economics 135, 2020; [the authors' summary](https://corpgov.law.harvard.edu/2019/08/20/how-do-venture-capitalists-make-decisions).
17. University of Washington DO-IT, [How can you make your presentation accessible?](https://www.washington.edu/doit/how-can-you-make-your-presentation-accessible); Newcastle University, [font size for presentations](https://services.ncl.ac.uk/itservice/help-services/accessibility-advice/designingaccessiblecontent/guidance/fontsize).
