---
name: Study Desk
description: A clinical lab report about your own studying, inside Anki.
colors:
  institutional-teal: "#0b5d57"
  institutional-teal-hover: "#08504b"
  teal-rail-hover: "#13706a"
  rail-muted-ink: "#c3e6df"
  teal-text: "#0b5d57"
  range-band: "rgba(11, 93, 87, .13)"
  range-band-strong: "rgba(11, 93, 87, .30)"
  selection-teal: "#bfe3dc"
  selection-ink: "#0b2522"
  row-selected: "#e6f1ef"
  report-ground: "#f4f6f6"
  result-sheet: "#ffffff"
  chart-ink: "#15201f"
  chart-ink-secondary: "#4b5957"
  chart-ink-muted: "#586563"
  hairline: "#e4e9e8"
  hairline-strong: "#cad2d1"
  row-hover: "#eff3f2"
  flag-high-red: "#c4122f"
  flag-low-blue: "#1d5fbf"
  crit-wash: "#fbe9ec"
  crit-line: "#efc2ca"
  cap-green: "#2e9e5b"
  cap-lavender: "#8b6fc7"
  cap-grey: "#8a9396"
  dark-shell: "#083f3b"
  dark-accent: "#3fa79b"
  dark-accent-ink: "#04201d"
  dark-accent-text: "#7fd6ca"
  dark-ground: "#0f1515"
  dark-sheet: "#161e1e"
  dark-ink: "#e3ecea"
  dark-ink-secondary: "#aebebb"
  dark-ink-muted: "#8d9e9b"
  dark-hairline: "#222d2d"
  dark-hairline-strong: "#344443"
  dark-flag-high: "#ff5a6e"
  dark-flag-low: "#6aa5ff"
  dark-crit-wash: "#2a1a1e"
  navy-shell: "#1d3f72"
  navy-dark-accent: "#4d7fc6"
  plum-shell: "#6a2c5f"
  plum-dark-accent: "#b0609f"
  graphite-shell: "#2f3539"
  graphite-dark-accent: "#8e9aa0"
typography:
  headline:
    fontFamily: "Segoe UI, system-ui, -apple-system, Cantarell, DejaVu Sans, sans-serif"
    fontSize: "21px"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Segoe UI, system-ui, -apple-system, Cantarell, DejaVu Sans, sans-serif"
    fontSize: "14.5px"
    fontWeight: 650
    lineHeight: 1.35
  body:
    fontFamily: "Segoe UI, system-ui, -apple-system, Cantarell, DejaVu Sans, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  label:
    fontFamily: "Segoe UI, system-ui, -apple-system, Cantarell, DejaVu Sans, sans-serif"
    fontSize: "11.5px"
    fontWeight: 600
    lineHeight: 1.2
  result:
    fontFamily: "Source Code Pro, DejaVu Sans Mono, ui-monospace, monospace"
    fontSize: "13.5px"
    fontWeight: 600
    fontFeature: "tnum"
  flag:
    fontFamily: "Segoe UI, system-ui, -apple-system, Cantarell, DejaVu Sans, sans-serif"
    fontSize: "12px"
    fontWeight: 800
    letterSpacing: "0.02em"
rounded:
  xs: "3px"
  sm: "4px"
  md: "6px"
  lg: "8px"
  pill: "10px"
spacing:
  xs: "8px"
  sm: "14px"
  md: "24px"
  lg: "32px"
  xl: "40px"
