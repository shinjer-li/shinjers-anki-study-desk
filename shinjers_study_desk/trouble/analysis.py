"""
Finds the topics and cards you miss most. Read-only: nothing in the
collection is changed. No Qt here, so it can be tested with just `anki`.

A "miss" is pressing Again on a card you'd already learned (a review). By
default, Again presses while first learning a new card don't count, because
missing brand-new cards is normal. Optionally they can be included.

Topics come from tags. For AnKing, the First Aid tags look like
    #AK_Step1_v12::#FirstAid::08_Endocrine::03_Physiology::05_Thyroid_hormones
and with detail level 3 the topic is "Endocrine › Physiology › Thyroid hormones".
"""

from __future__ import annotations

import csv
import html
import io
import json
import re
import time
from dataclasses import dataclass, field

# key -> (label, tag components that start the topic path, keep matched part)
# A component ending in "*" matches by prefix (e.g. all the Sketchy resources).
GROUPS = {
    "firstaid": ("First Aid sections", ["#firstaid"], False),
    "systems": ("Organ systems (^Systems)", ["^systems"], False),
    "bnb": ("Boards & Beyond videos", ["#b&b"], False),
    "pathoma": ("Pathoma chapters", ["#pathoma"], False),
    "sketchy": ("Sketchy videos", ["#sketchy*"], True),
    "bootcamp": ("Bootcamp videos", ["#bootcamp"], False),
    "physeo": ("Physeo videos", ["#physeo"], False),
    "deck": ("Subdecks", None, False),
    "custom": ("Custom tag…", None, False),
}

PERIODS = [(7, "Last 7 days"), (14, "Last 14 days"), (30, "Last 30 days"),
           (90, "Last 90 days"), (0, "All time")]

# Revlog types: 0 learn, 1 review, 2 relearn, 3 filtered/early, 4 manual.
REVIEW_TYPES = (1, 3)
LEARNING_TYPES = (0, 2)

# How strongly topics with few reviews are pulled toward your overall rate.
SMOOTHING = 20

DEFAULT_SETTINGS = {
    "decks": [],
    "days": 30,
    "group": "firstaid",
    "depth": 3,
    "custom": "",
    "include_learning": False,
}
SETTINGS_KEY = "trouble_spots_settings"

CLOZE = re.compile(r"\{\{c\d+::(.*?)(?:::[^}]*)?\}\}", re.S)
SOUND = re.compile(r"\[sound:[^\]]*\]")
TAGS = re.compile(r"<[^>]+>")
NUMBERING = re.compile(r"^\d+[_.\s-]*")


@dataclass
class CardStat:
    cid: int
    nid: int
    text: str
    deck: str
    lapses: int
    difficulty: float | None  # FSRS difficulty 1-10, if FSRS is on
    ease: int  # SM-2 ease in %, 0 for new
    reviews: int = 0
    again: int = 0
    topics: list[str] = field(default_factory=list)

    @property
    def again_rate(self) -> float:
        return self.again / self.reviews if self.reviews else 0.0


@dataclass
class TopicStat:
    name: str
    cards: int = 0  # cards studied in the period
    missed_cards: int = 0
    reviews: int = 0
    again: int = 0
    trouble: float = 0.0  # smoothed again rate
    card_ids: list[int] = field(default_factory=list)

    @property
    def again_rate(self) -> float:
        return self.again / self.reviews if self.reviews else 0.0


@dataclass
class Result:
    topics: list[TopicStat]
    cards: dict[int, CardStat]  # only cards studied in the period
    total_reviews: int
    total_again: int
    cards_studied: int
    uses_fsrs: bool
    group_label: str

    @property
    def again_rate(self) -> float:
        return self.total_again / self.total_reviews if self.total_reviews else 0.0

    def missed_cards(self, topic: str | None = None) -> list[CardStat]:
        """Cards with at least one miss, worst first (optionally one topic)."""
        if topic is None:
            cards = self.cards.values()
        else:
            t = next((t for t in self.topics if t.name == topic), None)
            cards = [self.cards[c] for c in t.card_ids] if t else []
        missed = [c for c in cards if c.again]
        missed.sort(key=lambda c: (-c.again, -c.again_rate, -c.lapses))
        return missed


# ── Text helpers ──────────────────────────────────────────────────────────────


