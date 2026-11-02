# Food stall counter

**Status:** draft. Built from what we learned making Order Control for a real Chinese food shop, plus published data. Every `[G]` waits for an interview.

## 1. Snapshot

Takes orders at the counter of a small shop selling Chinese food: fried rice, noodles, Manchurian, chilli chicken, lollipop, soup `[P]`. Most dishes come half or full, rice and noodles plain or Schezwan at the same price, and lollipop by the piece `[P]`. Trade runs past midnight `[P]`. A good night is a rush where nobody waits too long and every plate is paid for. A bad night is a forgotten order, a wrong total, or a customer who walks off without paying `[G]`.

## 2. The day

The shop's day runs from 5 AM to 5 AM in the books, because orders after midnight belong to the night before `[P]`. The timeline below is a draft.

| Time | Where | Doing | Hands and eyes | Phone use | Interruptions |
|---|---|---|---|---|---|
| Afternoon | Shop | Prep: chopping, sauces `[G]` | Wet, oily hands `[G]` | Little `[G]` | Supplier calls `[G]` |
| Early evening | Counter | First orders `[G]` | Taking cash, handing parcels `[G]` | Order board open `[P]` | Customers asking prices `[G]` |
| Night rush | Counter and stove | Several orders at once `[G]` | Heat, noise, steam, greasy screen `[G]` | One tap at a time, no reading `[P]` | Changes to orders, "is mine ready?" `[G]` |
| After midnight | Counter | Last orders, closing `[P]` | Tired `[G]` | Checks the day's takings `[P]` | Late customers `[G]` |

## 3. The week, the month, the year

- Weekends and holidays are busier `[G]`.
- Cricket matches and festivals change the rush `[G]`.

## 4. Tools today

| Tool | What it is good at |
|---|---|
| Memory `[P]` | Knows regulars by face, so orders need no names |
| Shouting to the kitchen `[G]` | Instant |
| Paper slips or a notebook `[G]` | Cheap, no battery |
| UPI QR code and cash `[D]` | How customers pay |
| Order Control `[P]` | One board, one tap per status |

The app competes with memory and shouting. Any extra tap during a rush is a tap too many `[P]`.

## 5. Phone and ability

- Android phone, probably propped up at the counter `[G]`.
- Very fast with numbers and money `[G]`.
- Reads dish names and numbers, skips sentences `[G]`.

## 6. Pressures

- Wait time: an order waiting fifteen minutes is already a problem `[P]`.
- Money: an unpaid order that leaves the board is lost money `[P]`.
- Mistakes under pressure: a wrong tap during a rush must cost nothing `[P]`.

## 7. Their words

| They say | An app might say |
|---|---|
| Half, full `[P]` | Small, large, portion |
| Parcel `[G]` | Takeaway, to go |
| Schezwan `[P]` | Variant, spicy |
| Token number `[P]` | Order ID |
| Ready, paid, done `[P]` | Status |

## 8. Three different people

| | A | B | C |
|---|---|---|---|
| Who | Owner who cooks and takes orders alone | Owner at the counter, one or two cooks | New helper on their first week |
| Phone | Glances between woks | Fast, uses the board all night | Does not know prices yet |
| Biggest need | Fewer taps | Seeing what is waiting and unpaid | Not getting the total wrong |

All three are `[G]` until interviews.

## 9. Task cards

These map to what Order Control does today `[P]`.

| Task | Pressure | Done when |
|---|---|---|
| Take three orders in two minutes while another customer asks a price. | Rush | Three correct orders on the board with the right totals |
| A customer changes half to full after ordering. | Kitchen already started | The order shows full and the total is updated |
| Four pieces of oil fried lollipop. | Customer waiting | Total is 3 pieces at 80 plus 1 extra piece at 40, so 120 |
| A customer says "I already paid". | Queue behind them | The order's paid state is checked and correct |
| At 1 AM: how much did we take today? | Closing up | The total for the business day that started at 5 AM is on screen |
| An order was marked done by mistake. | Rush continues | It is back on the board before the undo disappears |

## 10. Limits in numbers

Not set yet. These come from watching a real person do the task cards during a rush.

## 11. Caricature traps

- **"Small stall staff are slow with technology."** Wrong. They are fast with numbers, money and memory. What they lack is time and clean hands.
- **Reading the screen carefully.** In a rush nobody reads; they glance and tap.
- **Wanting features like loyalty points or customer accounts.** The owner chose to keep customer names out entirely `[P]`.

## 12. Open questions

1. When does the shop open and when is the rush, hour by hour?
2. Who holds the phone: the owner, the cook, a helper?
3. Where is the phone during service, and how clean are hands when tapping it?
4. How many orders at once at the peak?
5. Parcels versus eating at the stall: what share of each?
6. Do customers pay before or after eating?
7. How often do customers change an order after placing it?
8. What went wrong on the worst night so far?
9. Are online delivery apps part of the business?
10. What was used before Order Control, and what was missed?
