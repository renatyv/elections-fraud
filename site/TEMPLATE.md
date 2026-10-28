# Country-page template

Common skeleton of all nine country reports: a Minto-pyramid single-page report — verdict
first in a hero, then situation, numbered findings, deep-dive sections,
a collapsible test-by-test methods list, limitations, data provenance.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset/viewport>
  <title>{Country}, {election} — {date}: statistical fraud check</title>
  <meta name="description" + og:title/og:description/og:type=article>   <!-- same text -->
  <link rel="icon" href="data:image/svg+xml,...">                       <!-- inline SVG checkmark, country color -->
  <link rel="stylesheet" href="../styles.css">                          <!-- shared one level up -->
  <script defer src="/_vercel/insights/script.js"></script>
  <!-- multilingual pages only: -->
  <script defer src="translations.js"></script>
  <script defer src="../language.js"></script>
</head>
<body class="page-{country}-{year}">
  <header class="top"><div class="bar">
    <div class="brand">flag + "Country · Election · date"</div>
    <div class="right"> "← All analyses" (href="../")
      [multilingual: <nav class="langs"><button data-lang=...>] </div>
  </div></header>
  <main>
    1. HERO (Minto: ANSWER)  .hero > .hero-inner
       .kicker  "Independent statistical audit"
       h1       "The {election} of {date} — do the numbers add up?"
       .verdict     .check ✓ (clean) / .check warn ! (open findings),
                    aria-hidden="true" + h2 one-line fraud verdict
       .verdict.flip .check warn ⇄ (aria-hidden="true") + .flip-head +
                    1–2 .v-line (paradox / second finding)
       nav.jump     plain section links, below both verdicts
    2. SITUATION  <section> what was decided + turnout
       .res-card (or .cards2 grid): result bars — .p-row > .p-name + .p-track > .p-fill (width:%) + .p-pct
    3. KEY FINDINGS  .args > .arg ×3  (.num 1–3 + h4 + p)
    4. DEEP-DIVE  <section id="paradoxes"> (anchored from header)
       .px-sub subsections: intro p + .figs > figure.fig (img + figcaption) + table.splits + .note
    5. METHODS  <section> "Manipulation detection test results" > .m-list
       <details class="m"> per test family:
         summary: .badge.pass ✓ / .badge.warn ! or ≠ / .badge.neutral i + .m-head (h5 title + one-line p)
         .m-details: p (numbers + caveats) + .m-figs > figure(.fig, some .wide)
       canonical test order: Shpilkin tail · comet tail · Klimek fingerprints ·
         Kobak integer peaks · Benford 2nd digit · last digit · outliers+ML ·
         [control vs previous election] · self-test (synthetic fraud injection)
    6. LIMITATIONS  <section> scope caveats ("cannot conclude…" / .data ul)
    7. DATA  <section> .data ul: official source portal · cross-checks · toolkit · repo/links
  </main>
  <footer>Renat Iuldashev · renatyv.org · Data: {SOURCE} · Page generated {date}</footer>
</body>
```

## Conventions
- **Checkmark follows the verdict:** use `check ✓` (not `check warn !`) only
  when the page establishes no manipulation (portugal, india, slovakia,
  sloveniya, brazil); keep `check warn !` while open findings remain
  (serbia, bulgaria, usa — `serbia.test.js` fails on `class="check">✓`).
  The paradox badge is always `check warn ⇄`. Check glyphs are decorative:
  every `.check` div carries `aria-hidden="true"`.
  Method badges use the same fixed 28 × 28 px circle on every page:
  `badge pass` + `✓` (green, a check explicitly passed), `badge warn` + `!`
  (amber, an unresolved flag), `badge warn` + `≠` (amber, a rejected reference
  distribution), `badge neutral` + `i` (gray, context, descriptive evidence or
  an inconclusive check). Do not use dots or give neutral findings a green
  background. A rejected distribution is not proof of manipulation. Do not
  change status to make pages look alike: use the finding's actual meaning.
  Every `.badge` also carries `aria-hidden="true"`; adjacent text explains
  the result without relying on a glyph or color.
- **English fallback = `I18N.en`:** rewording means editing the HTML text and
  the `en:` block of `translations.js` together — tests diff them (bulgaria,
  serbia, slovakia); the landing page has no such test.
- **Landing order:** `site/index.html` cards sorted by election date,
  newest first.
- **Minto order fixed:** headline verdict → context → evidence; everything
  below the hero collapses in `<details class="m">`.
- **Measured voice:** first-person, every claim quantified and caveated;
  verdicts worded as "tests do not establish / needs a closer look", never
  "proven".
- **i18n (multilingual pages, absent on `usa-2024`):** `data-i18n` on text,
  `data-fig`/`data-dfig` + `data-alt` on images; figures live in
  `img/{lang}/` (section-level) and `img/details/{lang}/` (in-details).
- **Figures:** always `figure.fig > img loading="lazy" + figcaption`; `.wide`
  variants for hero charts; tables use `table.splits` or
  `table.data-table` inside `.table-wrap`.
- **One visual system:** use only `../styles.css`; no page-local `<style>`,
  stylesheet copies, or country-specific component overrides. Country selectors
  may define flags, data-dependent chart/table widths or spacing inside a
  report, but must not change status colors, badge shapes or hero typography.
  Keep layout and component changes in the shared stylesheet.
- **Header:** `.brand` uses `span.flag[aria-hidden="true"]` plus country,
  election and date; `.right` contains the home link and language buttons only.
  Put section anchors in `nav.jump` below both verdicts, never in header pills.
- **Hero:** kicker, h1, main verdict, second finding, then section navigation.
  Do not add metric chips, tags, extra status pills or a third verdict card.
  Put snapshot dates, coverage and sample sizes in context or data sections;
  `ul.context-facts > li[data-i18n]` is available for compact provenance facts.
- **Details:** every `details.m > summary` starts with one decorative status
  badge, followed by `.m-head`; use a neutral `i` for context/download sections.
  The shared CSS supplies the expand chevron. Method titles use `h5` (`h3` is
  supported for the English-only U.S. report), with identical visual styling.
- **Verification:** run `node --test site/tests/*.test.js` and
  `python3 -m unittest discover -s site/tests -p 'test_*.py'`. The shared
  report-style test checks every country directory, including newly added ones.
  Preview the affected pages on desktop and mobile and check long headings,
  warning/neutral/pass badges, navigation and expanded details.
