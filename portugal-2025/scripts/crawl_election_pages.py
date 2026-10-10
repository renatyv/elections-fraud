#!/usr/bin/env python3
"""Полуавтоматический обход разделов выборов на сайтах камар муниципалитетов.

Пайплайн на каждый сайт (из data/concelhos_sites.csv):
  1) robots.txt -> строки Sitemap; наряду с этим типовые пути
     /sitemap.xml /sitemap_index.xml /wp-sitemap.xml /sitemap-index.xml;
  2) рекурсивный разбор sitemap-индексов (лимиты на сайт);
  3) фильтрация URL по ключевым словам выборов, рейтинг;
  4) загрузка топ-кандидатов. Особый случай (типовые WordPress-камары):
     URL вида /?listas_ficheiros=<слаг-документа> редиректят СРАЗУ на файл —
     сверяем content-type; PDF-слаги с признаками карты результатов = цель;
  5) HTML-страницы: извлечение ссылок на PDF;
  6) --download: докачка «тира A» (карты результатов выборов) в
     data/seccoes/<DICO>_<slug>/, реестр data/seccoes/catalog.csv;
     отчёт по каждому сайту: data/seccoes/crawl/<DICO>_<slug>.json.

  python3 crawl_election_pages.py --names "Lisboa,Porto" [--download]
  python3 crawl_election_pages.py --top 6 [--download]
  python3 crawl_election_pages.py --dicos 1106,1312
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITES_CSV = os.path.join(BASE, 'data', 'concelhos_sites.csv')
SECCOES_DIR = os.path.join(BASE, 'data', 'seccoes')
CRAWL_DIR = os.path.join(SECCOES_DIR, 'crawl')
CATALOG_CSV = os.path.join(SECCOES_DIR, 'catalog.csv')

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) elections-research/1.0')

SITEMAP_PATHS = ['/sitemap.xml', '/sitemap_index.xml', '/wp-sitemap.xml',
                 '/sitemap-index.xml', '/sitemap1.xml', '/sitemap_prod.xml']

NS = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

ACCENTS = {'ç': 'c', 'ã': 'a', 'á': 'a', 'à': 'a', 'â': 'a', 'é': 'e',
           'ê': 'e', 'í': 'i', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ú': 'u'}
KW_STRONG = ['eleic', 'eleitor', 'votac', 'resultad', 'legislativ',
             'autarqu', 'presidenci', 'europei', 'referend', 'escrutin']
KW_WEAK = ['vot', 'sec', 'urna', 'mapa', '2025', '2024', '2026']

# тир A — карты результатов (качаем), тир B — прочие документы выборов (только в реестр)
ELECTION_TYPE = ['legislativ', 'autarqu', 'presidenci', 'europei', 'referend',
                 'eleic', 'eleitor']
RESULT_SIG = ['resultad', 'mapa', 'apurament', 'escrutin']


def deaccent(s):
    for k, v in ACCENTS.items():
        s = s.replace(k, v)
    return s


def norm_url(u):
    u = deaccent(urllib.parse.unquote(u).lower())
    return u.replace('_', '-')


def fetch(url, timeout=25, as_bytes=False):
    """GET с редиректами; -> (final_url, content_type, bytes|str)."""
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        ct = (r.headers.get('Content-Type') or '').lower()
        return r.geturl(), ct, (data if as_bytes else data.decode('utf-8', 'replace'))


def score_url(url):
    u = norm_url(url)
    s = 0
    for kw in KW_STRONG:
        if kw in u:
            s += 3
    for kw in KW_WEAK:
        if kw in u:
            s += 1
    return s


def pdf_tier(url):
    """A = карта результатов выборов; B = прочий документ выборов; '' = мимо."""
    u = norm_url(url)
    is_election = any(kw in u for kw in ELECTION_TYPE)
    has_result = any(kw in u for kw in RESULT_SIG)
    if not (is_election or has_result):
        return ''
    # эдитали/бюллетени/досрочное голосование/места голосования/составы mesa —
    # организация выборов, не результаты; только в реестр
    if any(k in u for k in ('edital', 'boletim', 'locais-e-horarios',
                            'voto-antecipado', 'votoantecipado',
                            'recenseament', 'locais-de-voto',
                            'eleitores-que', 'eleitores-votam',
                            'membros', 'mesa', 'assembleias-de-voto',
                            'assembleia-e-seccoes', 'mapa-definitivo')):
        return 'B' if 'resultado' not in u and 'apurament' not in u else 'A'
    if has_result or (is_election and any(k in u for k in ('secc', 'vot', 'mapa'))):
        return 'A'
    return 'B'


def load_sitemaps(site):
    host = urllib.parse.urlparse(site)
    root = f'{host.scheme}://{host.netloc}'
    seen_maps, urls, seen_urls = set(), [], set()
    queue = []

    try:
        _, _, robots = fetch(root + '/robots.txt', timeout=15)
        for line in robots.splitlines():
            if line.lower().startswith('sitemap:'):
                queue.append(line.split(':', 1)[1].strip())
    except Exception:
        pass

    for p in SITEMAP_PATHS:
        queue.append(root + p)

    while queue and len(urls) < 20000 and len(seen_maps) < 40:
        sm = queue.pop(0)
        if sm in seen_maps or not sm.startswith('http'):
            continue
        seen_maps.add(sm)
        try:
            _, _, xml_text = fetch(sm, timeout=20)
            root_el = ET.fromstring(
                re.sub(r'&(?![a-z]+;|#\d+;)', '&amp;', xml_text))
        except Exception:
            continue
        children = (root_el.findall('sm:sitemap/sm:loc', NS)
                    or root_el.findall('sitemap/loc'))
        locs = (root_el.findall('sm:url/sm:loc', NS)
                or root_el.findall('url/loc'))
        if children:
            queue.extend(c.text.strip() for c in children)
        for l in locs:
            if l.text and l.text.strip() not in seen_urls:
                seen_urls.add(l.text.strip())
                urls.append(l.text.strip())
        time.sleep(0.15)
    return urls, seen_maps


def extract_pdfs(html, base_url):
    out = set()
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.I):
        href = m.group(1)
        if '.pdf' in norm_url(href):
            out.add(urllib.parse.urljoin(base_url, href))
    return out


def save_pdf(url):
    """Скачивает PDF в data/seccoes/<dico>_<slug>/; -> (path, status)."""
    try:
        final, ct, data = fetch(url, as_bytes=True)
    except Exception as e:
        return None, type(e).__name__
    if not data.startswith(b'%PDF'):
        return None, f'not-a-pdf ({ct or "?"})'
    name = os.path.basename(urllib.parse.urlparse(final).path) or 'doc.pdf'
    if not name.lower().endswith('.pdf'):
        name += '.pdf'
    path = os.path.join(DEST_DIR, name)
    os.makedirs(DEST_DIR, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)
    return path, 'ok'


def append_catalog(rows):
    new = not os.path.exists(CATALOG_CSV)
    os.makedirs(SECCOES_DIR, exist_ok=True)
    with open(CATALOG_CSV, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['dico', 'name', 'site', 'tier',
                                          'pdf_url', 'local_path', 'bytes',
                                          'status', 'fetched_at'])
        if new:
            w.writeheader()
        w.writerows(rows)


DEST_DIR = ''  # выставляется в process() — каталог текущего конселью


def process(row, download=False, max_pages=20):
    global DEST_DIR
    name, site, dico = row['name'], row['website'], row['dico']
    slug = re.sub(r'[^a-z0-9]+', '', deaccent(name).lower())
    DEST_DIR = os.path.join(SECCOES_DIR, f'{dico}_{slug}')
    print(f'\n=== {name} ({dico}, {row["registered_voters"]} изб.) — {site}')

    urls, maps = load_sitemaps(site)
    print(f'  sitemap-файлов: {len(maps)}, URL: {len(urls)}')
    report = {'name': name, 'dico': dico, 'site': site, 'sitemaps': len(maps),
              'sitemap_urls': len(urls), 'tierA': [], 'tierB': [], 'notes': []}
    if not urls:
        report['notes'].append('sitemap не найден — нужен ручной обход/поиск')
        print('  ! sitemap не найден')
        save_report(report)
        return {'name': name, 'maps': 0, 'urls': 0, 'A': 0, 'B': 0, 'dl': 0}

    scored = sorted(((score_url(u), u) for u in urls), reverse=True)
    cands = [u for s, u in scored if s >= 4][:max_pages]
    report['candidates_sample'] = [{'score': score_url(u), 'url': u}
                                   for u in cands[:30]]
    print(f'  кандидатов: {sum(1 for s, _ in scored if s >= 4)}, берем {len(cands)}')

    # 1) прямые документы: PDF-урлы из sitemap + listas_ficheiros-редиректы
    pdf_docs = {}  # final_url -> origin
    for u in urls:
        if norm_url(u).endswith('.pdf'):
            pdf_docs[u] = 'sitemap'
    # 2) обход страниц-кандидатов
    for u in cands:
        try:
            final, ct, body = fetch(u)
        except Exception as e:
            report['notes'].append(f'{u}: {type(e).__name__}')
            continue
        if 'pdf' in ct:
            pdf_docs[final] = f'redirect<-{u}'
        elif 'html' in ct:
            for p in extract_pdfs(body, final):
                pdf_docs.setdefault(p, f'page<-{u}')
        time.sleep(0.3)

    # внешний хост (напр., sg.mai.gov.pt) — не качаем, только в реестр
    site_host = urllib.parse.urlparse(site).netloc.lower().removeprefix('www.')

    tierA = sorted({u: t for u in pdf_docs if (t := pdf_tier(u)) == 'A'
                    and urllib.parse.urlparse(u).netloc.lower()
                    .removeprefix('www.').endswith(site_host)}.items())
    tierA_ext = sorted(u for u in pdf_docs if pdf_tier(u) == 'A'
                       and u not in {x for x, _ in tierA})
    tierB = sorted({u: t for u in pdf_docs if (t := pdf_tier(u)) == 'B'}.items())
    report['tierA'] = [{'url': u, 'origin': o} for u, o in tierA]
    report['tierA_external'] = tierA_ext
    report['tierB'] = [{'url': u, 'origin': o} for u, o in tierB]
    print(f'  документов выборов: тир A {len(tierA)}, тир B {len(tierB)}')
    for u, o in tierA[:15]:
        print(f'    [A] {u}   ({o})')

    n_dl, cat_rows = 0, []
    if download and tierA:
        for u, o in tierA:
            path, st = save_pdf(u)
            if path:
                n_dl += 1
                cat_rows.append({'dico': dico, 'name': name, 'site': site,
                                 'tier': 'A', 'pdf_url': u,
                                 'local_path': path,
                                 'bytes': os.path.getsize(path), 'status': st,
                                 'fetched_at': time.strftime('%Y-%m-%d %H:%M')})
                print(f'    -> {path} ({os.path.getsize(path)} B)')
            else:
                cat_rows.append({'dico': dico, 'name': name, 'site': site,
                                 'tier': 'A', 'pdf_url': u, 'local_path': '',
                                 'bytes': 0, 'status': st,
                                 'fetched_at': time.strftime('%Y-%m-%d %H:%M')})
                print(f'    !! {u}: {st}')
            time.sleep(0.4)
    if download and tierB:
        for u, o in tierB:
            cat_rows.append({'dico': dico, 'name': name, 'site': site,
                             'tier': 'B', 'pdf_url': u, 'local_path': '',
                             'bytes': 0, 'status': 'not-downloaded',
                             'fetched_at': time.strftime('%Y-%m-%d %H:%M')})
    if cat_rows:
        append_catalog(cat_rows)
    save_report(report)
    return {'name': name, 'maps': len(maps), 'urls': len(urls),
            'A': len(tierA), 'B': len(tierB), 'dl': n_dl}


def save_report(report):
    os.makedirs(CRAWL_DIR, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '', deaccent(report['name']).lower())
    path = os.path.join(CRAWL_DIR, f"{report['dico']}_{slug}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--names', help='через запятую (как в CSV)')
    ap.add_argument('--dicos', help='DICO-коды через запятую, напр. 1106')
    ap.add_argument('--top', type=int, help='N крупнейших по избирателям')
    ap.add_argument('--download', action='store_true')
    args = ap.parse_args()

    with open(SITES_CSV, encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if r['website']]
    if args.names:
        want = {n.strip().lower() for n in args.names.split(',')}
        rows = [r for r in rows if r['name'].lower() in want]
    elif args.dicos:
        want = {d.strip() for d in args.dicos.split(',')}
        rows = [r for r in rows if r['dico'] in want]
    elif args.top:
        rows = rows[:args.top]
    if not rows:
        sys.exit('ничего не выбрано (проверьте --names/--dicos/--top)')

    stats = [process(r, args.download) for r in rows]
    print('\n===== сводка =====')
    for s in stats:
        print(f'  {s["name"]}: sitemap {s["maps"]}, URL {s["urls"]}, '
              f'тир A {s["A"]}, тир B {s["B"]}, скачано {s["dl"]}')


if __name__ == '__main__':
    sys.exit(main())
