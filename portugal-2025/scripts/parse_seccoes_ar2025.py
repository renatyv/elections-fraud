#!/usr/bin/env python3
"""Parse AR-2025 section-level PDFs into a single CSV + cross-check against MAI (freguesias).

Sources are the confirmed section publishers (see data/seccoes/PUBLISHER_CATALOG.md):
  1405 Benavente, 1501 Alcácer do Sal, 0703 Borba, 0712 Vendas Novas,
  0208 Ferreira do Alentejo (scan with a text layer), 0906 Gouveia (sections=parishes).
Output: data/seccoes/ar2025_seccoes.csv; the cross-check is printed to stdout and
data/seccoes/ar2025_seccoes_validation.txt.

Run: python3 scripts/parse_seccoes_ar2025.py
"""
import csv
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECCOES = os.path.join(BASE, 'data', 'seccoes')
MAI_CSV = os.path.join(BASE, 'data', 'legislativas2025_mai', 'results_all.csv')
OUT_CSV = os.path.join(SECCOES, 'ar2025_seccoes.csv')
OUT_VAL = os.path.join(SECCOES, 'ar2025_seccoes_validation.txt')

# party order as in the MAI results_all.csv
PARTIES = ['PPD/PSD.CDS-PP', 'PS', 'CH', 'IL', 'L', 'PCP-PEV', 'B.E.', 'PAN',
           'ADN', 'PPD/PSD.CDS-PP.PPM', 'JPP', 'R.I.R.', 'VP', 'PCTP/MRPP',
           'ND', 'E', 'PLS', 'PPM', 'NC', 'MPT', 'PTP']

TXT = '/tmp/seccoes_txt'

def pdf2txt(rel):
    pdf = os.path.join(SECCOES, rel)
    out = os.path.join(TXT, rel.replace('/', '_') + '.txt')
    os.makedirs(TXT, exist_ok=True)
    if not os.path.exists(out):
        subprocess.run(['pdftotext', '-layout', pdf, out], check=True)
    return out

def is_pct(t):
    return '%' in t or re.fullmatch(r'\d+,\d+', t) is not None

def to_int(t):
    return int(t.replace('O', '0').replace('o', '0').replace(' ', ''))

def merge_thousands(tokens):
    """'2 964' -> '2964' (iteratively, left to right)."""
    out = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and re.fullmatch(r'\d+', tokens[i]) \
                and re.fullmatch(r'\d{3}', tokens[i + 1]):
            tokens[i + 1] = tokens[i] + tokens[i + 1]
        else:
            out.append(tokens[i])
        i += 1
    return out


def split_cols(line, drop_pct=True):
    """Columns = 2+ spaces (pdftotext -layout). Inside a cell the numbers may
    be single-space separated; 'N NNN' (up to 2 digits + exactly 3) is a
    thousands separator."""
    s = re.sub(r'\d+,\d+', ' ', line) if drop_pct else line
    cols = []
    for c in re.split(r'\s{2,}', s.strip()):
        c = c.replace('º', '')
        if re.fullmatch(r'[O\d ]*[O\d]', c):
            c = c.replace('O', '0')
        if re.fullmatch(r'[\d ]*\d', c):
            parts = c.split()
            merged = []
            i = 0
            while i < len(parts):
                if i + 1 < len(parts) and len(parts[i]) <= 2 \
                        and len(parts[i + 1]) == 3:
                    parts[i + 1] = parts[i] + parts[i + 1]
                else:
                    merged.append(parts[i])
                i += 1
            cols.extend(str(int(p)) for p in merged)
        elif any(ch.isdigit() for ch in c):
            # mixed cell such as 'Orada 550': numbers and text split into parts
            for part in re.findall(r'\d+|[A-Za-zÀ-ÿ./-]+[^\d]*', c):
                part = part.strip()
                if part.isdigit():
                    cols.append(str(int(part)))
                elif part:
                    cols.append(part)
        else:
            cols.append(c)
    return cols

def row(dico, concelho, mai_key, freg, nivel, secao, local, nums, votes):
    return {'dico': dico, 'concelho': concelho, 'mai_key': mai_key,
            'freguesia': freg, 'nivel': nivel, 'secao': secao, 'local': local,
            'eleitores': nums['eleitores'], 'votantes': nums['votantes'],
            'brancos': nums['brancos'], 'nulos': nums['nulos'],
            'abst': nums.get('abst', ''),
            **{f'votes:{p}': votes.get(p, 0) for p in PARTIES}}


