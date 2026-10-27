# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

(Rendered inside Anki desktop's Qt WebEngine via AnkiWebView, aqt 24.11+, Linux/macOS/Windows.
Not a website: no external network requests, no CDN.)

## Users
Medical students preparing for USMLE Step 1 with Anki (AnKing-style decks tagged by First Aid,
Pathoma, Boards & Beyond, Sketchy). The author plus classmates who install it themselves, so it
must explain itself without the author present. Used daily at a desk, before or after a review
session, often in dark mode.

## Product Purpose
**Study Desk** consolidates three add-ons into one window with tabs:
- **Study Day**: plan the day: Study Ahead (pull upcoming reviews into a temporary filtered
  deck), Freeze (pause reviews for a break without a pile-up), forecast and pace, and a
  history with undo that stays in sync with Anki's own undo.
- **Trouble Spots**: which topics and cards are missed most (lapse rate, smoothed), grouped by
  resource tags, with a card drill-down, Browser jump, and printable study-sheet / CSV export.
- **Keyboard**: a full shortcut editor for review, overview and app-wide actions: click an
  action, press a key, see conflicts and their resolution (swap / spare key / delete), and the
  review-only "smart undo".
Success: a classmate can open it, understand their day and weak areas in seconds, and change
keys without editing JSON.

## Positioning
Built around how Step 1 students actually study: resource-tag topics (First Aid sections,
Pathoma chapters), study-ahead/vacation handling that Anki lacks, and undo that matches reality.

## Operating Context
Opened from the "Study Desk" link in Anki's top bar, Tools > Study Desk… or the Decks-screen
status bar. Non-modal, resizable window
kept open beside the main Anki window. A compact status bar also lives on the Decks screen.

## Capabilities and Constraints
- Logic carried over from the old add-ons: study_day/core.py + actions.py,
  trouble/analysis.py, keyboard/resolver.py + smart_undo.py. Behavior must be preserved.
- Light and dark mode (Anki adds `.night-mode` on `<html>`).
- Fonts must be bundled or system; nothing fetched from the internet.
- Open decision: whether the three packages merge into one package or stay separate with a
  shared window. **Resolved: merged into one package (see Decisions).**

## Decisions

### One "Study Desk" package (October 2026)
Study Day Control, Trouble Spots and Keybind Remapper are merged into a single add-on,
`study_desk`, replacing all three.
- **Who it's for:** the author and classmates, who install one add-on instead of three and
  get one window, one settings place and one look.
- **Keyboard:** a full shortcut editor tab (press a key, see the conflict, choose swap /
  spare key / unbind), not a JSON config.
- **Settings tab:** add-on-wide settings (mode, theme, window, top-bar link) plus every
  tab's own options. Tools > Add-ons > Config opens it.
- **Theme toggle:** a light/dark button on the rail; Auto follows Anki's night mode; four
  color themes (Teal, Navy, Plum, Graphite).
- **Entry points on Anki's main screen:** a "Study Desk" link in the top bar, the status bar
  on the Decks screen, and Tools > Study Desk….
- **Migration:** the old add-ons' shortcuts, undo history and stay-on-top choice are copied
  once; the old add-ons must be disabled because they register the same hooks.

## Evidence on Hand
Real user data only at runtime. Mockups use clearly fake sample numbers.

## Product Principles
1. Explain the consequence before the action (what happens to cards if you don't finish).
2. Reality wins: history and numbers reflect the collection, not the add-on's assumptions.
3. Never lose or silently change scheduling; everything is undoable.
4. Dense but legible: students check this daily, so the answer should be visible at a glance.
