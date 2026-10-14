// Downloader of MAI portal data from the context of a real browser.
// The portal's CDN (Akamai) blocks curl/urllib by TLS fingerprint under heavy
// downloading, but lets through fetch() requests from an open portal page.
//
// Usage (ZCode / any Chrome + an open page
// https://www.eleicoes.mai.gov.pt/<slug>/):
//   1) start the receiver: python3 scripts/local_receiver.py <download_dir> 8765
//   2) open https://www.eleicoes.mai.gov.pt/legislativas2025/ in the browser
//   3) in the page console (DevTools) run the code below, filling in the KEYS array
//      (territory keys from territory-tree.json / territory-children)
//
// Rate ~1.5 req/s, automatic 120 s pause on "Access Denied"; the results are sent
// to localhost:8765 (files are skipped if they already exist).

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
// progress: console.log(window.__dlStat)
