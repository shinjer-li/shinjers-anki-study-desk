# Shinjer's Study Desk

One Anki window (Anki 24.11 or newer) with tabs for your study day, the topics you miss most,
and your keyboard shortcuts. It replaces three older add-ons: **Study Day Control**,
**Trouble Spots** and **Keybind Remapper**.

## Opening it

- The **Shinjer's Study Desk** link in Anki's top bar, next to Decks, Add and Browse. You can turn
  this link off in Settings.
- The **status bar on the Decks screen**: what's left today, what you've done, and how long
  tomorrow's reviews and new cards should take. Click the logo or **Open** to open the window.
- **Tools > Shinjer's Study Desk…**

**Tools > Add-ons > Shinjer's Study Desk > Config** opens the Settings tab, not a JSON editor.

The window opens maximized. It's a normal window otherwise: you can restore it to a smaller
size and keep it open next to Anki.

## The tabs

| tab | what it's for |
|---|---|
| **Study Day** | Today's numbers next to your usual range, flagged **H** (high) or **L** (low) when they're outside it. **Study ahead** pulls upcoming reviews into a temporary "Ahead" deck. **Freeze** pauses reviews for a break so they don't pile up. Also a forecast, your pace, and a history you can undo, which stays in step with Anki's own undo. |
| **Trouble Spots** | Topics ranked by how often you miss them, grouped by resource tags (First Aid, Pathoma, Boards & Beyond, Sketchy…). Topics and the cards of the one you click sit side by side, and the controls at the top fold away with the arrow next to the title. You can jump to the Browser or export a study sheet or CSV. It never changes your cards. |
| **Keyboard** | Every shortcut on the review screen, the deck overview, and everywhere else. Click an action and press a key. If the key is taken, pick what happens to the action that had it: swap, give it a spare key, or unbind it. Also "smart undo" for reviewing. |
| **About** | What the add-on does, a quick start, the version, and links to the GitHub page and issue tracker. |
| **Settings** | Light/dark and color theme, the window, the top-bar link, plus each tab's own options (decks, status bar style, conflict rule, and so on). |

## Light, dark and themes

The sun/moon button at the bottom of the left rail switches between light and dark. In
Settings, **Mode** can also be **Auto**, which follows Anki's night mode. There are eleven color
themes: **Slate** (default), Frost, Navy, Indigo, Sage, Teal, Sand, Rose, Plum, Graphite and
Paper. They change the rail and accent
color; the results sheet and the H/L flag colors stay the same. The Decks-screen status bar
uses the same theme.

## How the code is laid out

```
__init__.py     wires everything up: TABS list, top-bar link, Tools menu, Config button
window.py       the window, and passing data between Python and the page
tab.py          what every tab provides (read this before adding a tab)
prefs.py        add-on settings (look, window, keyboard) and the one-time migration
config.json     default add-on settings (documented in config.md)
common/         shared bits (the deck picker)
study_day/      Study ahead, Freeze, the day's numbers, the Decks-screen status bar
trouble/        Trouble Spots analysis (read-only)
keyboard/       the shortcut remapper and smart undo
about/          the About tab (version number, GitHub and AnkiWeb links)
settings/       the Settings tab
web/            the page: index.html, css/, js/ (see web/README.md)
user_files/     the Study Day undo history (kept when the add-on updates)
```

Each tab is a Python class (in `<tab>/tab.py`) plus a CSS and a JS file in `web/`. Python
sends a tab its data as a dict; the page draws it and sends commands back. Study Day and
Trouble Spots keep their settings in the collection, so they follow your profile. The look,
window and keyboard settings are in the add-on config, so they apply to every profile.
`web/README.md` covers the page side: the `desk` JavaScript API, the theme tokens, and
`data-cmd` clicks.

## Adding a tab

Here is a small "Notes" tab that shows a count and has one button and one setting.

**1. Python:** make `notes/__init__.py` (empty) and `notes/tab.py`:

```python
from aqt import mw

from .. import window
from ..tab import Tab


class NotesTab(Tab):
    id = "notes"          # also the JS/CSS file names and the panel id "tab-notes"
    title = "Notes"       # label on the rail
    icon = "list"         # rail icon, a name from web/js/icons.js
    live = True           # redraw when the collection changes (reviews, undo, sync)

    def data(self, desk):
        # Everything render() needs. Return None and call desk.receive(self.id, {...})
        # later if this is slow.
        return {"count": mw.col.note_count(), "big": self._big()}

    def handle(self, desk, cmd, arg):
        # The page sent "notes:<cmd>:<arg>". arg is a string, or a dict/list if
        # the page sent an object.
        if cmd == "refresh":
            desk.render()

    # Shown on the Settings tab automatically.
    def settings(self):
        return [{"title": "Notes", "rows": [
            {"key": "big", "type": "switch", "value": self._big(),
             "label": "Show the count in large type",
             "hint": "Only changes this tab."},
        ]}]

    def set_setting(self, desk, key, value):
        if key == "big":
            mw.col.set_config("study_desk_notes_big", bool(value) and value != "0")
            window.rerender("notes")      # redraw if it's the tab showing
            window.rerender("settings")   # so the switch shows its new state

    def _big(self):
        return bool(mw.col.get_config("study_desk_notes_big", False))
```

