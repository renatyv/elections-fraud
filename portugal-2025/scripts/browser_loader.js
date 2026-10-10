// Загрузчик данных портала MAI из контекста реального браузера.
// CDN портала (Akamai) блокирует curl/urllib по TLS-отпечатку при интенсивной
// загрузке, но пропускает запросы fetch() из открытой страницы портала.
//
// Использование (ZCode / любой Chrome + открытая страница
// https://www.eleicoes.mai.gov.pt/<slug>/):
//   1) запустить приёмник: python3 scripts/local_receiver.py <каталог_выгрузки> 8765
//   2) открыть в браузере https://www.eleicoes.mai.gov.pt/legislativas2025/
//   3) в консоли страницы (DevTools) выполнить код ниже, подставив массив KEYS
//      (ключи территорий из territory-tree.json / territory-children)
//
// Темп ~1.5 req/s, авто-пауза 120с при «Access Denied», результаты улетают
// на localhost:8765 (файлы пропускаются, если уже есть).

const KEYS = ["GLOBAL-990000", "LOCAL-500000" /* , ... */];
const SUFFIX = "AR";            // AR | PE | PR | CM | AM | AF
const ELECTION = "legislativas2025";
const stat = window.__dlStat = { done: 0, saved: 0, nf: 0, denied: 0, finished: false, lastKey: "" };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b64 = (s) => { const u = new TextEncoder().encode(s); let b = ""; for (const c of u) b += String.fromCharCode(c); return btoa(b); };

(async () => {
  let buf = [];
  for (const k of KEYS) {
    stat.lastKey = k;
    let ok = false;
    for (let attempt = 0; attempt < 40 && !ok; attempt++) {
      try {
        const r = await fetch(`/${ELECTION}/assets/static/territory-results/territory-results-${k}-${SUFFIX}.json`);
        const t = await r.text();
        if (t.includes("Access Denied")) { stat.denied++; await sleep(120000); continue; }
        if (/^[{\[]/.test(t)) { buf.push({ name: `territory-results/${k}-${SUFFIX}.json`, b64: b64(t) }); stat.saved++; }
        else stat.nf++;
        ok = true;
      } catch (e) { await sleep(8000); }
    }
    stat.done++;
    if (buf.length >= 20) {
      await fetch("http://127.0.0.1:8765/put", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ files: buf }) });
      buf = [];
    }
    await sleep(600);
  }
  if (buf.length) {
    await fetch("http://127.0.0.1:8765/put", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ files: buf }) });
  }
  stat.finished = true;
})();
// прогресс: console.log(window.__dlStat)