def parse_benavente():
    """Two blocks: (CH,PPM,ADN,E,AD,PAN) and (BE,RIR,VP,PS,L,PCP,IL,+abst)."""
    txt = pdf2txt('1405_benavente/Legislativas2025-resultados.pdf')
    fregs = [('LOCAL-140501', 'Benavente', 9),
             ('LOCAL-140502', 'Samora Correia', 14),
             ('LOCAL-140503', 'Santo Estêvão', 3),
             ('LOCAL-140504', 'Barrosa', 1)]
    data, fi, prev_sec = {}, 0, None
    blocks = {'b1': ['CH', 'PPM', 'ADN', 'E', 'PPD/PSD.CDS-PP', 'PAN'],
              'b2': ['B.E.', 'R.I.R.', 'VP', 'PS', 'L', 'PCP-PEV', 'IL']}
    block = 'b1'
    for line in open(txt, encoding='utf-8'):
        toks = line.split()
        if not toks:
            continue
        if 'Secções' in line and 'B.E.' in line:
            block = 'b2'; fi, prev_sec = 0, None
            continue
        if toks[0] in ('Sm', 'Concelho', 'Freg.', 'N.º', 'Abstenção', 'Eleit.',
                       'PAN', 'PCP-PEV'):
            continue
        while toks and toks[0].isalpha() and len(toks) > 1:
            toks = toks[1:]  # FC/PA/FA and vertical freguesia names
        if not toks or not toks[0].isdigit():
            continue
        if not toks[0].isdigit():
            continue
        nums = [t for t in toks if not is_pct(t)]
        if len(nums) < 4:
            continue
        sec = int(nums[0])
        if sec == 1 and prev_sec is not None and prev_sec >= 1:
            fi += 1
        prev_sec = sec
        key, fname, _ = fregs[fi] if fi < len(fregs) else (None, None, None)
        if key is None:
            raise ValueError(f'benavente: unexpected section {sec}')
        d = data.setdefault((fi, sec), {'local': '', 'b1': {}, 'b2': {}})
        if block == 'b1':
            # sec eleit voted blank null + 6 parties
            assert len(nums) == 11, (sec, nums)
            d.update(secao=sec, eleitores=int(nums[1]), votantes=int(nums[2]),
                     brancos=int(nums[3]), nulos=int(nums[4]))
            for p, v in zip(blocks['b1'], nums[5:11]):
                d['b1'][p] = int(v)
        else:
            assert len(nums) == 10, (sec, nums)
            d['secao'] = sec
            d.setdefault('eleitores', int(nums[1]))
            for p, v in zip(blocks['b2'], nums[2:9]):
                d['b2'][p] = int(v)
            d['abst'] = int(nums[9])
    rows = []
    for (fi, sec), d in sorted(data.items()):
        votes = {**d['b1'], **d['b2']}
        nums = {'eleitores': d['eleitores'], 'votantes': d['votantes'],
                'brancos': d['brancos'], 'nulos': d['nulos'], 'abst': d.get('abst')}
        rows.append(row('1405', 'Benavente', fregs[fi][0], fregs[fi][1], 'secao',
                        sec, d.get('local', ''), nums, votes))
    assert len(rows) == 27, len(rows)
    return rows


