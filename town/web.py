"""Eyes and hands for web apps: a real Chrome, driven by Playwright."""
from pathlib import Path

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
  document.querySelectorAll('[data-local-id]').forEach(e => e.removeAttribute('data-local-id'));
  const items = []; let n = 0;
  for (const el of document.querySelectorAll(CONTROLS)) {
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
    const r = el.getBoundingClientRect(); const id = ++n;
    el.setAttribute('data-local-id', id);
    items.push({ id, role, text: text.slice(0, 300), lines: lines.slice(0, 10).map(s => s.slice(0, 200)), hint: hint.slice(0, 160), disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      active: el.classList.contains('active') || el.getAttribute('aria-pressed') === 'true' || el.getAttribute('aria-selected') === 'true',
      checked: el.checked === true, value: (role === 'slider' || role === 'text box') ? String(el.value || '') : '',
      x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) });
  }
  const blocks = [];
  for (const el of document.querySelectorAll('h1,h2,h3,h4,p,li,dt,dd,label,figcaption,[role=alert],[role=status],output')) {
    if (!visible(el) || el.closest(CONTROLS)) continue;
    const t = el.innerText.trim().replace(/\\s+/g, ' ');
    if (t) blocks.push(t.slice(0, 400));
  }
  const H = document.documentElement.scrollHeight;
  return { items, blocks: [...new Set(blocks)].slice(0, 30), title: document.title, url: location.href,
    scrollable: H > innerHeight + 5, at_bottom: scrollY + innerHeight >= H - 5 };
}"""


class Web:
    def __init__(self, url, device, files, out_dir, watch=False):
        self.url, self.device, self.files, self.out = url, device, [str(f) for f in files], Path(out_dir)
        self.watch = watch
        self.downloads, self._pending, self.picked_files = [], [], 0

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(channel="chrome", headless=not self.watch, slow_mo=250 if self.watch else 0)
        ctx = self._browser.new_context(accept_downloads=True, **(PHONE if self.device == "phone" else LAPTOP))
        self.page = ctx.new_page()
        self.page.on("filechooser", self._choose)
        self.page.on("download", lambda d: self._pending.append(d))
        self.page.goto(self.url, wait_until="networkidle")
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def _choose(self, chooser):
        # The local's phone gallery holds exactly the files the task gave them.
        chooser.set_files(self.files)
        self.picked_files += 1

    def see(self):
        return self.page.evaluate(SEE)

    def settle(self):
        self.page.wait_for_timeout(700)
        try:
            self.page.wait_for_load_state("networkidle", timeout=4000)
        except Exception:
            pass
        while self._pending:
            d = self._pending.pop(0)
            path = self.out / d.suggested_filename
            d.save_as(path)
            self.downloads.append(path)

    def act(self, action, target=None, text=""):
        el = self.page.locator(f'[data-local-id="{target}"]') if target is not None else None
        try:
            if action == "tap":
                el.click(timeout=4000)
            elif action == "type":
                el.fill(text, timeout=4000)
            elif action == "set":
                if el.evaluate("e => e.tagName") == "SELECT":
                    el.select_option(label=text, timeout=4000)
                else:
                    el.evaluate("(e, v) => { e.value = v; e.dispatchEvent(new Event('input', {bubbles: true}));"
                                " e.dispatchEvent(new Event('change', {bubbles: true})); }", text)
            elif action == "scroll":
                self.page.evaluate("window.scrollBy(0, innerHeight * 0.8)")
            elif action == "back":
                self.page.go_back(timeout=4000)
            elif action == "wait":
                self.page.wait_for_timeout(2000)
            result = "ok"
        except Exception as e:
            result = f"nothing happened ({type(e).__name__})"
        self.settle()
        return result

    def snapshot(self, path):
        self.page.screenshot(path=str(path))
