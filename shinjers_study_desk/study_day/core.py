"""
Collection logic for the Study Day tab. No Qt here, so it can be tested
with just the `anki` package.

Two features:

Study ahead -- pulls cards due in the next N days into a filtered deck
    named after your deck ("+ Cardio (Ahead)", so it sorts to the top of the
    deck list). Anki treats them as early reviews, and deleting the deck
    sends any unfinished cards back home untouched. The deck is removed
    automatically once it's empty, or at the start of the next day.

Freeze -- while frozen, each new day pushes every scheduled card in the
    chosen decks back by a day, so nothing becomes due and nothing piles up.
    After unfreezing you pick up exactly where you stopped.

Every change is recorded in a small history file so it can be undone later,
even after restarting Anki. Card undo only touches cards that still have the
value we gave them, so cards you've reviewed since are never clobbered.
"""

from __future__ import annotations

import json
import os
import time

from anki.collection import Collection, SearchNode
from anki.decks import FilteredDeckConfig
from anki.errors import FilteredDeckError
from anki.utils import ids2str

STATE_KEY = "study_day_control_state"
SETTINGS_KEY = "study_day_control_settings"
AHEAD_DECK_NAME = "Study Ahead"
HISTORY_LIMIT = 50
DEFAULT_SECS_PER_REVIEW = 10.0
# With no history of your own, assume a new card takes about this many reviews
# worth of time to get through its learning steps.
NEW_CARD_STEPS = 3

# Anki stores learning-step due times as epoch seconds and review due dates as
# day numbers. Anything this large is a timestamp.
TIMESTAMP_CUTOFF = 1_000_000_000

DEFAULT_STATE = {
    "frozen": False,
    "frozen_at": None,  # epoch seconds, for display
    "frozen_day": None,  # sched.today when freeze started
    "first_paused_day": None,  # frozen_day, or the day after if starting tomorrow
    "last_shift_day": None,  # cards have been pushed back through this day
    "ahead_deck_id": None,
    # The current Study Ahead build. built_at (ms) ties history entries to it.
    "ahead_built_at": None,
    "ahead_total": 0,  # cards in the deck when it was built
    "ahead_day": None,  # sched.today when it was built
}

DEFAULT_SETTINGS = {
    "decks": [],  # deck ids; a checked deck includes its subdecks; empty = all
    "days_ahead": 1,
    "extra_new": 0,
    "banner": "full",  # status bar on the Decks screen: full / compact / off
    "auto_finish": True,  # remove the Study Ahead deck once it's empty
    "new_day_cleanup": True,  # send unfinished Study Ahead cards home overnight
    "stay_on_top": False,
    "forecast_days": 14,
    "pace_days": 30,
}

BANNER_MODES = ("full", "compact", "off")


# ── State and settings (stored in the collection, so they follow the profile) ─


def get_state(col: Collection) -> dict:
    return {**DEFAULT_STATE, **(col.get_config(STATE_KEY, None) or {})}


def save_state(col: Collection, state: dict, undoable: bool = False) -> None:
    col.set_config(STATE_KEY, state, undoable=undoable)


def get_settings(col: Collection) -> dict:
    stored = col.get_config(SETTINGS_KEY, None) or {}
    settings = {**DEFAULT_SETTINGS, **stored}
    # Older versions had an on/off "show_banner" setting.
    if "banner" not in stored and stored.get("show_banner") is False:
        settings["banner"] = "off"
    settings.pop("show_banner", None)
    return settings


def save_settings(col: Collection, settings: dict) -> None:
    col.set_config(SETTINGS_KEY, settings)


# ── Decks ─────────────────────────────────────────────────────────────────────


def existing_roots(col: Collection, deck_ids: list[int]) -> list[int]:
    """Drop ids of decks that were deleted or turned into filtered decks."""
    out = []
    for did in deck_ids:
        deck = col.decks.get(did, default=False)
        if deck and not deck["dyn"]:
            out.append(did)
    return out