components:
  button:
    backgroundColor: "{colors.result-sheet}"
    textColor: "{colors.chart-ink}"
    rounded: "{rounded.sm}"
    height: "30px"
    padding: "0 12px"
  button-hover:
    backgroundColor: "{colors.row-hover}"
  button-primary:
    backgroundColor: "{colors.institutional-teal}"
    textColor: "{colors.result-sheet}"
    rounded: "{rounded.sm}"
    height: "30px"
    padding: "0 12px"
  button-primary-hover:
    backgroundColor: "{colors.institutional-teal-hover}"
  button-quiet:
    textColor: "{colors.chart-ink-secondary}"
    rounded: "{rounded.sm}"
    height: "30px"
  segmented:
    backgroundColor: "{colors.hairline}"
    rounded: "{rounded.md}"
    padding: "2px"
  segmented-selected:
    backgroundColor: "{colors.institutional-teal}"
    textColor: "{colors.result-sheet}"
    rounded: "{rounded.xs}"
    height: "24px"
  select:
    backgroundColor: "{colors.result-sheet}"
    textColor: "{colors.chart-ink}"
    rounded: "{rounded.sm}"
    height: "30px"
    padding: "0 28px 0 10px"
  switch:
    backgroundColor: "{colors.hairline}"
    rounded: "{rounded.pill}"
    width: "34px"
    height: "20px"
  switch-on:
    backgroundColor: "{colors.institutional-teal}"
  rail-tab:
    textColor: "{colors.rail-muted-ink}"
    typography: "{typography.label}"
    padding: "12px 6px 10px"
  rail-tab-active:
    backgroundColor: "{colors.report-ground}"
    textColor: "{colors.teal-text}"
  settings-card:
    backgroundColor: "{colors.result-sheet}"
    rounded: "{rounded.md}"
    padding: "0 20px"
  kbd:
    backgroundColor: "{colors.result-sheet}"
    textColor: "{colors.chart-ink}"
    rounded: "{rounded.sm}"
    height: "22px"
    padding: "0 6px"
  crit-panel:
    backgroundColor: "{colors.crit-wash}"
    textColor: "{colors.chart-ink}"
    padding: "14px 16px 16px"
---

# Design System: Study Desk

<!-- Captured from study_desk/web/css/tokens.css and base.css on 2026-10-26.
     tokens.css is the source of truth; if they disagree, update this file. -->

## Overview

**Creative North Star: "The Lab Report"**

Study Desk reads like a hospital lab-results printout about your own studying. A colored
institutional shell (the rail) frames a pale results ground. Every number sits in a
Measure / Result / Units / Your range layout, beside a reference-range bar drawn from *your
own* history, and gets an **H** or **L** flag only when it falls outside that range. A
classmate should see at a glance what is normal today and what isn't, the same way a
clinician scans a panel for flagged values.

The system is dense, flat and quiet. It is a working tool beside Anki, opened daily and often
in dark mode, so it uses system fonts, a 13px base, tabular numerals everywhere, hairline
table rules and almost no decoration. Color is reserved for meaning: the theme color marks
where you are and what you can press; red and blue mean high and low; tube-cap colors label
chart series. Everything else is ink on paper.

**Key Characteristics:**
- Results tables with hairline rules, right-aligned monospaced results and a range bar per row.
- H / L / CRIT flags as bold text, never icons.
- One theme color (Teal, Navy, Plum or Graphite) for the rail and primary actions only.
- Light and dark are designed separately, not inverted.
- No network: system fonts, inline SVG icons, no images.

## Colors

Clinical neutrals with one institutional theme color, plus fixed clinical signal colors that
never change with the theme.

Every component uses CSS custom properties from `tokens.css` and never a literal color. The
`<html>` element carries `data-theme="teal|navy|plum|graphite"` and `data-dark="1"` when
dark. Dark is on when mode is "dark", or when mode is "auto" and Anki is in night mode.

### Primary
- **Institutional Teal** (`--shell`, `--accent`): the rail background, primary buttons,
  the selected segment and switch, and the focus ring. In dark mode the shell deepens
  (dark-shell) and the accent lightens (dark-accent) so filled controls stay visible on a
  dark sheet; `--accent-text` (teal-text, dark-accent-text) is the readable version for
  links and the active rail tab's label.
- **Range Band** (`--band`, `--band-strong`): a translucent wash of the theme color for the
  "your range" band inside range bars and chart backgrounds.

### Themes
Each theme overrides only the shell/accent family (`--shell*`, `--accent*`, `--band*`,
`--focus`, `--sel-*`, `--row-sel`) for light and dark: **Teal** (default), **Navy**
(navy-shell, navy-dark-accent), **Plum** (plum-shell, plum-dark-accent) and **Graphite**
(graphite-shell, graphite-dark-accent). The full per-theme tables are in
`.impeccable/design.json` under `extensions.themes`. Neutrals and flags are shared by all
themes.

