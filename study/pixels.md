# Seeing pixels

A local reads a screen as words: the page's controls and text, or an Android app's accessibility tree. Some things a person sees cannot be read that way: text too faint to make out, a loading screen covering a page whose words are all there underneath, the one orange button the eye goes to first. This study is what a local now takes from the screenshot itself, and why.

**Status:** built 4 November 2026 (`town/pixels.py`).

## What is measured

Every step of a run already saves a screenshot. Code reads it, never a model, so the same screen gives the same answer.

| Measure | How | Rule |
|---|---|---|
| **What is really there** | Each run of text inside a control has a box. If none of a control's text leaves a mark in its box (one flat colour), something covers it or it has not been drawn yet. A control with no words counts as unseen only when its box is one flat colour the same as around it. | Unseen controls are taken off the local's screen: a person cannot tap what they cannot see. |
| **Contrast** | In each run of text, the most common colour is the background and the farthest in brightness is the ink. Their ratio is WCAG's contrast ratio. A box with many colours and no main one is a picture, and is not measured. Text fields and menus are not measured: their box holds a border and a caret, not one label. | Below 4.5:1 for normal text, or 3:1 for large text (24 px, or 18.66 px bold) and for symbols, is below what WCAG asks [1] `[D]`. Greyed out controls are left out, as WCAG leaves them out. |
| **What stands out, on a laptop** | For each control, the colour difference (CIE Lab) between it and what surrounds it, weighted by its size. | The three that differ most catch the eye first. Shown on laptop screens only (see below). |

**How it reads to a local.** Under 3:1, the floor for normal vision in the ISO and ANSI display standards that WCAG cites [1] `[D]`, a control is "faint, hard to make out". From 3:1 up to what WCAG asks, it is "low contrast": readable for most people, not for people with low vision. Inside a big card, each faint line is marked on its own, and the card as a whole is faint only when its main words (its biggest text) are. On a laptop, the screen description adds "What catches the eye first on this screen".

## Why phones get no "stands out"

On web pages, a classic saliency model (colour and brightness against the surroundings, after Itti and Koch) predicts where people first look [2] `[D]`. On phones it does not: in an eye tracking study of mobile app screens, bright and large elements did not draw the eye; text, pictures and the top left corner did [3] `[D]`. So on a phone the local keeps the reading order, top left first, and only a laptop gets the ranking. Turning a finding about desktop pages into a rule for phones would be the model's guess dressed up as evidence.

## Checked against the page's own colours

On PixelShift the contrast read from the screenshot was compared with the contrast computed from the page's CSS colours:

| Text | From CSS | From the screenshot |
|---|---|---|
| Main heading, white on near black | 17.6:1 | 17.6:1 |
| Labels at 58% white | about 6.2:1 | 5.9 to 6.1:1 |
| "IN" and "OUT" at 32% white | about 2.6:1 | 2.54 and 2.55:1 |

The last row is a real finding: PixelShift's "IN" and "OUT" labels are under half the contrast WCAG asks for. On the portfolio, the screenshot showed what the page's words could not: for the first seconds, a loading screen covers every link that the page reports as visible. A local arriving then now sees nothing to tap, and waits, as a person would.

## Where it goes

- **The local's screen.** Unseen controls are dropped; faint and low contrast ones are marked; on a laptop, what catches the eye first is named.
- **Their take.** The expert remarks get two more measured facts: how many controls fall below WCAG's contrast, with the faintest, and what colour and brightness pull the eye to first. A software engineer's take can now cite them.
- **Tests.** `tests/test_eyes.py` checks the ratio against WCAG's formula (#777 on white is 4.48:1), pictures, covered controls, faint lines in bright cards and the laptop ranking.

## What it cannot see

- A picture's own text (a banner image with words in it) is not read; that is the vision model's job, and it is only asked about icons today.
- Glare, a cracked screen or a smudge: the screenshot is clean, the person's screen is not. A site engineer in the sun loses contrast the screenshot never shows `[G]`.
- Motion. One screenshot per step cannot see an animation that draws the eye.

## Open questions

1. How much does sunlight on a phone cut the contrast a person sees, by how much, for a local outdoors?
2. Does the laptop ranking change where locals go, and does it bring them closer to people? (Testable with the Android in the Wild score's method, on desktop screens.)

## Sources

1. W3C, *Understanding Success Criterion 1.4.3: Contrast (Minimum)* and *1.4.11: Non-text Contrast*, WCAG 2.2. [w3.org](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
2. Still and Masciocchi, *A saliency model predicts fixations in web interfaces*, 2010, as described by Shen and Zhao, *Webpage Saliency*, ECCV 2014. [PDF](https://www-users.cse.umn.edu/~qzhao/publications/pdf/webpage_eccv14.pdf)
3. Leiva, Tavakoli, Oulasvirta and others, eye tracking of mobile app screens, MobileHCI 2020; [Aalto University summary](https://aalto.fi/en/news/how-mobile-apps-grab-our-attention).
