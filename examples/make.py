"""Builds the example talks: the same subject told two ways, as PowerPoint decks with speaker notes.

python examples/make.py
"""
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent

# Offline support for an order app, told the way an engineer tells it to other engineers.
TECHNICAL = [
    ("Offline first architecture for the order app",
     ["Service Worker based caching layer", "IndexedDB persistence", "Background Sync replay queue"],
     "Today I will walk through the offline first architecture we are proposing for the order app. The core of it is a "
     "Service Worker based caching layer, IndexedDB for persistence, and a Background Sync replay queue for writes."),
    ("Service Worker lifecycle",
     ["Install: precache the app shell from the Workbox manifest", "Activate: purge stale caches by revision hash",
      "Fetch: route requests through runtime caching strategies", "skipWaiting and clientsClaim for immediate control"],
     "The Service Worker lifecycle has three phases. On install we precache the app shell using the Workbox precache "
     "manifest. On activate we purge stale caches keyed by revision hash. On fetch we route each request through a runtime "
     "caching strategy. We call skipWaiting and clientsClaim so the new worker takes control immediately."),
    ("Caching strategies by route",
     ["Static assets: CacheFirst with a 30 day TTL and max entries", "API GET: StaleWhileRevalidate with ETag validation",
      "Navigation: NetworkFirst with a 3 second timeout, fallback to the shell", "Opaque responses excluded from quota accounting"],
     "Static assets use CacheFirst with a thirty day TTL and a max entries limit. API GETs use StaleWhileRevalidate with ETag "
     "validation, so the UI renders from cache and revalidates in the background. Navigations use NetworkFirst with a three "
     "second timeout and fall back to the cached shell. Opaque responses are excluded because of quota accounting."),
    ("Persistence with IndexedDB",
     ["Dexie wrapper over IndexedDB, schema versioned", "Orders store keyed by client generated UUIDv7",
      "Compound indexes on status and updatedAt", "Storage persistence requested via navigator.storage.persist"],
     "For persistence we wrap IndexedDB with Dexie and version the schema. Orders are keyed by a client generated UUID "
     "version seven so they sort by time and never collide. We add compound indexes on status and updatedAt, and request "
     "persistent storage through navigator storage persist so the browser does not evict us under pressure."),
    ("Write path: the replay queue",
     ["Mutations enqueued as idempotent commands", "Background Sync tag triggers replay on reconnect",
      "Exponential backoff with jitter, max 5 retries", "Server side idempotency keys dedupe replays"],
     "Writes go through a replay queue. Every mutation is enqueued as an idempotent command. A Background Sync tag triggers "
     "replay when connectivity returns, with exponential backoff and jitter, up to five retries. On the server, idempotency "
     "keys dedupe any replays so an order is never created twice."),
    ("Conflict resolution",
     ["Last writer wins on scalar fields", "Field level merge for line items", "Vector clocks considered, rejected for complexity",
      "Conflicts surfaced to the client via a 409 with the server version"],
     "For conflicts we use last writer wins on scalar fields and a field level merge for line items. We considered vector "
     "clocks but rejected them for complexity. When a merge is impossible the server returns a 409 with its version and the "
     "client reconciles."),
    ("Performance impact",
     ["LCP from 3.1 s to 1.2 s on repeat visits", "TTI improved 41 percent on a throttled 3G profile",
      "Cache hit ratio 87 percent in the staging soak test", "Bundle size unchanged after tree shaking"],
     "In staging, largest contentful paint on repeat visits went from 3.1 seconds to 1.2. Time to interactive improved 41 "
     "percent on a throttled 3G profile, and the cache hit ratio in our soak test was 87 percent. Bundle size is unchanged "
     "after tree shaking."),
    ("Next steps",
     ["Two sprints: SW and caching, then the replay queue", "Feature flag rollout to 10 percent", "Monitoring via RUM and Sentry breadcrumbs"],
     "The plan is two sprints, the Service Worker and caching first, then the replay queue. We roll it out behind a feature "
     "flag to ten percent of users, and monitor it with real user monitoring and Sentry breadcrumbs."),
]

# The same subject, told to people who use the app.
HOOKED = [
    ("When the network drops, the order should not",
     ["Our app should keep working without the internet"],
     "Last month, a fabrication shop owner in Vasai was taking an order in a customer's basement. The signal dropped, the app "
     "showed a blank screen, and he lost the whole order. He wrote it on his hand instead. My point today is simple: our app "
     "should keep working without the internet, and catch up by itself when the signal comes back."),
    ("How often does this happen to you?",
     ["Basements, lifts, trains, building sites"],
     "Quick question for all of you. Raise your hand if a form on your phone has ever lost what you typed because the network "
     "dropped. Almost everyone. It happens in basements, in lifts, on the train, on building sites. For the people who use our "
     "app, it happens every single day."),
    ("What we would change",
     ["The app opens without signal", "Orders are saved on the phone first", "They send themselves when signal returns"],
     "So here is what we would change, in three parts. One, the app opens even with no signal, because it keeps a copy of "
     "itself on the phone. Two, every order is saved on the phone first, the moment you tap save. Three, when the signal comes "
     "back, the orders send themselves. Nobody has to remember to do anything."),
    ("Watch",
     ["Airplane mode on", "Take an order", "Airplane mode off"],
     "Let me show you. I switch on airplane mode. No signal at all. I open the app, and it opens. I take an order for a steel "
     "gate, and tap save. It says saved on this phone. Now I switch airplane mode off, and in a few seconds, there, it says "
     "sent. The order is in the shop's list."),
    ("What it means for the shop",
     ["No lost orders", "Pages open in about a second"],
     "For the shop, it means no lost orders. And because the app keeps a copy of itself on the phone, pages open in about a "
     "second instead of three, even on a weak signal. In our test, that was the difference people noticed first."),
    ("What could go wrong",
     ["Two people change the same order", "The newer change wins, and you see both"],
     "What could go wrong? Two people might change the same order while one of them has no signal. When that happens, the "
     "newer change wins, and the app shows both versions so nothing is lost silently."),
    ("What we need",
     ["Two developers, four weeks", "Try it with ten percent of shops first"],
     "What we need is two developers for four weeks. We would try it with one in ten shops first, watch it closely, and then "
     "give it to everyone."),
    ("The order should not drop",
     ["Keeps working without signal", "Catches up by itself"],
     "So, back to the shop owner in that basement. With this, his order would have been saved on his phone and sent the "
     "moment he walked up the stairs. The network will keep dropping. The order should not."),
]


def build(slides, path):
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    for title, bullets, notes in slides:
        slide = deck.slides.add_slide(deck.slide_layouts[1])
        slide.shapes.title.text = title
        slide.shapes.title.text_frame.paragraphs[0].runs[0].font.size = Pt(36)
        body = slide.placeholders[1].text_frame
        for i, b in enumerate(bullets):
            p = body.paragraphs[0] if i == 0 else body.add_paragraph()
            p.text = b
            p.runs[0].font.size = Pt(20 if slides is TECHNICAL else 28)
        slide.notes_slide.notes_text_frame.text = notes
    deck.save(path)


if __name__ == "__main__":
    build(TECHNICAL, HERE / "offline-technical.pptx")
    build(HOOKED, HERE / "offline-for-people.pptx")
    print("Wrote offline-technical.pptx and offline-for-people.pptx")