Settings row types: `"switch"`; `"choice"` with `"options": [[value, label], ...]`;
`"decks"` with `"text"` (the current selection; opens the deck picker). Any row can have a
`"hint"`.

**2. List it** in `TABS` in `__init__.py`. Settings stays last, and is always pinned to the
bottom of the rail:

```python
from .notes.tab import NotesTab
TABS = [StudyDayTab(), TroubleTab(), KeyboardTab(), NotesTab(), SettingsTab()]
```

**3. The page:** add `web/js/notes.js`:

```js
(function () {
  desk.register("notes", {
    render(el, d) {              // el is <section id="tab-notes">
      el.innerHTML =
        `<h1>Notes</h1>` +
        `<p class="lede notes-count${d.big ? " big" : ""}">${desk.num(d.count)} notes</p>` +
        `<div class="btnrow"><button class="btn" data-cmd="notes:refresh:">Refresh</button></div>`;
    },
  });
})();
```

and, if it needs styles, `web/css/notes.css`. Scope everything under `#tab-notes` and use
the color tokens from `tokens.css`, never literal colors:

```css
#tab-notes .notes-count.big { font-size: 21px; color: var(--accent-text); }
```

Any element with `data-cmd="tab:cmd:arg"` sends that command when clicked, so simple
buttons need no JavaScript. From JS, use `desk.send("notes", "cmd", arg)`.

**4. Load the files:** add `"notes"` to both lists in `ASSETS` in `window.py`:

```python
ASSETS = {
    "css": ["tokens", "base", "study_day", "trouble", "keyboard", "settings", "notes"],
    "js": ["icons", "desk", "charts", "study_day", "trouble", "keyboard", "settings", "notes"],
}
```

The rail icon comes from the tab's `icon` attribute (names are in `web/js/icons.js`).

## Running the tests

The tests need Python with the `anki` package (`pip install anki`), not Anki itself. Run each one
from its own folder:

| folder (inside `shinjers_study_desk/`) | command |
|---|---|
| `study_day/` | `python test_core.py` |
| `study_day/` | `python test_ranges.py` |
| `trouble/` | `python test_analysis.py` |
| `keyboard/` | `python test_kbr.py` |
| `shinjers_study_desk/` itself | `python test_smoke.py` |
Each ends with `ALL OK` (or `FAILURES: 0` for the keyboard test). `test_smoke.py` loads the
whole add-on with a stubbed Anki UI and asks every tab for its settings, so run it after
adding a tab.

## Moving over from the old add-ons

Turn off **Study Day Control**, **Trouble Spots** and **Keybind Remapper** before you use
Shinjer's Study Desk. They hook into the same places, so with both running you'd get two status bars
and shortcuts applied twice.

1. In **Tools > Add-ons**, select the three old add-ons and click **Toggle Enabled** to
   disable them. Don't delete them yet.
2. Install Shinjer's Study Desk and restart Anki. When your profile opens, your settings are copied
   over once (see `prefs.migrate`):
   - Keybind Remapper: your shortcuts, conflict rule, spare keys and smart-undo choice.
   - Study Day Control: the undo history files from its `user_files` folder, and its
     "stay on top" choice.
   - Study Day and Trouble Spots settings live in your collection under the same names, so
     they carry over by themselves.
3. Check the Keyboard tab, then delete the three old add-ons and restart.

Why disable instead of delete: the shortcuts and history are read from the old add-ons'
folders (`addons21/keybind_remapper` and `addons21/study_day_control`). If you delete those
first, Shinjer's Study Desk starts with default shortcuts and an empty history. The migration only
looks for those folder names, and it runs once; it won't run again later.

### From Study Desk (the old name)

This add-on used to be called **Study Desk** (folder `study_desk`). Disable Study Desk the
same way, install Shinjer's Study Desk and restart: its settings and history are copied over
once from `addons21/study_desk`. Then delete Study Desk. Running both gives you two status
bars and two windows.
