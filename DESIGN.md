---
name: Concentration du patrimoine en France
description: Editorial, trustworthy data-journalism interface for exploring harmonized wealth-concentration series for France since 2000.
colors:
  paper: "oklch(0.985 0.006 85)"
  panel: "oklch(0.96 0.008 83)"
  hairline: "oklch(0.89 0.009 80)"
  ink: "oklch(0.26 0.015 72)"
  ink-muted: "oklch(0.52 0.013 74)"
  accent: "oklch(0.55 0.075 220)"
  accent-strong: "oklch(0.46 0.085 222)"
  accent-weak: "oklch(0.93 0.03 218)"
  rupture: "oklch(0.66 0.09 75)"
  series-wid: "#0072B2"
  series-insee: "#D55E00"
  series-dgfip: "#009E73"
  series-4: "#CC79A7"
  series-5: "#E69F00"
  series-6: "#56B4E9"
typography:
  display:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "2.25rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.005em"
  title:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.01em"
  data:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.4
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
rounded:
  sm: "4px"
  md: "8px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.paper}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.accent-strong}"
    textColor: "{colors.paper}"
  button-secondary:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
    typography: "{typography.label}"
  button-ghost:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.accent}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
    typography: "{typography.label}"
  filter-chip:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "6px 12px"
    typography: "{typography.label}"
  filter-chip-active:
    backgroundColor: "{colors.accent-weak}"
    textColor: "{colors.accent-strong}"
    rounded: "{rounded.md}"
    padding: "6px 12px"
    typography: "{typography.label}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
    typography: "{typography.body}"
  tab:
    textColor: "{colors.ink-muted}"
    typography: "{typography.title}"
  tab-active:
    textColor: "{colors.ink}"
    typography: "{typography.title}"
---

# Design System: Concentration du patrimoine en France

## 1. Overview

**Creative North Star: "The Reading Room"**

A calm, well-lit public reading room where anyone can come and read the record, and
trust it. The interface is the quiet room; the data is what's on the table. On a
politically charged subject, neutrality is conveyed by restraint: the chrome
recedes, the figures and their provenance carry the page. This is data journalism in
the lineage of Our World in Data, an explainer with the rigor of a statistical
instrument underneath. It is not a dashboard and it is not an op-ed.

The surface is warm paper, not screen-white. Near-neutral ink does almost all the
typographic work, and a single muted slate-teal marks what you can touch. Saturated
color is spent only where color *is* the data: the source and series lines, drawn
from the colorblind-safe Okabe-Ito set and always reinforced by direct labels and
dash patterns so meaning never rests on hue alone. Typography is editorial: Source
Serif 4 carries titles and section openings with authority and a reading cadence,
Source Sans 3 stays invisible and legible across body text, controls, and dense
data, with tabular figures everywhere numbers are compared.

This system explicitly rejects, carrying PRODUCT.md's anti-references forward: the
**generic SaaS dashboard** (KPI hero cards, gradient accents, identical card grids),
the **crypto / fintech dark-neon** look (dark-by-default, neon-on-black, glowing
charts), the **government-portal drab** (flat, cramped, low-contrast administrative
UI), and the **flashy infographic** (decoration that bends the data for effect).

**Key Characteristics:**
- Warm-paper surface (`oklch(0.985 0.006 85)`); neutral ink; chrome that recedes.
- One muted slate-teal accent (`oklch(0.55 0.075 220)`), ≤10% of any screen, for interaction only.
- Saturated color reserved for plotted data; colorblind-safe series plus non-hue cues.
- Source Serif 4 display over Source Sans 3 body; tabular figures for all data.
- Flat by default; motion is responsive feedback (150-220ms), never choreography.

## 2. Colors

Near-neutral and warm by default; saturated color is reserved for plotted data, never
for chrome. Chrome is authored in OKLCH (Tailwind v4 native); the series palette is
the canonical Okabe-Ito sRGB hex, kept exact rather than re-approximated.

### Primary
- **Slate-Teal Accent** (`oklch(0.55 0.075 220)`): the single interactive hue. Links,
  active filter, current selection, focus ring. Chosen for trust without political
  coding (deliberately not red, not partisan blue, not finance navy-gold). Rare:
  ≤10% of any screen.
- **Slate-Teal Strong** (`oklch(0.46 0.085 222)`): hover and active states of the accent.
- **Slate-Teal Wash** (`oklch(0.93 0.03 218)`): low-saturation fill for the active
  filter chip and the selected table row. Signals state without shouting.

