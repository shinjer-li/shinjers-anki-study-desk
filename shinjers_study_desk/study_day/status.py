"""
The headline for the day ("12 cards left today", "Frozen", ...), shared by the
Study Day tab and the Decks-screen status bar so they always agree.
"""

from __future__ import annotations

from . import core

FORECAST_DAYS = 30
PAST_DAYS = 30
PACE_MAX_DAYS = 365  # the Pace chart can look back up to a year
PACE_SPANS = (30, 90, 180, 365)


def snapshot(col) -> dict:
    """Everything the headline and the tab are worked out from, read once."""
    settings = core.get_settings(col)
    decks = settings["decks"]
    return {
        "settings": settings,
        "state": core.get_state(col),
        "forecast": core.forecast(col, decks, FORECAST_DAYS),
        "pace": core.pace(col, decks, PAST_DAYS),
        "ahead": core.ahead_info(col),
        "new_left": core.new_left_today(col, decks),
    }


def minutes(cards: int, secs: float) -> str:
    return minutes_text(max(1, round(cards * secs / 60)) if cards else 0)


def minutes_text(m: int) -> str:
    return f"{m // 60}h {m % 60}m" if m >= 60 else f"{m} min"


def study_minutes(pace: dict, reviews: int, new: int) -> int:
    """Minutes for `reviews` reviews plus `new` new cards (each new card is
    timed through all its learning steps)."""
    secs = reviews * pace["secs_per_review"] + new * pace["secs_per_new"]
    return max(1, round(secs / 60)) if reviews or new else 0


def cards_text(reviews: int, new: int, bold: bool = False) -> str:
    """"120 reviews + 22 new", leaving out a part that's zero. bold=True
    wraps the numbers in <b> for the status bar."""
    num = (lambda n: f"<b>{n:,}</b>") if bold else (lambda n: f"{n:,}")
    parts = []
    if reviews:
        parts.append(f"{num(reviews)} {'review' if reviews == 1 else 'reviews'}")
    if new:
        parts.append(f"{num(new)} new")
    return " + ".join(parts)


def headline(col, snap: dict) -> dict:
    """{state, title, lede, short, actions: [{cmd, label}]}, most urgent
    first. `cmd` is one of: unfreeze, study, remove, ahead."""
    state = snap["state"]
    info = snap["ahead"]
    due = snap["forecast"]["due"][0]
    secs = snap["pace"]["secs_per_review"]

    if state["frozen"]:
        day = core.paused_days(col)
        if day == 0:
            return {
                "state": "frozen",
                "title": "Frozen from tomorrow",
                "lede": "Today counts as normal. From tomorrow, every scheduled card "
                "moves back a day while you're away, so nothing piles up.",
                "short": "Frozen from tomorrow",
                "actions": [{"cmd": "unfreeze", "label": "Unfreeze"}],
            }
        return {
            "state": "frozen",
            "title": "Frozen",
            "lede": f"Day {day} of your break. Every scheduled card moves back a day, "
            "so nothing piles up.",
            "short": f"Frozen, day {day}",
            "actions": [{"cmd": "unfreeze", "label": "Unfreeze"}],
        }
    if info and info["due_now"]:
        n = info["due_now"]
        return {
            "state": "alert",
            "title": f"{n} Ahead {'card is' if n == 1 else 'cards are'} due today",
            "lede": f"They're still in {info['name']}, so your normal decks don't count "
            "them. Study them there, or send them back to their decks.",
            "short": f"{n} due in the Ahead deck",
            "actions": [
                {"cmd": "study", "label": "Study them"},
                {"cmd": "remove", "label": "Send them back"},
            ],
        }
    new = snap["new_left"]
    if due or new:
        n = due + new
        mins = minutes_text(study_minutes(snap["pace"], due, new))
        actions = [{"cmd": "study", "label": "Study Ahead deck"}] if info else []
        pace = f"{secs:g} s per review" + (f", {snap['pace']['secs_per_new']:g} s per new card" if new else "")
        return {
            "state": "due",
            "title": f"{n} {'card' if n == 1 else 'cards'} left today",
            "lede": f"{cards_text(due, new)}. About {mins} at your pace of {pace}.",
            "short": f"{n} left today",
            "actions": actions,
        }
    if info:
        return {
            "state": "ahead",
            "title": "Studying ahead",
            "lede": f"Today's reviews are done. {info['left']} of {info['total']} cards "
            f"left in {info['name']}.",
            "short": f"Ahead, {info['left']} left",
            "actions": [
                {"cmd": "study", "label": "Study now"},
                {"cmd": "remove", "label": "Remove"},
            ],
        }
    tomorrow = core.ahead_count(col, snap["settings"]["decks"], 1)
    lede = "Nothing else is due today."
    actions = []
    if tomorrow:
        lede += " Upcoming cards can be studied now with Study ahead; pick how many days on the right."
        actions.append({"cmd": "ahead", "label": f"Study tomorrow's {tomorrow} now"})
    return {
        "state": "done",
        "title": "All caught up",
        "lede": lede,
        "short": "All caught up",
        "actions": actions,
    }
