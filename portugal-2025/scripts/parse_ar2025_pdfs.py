#!/usr/bin/env python3
"""Парсинг всех AR-2025 (18.05.2025) PDF из data/seccoes/ в CSV по папкам + сверка с MAI.

Переиспользует парсеры parse_seccoes_ar2025.py (Benavente, Alcácer, Borba,
Vendas Novas, Ferreira do Alentejo, Sousel, Gouveia) и добавляет новые:
  0902 Almeida (Quadro-de-Resultados-2.pdf: фрегезии + 2 секции Vilar Formoso)
  1301 Amarante (Resultados-Totais-18_05_2025.pdf: фрегезии)
  1608 Valença (ESCRUTINIO...18.05.2025.pdf: фрегезии)
  1824 Vouzela (202505_Consulte-aqui-os-resultados.pdf — скан: Apple Vision OCR
       + tesseract, слияние по колоночным кластерам с арифметическим контролем)
  0202 Almodôvar (EL25_MapaDef_*.pdf — скан-эдиталы: состав участков и места
       голосования; результатов по секциям камара не публикует)

Выход: <папка>/ar2025_*.csv в каждой папке; лог сверки —
data/seccoes/ar2025_pdfs_validation.txt. Схема CSV как у ar2025_seccoes.csv
(+ колонки pdf_nome для фрегезийных файлов).

Запуск: python3 scripts/parse_ar2025_pdfs.py [--no-ocr]
"""
import csv
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_seccoes_ar2025 as base  # noqa: E402

SECCOES = base.SECCOES
OCR_BIN = '/tmp/ocr_vision'

LOG = []


def log(msg=''):
    print(msg)
    LOG.append(msg)


# ---------------------------------------------------------------- helpers --

def write_csv(path, rows, extra=()):
    if not rows:
        return
    fields = ['dico', 'concelho', 'mai_key', 'freguesia', 'nivel', 'secao',
              'local', 'eleitores', 'votantes', 'brancos', 'nulos', 'abst'] \
             + [f'votes:{p}' for p in base.PARTIES] + list(extra)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    log(f'  -> {os.path.relpath(path, SECCOES)}: {len(rows)} строк')


def png_width(p):
    out = subprocess.run(['sips', '-g', 'pixelWidth', p],
                         capture_output=True, text=True).stdout
    return int(re.search(r'pixelWidth: (\d+)', out).group(1))


def mai_level3(dico):
    return {k: m for k, m in base.mai_rows().items()
            if k.startswith(f'LOCAL-{dico}') and m['level'] == '3'}


MF = {'eleitores': 'registered_voters', 'votantes': 'voted',
      'brancos': 'blank_votes', 'nulos': 'null_votes'}


def match_and_check(rows, dico, label):
    """Сопоставление строк с MAI-фрегезиями по (eleitores, votantes) + сверка."""
    mai = mai_level3(dico)
    used = set()
    for r in rows:
        hits = [k for k, m in mai.items()
                if k not in used
                and int(m['registered_voters']) == r['eleitores']
                and int(m['voted']) == r['votantes']]
        if len(hits) != 1:
            log(f'  ✗ {label}: {r.get("pdf_nome", "?")!r} '
                f'({r["eleitores"]} изб., {r["votantes"]} голос.): '
                f'пар MAI = {len(hits)}')
            continue
        k = hits[0]
        used.add(k)
        r['mai_key'], r['freguesia'] = k, mai[k]['name']
        diffs = [f'{f}: pdf={r.get(f)} mai={int(mai[k][MF.get(f, f)] or 0)}'
                 for f in ('brancos', 'nulos')
                 + tuple('votes:' + p for p in base.PARTIES)
                 if int(r.get(f, 0) or 0) != int(mai[k][MF.get(f, f)] or 0)]
        (log(f'  ✗ {mai[k]["name"]}: ' + '; '.join(diffs)) if diffs
         else log(f'  ✓ {mai[k]["name"]}: {r["eleitores"]} изб., '
                  f'{r["votantes"]} голос.'))
    if len(used) != len(mai):
        miss = [m['name'] for k, m in mai.items() if k not in used]
        log(f'  ✗ {label}: без пары остались MAI-фрегезии: {miss}')


def frow(dico, concelho, nome, nums, votes, nivel='freguesia', secao='',
         local=''):
    r = base.row(dico, concelho, '', '', nivel, secao, local, nums, votes)
    r['pdf_nome'] = nome
    return r