def clean_text(sfld: str) -> str:
    """Card text for display: cloze answers shown in [brackets]."""
    text = CLOZE.sub(lambda m: f"[{m.group(1)}]", sfld or "")
    text = SOUND.sub("", text)
    text = TAGS.sub(" ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "(image or media card)"


def clean_component(part: str) -> str:
    part = part.lstrip("#^!*")
    part = NUMBERING.sub("", part) or part
    return part.replace("_", " ").strip()


def _matches(component: str, pattern: str) -> bool:
    if pattern.endswith("*"):
        return component.startswith(pattern[:-1])
    return component == pattern


def topics_for_tags(
    tags: list[str], patterns: list[str], keep_match: bool, depth: int
) -> list[str]:
    """Topic names (deduplicated) a note's tags place it under."""
    found = []
    for tag in tags:
        parts = tag.split("::")
        lower = [p.lower() for p in parts]
        n = len(patterns)
        for i in range(len(parts) - n + 1):
            if all(_matches(lower[i + k], patterns[k]) for k in range(n)):
                start = i if keep_match else i + n
                path = parts[start:start + depth]
                if path:
                    name = " › ".join(clean_component(p) for p in path)
                    if name not in found:
                        found.append(name)
                break
    return found


def topics_for_deck(deck_name: str, root_names: list[str], depth: int) -> list[str]:
    """Subdeck path below the selected deck it belongs to."""
    parts = deck_name.split("::")
    best = 0
    for root in root_names:
        r = root.split("::")
        if parts[: len(r)] == r and len(r) > best:
            best = len(r) - 1  # keep the selected deck itself as level 1
    path = parts[best:best + depth]
    return [" › ".join(path)]


# ── Analysis ──────────────────────────────────────────────────────────────────


def get_settings(col) -> dict:
    return {**DEFAULT_SETTINGS, **(col.get_config(SETTINGS_KEY, None) or {})}


def save_settings(col, settings: dict) -> None:
    col.set_config(SETTINGS_KEY, settings)


def scope_ids(col, deck_ids: list[int]) -> set[int] | None:
    ids: set[int] = set()
    for did in deck_ids:
        deck = col.decks.get(did, default=False)
        if deck and not deck["dyn"]:
            ids.update(col.decks.deck_and_child_ids(did))
    return ids or None


def group_patterns(group: str, custom: str) -> tuple[list[str] | None, bool, str]:
    label, patterns, keep = GROUPS.get(group, GROUPS["firstaid"])
    if group == "custom":
        patterns = [p.strip().lower() for p in custom.split("::") if p.strip()]
        label = f"Tag “{custom.strip()}”"
    return patterns, keep, label


def analyze(
    col,
    deck_ids: list[int],
    days: int,
    group: str,
    depth: int,
    custom: str = "",
    include_learning: bool = False,
) -> Result:
    scope = scope_ids(col, deck_ids)
    patterns, keep, label = group_patterns(group, custom)
    if group == "custom" and not patterns:
        raise ValueError("Type a tag for the Custom grouping first.")

    deck_names = {d.id: d.name for d in col.decks.all_names_and_ids()}
    root_names = [deck_names[d] for d in deck_ids if d in deck_names]

    # Review history in the period.
    types = REVIEW_TYPES + (LEARNING_TYPES if include_learning else ())
    cutoff = 0 if days <= 0 else int((time.time() - days * 86400) * 1000)
    per_card: dict[int, list[int]] = {}
    for cid, ease in col.db.execute(
        f"select cid, ease from revlog where id > ? and ease > 0 "
        f"and type in ({','.join(map(str, types))})",
        cutoff,
    ):
        stat = per_card.setdefault(cid, [0, 0])
        stat[0] += 1
        if ease == 1:
            stat[1] += 1

    cards: dict[int, CardStat] = {}
    uses_fsrs = False
    rows = col.db.execute(
        "select c.id, c.nid, c.did, c.odid, c.lapses, c.factor, c.data, "
        "n.sfld, n.tags from cards c join notes n on n.id = c.nid "
        f"where c.id in (select distinct cid from revlog where id > ? and ease > 0 "
        f"and type in ({','.join(map(str, types))}))",
        cutoff,
    )
    for cid, nid, did, odid, lapses, factor, data, sfld, tags in rows:
        if cid not in per_card:
            continue
        home = odid or did
        if scope is not None and home not in scope:
            continue
        difficulty = None
        if data:
            try:
                d = json.loads(data).get("d")
                if d:
                    difficulty = round(float(d), 1)
                    uses_fsrs = True
            except (ValueError, AttributeError):
                pass
        reviews, again = per_card[cid]
        card = CardStat(
            cid=cid,
            nid=nid,
            text=clean_text(str(sfld)),
            deck=deck_names.get(home, "?"),
            lapses=lapses,
            difficulty=difficulty,
            ease=factor // 10,
            reviews=reviews,
            again=again,
        )
        if group == "deck":
            card.topics = topics_for_deck(card.deck, root_names, depth)
        else:
            card.topics = topics_for_tags(tags.split(), patterns, keep, depth)
        if not card.topics:
            card.topics = [f"(no {label} tag)"]
        cards[cid] = card

    topics: dict[str, TopicStat] = {}
    for card in cards.values():
        for name in card.topics:
            t = topics.setdefault(name, TopicStat(name))
            t.cards += 1
            t.reviews += card.reviews
            t.again += card.again
            t.missed_cards += 1 if card.again else 0
            t.card_ids.append(card.cid)

    total_reviews = sum(c.reviews for c in cards.values())
    total_again = sum(c.again for c in cards.values())
    overall = total_again / total_reviews if total_reviews else 0.0
    for t in topics.values():
        t.trouble = (t.again + SMOOTHING * overall) / (t.reviews + SMOOTHING)

    ordered = sorted(topics.values(), key=lambda t: (-t.trouble, -t.again))
    return Result(
        topics=ordered,
        cards=cards,
        total_reviews=total_reviews,
        total_again=total_again,
        cards_studied=len(cards),
        uses_fsrs=uses_fsrs,
        group_label=label,
    )


# ── Export ────────────────────────────────────────────────────────────────────


def export_csv(result: Result) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Topic", "Topic trouble %", "Card", "Times missed", "Reviews",
                "Lapses (all time)", "Deck"])
    for topic in result.topics:
        for card in result.missed_cards(topic.name):
            w.writerow([topic.name, f"{topic.trouble * 100:.0f}", card.text,
                        card.again, card.reviews, card.lapses, card.deck])
    return out.getvalue()


