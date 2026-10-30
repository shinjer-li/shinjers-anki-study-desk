"""
The Study Day tab: today's numbers against your usual range, the Ahead deck,
forecast and pace charts, Study ahead / Freeze, and the history with undo.
Drawn by web/js/study_day.js.
"""

from __future__ import annotations

import datetime

from aqt import mw

from .. import window
from ..common.deck_picker import choose_decks
from ..tab import Tab
from . import actions, core, ranges, status

HISTORY_SHOWN = 5


def fmt_time(ts: int) -> str:
    """'Today 7:42 PM', 'Yesterday 9:05 AM' or 'Sun Oct 25, 4:00 AM'."""
    when = datetime.datetime.fromtimestamp(ts)
    days = (datetime.date.today() - when.date()).days
    clock = when.strftime("%I:%M %p").lstrip("0")
    if days == 0:
        return f"Today {clock}"
    if days == 1:
        return f"Yesterday {clock}"
    return f"{when.strftime('%a %b %d')}, {clock}"


def _anki_today() -> datetime.date:
    """Anki's today: before the day cutoff (4am by default) it's still yesterday."""
    return datetime.date.fromtimestamp(mw.col.sched.day_cutoff - 86400)


def _days(start: int, count: int) -> list[dict]:
    """Labels for `count` days starting `start` days from today."""
    today = _anki_today()
    out = []
    for i in range(start, start + count):
        d = today + datetime.timedelta(days=i)
        out.append({"wd": d.strftime("%a"), "date": d.strftime("%b %d").replace(" 0", " ")})
    return out


def _row(label, value, unit, rng=None, partial=False, digits=0, note=""):
    return {
        "label": label,
        "value": value,
        "unit": unit,
        "digits": digits,
        "flag": ranges.flag(value, rng, partial),
        "range": list(rng) if rng else None,
        "note": note,
    }


def lab_rows(snap: dict) -> list[dict]:
    fc, pace = snap["forecast"], snap["pace"]
    secs = pace["secs_per_review"]
    reviews, mins = pace["reviews"], pace["minutes"]
    daily = ranges.normal_range(reviews[:-1])
    per_card_days = [m * 60 / r for r, m in zip(reviews[:-1], mins[:-1]) if r >= 10]

    due, tomorrow, week = fc["due"][0], fc["due"][1], sum(fc["due"][1:8])
    rows = [
        _row("Due today", due, f"cards · ≈ {status.minutes(due, secs)}", daily),
        _row("Reviews today", reviews[-1], "reviews", daily, partial=True),
        _row("Study time today", round(mins[-1]), "min", ranges.normal_range(mins[:-1]), partial=True),
        _row("Tomorrow", tomorrow, f"due · ≈ {status.minutes(tomorrow, secs)}", daily),
        _row("Next 7 days", week, "due", ranges.scale(daily, 7)),
    ]
    if reviews[-1] >= 10:
        rows.append(_row("Time per card", round(mins[-1] * 60 / reviews[-1], 1), "s today",
                         ranges.normal_range(per_card_days), digits=1))
    else:
        rows.append(_row("Time per card", secs, "s average", digits=1,
                         note="today's shows after 10 reviews"))
    rows.append(_row("New cards left", core.new_count(mw.col, snap["settings"]["decks"]),
                     "unseen", note="no range"))
    return rows


def history() -> dict:
    hist = actions.history()
    nxt = hist.last_active()
    entries = [
        {
            "when": fmt_time(e["time"]),
            "kind": e["kind"],
            "label": e["label"],
            "undone": bool(e["undone"]),
            "note": e.get("note", ""),
            "next": e is nxt,
        }
        for e in reversed(hist.entries)
    ]
    return {"entries": entries, "shown": HISTORY_SHOWN}


