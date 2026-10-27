"""
Build a throwaway Anki collection full of made-up reviews, ask every tab for
its data the way the window would, and write it to tools/out/sample.json.
tools/screenshots.py draws the page from that file. No real collection is
touched, and the card text is invented.

Needs Python with the `anki` package (not Anki itself):
    python tools/sample_data.py
"""

import json
import os
import random
import sys
import tempfile
import time
import types
from functools import partial

from anki.collection import Collection

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "sample.json")
random.seed(7)


# ── Stub Anki's UI, like test_smoke.py ───────────────────────────────────────


class StubMeta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Stub()


class Stub(metaclass=StubMeta):
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


def shortcut_keys(actions):
    """Anki's (key, handler) list for a screen, with handlers named like Anki's."""
    def handler(name):
        if not name:
            return lambda: None
        base, _, arg = name.partition(":")
        fn = lambda *a: None
        fn.__name__ = base
        return partial(fn, int(arg)) if arg else fn
    return [(key, handler(h)) for _, h, keys in actions for key in keys]


class Reviewer:
    def _shortcutKeys(self):
        from shinjers_study_desk.keyboard.remap import REVIEW_ACTIONS
        return shortcut_keys(REVIEW_ACTIONS)


class Overview:
    def _shortcutKeys(self):
        from shinjers_study_desk.keyboard.remap import OVERVIEW_ACTIONS
        return shortcut_keys(OVERVIEW_ACTIONS)


# ── The sample collection ────────────────────────────────────────────────────

FA = "#AK_Step1_v12::#FirstAid::"
# (tag below #FirstAid, how hard it is, invented card texts)
TOPICS = [
    ("05_Cardiovascular::03_Physiology::05_Pressure-volume_loops", .26, [
        "Aortic stenosis raises {{c1::afterload}} and widens the loop upward",
        "Mitral regurgitation has no true {{c1::isovolumetric}} phases",
        "Increased preload shifts the loop to the {{c1::right}}",
        "Increased contractility makes the loop {{c1::wider}} with a larger stroke volume",
        "Aortic regurgitation has no true isovolumetric {{c1::relaxation}}",
        "The area inside the loop is {{c1::stroke work}}",
        "Mitral stenosis raises {{c1::left atrial}} pressure"]),
    ("11_Renal::03_Physiology::04_Renal_tubular_defects", .24, [
        "Bartter syndrome affects the {{c1::thick ascending limb}}",
        "Gitelman syndrome mimics a {{c1::thiazide}}",
        "Liddle syndrome: {{c1::increased}} ENaC activity",
        "Fanconi syndrome is a generalized {{c1::proximal tubule}} reabsorption defect",
        "Bartter syndrome looks like taking a {{c1::loop diuretic}}",
        "Type 1 RTA has urine pH {{c1::> 5.5}}",
        "Type 2 RTA is a defect in {{c1::HCO3-}} reabsorption",
        "Type 4 RTA causes {{c1::hyperkalemia}}",
        "Gitelman syndrome causes {{c1::hypomagnesemia}}",
        "SIADH gives {{c1::euvolemic}} hyponatremia"]),
    ("06_Endocrine::05_Pharmacology::01_Diabetes_drugs", .21, [
        "SGLT2 inhibitors can cause {{c1::euglycemic DKA}}",
        "Sulfonylureas close {{c1::K+ ATP}} channels",
        "Metformin's main risk is {{c1::lactic acidosis}}",
        "GLP-1 agonists can cause {{c1::pancreatitis}}",
        "Thiazolidinediones act on {{c1::PPAR-γ}}",
        "DPP-4 inhibitors end in {{c1::-gliptin}}",
        "SGLT2 inhibitors raise the risk of {{c1::genital}} infections"]),
    ("02_Immunology::04_Immune_responses::05_Hypersensitivity_types", .20, [
        "Type {{c1::II}} hypersensitivity is antibody-mediated against cell surfaces",
        "Serum sickness is type {{c1::III}}",
        "Contact dermatitis is type {{c1::IV}}"]),
    ("03_Microbiology::03_Bacteriology::02_Gram-positive_cocci", .17, [
        "Optochin-sensitive, bile-soluble: {{c1::S. pneumoniae}}",
        "Novobiocin-resistant: {{c1::S. saprophyticus}}"]),
    ("12_Reproductive::03_Physiology::02_Menstrual_cycle", .16, [
        "The LH surge triggers {{c1::ovulation}}",
        "Progesterone dominates the {{c1::luteal}} phase"]),
    ("09_Neurology::02_Anatomy_and_physiology::07_Brain_lesions", .15, [
        "Bilateral amygdala damage: {{c1::Klüver-Bucy}} syndrome",
        "Broca aphasia: {{c1::nonfluent}} with intact comprehension"]),
    ("08_Musculoskeletal::02_Pathology::04_Bone_tumors", .13, [
        "Soap-bubble appearance: {{c1::giant cell tumor}}",
        "Codman triangle: {{c1::osteosarcoma}}"]),
    ("10_Psychiatry::03_Pathology::04_Mood_disorders", .11, [
        "Lithium toxicity causes {{c1::tremor}} and nephrogenic DI"]),
    ("01_Biochem::04_Metabolism::06_Glycogen_storage_diseases", .10, [
        "Von Gierke: {{c1::glucose-6-phosphatase}} deficiency",
        "Pompe: {{c1::acid α-glucosidase}} deficiency"]),
    ("07_Hematology_and_oncology::03_Pathology::02_Anemias", .09, [
        "Microcytic with basophilic stippling: {{c1::lead poisoning}}"]),
    ("13_Respiratory::03_Physiology::03_V/Q_mismatch", .08, [
        "Apex of the lung has the {{c1::highest}} V/Q"]),
    ("04_Pathology::01_Cellular_injury::03_Necrosis", .07, [
        "Caseous necrosis is typical of {{c1::tuberculosis}}"]),
    ("05_Cardiovascular::01_Embryology::02_Heart_morphogenesis", .07, [
        "The truncus arteriosus gives rise to the {{c1::ascending aorta}} and pulmonary trunk"]),
    ("11_Renal::05_Pharmacology::01_Diuretics", .06, [
        "Acetazolamide causes {{c1::hyperchloremic metabolic acidosis}}"]),
]
DAY = 86400


