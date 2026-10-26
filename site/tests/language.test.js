const assert = require("node:assert/strict");
const { readFileSync, existsSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const site = path.resolve(__dirname, "..");
const runtime = readFileSync(path.join(site, "language.js"), "utf8");
const pages = ["", "portugal-2025", "brazil-oct-2026-round-1", "brazil-oct-2026-round-2", "india-2024", "sloveniya-referendum-2026"];

function loadPage(directory, locales, saved, blocked = false) {
  const root = path.join(site, directory);
  const html = readFileSync(path.join(root, "index.html"), "utf8");
  const buttons = [...html.matchAll(/<button data-lang="([^"]+)"/g)].map((match) => ({
    dataset: { lang: match[1] },
    setAttribute(name, value) { this[name] = value; },
    addEventListener(event, callback) { this.click = callback; },
  }));
  const texts = [...html.matchAll(/data-i18n="([^"]+)"/g)].map((match) => ({ dataset: { i18n: match[1] } }));
  const figures = [...html.matchAll(/<img\b[^>]*>/g)].map((match) => {
    const dataset = {};
    for (const attr of match[0].matchAll(/data-(fig|dfig|alt)="([^"]+)"/g)) dataset[attr[1]] = attr[2];
    return { dataset };
  }).filter((image) => image.dataset.fig || image.dataset.dfig);
  const document = {
    documentElement: {},
    querySelectorAll(selector) {
      if (selector === ".langs button") return buttons;
      if (selector === "[data-i18n]") return texts;
      return figures;
    },
  };
  const storage = {
    getItem() { if (blocked) throw new Error("Storage blocked"); return saved; },
    setItem(key, value) { if (blocked) throw new Error("Storage blocked"); saved = value; },
  };
  const context = vm.createContext({ document, navigator: { languages: locales }, localStorage: storage });
  vm.runInContext(readFileSync(path.join(root, "translations.js"), "utf8"), context);
  vm.runInContext(runtime, context);
  return { root, document, buttons, figures, texts, context };
}

for (const directory of pages) {
  test(`${directory || "home"}: every language, figure and pressed state`, () => {
    const page = loadPage(directory, ["en-US"], null);
    assert.equal(page.document.documentElement.lang, "en");
    for (const button of page.buttons) {
      button.click();
      const language = button.dataset.lang;
      assert.equal(page.document.documentElement.lang, language);
      assert.equal(page.document.title, vm.runInContext(`I18N.${language}.title`, page.context));
      assert.equal(page.buttons.filter((item) => item["aria-pressed"] === "true").length, 1);
      assert.equal(button["aria-pressed"], "true");
      for (const text of page.texts) assert.equal(typeof text.innerHTML, "string", text.dataset.i18n);
      for (const image of page.figures) {
        assert.ok(existsSync(path.join(page.root, image.src)), image.src);
        if (image.dataset.alt) assert.equal(typeof image.alt, "string", image.dataset.alt);
      }
    }
  });
  test(`${directory || "home"}: unavailable storage preserves language switching`, () => {
    const page = loadPage(directory, ["xx"], null, true);
    assert.equal(page.document.documentElement.lang, "en");
    page.buttons[0].click();
    assert.equal(page.document.documentElement.lang, page.buttons[0].dataset.lang);
  });
}

test("saved preferences, aliases and unsupported preferences", () => {
  assert.equal(loadPage("", ["en"], "pt").document.documentElement.lang, "pt");
  assert.equal(loadPage("portugal-2025", ["pt-BR"], "hi").document.documentElement.lang, "pt");
  assert.equal(loadPage("india-2024", ["mr-IN"], null).document.documentElement.lang, "hi");
  assert.equal(loadPage("sloveniya-referendum-2026", ["sr-RS"], null).document.documentElement.lang, "hr");
  assert.equal(loadPage("brazil-oct-2026-round-1", ["en-US", "es-ES"], null).document.documentElement.lang, "es");
});
