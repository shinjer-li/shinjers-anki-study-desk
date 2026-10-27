"""
Screenshots for the README and AnkiWeb, drawn from the add-on's real page
(web/) with the sample data from tools/sample_data.py. Run that first.

Needs Playwright with Chromium (pip install playwright; playwright install chromium):
    python tools/screenshots.py            # writes docs/screenshots/*.png
"""

import json
import os
import re

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ADDON = os.path.join(ROOT, "shinjers_study_desk")
WEB = os.path.join(ADDON, "web")
OUT = os.path.join(ROOT, "docs", "screenshots")
SAMPLE = os.path.join(HERE, "out", "sample.json")

# (file name, tab, mode, theme, what to do on the page first)
SHOTS = [
    ("study-day", "study_day", "light", "slate", None),
    ("study-day-dark", "study_day", "dark", "slate", None),
    ("trouble-spots", "trouble", "light", "slate", None),
    ("keyboard", "keyboard", "light", "slate", None),
    ("settings-dark", "settings", "dark", "navy", None),
    ("about", "about", "light", "slate", None),
]
SIZE = {"width": 1360, "height": 860}


def assets() -> dict:
    """window.ASSETS, read from window.py so the page loads what Anki loads."""
    with open(os.path.join(ADDON, "window.py"), encoding="utf-8") as f:
        src = f.read()
    return {kind: re.findall(r'"(\w+)"', re.search(rf'"{kind}": \[([^\]]*)\]', src).group(1))
            for kind in ("css", "js")}


def page_html(mode: str, theme: str) -> str:
    with open(os.path.join(WEB, "index.html"), encoding="utf-8") as f:
        body = f.read().replace("{base}", "web")
    a = assets()
    css = "".join(f'<link rel="stylesheet" href="web/css/{n}.css">' for n in a["css"])
    js = "".join(f'<script src="web/js/{n}.js"></script>' for n in a["js"])
    dark = ' data-dark="1"' if mode == "dark" else ""
    return (f'<!doctype html><html data-theme="{theme}"{dark}><head><meta charset="utf-8">'
            f"{css}{js}</head><body>{body}</body></html>")


DECKS_SCREEN = """<!doctype html><html><head><meta charset="utf-8"><style>
body { margin: 0; font: 13px/1.4 system-ui, sans-serif; background: #f5f5f5; color: #222; }
.top { display: flex; justify-content: center; gap: 22px; padding: 9px; background: #e9e9e9;
  border-bottom: 1px solid #d6d6d6; }
.top a { color: #222; text-decoration: none; }
.top a.sd { color: #0b5d57; font-weight: 600; }
table { margin: 14px auto 0; border-collapse: collapse; min-width: 420px; }
th { text-align: right; font-weight: 600; color: #555; padding: 4px 14px; }
th:first-child, td:first-child { text-align: left; }
td { padding: 5px 14px; text-align: right; }
.due { color: #2e7d32; } .new { color: #1565c0; }
</style></head><body>
<div class="top"><a>Decks</a><a>Add</a><a>Browse</a><a>Stats</a><a>Sync</a>
<a class="sd">Shinjer's Study Desk</a></div>
%s
<table><tr><th>Deck</th><th>New</th><th>Due</th></tr>
<tr><td>AnKing Step 1</td><td class="new">20</td><td class="due">186</td></tr>
<tr><td>Default</td><td>0</td><td>0</td></tr></table>
</body></html>"""


def status_bar(page, sample: dict, harness: str) -> None:
    """The status bar on a stand-in for Anki's Decks screen."""
    bar = re.sub(r"/_addons/[^/]+/web", "web", sample["banner"])
    with open(harness, "w", encoding="utf-8") as f:
        f.write(DECKS_SCREEN % bar)
    page.set_viewport_size({"width": 1000, "height": 240})
    page.goto("file://" + harness)
    page.wait_for_timeout(300)
    path = os.path.join(OUT, "status-bar.png")
    page.screenshot(path=path)
    page.set_viewport_size(SIZE)
    print(os.path.relpath(path, ROOT))


def main() -> None:
    with open(SAMPLE, encoding="utf-8") as f:
        sample = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    harness = os.path.join(ADDON, "_screenshot.html")  # next to web/, so relative paths work
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport=SIZE, device_scale_factor=2)
            for name, tab, mode, theme, action in SHOTS:
                with open(harness, "w", encoding="utf-8") as f:
                    f.write(page_html(mode, theme))
                page.goto("file://" + harness)
                boot = {"tabs": sample["tabs"], "active": tab,
                        "appearance": {"mode": mode, "theme": theme}, "night": mode == "dark"}
                page.evaluate("([boot, id, data]) => { desk.boot(boot); desk.receive(id, data); }",
                              [boot, tab, sample["data"][tab]])
                if action:
                    action(page)
                page.wait_for_timeout(300)
                path = os.path.join(OUT, f"{name}.png")
                page.screenshot(path=path)
                print(os.path.relpath(path, ROOT))
            status_bar(page, sample, harness)
            browser.close()
    finally:
        if os.path.exists(harness):
            os.remove(harness)


if __name__ == "__main__":
    main()