def build(col: Collection) -> int:
    deck = col.decks.id("AnKing Step 1")
    model = col.models.by_name("Basic")
    cutoff = col.sched.day_cutoff
    today = col.sched.today
    rid = int((cutoff - 366 * DAY) * 1000)
    revlog = []

    def add(text, tags, miss):
        note = col.new_note(model)
        note["Front"], note["Back"] = text, text.replace("{{c1::", "").replace("}}", "")
        note.tags = tags
        col.add_note(note, deck)
        return note.cards()[0].id, miss

    cards = []
    for tag, miss, texts in TOPICS:
        for t in texts:
            # The named cards come up often and are missed more, so they lead the list.
            cards.extend([add(t, [FA + tag], min(.7, miss * 2.5))] * 12)
        leaf = tag.split("::")[-1].split("_", 1)[1].replace("_", " ")
        for i in range(300):  # more cards per topic, so the counts look real
            cards.append(add(f"Sample card {i + 1} on {leaf.lower()}", [FA + tag], miss * .9))
    for i in range(120):  # new cards, never studied
        add(f"New sample card {i + 1}", [FA + "04_Pathology::01_Cellular_injury::01_Apoptosis"], 0)

    # A year of reviews, heavier lately, with a few days off.
    for day in range(365, 0, -1):
        if random.random() < .06:
            continue
        n = int(random.gauss(190 if day < 120 else 120, 30))
        start = cutoff - day * DAY - 15 * 3600 + random.randint(0, 3600)
        for k in range(max(0, n)):
            cid, miss = random.choice(cards)
            ease = 1 if random.random() < miss * (1 if day < 30 else .9) else random.choice((3, 3, 3, 4))
            ts = (start + k * 9) * 1000 + random.randint(0, 999)
            revlog.append((ts, cid, ease, random.randint(4000, 14000)))
    # Some reviews earlier today.
    for k in range(64):
        cid, miss = random.choice(cards)
        ts = (int(time.time()) - 3 * 3600 + k * 11) * 1000
        revlog.append((ts, cid, 1 if random.random() < miss else 3, random.randint(4000, 12000)))
    for ts, cid, ease, ms in revlog:
        rid = max(rid + 1, ts)
        col.db.execute(
            "insert into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type) "
            "values (?, ?, -1, ?, 10, 5, 2500, ?, 1)", rid, cid, ease, ms)

    # Every studied card becomes a review card due somewhere in the next month.
    studied = list({cid for cid, _ in cards})
    random.shuffle(studied)
    for i, cid in enumerate(studied):
        due = today + (0 if i < 186 else random.randint(1, 27))
        lapses = random.randint(0, 6)
        col.db.execute(
            "update cards set type=2, queue=2, due=?, ivl=?, factor=?, lapses=?, reps=? where id=?",
            due, random.randint(3, 60), random.choice((1900, 2100, 2300, 2500)), lapses, lapses + 8, cid)
    col.set_config("newPerDay", 20)
    conf = col.decks.config_dict_for_deck_id(deck)
    conf["new"]["perDay"] = 20
    conf["rev"]["perDay"] = 9999
    col.decks.save(conf)
    return deck


