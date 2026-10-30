"""
Smoke test: import the whole add-on with stubbed aqt/Qt and ask every tab for
its settings (plus the Keyboard and Settings tabs for their data), against a
real temporary collection. Catches import errors and typos.

Needs the `anki` package. Run:
    python test_smoke.py
"""

import os
import sys
import tempfile
import types

from anki.collection import Collection


class StubMeta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Stub()


class Stub(metaclass=StubMeta):
    """Anything: callable, subclassable, every attribute is another Stub."""

    def __init__(self, *a, **k): pass
    def __call__(self, *a, **k): return Stub()
    def __getattr__(self, name): return Stub()
    def __or__(self, other): return self


class StubModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return type(name, (Stub,), {})


class Hooks:
    def __getattr__(self, name):
        setattr(self, name, [])
        return getattr(self, name)


class QKeySequence(Stub):
    class SequenceFormat: PortableText = 0
    def __init__(self, k=""): self.s = getattr(k, "s", k)
    def toString(self, fmt=0): return self.s


class QAction(Stub):
    def shortcuts(self): return []
    def setShortcuts(self, keys): pass


class QShortcut(Stub):
    pass


class Reviewer:
    def onEnterKey(self): pass
    def _shortcutKeys(self): return [("Space", self.onEnterKey), ("Ctrl+1", lambda: None)]


class Overview:
    def _shortcutKeys(self): return [("o", lambda: None)]


CONFIG = {}
col = Collection(tempfile.mktemp(suffix=".anki2"))
mw = types.SimpleNamespace(
    col=col, state="deckBrowser", stateShortcuts=[], children=lambda: [],
    form=types.SimpleNamespace(menuTools=Stub(), actionUndo=QAction()),
    reviewer=Reviewer(), overview=Overview(), pm=types.SimpleNamespace(name="test"),
    addonManager=types.SimpleNamespace(
        getConfig=lambda name: CONFIG if name == "shinjers_study_desk" else None,
        writeConfig=lambda name, cfg: (CONFIG.clear(), CONFIG.update(cfg)),
        setWebExports=lambda *a: None, setConfigAction=lambda *a: None,
        addonsFolder=lambda: tempfile.gettempdir()),
)

for name in ["aqt", "aqt.qt", "aqt.utils", "aqt.operations", "aqt.theme", "aqt.webview"]:
    sys.modules[name] = StubModule(name)
sys.modules["aqt"].mw = mw
sys.modules["aqt"].gui_hooks = Hooks()
qt = sys.modules["aqt.qt"]
qt.QKeySequence, qt.QAction, qt.QShortcut = QKeySequence, QAction, QShortcut

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shinjers_study_desk  # noqa: E402

shinjers_study_desk.prefs.migrate()
shinjers_study_desk.keyboard.remap.on_profile_open()
for tab in shinjers_study_desk.TABS:
    sections = tab.settings()
    assert isinstance(sections, list) and all("rows" in s for s in sections), tab.id
    print(f"{tab.id}: settings ok ({len(sections)} section(s))")

kb = next(t for t in shinjers_study_desk.TABS if t.id == "keyboard").data(None)
assert [s["id"] for s in kb["scopes"]] == ["review", "overview", "global"], kb
review = next(s for s in kb["scopes"] if s["id"] == "review")
anking = next(g for g in review["groups"] if g["title"] == "AnKing & copy")
assert [r["name"] for r in anking["rows"]] == [
    "reveal_next", "reveal_all", "hint_next", "hint_all", "copy_text", "copy_image"], anking
assert next(r for r in anking["rows"] if r["name"] == "reveal_next")["keys"] == ["c"], anking
print("keyboard: data ok")
st = next(t for t in shinjers_study_desk.TABS if t.id == "settings").data(None)
assert st["appearance"] == {"mode": "auto", "theme": "slate"} and len(st["sections"]) == 4, st
print("settings: data ok")
ab = next(t for t in shinjers_study_desk.TABS if t.id == "about").data(None)
assert ab["version"] and "github" in ab["links"] and "ankiweb" not in ab["links"], ab
print("about: data ok")
assert CONFIG.get("migrated") is True

note = col.new_note(col.models.by_name("Basic"))
note["Front"], note["Back"] = "q", "a"
col.add_note(note, col.decks.id("Default"))
bar = shinjers_study_desk.study_day.banner.banner_html()
assert "sdk-logo" in bar and ">Today<" in bar and ">Done<" in bar and "Tomorrow" in bar, bar
assert "<b>1</b> new" in bar and "~" not in bar, bar
assert "Next 7 days" not in bar and "sdk-flag" not in bar, bar
print("status bar: render ok")
col.close()
print("ALL OK")
