"""
The Trouble Spots tab: topics ranked by how often you miss them, with your
own reference range, and the cards behind each topic. Read-only.
Drawn by web/js/trouble.js.
"""

from __future__ import annotations

import os
import time

import aqt
from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QFileDialog, QUrl
from aqt.utils import openLink, showWarning, tooltip

from .. import window
from ..common.deck_picker import choose_decks
from ..study_day import ranges
from ..tab import Tab
from . import analysis as a

TOPICS_SHOWN = 300
CARDS_SHOWN = 100
MIN_TOPIC_REVIEWS = 10  # topics with fewer reviews don't shape the range
# A sensible detail level for each kind of grouping.
DEFAULT_DEPTH = {"firstaid": 3, "systems": 2, "deck": 2, "custom": 1}


class TroubleTab(Tab):
    id = "trouble"
    title = "Trouble Spots"
    icon = "target"

    def __init__(self):
        self.result: a.Result | None = None
        self.error = ""
        self.selected: int | None = None
        self._run_id = 0
        # What `result` was computed from; unchanged means no need to redo it.
        self._result_key: tuple | None = None

    # ── data ──────────────────────────────────────────────────────────────────

    def data(self, desk) -> dict:
        """Show what we have now, and crunch fresh numbers in the background
        only if the collection or the settings changed since last time."""
        if self.result is not None and self._result_key == self._key():
            return self._payload()
        self._load(desk)
        return self._payload(loading=True)

    def _key(self) -> tuple:
        s = a.get_settings(mw.col)
        return (mw.col.mod, s["decks"], s["days"], s["group"], s["depth"],
                s["custom"], s["include_learning"], time.strftime("%Y-%m-%d"))

    def _load(self, desk) -> None:
        s = a.get_settings(mw.col)
        key = self._key()
        self._run_id += 1
        run_id = self._run_id

        def done(result):
            if run_id != self._run_id:
                return
            # Keep the same topic selected after a reload, wherever it now ranks.
            picked = self._topic()
            names = [t.name for t in result.topics]
            self.result, self.error = result, ""
            self._result_key = key
            if picked is not None and picked.name in names:
                self.selected = names.index(picked.name)
            else:
                self.selected = next((i for i, t in enumerate(result.topics) if t.again), None)
            self._send()

        def failed(exc):
            if run_id != self._run_id:
                return
            self.result, self.error = None, str(exc)
            self._send()  # replace the "Reading your reviews…" placeholder
            if not isinstance(exc, ValueError):
                showWarning(f"Trouble Spots couldn't load:\n\n{exc}", parent=window.current() or mw)

        QueryOp(
            parent=desk,
            op=lambda col: a.analyze(
                col, s["decks"], s["days"], s["group"], s["depth"],
                s["custom"], s["include_learning"],
            ),
            success=done,
        ).failure(failed).run_in_background()

    def _send(self) -> None:
        desk = window.current()
        if desk is not None:
            desk.receive(self.id, self._payload())

    def _controls(self) -> dict:
        s = a.get_settings(mw.col)
        return {
            "decks": _describe(s["decks"]),
            "days": s["days"],
            "periods": [[d, "All" if d == 0 else f"{d}d"] for d, _ in a.PERIODS],
            "group": s["group"],
            "groups": [[k, label] for k, (label, _, _) in a.GROUPS.items()],
            "depth": int(s["depth"]),
            "custom": s["custom"],
        }

    def _payload(self, loading: bool = False) -> dict:
        out = {"controls": self._controls(), "loading": loading, "error": self.error}
        r = self.result
        if r is None:
            return out
        rng = topic_range(r)
        out.update(
            summary={
                "reviews": r.total_reviews,
                "cards": r.cards_studied,
                "again": r.total_again,
                "rate": r.again_rate,
                "label": r.group_label,
            },
            range=list(rng) if rng else None,
            topics=[
                {
                    "name": t.name,
                    "cards": t.cards,
                    "missed": t.missed_cards,
                    "reviews": t.reviews,
                    "again": t.again,
                    "trouble": t.trouble,
                    "flag": "H" if rng and t.trouble > rng[1] else "",
                }
                for t in r.topics[:TOPICS_SHOWN]
            ],
            topic_count=len(r.topics),
            fsrs=r.uses_fsrs,
            **self._drill(),
        )
        return out

    def _drill(self) -> dict:
        r = self.result
        topic = self._topic()
        missed = r.missed_cards(topic.name if topic else None)
        cards = []
        for c in missed[:CARDS_SHOWN]:
            if r.uses_fsrs:
                strength = f"{c.difficulty:.1f}/10" if c.difficulty else "–"
            else:
                strength = f"{c.ease}%" if c.ease else "–"
            cards.append({
                "cid": c.cid,
                "text": c.text,
                "again": c.again,
                "reviews": c.reviews,
                "lapses": c.lapses,
                "strength": strength,
                "deck": c.deck.split("::")[-1],
            })
        return {"selected": self.selected if topic else None, "cards": cards,
                "card_total": len(missed)}

    def _topic(self) -> a.TopicStat | None:
        r = self.result
        if r is None or self.selected is None or self.selected >= len(r.topics):
            return None
        return r.topics[self.selected]

    # ── commands ──────────────────────────────────────────────────────────────

    def handle(self, desk, cmd, arg) -> None:
        if cmd == "set" and isinstance(arg, dict):
            self._set(desk, arg)
        elif cmd == "decks":
            s = a.get_settings(mw.col)
            chosen = choose_decks(mw.col, s["decks"], desk, "Trouble Spots: choose decks")
            if chosen is not None:
                s["decks"] = chosen
                a.save_settings(mw.col, s)
                self._reload(desk)
        elif cmd == "select":
            if self.result is None:
                return
            i = int(arg) if str(arg).lstrip("-").isdigit() else -1
            self.selected = None if i < 0 or i == self.selected else i
            desk.patch(self.id, self._drill())
        elif cmd == "browse":
            self._browse()
        elif cmd == "card" and str(arg).isdigit():
            _open_in_browser([int(arg)])
        elif cmd == "export" and arg in ("html", "csv"):
            self._export(desk, arg)
        elif cmd == "refresh":
            self._reload(desk)

    def _set(self, desk, changes: dict) -> None:
        s = a.get_settings(mw.col)
        if "days" in changes and int(changes["days"]) in {d for d, _ in a.PERIODS}:
            s["days"] = int(changes["days"])
        if changes.get("group") in a.GROUPS:
            s["group"] = changes["group"]
            s["depth"] = DEFAULT_DEPTH.get(s["group"], 1)
        if "depth" in changes:
            s["depth"] = max(1, min(6, int(changes["depth"])))
        if "custom" in changes:
            s["custom"] = str(changes["custom"]).strip()
        a.save_settings(mw.col, s)
        self._reload(desk)

    def _reload(self, desk) -> None:
        self.selected = None
        desk.receive(self.id, self._payload(loading=True))
        self._load(desk)

    def _browse(self) -> None:
        if self.result is None:
            return
        topic = self._topic()
        cids = [c.cid for c in self.result.missed_cards(topic.name if topic else None)]
        if not cids:
            tooltip("No missed cards to show.")
            return
        _open_in_browser(cids)

    def _export(self, desk, ext: str) -> None:
        if self.result is None:
            return
        folder = os.path.expanduser("~/Desktop")
        if not os.path.isdir(folder):
            folder = os.path.expanduser("~")
        kind = "Web page" if ext == "html" else "Spreadsheet"
        name = f"Trouble Spots {time.strftime('%Y-%m-%d')}.{ext}"
        path, _ = QFileDialog.getSaveFileName(
            desk, "Save", os.path.join(folder, name), f"{kind} (*.{ext})"
        )
        if not path:
            return
        if ext == "html":
            content = a.export_html(self.result, self._subtitle())
        else:
            content = a.export_csv(self.result)
        try:
            # The BOM tells Excel it's UTF-8 (otherwise "›" shows up as "â€º").
            encoding = "utf-8" if ext == "html" else "utf-8-sig"
            with open(path, "w", encoding=encoding, newline="") as f:
                f.write(content)
        except OSError as exc:
            showWarning(f"Couldn't save the file:\n\n{exc}", parent=desk)
            return
        openLink(QUrl.fromLocalFile(path))

    def _subtitle(self) -> str:
        s = a.get_settings(mw.col)
        period = dict(a.PERIODS).get(s["days"], "")
        return f"{_describe(s['decks'])} · {period.lower()}"

    # ── settings ──────────────────────────────────────────────────────────────

    def settings(self) -> list[dict]:
        s = a.get_settings(mw.col)
        return [
            {
                "title": "Trouble Spots",
                "rows": [
                    {"key": "include_learning", "type": "switch",
                     "value": bool(s["include_learning"]),
                     "label": "Count misses on new cards",
                     "hint": "Off: only misses on cards you'd already learned count, "
                     "since missing brand-new cards is normal."},
                ],
            }
        ]

    def set_setting(self, desk, key, value) -> None:
        if key != "include_learning":
            return
        s = a.get_settings(mw.col)
        s["include_learning"] = bool(value) and value != "0"
        a.save_settings(mw.col, s)
        self.result = None
        window.rerender("settings")


def topic_range(r: a.Result) -> tuple[float, float] | None:
    """Your usual miss rate across topics: the middle 80% of topics with
    enough reviews to say."""
    values = [t.trouble for t in r.topics if t.reviews >= MIN_TOPIC_REVIEWS]
    return ranges.normal_range(values)


def _open_in_browser(cids: list[int]) -> None:
    aqt.dialogs.open("Browser", mw, search=("cid:" + ",".join(map(str, cids)),))


def _describe(deck_ids: list[int]) -> str:
    names = [mw.col.decks.name(d) for d in deck_ids if mw.col.decks.get(d, default=False)]
    return ", ".join(names) if names else "All decks"
