"""Eyes and hands for web apps: a real Chrome, driven by Playwright."""
import json
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

PHONE = dict(viewport={"width": 393, "height": 852}, device_scale_factor=2, is_mobile=True, has_touch=True,
             user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/130.0 Mobile Safari/537.36")
LAPTOP = dict(viewport={"width": 1366, "height": 768})

# Collects what a sighted person could see and use: visible controls by their visible words,
# plus readable text that sits outside any control. Icon only buttons keep their hint separately.
SEE = """() => {
  const visible = el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05
      && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth; };
  const CONTROLS = 'a[href],button,input,select,textarea,[role=button],[role=link],[role=checkbox],[role=tab],[role=menuitem],[role=switch],[contenteditable=true]';
  // Open shadow roots too (web components, an extension's panel): a person sees them like the rest of the page.
  const deep = (sel, root = document, out = []) => { out.push(...root.querySelectorAll(sel));
    for (const h of root.querySelectorAll('*')) if (h.shadowRoot) deep(sel, h.shadowRoot, out); return out; };
  deep('[data-local-id]').forEach(e => e.removeAttribute('data-local-id'));
  // Letters, not numbers: a small model reads "product-1.png" as [1] if the labels are numbers.
  const code = i => { let s = ''; for (i += 1; i > 0; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + (i - 1) % 26) + s; return s; };
  // Each run of text inside a control, with its own box and size, so its contrast can be measured on the screenshot.
  const runs = el => { const out = [], walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let t; (t = walk.nextNode()) && out.length < 12; ) {
      const words = t.textContent.trim(), p = t.parentElement; if (!words || !visible(p)) continue;
      const range = document.createRange(); range.selectNodeContents(t); const b = range.getBoundingClientRect();
      if (b.width < 2 || b.height < 2) continue; const st = getComputedStyle(p);
      out.push({ text: words.slice(0, 80), x0: Math.round(b.left), y0: Math.round(b.top), x1: Math.round(b.right), y1: Math.round(b.bottom),
        font: parseFloat(st.fontSize) || 0, weight: parseInt(st.fontWeight) || 400 }); }
    return out; };
  const items = []; let n = 0;
  for (const el of deep(CONTROLS)) {
    if (!visible(el)) continue;
    const tag = el.tagName.toLowerCase(), type = (el.type || '').toLowerCase();
    let role = el.getAttribute('role') || {a: 'link', button: 'button', select: 'dropdown', textarea: 'text box'}[tag];
    if (tag === 'input') role = {checkbox: 'checkbox', radio: 'radio', range: 'slider', file: 'file picker', submit: 'button', button: 'button'}[type] || 'text box';
    // A big card that is one button shows several lines; a person glances at each line, not one long label.
    const lines = (el.innerText || (type === 'submit' || type === 'button' ? el.value : '') || '')
      .split('\\n').map(s => s.trim().replace(/\\s+/g, ' ')).filter(Boolean);
    const text = lines.join(' ');
    let hint = el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('placeholder') || '';
    if (!hint && el.labels && el.labels.length) hint = el.labels[0].innerText.trim();
    // A field with no label of its own: a sighted person reads the words just above it, as in a card with a question.
    let near = '';
    if (['text box', 'dropdown', 'checkbox', 'radio', 'slider'].includes(role) && !(el.labels && el.labels.length)) {
      for (let n = el, up = 0; n && up < 3 && !near; n = n.parentElement, up++)
        for (let p = n.previousElementSibling; p && !near; p = p.previousElementSibling) {
          const t = (p.innerText || '').trim().replace(/\\s+/g, ' ');
          if (t && t.length <= 120 && visible(p)) near = t; }
    }
    const r = el.getBoundingClientRect(); const id = code(n++);
    el.setAttribute('data-local-id', id);
    items.push({ id, role, text: text.slice(0, 300), lines: lines.slice(0, 10).map(s => s.slice(0, 200)), hint: hint.slice(0, 160), disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      active: el.classList.contains('active') || el.getAttribute('aria-pressed') === 'true' || el.getAttribute('aria-selected') === 'true',
      checked: el.checked === true, value: (role === 'slider' || role === 'text box') ? String(el.value || '') : '',
      x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), w: Math.round(r.width), h: Math.round(r.height),
      font: parseFloat(getComputedStyle(el).fontSize) || 0, weight: parseInt(getComputedStyle(el).fontWeight) || 400, runs: runs(el),
      near: near.slice(0, 120) });
  }
  const blocks = [];
  for (const el of deep('h1,h2,h3,h4,p,li,dt,dd,label,figcaption,[role=alert],[role=status],output')) {
    if (!visible(el) || el.closest(CONTROLS)) continue;
    const t = el.innerText.trim().replace(/\\s+/g, ' ');
    if (t) blocks.push(t.slice(0, 400));
  }
  const H = document.documentElement.scrollHeight;
  return { items, blocks: [...new Set(blocks)].slice(0, 30), title: document.title, url: location.href,
    scrollable: H > innerHeight + 5, at_bottom: scrollY + innerHeight >= H - 5 };
}"""


# Expert eyes: what a software engineer would see in the browser's tools, collected while the local works.
VITALS = """(() => { const v = window.__localsVitals = { lcp: null, cls: 0 };
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) v.lcp = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true }); } catch (_) {}
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) v.cls += e.value; }).observe({ type: 'layout-shift', buffered: true }); } catch (_) {}
})();"""
VITALS_READ = """() => { const v = window.__localsVitals || {}, n = performance.getEntriesByType('navigation')[0];
  const bytes = [...performance.getEntriesByType('resource'), n].filter(Boolean).reduce((s, e) => s + (e.transferSize || 0), 0);
  return { lcp: v.lcp, cls: v.cls, bytes, url: location.href }; }"""


# Links that leave the browser on a phone: the dialler, an SMS, WhatsApp. Tapping one is where a site hands over to a
# call; the run records it and does not follow it.
CALLS = ("tel:", "sms:", "whatsapp:", "https://wa.me/", "https://api.whatsapp.com/")
HREF = "e => { const a = e.closest('a'); return a ? [a.href, a.target] : ['', '']; }"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Web:
    def __init__(self, task, device, files, out_dir, watch=False):
        self.task, self.url, self.device, self.files, self.out = task, task.url, device, [str(f) for f in files], Path(out_dir)
        self.watch = watch
        self.slow_mo = 250 if watch else 0  # slowed down so you can follow a local; a person's own hands need none
        self.downloads, self._pending, self.picked_files, self.called = [], [], 0, []
        self.popups = []  # messages the page popped up (alert, confirm) that they read and closed
        self.seen = {"console": [], "errors": [], "failed": [], "uploads": []}
        self._server = self._browser = self.worker = self._profile = None

    def __enter__(self):
        self._pw = sync_playwright().start()
        screen = dict(accept_downloads=True, **(PHONE if self.device == "phone" else LAPTOP))
        ext = getattr(self.task, "extension", None)
        if ext:
            # Chrome no longer loads an extension from the command line, so it is loaded over the DevTools protocol, the
            # way Fill.ai's own tests do. A fresh profile each run: every local starts with it as just installed.
            self._profile = tempfile.TemporaryDirectory(prefix="locals-")
            self._ctx = self._pw.chromium.launch_persistent_context(
                self._profile.name, channel="chrome", headless=not self.watch, slow_mo=self.slow_mo,
                args=["--enable-unsafe-extension-debugging"], ignore_default_args=["--disable-extensions"], **screen)
            self._ctx.browser.new_browser_cdp_session().send("Extensions.loadUnpacked", {"path": str(ext)})
            self.worker = (self._ctx.service_workers[0] if self._ctx.service_workers
                           else self._ctx.wait_for_event("serviceworker", timeout=20000))
            seed = getattr(self.task, "seed", None)
            if seed:  # what the extension already knows, as if it was set up before the task
                self.worker.evaluate("async d => { await chrome.storage.local.clear(); await chrome.storage.local.set(d); }",
                                     json.loads(Path(seed).read_text(encoding="utf-8")))
            self.page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
            for extra in self._ctx.pages[1:]:
                extra.close()
        else:
            self._browser = self._pw.chromium.launch(channel="chrome", headless=not self.watch, slow_mo=self.slow_mo)
            self._ctx = self._browser.new_context(**screen)
            self.page = self._ctx.new_page()
        self._hook(self.page)
        self._ctx.on("page", self._new_tab)
        serve = getattr(self.task, "serve", None)
        if self.url.startswith("extension:") and self.worker:  # one of the extension's own pages, like its settings
            self.url = f"chrome-extension://{urlparse(self.worker.url).netloc}/{self.url.removeprefix('extension:').lstrip('/')}"
        elif serve:  # pages that come with the task, served on this machine only
            self._server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(serve)))
            threading.Thread(target=self._server.serve_forever, daemon=True).start()
            self.url = f"http://127.0.0.1:{self._server.server_address[1]}/{self.url.lstrip('/')}"
        self.page.goto(self.url, wait_until="networkidle")
        return self

    def _hook(self, page):
        page.on("filechooser", self._choose)
        page.on("download", lambda d: self._pending.append(d))
        page.add_init_script(VITALS)
        page.on("console", lambda m: m.type == "error" and self.seen["console"].append(m.text[:200]))
        page.on("pageerror", lambda e: self.seen["errors"].append(str(e)[:200]))
        page.on("requestfailed", lambda r: self.seen["failed"].append({"url": r.url[:200], "why": str(r.failure or "")[:80]}))
        page.on("response", lambda r: r.status >= 400 and self.seen["failed"].append({"url": r.url[:200], "why": f"HTTP {r.status}"}))
        page.on("request", self._request)
        page.on("dialog", self._dialog)

    def _dialog(self, dialog):
        """A pop up message: a person reads it and taps OK, so the local reads it on their next screen."""
        self.popups.append(" ".join(dialog.message.split())[:300])
        try:
            dialog.accept()
        except Exception:
            pass

    def _new_tab(self, page):
        """A link that opens in a new tab: the person is now looking at that tab."""
        if page is self.page:
            return
        self._hook(page)
        self.page = page
        try:
            page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass

    def _request(self, r):
        """Remembers any request that carries a file or a large body off the device."""
        if r.method not in ("POST", "PUT", "PATCH"):
            return
        try:
            size = len(r.post_data_buffer or b"")
        except Exception:
            size = 0
        if size > 20_000:
            self.seen["uploads"].append({"host": urlparse(r.url).netloc, "bytes": size})

    def observe(self):
        """Everything the expert eyes collected, read before the browser closes."""
        try:
            vitals = self.page.evaluate(VITALS_READ)
        except Exception:
            vitals = {}
        return {"platform": "web", **self.seen, **vitals}

    def __exit__(self, *exc):
        (self._browser or self._ctx).close()
        self._pw.stop()
        if self._server:
            self._server.shutdown()
        if self._profile:
            self._profile.cleanup()

    def _choose(self, chooser):
        # The local's phone gallery holds exactly the files the task gave them.
        chooser.set_files(self.files)
        self.picked_files += 1

    def see(self):
        screen = self.page.evaluate(SEE)
        if self.popups:
            screen["blocks"] = [f'A message popped up and they tapped OK: "{m}"' for m in self.popups] + screen["blocks"]
            self.popups = []
        name = getattr(self.task, "toolbar", None)
        if name and self.worker:
            # The extension's button sits in the browser's toolbar, outside the page; a person who installed it knows it.
            from .android import code
            w = (PHONE if self.device == "phone" else LAPTOP)["viewport"]["width"]
            screen["items"].append({"id": code(len(screen["items"])), "role": "browser toolbar button", "text": name,
                                    "lines": [name], "hint": "", "disabled": False, "active": False, "checked": False,
                                    "value": "", "x": w - 60, "y": -40, "w": 28, "h": 28, "toolbar": True})
        return screen

    def box_of(self, item):
        """A control's box, or a run of text's (x0..y1), in the screenshot's pixels (town/pixels.py): CSS pixels times
        the screen's density."""
        s = PHONE["device_scale_factor"] if self.device == "phone" else 1
        if "x0" in item:
            return item["x0"] * s, item["y0"] * s, item["x1"] * s, item["y1"] * s
        return ((item["x"] - item["w"] / 2) * s, (item["y"] - item["h"] / 2) * s,
                (item["x"] + item["w"] / 2) * s, (item["y"] + item["h"] / 2) * s)

    def settle(self):
        self.page.wait_for_timeout(700)
        try:
            self.page.wait_for_load_state("networkidle", timeout=4000)
        except Exception:
            pass
        self.collect()

    def collect(self):
        """Saves the downloads that have arrived on the device."""
        while self._pending:
            d = self._pending.pop(0)
            path = self.out / d.suggested_filename
            d.save_as(path)
            self.downloads.append(path)

    def act(self, action, target=None, text=""):
        el = self.page.locator(f'[data-local-id="{target}"]') if target is not None else None
        try:
            if action in ("tap", "set") and el is not None and el.count() == 0 and getattr(self.task, "toolbar", None):
                # The toolbar button: the extension opens itself on this page, as its own button does.
                self.worker.evaluate(f"u => globalThis.{self.task.toolbar_call}(u)", self.page.url)
                self.page.wait_for_timeout(1500)
                self.settle()
                return "ok"
            href, opens = el.evaluate(HREF, timeout=4000) if action == "tap" and el is not None else ("", "")
            if href.startswith(CALLS):
                self.called.append(href)
                self.settle()
                return "their phone opened " + ("the dialler" if href.startswith("tel:") else "a chat")
            if action == "tap" and opens == "_blank":
                # A link that opens a new tab: wait for it, so they are looking at it before anything is checked.
                with self._ctx.expect_page(timeout=8000) as tab:
                    el.click(timeout=4000)
                self._new_tab(tab.value)
            elif action == "tap":
                el.click(timeout=4000)
            elif action == "type":
                el.fill(text, timeout=4000)
            elif action == "set":
                tag = el.evaluate("e => e.tagName")
                if tag == "SELECT":
                    el.select_option(label=text, timeout=4000)
                elif tag not in ("INPUT", "TEXTAREA"):
                    el.click(timeout=4000)  # "setting" a button means pressing it
                else:
                    el.evaluate("(e, v) => { e.value = v; e.dispatchEvent(new Event('input', {bubbles: true}));"
                                " e.dispatchEvent(new Event('change', {bubbles: true})); }", text)
            elif action == "scroll":
                self.page.evaluate("window.scrollBy(0, innerHeight * 0.8)")
            elif action == "back":
                self.page.go_back(timeout=4000)
                if self.page.url == "about:blank":
                    # Back from the first page leaves the site; a run keeps them on it and tells them so.
                    self.page.go_forward(timeout=8000)
                    self.settle()
                    return "this was the first page, so back would only leave the site; they are still on it"
            elif action == "wait":
                self.page.wait_for_timeout(2000)
            result = "ok"
        except Exception as e:
            result = f"nothing happened ({type(e).__name__})"
        self.settle()
        return result

    def snapshot(self, path):
        self.page.screenshot(path=str(path))

    def text(self):
        return self.page.inner_text("body", timeout=2000)

    def knows(self, path):
        """A value from the extension's storage by a dotted path (for the "extension_has" check), or None."""
        if not self.worker:
            return None
        try:
            return self.worker.evaluate("""async path => { const [key, ...rest] = path.split('.');
              let v = (await chrome.storage.local.get(key))[key];
              for (const k of rest) v = v == null ? v : v[k];
              return v ?? null; }""", path)
        except Exception:
            return None

    def filled(self):
        """How many visible text fields, menus and boxes on the page hold an answer (for the "filled" check)."""
        try:
            return self.page.evaluate("""() => [...document.querySelectorAll('input,select,textarea')].filter(e => {
              const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false;
              if (['checkbox', 'radio'].includes(e.type)) return e.checked;
              if (['hidden', 'submit', 'button', 'file', 'password'].includes(e.type)) return false;
              return String(e.value || '').trim() !== ''; }).length""")
        except Exception:
            return 0

    def location(self):
        return self.page.url