def scope_ids(col: Collection, deck_ids: list[int]) -> set[int] | None:
    """All deck ids covered by the selection (with subdecks). None = all decks."""
    roots = existing_roots(col, deck_ids)
    if not roots:
        return None
    ids: set[int] = set()
    for did in roots:
        ids.update(col.decks.deck_and_child_ids(did))
    return ids


def deck_search(col: Collection, deck_ids: list[int]) -> str:
    """Search string matching cards in the selected decks ("" = all decks)."""
    roots = existing_roots(col, deck_ids)
    if not roots:
        return ""
    nodes = [SearchNode(deck=col.decks.name(did)) for did in roots]
    return col.build_search_string(*nodes, joiner="OR")


def describe_decks(col: Collection, deck_ids: list[int]) -> str:
    roots = existing_roots(col, deck_ids)
    if not roots:
        return "All decks"
    return ", ".join(col.decks.name(did) for did in roots)


def _and(*parts: str) -> str:
    return " ".join(f"({p})" for p in parts if p)


# ── Counts ────────────────────────────────────────────────────────────────────


def _scope_sql(col: Collection, deck_ids: list[int], alias: str = "") -> str:
    """SQL condition: the card's home deck is in the selection."""
    ids = scope_ids(col, deck_ids)
    if ids is None:
        return "1"
    p = alias
    joined = ",".join(str(i) for i in sorted(ids))
    return f"(case when {p}odid then {p}odid else {p}did end) in ({joined})"


def due_today_count(col: Collection, deck_ids: list[int]) -> int:
    """Cards due today, not counting ones already pulled into Study Ahead."""
    return forecast(col, deck_ids, 0)["due"][0]


def ahead_search(col: Collection, deck_ids: list[int], days: int) -> str:
    return _and(deck_search(col, deck_ids), f"prop:due>=1 prop:due<={days}")


def ahead_count(col: Collection, deck_ids: list[int], days: int) -> int:
    """Cards a Study Ahead deck would pull in (not suspended/buried/filtered)."""
    search = _and(
        ahead_search(col, deck_ids, days),
        "-is:suspended -is:buried -deck:filtered",
    )
    return len(col.find_cards(search))


def ahead_counts(col: Collection, deck_ids: list[int], days: int) -> list[int]:
    """ahead_count() for 1..`days` days in one search: [tomorrow, next 2 days, ...]."""
    search = _and(
        ahead_search(col, deck_ids, days),
        "-is:suspended -is:buried -deck:filtered",
    )
    ids = col.find_cards(search)
    per_day = [0] * days
    if ids:
        today, cutoff = col.sched.today, col.sched.day_cutoff
        rows = col.db.all(f"select queue, due from cards where id in {ids2str(ids)}")
        for queue, cdue in rows:
            idx = (cdue - cutoff) // 86400 + 1 if queue == 1 else cdue - today
            per_day[max(1, min(days, idx)) - 1] += 1
    out, total = [], 0
    for n in per_day:
        total += n
        out.append(total)
    return out


def new_count(col: Collection, deck_ids: list[int]) -> int:
    """Unseen cards in the selected decks."""
    return col.db.scalar(
        f"select count() from cards where queue = 0 and {_scope_sql(col, deck_ids)}"
    )


def _new_roots(col: Collection, tree, deck_ids: list[int]) -> list:
    """Deck-tree nodes the new-card counts add up: the selected decks (minus
    any inside another selected deck), or every top-level normal deck when
    nothing is selected."""
    roots = existing_roots(col, deck_ids)
    if not roots:
        return [n for n in tree.children if not n.filtered]
    picked = set(roots)
    nodes = []
    for did in roots:
        if any(p["id"] in picked for p in col.decks.parents(did)):
            continue
        node = col.decks.find_deck_in_tree(tree, did)
        if node:
            nodes.append(node)
    return nodes


