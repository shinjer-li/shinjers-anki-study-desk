"""Exercise Shinjer's Study Desk keyboard remapping with fake aqt/Qt modules.

Run:  python test_kbr.py
"""
import sys, types, importlib
from functools import partial

# ---- fake Qt ----
class Key:  # stands in for Qt.Key enums
    def __init__(s, n): s.n = n
class QKeySequence:
    class SequenceFormat: PortableText = 0
    MODS = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "meta": "Meta"}
    def __init__(s, k=""):
        if isinstance(k, QKeySequence): k = k.s
        if isinstance(k, Key): k = k.n
        if k == " ": k = "Space"
        parts = [p for p in k.split("+")] if k not in ("+",) else ["+"]
        out = []
        for p in parts:
            if p.lower() in s.MODS: out.append(s.MODS[p.lower()])
            elif p.lower() == "bogus": out = []; break
            elif len(p) == 1: out.append(p.upper())
            else: out.append(p[0].upper() + p[1:])
        s.s = "+".join(out)
    def toString(s, fmt=0): return s.s
class Signal:
    def __init__(s): s.slots = []
    def connect(s, f): s.slots.append(f)
    def emit(s): [f() if callable(f) else f.emit() for f in s.slots]
class QShortcut:
    def __init__(s, key, parent):
        s._k = QKeySequence(key); s.enabled = True; s.activated = Signal()
        parent._children.append(s)
    def key(s): return s._k
    def setKey(s, k): s._k = QKeySequence(k)
    def setEnabled(s, e): s.enabled = e
    def setAutoRepeat(s, v): pass
    def setParent(s, p): mw._children.remove(s) if s in mw._children else None
    def deleteLater(s): pass
class QAction:
    def __init__(s, text="", parent=None, keys=()): s._keys = [QKeySequence(k) for k in keys]; s.triggered = Signal()
    def shortcuts(s): return s._keys
    def setShortcuts(s, ks): s._keys = list(ks)

hooks = types.SimpleNamespace(state_shortcuts_will_change=[], state_did_change=[], profile_did_open=[],
                              reviewer_did_show_answer=[], operation_did_execute=[],
                              webview_will_set_content=[], webview_will_show_context_menu=[])
CONFIG = {}
class Form: pass
class MW:
    def __init__(s):
        s._children = []; s.stateShortcuts = []; s.form = Form(); s.state = "deckBrowser"
        s.form.actionUndo = QAction(keys=["Ctrl+Z"]); s.form.actionRedo = QAction(keys=["Ctrl+Shift+Z"])
        s.form.actionEmptyCards = QAction(); s.form.menuTools = types.SimpleNamespace(addAction=lambda a: None)
        s.addonManager = types.SimpleNamespace(getConfig=lambda n: {"keyboard": CONFIG}, writeConfig=lambda n, c: None)
    def children(s): return list(s._children)
mw = MW()
for k in ["Ctrl+:", "d", "s", "a", "b", "t", "Shift+t", "y"]:
    QShortcut(k, mw)

aqt = types.ModuleType("aqt"); aqt.gui_hooks = hooks; aqt.mw = mw
aqt_qt = types.ModuleType("aqt.qt"); aqt_qt.QAction = QAction; aqt_qt.QKeySequence = QKeySequence; aqt_qt.QShortcut = QShortcut
aqt_qt.QGuiApplication = aqt_qt.QImage = aqt_qt.Qt = aqt_qt.QUrl = object
aqt_utils = types.ModuleType("aqt.utils"); aqt_utils.showText = lambda *a, **k: print(a[0]); aqt_utils.tooltip = lambda *a, **k: print("TOOLTIP:", a[0])
sys.modules.update({"aqt": aqt, "aqt.qt": aqt_qt, "aqt.utils": aqt_utils})
import os
ADDONS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ADDONS)
# Load shinjers_study_desk as a bare package so its __init__ (window, tabs...) does not run.
pkg = types.ModuleType("shinjers_study_desk"); pkg.__path__ = [os.path.join(ADDONS, "shinjers_study_desk")]
sys.modules["shinjers_study_desk"] = pkg
kbr = importlib.import_module("shinjers_study_desk.keyboard.remap")
kbr.setup()

# ---- fake reviewer shortcut list, shaped like Anki's ----
class Reviewer:
    def _answerCard(s, ease): pass
    def onEnterKey(s): pass
    def showContextMenu(s): pass
    def replayAudio(s): pass
    def toggle_mark_on_current_note(s): pass
    def suspend_current_card(s): pass
    def suspend_current_note(s): pass
    def bury_current_card(s): pass
    def onOptions(s): pass
    def _shortcutKeys(s):
        undo = lambda: None; undo.__name__ = "undo"
        return [(" ", s.onEnterKey), (Key("Return"), s.onEnterKey), ("m", s.showContextMenu),
                ("r", s.replayAudio), (Key("F5"), s.replayAudio),
                *[(f"Ctrl+{i}", (lambda: None)) for i in range(1, 8)],
                ("*", s.toggle_mark_on_current_note), ("!", s.suspend_current_note), ("@", s.suspend_current_card),
                ("-", s.bury_current_card), ("o", s.onOptions), ("j", lambda: "other addon"),
                *[(str(e), partial(s._answerCard, e)) for e in (1, 2, 3, 4)], ("u", undo)]
