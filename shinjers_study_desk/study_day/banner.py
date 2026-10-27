"""
The status bar at the top of Anki's Decks screen: what's left today, what's
done, tomorrow and the Ahead deck, each with its time, plus quick links and a
button to open Shinjer's Study Desk. "Hide" shrinks it to a small pill; it can
be turned off in Settings.

It uses the same color tokens as the window (web/css/tokens.css), in the
theme picked in Settings, and follows Anki's light/dark mode.
"""

from __future__ import annotations

import html

from aqt import mw

from .. import prefs
from . import core, status

CMD = "shinjerdesk:"


def _logo(size: int) -> str:
    src = f"/_addons/{prefs.ADDON}/web/img/logo.png"
    return f'<img class="sdk-logo" src="{src}" width="{size}" height="{size}" alt="">'


CSS = """
<style>
.sdk{font:12.5px/1.45 var(--ui,system-ui,sans-serif);
  color:var(--ink,#15201f);max-width:760px;margin:10px auto 8px;text-align:left;
  font-variant-numeric:tabular-nums}
.sdk-strip{display:flex;align-items:stretch;background:var(--sheet,#fff);border-radius:6px;
  overflow:hidden;border:1px solid var(--rule,#e1e6e5);box-shadow:var(--shadow,none)}
.sdk-cap{flex:none;display:flex;align-items:center;justify-content:center;
  background:none;border:0;padding:0 0 0 14px;cursor:pointer}
.sdk-logo{display:block;border-radius:8px;object-fit:cover}
.sdk-cap:hover .sdk-logo{filter:brightness(1.1)}
.sdk-t{flex:1;min-width:0;padding:9px 18px 9px 16px}
.sdk-head{font-size:13.5px;font-weight:650;margin-bottom:3px}
.sdk-g{display:grid;grid-template-columns:auto auto 1fr;gap:1px 20px;align-items:baseline;
  font-size:12px;color:var(--ink-2)}
.sdk-g .k,.sdk-g .t{color:var(--ink-3)}
.sdk-g b{color:var(--ink);font-weight:600}
.sdk-g .lead{font-size:13.5px;color:var(--ink)}
.sdk-g .k.lead{font-weight:650}
.sdk-g .t.lead{font-weight:600}
.sdk-g .v.lead b{font-weight:650}
.sdk-l{display:flex;align-items:center;flex-wrap:wrap;justify-content:flex-end;gap:4px 14px;
  padding:6px 12px 6px 0;font-size:12px}
.sdk a{color:var(--accent-text,#0b5d57);font-weight:600;text-decoration:underline;
  text-underline-offset:3px;text-decoration-thickness:1px;cursor:pointer;white-space:nowrap}
.sdk a:hover{text-decoration-thickness:2px}
.sdk a.sdk-open{color:var(--accent-ink,#fff);background:var(--accent,#0b5d57);text-decoration:none;
  padding:3px 10px;border-radius:4px}
.sdk a.sdk-open:hover{background:var(--accent-hover,#08504b)}
.sdk a.sdk-quiet{color:var(--ink-3,#5e6b69);font-weight:500}
.sdk-track{display:inline-block;width:90px;height:4px;background:var(--rule,#e1e6e5);border-radius:2px;
  overflow:hidden;vertical-align:middle;margin-left:8px}
.sdk-track i{display:block;height:100%;border-radius:2px;background:var(--cap-green,#2e9e5b)}
.sdk.compact{display:flex;justify-content:center}
.sdk-pill{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--rule,#e1e6e5);
  background:var(--sheet,#fff);border-radius:999px;padding:3px 12px 3px 4px;cursor:pointer;color:inherit;
  font:inherit;box-shadow:var(--shadow,none)}
.sdk-pill:hover{border-color:var(--rule-2,#c8d0cf)}
.sdk-pill .sdk-logo{border-radius:50%}
</style>
"""


