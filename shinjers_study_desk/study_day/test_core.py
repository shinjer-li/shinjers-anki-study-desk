"""
Tests for core.py against a real (temporary) Anki collection.

Needs the `anki` package (pip install anki). Run:
    python test_core.py
"""

import os
import sys
import tempfile

from anki.collection import Collection

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402


def make_col():
    col = Collection(tempfile.mktemp(suffix=".anki2"))
    return col


def add_cards(col, deck, n, due_in=None, learning=False):
    """Add n notes to `deck`. due_in=None keeps them new; otherwise make them
    review cards due `due_in` days from today."""
    did = col.decks.id(deck)
    model = col.models.by_name("Basic")
    cids = []
    for i in range(n):
        note = col.new_note(model)
        note["Front"] = f"{deck} {i}"
        note["Back"] = "x"
        col.add_note(note, did)
        card = note.cards()[0]
        if due_in is not None:
            card.type, card.queue, card.ivl, card.factor = 2, 2, 10, 2500
            card.due = col.sched.today + due_in
            if learning:
                card.type, card.queue = 1, 1
                card.due = int(col.crt + (col.sched.today + due_in) * 86400)
            col.update_card(card)
        cids.append(card.id)
    return cids


class ShiftedSched:
    """Wraps the scheduler so `today` can be moved forward."""

    def __init__(self, sched):
        self._sched = sched
        self.offset = 0

    @property
    def today(self):
        return self._sched.today + self.offset

    def __getattr__(self, name):
        return getattr(self._sched, name)


def set_today(col, offset):
    """Pretend `offset` more days have passed."""
    if not isinstance(col.sched, ShiftedSched):
        col.sched = ShiftedSched(col.sched)
    col.sched.offset += offset


def due(col, cid):
    return col.get_card(cid).due


def test_study_ahead():
    col = make_col()
    a_tomorrow = add_cards(col, "A", 3, due_in=1)
    a_later = add_cards(col, "A::Sub", 2, due_in=2)
    b_tomorrow = add_cards(col, "B", 4, due_in=1)
    add_cards(col, "A", 5)  # new cards
    a = col.decks.id("A")

    assert core.ahead_count(col, [a], 1) == 3
    assert core.ahead_count(col, [a], 2) == 5
    assert core.ahead_count(col, [], 1) == 7
    assert core.ahead_counts(col, [a], 3) == [3, 5, 5]
    assert core.ahead_counts(col, [], 2) == [7, 9]

    did, count = core.create_study_ahead(col, [a], days=1, extra_new=2)
    assert count == 3 + 2, count
    assert core.ahead_deck_id(col) == did
    assert all(col.get_card(c).did == did for c in a_tomorrow)
    assert all(col.get_card(c).did != did for c in b_tomorrow + a_later)

    # Rebuilding reuses the same deck.
    did2, count2 = core.create_study_ahead(col, [a], days=2, extra_new=0)
    assert did2 == did and count2 == 5

    # Undo via history puts cards home.
    entry = {"kind": "ahead", "data": {"deck_id": did}}
    core.undo_entry(col, entry)
    assert core.ahead_deck_id(col) is None
    assert all(col.get_card(c).did == a for c in a_tomorrow)
    assert all(due(col, c) == col.sched.today + 1 for c in a_tomorrow)
    print("study ahead ok")


def test_study_ahead_keeps_current_deck():
    col = make_col()
    add_cards(col, "A", 3, due_in=1)
    a = col.decks.id("A")
    col.decks.select(a)
    did, _ = core.create_study_ahead(col, [a], 1, 0)
    assert did and col.decks.get_current_id() == a
    # Rebuilding while the Ahead deck is open keeps it open.
    col.decks.select(did)
    core.create_study_ahead(col, [a], 2, 0)
    assert col.decks.get_current_id() == did
    print("study ahead keeps current deck ok")


def test_study_ahead_nothing_due():
    col = make_col()
    add_cards(col, "A", 2, due_in=5)
    did, count = core.create_study_ahead(col, [col.decks.id("A")], 1, 0)
    assert did is None and count == 0
    assert core.ahead_deck_id(col) is None
    assert not [d for d in col.decks.all_names_and_ids() if "Study Ahead" in d.name]
    print("study ahead empty ok")


