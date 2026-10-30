"""
User actions, shared by the window and the Decks-screen banner.

Each one runs as a background CollectionOp with a named undo entry (so
Edit > Undo works right away) and is also written to the history file (so it
can be undone later from the History list).
"""

from __future__ import annotations

import html
import os
import re
from typing import Callable

from aqt import mw
from aqt.operations import CollectionOp
from aqt.utils import showWarning, tooltip

from . import core

# Undo history lives in the add-on's user_files folder, which Anki keeps on update.
ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Undo labels of our actions, to recognise Edit > Undo of one of them.
LABELS = {
    "Study Ahead",
    "Remove Study Ahead",
    "Finish Study Ahead",
    "New Day Cleanup",
    "Freeze Reviews",
    "Unfreeze Reviews",
    "Frozen Day",
}

_history: core.History | None = None
_history_profile: str | None = None
_busy: set[str] = set()
# Study Ahead builds whose automatic removal was undone with Edit > Undo; leave
# them alone so the undo sticks.
_keep_builds: set = set()


def history() -> core.History:
    """History for the current profile (reloaded when the profile changes)."""
    global _history, _history_profile
    profile = mw.pm.name or "default"
    if _history is None or _history_profile != profile:
        safe = re.sub(r"[^\w.-]", "_", profile)
        path = os.path.join(ADDON_DIR, "user_files", f"history-{safe}.json")
        _history = core.History(path)
        _history_profile = profile
    return _history


def sync_history() -> None:
    """Match the history list to the collection (after Edit > Undo, Redo, a
    deck deleted by hand, a sync...)."""
    if not mw.col:
        return
    try:
        redo = mw.col.undo_status().redo
    except Exception:
        redo = ""
    edit_undo = bool(redo) and (redo in LABELS or redo.startswith("Undo: "))
    hist = history()
    if core.reconcile(mw.col, hist.entries, edit_undo):
        hist.save()


def _run(
    parent,
    label: str,
    work: Callable,
    on_success: Callable,
    on_failure: Callable | None = None,
) -> None:
    """Run `work(col)` inside one undo step, then `on_success(result)`."""
    result: dict = {}

    def op(col):
        pos = col.add_custom_undo_entry(label)
        result["value"] = work(col)
        return col.merge_undo_entries(pos)

    def failed(exc):
        if on_failure:
            on_failure()
        showWarning(f"Shinjer's Study Desk: {label} failed.\n\n{exc}", parent=parent)

    CollectionOp(parent=parent or mw, op=op).success(
        lambda _changes: on_success(result.get("value"))
    ).failure(failed).run_in_background()


def _end_ahead(reason: str) -> None:
    """Note on the current Study Ahead's history entry why its deck went away."""
    built = core.get_state(mw.col)["ahead_built_at"]
    entry = history().current_ahead(built) if built else None
    if entry:
        entry["data"]["ended"] = reason
        history().save()


def _leave_removed_deck(did) -> None:
    """If Anki is showing the deck we just removed, go back to the deck list."""
    if mw.state == "overview" and did and mw.col.decks.get_current_id() == did:
        mw.moveToState("deckBrowser")


def study_ahead(parent, deck_ids, days: int, extra_new: int, done=None) -> None:
    if core.ahead_deck_id(mw.col):
        _end_ahead("Replaced by a new Study Ahead deck")

    def work(col):
        return core.create_study_ahead(col, deck_ids, days, extra_new)

    def finished(value):
        did, count = value
        if did:
            span = "tomorrow" if days == 1 else f"the next {days} days"
            history().add(
                "ahead",
                f"Study Ahead: {count} cards due {span}",
                {
                    "deck_id": did,
                    "built_at": core.get_state(mw.col)["ahead_built_at"],
                },
            )
            tooltip(
                f"Created <b>{html.escape(mw.col.decks.name(did))}</b> with {count} cards.",
                parent=parent,
            )
        else:
            tooltip("No upcoming cards found in those decks.", parent=parent)
        if done:
            done()

    _run(parent, "Study Ahead", work, finished)


def remove_study_ahead(parent, done=None) -> None:
    did = core.ahead_deck_id(mw.col)
    _end_ahead("Deck removed")

    def finished(removed):
        if removed:
            tooltip("Removed the Study Ahead deck. Unfinished cards are back home.", parent=parent)
            _leave_removed_deck(did)
        if done:
            done()

    _run(parent, "Remove Study Ahead", core.remove_study_ahead, finished)


