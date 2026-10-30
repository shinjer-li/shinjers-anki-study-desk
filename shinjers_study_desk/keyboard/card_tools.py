"""
Extra review-screen actions that Anki doesn't have, bound like any other
shortcut on the Keyboard tab:

- Reveal next / reveal all: AnKing's green cloze one-by-one buttons.
- Open next hint / open all hints: AnKing's hint buttons (First Aid, Bootcamp...)
  and Anki's own {{hint:}} fields.
- Copy image: the image under the mouse, or the card's images one per press.
- Copy card text: the card's main text with the clozes filled in, without
  Extra or the hints, ready to paste into a search.

Plus "Copy image" in the review screen's right-click menu. The page side is
web/card/card_tools.js, loaded into the reviewer.
"""

from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

from aqt import gui_hooks, mw
from aqt.qt import QGuiApplication, QImage, QUrl
from aqt.utils import tooltip

from .. import prefs

JS = f"/_addons/{prefs.ADDON}/web/card/card_tools.js"


def _call(fn: str, done) -> None:
    """Run studyDeskCard.<fn>() on the review screen and hand the result to done."""
    if mw.state != "review" or not mw.reviewer.card:
        return
    mw.reviewer.web.evalWithCallback(
        f"window.studyDeskCard ? studyDeskCard.{fn}() : null", done
    )


def _say(empty_msg: str):
    return lambda ok: None if ok else tooltip(empty_msg)


def reveal_next() -> None:
    _call("revealNext", _say("Nothing left to reveal"))


def reveal_all() -> None:
    _call("revealAll", _say("This card has no Reveal buttons"))


def hint_next() -> None:
    _call("hintNext", _say("No more hints to open"))


def hint_all() -> None:
    _call("hintAll", _say("This card has no hints"))


# ── copy image ────────────────────────────────────────────────────────────────


def media_path(url: str) -> str | None:
    """The file in the media folder that a card's image URL points at."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "file", ""):
        return None
    if parsed.scheme in ("http", "https") and parsed.hostname not in ("127.0.0.1", "localhost"):
        return None
    name = unquote(parsed.path).lstrip("/")
    media = mw.col.media.dir()
    path = os.path.normpath(os.path.join(media, name))
    if not path.startswith(os.path.normpath(media) + os.sep) or not os.path.isfile(path):
        return None
    return path


def copy_image_file(path: str) -> bool:
    image = QImage(path)
    if image.isNull():
        return False
    QGuiApplication.clipboard().setImage(image)
    return True


def copy_image() -> None:
    def done(picked) -> None:
        if not picked:
            tooltip("No image on this card")
            return
        path = media_path(picked.get("src", ""))
        if not path or not copy_image_file(path):
            tooltip("Couldn't copy that image")
            return
        what = f"{picked['section']} image" if picked.get("section") else "Image"
        count = f" ({picked['index']} of {picked['total']})" if picked.get("total", 1) > 1 else ""
        tooltip(f"{what} copied{count}", period=1500)

    _call("pickImage", done)


# ── copy card text ────────────────────────────────────────────────────────────


def copy_text() -> None:
    def done(text) -> None:
        if not text:
            tooltip("No text on this card")
            return
        QGuiApplication.clipboard().setText(text)
        preview = text.replace("\n", " ")
        if len(preview) > 70:
            preview = preview[:70] + "…"
        tooltip(f"Copied: {preview}", period=1800)

    _call("cardText", done)


# (action name, default keys, handler). The remapper lists these on the
# Keyboard tab's Review section next to Anki's own actions.
REVIEW_EXTRAS = [
    ("reveal_next", ["c"], reveal_next),
    ("reveal_all", ["v"], reveal_all),
    ("hint_next", [], hint_next),
    ("hint_all", [], hint_all),
    ("copy_image", ["p"], copy_image),
    ("copy_text", ["g"], copy_text),
]


# ── page and menu ─────────────────────────────────────────────────────────────


def on_webview_will_set_content(web_content, context) -> None:
    from aqt.reviewer import Reviewer

    if isinstance(context, Reviewer):
        web_content.js.append(JS)


def on_context_menu(webview, menu) -> None:
    """Right-click on an image on the review screen: Copy image."""
    if webview is not mw.reviewer.web or not mw.col:
        return
    request = webview.lastContextMenuRequest()
    if not request or request.mediaType() != request.MediaType.MediaTypeImage:
        return
    url: QUrl = request.mediaUrl()
    path = media_path(url.toString())
    action = menu.addAction("Copy image")
    if path:
        action.triggered.connect(
            lambda: tooltip("Image copied", period=1200)
            if copy_image_file(path)
            else tooltip("Couldn't copy that image")
        )
    else:
        # Not in the media folder (e.g. a web image): let the browser copy it.
        from aqt.qt import QWebEnginePage

        action.triggered.connect(
            lambda: webview.page().triggerAction(QWebEnginePage.WebAction.CopyImageToClipboard)
        )


def setup() -> None:
    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
    gui_hooks.webview_will_show_context_menu.append(on_context_menu)
