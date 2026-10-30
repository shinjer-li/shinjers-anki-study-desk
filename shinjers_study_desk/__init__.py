"""
Shinjer's Study Desk: one window for your study day, the topics you miss most, and your
keyboard shortcuts. Replaces the Study Day Control, Trouble Spots and Keybind
Remapper add-ons.

Open it from the "Shinjer's Study Desk" link in Anki's top bar, the status bar on the
Decks screen, or Tools > Shinjer's Study Desk.

Layout:
  window.py      the window and the page <-> Python plumbing
  tab.py         what every tab provides (read this to add a tab)
  prefs.py       add-on settings: look, window, keyboard
  study_day/     Study ahead, Freeze, the day's numbers, the Decks status bar
  trouble/       Trouble Spots (read-only analysis of your misses)
  keyboard/      the shortcut remapper, smart undo and card tools
  settings/      the Settings tab
  about/         the About tab (version, quick start, help links)
  web/           the page: index.html, css/, js/
"""

from __future__ import annotations

from aqt import gui_hooks, mw
from aqt.qt import QAction

from . import prefs, window
from .about.tab import AboutTab
from .keyboard import remap
from .keyboard.tab import KeyboardTab
from .settings.tab import SettingsTab
from .study_day import upkeep
from .study_day.tab import StudyDayTab
from .trouble.tab import TroubleTab

# The rail shows tabs in this order (Settings is pinned to the bottom).
TABS = [StudyDayTab(), TroubleTab(), KeyboardTab(), AboutTab(), SettingsTab()]


def add_toolbar_link(links: list[str], toolbar) -> None:
    if not prefs.get()["toolbar_link"]:
        return
    links.append(
        toolbar.create_link(
            "shinjerdesk",
            "Shinjer's Study Desk",
            lambda: window.open_desk(),
            tip="Open Shinjer's Study Desk: your study day, trouble spots and shortcuts",
            id="shinjerdesk",
        )
    )


# Migrate first, so the old add-ons' shortcuts are in place before they're applied.
gui_hooks.profile_did_open.append(prefs.migrate)
window.setup(TABS)
upkeep.setup()
remap.setup()

mw.addonManager.setWebExports(__name__, r"web/.*\.(css|js|png)")
gui_hooks.top_toolbar_did_init_links.append(add_toolbar_link)

action = QAction("Shinjer's Study Desk…", mw)
action.triggered.connect(lambda: window.open_desk())
mw.form.menuTools.addAction(action)

# The "Config" button in Tools > Add-ons opens the Settings tab.
mw.addonManager.setConfigAction(__name__, lambda: window.open_desk("settings"))
