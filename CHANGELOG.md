# What's new

## 1.1.0 (October 2026)

- **Review keys for AnKing cards**: `c` reveals the next cloze and `v` reveals them all (the
  green Reveal Next / Toggle All buttons). Anki's "Replay own voice" moves from `v` to a spare
  key. "Open next hint" and "Open all hints" (First Aid, Bootcamp…) are there to bind too.
- **Copy image**: right-click any image on the review screen, or press `p` to copy the image
  under the mouse. With the mouse elsewhere, each press copies the card's next image, even
  from a First Aid or Bootcamp section that's still closed.
- **Copy card text**: `g` copies the card's text with the clozes filled in, without Extra or
  the hints, ready to paste into a search.
- All of these are on the Keyboard tab under Review › AnKing & copy, and can be changed there.
- Copied images are pasted at the size they're shown on the card (at most 1200 px), not
  at full resolution.
- Fixed `c` (Reveal next) also showing the tags on AnKing cards.
- The Keyboard tab no longer lists Anki's Korean-layout duplicate keys (ㄷ, ㅕ…). They now
  follow the key they share, so your changes also work with a Korean keyboard.
- Keyboard: giving a key to one action no longer wipes the other keys of the action that had
  it (e.g. binding Return no longer unbinds Space from Show answer), and Swap no longer
  leaves that action with no key when there was nothing to swap.
- Study Day: learning cards in a Study Ahead or other filtered deck are counted on the day
  they're really due, which also fixes a false "Ahead cards are due today" right after
  building the deck. Day labels follow Anki's day cutoff (4am) instead of midnight.
- Trouble Spots: CSV exports open correctly in Excel ("›" no longer shows as "â€º"), the tab
  no longer sticks on "Reading your reviews…" after an error, and the selected topic stays
  selected after a refresh.
- Fixed the window sometimes opening blank until you scrolled.

## 1.0.0 (October 2026)

First public release.

- **Study Day**: today's reviews and new cards next to your usual range, flagged H or L.
  Study ahead, Freeze, a forecast, your pace, and a history you can undo.
- **Trouble Spots**: the topics you miss most, grouped by First Aid, Pathoma, Boards & Beyond,
  Sketchy, organ system, subdeck or any tag. Drill down to the cards, open them in the
  Browser, or export a study sheet or CSV.
- **Keyboard**: change any shortcut on the review screen, the deck overview or anywhere in
  Anki, with conflict handling and smart undo.
- **Settings**: light, dark or Auto, eleven color themes, and each tab's options.
- **About**: a quick start and links for help.
- A status bar on the Decks screen and a link in Anki's top bar.
- Replaces Study Day Control, Trouble Spots and Keybind Remapper; their settings are copied
  over once.
