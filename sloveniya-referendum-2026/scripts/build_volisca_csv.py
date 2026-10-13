#!/usr/bin/env python3
"""Сводный CSV по участкам всех четырёх референдумов + сверка сумм.

Читает data/latest/<референдум>/volisca_*.json (88 файлов на референдум,
итоги по каждому участку) и rezultati.json/udelezba.json (агрегаты),
строит data/derived/volisca_all.csv (строка = участок × референдум) и
data/derived/nacionalni_pregled.csv (страна / единицы / округа), сверяет
суммы по участкам с агрегатами DVK (округа, единицы, страна).

DVK предупреждает: суммы по единицам могут не сходиться с национальным
итогом (голоса за рубежом, по почте и на спецучастках OMNIA считаются
отдельно) — расхождения фиксируем, а не исправляем.
"""

import csv
import json
import sys
from pathlib import Path

from sloref.config import REFERENDUMS, data_dir

OUT_DIR = data_dir() / "derived"

VOLISCA_HEADER = [
    "referendum", "enota_st", "enota_naz", "okraj_rpeid", "okraj_naz",
    "volisce_st", "volisce_rpeid", "volisce_naz",
    "upr", "gl", "udelezba_prc",          # явка: избирателей, голосовавших, доля
    "glas", "velj", "nev",                # бюллетени, действительные, недействительные
    "za", "za_prc", "proti", "proti_prc", # голоса ЗА/ПРОТИ и доли
    "prestetih_glasov",                   # доля посчитанных бюллетеней (1.0 = все)
    "datum", "timestamp", "is_final",
]

NACIONALNI_HEADER = [
    "referendum", "nivo", "enota_st", "enota_naz", "okraj_rpeid", "okraj_naz",
    "upr", "gl", "prc", "glas", "velj", "nev", "za", "za_prc", "proti", "proti_prc",
    "datum",
]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def volisca_rows(key: str, slug: str, latest: Path):
    rows = []
    for path in sorted(latest.glob("volisca_*.json")):
        data = load_json(path)
        for vol in data.get("vol") or []:
            rez = vol.get("rez") or {}
            rezlist = {r["st"]: r for r in rez.get("rez") or []}
            udel = vol.get("udel") or {}
            za, proti = rezlist.get(1, {}), rezlist.get(0, {})
            nast = data.get("nastavitve") or {}
            rows.append({
                "referendum": key,
                "enota_st": data.get("en_st"),
                "enota_naz": data.get("en_naz"),
                "okraj_rpeid": data.get("rpeid"),
                "okraj_naz": data.get("naz"),
                "volisce_st": vol.get("st"),
                "volisce_rpeid": vol.get("rpeid"),
                "volisce_naz": vol.get("naz"),
                "upr": udel.get("upr"),
                "gl": udel.get("gl"),
                "udelezba_prc": udel.get("prc"),
                "glas": rez.get("glas"),
                "velj": rez.get("velj"),
                "nev": rez.get("nev"),
                "za": za.get("gl"),
                "za_prc": za.get("prc"),
                "proti": proti.get("gl"),
                "proti_prc": proti.get("prc"),
                "prestetih_glasov": vol.get("prestetih_glasov"),
                "datum": nast.get("datum"),
                "timestamp": nast.get("timestamp"),
                "is_final": nast.get("is_final"),
            })
    return rows


def nacionalni_rows(key: str, latest: Path):
    rez = load_json(latest / "rezultati.json")
    udel = load_json(latest / "udelezba.json")
    datum = rez.get("datum")
    rows = []

    def rez_pairs(rlist):
        d = {r["st"]: r for r in rlist or []}
        return (d.get(1, {}).get("gl"), d.get(1, {}).get("prc"),
                d.get(0, {}).get("gl"), d.get(0, {}).get("prc"))

    # уровень: slovenija (итог по стране; udelezba.glas != rezultati.glas:
    # в явке учитываются все голосовавшие, включая бюллетени без ответа?)
    s_rez = rez.get("slovenija") or []
    za, za_prc, proti, proti_prc = rez_pairs(s_rez)
    su = udel.get("slovenija") or {}
    rows.append({"referendum": key, "nivo": "slovenija", "datum": datum,
                 "upr": su.get("upr"), "gl": su.get("gl"), "prc": su.get("prc"),
                 "glas": rez.get("glas"), "velj": rez.get("velj"),
                 "nev": rez.get("nev"), "za": za, "za_prc": za_prc,
                 "proti": proti, "proti_prc": proti_prc})

    for en in rez.get("enote") or []:
        eu = next((u for u in (udel.get("enote") or [])
                   if u.get("st") == en.get("st")), {})
        za, za_prc, proti, proti_prc = rez_pairs(en.get("rez"))
        rows.append({"referendum": key, "nivo": "enota",
                     "enota_st": en.get("st"), "enota_naz": en.get("naz"),
                     "upr": eu.get("upr"), "gl": eu.get("gl"), "prc": eu.get("prc"),
                     "glas": en.get("glas"), "velj": en.get("velj"),
                     "nev": en.get("nev"), "za": za, "za_prc": za_prc,
                     "proti": proti, "proti_prc": proti_prc, "datum": datum})
        for ok in en.get("okraji") or []:
            ou = next((o for o in (eu.get("okraji") or [])
                       if o.get("st") == ok.get("st")), {})
            za, za_prc, proti, proti_prc = rez_pairs(ok.get("rez"))
            rows.append({"referendum": key, "nivo": "okraj",
                         "enota_st": en.get("st"), "enota_naz": en.get("naz"),
                         "okraj_rpeid": ok.get("rpeid"), "okraj_naz": ok.get("naz"),
                         "upr": ou.get("upr"), "gl": ou.get("gl"), "prc": ou.get("prc"),
                         "glas": ok.get("glas"), "velj": ok.get("velj"),
                         "nev": ok.get("nev"), "za": za, "za_prc": za_prc,
                         "proti": proti, "proti_prc": proti_prc, "datum": datum})
    return rows


