"""
Keyboard shortcuts: change any Anki shortcut on the review screen, the deck
overview, or everywhere. The bindings live in the add-on config under
"keyboard" and are edited on the Keyboard tab (or in the config editor).

Ported from Keybind Remapper; the conflict rules are in resolver.py.
"""

from functools import partial

from aqt import gui_hooks, mw
from aqt.qt import QAction, QKeySequence, QShortcut
from aqt.utils import tooltip

from .. import prefs
from . import card_tools, smart_undo
from .resolver import POLICIES, SWAP, parse_keys, resolve, translate_names

# Each entry: (action name, Anki's internal handler name, default keys).
# The handler name is how we recognize the shortcut even if its key was
# already changed (e.g. answer keys set in Preferences). When the handler is
# an anonymous lambda we fall back to recognizing it by its default key.
REVIEW_ACTIONS = [
    ("again", "_answerCard:1", ["1"]),
    ("hard", "_answerCard:2", ["2"]),
    ("good", "_answerCard:3", ["3"]),
    ("easy", "_answerCard:4", ["4"]),
    ("show_answer", "onEnterKey", ["Space", "Return", "Enter"]),
    ("undo", "undo", ["u"]),
    ("suspend_card", "suspend_current_card", ["@"]),
    ("suspend_note", "suspend_current_note", ["!"]),
    ("mark", "toggle_mark_on_current_note", ["*"]),
    ("bury_card", "bury_current_card", ["-"]),
    ("bury_note", "bury_current_note", ["="]),
    ("edit", "onEditCurrent", ["e"]),
    ("more_menu", "showContextMenu", ["m"]),
    ("replay_audio", "replayAudio", ["r", "F5"]),
    ("pause_audio", "on_pause_audio", ["5"]),
    ("seek_backward", "on_seek_backward", ["6"]),
    ("seek_forward", "on_seek_forward", ["7"]),
    ("record_voice", "onRecordVoice", ["Shift+V"]),
    ("replay_voice", "onReplayRecorded", ["v"]),
    ("deck_options", "onOptions", ["o"]),
    ("card_info", "on_card_info", ["i"]),
    ("previous_card_info", "on_previous_card_info", ["Ctrl+Alt+I"]),
    ("forget", "forget_current_card", ["Ctrl+Alt+N"]),
    ("create_copy", "on_create_copy", ["Ctrl+Alt+E"]),
    ("delete_note", "delete_current_note", ["Ctrl+Delete", "Ctrl+Backspace"]),
    ("set_due_date", "on_set_due", ["Ctrl+Shift+D"]),
    ("auto_advance", "toggle_auto_advance", ["Shift+A"]),
    *[(f"flag_{i}", None, [f"Ctrl+{i}"]) for i in range(1, 8)],
]

OVERVIEW_ACTIONS = [
    ("deck_options", None, ["o"]),
    ("rebuild", "rebuild_current_filtered_deck", ["r"]),
    ("empty", "empty_current_filtered_deck", ["e"]),
    ("custom_study", "onCustomStudyKey", ["c"]),
    ("unbury", "on_unbury", ["u"]),
]

STATE_ACTIONS = {"review": REVIEW_ACTIONS, "overview": OVERVIEW_ACTIONS}

# Our own actions that Anki doesn't have (card_tools.py), per screen:
# [(name, default keys, handler)].
STATE_EXTRAS = {"review": card_tools.REVIEW_EXTRAS}

# App-wide shortcuts that work on every screen, recognized by default key.
GLOBAL_SHORTCUTS = {
    "d": "decks",
    "s": "study",
    "a": "add",
    "b": "browse",
    "t": "stats",
    "Shift+T": "stats",
    "y": "sync",
    "Ctrl+:": "debug_console",
}

# Friendly names for menu-bar items. Any other menu item can be used as
# "menu:<objectName>", e.g. "menu:actionEmptyCards".
MENU_ALIASES = {
    "actionUndo": "undo_menu",
    "actionRedo": "redo_menu",
    "actionPreferences": "preferences",
    "actionSwitchProfile": "switch_profile",
    "actionImport": "import",
    "actionExport": "export",
    "actionStudyDeck": "study_deck",
    "actionCreateFiltered": "create_filtered_deck",
    "actionNoteTypes": "note_types",
    "actionAdd_ons": "addons",
    "actionExit": "exit",
    "actionDocumentation": "guide",
    "actionFullScreen": "full_screen",
    "actionZoomIn": "zoom_in",
    "actionZoomOut": "zoom_out",
    "actionResetZoom": "reset_zoom",
}


def norm(key):
    """Normalize any key representation to Qt's portable text, e.g. 'Ctrl+Z'."""
    return QKeySequence(key).toString(QKeySequence.SequenceFormat.PortableText)