def new_per_day(col: Collection, deck_ids: list[int]) -> int:
    """New cards a fresh day would bring, worked out the way Anki does: each
    deck gives its own unseen cards plus what its subdecks give, capped by
    its "New cards/day" limit."""
    unseen = dict(col.db.all("select did, count() from cards where queue = 0 group by did"))

    def give(node) -> int:
        if node.filtered:
            return 0
        limit = col.decks.config_dict_for_deck_id(node.deck_id)["new"]["perDay"]
        return min(limit, unseen.get(node.deck_id, 0) + sum(give(c) for c in node.children))

    tree = col.sched.deck_due_tree()
    return sum(give(n) for n in _new_roots(col, tree, deck_ids))


def new_left_today(col: Collection, deck_ids: list[int]) -> int:
    """New cards still to come today, as Anki's Decks screen counts them:
    deck and subdeck limits, the ones already started today, and the
    review limit are all taken into account."""
    tree = col.sched.deck_due_tree()
    return sum(n.new_count for n in _new_roots(col, tree, deck_ids))


def forecast(col: Collection, deck_ids: list[int], days: int) -> dict:
    """Cards due on each of the next `days` days (index 0 = today, overdue
    included). Suspended and buried cards are left out.

    due:      cards in their normal decks
    ahead:    cards sitting in the Study Ahead deck, on the day they're really due
    pullable: of `due`, the review cards a Study Ahead deck could take
              (cards in other filtered decks can't be moved)
    """
    today = col.sched.today
    cutoff = col.sched.day_cutoff
    ahead = ahead_deck_id(col)
    due = [0] * (days + 1)
    in_ahead = [0] * (days + 1)
    pullable = [0] * (days + 1)
    rows = col.db.all(
        "select queue, due, odue, did, odid from cards "
        f"where queue in (1, 2, 3) and {_scope_sql(col, deck_ids)}"
    )
    for queue, cdue, odue, did, odid in rows:
        if queue == 1:
            # Learning step due at a timestamp.
            idx = 0 if cdue < cutoff else (cdue - cutoff) // 86400 + 1
        else:
            # Review cards in a filtered deck keep their real date in odue.
            day = odue if (queue == 2 and odid) else cdue
            idx = max(0, day - today)
        if idx > days:
            continue
        if ahead and did == ahead:
            in_ahead[idx] += 1
        else:
            due[idx] += 1
            if not odid and queue in (2, 3):
                pullable[idx] += 1
    return {"due": due, "ahead": in_ahead, "pullable": pullable}