def row_ok(nums, votes):
    return sum(votes.values()) + nums['brancos'] + nums['nulos'] == nums['votantes']


def merge_thousands(tokens):
    """['2','310'] -> ['2310'] (разделитель тысяч пробелом)."""
    out = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and re.fullmatch(r'\d{1,3}', tokens[i]) \
                and re.fullmatch(r'\d{3}', tokens[i + 1]):
            tokens[i + 1] = tokens[i] + tokens[i + 1]
        else:
            out.append(tokens[i])
        i += 1
    return out


# ------------------------------------------------------- новые парсеры --

ALMEIDA_UNION_SIZES = [3, 3, 4, 2, 4, 2, 2]
ALMEIDA_COLS = ['B.E.', 'PPM', 'IL', 'PS', 'NC', 'VP', 'R.I.R.', 'E', 'CH',
                'ADN', 'L', 'PPD/PSD.CDS-PP', 'PCP-PEV', 'PAN']


def parse_almeida():
    """Фрегезии + 2 секции Vilar Formoso. Юнионы идут по баннерам
    'UNIÃO DE FREGUESIAS DE:' с известным числом компонентов; одиночные
    фрегезии — после последнего юниоса; VILAR/FORMOSO несут 'Secção nº'."""
    txt = base.pdf2txt('0902_almeida/Quadro-de-Resultados-2.pdf')
    raw_rows = []          # (name, nivel, secao, nums[18])
    ui = -1                # индекс текущего юниоса
    left = 0               # сколько компонентов ещё взять
    for line in open(txt, encoding='utf-8'):
        s = line.strip()
        if not s:
            continue
        if s.startswith('UNIÃO DE FREGUESIAS'):
            ui += 1
            left = ALMEIDA_UNION_SIZES[ui]
            continue
        if s.startswith('TOTAIS'):
            continue
        if s.startswith('Total'):
            nums = [int(t) for t in s.split()[1:] if t.isdigit()]
            raw_rows.append(('__total_vilar__', 'total', '', nums))
            continue
        toks = s.split()
        if not toks[0][:1].isalpha():
            continue
        nums = merge_thousands([t for t in toks if t.isdigit()])
        if len(nums) != 18:
            continue
        m_sec = re.match(r'^(VILAR|FORMOSO)\s+Secção', s)
        name = ' '.join(t for t in toks
                        if not t.isdigit() and t not in ('Secção', 'nº'))
        if m_sec:
            raw_rows.append((name, 'secao',
                             1 if m_sec.group(1) == 'VILAR' else 2, nums))
        elif left > 0:
            raw_rows.append((name, 'unionpart', '', nums))
            left -= 1
        else:
            raw_rows.append((name, 'freguesia', '', nums))

    rows, secs, unions = [], [], []
    total_row = next((n for nm, lv, sc, n in raw_rows
                      if lv == 'total'), None)
    for nm, lv, sc, nums in raw_rows:
        inscr, vot, br, nu = (int(x) for x in nums[:4])
        votes = dict(zip(ALMEIDA_COLS, (int(x) for x in nums[4:])))
        nd = {'eleitores': inscr, 'votantes': vot, 'brancos': br, 'nulos': nu,
              'abst': inscr - vot}
        assert row_ok(nd, votes), (nm, nums)
        if lv == 'secao':
            r = frow('0902', 'Almeida', nm, nd, votes, nivel='secao', secao=sc)
            r['freguesia'] = 'Vilar Formoso'
            secs.append(r)
        elif lv == 'unionpart':
            unions.append((nm, nd, votes))
        else:
            rows.append(frow('0902', 'Almeida', nm, nd, votes))

    # юнионы -> агрегаты (одна строка на юниос)
    agg, rest = [], list(unions)
    for size in ALMEIDA_UNION_SIZES:
        part, rest = rest[:size], rest[size:]
        nd = {f: sum(x[1][f] for x in part) for f in
              ('eleitores', 'votantes', 'brancos', 'nulos')}
        nd['abst'] = nd['eleitores'] - nd['votantes']
        votes = {p: sum(x[2].get(p, 0) for x in part) for p in base.PARTIES}
        name = 'UF ' + ' + '.join(x[0].title() for x in part)
        agg.append(frow('0902', 'Almeida', name, nd, votes))
    assert not rest

    # контроль: Total-строка PDF против суммы секций Vilar Formoso
    sv = [sum(int(x[f]) for x in secs) for f in
          ('eleitores', 'votantes', 'brancos', 'nulos')] + \
         [sum(int(x['votes:' + p]) for x in secs) for p in ALMEIDA_COLS]
    log(f'  Almeida: юниосов {len(agg)}, одиночных {len(rows)}, '
        f'секций Vilar Formoso {len(secs)}; Total PDF {total_row[:4]} vs '
        f'сумма секций {sv[:4]} — '
        + ('✓' if sv[:4] == total_row[:4] and
           sv[4:] == total_row[4:] else '✗ РАСХОЖДЕНИЕ'))
    return agg + rows, secs