def handler_id(fn):
    if isinstance(fn, partial):
        name = getattr(fn.func, "__name__", "")
        return f"{name}:{fn.args[0]}" if fn.args else name
    return getattr(fn, "__name__", "")


def config():
    return prefs.keyboard()


def read_section(section):
    """Parse one bindings section of the config into {name: [keys]}."""
    wanted, errors = {}, []
    for name, value in (config().get(section) or {}).items():
        if name.startswith("key:"):
            name = f"key:{norm(name[4:])}"
        try:
            wanted[name] = parse_keys(value, norm)
        except ValueError as e:
            errors.append(f"'{name}': {e}")
    return wanted, errors


def policy():
    value = config().get("on_conflict", SWAP)
    return value if value in POLICIES else SWAP


DEFAULT_SPARE_KEYS = ["F6", "F7", "F8", "F9", "F10", "F12"]


def spare_keys():
    keys = []
    for raw in config().get("spare_keys", DEFAULT_SPARE_KEYS) or []:
        key = norm(raw)
        if key:
            keys.append(key)
    return keys


class AppWide:
    """Menu-bar actions and global shortcuts, which apply on every screen."""

    def __init__(self):
        self.handles = {}  # name -> list of QShortcut/QAction
        self.original = {}  # name -> [keys] as Anki set them up
        self.result = {}
        self.notes, self.errors = {}, []
        self.wanted_keys = set()
        self.extra = []  # QShortcuts we created for additional keys
        self.collected = False

    def collect(self):
        if self.collected:
            return
        self.collected = True
        state_ids = {id(s) for s in getattr(mw, "stateShortcuts", [])}
        global_names = {norm(k): n for k, n in GLOBAL_SHORTCUTS.items()}
        for child in mw.children():
            if not isinstance(child, QShortcut) or id(child) in state_ids:
                continue
            key = norm(child.key())
            if key:
                self._add(global_names.get(key, f"key:{key}"), child, [key])
        for obj_name, obj in vars(mw.form).items():
            if isinstance(obj, QAction):
                name = MENU_ALIASES.get(obj_name, f"menu:{obj_name}")
                keys = [norm(s) for s in obj.shortcuts() if norm(s)]
                self._add(name, obj, keys)

    def _add(self, name, handle, keys):
        self.handles.setdefault(name, []).append(handle)
        current = self.original.setdefault(name, [])
        current.extend(k for k in keys if k not in current)

    def recompute(self):
        wanted, errors = read_section("global")
        wanted, name_errors = translate_names(self.original, wanted)
        self.wanted_keys = {k for keys in wanted.values() for k in keys}
        # Don't hand screen-specific keys to displaced app-wide actions.
        avoid = set()
        for state, actions in STATE_ACTIONS.items():
            avoid.update(norm(k) for _, _, keys in actions for k in keys)
            avoid.update(norm(k) for _, keys, _ in STATE_EXTRAS.get(state, []) for k in keys)
            avoid.update(k for keys in read_section(state)[0].values() for k in keys)
        self.result, self.notes, res_errors = resolve(
            self.original, wanted, policy(), spare_keys(), avoid=avoid
        )
        self.errors = errors + name_errors + res_errors
        self.apply()

    def apply(self, shadow=()):
        """Set the resolved keys, temporarily leaving out any in `shadow`.

        Screen-specific shortcuts shadow app-wide ones while that screen is
        showing; otherwise Qt sees two shortcuts on one key and fires neither.
        """
        for sc in self.extra:
            sc.setEnabled(False)
            sc.setParent(None)
            sc.deleteLater()
        self.extra = []
        for name, handles in self.handles.items():
            keys = [k for k in self.result.get(name, self.original[name]) if k not in shadow]
            shortcuts = [h for h in handles if isinstance(h, QShortcut)]
            for action in (h for h in handles if isinstance(h, QAction)):
                action.setShortcuts([QKeySequence(k) for k in keys])
            if not shortcuts:
                continue
            for i, sc in enumerate(shortcuts):
                if i < len(keys):
                    sc.setKey(QKeySequence(keys[i]))
                sc.setEnabled(i < len(keys))
            for key in keys[len(shortcuts):]:
                sc = QShortcut(QKeySequence(key), mw)
                sc.setAutoRepeat(False)
                sc.activated.connect(shortcuts[0].activated)
                self.extra.append(sc)

    def all_keys(self):
        return {k for keys in self.result.values() for k in keys}


app_wide = AppWide()
last_reports = {}  # state -> (result, notes, errors)


