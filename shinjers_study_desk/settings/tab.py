"""
The Settings tab. It owns the add-on-wide settings (look, window, toolbar
link) and also shows every other tab's settings() sections, so a new tab's
options appear here without touching this file. Drawn by web/js/settings.js.
"""

from __future__ import annotations

from aqt import mw

from .. import prefs, window
from ..tab import Tab


class SettingsTab(Tab):
    id = "settings"
    title = "Settings"
    icon = "gear"

    def data(self, desk) -> dict:
        sections = self.settings()
        for t in window.tabs():
            if t is not self:
                for section in t.settings():
                    sections.append({**section, "tab": t.id})
        return {
            "appearance": prefs.appearance(),
            "themes": [[k, v] for k, v in prefs.THEMES.items()],
            "sections": sections,
        }

    def handle(self, desk, cmd, arg) -> None:
        # {"tab": owner id, "key": row key, "value": new value}
        if cmd != "set" or not isinstance(arg, dict):
            return
        owner = window.tab(arg.get("tab") or self.id)
        if owner is not None:
            owner.set_setting(desk, str(arg.get("key", "")), arg.get("value"))

    def settings(self) -> list[dict]:
        cfg = prefs.get()
        return [
            {
                "tab": self.id,
                "title": "Window",
                "rows": [
                    {"key": "on_top", "type": "switch", "value": bool(cfg["window"]["on_top"]),
                     "label": "Keep Shinjer's Study Desk above other windows"},
                    {"key": "toolbar_link", "type": "switch", "value": bool(cfg["toolbar_link"]),
                     "label": "Shinjer's Study Desk link in Anki's top bar",
                     "hint": "Next to Decks, Add and Browse. It's also in the Tools menu, "
                     "and on the Decks screen status bar."},
                ],
            }
        ]

    def set_setting(self, desk, key, value) -> None:
        on = bool(value) and value != "0"
        if key == "on_top":
            prefs.set_value("window.on_top", on)
            desk.update_on_top()
        elif key == "toolbar_link":
            prefs.set_value("toolbar_link", on)
            mw.toolbar.draw()
        elif key in ("mode", "theme"):
            if prefs.set_appearance(key, str(value)):
                window.appearance_changed()
        else:
            return
        window.rerender(self.id)