def test_freeze_cycle():
    col = make_col()
    a = add_cards(col, "A", 3, due_in=0)  # due today
    a_later = add_cards(col, "A", 2, due_in=3)
    learn = add_cards(col, "A", 1, due_in=0, learning=True)
    b = add_cards(col, "B", 2, due_in=0)
    new = add_cards(col, "A", 2)
    scope = [col.decks.id("A")]
    today0 = col.sched.today
    learn_due0 = due(col, learn[0])

    core.freeze(col, start_tomorrow=False)
    assert core.get_state(col)["frozen"]
    assert core.days_to_catch_up(col) == 0

    # Three days pass while frozen.
    set_today(col, 3)
    assert col.sched.today == today0 + 3
    assert core.days_to_catch_up(col) == 3
    days, changes = core.catch_up(col, scope)
    assert days == 3
    assert {c[0] for c in changes} == set(a + a_later + learn)
    # Cards due on the freeze day are due "today" again; nothing piled up.
    assert all(due(col, c) == col.sched.today for c in a)
    assert all(due(col, c) == col.sched.today + 3 for c in a_later)
    assert due(col, learn[0]) == learn_due0 + 3 * 86400
    # Out-of-scope and new cards untouched.
    assert all(due(col, c) == today0 for c in b)
    assert all(col.get_card(c).type == 0 for c in new)
    assert core.days_to_catch_up(col) == 0

    # Review one card after the shift, then undo the shift: that card is kept.
    reviewed = col.get_card(a[0])
    reviewed.due = col.sched.today + 20
    col.update_card(reviewed)
    restored, skipped = core.revert_changes(col, changes)
    assert skipped == 1 and restored == len(changes) - 1
    assert due(col, a[0]) == col.sched.today + 20
    assert all(due(col, c) == today0 for c in a[1:])
    core.revert_changes(col, [])  # no-op

    prev = core.unfreeze(col)
    assert prev["frozen"] and not core.get_state(col)["frozen"]
    assert core.days_to_catch_up(col) == 0
    print("freeze cycle ok")


def test_freeze_start_tomorrow():
    col = make_col()
    a = add_cards(col, "A", 2, due_in=1)
    today0 = col.sched.today
    core.freeze(col, start_tomorrow=True)
    set_today(col, 1)
    assert core.days_to_catch_up(col) == 0  # tomorrow is the first day off
    set_today(col, 1)
    assert core.days_to_catch_up(col) == 1
    core.catch_up(col, [])
    # Two days later, you see what was due the day after you froze.
    assert all(due(col, c) == col.sched.today for c in a)
    assert col.sched.today == today0 + 2
    print("freeze start tomorrow ok")


def test_freeze_removes_study_ahead_and_shifts_filtered():
    col = make_col()
    a = add_cards(col, "A", 2, due_in=1)
    core.create_study_ahead(col, [], 1, 0)
    core.freeze(col, start_tomorrow=False)
    assert core.ahead_deck_id(col) is None
    assert all(col.get_card(c).odid == 0 for c in a)

    # A card sitting in some other filtered deck gets its return date moved.
    other = col.sched.get_or_create_filtered_deck(0)
    other.name = "Other"
    other.config.search_terms[0].search = "deck:A"
    other.config.reschedule = True
    col.sched.add_or_update_filtered_deck(other)
    odue0 = col.get_card(a[0]).odue
    assert odue0
    set_today(col, 2)
    days, changes = core.catch_up(col, [])
    assert days == 2
    assert col.get_card(a[0]).odue == odue0 + 2
    print("filtered shift ok")


def test_undo_entries_and_history():
    col = make_col()
    add_cards(col, "A", 1, due_in=0)
    path = os.path.join(tempfile.mkdtemp(), "h", "history.json")
    hist = core.History(path)
    assert hist.last_active() is None

    prev = core.freeze(col, start_tomorrow=False)
    hist.add("freeze", "Froze", {"prev": prev})
    set_today(col, 1)
    days, changes = core.catch_up(col, [])
    hist.add("shift", "Shift", {"days": days, "changes": changes})
    prev = core.unfreeze(col)
    hist.add("unfreeze", "Unfroze", {"prev": prev})

    hist2 = core.History(path)  # reload from disk
    assert [e["kind"] for e in hist2.entries] == ["freeze", "shift", "unfreeze"]

    core.undo_entry(col, hist2.last_active())
    hist2.last_active()["undone"] = True
    st = core.get_state(col)
    assert st["frozen"] and st["last_shift_day"] == col.sched.today
    assert core.days_to_catch_up(col) == 0
    core.undo_entry(col, hist2.last_active())
    hist2.last_active()["undone"] = True
    core.undo_entry(col, hist2.last_active())
    assert not core.get_state(col)["frozen"]

    for i in range(core.HISTORY_LIMIT + 5):
        hist2.add("ahead", str(i), {"deck_id": None})
    assert len(hist2.entries) == core.HISTORY_LIMIT

    # Corrupt history file -> starts empty instead of crashing.
    with open(path, "w") as f:
        f.write("{not json")
    assert core.History(path).entries == []
    print("history ok")


