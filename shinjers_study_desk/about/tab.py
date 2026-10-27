"""
The About tab: what the add-on does, a quick start, the version, and links
for help. The words are in web/js/about.js; this only sends the version and
opens links in the browser.
"""

from __future__ import annotations

from aqt.utils import openLink

from ..tab import Tab

# Bump this (and "human_version" in manifest.json) for every release.
VERSION = "1.0.0"
REPO = "https://github.com/shinjer-li/shinjers-anki-study-desk"
# The number AnkiWeb gives the add-on after the first upload. None hides the
# "Rate it" link and the install code.
ANKIWEB_ID: int | None = None

LINKS = {
    "github": REPO,
    "issues": f"{REPO}/issues/new/choose",
    "changes": f"{REPO}/blob/main/CHANGELOG.md",
    "ankiweb": f"https://ankiweb.net/shared/info/{ANKIWEB_ID}" if ANKIWEB_ID else "",
}


class AboutTab(Tab):
    id = "about"
    title = "About"
    icon = "info"

    def data(self, desk) -> dict:
        return {
            "version": VERSION,
            "ankiweb_id": ANKIWEB_ID,
            "links": [k for k, url in LINKS.items() if url],
        }

    def handle(self, desk, cmd, arg) -> None:
        if cmd == "link" and LINKS.get(arg):
            openLink(LINKS[arg])
