const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../bulgaria-oct-2026-round-2');
const html = readFileSync(path.join(root, 'index.html'), 'utf8');
const context = vm.createContext({});
vm.runInContext(readFileSync(path.join(root, 'translations.js'), 'utf8'), context);
const translations = vm.runInContext('I18N', context);

test('Bulgaria runoff: English fallback and complete Bulgarian translations', () => {
  for (const match of html.matchAll(/<([\w]+)\b[^>]*data-i18n="([^"]+)"[^>]*>([\s\S]*?)<\/\1>/g)) {
    assert.equal(match[3].trim(), translations.en[match[2]], match[2]);
  }
  assert.deepEqual(Object.keys(translations.bg).sort(), Object.keys(translations.en).sort());
  for (const match of html.matchAll(/data-i18n="([^"]+)"/g)) {
    assert.equal(typeof translations.bg[match[1]], 'string', match[1]);
    assert.ok(translations.bg[match[1]].length > 0, match[1]);
  }
});

test('Bulgaria runoff: local assets, translated downloads and anchors resolve', () => {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(ids.length, new Set(ids).size);
  for (const content of [html, ...Object.values(translations.bg)]) {
    for (const match of content.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
      const url = new URL(match[1], 'https://preview.invalid/bulgaria-oct-2026-round-2/');
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

test('Bulgaria runoff: published standings agree with the bundled outputs', () => {
  const source = JSON.parse(readFileSync(path.join(root, 'downloads/source-check.json')));
  const audit = JSON.parse(readFileSync(path.join(root, 'downloads/eligibility.json')));
  const forensic = JSON.parse(readFileSync(path.join(root, 'downloads/forensics.json')));
  const sensitivity = JSON.parse(readFileSync(path.join(root, 'downloads/sensitivity.json')));
  assert.equal(source.national.processed_pct, 100);
  assert.equal(source.listed_votes, 1900183);
  assert.equal(source.indexed_sections, 12717);
  assert.ok(source.sections_reconcile);
  assert.ok(Object.values(source.section_minus_national).every(n => n === 0));
  assert.equal(source.invalid_balances.length, 14);
  assert.equal(source.national.candidates.find(c => c.no === 25).votes, 1093852);
  assert.equal(source.national.candidates.find(c => c.no === 4).votes, 750251);
  assert.equal(audit.eligible, forensic.n_units);
  assert.equal(audit.eligible + audit.excluded, audit.indexed);
  assert.equal(audit.eligible, 10656);
  assert.equal(forensic.shpilkin.tail_votes_party, 28904);
  assert.equal(forensic.shpilkin.t_cut_source, 'controls');
  assert.equal(sensitivity.digit_holm_mc.length, 4);
  const leaderSecond = sensitivity.digit_holm_mc.find(r => r.party === 'Yotova' && r.test === 'benford2');
  assert.ok(leaderSecond.p_mc < 0.05 && leaderSecond.p_holm < 0.05);
});

test('Bulgaria runoff: discoverable from the homepage and sitemap in every existing homepage language', () => {
  const home = readFileSync(path.join(root, '../index.html'), 'utf8');
  assert.match(home, /href="bulgaria-oct-2026-round-2\/index.html"/);
  const homeContext = vm.createContext({});
  vm.runInContext(readFileSync(path.join(root, '../translations.js'), 'utf8'), homeContext);
  const homeTranslations = vm.runInContext('I18N', homeContext);
  for (const translation of Object.values(homeTranslations)) {
    assert.equal(typeof translation.bg2_title, 'string');
    assert.equal(typeof translation.bg2_desc, 'string');
  }
  assert.match(readFileSync(path.join(root, '../sitemap.xml'), 'utf8'), /https:\/\/www\.renatyv\.org\/bulgaria-oct-2026-round-2\//);
});

test('Bulgaria runoff: language keys match the round-1 figure set and quoted numbers appear in both languages', () => {
  for (const lang of ['en', 'bg']) {
    assert.match(translations[lang].verdict_sub, lang === 'en' ? /12,717/ : /12 717/);
    assert.match(translations[lang].verdict_sub, /57[.,]566%/);
    assert.match(translations[lang].method_benford_p, /0[.,]0100/);
    for (const fig of ['mir', 'swing', 'turnout']) {
      assert.equal(typeof translations[lang][`${fig}_cap`], 'string');
      assert.equal(typeof translations[lang][`${fig}_alt`], 'string');
    }
  }
});


test('Bulgaria runoff: every detection method has an independent foldable and localized plot', () => {
  const section = html.match(/<section id="methods">([\s\S]*?)<\/section>/)[1];
  const methods = ['shpilkin', 'comet', 'fingerprint', 'integer', 'benford', 'last', 'outliers', 'ml', 'control', 'selftest'];
  assert.equal([...section.matchAll(/<details\b/g)].length, methods.length);
  assert.doesNotMatch(section, /<table\b/);
  for (const method of methods) {
    const foldable = section.match(new RegExp(`<details class="m" id="method-${method}">([\\s\\S]*?)<\\/details>`));
    assert.ok(foldable, method);
    assert.doesNotMatch(foldable[1], /<details\b/);
    assert.match(foldable[1], new RegExp(`data-dfig="${method}"`));
    for (const lang of ['en', 'bg']) {
      assert.ok(existsSync(path.join(root, 'img/details', lang, `${method}.png`)));
      for (const suffix of ['t', 'b', 'p']) assert.ok(translations[lang][`method_${method}_${suffix}`]);
      assert.ok(translations[lang][`${method}_alt`]);
      assert.ok(translations[lang][`${method}_cap`]);
    }
  }
  assert.match(section, /id="method-benford">\s*<summary><span class="badge warn"/);
  assert.match(section, /id="method-last">\s*<summary><span class="badge pass"/);
});


test('Bulgaria runoff: second-digit description agrees with the eligible candidate tallies', () => {
  const [header, ...rows] = readFileSync(path.join(root, 'downloads/sections.csv'), 'utf8').trim().split(/\r?\n/);
  const column = header.split(',').indexOf('votes:Yotova');
  assert.ok(column >= 0);
  const counts = rows.map(row => Number(row.split(',')[column])).filter(n => n >= 10);
  assert.equal(counts.length, 10445);
  assert.equal(counts.filter(n => String(n)[1] === '0').length, 1452);
  assert.match(translations.en.method_benford_p, /1,452 second-digit zeros/);
  assert.match(translations.bg.method_benford_p, /1 452 нули/);
});