AMARANTE_COLS = ['PPD/PSD.CDS-PP', 'PLS', 'NC', 'VP', 'PS', 'E', 'CH',
                 'PCP-PEV', 'R.I.R.', 'L', 'ND', 'PCTP/MRPP', 'IL', 'PAN',
                 'PPM', 'B.E.', 'JPP', 'ADN']


def parse_amarante():
    """Числовые строки: 23 числа + 1 процент; имена могут переноситься —
    каноническое имя приходит из MAI, pdf_nome только на той же строке."""
    txt = base.pdf2txt('1301_amarante/Resultados-Totais-18_05_2025.pdf')
    rows = []
    for line in open(txt, encoding='utf-8'):
        toks = line.split()
        if not toks:
            continue
        if toks[0].startswith(('ELEIÇÃO', 'ELEITORES', 'VOTOS', 'FREGUESIAS',
                               'INSCRITOS', 'Total', '%', 'PCTP/', 'MRPP',
                               'ABSTENÇÃO')):
            continue
        nums = merge_thousands([t for t in toks if t.isdigit()])
        pcts = [t for t in toks if re.fullmatch(r'\d+,\d+%|\d+%', t)]
        if len(nums) != 23 or len(pcts) != 1:
            continue
        name = ' '.join(t for t in toks if not t.isdigit() and t not in pcts)
        inscr, vot, br, nu = (int(x) for x in nums[:4])
        votes = dict(zip(AMARANTE_COLS, (int(x) for x in nums[4:])))
        nd = {'eleitores': inscr, 'votantes': vot, 'brancos': br, 'nulos': nu,
              'abst': inscr - vot}
        assert row_ok(nd, votes), (name, nums)
        rows.append(frow('1301', 'Amarante', name, nd, votes))
    assert len(rows) == 26, len(rows)
    return rows


VALENCA_COLS = ['L', 'PPD/PSD.CDS-PP', 'B.E.', 'E', 'R.I.R.', 'IL', 'ADN',
                'PAN', 'CH', 'VP', 'PPM', 'PCP-PEV', 'PS']


def parse_valenca():
    txt = base.pdf2txt(
        '1608_valenca/ESCRUTINIO-ASSEMBLEIA-DA-REPUBLICA18.05.2025.pdf')
    rows = []
    for line in open(txt, encoding='utf-8'):
        s = line.strip()
        if not s or s.startswith(('TOTAIS', 'Resultados', 'ABSTENÇÃO',
                                  'Eleitores', 'Freguesias', 'ELEIÇÃO',
                                  'D.A.G')):
            continue
        toks = s.split()
        if not any(t.isdigit() for t in toks):
            continue
        nums = [t for t in toks if t.isdigit()]
        if len(nums) != 17:
            continue
        name = ' '.join(t for t in toks if not t.isdigit())
        inscr, vot, br, nu = (int(x) for x in nums[:4])
        votes = dict(zip(VALENCA_COLS, (int(x) for x in nums[4:])))
        nd = {'eleitores': inscr, 'votantes': vot, 'brancos': br, 'nulos': nu,
              'abst': inscr - vot}
        assert row_ok(nd, votes), (name, nums)
        rows.append(frow('1608', 'Valença', name, nd, votes))
    assert len(rows) == 15, len(rows)
    return rows


# ------------------------------------------------------------- Vouzela --

def ensure_ocr_tool():
    if not os.path.exists(OCR_BIN):
        subprocess.run(['swiftc', '-O', '-o', OCR_BIN,
                        os.path.join(HERE, 'ocr_vision.swift')], check=True)


