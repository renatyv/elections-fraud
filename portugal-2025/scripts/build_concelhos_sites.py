#!/usr/bin/env python3
"""All 308 Portuguese concelhos with their official websites.

Based on data/legislativas2025_mai/results_concelhos.csv (key, DICO code,
district, AR-2025 electorate). Websites:
  1) Wikidata: P856 on instances of Q13217644 "municipality of Portugal"
     (cache: data/concelhos_sites_wikidata.json, refreshed with --refresh-wd);
  2) liveness check via HTTP GET (follows redirects, records the final URL);
  3) for missing/dead ones — try the cm-<slug>.pt patterns
     (slug without spaces/hyphens and with them — as in cm-alcacerdosal.pt).

Result: data/concelhos_sites.csv, sorted by descending electorate.

  python3 build_concelhos_sites.py [--no-verify] [--refresh-wd] [--top N]
"""
import argparse
import csv
import json
import os
import re
import ssl
import sys
import time
import unicodedata
import urllib.request
import urllib.parse
import urllib.error

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_IN = os.path.join(BASE, 'data', 'legislativas2025_mai', 'results_concelhos.csv')
CSV_OUT = os.path.join(BASE, 'data', 'concelhos_sites.csv')
WD_CACHE = os.path.join(BASE, 'data', 'concelhos_sites_wikidata.json')

WD_QUERY = ('SELECT ?name ?site WHERE { ?m wdt:P31 wd:Q13217644 . '
            '?m wdt:P856 ?site . ?m rdfs:label ?name . FILTER(LANG(?name)="pt") }')

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) elections-research/1.0')

SKIP_HOSTS = ('facebook.com', 'twitter.com', 'x.com', 'instagram.com',
              'youtube.com', 'linkedin.com', 'wikipedia.org')

# Known exceptions to the cm-<full-name>.pt pattern
PATTERN_OVERRIDES = {
    'vila nova de gaia': ['cm-gaia.pt'],
    'sao pedro do sul': ['cm-spsul.pt'],
    'santo tirso': ['cm-stirso.pt'],
    'vila franca de xira': ['cm-vfxira.pt'],
    'vila nova de famalicao': ['cm-famalicao.pt'],
    'ponte de sor': ['cm-pontedesor.pt', 'cm-pontedesor.com'],
    'santa maria da feira': ['cm-smf.pt'],
    'oeiras': ['oeiras.pt', 'cm-oeiras.pt'],
}


def deaccent(s):
    s = s.replace('ç', 'c').replace('Ç', 'C')
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def norm_name(s):
    """Normalization for Wikidata matching: no accents/case/punctuation."""
    return re.sub(r'[^a-z0-9]', '', deaccent(s).lower())


def slug_variants(name):
    base = deaccent(name).lower()
    no_punct = re.sub(r"[^a-z0-9]", "", base)
    with_dash = re.sub(r"\s+", "-", re.sub(r"[^a-z0-9\s-]", "", base))
    outs = []
    for host in (f'cm-{no_punct}.pt', f'cm-{with_dash}.pt'):
        if host not in outs and 'cm-..pt' not in host:
            outs.append(host)
    return outs


def fetch_wikidata():
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode(
        {'query': WD_QUERY, 'format': 'json'})
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    sites = {}
    for b in data['results']['bindings']:
        name, site = b['name']['value'], b['site']['value'].strip('/')
        host = urllib.parse.urlparse(site).netloc.lower()
        if any(h in host for h in SKIP_HOSTS):
            continue
        sites.setdefault(norm_name(name), []).append(site)
    # several P856 may be listed: prefer https and a .pt domain
    for k, v in sites.items():
        v.sort(key=lambda s: (not s.startswith('https'), '.pt' not in s, s))
    return sites


def http_check(url, timeout=15):
    """GET with redirects; -> (final_url, status) or (None, 'error')."""
    req = urllib.request.Request(url, headers={'User-Agent': UA,
                                               'Accept': 'text/html,*/*'})
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.geturl(), r.status
    except urllib.error.HTTPError as e:
        # 403/405 from some CMS — the site is alive behind a bot filter; count as alive
        if e.code in (403, 405, 429, 503):
            return url, e.code
        return None, f'HTTP {e.code}'
    except Exception as e:
        return None, type(e).__name__


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-verify', action='store_true',
                    help='skip HTTP verification of sites (Wikidata only)')
    ap.add_argument('--refresh-wd', action='store_true')
    ap.add_argument('--top', type=int, default=0,
                    help='process only the N largest (0 = all)')
    args = ap.parse_args()

    with open(CSV_IN, encoding='utf-8-sig') as f:
        rows = [r for r in csv.DictReader(f) if r['key'].startswith('LOCAL-')]
    rows.sort(key=lambda r: int(r['registered_voters']), reverse=True)
    if args.top:
        rows = rows[:args.top]
    print(f'concelhos from CSV: {len(rows)}')

    if args.refresh_wd or not os.path.exists(WD_CACHE):
        print('querying Wikidata (P856)...')
        sites = fetch_wikidata()
        with open(WD_CACHE, 'w', encoding='utf-8') as f:
            json.dump(sites, f, ensure_ascii=False, indent=1)
    else:
        with open(WD_CACHE, encoding='utf-8') as f:
            sites = json.load(f)
    print(f'sites from Wikidata: {len(sites)} municipalities')

    out, no_site = [], []
    for i, r in enumerate(rows, 1):
        key = r['key']
        dico = key.replace('LOCAL-', '')[:4]
        district = r['path'].split(' > ')[1] if ' > ' in r['path'] else ''
        name = r['name']
        voters = int(r['registered_voters'])

        site, source, status, final = '', 'none', '', ''
        wd = sites.get(norm_name(name))
        if wd:
            site, source = wd[0], 'wikidata'

        if not args.no_verify:
            if site:
                final, status = http_check(site)
                if not final:
                    print(f'  [{i}/{len(rows)}] {name}: {site} unreachable '
                          f'({status}), trying patterns')
                    site, source = '', 'none'
            if not site:
                cands = PATTERN_OVERRIDES.get(name.lower(), []) + slug_variants(name)
                for host in cands:
                    for scheme in ('https://', 'http://'):
                        final, status = http_check(scheme + host)
                        if final:
                            site, source = scheme + host, 'pattern'
                            break
                    if site:
                        break
            time.sleep(0.35)
        elif site:
            final, status = site, 'unverified'

        if not site:
            no_site.append(name)
        out.append({'rank': i, 'key': key, 'dico': dico, 'name': name,
                    'district': district, 'registered_voters': voters,
                    'website': site, 'final_url': final,
                    'http_status': status, 'source': source})
        if i % 40 == 0:
            print(f'  ... {i}/{len(rows)}')

    with open(CSV_OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f'\ndone: {CSV_OUT}')
    ok = sum(1 for r in out if r['website'])
    print(f'with websites: {ok}/{len(out)}')
    if no_site:
        print('without a website:', ', '.join(no_site))


if __name__ == '__main__':
    sys.exit(main())
