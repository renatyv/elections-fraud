#!/usr/bin/env python3
"""Пересборка data/seccoes/catalog.csv по актуальным правилам тиров.

После смены правил pdf_tier() часть скачанных файлов оказывается тиром B
(организация выборов, не результаты): их удаляем, реестр переписываем.
Запуск: python3 scripts/recatalog_seccoes.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crawl_election_pages import pdf_tier, norm_url, SECCOES_DIR, CATALOG_CSV


def main():
    if not os.path.exists(CATALOG_CSV):
        sys.exit('нет catalog.csv')
    rows = list(csv.DictReader(open(CATALOG_CSV, encoding='utf-8')))
    kept, removed = [], []
    for r in rows:
        tier = pdf_tier(r['pdf_url'])
        junk_kw = ('2014', 'op2014', 'folheto', 'atestado', 'designacao',
                   'mapa-calendario', 'locais-de-voto', 'pr5-', 'al6-',
                   'mapa-de-pessoal', 'informacao-mapa-de-pessoal',
                   'orcamento-participativo', 'siadap', 'comissaoparitaria',
                   'como-votar', 'trimestre', 'mapatransportes',
                   'desdobramentoassembleias', 'mapa-assembleias',
                   'assembleias-e-seccoes-de-voto', 'mapadasassembleias',
                   'horarios.funcionamento', 'resultado-eleitoral-para')
        u = norm_url(r['pdf_url'])
        # вручную выверенные мимо: старые выборы/листовки/места голосования
        manual_junk = ('1105_cascais/resultados-concelho-de-cascais-parlamento',
                       '1105_cascais/op2014')
        if tier != 'A' or any(k in u for k in junk_kw) or any(m in u for m in manual_junk):
            if r['local_path'] and os.path.exists(r['local_path']):
                os.remove(r['local_path'])
                removed.append(r['local_path'])
            continue
        r['tier'] = tier
        kept.append(r)

    # подчистить пустые каталоги конселью
    for d in os.listdir(SECCOES_DIR):
        p = os.path.join(SECCOES_DIR, d)
        if os.path.isdir(p) and not os.listdir(p) and d != 'crawl':
            os.rmdir(p)

    with open(CATALOG_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['dico', 'name', 'site', 'tier',
                                          'pdf_url', 'local_path', 'bytes',
                                          'status', 'fetched_at'])
        w.writeheader()
        w.writerows(kept)
    print(f'оставлено {len(kept)}, удалено файлов {len(removed)}')
    for p in removed:
        print('  rm', os.path.basename(p))


if __name__ == '__main__':
    main()