def parse_alcacer():
    txt = pdf2txt('1501_alcacerdosal/LEGISLATIVAS-2025-Resultados-no-concelho-de-Alcacer-do-Sal.pdf')
    cols = ['PCP-PEV', 'VP', 'L', 'PPD/PSD.CDS-PP', 'R.I.R.', 'NC', 'PPM',
            'ADN', 'PLS', 'E', 'B.E.', 'PCTP/MRPP', 'PS', 'JPP', 'IL', 'ND',
            'PAN', 'CH']
    freg = None
    fregs = {'UNIÃO': ('LOCAL-150107', 'Uf Alcácer do Sal (SM Castelo e Santiago) e Santa Susana'),
             'TORRÃO': ('LOCAL-150104', 'Torrão'),
             'COMPORTA': ('LOCAL-150106', 'Comporta'),
             'SÃO MARTINHO': ('LOCAL-150105', 'São Martinho')}
    rows = []
    for line in open(txt, encoding='utf-8'):
        s = line.strip()
        up = s.upper()
        if up.startswith('TOTAL'):
            continue
        hit = next((v for k, v in fregs.items() if up.startswith(k) and len(up) < 90), None)
        if hit and not s[0].isdigit():
            freg = hit
            continue
        if freg is None or not s or not s[0].isdigit():
            continue
        toks = s.split()
        i = next(j for j, t in enumerate(toks) if t.isdigit() and j > 0)
        sec = int(toks[0])
        local = ' '.join(toks[1:i])
        inscr = int(toks[i])
        rest = [t for t in toks[i + 1:] if not is_pct(t)]
        # 18 parties + total + brc + nulos + urna + abst
        assert len(rest) == 23, (sec, rest)
        votes = dict(zip(cols, map(int, rest[:18])))
        nums = {'eleitores': inscr, 'votantes': int(rest[21]),
                'brancos': int(rest[19]), 'nulos': int(rest[20]),
                'abst': None}
        assert sum(votes.values()) == int(rest[18])
        rows.append(row('1501', 'Alcácer do Sal', freg[0], freg[1], 'secao',
                        sec, local, nums, votes))
    assert len(rows) == 21, len(rows)
    return rows


def parse_borba():
    txt = pdf2txt('0703_borba/Eleicoes-Legislativas-2025-Votacao-no-concelho-de-Borba.pdf')
    cols = ['NC', 'PAN', 'IL', 'PS', 'B.E.', 'L', 'VP', 'E', 'PCP-PEV', 'CH',
            'PPM', 'ADN', 'R.I.R.', 'PPD/PSD.CDS-PP']
    plan = [('LOCAL-070301', 'Borba (Matriz)')] * 3 + \
           [('LOCAL-070304', 'Borba (São Bartolomeu)')] + \
           [('LOCAL-070303', 'Rio de Moinhos')] * 3 + \
           [('LOCAL-070302', 'Orada')]
    rows, k = [], 0
    for line in open(txt, encoding='utf-8'):
        s = line.strip()
        if not s or s.startswith('Total'):
            continue
        cells = split_cols(line)
        nums = [c for c in cells if c.isdigit()]
        if len(nums) == 21 and 1 <= int(nums[0]) <= 9:
            sec, rest = int(nums[0]), nums[1:]
        elif len(nums) == 20:
            sec, rest = 1, nums
        else:
            continue
        # eleit voted abst blank null apurados + 14 parties
        assert len(rest) == 20, rest
        votes = dict(zip(cols, map(int, rest[6:])))
        nums_d = {'eleitores': int(rest[0]), 'votantes': int(rest[1]),
                  'brancos': int(rest[3]), 'nulos': int(rest[4]),
                  'abst': int(rest[2])}
        assert sum(votes.values()) == int(rest[5]), rest
        assert nums_d['brancos'] + nums_d['nulos'] + int(rest[5]) == nums_d['votantes']
        mai_key, fname = plan[k]
        rows.append(row('0703', 'Borba', mai_key, fname, 'secao', sec, '',
                        nums_d, votes))
        k += 1
    assert k == 8, k
    return rows


