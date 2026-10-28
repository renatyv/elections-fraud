const assert = require('node:assert/strict');
const { readdirSync, readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');

const site = path.resolve(__dirname, '..');
const openFindings = new Set(['serbia-oct-2026', 'bulgaria-oct-2026', 'usa-2024']);

for (const directory of readdirSync(site, { withFileTypes: true })) {
  const file = path.join(site, directory.name, 'index.html');
  if (!directory.isDirectory() || !existsSync(file)) continue;
  const html = readFileSync(file, 'utf8');

  test(`${directory.name}: shared report appearance and meaningful status icons`, () => {
    assert.deepEqual([...html.matchAll(/<link\b[^>]*rel="stylesheet"[^>]*>/g)].map(m => m[0]),
      ['<link rel="stylesheet" href="../styles.css">']);
    assert.doesNotMatch(html, /<style\b|class="chips?"/);
    const header = html.match(/<header\b[\s\S]*?<\/header>/)[0];
    assert.doesNotMatch(header, /href="#/);
    assert.match(header, /class="flag" aria-hidden="true"/);
    assert.match(html, /<nav class="jump" aria-label="Sections">/);

    const checks = [...html.matchAll(/<div class="(check(?: warn)?)"([^>]*)>\s*([^<]+?)\s*<\/div>/g)];
    assert.equal(checks.length, 2);
    for (const check of checks) assert.match(check[2], /aria-hidden="true"/);
    assert.equal(checks[0][1], openFindings.has(directory.name) ? 'check warn' : 'check');
    assert.equal(checks[0][3], openFindings.has(directory.name) ? '!' : '✓');
    assert.equal(checks[1][1], 'check warn');
    assert.equal(checks[1][3], '⇄');

    for (const summary of html.matchAll(/<summary>([\s\S]*?)<\/summary>/g)) {
      const badge = summary[1].match(/^\s*<span class="badge (pass|warn|neutral)" aria-hidden="true">([^<]+)<\/span>/);
      assert.ok(badge, summary[1].slice(0, 100));
      assert.ok({ pass: ['✓'], warn: ['!', '≠'], neutral: ['i'] }[badge[1]].includes(badge[2]));
    }
  });
}
