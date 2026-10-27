"""
Settings that belong to the add-on rather than to a collection: appearance,
the toolbar link and keyboard shortcuts. They're kept in the add-on config
(config.json defaults + Anki's meta.json), so they apply to every profile.

Study Day and Trouble Spots keep their settings in the collection instead
(see study_day/core.py and trouble/analysis.py), so they follow the profile.
"""

from __future__ import annotations

import copy
import json
import os
import shutil

from aqt import mw

ADDON = __name__.split(".")[0]
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))

MODES = ("auto", "light", "dark")
# id -> label. The colors themselves live in web/css/tokens.css (and the
# status bar's copy in study_day/banner.py).
THEMES = {
    "slate": "Slate", "frost": "Frost", "navy": "Navy", "indigo": "Indigo",
    "sage": "Sage", "teal": "Teal", "sand": "Sand", "rose": "Rose",
    "plum": "Plum", "graphite": "Graphite", "paper": "Paper",
}
DEFAULT_THEME = "slate"


def _defaults() -> dict:
    with open(os.path.join(ADDON_DIR, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def get() -> dict:
    """The full config, with any missing keys filled in from the defaults."""
    cfg = copy.deepcopy(mw.addonManager.getConfig(ADDON) or {})
    for key, value in _defaults().items():
        if isinstance(value, dict):
            cfg[key] = {**value, **(cfg.get(key) or {})}
        else:
            cfg.setdefault(key, value)
    return cfg


def save(cfg: dict) -> None:
    mw.addonManager.writeConfig(ADDON, cfg)


def appearance() -> dict:
    a = get()["appearance"]
    return {
        "mode": a["mode"] if a["mode"] in MODES else "auto",
        "theme": a["theme"] if a["theme"] in THEMES else DEFAULT_THEME,
    }


def set_appearance(key: str, value: str) -> bool:
    allowed = {"mode": MODES, "theme": THEMES}
    if value not in allowed.get(key, ()):
        return False
    cfg = get()
    cfg["appearance"][key] = value
    save(cfg)
    return True


def set_value(path: str, value) -> None:
    """Set one plain value, e.g. set_value("window.on_top", True)."""
    cfg = get()
    *parents, last = path.split(".")
    node = cfg
    for key in parents:
        node = node.setdefault(key, {})
    node[last] = value
    save(cfg)


def keyboard() -> dict:
    return get()["keyboard"]


def save_keyboard(section: dict) -> None:
    cfg = get()
    cfg["keyboard"] = section
    save(cfg)


# ── Moving over from the three separate add-ons ──────────────────────────────


def migrate() -> None:
    """Copy settings from older versions of this add-on, once each."""
    _from_study_desk()
    _from_separate_addons()


def _copy_history(old_addon: str) -> None:
    old_files = os.path.join(mw.addonManager.addonsFolder(), old_addon, "user_files")
    new_files = os.path.join(ADDON_DIR, "user_files")
    if os.path.isdir(old_files):
        os.makedirs(new_files, exist_ok=True)
        for name in os.listdir(old_files):
            if name.startswith("history-") and not os.path.exists(os.path.join(new_files, name)):
                shutil.copy2(os.path.join(old_files, name), new_files)


def _from_study_desk() -> None:
    """This add-on used to be called "Study Desk" (folder study_desk). Take its
    look, window, top-bar and keyboard settings and its undo history."""
    cfg = get()
    if cfg.get("migrated_study_desk"):
        return
    old = mw.addonManager.getConfig("study_desk")
    if old:
        for key, value in old.items():
            cfg[key] = copy.deepcopy(value)
        _copy_history("study_desk")
    cfg["migrated_study_desk"] = True
    save(cfg)


def _from_separate_addons() -> None:
    """One time: take over Keybind Remapper's shortcuts and Study Day Control's
    undo history, if those add-ons were used before. (Study Day and Trouble
    Spots settings are stored in the collection under the same keys, so they
    carry over by themselves.)"""
    cfg = get()
    if cfg.get("migrated"):
        return
    old = mw.addonManager.getConfig("keybind_remapper")
    if old:
        kb = cfg["keyboard"]
        for key in ("review", "overview", "global", "on_conflict", "smart_undo", "spare_keys"):
            if key in old:
                kb[key] = old[key]
    if mw.col and (mw.col.get_config("study_day_control_settings", None) or {}).get("stay_on_top"):
        cfg["window"]["on_top"] = True
    _copy_history("study_day_control")
    cfg["migrated"] = True
    save(cfg)
