"""
Tests for analysis.py against a real (temporary) Anki collection.

Needs the `anki` package (pip install anki). Run:
    python test_analysis.py
"""

import os
import sys
import tempfile
import time

from anki.collection import Collection

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis as a  # noqa: E402

FA = "#AK_Step1_v12::#FirstAid::{}"
_rid = [int(time.time() * 1000) - 10 * 86400 * 1000]


def add(col, deck, text, tags, history, days_ago=1, rtype=1):
    """Add a card; history is a string of buttons pressed, e.g. "3133"."""
    note = col.new_note(col.models.by_name("Cloze"))
    note["Text"] = text
    note.tags = tags
    col.add_note(note, col.decks.id(deck))
    card = note.cards()[0]
    card.lapses = history.count("1")
    col.update_card(card)
    base = int((time.time() - days_ago * 86400) * 1000)
    for i, ease in enumerate(history):
        col.db.execute(
            "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type) "
            "values (?,?,0,?,1,1,2500,1000,?)",
            base + i * 1000 + card.id % 1000, card.id, int(ease), rtype,
        )
    return card.id


def test_text_and_tags():
    assert a.clean_text("The {{c1::thyroid::organ}} makes <b>T4</b>&nbsp;") == \
        "The [thyroid] makes T4"
    assert a.clean_text("<img src=x.jpg>") == "(image or media card)"
    tags = [FA.format("08_Endocrine::03_Physiology::05_Thyroid_hormones"),
            FA.format("08_Endocrine::03_Physiology::06_Other"),
            "#AK_Step1_v12::^Systems::Endocrine"]
    assert a.topics_for_tags(tags, ["#firstaid"], False, 1) == ["Endocrine"]
    assert a.topics_for_tags(tags, ["#firstaid"], False, 3) == [
        "Endocrine › Physiology › Thyroid hormones",
        "Endocrine › Physiology › Other"]
    assert a.topics_for_tags(tags, ["^systems"], False, 2) == ["Endocrine"]
    sk = ["#AK_Step1_v12::#SketchyPharm::02_Antibiotics::03_Penicillins"]
    assert a.topics_for_tags(sk, ["#sketchy*"], True, 2) == [
        "SketchyPharm › Antibiotics"]
    # Custom multi-part tag, case-insensitive
    assert a.topics_for_tags(["My::Weak_Stuff::Renal"], ["my", "weak_stuff"],
                             False, 1) == ["Renal"]
    assert a.topics_for_deck("AnKing::Step1::Cardio", ["AnKing::Step1"], 2) == [
        "Step1 › Cardio"]
    print("text and tags ok")


def test_analyze():
    col = Collection(tempfile.mktemp(suffix=".anki2"))
    thy = [FA.format("08_Endocrine::03_Physiology::05_Thyroid")]
    car = [FA.format("09_Cardio::02_Anatomy")]
    c1 = add(col, "AnKing", "{{c1::TSH}} rises", thy, "1131")   # 3 misses
    c2 = add(col, "AnKing", "{{c1::T3}} active", thy, "3313")   # 1 miss
    c3 = add(col, "AnKing", "aorta {{c1::x}}", car, "3333")     # 0
    c4 = add(col, "AnKing", "none {{c1::y}}", [], "13")         # untagged
    old = add(col, "AnKing", "old {{c1::z}}", car, "1111", days_ago=60)
    other = add(col, "Other", "{{c1::other}}", thy, "1111")
    learn = add(col, "AnKing", "{{c1::new}}", car, "111", rtype=0)

    r = a.analyze(col, [], 30, "firstaid", 2)
    names = [t.name for t in r.topics]
    assert names[0] == "Endocrine › Physiology", names  # worst first
    endo = r.topics[0]
    # c1, c2 and "other" (all decks), learning card excluded
    assert (endo.cards, endo.reviews, endo.again) == (3, 12, 8), endo
    assert old not in r.cards and learn not in r.cards
    assert "(no First Aid sections tag)" in names

    # Deck scope
    r = a.analyze(col, [col.decks.id("AnKing")], 30, "firstaid", 2)
    assert other not in r.cards
    assert [c.cid for c in r.missed_cards()][0] == c1
    assert set(c.cid for c in r.missed_cards()) == {c1, c2, c4}
    assert [c.cid for c in r.missed_cards("Endocrine › Physiology")] == [c1, c2]
    assert r.cards[c1].text == "[TSH] rises"
    assert (r.total_reviews, r.total_again) == (14, 5)

    # All time + learning
    r = a.analyze(col, [col.decks.id("AnKing")], 0, "firstaid", 1,
                  include_learning=True)
    assert old in r.cards and learn in r.cards
    assert c3 in r.cards and r.cards[c3].again == 0

    # Group by subdeck and custom
    r = a.analyze(col, [], 30, "deck", 1)
    assert {t.name for t in r.topics} == {"AnKing", "Other"}
    try:
        a.analyze(col, [], 30, "custom", 1, custom="  ")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass

    # Exports
    csv = a.export_csv(r)
    assert "AnKing,44,[TSH] rises,3,4,3,AnKing" in csv, csv
    page = a.export_html(r, "AnKing · last 30 days")
    assert "<b>TSH</b>" in page and "missed 3×" in page

    # Deleted deck in settings is ignored
    r = a.analyze(col, [123456789], 30, "firstaid", 2)
    assert r.cards_studied > 0
    # Empty collection
    empty = Collection(tempfile.mktemp(suffix=".anki2"))
    r = a.analyze(empty, [], 30, "firstaid", 3)
    assert r.topics == [] and r.again_rate == 0
    assert "No misses" in a.export_html(r, "x")
    col.close(); empty.close()
    print("analyze ok")


if __name__ == "__main__":
    test_text_and_tags()
    test_analyze()
    print("ALL OK")