def check_sums(key: str, latest: Path, rows: list[dict]):
    """Сверка участков с агрегатами DVK и арифметика внутри участков.

    1. Арифметика участка: velj = za + proti, glas = velj + nev — должна
       сходиться до голоса (настоящая проверка целостности).
    2. Суммы по участкам vs агрегаты DVK — НЕ обязаны сходиться: голоса
       по почте, в диппредставительствах и прочих спецтипах DVK считает
       только на уровне единицы и/или страны (официальная документация,
       «Pozor!»). Расхождение квантифицируем, ошибкой не считаем.
    """
    rez = load_json(latest / "rezultati.json")
    problems = []
    # 1) арифметика внутри участков
    bad_arith = 0
    for r in rows:
        if None in (r["za"], r["proti"], r["velj"], r["glas"], r["nev"]):
            problems.append(f"{key}: участок без данных {r['okraj_rpeid']}/{r['volisce_st']}")
            continue
        if r["za"] + r["proti"] != r["velj"] or r["velj"] + r["nev"] != r["glas"]:
            bad_arith += 1
            if bad_arith <= 5:
                problems.append(
                    f"{key}: арифметика участка {r['enota_st']}/{r['okraj_rpeid']}/"
                    f"{r['volisce_st']} {r['volisce_naz']}: za+proti={r['za'] + r['proti']} "
                    f"velj={r['velj']}, velj+nev={r['velj'] + r['nev']} glas={r['glas']}")
    if bad_arith:
        problems.append(f"{key}: всего участков с несовходящейся арифметикой: {bad_arith}")

    # 2) квантификация спецголосований (не участковых) на уровне округа
    by_okraj: dict[tuple, dict[str, int]] = {}
    for r in rows:
        k = (r["enota_st"], r["okraj_rpeid"])
        acc = by_okraj.setdefault(k, {"glas": 0, "velj": 0, "za": 0, "proti": 0})
        acc["glas"] += r["glas"] or 0
        acc["velj"] += r["velj"] or 0
        acc["za"] += r["za"] or 0
        acc["proti"] += r["proti"] or 0
    missing_okraji = 0
    spec_glas = spec_velj = spec_za = spec_proti = 0
    for en in rez.get("enote") or []:
        for ok in en.get("okraji") or []:
            k = (en.get("st"), ok.get("rpeid"))
            acc = by_okraj.get(k)
            if acc is None:
                missing_okraji += 1
                continue
            okr = {r["st"]: r for r in ok.get("rez") or []}
            spec_glas += (ok.get("glas") or 0) - acc["glas"]
            spec_velj += (ok.get("velj") or 0) - acc["velj"]
            spec_za += (okr.get(1, {}).get("gl") or 0) - acc["za"]
            spec_proti += (okr.get(0, {}).get("gl") or 0) - acc["proti"]
    if missing_okraji:
        problems.append(f"{key}: округов без участков: {missing_okraji}")
    print(f"  {key}: спецголосования сверх участков — бюллетеней {spec_glas:+d}, "
          f"действительных {spec_velj:+d}, ЗА {spec_za:+d}, ПРОТИ {spec_proti:+d}")

    slo = {r["st"]: r for r in rez.get("slovenija") or []}
    tot = {"za": sum(r["za"] or 0 for r in rows),
           "proti": sum(r["proti"] or 0 for r in rows),
           "glas": sum(r["glas"] or 0 for r in rows)}
    for fld, val in (("za", slo.get(1, {}).get("gl")), ("proti", slo.get(0, {}).get("gl")),
                     ("glas", rez.get("glas"))):
        diff = tot[fld] - (val or 0)
        print(f"  {key}: участки {fld}={tot[fld]} vs DVK slovenija={val} "
              f"(разница {diff:+d})")
    return problems


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_volisca: list[dict] = []
    all_nac: list[dict] = []
    problems: list[str] = []

    for key, slug, _title in REFERENDUMS:
        latest = data_dir() / "latest" / key
        rows = volisca_rows(key, slug, latest)
        all_volisca += rows
        all_nac += nacionalni_rows(key, latest)
        print(f"{key}: участков {len(rows)}")
        problems += check_sums(key, latest, rows)

    with open(OUT_DIR / "volisca_all.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VOLISCA_HEADER)
        w.writeheader()
        w.writerows(all_volisca)
    with open(OUT_DIR / "nacionalni_pregled.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=NACIONALNI_HEADER)
        w.writeheader()
        w.writerows(all_nac)

    print(f"\nwritten: {OUT_DIR/'volisca_all.csv'} ({len(all_volisca)} строк)")
    print(f"written: {OUT_DIR/'nacionalni_pregled.csv'} ({len(all_nac)} строк)")
    if problems:
        print(f"\nПРОБЛЕМЫ ({len(problems)}):")
        for p in problems:
            print(" ", p)
        return 1
    print("\nАрифметика всех участков сходится; расхождения с агрегатами — "
          "только спецголосования (см. выше).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
