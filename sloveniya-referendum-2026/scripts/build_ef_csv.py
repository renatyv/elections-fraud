"""Адаптация итогов референдумов к формату analysis-tool (выгрузка MAI).

Читает data/derived/volisca_all.csv (scripts/build_volisca_csv.py) и собирает
для каждого референдума каталог data/ef/<референдум>/results_freguesias.csv —
тот же формат, что и выгрузки MAI в portugal-2025 (key, level, name, path,
parent_key, registered_voters, voted, turnout_pct, blank_votes, null_votes,
votes:ZA, votes:PROTI). Дальше работает штатный пайплайн analysis-tool:

    cd ../analysis-tool && uv run ef-analyze \
        --data ../sloveniya-referendum-2026/data/ef/preiskava \
        --out ../sloveniya-referendum-2026/analysis/preiskava \
        --title "Словения, референдум ZPPre-B 11.10.2026 (участки)" \
        --controls <каталоги остальных трёх референдумов>

Ключ участка повторяет схему MAI LOCAL-0XYZAB (12 символов, district_key =
округ по символам [6:8]): LOCAL-0<enota><порядковый номер внутри enota>;
тогда district_correlations группирует по 8 избирательным единицам. Для теста
соседей parent_key = «enota-okraj» (88 групп по ~34 участка). Путь:
«референдум > enota > okraj > участок» ([-2] = okraj — подписи выбросов).

Точки досрочного голосования (номера участков ≥ 900, upr = 0 — электорат не
определён) в turnout-формат не переводятся и пайплайн не проходят: их проверяет
scripts/analyze_extra.py (цифровые тесты). Здесь они используются только в
сверках полноты.

Одновременно выполняется валидация адаптации (журнал — data/ef/ВАЛИДАЦИЯ.txt):
арифметика строк, сходимость электората и явки между четырьмя референдумами
(одни и те же участки), покрытие национального итога DVK.

Запуск (из sloveniya-referendum-2026/):

    ../analysis-tool/.venv/bin/python scripts/build_ef_csv.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]  # sloveniya-referendum-2026/
SRC = BASE / "data" / "derived" / "volisca_all.csv"
NAC = BASE / "data" / "derived" / "nacionalni_pregled.csv"
OUT = BASE / "data" / "ef"
LOG = OUT / "ВАЛИДАЦИЯ.txt"

REF_TITLE = {
    "preiskava": "preiskava (ZPPre-B, законодательный)",
    "socialna_pomoc": "socialna_pomoc (социальная помощь)",
    "volilna_pravica": "volilna_pravica (избирательное право иностранцев)",
    "rtv_prispevek": "rtv_prispevek (взнос RTV Slovenija)",
}


def adapt(ref: str, df: pd.DataFrame) -> pd.DataFrame:
    """Участки одного референдума → формат results_freguesias.csv (MAI)."""
    df = df.sort_values(["enota_st", "okraj_rpeid", "volisce_rpeid"]).copy()
    seq = df.groupby("enota_st").cumcount() + 1  # нумерация внутри enota (< 10 000)
    out = pd.DataFrame(
        {
            "key": "LOCAL-0" + df["enota_st"].astype(str) + seq.astype(str).str.zfill(4),
            "level": 3,
            "name": df["volisce_naz"],
            "path": REF_TITLE[ref] + " > " + df["enota_naz"] + " > "
                    + df["okraj_naz"] + " > " + df["volisce_naz"],
            "parent_key": df["enota_st"].astype(str) + "-" + df["okraj_rpeid"].astype(str),
            "registered_voters": df["upr"].astype(int),
            "voted": df["glas"].astype(int),
            "turnout_pct": 100.0 * df["glas"] / df["upr"],
            "blank_votes": 0,  # категории «бланк» на референдумах нет
            "null_votes": df["nev"].astype(int),
            "votes:ZA": df["za"].astype(int),
            "votes:PROTI": df["proti"].astype(int),
            # служебные (трассировка к volisca_all.csv; analysis-tool их игнорирует)
            "okraj_rpeid": df["okraj_rpeid"],
            "volisce_rpeid": df["volisce_rpeid"],
            "okraj_naz": df["okraj_naz"],
            "prestetih_glasov": df["prestetih_glasov"],
        }
    )
    assert out["key"].is_unique, f"дубликаты ключей в {ref}"
    assert (seq <= 9999).all()
    return out


def main() -> None:
    raw = pd.read_csv(SRC)
    raw["station"] = (raw["okraj_rpeid"].astype(str) + "_"
                      + raw["volisce_rpeid"].astype(str).str.zfill(3))
    reg = raw[raw["volisce_rpeid"] < 900].copy()
    early = raw[raw["volisce_rpeid"] >= 900].copy()
    nac = pd.read_csv(NAC)
    nat = nac[nac["nivo"] == "slovenija"].set_index("referendum")

    OUT.mkdir(parents=True, exist_ok=True)
    log: list[str] = [
        "Валидация адаптации volisca_all.csv → data/ef/<референдум>/results_freguesias.csv",
        f"источник: {SRC.name}; регулярные участки — номера < 900, досрочные точки — >= 900",
        "",
    ]

    adapted: dict[str, pd.DataFrame] = {}
    for ref in REF_TITLE:
        d = adapt(ref, reg[reg.referendum == ref])
        adapted[ref] = d
        (OUT / ref).mkdir(parents=True, exist_ok=True)
        d.to_csv(OUT / ref / "results_freguesias.csv", index=False, encoding="utf-8-sig")

        # арифметика строк на исходных числах DVK
        g = reg[reg.referendum == ref]
        d_bal = (g["za"] + g["proti"] - g["velj"]).abs().max()
        d_tot = (g["velj"] + g["nev"] - g["glas"]).abs().max()
        n_early = int((early.referendum == ref).sum())
        log += [
            f"[{ref}] {REF_TITLE[ref]}",
            f"  участков: {len(d)} (досрочных точек отдельно: {n_early}); "
            f"enota: {g.enota_st.nunique()}, okraj: {g.okraj_rpeid.nunique()}",
            f"  ЗА+ПРОТИ=действительные: макс. расхождение {d_bal}; "
            f"действит.+недействит.=бюллетени: {d_tot}",
            f"  электорат {g.upr.sum():,}, бюллетеней {g.glas.sum():,} "
            f"(явка {100 * g.glas.sum() / g.upr.sum():.2f}%), "
            f"ЗА {100 * g.za.sum() / g.velj.sum():.2f}% действительных",
            f"  покрытие национального итога DVK: электорат "
            f"{100 * g.upr.sum() / nat.loc[ref, 'upr']:.1f}%, бюллетени "
            f"{100 * g.glas.sum() / nat.loc[ref, 'glas']:.2f}% "
            f"(остаток — досрочные точки, OMNIA, почта, диппредставительства)",
        ]
        # расхождение адаптированных сумм с итогом по участкам из volisca
        for col_a, col_r in (("votes:ZA", "za"), ("votes:PROTI", "proti"),
                             ("null_votes", "nev"), ("voted", "glas")):
            assert int(d[col_a].sum()) == int(g[col_r].sum()), ref
        log.append("  суммы адаптированного CSV = суммам volisca_all.csv: да")
        log.append("")

    # кросс-референдумные сверки: одни и те же участки во всех четырёх бюллетенях
    piv_upr = reg.pivot_table(index="station", columns="referendum", values="upr", aggfunc="first")
    bad_upr = piv_upr[piv_upr.nunique(axis=1) > 1]
    log += ["Электорат участка (upr) одинаков во всех четырёх референдумах:"]
    if len(bad_upr) == 0:
        log.append("  да, все 2 984 участка")
    else:
        log.append(f"  НЕТ у {len(bad_upr)} участков:")
        for st, row in bad_upr.iterrows():
            log.append(f"    {st}: " + ", ".join(f"{r}={v:g}" for r, v in row.items()))

    piv_gl = reg.pivot_table(index="station", columns="referendum", values="gl", aggfunc="first")
    dmax = piv_gl.max(axis=1) - piv_gl.min(axis=1)
    log += [
        "",
        "Явка участка (gl, бюллетеней выдано) по четырём референдумам:",
        f"  совпадает точно: {int((dmax == 0).sum())}; расхождение 1–2: "
        f"{int(((dmax >= 1) & (dmax <= 2)).sum())}; 3–5: {int(((dmax >= 3) & (dmax <= 5)).sum())}; "
        f"больше 5: {int((dmax > 5).sum())} (максимум {int(dmax.max())})",
        "  участки с расхождением > 2 бюллетеней:",
    ]
    for st, row in piv_gl.loc[dmax[dmax > 2].index].iterrows():
        log.append(f"    {st}: " + ", ".join(f"{r}={v:g}" for r, v in row.items()))

    gg = reg[reg["glas"] > reg["gl"]]
    if len(gg):
        log += ["", "Посчитано бюллетеней больше, чем зафиксировала явка (glas > gl):"]
        for _, r in gg.iterrows():
            log.append(f"    {r.station} [{r.referendum}]: gl={r.gl}, glas={r.glas}")

    # досрочные точки: сводка по референдумам
    log += ["", "Досрочные точки (номера >= 900, upr = 0), по референдумам:"]
    for ref, g in early.groupby("referendum"):
        log.append(f"  {ref}: точек {g.station.nunique()}, бюллетеней {g.glas.sum():,}, "
                   f"ЗА {100 * g.za.sum() / g.velj.sum():.2f}% действительных")

    log_text = "\n".join(log) + "\n"
    LOG.write_text(log_text, encoding="utf-8")
    print(log_text)
    print(f"готово: {OUT}/<референдум>/results_freguesias.csv; журнал — {LOG}")


if __name__ == "__main__":
    main()
