# Shinjer's Study Desk page

`window.py` loads `index.html` with Anki's `stdHtml`, then every file in
`css/` and `js/` listed in `window.ASSETS` (in order). Scripts run before the
body exists, so nothing touches the DOM until `DOMContentLoaded`.
No network: no fonts, no CDNs, no images. Icons are inline SVG from `js/icons.js`.

## Files

| file | owns |
|---|---|
| css/tokens.css | every color, font and shadow token; light/dark; the 4 themes |
| css/base.css   | shell (rail, content), shared components |
| css/<tab>.css  | only that tab's layout, scoped under `#tab-<id>` |
| js/icons.js    | `desk.icon(name)` → SVG string |
| js/desk.js     | boot, tab switching, data in, commands out, theme, helpers |
| js/charts.js   | `charts.bars(el, opts)` SVG bar chart (Study Day) |
| js/<tab>.js    | `desk.register("<id>", {render})` |

## Theme

`<html>` carries `data-dark="1"` (when dark) and `data-theme="slate|frost|navy|…"` (the list is prefs.THEMES).
Dark = mode "dark", or mode "auto" and Anki is in night mode.
Components use tokens only, never literal colors.

Tokens (all defined in tokens.css, with light teal as the fallback, overridden by `[data-dark="1"]`
and `[data-theme=…]`): `--ground --page --sheet --ink --ink-2 --ink-3 --rule --rule-2
--hover --row-sel --shell --shell-ink --shell-muted --shell-sub --shell-hover
--accent --accent-ink --accent-hover --accent-text --band --band-strong --focus
--sel-bg --sel-ink --flag-h --flag-l --hi --lo --crit-bg --crit-line
--cap-green --cap-gold --cap-grey --cap-lblue --cap-lav --cap-text
--shadow --win-shadow --ui --mono`.

## desk.js API

```js
desk.register(id, { render(el, data) })   // el = <section id="tab-<id>">; set el.innerHTML
desk.send(tab, cmd, arg)                  // pycmd(`${tab}:${cmd}:${arg}`); objects → JSON
desk.state[id]                            // last data the tab got
desk.esc(s)                               // HTML-escape
desk.num(n, digits=0)                     // "1,234" / "4.5", tabular in CSS
desk.icon(name)                           // see icons.js for names
desk.rangeBar(value, range, max)          // HTML for a .rb range bar (range = [lo, hi] or null)
desk.flag(f)                              // HTML for "H"/"L" flag or ""
```

Python calls `desk.boot`, `desk.receive(id, data)` (replace + render),
`desk.patch(id, part)` (merge + render), `desk.show(id)`, `desk.fail(id, msg)`,
`desk.setAppearance({mode, theme})`, `desk.setNight(bool)`.

Clicks: any element with `data-cmd="tab:cmd:arg"` sends that command; no JS needed.
Re-rendering replaces innerHTML, so bind events by delegation on `el` (once) or
inline via data-cmd. Keep focus/scroll where sensible.

## Adding a tab

1. Python: subclass `Tab` (see `tab.py`), set `icon = "<name from icons.js>"` for its
   rail icon, and add it to `TABS` in `__init__.py`.
2. Add `css/<id>.css` and `js/<id>.js`, list them in `window.ASSETS`.
3. Its `settings()` rows appear on the Settings tab automatically.