def main() -> None:
    config = {}
    col = Collection(tempfile.mktemp(suffix=".anki2"))
    mw = types.SimpleNamespace(
        col=col, state="deckBrowser", stateShortcuts=[], children=lambda: [],
        form=types.SimpleNamespace(menuTools=Stub(), actionUndo=QAction()),
        reviewer=Reviewer(), overview=Overview(), pm=types.SimpleNamespace(name="sample"),
        addonManager=types.SimpleNamespace(
            getConfig=lambda name: config, writeConfig=lambda name, cfg: config.update(cfg),
            setWebExports=lambda *a: None, setConfigAction=lambda *a: None,
            addonsFolder=lambda: tempfile.gettempdir()),
    )
    for name in ["aqt", "aqt.qt", "aqt.utils", "aqt.operations", "aqt.theme", "aqt.webview"]:
        sys.modules[name] = StubModule(name)
    sys.modules["aqt"].mw = mw
    sys.modules["aqt"].gui_hooks = Hooks()
    qt = sys.modules["aqt.qt"]
    qt.QKeySequence, qt.QAction, qt.QShortcut = QKeySequence, QAction, Stub

    sys.path.insert(0, os.path.dirname(HERE))
    import shinjers_study_desk as sd
    from shinjers_study_desk.trouble import analysis

    # Keep the sample history out of the real user_files folder.
    sd.study_day.actions.ADDON_DIR = tempfile.mkdtemp()
    sd.prefs.migrate()
    sd.prefs.set_value("keyboard.review", {"undo": "z", "bury_card": "b"})
    sd.keyboard.remap.on_profile_open()

    deck = build(col)
    sd.study_day.core.save_settings(col, {**sd.study_day.core.get_settings(col), "decks": [deck]})

    tabs = {t.id: t for t in sd.TABS}
    out = {"tabs": [{"id": t.id, "title": t.title, "icon": t.icon} for t in sd.TABS], "data": {}}
    for tab_id, t in tabs.items():
        if tab_id == "trouble":
            s = analysis.get_settings(col)
            t.result = analysis.analyze(col, [deck], s["days"], s["group"], s["depth"])
            t._result_key = t._key()
            t.selected = 0
        out["data"][tab_id] = t.data(None)

    # A short, plausible Study Day history.
    now = int(time.time())
    fmt = sd.study_day.tab.fmt_time
    out["data"]["study_day"]["history"]["entries"] = [
        {"when": fmt(now - 26 * 3600), "kind": "ahead", "label": "Study ahead 1 day (171 cards)",
         "undone": False, "note": "Finished and removed", "next": False},
        {"when": fmt(now - 3 * DAY), "kind": "unfreeze", "label": "Unfreeze (back after 4 days)",
         "undone": False, "note": "", "next": True},
        {"when": fmt(now - 7 * DAY), "kind": "freeze", "label": "Freeze reviews",
         "undone": False, "note": "", "next": False},
    ]
    out["banner"] = sd.study_day.banner.banner_html()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    col.close()
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