def maintain(done=None) -> None:
    """Remove the Study Ahead deck once it's finished, or at the start of a
    new day (sending unfinished cards home), depending on the settings."""
    if "maintain" in _busy or not mw.col:
        return
    info = core.ahead_info(mw.col)
    if not info:
        return
    try:
        redo = mw.col.undo_status().redo
    except Exception:
        redo = ""
    if redo in ("Finish Study Ahead", "New Day Cleanup"):
        _keep_builds.add(info["built_at"])
    if info["built_at"] in _keep_builds:
        return
    settings = core.get_settings(mw.col)
    did = info["id"]

    if info["left"] == 0 and settings["auto_finish"]:
        _busy.add("maintain")
        _end_ahead("Finished: deck removed")

        def finished(_):
            _busy.discard("maintain")
            tooltip("Study Ahead finished! Removed the empty deck.", period=4000)
            _leave_removed_deck(did)
            if done:
                done()

        _run(None, "Finish Study Ahead", core.remove_study_ahead, finished,
             lambda: _busy.discard("maintain"))

    elif info["stale"] and settings["new_day_cleanup"]:
        _busy.add("maintain")
        card_ids = core.ahead_card_ids(mw.col)
        _end_ahead("Sent home at the start of a new day")

        def finished(_):
            _busy.discard("maintain")
            n = len(card_ids)
            history().add(
                "cleanup",
                f"New day: sent {n} unfinished Study Ahead cards home",
                {
                    "card_ids": card_ids,
                    "name": info["name"],
                    "built_at": info["built_at"],
                    "total": info["total"],
                },
            )
            tooltip(
                f"New day: sent {n} unfinished Study Ahead cards back to their decks.",
                period=5000,
            )
            _leave_removed_deck(did)
            if done:
                done()

        _run(None, "New Day Cleanup", core.remove_study_ahead, finished,
             lambda: _busy.discard("maintain"))


def freeze(parent, start_tomorrow: bool, done=None) -> None:
    if core.ahead_deck_id(mw.col):
        _end_ahead("Removed when you froze reviews")

    def finished(prev):
        when = "starting tomorrow" if start_tomorrow else "starting now"
        history().add(
            "freeze",
            f"Froze reviews ({when})",
            {"prev": prev, "frozen_at": core.get_state(mw.col)["frozen_at"]},
        )
        tooltip("Reviews frozen. Nothing will pile up.", parent=parent)
        if done:
            done()

    _run(parent, "Freeze Reviews", lambda col: core.freeze(col, start_tomorrow), finished)


def unfreeze(parent, done=None) -> None:
    def finished(prev):
        history().add("unfreeze", "Unfroze reviews", {"prev": prev})
        tooltip("Unfrozen. Welcome back!", parent=parent)
        if done:
            done()

    _run(parent, "Unfreeze Reviews", core.unfreeze, finished)


def catch_up_if_needed(done=None) -> None:
    """While frozen, push cards back for any days that have passed."""
    if "catch_up" in _busy or not mw.col or core.days_to_catch_up(mw.col) <= 0:
        return
    _busy.add("catch_up")
    deck_ids = core.get_settings(mw.col)["decks"]

    def finished(value):
        _busy.discard("catch_up")
        days, changes = value
        if days:
            history().add(
                "shift",
                f"Frozen day(s): pushed {len(changes)} cards back {days} day(s)",
                {"days": days, "changes": changes},
            )
            tooltip(f"Frozen: pushed your cards back {days} day(s).")
        if done:
            done()

    _run(None, "Frozen Day", lambda col: core.catch_up(col, deck_ids), finished,
         lambda: _busy.discard("catch_up"))


def undo_last(parent, done=None) -> None:
    sync_history()
    hist = history()
    entry = hist.last_active()
    if not entry:
        tooltip("Nothing to undo.", parent=parent)
        return
    did = core.ahead_deck_id(mw.col)

    def finished(message):
        entry["undone"] = True
        entry["note"] = "Undone here"
        hist.save()
        tooltip(message, parent=parent, period=5000)
        if entry["kind"] == "ahead":
            _leave_removed_deck(did)
        if done:
            done()

    _run(
        parent,
        f"Undo: {entry['label']}",
        lambda col: core.undo_entry(col, entry),
        finished,
    )


def open_ahead_deck() -> None:
    """Show the Study Ahead deck's overview in the main window."""
    did = core.ahead_deck_id(mw.col)
    if not did:
        return
    mw.col.decks.select(did)
    mw.moveToState("overview")
    if mw.isMinimized():
        mw.showNormal()
    mw.raise_()
    mw.activateWindow()
