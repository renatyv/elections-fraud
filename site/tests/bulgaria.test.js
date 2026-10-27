const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../bulgaria-oct-2026');
const html = readFileSync(path.join(root, 'index.html'), 'utf8');
const context = vm.createContext({});
vm.runInContext(readFileSync(path.join(root, 'translations.js'), 'utf8'), context);
const translations = vm.runInContext('I18N', context);

test('Bulgaria: English fallback and complete Bulgarian translations', () => {
  for (const match of html.matchAll(/<([\w]+)\b[^>]*data-i18n="([^"]+)"[^>]*>([\s\S]*?)<\/\1>/g)) {
    assert.equal(match[3].trim(), translations.en[match[2]], match[2]);
  }
  assert.deepEqual(Object.keys(translations.bg).sort(), Object.keys(translations.en).sort());
  for (const match of html.matchAll(/data-i18n="([^"]+)"/g)) {
    assert.equal(typeof translations.bg[match[1]], 'string', match[1]);
    assert.ok(translations.bg[match[1]].length > 0, match[1]);
  }
});

test('Bulgaria: local assets, translated downloads and anchors resolve', () => {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(ids.length, new Set(ids).size);
  for (const content of [html, ...Object.values(translations.bg)]) {
    for (const match of content.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
      const url = new URL(match[1], 'https://preview.invalid/bulgaria-oct-2026/');
      if (url.origin !== 'https://preview.invalid' || url.pathname.startsWith('/_vercel/')) continue;
      assert.ok(existsSync(path.resolve(root, '..', `.${url.pathname}`)), match[1]);
      if (url.hash) assert.ok(ids.includes(url.hash.slice(1)), match[1]);
    }
  }
  for (const image of html.matchAll(/<img\b([^>]+)>/g)) {
    assert.match(image[1], /loading="lazy"/);
    assert.match(image[1], /alt="[^"]+"/);
  }
  for (const image of html.matchAll(/data-fig="([^"]+)"/g)) {
    for (const lang of ['en', 'bg']) {
      assert.ok(existsSync(path.join(root, 'img', lang, `${image[1]}.png`)), `${lang}/${image[1]}`);
    }
  }
});

test('Bulgaria: published standings agree with the bundled metrics', () => {
  const metrics = JSON.parse(readFileSync(path.join(root, 'downloads/metrics.json')));
  assert.equal(metrics.snapshots, 10);
  assert.equal(metrics.listed_votes_final, 1512779);
  assert.equal(metrics.pct_counted_series[metrics.last_fetch_utc], 98.99);
  assert.equal(metrics.shares_final_pct['25'], 34.699);
  assert.equal(metrics.shares_final_pct['4'], 31.984);
  assert.deepEqual(metrics.runoff.pair, ['Yotova', 'Gyurov']);
  assert.equal(metrics.runoff.date, '2026-11-01');
  assert.equal(metrics.consistency_mir_sum_equals_country_final, true);
  assert.equal(Object.keys(metrics.per_mir).length, 32);
  assert.match(translations.en.result_note, /4\.426%/);
  assert.match(translations.bg.result_note, /4,426%/);
  assert.match(translations.en.verdict_sub, /1,512,779/);
  assert.match(translations.bg.verdict_sub, /1 512 779/);
  assert.match(translations.en.chip_count, /100%/);
  assert.match(translations.bg.chip_count, /100%/);
});

test('Bulgaria: discoverable from the homepage and sitemap in every existing homepage language', () => {
  const home = readFileSync(path.join(root, '../index.html'), 'utf8');
  assert.match(home, /href="bulgaria-oct-2026\/index.html"/);
  const homeContext = vm.createContext({});
  vm.runInContext(readFileSync(path.join(root, '../translations.js'), 'utf8'), homeContext);
  const homeTranslations = vm.runInContext('I18N', homeContext);
  for (const translation of Object.values(homeTranslations)) {
    assert.equal(typeof translation.bg_title, 'string');
    assert.equal(typeof translation.bg_desc, 'string');
  }
  assert.match(readFileSync(path.join(root, '../sitemap.xml'), 'utf8'), /https:\/\/www\.renatyv\.org\/bulgaria-oct-2026\//);
});


test('Bulgaria: current results and section screening reconcile with published outputs', () => {
  const source = JSON.parse(readFileSync(path.join(root, 'downloads/source-check.json')));
  const audit = JSON.parse(readFileSync(path.join(root, 'downloads/eligibility.json')));
  const forensic = JSON.parse(readFileSync(path.join(root, 'downloads/forensics.json')));
  const sensitivity = JSON.parse(readFileSync(path.join(root, 'downloads/sensitivity.json')));
  assert.equal(source.national.processed_pct, 100);
  assert.equal(source.listed_votes, 1521711);
  assert.equal(source.indexed_sections, 12719);
  assert.ok(source.sections_reconcile);
  assert.ok(Object.values(source.section_minus_national).every(n => n === 0));
  assert.equal(source.invalid_balances.length, 22);
  assert.equal(source.national.candidates.find(c => c.no === 25).votes, 528929);
  assert.equal(audit.eligible, forensic.n_units);
  assert.equal(audit.eligible + audit.excluded, audit.indexed);
  assert.equal(audit.eligible, 10616);
  assert.equal(forensic.shpilkin.tail_votes_party, 7845);
  assert.equal(forensic.fingerprint.separated, false);
  assert.equal(sensitivity.digit_holm_mc.length, 7);
  const leaderLast = sensitivity.digit_holm_mc.find(r => r.party === 'Yotova' && r.test === 'last');
  assert.ok(leaderLast.p_mc < 0.05 && leaderLast.p_holm > 0.05);
  for (const lang of ['en', 'bg']) {
    assert.match(translations[lang].verdict_sub, lang === 'en' ? /10,616/ : /10 616/);
    assert.match(translations[lang].methods_table, /0[.,]1122/);
  }
});