def parse_vendasnovas():
    txt = pdf2txt('0712_vendasnovas/Legislativas-2025-Resultados-Provisorios.pdf')
    cols = ['NC', 'PAN', 'IL', 'PS', 'B.E.', 'L', 'VP', 'E', 'PCP-PEV', 'CH',
            'PPM', 'ADN', 'R.I.R.', 'PPD/PSD.CDS-PP']
    rows = []
    freg_banner = 0  # 0: sections 1-15; 1: VN freguesia total; 2: Landeira row
    for line in open(txt, encoding='utf-8'):
        s = line.strip()
        if not s:
            continue
        toks = [t for t in s.split() if not is_pct(t)]
        if not any(t[0].isdigit() for t in toks):
            if 'FREGUESIA' in s.upper():
                freg_banner += 1
            continue
        if s.upper().startswith('CONCELHO'):
            continue
        while toks and not toks[0].isdigit():
            toks = toks[1:]  # place name (Piçarras, Bombel, …)
        if freg_banner == 0 and len(toks) == 20:
            sec = int(toks[0])
            votes = dict(zip(cols, map(int, toks[1:15])))
            nums = {'eleitores': int(toks[19]), 'votantes': int(toks[17]),
                    'brancos': int(toks[15]), 'nulos': int(toks[16]),
                    'abst': int(toks[18])}
            mai_key, fname = 'LOCAL-071201', 'Vendas Novas'
        elif freg_banner == 2 and len(toks) == 19:
            sec = 1
            votes = dict(zip(cols, map(int, toks[0:14])))
            nums = {'eleitores': int(toks[18]), 'votantes': int(toks[16]),
                    'brancos': int(toks[14]), 'nulos': int(toks[15]),
                    'abst': int(toks[17])}
            mai_key, fname = 'LOCAL-071202', 'Landeira'
        else:
            continue
        assert sum(votes.values()) + nums['brancos'] + nums['nulos'] == nums['votantes'], sec
        rows.append(row('0712', 'Vendas Novas', mai_key, fname, 'secao', sec,
                        '', nums, votes))
    assert len(rows) == 16, len(rows)
    return rows


def parse_ferreira():
    """Scan with a text layer ('resultadoscorrigidos'); the column order was
    established by cross-checking the totals against MAI: mesa, inscr, voted,
    abst, brancos, nulos, RIR, B.E., PCP-PEV, L, PS, IL, PPM, AD, VP, E, CH,
    PAN, PCTP/MRPP, ND, ADN."""
    txt = pdf2txt('0208_ferreiradoalentejo/resultadoscorrigidos.pdf')
    cols = ['R.I.R.', 'B.E.', 'PCP-PEV', 'L', 'PS', 'IL', 'PPM',
            'PPD/PSD.CDS-PP', 'VP', 'E', 'CH', 'PAN', 'PCTP/MRPP', 'ND', 'ADN']
    groups = [('LOCAL-020807', 'Alfundão e Peroguarda', 2),
              ('LOCAL-020808', 'Ferreira do Alentejo e Canhestros', 9),
              ('LOCAL-020803', 'Figueira dos Cavaleiros', 2),
              ('LOCAL-020804', 'Odivelas', 1)]
    rows, g, seen_in_g = [], 0, 0
    totals_concelho = None
    for line in open(txt, encoding='utf-8'):
        if 'RESULTADOSGERAIS' in line:
            cells = split_cols(re.sub(r'\d+,\d+%', ' ', line))
            nums = [int(c) for c in cells if c.isdigit()]
            # [number of mesas, inscr, voted, abst, 17 values]
            totals_concelho = nums[1:]
            continue
        if 'TOTAL' in line or '%' in line or 'Percentagem' in line \
                or 'EDITAL' in line or 'LISTAS' in line:
            continue
        cells = split_cols(re.sub(r'\d+,\d+%', ' ', line))
        nums = [int(c) for c in cells if c.isdigit()]
        if len(nums) < 21:
            continue
        # place names containing digits ('5 VARGARIDA', 'OLI-1AS') produce
        # phantom numbers on the left — take the 21 rightmost values
        nums = nums[-21:]
        mesa, inscr, voted, abst = nums[0], nums[1], nums[2], nums[3]
        blank, null = nums[4], nums[5]
        votes = dict(zip(cols, nums[6:]))
        if sum(votes.values()) + blank + null != voted:
            continue
        if inscr != voted + abst and str(voted + abst).startswith(str(inscr)):
            inscr = voted + abst  # mangled electorate digit (mesa 6: '15'->156)
        if seen_in_g >= groups[g][2]:
            g += 1
            seen_in_g = 0
        mai_key, fname, _ = groups[g]
        nums_d = {'eleitores': inscr, 'votantes': voted, 'brancos': blank,
                  'nulos': null, 'abst': abst}
        rows.append(row('0208', 'Ferreira do Alentejo', mai_key, fname,
                        'secao', mesa, '', nums_d, votes))
        seen_in_g += 1
    assert len(rows) == 14, len(rows)
    return rows, totals_concelho


