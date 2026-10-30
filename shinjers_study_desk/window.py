"""
The Shinjer's Study Desk window: one web view with a tab rail. It knows nothing about
what the tabs do; it loads web/index.html, passes data from each Tab to the
page and routes the page's commands back (see tab.py for the contract).

It's a normal top-level window (minimize, maximize, resize, not modal) that
opens maximized.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from aqt import gui_hooks, mw
from aqt.qt import QColor, QIcon, QTimer, Qt, QVBoxLayout, QWidget
from aqt.theme import theme_manager
from aqt.utils import restoreGeom, saveGeom
from aqt.webview import AnkiWebView

from . import prefs
from .tab import Tab

GEOM_KEY = "studyDesk"
WEB_DIR = os.path.join(prefs.ADDON_DIR, "web")
LOGO = os.path.join(WEB_DIR, "img", "logo.png")

# Loaded in this order. Add a tab's files here.
ASSETS = {
    "css": ["tokens", "base", "study_day", "trouble", "keyboard", "settings", "about"],
    "js": ["icons", "desk", "charts", "study_day", "trouble", "keyboard", "settings", "about"],
}

_tabs: list[Tab] = []
_window: DeskWindow | None = None


def setup(tabs: list[Tab]) -> None:
    _tabs[:] = tabs


def _is_dark(look: dict) -> bool:
    return look["mode"] == "dark" or (look["mode"] == "auto" and theme_manager.night_mode)


def theme_color(look: dict, token: str) -> str | None:
    """A token's color (e.g. "--ground") in the picked theme and mode, read
    from web/css/tokens.css, for painting Qt before the page has loaded."""
    with open(os.path.join(WEB_DIR, "css", "tokens.css"), encoding="utf-8") as f:
        css = f.read()
    sel = re.escape(f'[data-theme="{look["theme"]}"]')
    if _is_dark(look):
        sel += re.escape('[data-dark="1"]')
    block = re.search(sel + r"\s*\{([^}]*)\}", css)
    value = block and re.search(re.escape(token) + r":\s*(#[0-9a-fA-F]{3,8})", block.group(1))
    return value.group(1) if value else None


def tabs() -> list[Tab]:
    return list(_tabs)


def tab(tab_id: str) -> Tab | None:
    return next((t for t in _tabs if t.id == tab_id), None)


class DeskWindow(QWidget):
    def __init__(self, start: str):
        super().__init__(None)
        self.setWindowTitle("Shinjer's Study Desk")
        self.setWindowIcon(QIcon(LOGO))
        self.setMinimumSize(640, 480)
        self.active = start
        self.ready = False
        self._apply_flags()

        self.web = AnkiWebView(parent=self, title="study desk")
        self.web.set_bridge_command(self._on_cmd, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self._paint_background()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(lambda: self.render(live_only=True))

        self.resize(1040, 760)
        restoreGeom(self, GEOM_KEY)
        # Load once the window is on screen at its final (maximized) size. A page
        # that loads while the window is still being shown can come up blank
        # until something forces a repaint, like scrolling.
        QTimer.singleShot(0, self._load_page)

    # ── page ──────────────────────────────────────────────────────────────────

    def _load_page(self) -> None:
        self.ready = False
        with open(os.path.join(WEB_DIR, "index.html"), encoding="utf-8") as f:
            body = f.read()
        base = f"/_addons/{prefs.ADDON}/web"
        body = body.replace("{base}", base)
        # Set the theme in <head>, before the first paint, and paint the empty
        # view in the theme's background, so opening doesn't flash Anki's grey
        # or the fallback colors.
        look = prefs.appearance()
        dark = _is_dark(look)
        self._paint_background()
        head = (
            "<script>document.documentElement.setAttribute('data-theme', "
            f"{json.dumps(look['theme'])});document.documentElement.setAttribute("
            f"'data-dark', '{1 if dark else 0}');</script>"
        )
        self.web.stdHtml(
            body,
            css=[f"{base}/css/{name}.css" for name in ASSETS["css"]],
            js=[f"{base}/js/{name}.js" for name in ASSETS["js"]],
            head=head,
            context=self,
            default_css=False,
        )

    def _paint_background(self) -> None:
        color = theme_color(prefs.appearance(), "--ground")
        if color:
            self.web.page().setBackgroundColor(QColor(color))

    def _boot(self) -> None:
        """The page has loaded: tell it the tabs and the look, then draw."""
        self.ready = True
        boot = {
            "tabs": [{"id": t.id, "title": t.title, "icon": t.icon} for t in _tabs],
            "active": self.active,
            "appearance": prefs.appearance(),
            "night": theme_manager.night_mode,
        }
        self.web.eval(f"desk.boot({json.dumps(boot)})")
        self.render()

    def render(self, live_only: bool = False) -> None:
        """Draw the active tab with fresh data."""
        t = tab(self.active)
        if not (self.ready and mw.col and t) or (live_only and not t.live):
            return
        try:
            data = t.data(self)
        except Exception as exc:  # never leave the tab blank without a reason
            self.web.eval(f"desk.fail({json.dumps(t.id)}, {json.dumps(str(exc))})")
            return
        if data is not None:
            self.receive(t.id, data)

    def receive(self, tab_id: str, data: dict) -> None:
        if self.ready:
            self.web.eval(f"desk.receive({json.dumps(tab_id)}, {json.dumps(data)})")

    def patch(self, tab_id: str, data: dict) -> None:
        """Merge `data` into what the tab already shows, and redraw it."""
        if self.ready:
            self.web.eval(f"desk.patch({json.dumps(tab_id)}, {json.dumps(data)})")

    def refresh(self) -> None:
        """Redraw soon (several changes in a row only redraw once)."""
        self._timer.start()

    def show_tab(self, tab_id: str) -> None:
        if tab(tab_id) and tab_id != self.active:
            self.active = tab_id
            if self.ready:
                self.web.eval(f"desk.show({json.dumps(tab_id)})")
                self.render()

    def appearance_changed(self) -> None:
        self._paint_background()
        if self.ready:
            self.web.eval(f"desk.setAppearance({json.dumps(prefs.appearance())})")

    def night_mode_changed(self) -> None:
        self._paint_background()
        if self.ready:
            self.web.eval(f"desk.setNight({json.dumps(theme_manager.night_mode)})")

    def _apply_flags(self) -> None:
        flags = (
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        if prefs.get()["window"]["on_top"]:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def update_on_top(self) -> None:
        self._apply_flags()
        self.show()

    # ── commands from the page ────────────────────────────────────────────────

    def _on_cmd(self, message: str) -> Any:
        if not mw.col:
            return None
        tab_id, _, rest = message.partition(":")
        cmd, _, raw = rest.partition(":")
        arg: Any = raw
        if raw[:1] in ("{", "["):
            try:
                arg = json.loads(raw)
            except ValueError:
                return None
        if tab_id == "desk":
            return self._desk_cmd(cmd, arg)
        t = tab(tab_id)
        if t:
            t.handle(self, cmd, arg)
        return None

    def _desk_cmd(self, cmd: str, arg: Any) -> None:
        if cmd == "ready":
            self._boot()
        elif cmd == "open":
            # The page has already switched; just send the data.
            if tab(arg):
                self.active = arg
                self.render()
        elif cmd == "pref":
            key, _, value = str(arg).partition(":")
            if prefs.set_appearance(key, value):
                appearance_changed()

    # ── window ────────────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.ready:
            self.web.eval("desk.repaint()")

    def closeEvent(self, event) -> None:
        global _window
        saveGeom(self, GEOM_KEY)
        self._timer.stop()
        self.web.cleanup()
        _window = None
        super().closeEvent(event)


# ── module-level helpers (the rest of the add-on uses these) ─────────────────


def open_desk(tab_id: str | None = None) -> None:
    """Show the window on `tab_id` (or bring it to the front)."""
    global _window
    if not mw.col or not _tabs:
        return
    if _window is None:
        _window = DeskWindow(tab_id if tab(tab_id or "") else _tabs[0].id)
        _window.showMaximized()
    elif tab_id:
        _window.show_tab(tab_id)
    else:
        _window.refresh()
    if _window.isMinimized():
        _window.showMaximized()
    _window.show()
    _window.raise_()
    _window.activateWindow()


def current() -> DeskWindow | None:
    return _window


def refresh() -> None:
    if _window is not None:
        _window.refresh()


def rerender(tab_id: str) -> None:
    """Redraw one tab now if it's the one showing (after a setting changed)."""
    if _window is not None and _window.active == tab_id:
        _window.render()


def appearance_changed() -> None:
    if _window is not None:
        _window.appearance_changed()
    # The Decks-screen status bar uses the theme colors too.
    if mw.col and mw.state == "deckBrowser":
        mw.deckBrowser.refresh()


def close() -> None:
    if _window is not None:
        _window.close()


def _night_mode_changed() -> None:
    if _window is not None:
        _window.night_mode_changed()


gui_hooks.profile_will_close.append(close)
gui_hooks.theme_did_change.append(_night_mode_changed)