def test_deleted_decks_in_settings():
    col = make_col()
    add_cards(col, "A", 2, due_in=1)
    gone = col.decks.id("Gone")
    col.decks.remove([gone])
    assert core.scope_ids(col, [gone]) is None
    assert core.describe_decks(col, [gone]) == "All decks"
    assert core.ahead_count(col, [gone], 1) == 2
    # Deck names with search-special characters still work.
    weird = col.decks.id('Weird "deck" (1)*')
    add_cards(col, 'Weird "deck" (1)*', 3, due_in=1)
    assert core.ahead_count(col, [weird], 1) == 3
    print("deck handling ok")


def in_undo_step(col, label, fn):
    """Run fn(col) as one named undo step, the way the add-on does."""
    pos = col.add_custom_undo_entry(label)
    out = fn(col)
    col.merge_undo_entries(pos)
    return out


def test_naming_forecast_and_progress():
    col = make_col()
    cardio = add_cards(col, "Step::Cardio", 3, due_in=1)
    add_cards(col, "Step::Cardio", 2, due_in=3)
    add_cards(col, "Step::Cardio", 1, due_in=-2)  # overdue counts as today
    add_cards(col, "Step::Renal", 4, due_in=1)
    add_cards(col, "Step::Cardio", 6)  # new
    c = col.decks.id("Step::Cardio")
    r = col.decks.id("Step::Renal")

    assert core.ahead_name(col, [c]) == "+ Cardio (Ahead)"
    assert core.ahead_name(col, [c, r]) == "+ Cardio + Renal (Ahead)"
    assert core.ahead_name(col, []) == "+ Study Ahead"
    assert core.new_count(col, [c]) == 6

    fc = core.forecast(col, [c], 7)
    assert fc["due"][:4] == [1, 3, 0, 2], fc
    assert sum(fc["ahead"]) == 0 and fc["pullable"][1] == 3

    did, count = core.create_study_ahead(col, [c], days=1, extra_new=0)
    assert col.decks.name(did) == "+ Cardio (Ahead)"
    # Sorts to the top of the deck list.
    assert col.sched.deck_due_tree().children[0].name == "+ Cardio (Ahead)"
    fc = core.forecast(col, [c], 7)
    assert fc["due"][1] == 0 and fc["ahead"][1] == 3, fc
    assert core.due_today_count(col, [c]) == 1

    info = core.ahead_info(col)
    assert (info["total"], info["left"], info["done"], info["due_now"]) == (3, 3, 0, 0)
    assert not info["stale"]
    # Study one card: it leaves the deck.
    card = col.get_card(cardio[0])
    card.start_timer()
    col.sched.answerCard(card, 3)
    info = core.ahead_info(col)
    assert info["left"] == 2 and info["done"] == 1, info

    # Next day: the leftovers are now due today, and the deck is stale.
    set_today(col, 1)
    info = core.ahead_info(col)
    assert info["stale"] and info["due_now"] == 2, info

    p = core.pace(col, [c], 30)
    assert len(p["reviews"]) == 30 and p["secs_per_review"] > 0
    assert p["secs_per_new"] == p["secs_per_review"] * core.NEW_CARD_STEPS  # no learning yet
    print("naming / forecast / progress ok")


def test_new_per_day():
    col = make_col()
    add_cards(col, "A", 30)
    add_cards(col, "B", 4)
    a, b = col.decks.id("A"), col.decks.id("B")
    conf = col.decks.config_dict_for_deck_id(a)
    conf["new"]["perDay"] = 20
    col.decks.save(conf)
    assert core.new_per_day(col, [a]) == 20
    assert core.new_per_day(col, [b]) == 4  # only 4 left
    assert core.new_per_day(col, []) == 24
    assert core.new_left_today(col, [a]) == 20

    # Start 5 of A's new cards today: 15 of the 20 are left.
    for cid in col.find_cards(f"did:{a} is:new")[:5]:
        card = col.get_card(cid)
        card.start_timer()
        col.sched.answerCard(card, 3)
    assert core.new_left_today(col, [a]) == 15
    assert core.new_left_today(col, [b]) == 4

    # A subdeck with a lower limit caps what it gives its parent.
    add_cards(col, "P::Kid", 50)
    par, kid = col.decks.id("P"), col.decks.id("P::Kid")
    small = col.decks.add_config_returning_id("small")
    kid_deck = col.decks.get(kid)
    kid_deck["conf"] = small
    col.decks.save(kid_deck)
    conf = col.decks.get_config(small)
    conf["new"]["perDay"] = 7
    col.decks.save(conf)
    assert core.new_per_day(col, [par]) == 7
    assert core.new_left_today(col, [par]) == 7
    assert core.new_left_today(col, [par, kid]) == 7  # the subdeck isn't counted twice
    print("new per day ok")