def parse_gouveia():
    """Sections = parishes (same level as MAI), but this is an independent
    transcription of the municipality — MAI is the control. Columns: BE PPM IL PS NC VP RIR E CH ADN L AD PCP PAN."""
    txt = pdf2txt('0906_gouveia/Legislativas-AR-2025-Apuramento-Parcial-Seccoes.pdf')
    cols = ['B.E.', 'PPM', 'IL', 'PS', 'NC', 'VP', 'R.I.R.', 'E', 'CH', 'ADN',
            'L', 'PPD/PSD.CDS-PP', 'PCP-PEV', 'PAN']
    rows = []
    pending_name = ''
    for line in open(txt, encoding='utf-8'):
        s = line.strip()
        if not s or s.startswith(('Totais', 'Votantes', 'Abstenção', 'ELEIÇÕES',
                                  '18 de maio', 'Resultado do', 'PPD/PSD',
                                  'Inscritos')):
            continue
        cells = split_cols(line, drop_pct=False)
        nums = [int(c) for c in cells if c.isdigit()]
        if len(nums) == 18:
            inscr, voted, blank, null = nums[:4]
            votes = dict(zip(cols, nums[4:]))
            nums_d = {'eleitores': inscr, 'votantes': voted, 'brancos': blank,
                      'nulos': null, 'abst': inscr - voted}
            rows.append({'name_hint': pending_name.strip(),
                         **row('0906', 'Gouveia', '', '', 'freguesia', '', '',
                               nums_d, votes)})
            pending_name = ''
        elif not nums:
            pending_name += ' ' + s
    assert len(rows) == 16, len(rows)
    return rows


def parse_sousel():
    """Scan without a text layer (the table is an image from SIC). Transcribed
    by a vision model: data/seccoes/1215_sousel/ar2025_sousel_ocr.csv; every
    row was verified against MAI (see the validation output)."""
    path = os.path.join(SECCOES, '1215_sousel', 'ar2025_sousel_ocr.csv')
    rows = []
    for r in csv.DictReader(open(path, encoding='utf-8')):
        votes = {p: int(r['votes:' + p] or 0) for p in PARTIES if 'votes:' + p in r}
        nums = {'eleitores': int(r['eleitores']), 'votantes': int(r['votantes']),
                'brancos': int(r['brancos']), 'nulos': int(r['nulos']),
                'abst': int(r['abst'])}
        assert sum(votes.values()) + nums['brancos'] + nums['nulos'] == nums['votantes']
        rows.append(row(r['dico'], r['concelho'], r['mai_key'], r['freguesia'],
                        'secao', int(r['secao']), 'OCR', nums, votes))
    assert len(rows) == 5, len(rows)
    return rows


def mai_rows():
    out = {}
    for r in csv.DictReader(open(MAI_CSV, encoding='utf-8-sig')):
        key = r['key']
        out[key] = r
    return out