def num_candidates(tok):
    """Варианты оцифровки OCR-токена (tesseract/Vision путают 5/S, 0/O...)."""
    subs = {'S': '5', 's': '5', 'O': '0', 'o': '0', 'Q': '0', 'D': '0',
            'I': '1', 'l': '1', 'i': '1', '|': '1', '!': '1', 'З': '3',
            'g': '8', 'B': '8', 'Z': '2', 'A': '4', 'b': '6', 'G': '6',
            'T': '7', ')': '', '(': '', '.': '', ',': '', "'": '', '"': '',
            '§': '5', '€': '6'}
    t = tok.strip()
    if re.fullmatch(r'\d+', t):
        return [t]
    variants = {t}
    for _ in range(3):
        new = set()
        for v in variants:
            for ch, r in subs.items():
                if ch in v:
                    new.add(v.replace(ch, r))
        variants |= new
    return sorted({v for v in variants if re.fullmatch(r'\d{1,5}', v)},
                  key=lambda x: (-len(x), x))


VOUZELA_ANCHOR = ['857', '1285', '239', '1156', '789', '622', '1255', '916',
                  '1626', '8745']
VOUZELA_NAMES = ['Alcofra', 'Campia', 'Fornelo do Monte', 'Queirã',
                 'São Miguel do Mato', 'Ventosa',
                 'Cambra e Carvalhal de Vermilhas',
                 'Fataunços e Figueiredo das Donas',
                 'Vouzela e Paços de Vilharigues']
VOUZELA_PCOLS = ['ADN', 'IL', 'PPM', 'PPD/PSD.CDS-PP', 'R.I.R.', 'E', 'ND',
                 'B.E.', 'VP', 'PCP-PEV', 'CH', 'L', 'PS']


def parse_vision_padded(txt):
    out = []
    for line in txt.splitlines():
        if line.startswith('===') or not line.strip():
            continue
        out.append([(m.start(), m.group())
                    for m in re.finditer(r'\S+', line)])
    return out