### Signal (clinical flags)
- **Flag High Red** (`--flag-h`, alias `--hi`): H flags, an out-of-range-high result, the
  marker on a high range bar, error icons, a key that is already taken.
- **Flag Low Blue** (`--flag-l`, alias `--lo`): L flags and low results.
- **Crit Wash / Crit Line** (`--crit-bg`, `--crit-line`): the pale red panel behind a
  keyboard conflict ("CRIT") and the pending key chip.

### Series (tube caps)
Chart and legend colors borrowed from blood-tube caps: **Cap Green** (`--cap-green`: done,
in the Ahead deck, progress), **Cap Lavender** (`--cap-lav`: due / can be studied ahead),
**Cap Grey** (`--cap-grey`: default legend swatch). `--cap-gold`, `--cap-lblue` and
`--cap-text` are defined but not used yet; use them before inventing new series colors.

### Neutral
- **Report Ground** (`--ground`): the content area behind everything.
- **Result Sheet** (`--sheet`): raised surfaces: buttons, inputs, settings cards, key chips.
- **Chart Ink** (`--ink`), **Secondary Ink** (`--ink-2`: ledes, quiet buttons), **Muted Ink**
  (`--ink-3`: table headers, units, hints, meta).
- **Hairline** (`--rule`: row dividers, segmented-control track), **Strong Hairline**
  (`--rule-2`: control borders, header underline, scrollbar thumb).
- **Row Hover** (`--hover`) and **Row Selected** (`--row-sel`).
- `--page` is defined but unused.

### Named Rules
**The Flags Mean Something Rule.** Red and blue appear only for out-of-range values, errors
and conflicts. A normal value is plain ink, never green.

**The Tokens Only Rule.** Components never contain a literal color; add or reuse a token in
`tokens.css`, and give it a dark value and (if it is a theme color) a value in every theme.

**The Theme Stays in the Frame Rule.** The theme color is for the rail, primary actions,
selection and focus. It never tints the results themselves.

## Typography

**Body Font:** system UI (`--ui`: Segoe UI, system-ui, -apple-system, Cantarell, DejaVu Sans)
**Result Font:** monospace (`--mono`: Source Code Pro, DejaVu Sans Mono, ui-monospace)

**Character:** the plain system face of a lab information system, with a monospace face for
the numbers you read down a column. Nothing is bundled or fetched.

### Hierarchy
- **Headline** (650, 21px, 1.25): the tab's one headline, e.g. today's state.
- **Title** (650, 14.5px, 1.35): section headings; `h3` is 650 at 13px.
- **Body** (400, 13px, 1.5): everything else. Ledes in Secondary Ink, max about 62ch.
- **Label** (600, 11.5px): rail tab labels, table headers, legends, small buttons. Sentence
  case, no letter-spaced capitals except flags.
- **Result** (600, 13.5px, mono): the result column; other numbers use `.num` (mono) or
  tabular numerals in the UI font.
- **Flag** (800, 12px, +0.02em): H and L. CRIT is 800 at 11px with +0.06em.

### Named Rules
**The Tabular Rule.** All numerals are tabular (`font-variant-numeric: tabular-nums` is on
`body`), so columns line up.

## Layout

A fixed rail on the left (96px) and a scrolling content area. The rail holds the tabs at the
top, and the light/dark toggle and Settings pinned at the bottom. The content area has
rounded left corners where it meets the rail, so the rail reads as the frame of the sheet.
Tab panels are padded 24px top, 32px sides, 40px bottom.

Tabs that need a side column use a two-column grid: main column plus a 300px side column with
a 40px gap (48px on Study Day). Below 900px the side column drops under the main one. The
window's minimum size is 640 x 480 and every tab must work at 640px wide.

Spacing is informal but repeats 8, 14, 24, 32 and 40px. Table rows are 30px tall (34px on
the Study Day results table); controls are 30px, small 26px, extra-small 22px.

## Elevation & Depth