class StudyDayTab(Tab):
    id = "study_day"
    title = "Study Day"
    icon = "calendar"
    live = True

    def data(self, desk) -> dict:
        col = mw.col
        actions.sync_history()
        snap = status.snapshot(col)
        settings, state = snap["settings"], snap["state"]
        decks = settings["decks"]
        pace = snap["pace"]

        frozen = None
        if state["frozen"]:
            since = state["frozen_at"]
            frozen = {"day": core.paused_days(col), "since": fmt_time(since) if since else "earlier"}
        ahead = snap["ahead"]
        if ahead:
            built = ahead["built_at"]
            ahead["created"] = fmt_time(built // 1000) if built else "earlier"
            ahead["minutes"] = status.minutes(ahead["left"], pace["secs_per_review"])

        daily = ranges.normal_range(pace["reviews"][:-1])
        year = core.pace(col, decks, status.PACE_MAX_DAYS)
        return {
            "now": _anki_today().strftime("%a %b %d").replace(" 0", " "),
            "decks": core.describe_decks(col, decks),
            "head": status.headline(col, snap),
            "rows": lab_rows(snap),
            "range_days": status.PAST_DAYS,
            "ahead": ahead,
            "ahead_name": core.ahead_name(col, decks),
            "frozen": frozen,
            "forecast": {
                "due": snap["forecast"]["due"],
                "ahead": snap["forecast"]["ahead"],
                "pullable": snap["forecast"]["pullable"],
                "days": _days(0, status.FORECAST_DAYS + 1),
                "range": list(daily) if daily else None,
                "show": settings["forecast_days"],
            },
            # Up to a year of days; the page shows the span picked (pace_days)
            # and works out the averages for it. The range stays the 30-day one.
            "pace": {
                "reviews": year["reviews"],
                "minutes": year["minutes"],
                "days": _days(-(status.PACE_MAX_DAYS - 1), status.PACE_MAX_DAYS),
                "range": list(daily) if daily else None,
                "show": settings["pace_days"] if settings["pace_days"] in status.PACE_SPANS else 30,
            },
            "form": {"days": settings["days_ahead"], "extra": settings["extra_new"]},
            # Cards Study ahead would pull for 1..7 days, so the headline button
            # can follow the days picked in the form.
            "ahead_counts": [] if ahead else core.ahead_counts(col, decks, 7),
            "history": history(),
        }

    def handle(self, desk, cmd, arg) -> None:
        settings = core.get_settings(mw.col)
        done = desk.refresh
        if cmd == "create" and isinstance(arg, dict):
            days = max(1, min(7, int(arg.get("days", 1))))
            extra = max(0, min(500, int(arg.get("extra", 0))))
            settings.update(days_ahead=days, extra_new=extra)
            core.save_settings(mw.col, settings)
            actions.study_ahead(desk, settings["decks"], days, extra, done)
        elif cmd == "ahead":
            # "Study tomorrow's N now" from the headline.
            actions.study_ahead(desk, settings["decks"], 1, int(settings["extra_new"]), done)
        elif cmd == "remove":
            actions.remove_study_ahead(desk, done)
        elif cmd == "study":
            actions.open_ahead_deck()
        elif cmd == "freeze":
            actions.freeze(desk, arg == "tomorrow", done)
        elif cmd == "unfreeze":
            actions.unfreeze(desk, done)
        elif cmd == "undo":
            actions.undo_last(desk, done)
        elif cmd == "decks":
            self.set_setting(desk, "decks", None)
        elif cmd == "forecast" and arg in ("7", "14", "30"):
            # The page redraws the chart itself; just remember the choice.
            settings["forecast_days"] = int(arg)
            core.save_settings(mw.col, settings)
        elif cmd == "pace" and arg in [str(n) for n in status.PACE_SPANS]:
            settings["pace_days"] = int(arg)
            core.save_settings(mw.col, settings)

    # ── settings ──────────────────────────────────────────────────────────────

    def settings(self) -> list[dict]:
        s = core.get_settings(mw.col)
        return [
            {
                "title": "Study Day",
                "rows": [
                    {"key": "decks", "type": "decks", "label": "Decks",
                     "text": core.describe_decks(mw.col, s["decks"]),
                     "hint": "Study ahead, Freeze and the numbers use these decks."},
                    {"key": "banner", "type": "choice", "label": "Status bar on the Decks screen",
                     "value": s["banner"],
                     "options": [["full", "Full"], ["compact", "Compact"], ["off", "Off"]]},
                    {"key": "auto_finish", "type": "switch", "value": s["auto_finish"],
                     "label": "Remove the Ahead deck when it's finished"},
                    {"key": "new_day_cleanup", "type": "switch", "value": s["new_day_cleanup"],
                     "label": "Send unfinished Ahead cards back overnight",
                     "hint": "They return to their decks with their original due dates."},
                ],
            }
        ]

    def set_setting(self, desk, key, value) -> None:
        col = mw.col
        s = core.get_settings(col)
        if key == "decks":
            chosen = choose_decks(col, s["decks"], desk, "Decks to include")
            if chosen is None:
                return
            s["decks"] = chosen
        elif key == "banner":
            if value not in core.BANNER_MODES:
                return
            s["banner"] = value
        elif key in ("auto_finish", "new_day_cleanup"):
            s[key] = bool(value) and value != "0"
        else:
            return
        core.save_settings(col, s)
        changed()


def changed() -> None:
    """A Study Day setting changed: redraw everything that shows it."""
    window.rerender("study_day")
    window.rerender("settings")
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()
