# A year in the town

The same app meets a different person on a different day. A food stall counter on Diwali night, a fabricator during a monsoon downpour and an advocate in court vacation are not the people they are on a quiet Tuesday in February. This study is what lets a local's day depend on the date, for any date in one year.

**Status:** first version, built from public calendars and published studies. The year modelled is **2026** in **Mumbai**, where the first real users of our apps live. Every effect on a job is tagged like the profiles (`[D]` data, `[A]` first hand account, `[P]` from our apps, `[G]` guess).

## The rule that comes first

**Festivals change the city, never a person's faith.** A festival changes crowds, closures, traffic, noise and how busy a job is. It never assigns a religion or a practice to a local, and a local's name never decides what they observe. Assigning faith from names is exactly the flattening the persona research warns about ([study](README.md#what-the-research-on-ai-personas-says)).

## What changes across a year

### The week
- Sunday: courts and most offices are closed `[D]`; the fabrication shop keeps shorter Sunday hours, 10 to 5 instead of 9 to 7 `[P]`.
- Weekend nights are busier at food stalls `[G]`.

### Public holidays, Maharashtra 2026
The state notified 24 public holidays for 2026, plus Bhaubeej for state offices `[D]`. Islamic holidays can move by a day with the moon sighting `[D]`.

| Date | Holiday | Date | Holiday |
|---|---|---|---|
| 26 Jan | Republic Day | 28 May | Bakri Id |
| 15 Feb | Mahashivratri | 26 Jun | Muharram |
| 19 Feb | Chhatrapati Shivaji Maharaj Jayanti | 15 Aug | Independence Day, Parsi New Year |
| 3 Mar | Holi | 26 Aug | Id-e-Milad |
| 19 Mar | Gudhi Padwa | 14 Sep | Ganesh Chaturthi |
| 21 Mar | Ramzan Id | 2 Oct | Gandhi Jayanti |
| 26 Mar | Ram Navami | 20 Oct | Dasara |
| 31 Mar | Mahavir Janmakalyanak | 8 Nov | Diwali, Laxmi Pujan |
| 3 Apr | Good Friday | 10 Nov | Diwali, Bali Pratipada |
| 14 Apr | Dr. Babasaheb Ambedkar Jayanti | 11 Nov | Bhaubeej |
| 1 May | Maharashtra Din, Buddha Pournima | 24 Nov | Guru Nanak Jayanti |
| | | 25 Dec | Christmas |

### Festival seasons
A holiday is one day; the city feels a festival for longer. Anchor dates come from the list above `[D]`; the length of each season is `[G]` until confirmed.

| Season | 2026 | What the city feels |
|---|---|---|
| Ramzan | 19 Feb to 20 Mar | Busy late evenings and food streets after sunset `[G]` |
| Holi | 2 to 3 Mar | Colour on the streets, a holiday mood `[G]` |
| Ganeshotsav | 14 to 24 Sep | Pandals, processions, music, traffic jams, crowded evenings `[G]` |
| Navratri | 11 to 19 Oct | Garba nights, crowded evenings `[G]` |
| Diwali | 6 to 11 Nov | Lights, shopping crowds, renovation finished before the festival `[G]` |
| Christmas and New Year | 24 to 31 Dec | Party nights, year end quiet in offices `[G]` |

### Monsoon
- The normal onset over Mumbai is around 10 to 11 June `[D]`, and the normal withdrawal around 8 to 10 October `[D]`. Years vary widely: in 2025 it arrived on 26 May `[D]`; in 2020 it left on 28 October `[D]`.
- July is the heaviest month, and heavy rain days flood roads and stop trains `[G]`.
- In the model, each monsoon day has a chance of rain and of heavy rain, fixed by the date so the same day always has the same weather.

### Courts
- Bombay High Court 2026: summer vacation 11 May to 7 June, Diwali vacation 6 to 18 November, Christmas vacation 25 December to 3 January `[D]` (from a published copy of the court calendar).
- District court vacations in Maharashtra were not found and may differ `[G]`.

### Money and work calendars
- The financial year ends on 31 March: in-house teams and firms close deals and contracts before it `[G]`.
- Wedding season, roughly November to February, matters most to the media family to come `[G]`.

### A pandemic
Modelled on the 2020 lockdown, as a switch rather than a date:
- Courts were fully closed for about two months, then moved to video hearings; many district courts struggled with them for months `[D]`.
- Street vendors had to stop working, and many switched to selling fruit and vegetables within limited hours `[D]`; revenue, customers and working hours dropped sharply `[D]`.
- Offices moved to working from home `[G]`; everyone was home, so networks were slower `[G]`.

Two phases: **lockdown** (closed, at home, anxious, slow network) and **reopening** (masks, limited hours, queues).

## How a date becomes a local's day

1. **The date** gives a weekday, any public holiday, festival season, court vacation, money period and season, and rain fixed by the date.
2. **Effects** in [year/effects.toml](../year/effects.toml) say what each of those does to each job: a sentence about the day, sometimes a different place, and changes to the local's limits (patience, reading, slips).
3. **The local** gets a "Today" paragraph in their situation, and their limits are changed by code, never by asking the model to imagine being rushed.

## Open questions

1. Which district courts in Thane district close on which Saturdays, and for which vacations?
2. Does the fabrication shop close for Diwali, or is it the busiest week?
3. Does the food stall stay open during Ganeshotsav nights, and how much busier is it?
4. How did the fabrication business run during the 2020 lockdown?
5. On heavy rain days, does anyone still go to sites or stalls?

## Sources

- Maharashtra 2026 public holidays, General Administration Department notification, as listed by [Keka](https://www.keka.com/compliance/public-holiday/maharashtra) and [Sakshi Post](https://www.sakshipost.com/news/education/maharashtra-2026-public-holiday-calendar-out-24-festive-and-national-holidays).
- Bombay High Court calendar 2026, [published copy](https://ebc.co.in/wp-content/uploads/2026/01/HC_Bombay_Cal2026.pdf).
- IMD normal monsoon dates: [Mausam journal](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/33); withdrawal 2025, [IMD press release](https://mausam.imd.gov.in/Forecast/mcmarq/mcmarq_data/Press%20release%20dated%2010.10.2025%20on%20Withdrawal%20of%20Southwest%20Monsoon%202025.pdf); [Free Press Journal](https://www.freepressjournal.in/mumbai/monsoon-officially-withdraws-from-mumbai).
- Street vendors in Maharashtra during the lockdown, [International Journal of Community Medicine and Public Health](https://www.ijcmph.com/index.php/ijcmph/article/view/8851).
- Courts during COVID-19, [The Leaflet](https://theleaflet.in/analysis/covid-19-did-indias-courts-run-just-to-stay-where-they-are) and [iPleaders](https://blog.ipleaders.in/indian-legal-system-and-access-to-justice-during-covid-19/).
