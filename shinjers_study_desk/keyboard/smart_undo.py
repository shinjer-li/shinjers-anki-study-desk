"""
Smarter undo for the review screen's undo key.

- Answer showing: flip back to the question. The card's timer resumes from
  where it was when you flipped, so time spent looking at the answer is dropped.
- Question showing: normal Anki undo, but never past the start of the current
  review session (entering the review screen). With nothing to undo, a tooltip
  says so instead of jumping back to a card from an earlier session.
"""

import time

from aqt import gui_hooks, mw
from aqt.utils import tooltip

session = {"depth": 0, "last_step": None}  # undo steps made this session
flip = {"card_id": None, "elapsed": 0.0}  # timer value when the answer was shown


def _undo_status():
    return mw.col.undo_status() if mw.col else None


def undo():
    reviewer = mw.reviewer
    card = reviewer.card
    if reviewer.state == "answer" and card:
        reviewer._showQuestion()
        reviewer._reps -= 1  # _showQuestion counts itself as a new card shown
        if flip["card_id"] == card.id:
            card.timer_started = time.time() - flip["elapsed"]
        return
    if session["depth"] <= 0:
        tooltip("Nothing to undo this session")
        return
    mw.undo()


def on_show_answer(card):
    flip["card_id"] = card.id
    flip["elapsed"] = time.time() - (card.timer_started or time.time())


def on_state_did_change(new_state, old_state):
    if new_state == "review" and old_state != "review":
        status = _undo_status()
        session["depth"] = 0
        session["last_step"] = status.last_step if status else None


def on_operation_did_execute(changes, handler):
    if mw.state != "review":
        return
    status = _undo_status()
    if not status or status.last_step == session["last_step"]:
        return
    session["last_step"] = status.last_step
    if not status.undo:
        session["depth"] = 0  # undo history was cleared
    elif status.redo:
        session["depth"] = max(0, session["depth"] - 1)  # this op was an undo
    else:
        session["depth"] += 1


gui_hooks.reviewer_did_show_answer.append(on_show_answer)
gui_hooks.state_did_change.append(on_state_did_change)
gui_hooks.operation_did_execute.append(on_operation_did_execute)