Flat. Depth comes from tone: the colored rail, the pale ground and white sheet surfaces.
One soft shadow exists for raised cards.

### Shadow Vocabulary
- **Sheet** (`--shadow`: `0 1px 2px rgba(16,40,38,.05), 0 4px 14px rgba(16,40,38,.05)`;
  darker in dark mode): settings cards and `.sheet` surfaces.
- **Window** (`--win-shadow`): defined for floating windows, unused today.

### Named Rules
**The One Shadow Rule.** Only the Sheet shadow is used, and only on cards. Tables, buttons and
panels are flat with hairlines.

## Shapes

Small, square-ish corners: 3px (segment buttons), 4px (buttons, inputs, key chips, choice
cards), 5-6px (segmented track, cards), 7-8px (rail tabs and the content area's left edge),
10px only for the switch. Lines are 1px hairlines; the only thick line is a key chip's 2px
bottom edge. Range bars are a 1px track, a 6px band and a 2px marker (3px and colored when
flagged).

## Components

### Buttons
- **Shape:** gently squared (4px), 30px tall, 600 weight at 12.5px.
- **Default:** Result Sheet with a Strong Hairline border; hover goes to Row Hover with a Muted
  Ink border.
- **Primary:** filled theme accent with accent ink; hover uses `--accent-hover`. One primary
  per area.
- **Quiet:** transparent, Secondary Ink, Row Hover on hover.
- **Link button:** accent text, underlined (1px, thicker on hover).
- Sizes `.sm` (26px) and `.xs` (22px). Disabled is 50% opacity.

### Segmented control
A Hairline track (5px radius, 2px padding) with 24px buttons; the selected one is filled
with the accent. Used for Mode, Theme and view switches.

### Inputs
Select and number fields share the button frame: 30px, 4px radius, Strong Hairline border,
Muted Ink border on hover. Number fields are right-aligned with tabular numerals and no spin
buttons.

### Switch
34 x 20px, Hairline track; on, it fills with the accent and the knob turns accent ink.
The knob slides with `cubic-bezier(.16, 1, .3, 1)` over 0.18s.

### Navigation (rail)
Icon over label, Rail Muted Ink on the theme shell. Hover uses `--shell-hover`. The active tab
takes the ground color with accent text and joins the content area (rounded on the left
only), like a tab on a folder. Up/Down arrows move between tabs.

### Results table (signature)
Columns Measure / Result / Units / Your range / Flag. Hairline row dividers, a Muted Ink 11.5px
header over a Strong Hairline. Results are right-aligned, mono, 600; flagged rows color the
result red or blue and show H or L at the end. **Range bar** (`desk.rangeBar`): 74px wide,
the theme band for your range, an ink marker for today's value that turns red or blue when
outside.

### Conflict panel
On the Keyboard tab, a taken key opens a Crit Wash panel with a red "CRIT" label, the key
chip and choice cards (swap / spare key / unbind); the chosen card gets an accent border.

### Key chip
`kbd`: Result Sheet, Strong Hairline border with a 2px bottom edge, mono 600 at 11.5px.

### States
Loading is a small spinner in Muted Ink with the accent on top; errors show the red alert icon,
a title and the message in mono; empty states are left-aligned text up to 52ch. With reduced
motion, transitions and animation are switched off.

## Do's and Don'ts

### Do:
- **Do** put every number next to a range when there is one, and flag only what is outside it.
- **Do** use tokens from `tokens.css` only, and check new colors in all four themes, light
  and dark, at 4.5:1 contrast for text.
- **Do** use tabular numerals and right-align numeric columns.
- **Do** theme focus rings (`--focus`, 2px, 2px offset), selection and scrollbars.
- **Do** draw icons as inline SVG from `web/js/icons.js`.

### Don't:
- **Don't** use icons, emoji or symbol glyphs as flags; flags are the letters H, L and CRIT.
- **Don't** color normal values green or tint results with the theme color.
- **Don't** load fonts, images or scripts from the network.
- **Don't** add shadows to tables, buttons or panels, or nest cards inside cards.
- **Don't** use colored left borders, gradient text, glass blur or eyebrow labels above
  headings.
