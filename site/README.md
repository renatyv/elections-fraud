# Election Forensics website

Static HTML, CSS and JavaScript, served from this directory on Vercel. No build
step or frontend dependencies are required.

Every `index.html` keeps its report content and section order. Shared files:

- `styles.css`: layout, typography, cards, figures, tables and responsive styles.
- `language.js`: language selection, saved preference and translated figures.
- Each multilingual page's `translations.js`: its existing text and HTML by language.

To edit a report, update its HTML and translations together. `data-i18n` names a
translation key. Figures use `data-fig` for `img/<language>/<name>.png` or
`data-dfig` for `img/details/<language>/<name>.png`; `data-alt` names the translated
alt-text key. The U.S. report is English-only and uses the same stylesheet.

Translations may contain trusted, repository-authored HTML. Do not populate them
from user input. Language switching works even if browser storage is disabled.

Preview from this directory with `python3 -m http.server 8000`. Run the shared
language checks from the repository root with `node --test site/tests/language.test.js`.
Country-specific data and publishing notes remain in each report's README.
