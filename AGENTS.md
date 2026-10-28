# Goal 
apply election forensics methods; present results in a form easily readable by normal humans.

# Template for webpage

site/TEMPLATE.md — country-page skeleton and site conventions. Rules that
tests or reviews keep tripping on:

- hero checkmark follows the verdict: `check ✓` only when the page establishes
  no manipulation; keep `check warn !` while open findings remain
  (serbia/bulgaria/usa — `serbia.test.js` fails on `class="check">✓`).
  The paradox badge is always `check warn ⇄`; every `.check` div carries
  `aria-hidden="true"`
- landing `site/index.html`: cards sorted by election date, newest first
- English fallback text in the HTML must equal the `en:` block of the page's
  `translations.js` (tests diff them); reword both together

## analysis-tool

```bash
cd analysis-tool && uv sync
uv run ef-analyze \
  --data ../portugal-2025/data/legislativas2025_mai \
  --out ../portugal-2025/analysis \
  --title "Португалия AR 2025 (freguesias)" \
  --merge "votes:PPD/PSD.CDS-PP<-votes:PPD/PSD.CDS-PP.PPM" \
  --controls ../portugal-2025/data/legislativas2022_mai,../portugal-2025/data/legislativas2024_mai
uv run pytest
```
# code guidelines

- Use type hints at least in method definitions
- prefer
    - strenums to plain 'str'
    - dataclasses instead of plain dicts or tuples
- httpx2 for instead of requests

# Good software architecture principles

- no reverse calls: a module should not use its parent
- no parallel calls: a module should not use another one on the same level
- avoid downstream calls: a module should not use a function or a module which is at least 2 levels below it
- functions should use simple data classes in and simple data classes out.
- side effects should be encapsulated in separate modules: one can read from the database, but not directly change it
- a module should not save a history of calls to control its operations
- a module only does one thing, completely
- major decision making should be pushed to the highest possible level. Typically, the main decisions are made by the head module (at the first level). This head module serves as a succinct "summary" of the entire program.
- a lower-level module should not make decisions for higher-level modules. Therefore, a module shouldn't perform actions that directly alter the program's operation.
- errors should bubble up until the level where the control-flow decision can be made

# Parsing PDF and scanned documents

Use openrouter + [GPT-luna-latest](https://openrouter.ai/~openai/gpt-luna-latest), reasoning=off or reasoning=low if the resulting quality is not low.
The key `OPENROUTER_KEY=...` is in `.env`. Never read it, only use it in scripts.


# Commits

- split large commits into smaller logical ones
- use conventional commits
