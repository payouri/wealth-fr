# Product

## Register

product

## Users

The primary reader is the **informed general public**: curious citizens, students,
and the journalists or educators who serve them. They arrive wanting to understand
how wealth concentration in France has moved since 2000, not to run a statistical
office. They are comfortable with a chart and a percentage, but they are *not*
expected to know what separates WID's `adulte`/`net` figures from INSEE's
`menage`/`brut` ones. The interface must teach that distinction in passing, never
assume it.

Context of use: someone reading on a laptop or phone, following a link from an
article or a course, willing to spend a few minutes exploring if the first screen
earns their trust. The job to be done: "show me a credible picture of who owns
what, and let me see where the number comes from."

## Product Purpose

wealth-fr explores, visualizes, and compares harmonized wealth-concentration
series for France (top 10 / 1 / 0.1% shares, Gini, average wealth) drawn from three
public sources whose measurement **Conventions are deliberately not interchangeable**
(WID, INSEE, DGFiP).

Success is a reader who leaves with a defensible understanding of a trend *and* of
its caveats: which source, which convention, which millésime, and why a 2018 break
exists. The product wins by being trustworthy and legible, not by being
comprehensive or clever. It is a public-good explainer with the rigor of a
statistical instrument underneath.

## Brand Personality

**Editorial, lucid, trustworthy.** This is data journalism, not a dashboard: charts
carry annotated narrative, methodology is invited in rather than bolted on, and the
voice is authoritative but warm. Closer to a well-made explainer than to an
analytics tool. It should feel like it was made by people who care about getting the
numbers right and about helping you understand them.

Tone of copy: plain, precise French. Confident without jargon. When a caveat
matters (a convention mismatch, a series break), it is stated clearly and calmly,
never buried and never alarmist.

## Anti-references

- **Generic SaaS dashboard.** No KPI hero-metric cards, no gradient accents, no
  identical icon-heading-text card grids, no "analytics template" chrome. The data,
  not a widget shell, is the interface.
- **Crypto / fintech dark-neon.** No dark-mode-by-default, no neon-on-black, no
  glowing charts or hype aesthetic. Light, calm, and legible by default.
- **Government-portal drab.** Avoid the flat, cramped, low-contrast, Bootstrap-era
  public-administration look. Civic credibility through craft, not through dullness.
- **Flashy infographic.** No decorative or animation-heavy charts that bend the data
  for effect. Visual honesty comes first.

## Design Principles

1. **The Convention is the contract.** Two series from different conventions may be
   overlaid for comparison but never merged or read as one quantity. Every plotted
   line declares its unité and concept; the guard rail is visible, not implied.

2. **Traceability is a feature, not a footnote.** Source, millésime, and extraction
   date stay legible for every displayed figure. The reader can always answer "where
   does this number come from?" without leaving the chart.

3. **Explain the break, don't smooth it.** The 2018 ISF→IFI rupture and retroactive
   révisions are annotated and narrated, treated as teaching moments rather than
   discontinuities to hide. Honesty about the data's seams builds trust.

4. **Lead the reader, respect the data.** Editorial guidance for a non-expert
   audience, delivered through progressive disclosure: the headline trend is
   immediate, the methodology is one deliberate step away. Accessible never means
   dumbed down.

5. **Honest charts only.** Encoding serves comprehension and never distorts. No
   truncated-axis tricks, no decoration over integrity, no color-only meaning.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**: contrast ratios met for text and meaningful UI, full
keyboard operability, visible focus. Because the product is line- and color-heavy:

- **Colorblind-safe series palettes**, and **never color-only encoding**. Lines are
  distinguished by additional cues (direct labels, markers, or dash patterns), and
  the 2018 rupture and convention differences are readable without relying on hue.
- Respect `prefers-reduced-motion`: chart transitions and any motion degrade to
  instant, non-essential animation removed.
- Charts carry text alternatives (accessible names, and where feasible a tabular or
  exportable view) so the data is reachable without seeing the plot.
