Everything here can be changed in the Shinjer's Study Desk window (Tools > Shinjer's Study Desk…), on the
**Settings** and **Keyboard** tabs. You don't need to edit this by hand. (The Config button
opens the Settings tab.)

- `appearance.mode`: `auto` (follow Anki's night mode), `light` or `dark`.
- `appearance.theme`: `slate` (default), `frost`, `navy`, `indigo`, `sage`, `teal`, `sand`,
  `rose`, `plum`, `graphite` or `paper`.
- `window.on_top`: keep the Shinjer's Study Desk window above other windows.
- `toolbar_link`: show "Shinjer's Study Desk" in Anki's top bar.
- `keyboard`: your shortcuts.
  - `review`, `overview`, `global`: each maps an action to a key (`"j"`), a list of keys
    (`["j", "Left"]`) or `""` for no key. List only what you changed; anything left out
    keeps Anki's key. Other menu items can be used as `"menu:<name>"`, e.g.
    `"menu:actionEmptyCards"`.
  - `on_conflict`: what happens to the action that already had a key: `swap` (it takes
    the key you freed), `spare` (it takes the first free key from `spare_keys`) or
    `delete` (it loses its key).
  - `smart_undo`: `true` makes the review screen's undo flip back to the question when
    the answer is showing, and never undo past the start of the session. `false` gives
    Anki's normal undo.
  - `spare_keys`: keys handed out by `spare`, in order.
- `migrated`, `migrated_study_desk`: set after your settings have been copied from the old
  add-ons (or from Study Desk, this add-on's old name) once. Leave them alone.

Study Day and Trouble Spots settings (decks, status bar, and so on) are stored in your
collection, not here, so they follow your profile.