### Neutral
- **Warm Paper** (`oklch(0.985 0.006 85)`): primary background. Warm off-white, never
  `#fff`, so the page reads as paper.
- **Panel** (`oklch(0.96 0.008 83)`): the second neutral layer for the filter bar,
  toolbars, methodology callouts, and table headers. Slightly deeper than paper.
- **Hairline** (`oklch(0.89 0.009 80)`): 1px dividers, chart gridlines, input strokes.
  Structural, never decorative.
- **Ink** (`oklch(0.26 0.015 72)`): primary text. Warm near-black, never `#000`.
- **Muted Ink** (`oklch(0.52 0.013 74)`): secondary text, captions, and the
  always-visible traceability line (source · millésime · date d'extraction).

### Data Series (categorical, not chrome)
- **Okabe-Ito categorical set**: WID `#0072B2` (blue), INSEE `#D55E00` (vermillion),
  DGFiP `#009E73` (bluish green), then `#CC79A7`, `#E69F00`, `#56B4E9` for additional
  series. One stable hue per source; always paired with a non-hue cue (direct
  end-of-line label and/or dash pattern). Okabe-Ito is colorblind-safe by design.
- **Rupture / Annotation** (`oklch(0.66 0.09 75)`, muted amber): the 2018 ISF→IFI
  break and millésime markers. Calm and explanatory, **never** alarm-red. Replaces
  the `#dc2626` currently hardcoded in the chart stub.

### Named Rules
**The Quiet Chrome Rule.** Color belongs to the data. The interface chrome stays
near-neutral; the only chromatic UI element is the slate-teal accent, and it appears
on ≤10% of any screen. If the shell competes with the chart for attention, the shell
is too loud.

**The Impartial Hue Rule.** No politically-coded color carries meaning in the UI. The
primary accent is never red or partisan blue; series colors encode source identity,
never a value judgment. Hue is information, never editorial.

## 3. Typography

**Display Font:** Source Serif 4 (with Georgia, serif)
**Body Font:** Source Sans 3 (with system-ui, sans-serif)

**Character:** An editorial pairing. Source Serif 4 carries authority and a reading
cadence for titles and section openings; Source Sans 3 stays quiet and legible for
body text, controls, and dense data. Both are open-licence siblings with strong
tabular figures, so numbers align and the system reads as a considered explainer, not
tool chrome. Scale is fixed-rem (not fluid), since users view at consistent DPI.

### Hierarchy
- **Display** (Source Serif 4, 600, 2.25rem / 36px, line-height 1.15): page and view
  titles. One per screen.
- **Headline** (Source Serif 4, 600, 1.5rem / 24px, line-height 1.25): section
  headings and chart titles.
- **Title** (Source Sans 3, 600, 1.125rem / 18px, line-height 1.3): figure headings,
  filter-group labels, table captions.
- **Body** (Source Sans 3, 400, 1rem / 16px, line-height 1.6): explanatory prose.
  Cap measure at 65-75ch.
- **Label** (Source Sans 3, 500, 0.8125rem / 13px, letter-spacing 0.01em): filter
  labels, buttons, axis ticks, the traceability line. Often in muted ink.
- **Data** (Source Sans 3, 500, 0.875rem / 14px, tabular figures): numerals in axes,
  tables, tooltips, inline figures.

### Named Rules
**The Tabular Figures Rule.** Every numeral in a data context (axes, tables,
tooltips, inline figures) uses tabular figures (`font-feature-settings: "tnum" 1`) so
columns align and values don't jitter as they update. Proportional figures are for
prose only.

## 4. Elevation

Flat by default. Depth comes from the warm-paper / panel / ink tonal relationship and
from 1px hairlines, not from shadows. This keeps the surface paper-like and avoids the
floating-card SaaS look. A single soft shadow exists only for transient overlays
(open dropdown, tooltip), never on resting surfaces.

### Shadow Vocabulary
- **Overlay** (`box-shadow: 0 8px 24px oklch(0.26 0.015 72 / 0.12)`): dropdowns,
  popovers, the chart tooltip. The only shadow in the system.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest. Shadow appears only as a
transient response to state. If a resting element needs a shadow to be understood,
fix the layout before reaching for elevation.

## 5. Components

Synthesized from the tokens (no component library is built yet). Every interactive
component must ship its full state set: default, hover, focus-visible, active,
disabled, and where relevant loading, selected, and error.

**Sourcing: reach for shadcn/ui first.** Prefer installing a **shadcn/ui** primitive
(button, select, tabs, dialog, tooltip, table, etc.) and restyling it to the tokens
below before hand-rolling a custom one. shadcn fits the stack (React 19 + Tailwind v4
+ Radix) and gives accessible, state-complete primitives for free, which serves the
WCAG AA goal. Hand-roll a custom primitive only when no shadcn equivalent exists or
when restyling one would be more work than building from scratch (the chart surface,
the Convention legend, the traceability line are custom by nature). The specs in this
section are the **target appearance** a borrowed primitive must be tuned to, not a
mandate to build from zero.

### Named Rules
**The Borrowed Primitive Rule.** Borrow the behavior, own the look. Install the
shadcn/ui primitive for accessibility and state coverage, then bend it to these
tokens (warm paper, slate-teal accent, 8px radius, no pills, tabs as an underline not
a box). Never ship a shadcn component in its default New-York/Slate skin; an unstyled
default reads as "AI made that" and breaks The Quiet Chrome Rule.

### Buttons
- **Shape:** gently squared (8px radius, `{rounded.md}`); padding `10px 18px`; Label type.
- **Primary:** slate-teal accent fill, paper text. Hover deepens to Slate-Teal Strong.
  For primary *actions* only (export, apply), not decoration.
- **Secondary:** panel fill, ink text, hairline border. The default for most actions.
- **Ghost:** transparent on paper, accent text; for low-emphasis inline actions.
- **Focus:** 2px slate-teal outline at 2px offset (never a glow). Same ring on all controls.

### Chips (filters)
- **Style:** panel fill, ink text, 8px radius (not pill, pills read SaaS-y). Label type.
- **Active:** Slate-Teal Wash fill, Slate-Teal Strong text. Used for the Convention
  filters (unité / concept) and source toggles, which are first-level and never hidden.

### Inputs / Fields
- **Style:** paper fill, 1px hairline stroke, 8px radius, Body type.
- **Focus:** border shifts to slate-teal plus the 2px accent ring. No glow.
- **Disabled:** panel fill, muted-ink text. **Error:** rupture-amber border + helper text.

### Navigation (tabs)
- **Style:** text tabs (Tableau de bord · Comparaison · Sources & méthodologie), Title
  type. Inactive in muted ink; active in ink with a 2px slate-teal underline. No pills,
  no boxed tabs.

### Chart (signature surface)
- **Lines:** one Okabe-Ito hue per series, 2px stroke, with a direct end-of-line label
  carrying the source and its Convention (unité / concept). Conventions differ →
  dash pattern differs, so overlays never read as merged.
- **Rupture marker:** muted-amber dashed vertical reference line at 2018 with a small
  label ("ISF→IFI"), calm not alarming.
- **Axes / grid:** hairline grid, muted-ink ticks in tabular Data type, honest
  origin (no truncated y-axis on share/Gini charts).
- **Traceability:** every figure carries source · millésime · date d'extraction in
  muted-ink Label type, always visible, never a hover-only afterthought.

## 6. Do's and Don'ts

### Do:
- **Do** keep chrome near-neutral and spend saturated color only on plotted data (The Quiet Chrome Rule).
- **Do** label every plotted line with its Convention (unité/concept) and reinforce series with non-hue cues (direct labels, dash patterns), so meaning survives colorblindness and grayscale.
- **Do** keep `source`, `millesime_source`, and `date_extraction` visible for every displayed figure. Traceability is a feature, not a footnote.
- **Do** annotate the 2018 ISF→IFI rupture and millésime révisions calmly with the muted-amber marker. Explain the break; don't smooth it.
- **Do** use tabular figures for all numeric data, fixed-rem type sizes, and a body measure capped at 65-75ch.
- **Do** keep surfaces flat and warm; tint every neutral and never use `#000` or `#fff`.

### Don't:
- **Don't** build a **generic SaaS dashboard**: no KPI hero-metric cards, no gradient accents, no identical icon-heading-text card grids, no analytics-template chrome.
- **Don't** go **crypto / fintech dark-neon**: no dark-mode-by-default, no neon-on-black, no glowing charts.
- **Don't** settle for **government-portal drab**: no flat, cramped, low-contrast administrative look. Civic credibility comes from craft, not dullness.
- **Don't** make a **flashy infographic**: no decorative or animation-heavy charts that bend the data for effect.
- **Don't** make a red or partisan-blue color carry meaning in the UI, and **don't** use alarm-red (`#dc2626`) for the 2018 rupture; it's a methodological seam, not a warning (The Impartial Hue Rule).
- **Don't** encode anything by color alone, and **don't** merge series from different Conventions into one quantity. Overlay with explicit labels only.