class Overview:
    def _shortcutKeys(s): return [("o", lambda: None), ("u", lambda: None)]
mw.reviewer, mw.overview = Reviewer(), Overview()

def run(cfg, state="review"):
    CONFIG.clear(); CONFIG.update(cfg)
    kbr.app_wide.recompute()
    new, result, notes, errors = kbr.remap_state(state, list(getattr(mw, "reviewer" if state=="review" else "overview")._shortcutKeys()))
    return {k: v for k, v in result.items()}, notes, errors

kbr.app_wide.collect()
fails = 0
def check(label, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + label); fails += not cond
    return cond

# 1. Defaults in config -> no change
r, n, e = run({"review": {"again": "1", "hard": "2", "good": "3", "easy": "4", "suspend_card": "@", "undo": "u", "mark": "*"}})
check("defaults change nothing", not n and not e and r["again"] == ["1"] and r["undo"] == ["U"])

# 2. Swap: again->m displaces more_menu to 1
r, n, e = run({"review": {"again": "m"}})
check("swap more_menu -> 1", r["again"] == ["M"] and r["more_menu"] == ["1"], ) or print(r, n)

# 3. Home-row remap: j k l ; ; j held by another add-on
r, n, e = run({"review": {"again": "j", "hard": "k", "good": "l", "easy": ";", "suspend_card": "s", "undo": "z", "mark": "Shift+M"}})
check("answers remapped", [r[x] for x in ("again","hard","good","easy")] == [["J"],["K"],["L"],[";"]])
check("other add-on on j swapped to 1", r["key:J"] == ["1"]) or print(r["key:J"], n)
check("no errors", not e) or print(e)

# 4. delete policy
r, n, e = run({"review": {"again": "m"}, "on_conflict": "delete"})
check("delete unbinds more_menu", r["more_menu"] == [] and "unbound" in n["more_menu"])

# 5. spare policy
r, n, e = run({"review": {"again": "m"}, "on_conflict": "spare"})
check("spare uses F6", r["more_menu"] == ["F6"])

# 6. multi-key action loses one key only
r, n, e = run({"review": {"again": "F5"}})
check("replay_audio keeps r", r["replay_audio"] == ["R"] and "still has" in n["replay_audio"])

# 7. bad key, unknown action, duplicate key
r, n, e = run({"review": {"again": "Bogus", "flurb": "x", "hard": "q", "good": "q"}})
check("errors reported", len(e) == 3) or print(e)

# 8. key: syntax
r, n, e = run({"review": {"key:o": "Shift+O"}})
check("key:o moves deck_options", r["deck_options"] == ["Shift+O"])

# 9. unbind + list
r, n, e = run({"review": {"mark": "", "again": ["1", "Left"]}})
check("unbind and multi", r["mark"] == [] and r["again"] == ["1", "Left"])

# 10. global conflict: review suspend on 'a' shadows Add only in review
CONFIG.clear(); CONFIG.update({"review": {"suspend_card": "a"}}); kbr.app_wide.recompute()
sl = mw.reviewer._shortcutKeys(); kbr.on_state_shortcuts("review", sl)
add_sc = kbr.app_wide.handles["add"][0]
check("Add disabled while reviewing", add_sc.enabled is False)
check("reviewer list has A", any(k == "A" for k, f in sl))
kbr.on_state_did_change("deckBrowser", "review")
check("Add re-enabled on deck list", add_sc.enabled is True and add_sc.key().s == "A")

# 11. global remap: undo_menu -> Ctrl+Y ; browse -> e displaces reviewer edit? (edit absent in fake list) ; add -> x
CONFIG.clear(); CONFIG.update({"global": {"undo_menu": "Ctrl+Y", "browse": "m"}}); kbr.app_wide.recompute()
check("undo menu remapped", [k.s for k in mw.form.actionUndo.shortcuts()] == ["Ctrl+Y"])
r, n, e = run({"global": {"browse": "m"}})
check("app-wide browse=m displaces review more_menu", r["more_menu"] != ["M"] and "M" not in sum(r.values(), [])) or print(r["more_menu"], n)

# 12. stats has two QShortcuts; give it three keys then one
CONFIG.clear(); CONFIG.update({"global": {"stats": ["t", "Shift+T", "F9"]}}); kbr.app_wide.recompute()
check("extra QShortcut created", len(kbr.app_wide.extra) == 1 and kbr.app_wide.extra[0].key().s == "F9")
CONFIG.clear(); CONFIG.update({"global": {"stats": "t"}}); kbr.app_wide.recompute()
st = kbr.app_wide.handles["stats"]
check("second stats shortcut disabled", st[0].enabled and not st[1].enabled and not kbr.app_wide.extra)

