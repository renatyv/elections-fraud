const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../serbia-oct-2026');
const html = readFileSync(path.join(root, 'index.html'), 'utf8');
const context = vm.createContext({});
vm.runInContext(readFileSync(path.join(root, 'translations.js'), 'utf8'), context);
const translations = vm.runInContext('I18N', context);

test('Serbia: English fallback and complete Serbian translations', () => {
  for (const match of html.matchAll(/<([\w]+)\b[^>]*data-i18n="([^"]+)"[^>]*>([\s\S]*?)<\/\1>/g)) {
    assert.equal(match[3].trim(), translations.en[match[2]], match[2]);
  }
  assert.deepEqual(Object.keys(translations.sr).sort(), Object.keys(translations.en).sort());
  for (const match of html.matchAll(/data-i18n="([^"]+)"/g)) {
    assert.equal(typeof translations.sr[match[1]], 'string', match[1]);
    assert.ok(translations.sr[match[1]].length > 0, match[1]);
  }
});

test('Serbia: local assets, translated downloads and anchors resolve', () => {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(ids.length, new Set(ids).size);
  for (const content of [html, ...Object.values(translations.sr)]) {
    for (const match of content.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
      const url = new URL(match[1], 'https://preview.invalid/serbia-oct-2026/');
      if (url.origin !== 'https://preview.invalid' || url.pathname.startsWith('/_vercel/')) continue;
      assert.ok(existsSync(path.resolve(root, '..', `.${url.pathname}`)), match[1]);
      if (url.hash) assert.ok(ids.includes(url.hash.slice(1)), match[1]);
    }
  }
  for (const image of html.matchAll(/<img\b([^>]+)>/g)) {
    assert.match(image[1], /loading="lazy"/);
    assert.match(image[1], /alt="[^"]+"/);
  }
});

test('Serbia: published snapshot and projected mandates agree with bundled evidence', () => {
  const metrics = JSON.parse(readFileSync(path.join(root, 'downloads/metrics.json')));
  const diagnostics = JSON.parse(readFileSync(path.join(root, 'downloads/diagnostics.json')));
  assert.equal(metrics.snapshots, 14);
  assert.equal(metrics.last_source_ts, '26.10.2026 21:15:00');
  assert.equal(metrics.shares_final['3'], 52.71);
  assert.equal(metrics.shares_final['1'], 39.17);
  assert.equal(diagnostics.cast_minus_valid_minus_invalid_2026, 2650);
  assert.equal(diagnostics.stations_2023_all, 8273);
  const csv = readFileSync(path.join(root, 'downloads/seats.csv'), 'utf8').trim().split('\n');
  const header = csv[0].split(',');
  const seatColumn = header.indexOf('seats_dhondt');
  const rows = csv.slice(1).map(line => line.split(','));
  const students = rows.find(row => row[0] === '3');
  const incumbent = rows.find(row => row[0] === '1');
  assert.equal(Number(students[seatColumn]), 140);
  assert.equal(Number(incumbent[seatColumn]), 104);
  assert.equal(rows.reduce((sum, row) => sum + Number(row[seatColumn]), 0), 250);
  assert.match(translations.en.result_note, /16:55 CET/);
  assert.match(translations.sr.result_note, /16:55 CET/);
  assert.match(translations.en.limit2, /2,650/);
  assert.match(translations.sr.limit2, /2\.650/);
});

test('Serbia: discoverable from the homepage and sitemap in every existing homepage language', () => {
  const home = readFileSync(path.join(root, '../index.html'), 'utf8');
  assert.match(home, /href="serbia-oct-2026\/index.html"/);
  const homeContext = vm.createContext({});
  vm.runInContext(readFileSync(path.join(root, '../translations.js'), 'utf8'), homeContext);
  const homeTranslations = vm.runInContext('I18N', homeContext);
  for (const translation of Object.values(homeTranslations)) {
    assert.equal(typeof translation.rs_title, 'string');
    assert.equal(typeof translation.rs_desc, 'string');
  }
  assert.match(readFileSync(path.join(root, '../sitemap.xml'), 'utf8'), /https:\/\/www\.renatyv\.org\/serbia-oct-2026\//);
});


test('Serbia: year/list comparisons and model assumptions agree with the archived metrics', () => {
  const current = JSON.parse(readFileSync(path.join(root, 'downloads/screening_2026.json')));
  const previous = JSON.parse(readFileSync(path.join(root, 'downloads/reference_2023.json')));
  const diagnostics = JSON.parse(readFileSync(path.join(root, 'downloads/diagnostics.json')));
  assert.equal(current.n_units, 8124);
  assert.equal(previous.n_units, 8163);
  assert.equal(current.fingerprint.party, 'Students');
  assert.equal(previous.fingerprint.party, 'Vučić');
  assert.ok(current.fingerprint.mean_anom[1] > current.fingerprint.mean_main[1]);
  assert.ok(previous.fingerprint.mean_anom[1] < previous.fingerprint.mean_main[1]);
  assert.equal(diagnostics.incumbent_fingerprint.separated, false);
  assert.equal(current.benford2.length, 3);
  assert.equal(current.last_digit.find(row => row.party === 'Dacić (SPS)').n_numbers, 33);
  assert.equal(current.selftest.injected_added_ballots_party, 87179);
  assert.equal(current.selftest.peaks_z_rounded.toFixed(2), '3.23');
  assert.doesNotMatch(html, /class="badge(?: pass)?"[^>]*>\s*✓|class="check"[^>]*>\s*✓/);
  assert.match(translations.en.m3_p, /two overlapping Gaussian components specified in advance/);
  assert.match(translations.en.m3_p, /not a statistical test of cluster separation/);
  assert.match(translations.en.m3_cap, /third panel/);
  assert.match(translations.sr.m3_guide, /трећи/);
  assert.match(translations.en.source, /did not refresh/);
});


test('Serbia: other lists and invalid ballots are distinct categories', () => {
  const { ballot_breakdown: ballots } = JSON.parse(readFileSync(path.join(root, 'downloads/metrics.json')));
  assert.equal(ballots.valid + ballots.invalid, ballots.denominator);
  assert.equal(Object.values(ballots.list_votes).reduce((sum, n) => sum + n, 0), ballots.valid);
  assert.equal(ballots.other_lists + ballots.list_votes['1'] + ballots.list_votes['2'] + ballots.list_votes['3'], ballots.valid);
  assert.equal((100 * ballots.other_lists / ballots.denominator).toFixed(2), '4.66');
  assert.equal((100 * ballots.invalid / ballots.denominator).toFixed(2), '1.29');
  assert.equal(translations.en.pct_others, '4.66%');
  assert.equal(translations.en.pct_invalid, '1.29%');
  assert.match(html, /data-i18n="invalid">Invalid ballots/);
});
