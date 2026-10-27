const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../slovakia-oct-2026');
const html = readFileSync(path.join(root, 'index.html'), 'utf8');
const context = vm.createContext({});
vm.runInContext(readFileSync(path.join(root, 'translations.js'), 'utf8'), context);
const translations = vm.runInContext('I18N', context);

test('Slovakia: English fallback agrees with runtime translations', () => {
  for (const match of html.matchAll(/<([\w]+)\b[^>]*data-i18n="([^"]+)"[^>]*>([\s\S]*?)<\/\1>/g)) {
    assert.equal(match[3].trim(), translations.en[match[2]], match[2]);
  }
  assert.deepEqual(Object.keys(translations.sk).sort(), Object.keys(translations.en).sort());
});

test('Slovakia: local resources and section anchors resolve', () => {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(ids.length, new Set(ids).size);
  for (const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
    const url = new URL(match[1], 'https://preview.invalid/slovakia-oct-2026/');
    if (url.origin !== 'https://preview.invalid' || url.pathname.startsWith('/_vercel/')) continue;
    assert.ok(existsSync(path.resolve(root, '..', `.${url.pathname}`)), match[1]);
    if (url.hash) assert.ok(ids.includes(url.hash.slice(1)), match[1]);
  }
});
