"""
The Keyboard tab: every shortcut on the review screen, the deck overview and
app-wide, with a "press a key" editor. When the key is already taken, the page
asks what should happen to the action that had it. Drawn by web/js/keyboard.js.
"""

from __future__ import annotations

import re

from aqt import mw

from .. import prefs, window
from ..tab import Tab
from . import remap
from .resolver import DELETE, POLICIES, SPARE, SWAP

SCOPES = [
    ("review", "Review", "While studying cards."),
    ("overview", "Deck overview", "The screen with a deck's Study Now button."),
    ("global", "Everywhere", "Work on every screen, unless a screen uses the same key."),
]

POLICY_LABELS = {SWAP: "Swap keys", SPARE: "Give it a spare key", DELETE: "Unbind it"}

LABELS = {
    "again": "Again", "hard": "Hard", "good": "Good", "easy": "Easy",
    "show_answer": "Show answer", "undo": "Undo",
    "suspend_card": "Suspend card", "suspend_note": "Suspend note", "mark": "Mark note",
    "bury_card": "Bury card", "bury_note": "Bury note", "edit": "Edit note",
    "more_menu": "More menu", "replay_audio": "Replay audio", "pause_audio": "Pause audio",
    "seek_backward": "Audio back 5 s", "seek_forward": "Audio forward 5 s",
    "record_voice": "Record own voice", "replay_voice": "Replay own voice",
    "deck_options": "Deck options", "card_info": "Card info",
    "previous_card_info": "Previous card info", "forget": "Reset card",
    "create_copy": "Create copy", "delete_note": "Delete note",
    "set_due_date": "Set due date", "auto_advance": "Auto advance",
    "rebuild": "Rebuild filtered deck", "empty": "Empty filtered deck",
    "custom_study": "Custom study", "unbury": "Unbury",
    "decks": "Decks", "study": "Study", "add": "Add", "browse": "Browse",
    "stats": "Stats", "sync": "Sync", "debug_console": "Debug console",
    "undo_menu": "Undo", "redo_menu": "Redo", "preferences": "Preferences",
    "switch_profile": "Switch profile", "import": "Import", "export": "Export",
    "study_deck": "Study deck", "create_filtered_deck": "Create filtered deck",
    "note_types": "Note types", "addons": "Add-ons", "exit": "Exit", "guide": "Guide",
    "full_screen": "Full screen", "zoom_in": "Zoom in", "zoom_out": "Zoom out",
    "reset_zoom": "Reset zoom",
    "reveal_next": "Reveal next cloze", "reveal_all": "Reveal all clozes",
    "hint_next": "Open next hint", "hint_all": "Open all hints",
    "copy_image": "Copy image", "copy_text": "Copy card text",
    **{f"flag_{i}": f"Flag {c}" for i, c in enumerate(
        ["red", "orange", "green", "blue", "pink", "turquoise", "purple"], 1)},
}

# Rows are grouped so the long lists are easy to scan. Anything not listed
# goes in the last group.
GROUPS = {
    "review": [
        ("Answer", ["again", "hard", "good", "easy", "show_answer", "undo"]),
        ("Card", ["mark", *[f"flag_{i}" for i in range(1, 8)], "suspend_card",
                  "suspend_note", "bury_card", "bury_note", "edit", "forget",
                  "set_due_date", "create_copy", "delete_note"]),
        ("AnKing & copy", ["reveal_next", "reveal_all", "hint_next", "hint_all",
                           "copy_text", "copy_image"]),
        ("Audio", ["replay_audio", "pause_audio", "seek_backward", "seek_forward",
                   "record_voice", "replay_voice"]),
        ("Other", []),
    ],
    "overview": [("Deck", [])],
    "global": [
        ("Screens", ["decks", "study", "add", "browse", "stats", "sync"]),
        ("Menus", []),
    ],
}


def label(name: str) -> str:
    if name in LABELS:
        return LABELS[name]
    if name.startswith("key:"):
        return f"Another add-on's {name[4:]} key"
    if name.startswith("menu:"):
        words = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name[5:].removeprefix("action"))
        return words.replace("_", " ").strip().capitalize() or name
    return name.replace("_", " ").capitalize()


