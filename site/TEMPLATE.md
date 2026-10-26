# Country-page template

Common skeleton of the country pages (`portugal-2025`, `usa-2024`,
`brazil-oct-2026-round-1`): a Minto-pyramid single-page report — verdict
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
    <div class="right"> "← All analyses" (href="../") + anchor links ↓
      [multilingual: <nav class="langs"><button data-lang=...>] </div>
  </div></header>
  <main>
    1. HERO (Minto: ANSWER)  .hero > .hero-inner
       .kicker  "Independent statistical audit"
       h1       "The {election} of {date} — do the numbers add up?"
       .verdict     icon (✓ or ! warn) + h2 one-line fraud verdict
       .verdict.flip icon (⇄) + .flip-head + 1–2 .v-line (paradox / second finding)
    2. SITUATION  <section> what was decided + turnout
       .res-card (or .cards2 grid): result bars — .p-row > .p-name + .p-track > .p-fill (width:%) + .p-pct
    3. KEY FINDINGS  .args > .arg ×3  (.num 1–3 + h4 + p)
    4. DEEP-DIVE  <section id="paradoxes"> (anchored from header)
       .px-sub subsections: intro p + .figs > figure.fig (img + figcaption) + table.splits + .note
    5. METHODS  <section> "Manipulation detection test results" > .m-list
       <details class="m"> per test family:
         summary: .badge (✓ pass / ! warn / • neutral / ≠ rejects) + .m-head (h5 title + one-line p)
         .m-details: p (numbers + caveats) + .m-figs > figure(.fig, some .wide)
       canonical test order: Shpilkin tail · comet tail · Klimek fingerprints ·
         Kobak integer peaks · Benford 2nd digit · last digit · outliers+ML ·
         [control vs previous election] · self-test (synthetic fraud injection)
    6. LIMITATIONS  <section> scope caveats ("cannot conclude…" / .data ul)
    7. DATA  <section> .data ul: official source portal · cross-checks · toolkit · repo/links
  </main>
  <footer>Independent analysis · renatyv.org · Data: {SOURCE} · Page generated {date}</footer>
</body>
```

## Conventions

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
- **Minor divergences:** `usa-2024` uses an emoji brand, `h3` in `.m-head`,
  a cache-busted CSS query and no translations; PT/BR pages use
  `span.flag`, `h5` in `.m-head` and the language switcher.
