"""
Background housekeeping for Study Day, and the hooks that drive it:
catch up a freeze after days away, tidy up the Ahead deck when it's finished
or a new day starts, and keep the history in step with Edit > Undo.
"""

from __future__ import annotations

from aqt import gui_hooks, mw

from .. import window
from . import actions, banner

CHECK_EVERY_MS = 5 * 60 * 1000

_timer = None


def check_day() -> None:
    """While frozen, catch up on days that passed; tidy up the Study Ahead deck
    when it's finished or a new day starts. Runs on a timer too."""
    if mw.col and mw.state in ("deckBrowser", "overview"):
        actions.catch_up_if_needed()
        actions.maintain()


def on_operation(changes, handler) -> None:
    """After anything changes the collection (our actions, Edit > Undo/Redo,
    deleting a deck, reviewing...), keep History and the window in step."""
    if not mw.col:
        return
    actions.sync_history()
    window.refresh()
    # Finishing the last card of the Study Ahead deck removes it.
    if mw.state in ("deckBrowser", "overview"):
        actions.maintain()


def on_profile_open() -> None:
    global _timer
    mw.progress.single_shot(1500, check_day)
    if _timer is None:
        _timer = mw.progress.timer(CHECK_EVERY_MS, check_day, True, parent=mw)


def on_state_change(new_state, old_state) -> None:
    if new_state in ("deckBrowser", "overview"):
        check_day()
        window.refresh()


def on_js_message(handled, message, context):
    """Links on the Decks-screen status bar."""
    if not isinstance(message, str) or not message.startswith(banner.CMD):
        return handled
    cmd = message[len(banner.CMD):]
    refresh = mw.deckBrowser.refresh
    if cmd == "unfreeze":
        actions.unfreeze(mw, refresh)
    elif cmd == "ahead":
        from . import core

        settings = core.get_settings(mw.col)
        actions.study_ahead(mw, settings["decks"], 1, int(settings["extra_new"]), refresh)
    elif cmd == "study":
        actions.open_ahead_deck()
    elif cmd == "remove":
        actions.remove_study_ahead(mw, refresh)
    elif cmd == "hide":
        banner.set_mode("compact")
    elif cmd == "show":
        banner.set_mode("full")
    elif cmd == "open":
        window.open_desk("study_day")
    return (True, None)


def setup() -> None:
    gui_hooks.deck_browser_will_render_content.append(banner.on_deck_browser_render)
    gui_hooks.webview_did_receive_js_message.append(on_js_message)
    gui_hooks.operation_did_execute.append(on_operation)
    gui_hooks.profile_did_open.append(on_profile_open)
    gui_hooks.state_did_change.append(on_state_change)
    gui_hooks.sync_did_finish.append(check_day)