def _link(cmd: str, text: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f"<a{c} href=# onclick=\"return pycmd('{CMD}{cmd}')\">{html.escape(text)}</a>"


def banner_html() -> str:
    col = mw.col
    settings = core.get_settings(col)
    mode = settings["banner"]
    if mode == "off":
        return ""
    look = prefs.appearance()
    dark = look["mode"] == "dark" or (look["mode"] == "auto" and _night())
    css_url = f"/_addons/{prefs.ADDON}/web/css/tokens.css"
    scope = f'data-theme="{look["theme"]}" data-dark="{1 if dark else 0}"'

    snap = status.snapshot(col)
    head = status.headline(col, snap)
    head_html = f'<link rel="stylesheet" href="{css_url}">{CSS}'

    if mode == "compact":
        return (
            f'{head_html}<div class="sdk sd-tokens compact" {scope}>'
            f"<button class=\"sdk-pill\" title=\"Show the Shinjer's Study Desk status bar\" "
            f"onclick=\"return pycmd('{CMD}show')\">{_logo(22)}"
            f"<span>{html.escape(head['short'])}</span></button></div>"
        )

    body = _summary(snap, head)
    links = [_link(a["cmd"], a["label"]) for a in head["actions"]]
    links += [_link("open", "Open", "sdk-open"), _link("hide", "Hide", "sdk-quiet")]
    return (
        f'{head_html}<div class="sdk sd-tokens" {scope} role="status">'
        f'<div class="sdk-strip">'
        f"<button class=\"sdk-cap\" title=\"Open Shinjer's Study Desk\" onclick=\"return pycmd('{CMD}open')\">"
        f"{_logo(32)}</button>"
        f'<div class="sdk-t">{body}</div>'
        f'<div class="sdk-l">{"".join(links)}</div></div></div>'
    )


def _summary(snap: dict, head: dict) -> str:
    """Rows of label / cards / time: Today (while cards are left), Done,
    Tomorrow and Ahead. With nothing left today, the day's headline goes on
    top instead of the Today row."""
    e = html.escape
    pace, fc = snap["pace"], snap["forecast"]
    due, new = fc["due"][0], snap["new_left"]

    rows = []
    top = ""
    if head["state"] == "due":
        mins = status.study_minutes(pace, due, new)
        rows.append(("Today", status.cards_text(due, new, bold=True), status.minutes_text(mins), "lead"))
    elif head["state"] == "done":
        top = "All caught up today"
    elif head["state"] == "frozen":
        top = head["short"]
    else:
        top = head["title"]

    done, done_min = pace["reviews"][-1], round(pace["minutes"][-1])
    rows.append(("Done", f"<b>{done:,}</b> {'card' if done == 1 else 'cards'}",
                 status.minutes_text(done_min) if done else "", ""))
    if not snap["state"]["frozen"]:
        reviews = fc["due"][1]
        new_t = core.new_per_day(mw.col, snap["settings"]["decks"])
        mins = status.study_minutes(pace, reviews, new_t)
        rows.append(("Tomorrow", status.cards_text(reviews, new_t, bold=True) or "Nothing due",
                     status.minutes_text(mins) if mins else "", ""))
    info = snap["ahead"]
    if info:
        pct = info["done"] / info["total"] * 100 if info["total"] else 100
        track = f'<span class="sdk-track"><i style="width:{pct:.0f}%"></i></span>'
        mins = status.study_minutes(pace, info["left"] - info["left_new"], info["left_new"])
        rows.append(("Ahead", f"<b>{info['done']}</b> of {info['total']}{track}",
                     status.minutes_text(mins) if mins else "", ""))

    grid = "".join(
        f'<span class="k {c}">{k}</span><span class="v {c}">{v}</span><span class="t {c}">{t}</span>'
        for k, v, t, c in rows
    )
    head_html = f'<div class="sdk-head">{e(top)}</div>' if top else ""
    return f'{head_html}<div class="sdk-g">{grid}</div>'


def _night() -> bool:
    from aqt.theme import theme_manager

    return theme_manager.night_mode


def on_deck_browser_render(deck_browser, content) -> None:
    try:
        content.tree = banner_html() + content.tree
    except Exception:
        # The status bar is a convenience; never break the Decks screen.
        pass


def set_mode(mode: str) -> None:
    settings = core.get_settings(mw.col)
    settings["banner"] = mode
    core.save_settings(mw.col, settings)
    from .tab import changed

    changed()