class KeyboardTab(Tab):
    id = "keyboard"
    title = "Keyboard"
    icon = "keyboard"

    # ── data ──────────────────────────────────────────────────────────────────

    def _states(self) -> dict:
        """scope -> (defaults, result, notes, errors)."""
        remap.app_wide.collect()
        reports = remap.preview_reports()
        out = {}
        for state, screen in (("review", mw.reviewer), ("overview", mw.overview)):
            try:
                defaults = remap.default_bindings(state, list(screen._shortcutKeys()))
            except Exception:
                defaults = {}
            out[state] = (defaults, *reports[state])
        aw = remap.app_wide
        result = {n: aw.result.get(n, keys) for n, keys in aw.original.items()}
        out["global"] = (aw.original, result, aw.notes, aw.errors)
        return out

    def data(self, desk) -> dict:
        cfg = prefs.keyboard()
        states = self._states()
        scopes = []
        for scope, title, hint in SCOPES:
            defaults, result, notes, errors = states[scope]
            configured = {remap.norm(n[4:]) if n.startswith("key:") else n
                          for n in (cfg.get(scope) or {})}
            rows = []
            for name, keys in result.items():
                if scope == "global" and not keys and not defaults.get(name):
                    continue  # menu items with no shortcut at all
                rows.append({
                    "name": name,
                    "label": label(name),
                    "keys": keys,
                    "defaults": defaults.get(name, []),
                    "note": notes.get(name, ""),
                    "changed": name in configured
                    or (name.startswith("key:") and name[4:] in configured),
                    "smart": scope == "review" and name == "undo" and cfg.get("smart_undo", True),
                })
            scopes.append({"id": scope, "title": title, "hint": hint,
                           "groups": _group(scope, rows), "errors": errors})
        return {
            "scopes": scopes,
            "policy": remap.policy(),
            "policies": [[p, POLICY_LABELS[p]] for p in POLICIES],
        }

    # ── commands ──────────────────────────────────────────────────────────────

    def handle(self, desk, cmd, arg) -> None:
        cfg = prefs.keyboard()
        if cmd == "bind" and isinstance(arg, dict):
            if not self._bind(cfg, arg):
                return
        elif cmd in ("clear", "reset") and isinstance(arg, dict) and arg.get("name"):
            if arg.get("scope") not in {s for s, _, _ in SCOPES}:
                return
            section = cfg.setdefault(arg.get("scope"), {})
            if cmd == "clear":
                section[arg["name"]] = []
            else:
                section.pop(arg["name"], None)
        elif cmd == "reset_all":
            for scope, _, _ in SCOPES:
                cfg[scope] = {}
        else:
            return
        prefs.save_keyboard(cfg)
        changed()

    def _bind(self, cfg: dict, arg: dict) -> bool:
        scope, name = arg.get("scope"), arg.get("name")
        key = remap.norm(str(arg.get("key", "")))
        if scope not in {s for s, _, _ in SCOPES} or not name or not key:
            return False
        _, result, _, _ = self._states()[scope]
        section = cfg.setdefault(scope, {})
        old = result.get(name, [])
        section[name] = [key]
        holder = next((n for n, ks in result.items() if key in ks and n != name), None)
        if holder:
            how = arg.get("resolve") if arg.get("resolve") in POLICIES else remap.policy()
            # The holder only loses this key; any other keys it has stay.
            rest = [k for k in result[holder] if k != key]
            freed = [k for k in old if k != key][:1]
            if how == SWAP and freed:
                section[holder] = rest + [k for k in freed if k not in rest]
            elif how == DELETE or rest:
                section[holder] = rest
            else:
                # Spare, or a swap with no old key to give: hand out a spare key.
                used = {k for ks in result.values() for k in ks} | remap.app_wide.all_keys()
                spare = next((k for k in remap.spare_keys() if k not in used and k != key), None)
                section[holder] = [spare] if spare else []
        return True

    # ── settings ──────────────────────────────────────────────────────────────

    def settings(self) -> list[dict]:
        cfg = prefs.keyboard()
        return [
            {
                "title": "Keyboard",
                "rows": [
                    {"key": "on_conflict", "type": "choice", "value": remap.policy(),
                     "label": "When a key is taken",
                     "options": [[p, POLICY_LABELS[p]] for p in POLICIES],
                     "hint": "What happens to the action that had the key. "
                     "You can still pick each time on the Keyboard tab."},
                    {"key": "smart_undo", "type": "switch",
                     "value": bool(cfg.get("smart_undo", True)),
                     "label": "Smart undo while reviewing",
                     "hint": "With the answer showing, undo flips back to the question. "
                     "Never undoes past the start of the session."},
                ],
            }
        ]

    def set_setting(self, desk, key, value) -> None:
        cfg = prefs.keyboard()
        if key == "on_conflict" and value in POLICIES:
            cfg["on_conflict"] = value
        elif key == "smart_undo":
            cfg["smart_undo"] = bool(value) and value != "0"
        else:
            return
        prefs.save_keyboard(cfg)
        changed()


def _group(scope: str, rows: list[dict]) -> list[dict]:
    groups = GROUPS[scope]
    order = {name: (gi, i) for gi, (_, names) in enumerate(groups) for i, name in enumerate(names)}
    rest = len(groups) - 1
    buckets: list[list[dict]] = [[] for _ in groups]
    for row in sorted(rows, key=lambda r: order.get(r["name"], (rest, 999))):
        buckets[order.get(row["name"], (rest, 0))[0]].append(row)
    return [{"title": t, "rows": b} for (t, _), b in zip(groups, buckets) if b]


def changed() -> None:
    """Keyboard config changed (here, on the Settings tab or in the config
    editor): rebind, and redraw whatever shows it."""
    remap.apply_config()
    window.rerender("keyboard")
    window.rerender("settings")