def test_cleanup_and_restore():
    col = make_col()
    add_cards(col, "A", 4, due_in=1)
    a = col.decks.id("A")
    did, count = core.create_study_ahead(col, [a], 1, 0)
    state = core.get_state(col)
    built = state["ahead_built_at"]
    cards = core.ahead_card_ids(col)
    assert len(cards) == 4
    entries = [
        {"kind": "ahead", "label": "x", "undone": False, "data": {"deck_id": did, "built_at": built}},
    ]
    core.remove_study_ahead(col)
    entries.append({"kind": "cleanup", "label": "y", "undone": False,
                    "data": {"card_ids": cards, "name": "+ A (Ahead)", "built_at": built, "total": 4}})
    entries[0]["data"]["ended"] = "Sent home at the start of a new day"
    assert core.reconcile(col, entries)
    assert entries[0]["undone"] and entries[0]["note"] == "Sent home at the start of a new day"
    assert not entries[1]["undone"]

    msg = core.undo_entry(col, entries[1])
    assert "4 cards" in msg, msg
    assert core.ahead_deck_id(col) and core.get_state(col)["ahead_built_at"] == built
    core.reconcile(col, entries)
    # The original Study Ahead is back in effect; the cleanup is undone.
    assert not entries[0]["undone"] and entries[1]["undone"]
    print("cleanup / restore ok")


def test_reconcile_edit_undo_redo_and_delete():
    col = make_col()
    add_cards(col, "A", 3, due_in=1)
    a = col.decks.id("A")
    entries = []

    def add(kind, data):
        entries.append({"kind": kind, "label": kind, "undone": False, "note": "", "data": data})

    did, _ = in_undo_step(col, "Study Ahead", lambda c: core.create_study_ahead(c, [a], 1, 0))
    add("ahead", {"deck_id": did, "built_at": core.get_state(col)["ahead_built_at"]})
    assert not core.reconcile(col, entries)

    # Edit > Undo in Anki: deck and state go back.
    col.undo()
    assert core.ahead_deck_id(col) is None
    assert core.reconcile(col, entries, edit_undo=True)
    assert entries[0]["undone"] and entries[0]["note"] == core.EDIT_UNDO_NOTE

    # Edit > Redo: back in effect, white again.
    col.redo()
    assert core.reconcile(col, entries)
    assert not entries[0]["undone"] and entries[0]["note"] == ""

    # Deleting the deck by hand on the main screen.
    col.decks.remove([core.ahead_deck_id(col)])
    core.reconcile(col, entries)
    assert entries[0]["undone"] and entries[0]["note"] == "Deck deleted"

    # Freeze, unfreeze: the freeze entry is ended, not undone.
    prev = in_undo_step(col, "Freeze Reviews", lambda c: core.freeze(c, False))
    add("freeze", {"prev": prev, "frozen_at": core.get_state(col)["frozen_at"]})
    prev = in_undo_step(col, "Unfreeze Reviews", core.unfreeze)
    add("unfreeze", {"prev": prev})
    core.reconcile(col, entries)
    assert not entries[1]["undone"] and entries[1]["note"] == "Ended when you unfroze"
    assert not entries[2]["undone"]

    # Edit > Undo of the unfreeze: frozen again, unfreeze shows undone.
    col.undo()
    core.reconcile(col, entries, edit_undo=True)
    assert entries[2]["undone"] and entries[2]["note"] == core.EDIT_UNDO_NOTE
    assert not entries[1]["undone"] and entries[1]["note"] == ""

    # Shift entries only flip on Edit > Undo, not because a card was reviewed.
    set_today(col, 1)
    days, changes = in_undo_step(col, "Frozen Day", lambda c: core.catch_up(c, []))
    add("shift", {"days": days, "changes": changes})
    for cid, *_ in changes:
        card = col.get_card(cid)
        card.due += 30
        col.update_card(card)
    core.reconcile(col, entries)
    assert not entries[3]["undone"]
    print("reconcile ok")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ALL OK")