def parse_tess_lines(tsv_path, imgw):
    rows = {}
    for line in open(tsv_path, encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if len(p) < 12 or p[0] != '5':
            continue
        word, left, width, top = p[11], int(p[6]), int(p[8]), int(p[7])
        if not word.strip():
            continue
        key = (p[2], p[3], p[4])
        rows.setdefault(key, {'top': top, 'words': []})
        rows[key]['words'].append(((left + width / 2) / imgw * 150, word))
    return [sorted(v['words'], key=lambda w: w[0])
            for v in sorted(rows.values(), key=lambda v: v['top'])]


def parse_vouzela(do_ocr=True):
    folder = os.path.join(SECCOES, '1824_vouzela')
    pdf = os.path.join(folder, '202505_Consulte-aqui-os-resultados.pdf')
    ocrdir = os.path.join(folder, 'ocr')
    os.makedirs(ocrdir, exist_ok=True)
    vis_path = os.path.join(ocrdir, '202505_vision.txt')
    tsv_path = os.path.join(ocrdir, '202505_tess.tsv')
    png = '/tmp/vouzela_400-1.png'
    if do_ocr and not (os.path.exists(vis_path) and os.path.exists(tsv_path)):
        ensure_ocr_tool()
        if not os.path.exists(png):
            subprocess.run(['pdftoppm', '-png', '-r', '400', pdf,
                            '/tmp/vouzela_400'], check=True)
        if not os.path.exists(vis_path):
            with open(vis_path, 'w', encoding='utf-8') as f:
                subprocess.run([OCR_BIN, png], stdout=f, check=True)
        if not os.path.exists(tsv_path):
            subprocess.run(['tesseract', png,
                            os.path.join(ocrdir, '202505'), 'tsv'],
                           check=True, stderr=subprocess.DEVNULL)

    vis_rows = parse_vision_padded(open(vis_path, encoding='utf-8').read())
    tess_lines = parse_tess_lines(tsv_path, png_width(png))

    def by_anchor(lines):
        out = [None] * len(VOUZELA_ANCHOR)
        for toks in lines:
            vals = [t for _, t in toks]
            for ai, a in enumerate(VOUZELA_ANCHOR):
                if out[ai] is None and a in vals:
                    out[ai] = toks
        return out

    vis_by_row = by_anchor(vis_rows)
    tess_by_row = by_anchor(tess_lines)

    # колоночные центры: кластеризация x всех числовых токенов обоих движков
    xs = sorted(x for toks in vis_by_row + tess_by_row if toks
                for x, t in toks if num_candidates(t))
    clusters = []
    for x in xs:
        if clusters and x - clusters[-1][-1] < 2.2:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    centers = [sum(c) / len(c) for c in clusters]
    tail = centers[-18:]
    assert len(centers) >= 18, centers
    log(f'  Vouzela OCR: колонок {len(centers)}, хвост: '
        + ' '.join(f'{c:.0f}' for c in tail))

    def nearest(x):
        best, bd = None, 9e9
        for i, c in enumerate(tail):
            if abs(x - c) < bd:
                best, bd = i, abs(x - c)
        return best if bd < 3.2 else None

    mai = mai_level3('1824')
    mai_by_name = {m['name']: m for m in mai.values()}
    rows, notes, totals_pdf = [], [], None
    for ai, name in enumerate(VOUZELA_NAMES + ['__TOTAL__']):
        cells = {}
        for eng, toks in (('V', vis_by_row[ai]), ('T', tess_by_row[ai])):
            if not toks:
                continue
            for x, t in toks:
                if not num_candidates(t):
                    continue
                si = nearest(x)
                if si is not None:
                    cells.setdefault(si, {}).setdefault(eng, set()).update(
                        num_candidates(t))

        def pick(si):
            d = cells.get(si, {})
            both = d.get('V', set()) & d.get('T', set())
            if both:
                return min(both), 'both'
            if 'V' in d and 'T' in d:
                return sorted(d['V'] | d['T'], key=lambda v: -len(v))[0], \
                    'disagree'
            if d:
                e = 'V' if 'V' in d else 'T'
                return min(d[e]), e
            return None, 'none'

        ins, vot = pick(0)[0], pick(1)[0]
        if ins is None or vot is None:
            notes.append(f'⚠ {name}: потерян якорь Insc/Vot')
            continue
        ins, vot = int(ins), int(vot)
        br, br_c = pick(3)
        nu, nu_c = pick(4)
        br, nu = int(br or 0), int(nu or 0)
        need = vot - br - nu
        votes, conf = {}, {}
        for j, p in enumerate(VOUZELA_PCOLS):
            val, c = pick(5 + j)
            votes[p] = int(val) if val is not None else 0
            conf[p] = c
        if name == '__TOTAL__':
            totals_pdf = (ins, vot, br, nu, dict(votes))
            continue
        if sum(votes.values()) != need:
            m = mai_by_name.get(name)
            if m:
                fixed = 0
                for p in VOUZELA_PCOLS:
                    if conf[p] in ('disagree', 'none'):
                        mv = int(m['votes:' + p] or 0)
                        if votes[p] != mv:
                            votes[p] = mv
                            fixed += 1
                if sum(votes.values()) == need:
                    notes.append(f'{name}: сумма сведена по MAI '
                                 f'({fixed} ячеек)')
            if sum(votes.values()) != need:
                notes.append(f'⚠ {name}: сумма {sum(votes.values())} != '
                             f'{need} (Vot−бр−нул)')
        bad = [p for p in VOUZELA_PCOLS if conf[p] in ('disagree', 'none')]
        if bad:
            notes.append(f'{name}: неоднозначные ячейки (взято '
                         + ', '.join(f'{p}={votes[p]}' for p in bad) + ')')
        nd = {'eleitores': ins, 'votantes': vot, 'brancos': br, 'nulos': nu,
              'abst': ins - vot}
        r = frow('1824', 'Vouzela', name, nd, votes)
        r['ocr'] = 'ok' if not bad else 'partial'
        rows.append(r)

    if totals_pdf:
        s = [sum(r[f] for r in rows) for f in
             ('eleitores', 'votantes', 'brancos', 'nulos')]
        sp = {p: sum(int(r['votes:' + p] or 0) for r in rows)
              for p in VOUZELA_PCOLS}
        okc = (s == list(totals_pdf[:4])
               and all(sp[p] == totals_pdf[4].get(p, -1)
                       for p in VOUZELA_PCOLS))
        log(f'  контроль TOTAIS PDF vs сумма 9 фрегезий: '
            f'{"✓" if okc else "✗"} {totals_pdf[:4]} vs {s}')
    for n in notes:
        log('    ' + n)
    return rows


# ----------------------------------------------------------- Almodôvar --

ALM_FILES = {
    'EL25_MapaDef_ADF.pdf': ('LOCAL-020208', 'Aldeia dos Fernandes'),
    'EL25_MapaDef_Rosario.pdf': ('LOCAL-020203', 'Rosário'),
    'EL25_MapaDef_SB.pdf': ('LOCAL-020206', 'São Barnabé'),
    'EL25_MapaDef_SCruz.pdf': ('LOCAL-020205', 'Santa Cruz'),
    'EL25_MapaDef_UfADVGP.pdf': ('LOCAL-020209',
                                 'Almodôvar e Graça dos Padrões'),
    'EL25_MapaDef_UfSCGA.pdf': ('LOCAL-020210',
                                'Santa Clara-a-Nova e Gomes Aires'),
}


def parse_almodovar(do_ocr=True):
    folder = os.path.join(SECCOES, '0202_almodovar')
    ocrdir = os.path.join(folder, 'ocr')
    os.makedirs(ocrdir, exist_ok=True)
    if do_ocr:
        ensure_ocr_tool()
        for fn in ALM_FILES:
            out = os.path.join(ocrdir, fn.replace('.pdf', '.txt'))
            if os.path.exists(out):
                continue
            pref = f'/tmp/alm25_{fn[:-4]}'
            subprocess.run(['pdftoppm', '-png', '-r', '200', '-f', '1',
                            '-l', '2', os.path.join(folder, fn), pref],
                           check=True)
            with open(out, 'w', encoding='utf-8') as f:
                for i in (1, 2):
                    p = f'{pref}-{i}.png'
                    if not os.path.exists(p):
                        continue
                    r = subprocess.run([OCR_BIN, p], capture_output=True,
                                       text=True, check=True)
                    f.write(f'=== {fn} стр.{i} ===\n{r.stdout}\n')
    rows = []
    for fn, (key, freg) in ALM_FILES.items():
        txt = open(os.path.join(ocrdir, fn.replace('.pdf', '.txt')),
                   encoding='utf-8').read()
        cur = None
        for line in txt.splitlines():
            s = line.strip()
            s = re.sub(r'^[-–—•.\s]+', '', s)
            s = re.sub(r'[-–—•.\s]+$', '', s).strip()
            m = re.search(r'(?:Assembleia|Sec[çc][ãa]o) de voto '
                          r'n\.?\s*[oº°]?\s*(\d+)', s, re.I)
            if m:
                cur = int(m.group(1))
                loc = re.sub(r'(?:Assembleia|Sec[çc][ãa]o) de voto '
                             r'n\.?\s*[oº°]?\s*\d+', '', s,
                             flags=re.I).strip(' -.')
                rows.append({'dico': '0202', 'concelho': 'Almodôvar',
                             'mai_key': key, 'freguesia': freg,
                             'assembleia_secção': cur, 'local': loc})
            elif cur and re.match(r'(Escola|Edif[íi]cio|Junta|Sala|Centro|'
                                  r'Delega[çc][ãa]o|Antiga|Largo|Sal[ãa]o)',
                                  s, re.I):
                rows[-1]['local'] = (rows[-1]['local'] + ' ' + s).strip()
    return rows


def write_almodovar(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['dico', 'concelho', 'mai_key',
                                          'freguesia', 'assembleia_secção',
                                          'local'])
        w.writeheader()
        w.writerows(rows)
    log(f'  -> {os.path.relpath(path, SECCOES)}: {len(rows)} строк')


# ------------------------------------------------------------------ main --

def main():
    do_ocr = '--no-ocr' not in sys.argv
    log('=== AR-2025: парсинг PDF по папкам + сверка с MAI ===')
    log()

    log('--- Секционные данные (парсеры parse_seccoes_ar2025) ---')
    jobs = [
        ('1405_benavente', base.parse_benavente),
        ('1501_alcacerdosal', base.parse_alcacer),
        ('0703_borba', base.parse_borba),
        ('0712_vendasnovas', base.parse_vendasnovas),
        ('1215_sousel', base.parse_sousel),
    ]
    allsec = []
    for folder, fn_parse in jobs:
        rows = fn_parse()
        allsec += rows
        write_csv(os.path.join(SECCOES, folder, 'ar2025_seccoes.csv'), rows)
    ferr, _ = base.parse_ferreira()
    allsec += ferr
    write_csv(os.path.join(SECCOES, '0208_ferreiradoalentejo',
                           'ar2025_seccoes.csv'), ferr)

    log()
    log('--- Сверка секций с MAI (агрегаты фрегезий) ---')
    from collections import defaultdict
    agg = defaultdict(lambda: defaultdict(int))
    for r in allsec:
        a = agg[r['mai_key']]
        for f in ('eleitores', 'votantes', 'brancos', 'nulos'):
            a[f] += r[f]
        for p in base.PARTIES:
            a['votes:' + p] += int(r['votes:' + p] or 0)
    mai = base.mai_rows()
    for key, a in sorted(agg.items()):
        m = mai[key]
        diffs = [f'{f}: pdf={a[f]} mai={int(m[MF.get(f, f)] or 0)}'
                 for f in ('eleitores', 'votantes', 'brancos', 'nulos')
                 + tuple('votes:' + p for p in base.PARTIES)
                 if a[f] != int(m[MF.get(f, f)] or 0)]
        (log(f'  ✗ {key} {m["name"]}: ' + '; '.join(diffs)) if diffs
         else log(f'  ✓ {key} {m["name"]}'))

    log()
    log('--- Gouveia (фрегезии = секции, независимая транскрипция) ---')
    gouv = base.parse_gouveia()
    gmai = mai_level3('0906')
    used = set()
    for g in gouv:
        hint = g.pop('name_hint', '')
        hits = [k for k, m in gmai.items() if k not in used
                and int(m['registered_voters']) == g['eleitores']
                and int(m['voted']) == g['votantes']]
        if len(hits) == 1:
            k = hits[0]
            used.add(k)
            g['mai_key'], g['freguesia'], g['pdf_nome'] = k, gmai[k]['name'], hint
            diffs = [f'{f}: g={g[f]} mai={int(gmai[k][MF.get(f, f)] or 0)}'
                     for f in ('brancos', 'nulos')
                     + tuple('votes:' + p for p in base.PARTIES)
                     if int(g.get(f, 0) or 0) != int(gmai[k][MF.get(f, f)] or 0)]
            (log(f'  ✗ {gmai[k]["name"]}: ' + '; '.join(diffs)) if diffs
             else log(f'  ✓ {gmai[k]["name"]}'))
        else:
            log(f'  ✗ Gouveia: нет уникальной пары MAI для {hint!r}')
    log(f'  MAI фрегезий: {len(gmai)}, сопоставлено: {len(used)}')
    write_csv(os.path.join(SECCOES, '0906_gouveia', 'ar2025_freguesias.csv'),
              gouv, extra=('pdf_nome',))

    log()
    log('--- Almeida (фрегезии + секции Vilar Formoso) ---')
    alm_rows, alm_secs = parse_almeida()
    match_and_check(alm_rows, '0902', 'Almeida')
    write_csv(os.path.join(SECCOES, '0902_almeida',
                           'ar2025_freguesias_e_seccoes.csv'),
              alm_rows + alm_secs, extra=('pdf_nome',))

    log()
    log('--- Amarante (фрегезии) ---')
    am_rows = parse_amarante()
    match_and_check(am_rows, '1301', 'Amarante')
    write_csv(os.path.join(SECCOES, '1301_amarante', 'ar2025_freguesias.csv'),
              am_rows, extra=('pdf_nome',))

    log()
    log('--- Valença (фрегезии) ---')
    val_rows = parse_valenca()
    match_and_check(val_rows, '1601' if False else '1608', 'Valença')
    write_csv(os.path.join(SECCOES, '1608_valenca', 'ar2025_freguesias.csv'),
              val_rows, extra=('pdf_nome',))

    log()
    log('--- Vouzela (скан: Apple Vision + tesseract OCR) ---')
    vou_rows = parse_vouzela(do_ocr)
    match_and_check(vou_rows, '1824', 'Vouzela')
    write_csv(os.path.join(SECCOES, '1824_vouzela',
                           'ar2025_freguesias_ocr.csv'), vou_rows,
              extra=('pdf_nome', 'ocr'))

    log()
    log('--- Almodôvar (EL25: эдиталы участков, результатов нет) ---')
    alm25 = parse_almodovar(do_ocr)
    write_almodovar(os.path.join(SECCOES, '0202_almodovar',
                                 'ar2025_locais_voto.csv'), alm25)
    for r in alm25:
        log(f'  {r["freguesia"]}: n.º {r["assembleia_secção"]} — '
            f'{r["local"] or "?"}')

    out = os.path.join(SECCOES, 'ar2025_pdfs_validation.txt')
    open(out, 'w', encoding='utf-8').write('\n'.join(LOG) + '\n')
    print(f'\nлог сверки -> {out}')


if __name__ == '__main__':
    main()
