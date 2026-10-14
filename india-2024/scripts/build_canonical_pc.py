#!/usr/bin/env python3
"""Сборка канонической таблицы итогов Лок Сабха-2024 (543 PC, по кандидатам).

Источники (локальные, без сети):
  1. data/wayback/pages_en/*.htm — EN-страницы ConstituencywiseSXXYY.htm из Wayback
  2. data/wayback/pages_hi/*.htm — hi-зеркало (524 PC; числа те же, имена партий хинди)
  3. data/kaggle/GE_2024_Results.csv — выгрузка Kaggle (сверка + EN-имена PC/штатов)
  4. data/results_pc/in-rolls_2024_constituencywise_detailed_result.csv — официальная
     детальная выгрузка ECI (электорат по PC)

Логика: ключ (state_code S01..S36, pc_no). Для каждого PC берём EN-таблицу, если
она есть, иначе hi. Имя штата — по EN-страницам; EN-имя PC для hi-строк — из
Kaggle по совпадению суммы голосов. Затем сверка с Kaggle: суммы по PC и имена
победителей. Электорат присоединяется из in-rolls по нормализованному имени PC.

Выход:
  data/results_pc/canonical_pc_results.csv  — каноническая таблица
  data/results_pc/validation_canonical.txt  — отчёт сверок
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from download_wayback_pc_results import parse_html  # noqa: E402

DATA = HERE.parent / "data"
OUT = DATA / "results_pc"

COL_MAP = {
    "candidate": "candidate",
    "party": "party",
    "evm votes": "evm_votes",
    "postal votes": "postal_votes",
    "total votes": "total_votes",
    "% of votes": "pct_votes",
    # hi-зеркало портала ECI
    "अभ्यर्थी": "candidate",
    "दल का नाम": "party",
    "ई.वी.एम. मत": "evm_votes",
    "डाक द्वारा मत": "postal_votes",
    "कुल मत": "total_votes",
    "% मत": "pct_votes",
}
PC_FILE_RE = re.compile(r"ConstituencywiseS(\d{2})(\d+)\.htm$", re.I)

# штат: code -> EN-имя (фолбэк для штатов без EN-страниц)
STATE_EN = {
    "01": "Andhra Pradesh", "02": "Arunachal Pradesh", "03": "Assam", "04": "Bihar",
    "05": "Chhattisgarh", "06": "Goa", "07": "Gujarat", "08": "Haryana",
    "09": "Himachal Pradesh", "10": "Jharkhand", "11": "Karnataka", "12": "Kerala",
    "13": "Madhya Pradesh", "14": "Maharashtra", "15": "Manipur", "16": "Meghalaya",
    "17": "Mizoram", "18": "Odisha", "19": "Punjab", "20": "Rajasthan",
    "21": "Sikkim", "22": "Tamil Nadu", "23": "Telangana", "24": "Tripura",
    "25": "Uttar Pradesh", "26": "Uttarakhand", "27": "West Bengal",
    "28": "NCT of Delhi", "29": "Jammu & Kashmir", "30": "Ladakh",
    "31": "Chandigarh", "32": "Puducherry", "33": "Andaman & Nicobar Islands",
    "34": "Dadra & Nagar Haveli and Daman & Diu", "35": "Lakshadweep",
    "36": "Kerala",
}


def norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def norm_key(s: str) -> str:
    """Нормализация имени PC: без пунктуации и хвостовых ST/SC."""
    k = norm_name(s)
    return re.sub(r"(st|sc)$", "", k)


def collect(lang_dir: Path) -> dict[tuple[str, int], dict]:
    out = {}
    if not lang_dir.exists():
        return out
    for f in sorted(lang_dir.glob("ConstituencywiseS*.htm")):
        m = PC_FILE_RE.search(f.name)
        if not m:
            continue
        key = (m.group(1), int(m.group(2)))
        parsed = parse_html(f.read_bytes(), f"https://results.eci.gov.in/x/{f.name}")
        if parsed is None:
            print(f"  PARSE_FAIL {lang_dir.name}/{f.name}")
            continue
        out[key] = parsed
    return out


def _to_num(s: pd.Series, int_out: bool = True) -> pd.Series:
    if isinstance(s, pd.DataFrame):  # дубли меток колонок
        s = s.iloc[:, 0]
    s = pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")
    return s.fillna(0).astype("int64") if int_out else s


def norm_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join(str(x) for x in tup if str(x) != "nan") for tup in df.columns]
    df.columns = [COL_MAP.get(str(c).strip().lower(), norm_col(c)) for c in df.columns]
    df = df.loc[:, ~pd.Index(df.columns).duplicated()]
    keep = [c for c in dict.fromkeys(COL_MAP.values()) if c in df.columns]
    df = df[keep]
    if "candidate" in df.columns:  # выбросить итоговую строку "Total"/"कुल" (S.N. пустой)
        df = df[~df["candidate"].astype(str).str.strip().str.lower().isin(["total", "कुल"])]
    for c in ("evm_votes", "postal_votes", "total_votes"):
        if c in df.columns:
            df[c] = _to_num(df[c])
    if "pct_votes" in df.columns:
        df["pct_votes"] = _to_num(df["pct_votes"], int_out=False)
    return df


def norm_col(c) -> str:
    return str(c).strip().lower()


def main() -> None:
    en = collect(DATA / "wayback" / "pages_en")
    hi = collect(DATA / "wayback" / "pages_hi")
    print(f"EN страниц разобрано: {len(en)}, HI: {len(hi)}")

    kg = pd.read_csv(DATA / "kaggle" / "GE_2024_Results.csv", dtype=str)
    kg.columns = [c.strip() for c in kg.columns]
    kg["tv"] = pd.to_numeric(kg["Total Votes"].str.replace(",", ""), errors="coerce")
    kg["_s"] = kg["State"].map(norm_key)
    kg["_c"] = kg["Constituency"].map(norm_key)
    kg_g = kg.groupby(["_s", "_c"]).agg(
        kg_total=("tv", "sum"), kg_n=("tv", "size"),
        state_en=("State", "first"), pc_en=("Constituency", "first"),
    ).reset_index()

    merged: list[pd.DataFrame] = []
    src_count = {"en": 0, "hi": 0}
    missing_names: list[str] = []
    for key in sorted(set(en) | set(hi), key=lambda k: (k[0], k[1])):
        sc, pc = key
        if key in en:
            p, lang = en[key], "en"
        else:
            p, lang = hi[key], "hi"
        src_count[lang] += 1
        t = norm_table(p["table"])
        total = int(t["total_votes"].sum()) if "total_votes" in t else -1

        # EN-имена: прямые по имени из EN-страницы, иначе через Kaggle по сумме
        state = STATE_EN.get(sc, "")
        pc_name = p["pc_name"] if lang == "en" else ""
        if not pc_name or not state:
            sel = kg_g[kg_g["_s"] == norm_key(state or pc_name)]
            cand = sel[sel["kg_total"].sub(total).abs() <= 3] if total >= 0 else sel
            if not cand.empty:
                state = state or cand["state_en"].iloc[0]
                pc_name = pc_name or cand["pc_en"].iloc[0]
            elif not pc_name:
                missing_names.append(f"S{sc}PC{pc} total={total}")
        t.insert(0, "pc_no", pc)
        t.insert(0, "pc_name", pc_name)
        t.insert(0, "state", state)
        t.insert(0, "state_code", sc)
        t.insert(0, "lang", lang)
        merged.append(t)

    can = pd.concat(merged, ignore_index=True)
    n_pc = can.groupby(["state_code", "pc_no"]).ngroups
    print(f"канон: {can.shape}, PC: {n_pc} (EN: {src_count['en']}, HI: {src_count['hi']})")
    if missing_names:
        print("PC без EN-имени:", missing_names)

    # --- сверка с Kaggle ---------------------------------------------------
    can["_s"] = can["state"].map(norm_key)
    can["_c"] = can["pc_name"].map(norm_key)
    lines: list[str] = []
    n_ok = n_diff = n_unmatched = 0
    for (sc, pc), g in can.groupby(["state_code", "pc_no"]):
        st, pcn = g["_s"].iloc[0], g["_c"].iloc[0]
        total = int(g["total_votes"].sum())
        sel = kg_g[(kg_g["_s"] == st) & (kg_g["_c"] == pcn)]
        if sel.empty:
            sel = kg_g[(kg_g["_s"] == st) & (kg_g["kg_total"].sub(total).abs() <= 3)]
        if sel.empty:
            n_unmatched += 1
            lines.append(f"UNMATCHED S{sc}PC{pc} {g['state'].iloc[0]} / {g['pc_name'].iloc[0]} total={total}")
            continue
        d = int(sel["kg_total"].iloc[0]) - total
        if abs(d) <= 2:
            n_ok += 1
        else:
            n_diff += 1
            lines.append(f"DIFF S{sc}PC{pc} {g['state'].iloc[0]} / {g['pc_name'].iloc[0]}: "
                         f"wayback={total} kaggle={int(sel['kg_total'].iloc[0])} Δ={d}")
    summary = [
        "СВЕРКА канонической таблицы (Wayback EN+HI) с Kaggle GE_2024_Results.csv",
        f"PC в каноне: {n_pc} (EN: {src_count['en']}, HI: {src_count['hi']});"
        f" строк-кандидатов: {len(can)}",
        f"сверено сумм: {n_ok + n_diff}, совпало (±2): {n_ok}, расхождений: {n_diff},"
        f" не сопоставлено: {n_unmatched}",
        "",
    ]
    report = "\n".join(summary + lines)
    (OUT / "validation_canonical.txt").write_text(report)
    print("\n".join(summary))

    # --- электорат из in-rolls ---------------------------------------------
    try:
        ir = pd.read_csv(DATA / "results_pc" / "in-rolls_2024_constituencywise_detailed_result.csv")
        ir.columns = [c.split("\n")[0].strip() for c in ir.columns]
        ir = ir.rename(columns={"State Name": "st", "PC Name": "pc", "Total Electors": "electors"})
        ir["_s"] = ir["st"].map(norm_key)
        ir["_c"] = ir["pc"].map(norm_key)
        ir_g = ir.groupby(["_s", "_c"])["electors"].first()
        can["_k"] = list(zip(can["_s"], can["_c"]))
        can["electors"] = can["_k"].map(ir_g)
        n_el = can["electors"].notna().sum()
        print(f"электорат присоединён к {n_el}/{len(can)} строкам")
        can.drop(columns=["_s", "_c", "_k"], inplace=True)
    except Exception as e:
        print(f"электорат: пропущено ({e})")

    can.to_csv(OUT / "canonical_pc_results.csv", index=False)
    print(f"-> {OUT / 'canonical_pc_results.csv'}")


if __name__ == "__main__":
    main()