def pace(col: Collection, deck_ids: list[int], days: int = 30) -> dict:
    """Reviews and minutes per day over the last `days` days (last = today),
    the average seconds per review, and the average time a new card takes
    through its learning steps (for time estimates)."""
    start = col.sched.day_cutoff - days * 86400
    reviews = [0] * days
    secs = [0.0] * days
    learn_secs, learn_cards = 0.0, set()
    rows = col.db.all(
        "select r.id, r.time, r.type, r.cid from revlog r join cards c on c.id = r.cid "
        f"where r.id > ? and r.type < 4 and r.time > 0 and {_scope_sql(col, deck_ids, 'c.')}",
        start * 1000,
    )
    for rid, ms, kind, cid in rows:
        idx = int((rid // 1000 - start) // 86400)
        if 0 <= idx < days:
            reviews[idx] += 1
            secs[idx] += ms / 1000
            if kind == 0:  # a learning step of a new card
                learn_secs += ms / 1000
                learn_cards.add(cid)
    total = sum(reviews)
    per_review = sum(secs) / total if total >= 20 else DEFAULT_SECS_PER_REVIEW
    if len(learn_cards) >= 10:
        per_new = learn_secs / len(learn_cards)
    else:
        per_new = per_review * NEW_CARD_STEPS
    return {
        "reviews": reviews,
        "minutes": [round(s / 60, 1) for s in secs],
        "secs_per_review": round(per_review, 1),
        "secs_per_new": round(per_new, 1),
    }


# ── Study ahead ───────────────────────────────────────────────────────────────


def ahead_deck_id(col: Collection) -> int | None:
    """Id of our Study Ahead deck if it still exists."""
    did = get_state(col)["ahead_deck_id"]
    if did:
        deck = col.decks.get(did, default=False)
        if deck and deck["dyn"]:
            return did
    return None


def ahead_name(col: Collection, deck_ids: list[int]) -> str:
    """'+ Cardio (Ahead)': named after your deck, and the '+' sorts it to the
    top of the deck list."""
    roots = existing_roots(col, deck_ids)
    if not roots:
        return f"+ {AHEAD_DECK_NAME}"
    leaves = [col.decks.name(did).split("::")[-1] for did in roots]
    if len(leaves) > 2:
        leaves = [leaves[0], f"{len(leaves) - 1} more"]
    return f"+ {' + '.join(leaves)} (Ahead)"


def ahead_info(col: Collection) -> dict | None:
    """Progress of the current Study Ahead deck, or None if there isn't one."""
    did = ahead_deck_id(col)
    if not did:
        return None
    state = get_state(col)
    today = col.sched.today
    left = col.db.scalar("select count() from cards where did = ?", did)
    left_new = col.db.scalar("select count() from cards where did = ? and queue = 0", did)
    # Cards whose real due date has now arrived (the deck was left overnight).
    due_now = col.db.scalar(
        "select count() from cards where did = ? and ("
        "(queue = 2 and odue <= ?) or (queue = 3 and due <= ?) or (queue = 1 and due < ?))",
        did,
        today,
        today,
        col.sched.day_cutoff,
    )
    total = max(int(state["ahead_total"] or 0), left)
    built_day = state["ahead_day"]
    return {
        "id": did,
        "name": col.decks.name(did),
        "total": total,
        "left": left,
        "left_new": left_new,  # of `left`, extra new cards (timed as new cards)
        "done": total - left,
        "due_now": due_now,
        "built_at": state["ahead_built_at"],
        "stale": built_day is not None and today > built_day,
    }


def create_study_ahead(
    col: Collection, deck_ids: list[int], days: int, extra_new: int
) -> tuple[int | None, int]:
    """Build (or rebuild) the Study Ahead deck. Returns (deck id, card count).

    If nothing matches, no deck is left behind and (None, 0) is returned.
    """
    terms = [
        FilteredDeckConfig.SearchTerm(
            search=ahead_search(col, deck_ids, days),
            limit=99999,
            order=FilteredDeckConfig.SearchTerm.Order.DUE,
        )
    ]
    if extra_new > 0:
        terms.append(
            FilteredDeckConfig.SearchTerm(
                search=_and(deck_search(col, deck_ids), "is:new"),
                limit=extra_new,
                order=FilteredDeckConfig.SearchTerm.Order.DUE,
            )
        )
    return _build_ahead(col, ahead_name(col, deck_ids), terms)


def restore_study_ahead(
    col: Collection, card_ids: list[int], name: str, built_at, total: int
) -> tuple[int | None, int]:
    """Rebuild a Study Ahead deck from a list of cards (undoing a cleanup).

    Keeps the original build stamp, so the original history entry shows as
    in effect again.
    """
    if not card_ids:
        return None, 0
    terms = [
        FilteredDeckConfig.SearchTerm(
            search="cid:" + ",".join(str(c) for c in card_ids),
            limit=len(card_ids),
            order=FilteredDeckConfig.SearchTerm.Order.DUE,
        )
    ]
    did, count = _build_ahead(col, name, terms)
    if did:
        state = get_state(col)
        state.update(ahead_built_at=built_at, ahead_total=max(total, count))
        save_state(col, state, undoable=True)
    return did, count


def _build_ahead(col: Collection, name: str, terms: list) -> tuple[int | None, int]:
    existing = ahead_deck_id(col)
    # Anki makes a freshly built filtered deck the current deck. Put the user's
    # own deck back, so the Ahead deck is only studied when they open it.
    prev_current = col.decks.get_current_id()
    try:
        return _build_ahead_inner(col, name, terms, existing)
    finally:
        if col.decks.get(prev_current, default=False):
            col.decks.select(prev_current)


def _build_ahead_inner(
    col: Collection, name: str, terms: list, existing: int | None
) -> tuple[int | None, int]:
    deck = col.sched.get_or_create_filtered_deck(existing or 0)
    if not existing or deck.name != name:
        deck.name = _unique_name(col, name, existing)
    del deck.config.search_terms[:]
    deck.config.search_terms.extend(terms)
    deck.config.reschedule = True

    try:
        did = col.sched.add_or_update_filtered_deck(deck).id
    except FilteredDeckError:
        # Anki refuses to build a filtered deck that matches no cards.
        if existing:
            col.decks.remove([existing])
        _set_ahead(col, None)
        return None, 0

    count = len(col.find_cards(f"did:{did}"))
    if count == 0:
        col.decks.remove([did])
        _set_ahead(col, None)
        return None, 0
    _set_ahead(col, did, count)
    return did, count


def ahead_card_ids(col: Collection) -> list[int]:
    did = ahead_deck_id(col)
    return list(col.find_cards(f"did:{did}")) if did else []


def remove_study_ahead(col: Collection) -> bool:
    """Delete the Study Ahead deck; unfinished cards go back to their decks."""
    did = ahead_deck_id(col)
    if did:
        col.decks.remove([did])
    _set_ahead(col, None)
    return bool(did)


def _set_ahead(col: Collection, did: int | None, total: int = 0) -> None:
    state = get_state(col)
    if did:
        state.update(
            ahead_deck_id=did,
            ahead_built_at=int(time.time() * 1000),
            ahead_total=total,
            ahead_day=col.sched.today,
        )
    elif state["ahead_deck_id"] is None and state["ahead_built_at"] is None:
        return
    else:
        state.update(
            ahead_deck_id=None, ahead_built_at=None, ahead_total=0, ahead_day=None
        )
    save_state(col, state, undoable=True)


def _unique_name(col: Collection, name: str, own_id: int | None = None) -> str:
    def taken(n):
        did = col.decks.id_for_name(n)
        return did and did != own_id

    if not taken(name):
        return name
    n = 2
    while taken(f"{name} {n}"):
        n += 1
    return f"{name} {n}"


# ── Freeze ────────────────────────────────────────────────────────────────────


def freeze(col: Collection, start_tomorrow: bool) -> dict:
    """Start a freeze. Returns the previous state (for undo).

    start_tomorrow=False: today's remaining cards wait for you.
    start_tomorrow=True: today counts as normal; tomorrow is the first day off.
    """
    prev = get_state(col)
    remove_study_ahead(col)
    today = col.sched.today
    state = get_state(col)
    state.update(
        frozen=True,
        frozen_at=int(time.time()),
        frozen_day=today,
        first_paused_day=today + 1 if start_tomorrow else today,
        last_shift_day=today + 1 if start_tomorrow else today,
    )
    save_state(col, state, undoable=True)
    return prev


def unfreeze(col: Collection) -> dict:
    """End the freeze. Returns the previous state (for undo)."""
    prev = get_state(col)
    state = dict(prev)
    state.update(
        frozen=False,
        frozen_at=None,
        frozen_day=None,
        first_paused_day=None,
        last_shift_day=None,
    )
    save_state(col, state, undoable=True)
    return prev


def paused_days(col: Collection) -> int:
    """Which day of the break today is (0 = the break hasn't started yet)."""
    state = get_state(col)
    first = state["first_paused_day"]
    if not state["frozen"] or first is None:
        return 0
    return max(0, col.sched.today - first + 1)


def days_to_catch_up(col: Collection) -> int:
    state = get_state(col)
    if not state["frozen"] or state["last_shift_day"] is None:
        return 0
    return max(0, col.sched.today - state["last_shift_day"])


def catch_up(col: Collection, deck_ids: list[int]) -> tuple[int, list]:
    """Push cards back by however many frozen days have passed.

    Returns (days shifted, changes). Each change is [card id, field, new value,
    delta], where field 0 = due and 1 = original due (cards in filtered decks).
    """
    days = days_to_catch_up(col)
    if days <= 0:
        return 0, []
    changes = shift_cards(col, deck_ids, days)
    state = get_state(col)
    state["last_shift_day"] = col.sched.today
    save_state(col, state, undoable=True)
    return days, changes


def shift_cards(col: Collection, deck_ids: list[int], days: int) -> list:
    """Move every scheduled (non-new) card in scope `days` later."""
    scope = scope_ids(col, deck_ids)
    rows = col.db.all(
        "select id, did, odid, type, due, odue from cards where type != 0"
    )
    cards = []
    changes = []
    for cid, did, odid, ctype, due, odue in rows:
        home = odid or did
        if scope is not None and home not in scope:
            continue
        if odid:
            # In a filtered deck: move the date it returns home with.
            if not odue:
                continue
            delta = days * 86400 if odue > TIMESTAMP_CUTOFF else days
            card = col.get_card(cid)
            card.odue += delta
            changes.append([cid, 1, card.odue, delta])
        else:
            delta = days * 86400 if due > TIMESTAMP_CUTOFF else days
            card = col.get_card(cid)
            card.due += delta
            changes.append([cid, 0, card.due, delta])
        cards.append(card)
    if cards:
        col.update_cards(cards)
    return changes


def revert_changes(col: Collection, changes: list) -> tuple[int, int]:
    """Undo shift changes. Returns (restored, skipped because card changed)."""
    cards = []
    skipped = 0
    for cid, field, new_value, delta in changes:
        try:
            card = col.get_card(cid)
        except Exception:
            skipped += 1  # card was deleted
            continue
        attr = "odue" if field == 1 else "due"
        if getattr(card, attr) != new_value:
            skipped += 1
            continue
        setattr(card, attr, new_value - delta)
        cards.append(card)
    if cards:
        col.update_cards(cards)
    return len(cards), skipped


# ── History (lives in the add-on's user_files, per profile) ───────────────────


class History:
    """A stack of undoable actions saved to a JSON file.

    Entry: {"id", "time", "kind", "label", "data", "undone", "note"}
    kinds: "ahead" {deck_id, built_at}, "freeze" {prev, frozen_at},
           "unfreeze" {prev}, "shift" {days, changes},
           "cleanup" {card_ids, name, built_at, total}
    "note" says how an entry was undone or ended ("Undone with Edit > Undo").
    """

    def __init__(self, path: str):
        self.path = path
        self.entries: list[dict] = []
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                self.entries = json.load(f)
        except (OSError, ValueError):
            self.entries = []

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.entries, f)
        os.replace(tmp, self.path)

    def add(self, kind: str, label: str, data: dict) -> None:
        self.entries.append(
            {
                "id": int(time.time() * 1000),
                "time": int(time.time()),
                "kind": kind,
                "label": label,
                "data": data,
                "undone": False,
                "note": "",
            }
        )
        self.entries = self.entries[-HISTORY_LIMIT:]
        self.save()

    def last_active(self) -> dict | None:
        for entry in reversed(self.entries):
            if not entry["undone"]:
                return entry
        return None

    def current_ahead(self, built_at) -> dict | None:
        """The entry that built the current Study Ahead deck."""
        for entry in reversed(self.entries):
            if entry["kind"] == "ahead" and entry["data"].get("built_at") == built_at:
                return entry
        return None


def undo_entry(col: Collection, entry: dict) -> str:
    """Reverse one history entry. Returns a message for the user."""
    kind, data = entry["kind"], entry["data"]
    if kind == "ahead":
        if ahead_deck_id(col) and (
            data.get("built_at") is None
            or get_state(col)["ahead_built_at"] == data.get("built_at")
        ):
            remove_study_ahead(col)
            return "Removed the Study Ahead deck. Unfinished cards are back in their decks."
        return "The Study Ahead deck was already gone."
    if kind == "cleanup":
        did, count = restore_study_ahead(
            col, data["card_ids"], data["name"], data.get("built_at"), data.get("total", 0)
        )
        if did:
            return f"Brought back the Study Ahead deck with {count} cards."
        return "Those cards have all been studied or moved since, so there's nothing to bring back."
    if kind == "shift":
        restored, skipped = revert_changes(col, data["changes"])
        msg = f"Moved {restored} cards back to their earlier due dates."
        if skipped:
            msg += f" Left {skipped} alone because they were reviewed or changed since."
        return msg
    if kind in ("freeze", "unfreeze"):
        prev = dict(data["prev"])
        # Freeze state goes back; the Study Ahead deck is left as it is now.
        current = get_state(col)
        for key in AHEAD_KEYS:
            prev[key] = current[key]
        if kind == "unfreeze" and prev.get("last_shift_day") is not None:
            # Don't retroactively freeze days you may already have studied.
            prev["last_shift_day"] = max(prev["last_shift_day"], col.sched.today)
        save_state(col, prev, undoable=True)
        return "Freeze cancelled." if kind == "freeze" else "Frozen again."
    return "Nothing to undo."


AHEAD_KEYS = ("ahead_deck_id", "ahead_built_at", "ahead_total", "ahead_day")

EDIT_UNDO_NOTE = "Undone with Edit > Undo"


def in_effect(col: Collection, entry: dict, state: dict) -> bool | None:
    """Whether an entry's change is still in place. None = can't tell (older
    entries saved before this was tracked)."""
    kind, data = entry["kind"], entry["data"]
    if kind == "ahead":
        built = data.get("built_at")
        if built is None:
            return None
        return bool(ahead_deck_id(col)) and state["ahead_built_at"] == built
    if kind == "cleanup":
        return not (ahead_deck_id(col) and state["ahead_built_at"] == data.get("built_at"))
    if kind == "freeze":
        fa = data.get("frozen_at")
        if fa is None:
            return None
        return bool(state["frozen"]) and state["frozen_at"] == fa
    if kind == "unfreeze":
        fa = data["prev"].get("frozen_at")
        if fa is None:
            return None
        return not (state["frozen"] and state["frozen_at"] == fa)
    if kind == "shift":
        sample = data["changes"][:50]
        if not sample:
            return None
        ids = ",".join(str(int(c[0])) for c in sample)
        now = {cid: (d, od) for cid, d, od in col.db.all(
            f"select id, due, odue from cards where id in ({ids})"
        )}
        return any(
            cid in now and now[cid][field] == value for cid, field, value, _ in sample
        )
    return None


def reconcile(col: Collection, entries: list[dict], edit_undo: bool = False) -> bool:
    """Bring each entry's undone flag in line with the collection, so things
    undone with Edit > Undo, redone, or deleted by hand show correctly.

    edit_undo: the last thing Anki did was Edit > Undo of one of our actions.
    Returns True if anything changed.
    """
    state = get_state(col)
    changed = False
    for i, entry in enumerate(entries):
        entry.setdefault("note", "")
        data = entry["data"]
        live = in_effect(col, entry, state)
        if live is None:
            continue
        if entry["kind"] == "freeze" and not live and _ended_by_unfreeze(col, entry, entries[i + 1:], state):
            # Unfrozen normally: still part of the undo stack, just over.
            live, ended = True, "Ended when you unfroze"
        else:
            ended = ""
        if live:
            if entry["undone"] or entry["note"] != ended:
                entry["undone"] = False
                entry["note"] = ended
                data.pop("ended", None)
                changed = True
        elif not entry["undone"]:
            if entry["kind"] == "shift" and not edit_undo:
                # Cards also change when you review them; only trust Edit > Undo.
                continue
            entry["undone"] = True
            if data.get("ended"):
                entry["note"] = data["ended"]
            elif edit_undo:
                entry["note"] = EDIT_UNDO_NOTE
            elif entry["kind"] == "ahead":
                entry["note"] = "Deck deleted"
            else:
                entry["note"] = "Undone in Anki"
            changed = True
    return changed


def _ended_by_unfreeze(col, entry, later: list[dict], state: dict) -> bool:
    fa = entry["data"].get("frozen_at")
    for other in later:
        if (
            other["kind"] == "unfreeze"
            and other["data"]["prev"].get("frozen_at") == fa
            and in_effect(col, other, state)
        ):
            return True
    return False