def current_bindings(state, shortcuts):
    """What Anki binds on one screen before our changes: ({name: [keys]},
    {name: handler}). Unrecognized shortcuts (other add-ons) are "key:X"."""
    actions = STATE_ACTIONS[state]
    by_handler = {h: name for name, h, _ in actions if h}
    by_key = {norm(k): name for name, _, keys in actions for k in keys}

    entries = [(norm(key), fn) for key, fn in shortcuts]
    entries = [(k, fn) for k, fn in entries if k]
    matched = {by_handler[handler_id(fn)] for _, fn in entries if handler_id(fn) in by_handler}

    current, fns = {}, {}
    for key, fn in entries:
        name = by_handler.get(handler_id(fn))
        if name is None:
            name = by_key.get(key)
            if name is None or name in matched:
                name = f"key:{key}"
        keys = current.setdefault(name, [])
        if key not in keys:
            keys.append(key)
        fns.setdefault(name, fn)
    return current, fns


def default_bindings(state, shortcuts):
    """Every action on one screen with its keys before the user's changes,
    including our own actions' default keys."""
    current, _ = current_bindings(state, shortcuts)
    for name, keys, _ in STATE_EXTRAS.get(state, []):
        current[name] = [norm(k) for k in keys]
    return current


def remap_state(state, shortcuts):
    """Return (new shortcut list, result, notes, errors) for one screen."""
    current, fns = current_bindings(state, shortcuts)
    extras = STATE_EXTRAS.get(state, [])
    for name, _, fn in extras:
        current[name] = []
        fns[name] = fn
    if state == "review" and "undo" in fns and config().get("smart_undo", True):
        fns["undo"] = smart_undo.undo

    actions = STATE_ACTIONS[state]
    wanted, errors = read_section(state)
    known = {name for name, _, _ in actions}
    for name in [n for n in wanted if n in known and n not in current]:
        errors.append(f"'{name}' isn't available in your Anki version")
        del wanted[name]
    # Our actions' default keys are applied as if the user had picked them, so
    # an Anki action on the same key moves aside instead of sharing it.
    # Keys you gave to something yourself always win over these defaults.
    defaults = {}
    taken = {k for keys in wanted.values() for k in keys} | app_wide.wanted_keys
    for name, keys, _ in extras:
        if name not in wanted:
            defaults[name] = wanted[name] = [k for k in map(norm, keys) if k not in taken]
    wanted, name_errors = translate_names(current, wanted)

    reserved = app_wide.wanted_keys
    avoid = app_wide.all_keys()
    result, notes, res_errors = resolve(
        current,
        wanted,
        policy(),
        spare_keys(),
        reserved=reserved,
        avoid=avoid,
        reserved_label="an app-wide shortcut",
    )
    for name, keys in defaults.items():
        if result.get(name) == keys:
            notes.pop(name, None)
    new_list = [(k, fns[name]) for name, keys in result.items() for k in keys]
    return new_list, result, notes, errors + name_errors + res_errors


def on_state_shortcuts(state, shortcuts):
    if state not in STATE_ACTIONS:
        return
    app_wide.collect()
    new_list, result, notes, errors = remap_state(state, shortcuts)
    shortcuts[:] = new_list
    last_reports[state] = (result, notes, errors)
    app_wide.apply(shadow={k for keys in result.values() for k in keys})


def on_state_did_change(new_state, old_state):
    if new_state not in STATE_ACTIONS:
        app_wide.apply()


def refresh_current_screen():
    screens = {"review": mw.reviewer, "overview": mw.overview}
    if mw.state in screens:
        mw.clearStateShortcuts()
        mw.setStateShortcuts(screens[mw.state]._shortcutKeys())


def on_profile_open():
    app_wide.collect()
    app_wide.recompute()
    problems = len(app_wide.errors) + sum(len(e) for e in preview_reports().values())
    if problems:
        tooltip(
            f"Shinjer's Study Desk: {problems} keyboard setting(s) were ignored.<br>"
            "See the Keyboard tab for details.",
            period=6000,
        )


def apply_config():
    """The keyboard config changed: rebind everything now."""
    app_wide.recompute()
    refresh_current_screen()


def preview_reports():
    """Work out each screen's bindings without needing to be on that screen."""
    reports = {}
    screens = {"review": mw.reviewer, "overview": mw.overview}
    for state, screen in screens.items():
        try:
            _, result, notes, errors = remap_state(state, list(screen._shortcutKeys()))
        except Exception as e:  # collection not loaded, API changed, ...
            if state in last_reports:
                reports[state] = last_reports[state]
            else:
                reports[state] = ({}, {}, [f"couldn't read shortcuts: {e}"])
            continue
        names = [n for n, _, _ in STATE_ACTIONS[state]] + [n for n, _, _ in STATE_EXTRAS.get(state, [])]
        order = {name: i for i, name in enumerate(names)}
        result = dict(sorted(result.items(), key=lambda kv: order.get(kv[0], len(order))))
        reports[state] = (result, notes, errors)
    return reports


def setup():
    gui_hooks.state_shortcuts_will_change.append(on_state_shortcuts)
    gui_hooks.state_did_change.append(on_state_did_change)
    gui_hooks.profile_did_open.append(on_profile_open)
    card_tools.setup()