def main():
    rows = []
    rows += parse_benavente()
    rows += parse_alcacer()
    rows += parse_borba()
    rows += parse_vendasnovas()
    ferr, ferr_tot = parse_ferreira()
    rows += ferr
    rows += parse_sousel()
    gouv = parse_gouveia()
    mai = mai_rows()

    # cross-check of section sums against MAI at freguesia level
    log = []
    log.append('=== Cross-check of section sums against MAI (results_all.csv AR-2025) ===')
    bad = 0
    from collections import defaultdict
    agg = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r['nivel'] != 'secao':
            continue
        a = agg[r['mai_key']]
        a['eleitores'] += r['eleitores']
        a['votantes'] += r['votantes']
        a['brancos'] += r['brancos']
        a['nulos'] += r['nulos']
        for p in PARTIES:
            a['votes:' + p] += int(r['votes:' + p] or 0)
    MFIELD = {'eleitores': 'registered_voters', 'votantes': 'voted',
              'brancos': 'blank_votes', 'nulos': 'null_votes'}
    for key, a in sorted(agg.items()):
        m = mai[key]
        diffs = []
        for f in ('eleitores', 'votantes', 'brancos', 'nulos') + \
                 tuple('votes:' + p for p in PARTIES):
            mv = int(m[MFIELD.get(f, f)] or 0)
            if a[f] != mv:
                diffs.append(f'{f}: pdf={a[f]} mai={mv}')
        nm = m['name']
        if diffs:
            bad += 1
            log.append(f'✗ {key} {nm}: ' + '; '.join(diffs))
        else:
            log.append(f'✓ {key} {nm}: {a["eleitores"]} voters, {a["votantes"]} voted.')
    # Gouveia: row by row
    log.append('')
    log.append('=== Gouveia (independent transcription by the camara, freguesia level) ===')
    gmai = {k: v for k, v in mai.items() if k.startswith('LOCAL-0906') and v['level'] == '3'}
    matched = set()
    for g in gouv:
        hit = None
        for k, m in gmai.items():
            if int(m['registered_voters']) == g['eleitores'] and \
               int(m['voted']) == g['votantes']:
                hit = (k, m)
                break
        if not hit:
            log.append(f'✗ no MAI match found for {g["name_hint"]!r} '
                       f'({g["eleitores"]} voters)')
            bad += 1
            continue
        k, m = hit
        matched.add(k)
        g['mai_key'] = k
        g['freguesia'] = m['name']
        diffs = []
        for f in ('brancos', 'nulos') + tuple('votes:' + p for p in PARTIES):
            mv = int(m[MFIELD.get(f, f)] or 0)
            gv = int(g[f] or 0)
            if gv != mv:
                diffs.append(f'{f}: gouveia={gv} mai={mv}')
        if diffs:
            bad += 1
            log.append(f'✗ {m["name"]}: ' + '; '.join(diffs))
        else:
            log.append(f'✓ {m["name"]}: {g["eleitores"]} voters')
    if len(matched) != len(gmai):
        bad += 1
        log.append(f'✗ MAI parishes: {len(gmai)}, matched {len(matched)}')

    # Ferreira: cross-check of the "RESULTADOSGERAIS" total row
    log.append('')
    log.append('=== Ferreira do Alentejo: RESULTADOSGERAIS row vs MAI ===')
    m = mai['LOCAL-020800']
    ferr_cols = ['R.I.R.', 'B.E.', 'PCP-PEV', 'L', 'PS', 'IL', 'PPM',
                 'PPD/PSD.CDS-PP', 'VP', 'E', 'CH', 'PAN', 'PCTP/MRPP',
                 'ND', 'ADN']
    ferr_map = dict(zip(['brancos', 'nulos'] + ferr_cols, ferr_tot[3:]))
    log.append(f"PDF total: inscr={ferr_tot[0]} voted={ferr_tot[1]} "
               f"abst={ferr_tot[2]}; MAI: {m['registered_voters']}/{m['voted']}")
    ferr_diffs = []
    for f, mv in [('brancos', m['blank_votes']), ('nulos', m['null_votes'])] + \
            [(p, m['votes:' + p]) for p in PARTIES]:
        mv = int(mv or 0)
        gv = ferr_map.get(f, 0)
        if gv != mv:
            ferr_diffs.append(f'  ✗ {f}: pdf={gv} mai={mv}')
    log.extend(ferr_diffs or ['  ✓ all parties and blank/null votes match'])

    # overall coverage
    secs = [r for r in rows if r['nivel'] == 'secao']
    nat = int(mai['LOCAL-500000']['registered_voters'])
    log.append('')
    log.append('=== Coverage ===')
    el = sum(r['eleitores'] for r in secs)
    ncon = len(set(r['dico'] for r in secs))
    log.append(f"section rows: {len(secs)} in {ncon} concelhos; electorate "
               f"{el} of {nat} national ({100 * el / nat:.2f}%)")
    turn = [r['votantes'] / r['eleitores'] for r in secs if r['eleitores']]
    log.append(f"turnout across sections: {min(turn) * 100:.1f}%–{max(turn) * 100:.1f}% "
               f"(median {sorted(turn)[len(turn) // 2] * 100:.1f}%)")
    for d in sorted(set(r['dico'] for r in secs)):
        sub = [r for r in secs if r['dico'] == d]
        log.append(f"  {d} {sub[0]['concelho']}: {len(sub)} sections, "
                   f"{sum(r['eleitores'] for r in sub)} voters")

    for g in gouv:
        g.pop('name_hint', None)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows + gouv)
    val = '\n'.join(log)
    open(OUT_VAL, 'w', encoding='utf-8').write(val + '\n')
    print(val)
    print(f'\nwrote {len(rows) + len(gouv)} rows -> {OUT_CSV}')
    print('mismatches vs MAI (groups):', bad)


if __name__ == '__main__':
    main()
