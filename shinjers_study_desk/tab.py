"""
The contract every Shinjer's Study Desk tab follows. To add a tab:

1. Make a folder with a `tab.py` holding a Tab subclass (see study_day/tab.py
   for a full one, settings/tab.py for a small one).
2. Add `web/js/<id>.js` that calls `desk.register("<id>", {render(el, data) {...}})`
   and, if it needs styles, `web/css/<id>.css`.
3. List the tab in TABS in __init__.py, and its files in window.py's ASSETS.

Python and the page talk in two directions:
  - Python -> page: the window calls `data()` and hands the dict to the tab's
    render() in JavaScript. A tab can also push data later with
    `desk.receive(self.id, data)` (or a partial update with `desk.patch`).
  - page -> Python: `desk.send("<id>", "<cmd>", arg)` arrives here as
    `handle(desk, cmd, arg)`. `arg` is a string, or a dict/list when the page
    sent an object.
"""

from __future__ import annotations

from typing import Any


class Tab:
    id = ""
    title = ""
    # Rail icon: a name from web/js/icons.js.
    icon = "list"
    # Re-render whenever the collection changes (reviews, undo, sync...).
    live = False

    def data(self, desk) -> dict | None:
        """Everything the page needs to draw this tab. Return None if the
        data will be pushed later with desk.receive() (slow work)."""
        return {}

    def handle(self, desk, cmd: str, arg: Any) -> None:
        """A command from this tab's page."""

    # Settings shown on the Settings tab. Each section:
    #   {"title": str, "rows": [{"key", "label", "type", "value", ...}]}
    # Row types: "switch"; "choice" (+ "options": [[value, label], ...]);
    # "decks" (+ "text": the current selection; opens the deck picker).
    # An optional "hint" is shown under the row.
    def settings(self) -> list[dict]:
        return []

    def set_setting(self, desk, key: str, value: Any) -> None:
        """A row from settings() was changed on the Settings tab."""