# 13. our own review actions (card_tools.py)
ct = kbr.card_tools
r, n, e = run({})
check("extras get their default keys", r["reveal_next"] == ["C"] and r["reveal_all"] == ["V"]
      and r["copy_text"] == ["G"] and r["copy_image"] == ["P"] and r["hint_next"] == []) or print(r)
check("defaults leave no notes", not n and not e) or print(n, e)
def replay_voice(): pass
replay_voice.__name__ = "onReplayRecorded"
with_v = list(mw.reviewer._shortcutKeys()) + [("v", replay_voice)]
CONFIG.clear(); kbr.app_wide.recompute()
new, r, n, e = kbr.remap_state("review", with_v)
check("Anki's v moves aside for reveal_all", r["reveal_all"] == ["V"] and r["replay_voice"] == ["F6"]
      and "reveal_all" in n["replay_voice"] and not e) or print(r, n, e)
check("keys call our handlers", dict(new)["C"] is ct.reveal_next and dict(new)["V"] is ct.reveal_all
      and dict(new)["F6"] is replay_voice)
r, n, e = run({"review": {"mark": "c"}})
check("your own c beats the default", r["mark"] == ["C"] and r["reveal_next"] == [] and not e) or print(r, e)
r, n, e = run({"review": {"reveal_next": "", "hint_next": "h", "copy_image": "x"}})
check("extras can be cleared and rebound", r["reveal_next"] == [] and r["hint_next"] == ["H"]
      and r["copy_image"] == ["X"] and n.get("hint_next") == "changed by you" and not e) or print(r, n, e)
r, n, e = run({"global": {"browse": "g"}})
check("app-wide key beats the default", r["copy_text"] == [] and not e) or print(r["copy_text"], e)
d = kbr.default_bindings("review", with_v)
check("defaults column shows extras", d["reveal_all"] == ["V"] and d["replay_voice"] == ["V"])

# 13b. Anki's Korean-layout aliases are hidden and follow the key they sit on
with_ko = with_v + [("ㅍ", replay_voice), ("ㄱ", mw.reviewer.replayAudio)]
CONFIG.clear(); CONFIG.update({"review": {"replay_audio": "q"}}); kbr.app_wide.recompute()
new, r, n, e = kbr.remap_state("review", with_ko)
d = kbr.default_bindings("review", with_ko)
check("no Hangul keys shown", not any(kbr.is_hangul(k) for ks in list(r.values()) + list(d.values()) for k in ks)) or print(r, d)
check("aliases follow their keys", dict(new)["ㅂ"] == mw.reviewer.replayAudio and "ㄱ" not in dict(new)
      and dict(new)["ㅍ"] is ct.reveal_all and dict(new)["ㅊ"] is ct.reveal_next) or print(new)
check("hangul twin keeps modifiers", kbr.hangul_twin("Ctrl+Alt+N") == "Ctrl+Alt+ㅜ" and kbr.hangul_twin("F6") is None)

# 14. smart undo
import time
su = kbr.smart_undo
CONFIG.clear(); CONFIG.update({"review": {"undo": "z"}})
new, *_ = kbr.remap_state("review", list(mw.reviewer._shortcutKeys()))
check("undo key wired to smart undo", dict(new)["Z"] is su.undo)
CONFIG["smart_undo"] = False
new, *_ = kbr.remap_state("review", list(mw.reviewer._shortcutKeys()))
check("smart_undo false keeps Anki undo", dict(new)["Z"] is not su.undo)

class Status:
    def __init__(s, step, undo="", redo=""): s.last_step, s.undo, s.redo = step, undo, redo
col = types.SimpleNamespace(status=Status(10, "Answer Card"))
col.undo_status = lambda: col.status
card = types.SimpleNamespace(id=1, timer_started=None)
rv = mw.reviewer
rv.card, rv.state, rv._reps = card, "question", 1
rv._showQuestion = lambda: (setattr(rv, "state", "question"), setattr(rv, "_reps", rv._reps + 1))
calls = []
mw.col, mw.undo = col, lambda: calls.append("undo")
hook = lambda name, *a: [f(*a) for f in getattr(hooks, name)]
def op(step, undo="Answer Card", redo=""): col.status = Status(step, undo, redo); hook("operation_did_execute", None, None)

mw.state = "review"; hook("state_did_change", "review", "overview")
su.undo()
check("first card: no undo", calls == [])
card.timer_started = time.time() - 5; hook("reviewer_did_show_answer", card); rv.state = "answer"
card.timer_started = time.time() - 7  # 2 more seconds on the answer side
su.undo()
check("flip undone", rv.state == "question" and calls == [] and rv._reps == 1)
check("timer back to 5s", abs(time.time() - card.timer_started - 5) < 0.1)
op(11); op(12)                      # answered two cards
su.undo(); op(13, redo="Answer Card")   # undo one
su.undo(); op(14, redo="Answer Card")   # undo the other
su.undo()
check("undo stops at session start", calls == ["undo", "undo"])
op(15, undo=""); su.undo()
check("cleared history -> nothing to undo", calls == ["undo", "undo"])
print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