def export_html(
    result: Result, subtitle: str, max_topics: int = 40, cards_per_topic: int = 15
) -> str:
    """A printable study sheet: worst topics first, with the cards missed."""
    e = html.escape
    sections = []
    shown = [t for t in result.topics if t.again][:max_topics]
    for i, topic in enumerate(shown, 1):
        missed = result.missed_cards(topic.name)
        items = "".join(
            f"<li>{_bold_answers(e(c.text))} "
            f"<span class=m>missed {c.again}×</span></li>"
            for c in missed[:cards_per_topic]
        )
        more = len(missed) - cards_per_topic
        if more > 0:
            items += f"<li class=m>…and {more} more</li>"
        sections.append(
            f"<section><h2>{i}. {e(topic.name)}</h2>"
            f"<p class=m>Missed {topic.again} of {topic.reviews} reviews "
            f"({topic.again_rate * 100:.0f}%) · {topic.missed_cards} of "
            f"{topic.cards} cards</p><ol>{items}</ol></section>"
        )
    body = "".join(sections) or "<p>No misses in this period. Nice work!</p>"
    return f"""<!doctype html><html><head><meta charset=utf-8>
<title>Trouble Spots</title><style>
body{{font:15px/1.5 system-ui,sans-serif;max-width:820px;margin:32px auto;padding:0 16px;color:#222}}
h1{{margin-bottom:0}} h2{{font-size:17px;margin:28px 0 2px;border-bottom:1px solid #ddd}}
.m{{color:#777;font-size:13px}} li{{margin:5px 0}} b{{color:#b45309}}
section{{break-inside:avoid}} @media print{{body{{margin:0}}}}
</style></head><body>
<h1>Trouble Spots</h1>
<p class=m>{e(subtitle)} · {result.total_reviews} reviews, {result.again_rate * 100:.1f}%
missed overall · cloze answers in <b>bold</b></p>
{body}</body></html>"""


def _bold_answers(escaped: str) -> str:
    return re.sub(r"\[([^\[\]]*)\]", r"<b>\1</b>", escaped)
