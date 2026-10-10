#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "httpx[http2]>=0.27",
#     "rich>=13",
# ]
# ///
"""
Скрейпер промежуточных результатов выборов Бразилии (TSE — Divulgação de Resultados).

Запуск через uv (зависимости объявлены выше в PEP 723 и ставятся автоматически):
    uv run scripts/tse_scrape.py --loop

Источник: https://resultados.tse.jus.br/oficial/...
  официальные статические JSON-файлы, которые использует сам портал TSE.
  Обновляются по мере подсчёта голосов (в ночь выборов — примерно каждую минуту).

Основные файлы (ele = код выборов, например 6258 — 2-й тур президентских 2026):
  oficial/comum/config/ele-c.json                        — индекс всех выборов и кодов
  oficial/ele2026/{ele}/dados/br/br-c{cargo}-e{ele}-u.json — результаты по стране
  oficial/ele2026/{ele}/dados/{uf}/{uf}-c{cargo}-e{ele}-u.json — результаты по штату
  oficial/ele2026/{ele}/dados/br/br-e{ele}-ab.json        — прогресс подсчёта по штатам

Что делает один проход (cycle):
  1) читает индекс ele-c.json и сам находит код нужных выборов (или берёт --election);
  2) скачивает u.json (результаты) и ab.json (прогресс) через один httpx-клиент
     с пулом соединений и HTTP/2;
  3) сохраняет сырые снапшоты в data/snapshots/<ele>/ (только если данные изменились — по idg);
  4) дописывает строки кандидатов в data/timeline.csv и прогресс по штатам в data/progress_by_uf.csv;
  5) обновляет data/latest.json, data/scraper.log и рисует сводную таблицу в консоль (rich).

Режимы:
    uv run scripts/tse_scrape.py --once   один проход
    uv run scripts/tse_scrape.py --loop   цикл с интервалом --interval (по умолч. 900 сек = 15 мин)

Примеры:
    uv run scripts/tse_scrape.py --loop                            # 2-й тур президентских, каждые 15 мин
    uv run scripts/tse_scrape.py --once --turno 1                  # 1-й тур (финальные данные)
    uv run scripts/tse_scrape.py --loop --uf all                   # страна + все 27 штатов
    uv run scripts/tse_scrape.py --loop --election 6260 --cargo 3 --uf all   # 2-е туры губернаторов
"""

import argparse
import csv
import fcntl
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

try:  # красивый вывод в консоль; в лог всё равно пишется простым текстом
    from rich.console import Console
    from rich.table import Table
    console = Console()
except ImportError:  # прагматичный фолбэк, если rich внезапно недоступен
    console = None

HOST = "https://resultados.tse.jus.br"
CICLO = "ele2026"  # папка цикла выборов 2026 (из ele-c.json: pl[].c)

UF_LIST = ["ac","al","ap","am","ba","ce","df","es","go","ma","mt","ms","mg",
           "pa","pb","pr","pe","pi","rj","rn","rs","ro","rr","sc","sp","se","to"]

USER_AGENT = "elections-research-scraper/2.0 (15-min polling of public TSE results JSON)"

TIMELINE_COLS = [
    "fetched_at_utc","election","turno","election_name","uf","cargo","cargo_name",
    "idg","data_geracao","hora_geracao",
    "secoes_total","secoes_apuradas","pct_secoes_apuradas",
    "eleitorado_total","eleitorado_apurado",
    "votos_totais","votos_validos","votos_brancos","votos_nulos",
    "sqcand","numero","nome_urna","nome_completo","partido","coligacao","vice",
    "votos","pct_validos","pct_validos_num","eleito","status_candidato",
]

PROGRESS_COLS = [
    "fetched_at_utc","election","turno","uf","idg","data_geracao","hora_geracao",
    "pct_secoes_apuradas","pct_secoes_num","secoes_total","secoes_apuradas",
    "pct_eleitorado_apurado","eleitorado_total","eleitorado_apurado",
    "municipios_nao_apurados","municipios_finais",
]


# ----------------------------- HTTP (httpx) -----------------------------

def make_client() -> httpx.Client:
    return httpx.Client(
        base_url=HOST,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/plain, */*"},
        timeout=httpx.Timeout(30.0, connect=10.0),
        # пул соединений переживает циклы; retries на уровне транспорта — повтор коннекта
        transport=httpx.HTTPTransport(retries=2, http2=True),
        follow_redirects=True,
    )


def fetch_json(client: httpx.Client, url: str, retries: int = 2):
    """GET JSON. Возвращает распарсенный объект или None, если 404 (данные ещё не появились)."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = client.get(url)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            client.http_version_seen = r.http_version  # для лога (h2/http1.1)
            return json.loads(r.content.decode("utf-8-sig"))
        except httpx.HTTPStatusError as e:
            last_err = e
        except httpx.HTTPError as e:  # таймауты, обрывы, ошибки соединения
            last_err = e
        if attempt < retries:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url}: {last_err}")


def fetch_bytes(client: httpx.Client, url: str):
    r = client.get(url)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    client.http_version_seen = r.http_version
    return r.content


# ------------------------- индекс выборов -------------------------

def load_election_index(client):
    """ele-c.json — официальный индекс всех плебисцитов/выборов."""
    return fetch_json(client, "oficial/comum/config/ele-c.json")


def resolve_election(index: dict, turno: int, tp: int = 8, cargo_cd: str = "1"):
    """Найти код выборов в ele2026: федеральные (tp=8, президент) нужного тура."""
    for pl in index.get("pl", []):
        if pl.get("c") != CICLO:
            continue
        for el in pl.get("e", []):
            if el.get("tp") != str(tp) or el.get("t") != str(turno):
                continue
            for abr in el.get("abr", []):
                if abr.get("cd") == "br" and any(cp.get("cd") == cargo_cd for cp in abr.get("cp", [])):
                    return {
                        "code": el["cd"],
                        "name": el.get("nm", ""),
                        "turno": int(el.get("t", 0)),
                        "pleito_date": pl.get("dt", ""),
                    }
    return None


def cargo_name_from_index(index: dict, election_code: str, cargo_cd: str):
    for pl in index.get("pl", []):
        if pl.get("c") != CICLO:
            continue
        for el in pl.get("e", []):
            if el.get("cd") != str(election_code):
                continue
            for abr in el.get("abr", []):
                for cp in abr.get("cp", []):
                    if cp.get("cd") == cargo_cd:
                        return cp.get("ds", "")
    return f"cargo {cargo_cd}"


# --------------------------- URL-хелперы ---------------------------

def pad(n, width):
    return str(n).zfill(width)

def url_u(election, uf, cargo):
    """Единый файл результатов (unificado) для пары (uf, cargo)."""
    return f"oficial/{CICLO}/{election}/dados/{uf}/{uf}-c{pad(cargo,4)}-e{pad(election,6)}-u.json"

def url_ab(election, uf="br"):
    """Файл сопровождения (acompanhamento) — прогресс подсчёта по штатам."""
    return f"oficial/{CICLO}/{election}/dados/{uf}/{uf}-e{pad(election,6)}-ab.json"


# ---------------------------- парсинг ----------------------------

def num(s):
    """'47,027772356' -> 47.027772356; '' -> None."""
    if s is None or s == "":
        return None
    try:
        return float(str(s).replace(",", "."))
    except ValueError:
        return None

def parse_u(u: dict):
    """Разобрать u.json в плоский словарь состояния + список кандидатов."""
    cands = []
    for carg in u.get("carg", []):
        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    vice = ""
                    if c.get("vs"):
                        vice = c["vs"][0].get("nmu", "")
                    cands.append({
                        "cargo_code": carg.get("cd", ""),
                        "cargo_name": carg.get("nmn", ""),
                        "sqcand": c.get("sqcand", ""),
                        "numero": c.get("n", ""),
                        "nome_urna": c.get("nmu", ""),
                        "nome_completo": c.get("nm", ""),
                        "partido": par.get("sg", ""),
                        "coligacao": agr.get("com", par.get("nm", "")),
                        "vice": vice,
                        "votos": c.get("vap", ""),
                        "pct_validos": c.get("pvap", ""),
                        "pct_validos_num": num(c.get("pvapn")),
                        "eleito": c.get("e", ""),
                        "status_candidato": c.get("st", ""),
                    })
    s = u.get("s", {})   # секции (участки)
    e = u.get("e", {})   # электорат
    v = u.get("v", {})   # голоса
    return {
        "idg": u.get("idg", ""),
        "dg": u.get("dg", ""),
        "hg": u.get("hg", ""),
        "dt": u.get("dt", ""),     # дата тотализации
        "ht": u.get("ht", ""),
        "tf": u.get("tf", ""),     # totalizado final: s/n
        "and": u.get("and", ""),   # andamento
        "secoes_total": s.get("ts", ""),
        "secoes_apuradas": s.get("st", ""),
        "pct_secoes_apuradas": s.get("pst", ""),
        "eleitorado_total": e.get("te", ""),
        "eleitorado_apurado": e.get("est", ""),
        "votos_totais": v.get("tv", ""),
        "votos_validos": v.get("vv", v.get("vvc", "")),
        "votos_brancos": v.get("vb", ""),
        "votos_nulos": v.get("vn", v.get("tvn", "")),
        "candidates": cands,
    }


# ----------------------------- записи -----------------------------

def append_csv(path: Path, cols, row: dict):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def save_snapshot(snap_dir: Path, uf, cargo, payload: bytes):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = snap_dir / f"{stamp}_{uf}_c{pad(cargo,4)}.json"
    p.write_bytes(payload)
    return p


def load_state(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_state(path: Path, state: dict):
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


# ----------------------------- один проход -----------------------------

def render_summary(latest: dict, election: str):
    """Сводная таблица в консоль (rich): топ кандидатов по стране + прогресс подсчёта."""
    if console is None:
        return
    br = latest["ufs"].get("br")
    if not br:
        return
    table = Table(title=f"{latest['election_name']}  |  срез {latest['fetched_at_utc']} UTC  |  "
                        f"участков подсчитано: {br['sections_counted_pct']}%",
                  title_justify="left")
    for col in ("#", "Кандидат", "Партия", "Голоса", "% валидных", "Статус"):
        table.add_column(col, justify="right" if col in ("#", "Голоса", "% валидных") else "left")
    for i, c in enumerate(br["candidates"][:8], 1):
        table.add_row(str(i), c["nome"], c["partido"], f"{int(c['votos'] or 0):,}".replace(",", " "),
                      str(c["pct"]).replace(".", ","), c["status"] or ("избран" if c["eleito"] == "s" else ""))
    console.print(table)


def run_cycle(args, client: httpx.Client, data_dir: Path, state: dict, log) -> dict:
    now = datetime.now(timezone.utc)
    now_s = now.strftime("%Y-%m-%d %H:%M:%S")
    summary = {"fetched_at_utc": now_s, "targets": []}

    index = load_election_index(client)
    if index is None:
        log(f"[{now_s}] WARN: ele-c.json недоступен, пропуск прохода")
        return summary

    # код выборов: явный --election или авто-поиск по индексу
    if args.election:
        election = str(args.election)
        meta = resolve_election(index, args.turno)
        el_name = meta["name"] if meta and meta["code"] == election else f"election {election}"
        pleito_date = meta["pleito_date"] if meta else ""
    else:
        meta = resolve_election(index, args.turno)
        if not meta:
            raise SystemExit(f"Не найдены выборы (ciclo={CICLO}, turno={args.turno}) в ele-c.json; "
                             f"укажите код явно через --election")
        election, el_name, pleito_date = meta["code"], meta["name"], meta["pleito_date"]

    summary["election"] = election
    summary["election_name"] = el_name
    summary["turno"] = args.turno
    log(f"[{now_s}] выборы {election} ({el_name}), плебисцит {pleito_date}, "
        f"cargo={args.cargo}, ufs={args.uf}, http={getattr(client, 'http_version_seen', '?')}")

    snap_dir = data_dir / "snapshots" / election
    snap_dir.mkdir(parents=True, exist_ok=True)
    default_cargo_name = cargo_name_from_index(index, election, args.cargo)

    # br (страна) всегда включаем; помимо него — все штаты или конкретный список
    if args.uf == "br":
        ufs = ["br"]
    elif args.uf == "all":
        ufs = ["br"] + UF_LIST
    else:
        ufs = ["br"] + [u.strip().lower() for u in args.uf.split(",") if u.strip()]

    latest = {"fetched_at_utc": now_s, "election": election, "election_name": el_name,
              "turno": args.turno, "pleito_date": pleito_date,
              "cargo": args.cargo, "cargo_name": default_cargo_name,
              "sources": [], "ufs": {}}

    for uf in ufs:
        ujson_url = url_u(election, uf, args.cargo)
        try:
            raw = fetch_bytes(client, ujson_url)
        except (RuntimeError, httpx.HTTPError) as e:
            log(f"[{now_s}] {uf}: ERROR {e}")
            continue
        if raw is None:
            log(f"[{now_s}] {uf}: 404 — файл результатов ещё не опубликован")
            continue
        u = json.loads(raw.decode("utf-8-sig"))

        parsed = parse_u(u)
        key = f"u:{election}:{uf}:c{args.cargo}"
        changed = state.get(key) != parsed["idg"]

        if changed:
            snap_path = save_snapshot(snap_dir, uf, args.cargo, raw)
            state[key] = parsed["idg"]
            log(f"[{now_s}] {uf}: НОВЫЕ данные idg={parsed['idg']} "
                f"(ген. {parsed['dg']} {parsed['hg']}, участков подсчитано {parsed['pct_secoes_apuradas']}%), "
                f"снапшот {snap_path.name}")
        else:
            log(f"[{now_s}] {uf}: без изменений (idg={parsed['idg']})")

        if changed:  # строку в timeline пишем только при изменении
            for c in parsed["candidates"]:
                append_csv(data_dir / "timeline.csv", TIMELINE_COLS, {
                    "idg": parsed["idg"],
                    "data_geracao": parsed["dg"], "hora_geracao": parsed["hg"],
                    "secoes_total": parsed["secoes_total"],
                    "secoes_apuradas": parsed["secoes_apuradas"],
                    "pct_secoes_apuradas": parsed["pct_secoes_apuradas"],
                    "eleitorado_total": parsed["eleitorado_total"],
                    "eleitorado_apurado": parsed["eleitorado_apurado"],
                    "votos_totais": parsed["votos_totais"],
                    "votos_validos": parsed["votos_validos"],
                    "votos_brancos": parsed["votos_brancos"],
                    "votos_nulos": parsed["votos_nulos"],
                    "fetched_at_utc": now_s, "election": election, "turno": args.turno,
                    "election_name": el_name, "uf": uf, "cargo": args.cargo,
                    "cargo_name": c["cargo_name"] or default_cargo_name,
                    **c,
                })

        latest["ufs"][uf] = {
            "idg": parsed["idg"], "generated": f'{parsed["dg"]} {parsed["hg"]}',
            "sections_counted_pct": parsed["pct_secoes_apuradas"],
            "totalized_final": parsed["tf"],
            "valid_votes": parsed["votos_validos"],
            "candidates": [
                {"nome": c["nome_urna"], "partido": c["partido"], "votos": c["votos"],
                 "pct": c["pct_validos"], "eleito": c["eleito"], "status": c["status_candidato"]}
                for c in sorted(parsed["candidates"],
                                key=lambda c: int(c["votos"] or 0), reverse=True)
            ],
        }
        summary["targets"].append({"uf": uf, "idg": parsed["idg"], "changed": changed})
        latest["sources"].append(f"{HOST}/{ujson_url}")
        time.sleep(args.delay)  # вежливость к CDN TSE

    # прогресс подсчёта по всем штатам (acompanhamento) — только для уровня br
    ab_url = url_ab(election, "br")
    try:
        ab = fetch_json(client, ab_url)
    except (RuntimeError, httpx.HTTPError) as e:
        ab = None
        log(f"[{now_s}] ab.json: ERROR {e}")
    if ab is not None:
        key = f"ab:{election}"
        if state.get(key) != ab.get("idg"):
            state[key] = ab.get("idg", "")
            (snap_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}_ab.json").write_text(
                json.dumps(ab, ensure_ascii=False), encoding="utf-8")
            for row in ab.get("abr", []):
                s, e_ = row.get("s", {}), row.get("e", {})
                append_csv(data_dir / "progress_by_uf.csv", PROGRESS_COLS, {
                    "fetched_at_utc": now_s, "election": election, "turno": args.turno,
                    "uf": row.get("cdabr", ""),
                    "idg": ab.get("idg", ""),
                    "data_geracao": ab.get("dg", ""), "hora_geracao": ab.get("hg", ""),
                    "pct_secoes_apuradas": s.get("pst", ""),
                    "pct_secoes_num": num(s.get("pstn")),
                    "secoes_total": s.get("ts", ""), "secoes_apuradas": s.get("st", ""),
                    "pct_eleitorado_apurado": e_.get("pest", ""),
                    "eleitorado_total": e_.get("te", ""), "eleitorado_apurado": e_.get("est", ""),
                    "municipios_nao_apurados": row.get("munnr", ""),
                    "municipios_finais": row.get("munf", ""),
                })
            log(f"[{now_s}] ab.json: обновлён (idg={ab.get('idg')}), прогресс по штатам дописан")
        else:
            log(f"[{now_s}] ab.json: без изменений (idg={ab.get('idg')})")
        latest["sources"].append(f"{HOST}/{ab_url}")

    # компактная сводка
    top = latest["ufs"].get("br", {}).get("candidates", [])
    if top:
        log(f"[{now_s}] БРАЗИЛИЯ топ: " + " | ".join(
            f'{c["nome"]} ({c["partido"]}) {c["pct"]}%' for c in top[:2]))

    (data_dir / "latest.json").write_text(
        json.dumps(latest, ensure_ascii=False, indent=1), encoding="utf-8")
    render_summary(latest, election)
    return summary


# ------------------------------- main -------------------------------

def make_logger(log_path: Path):
    def log(msg):
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        line = f"{stamp} {msg}" if not msg.startswith("[") else msg
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return log


def main():
    ap = argparse.ArgumentParser(description="Скрейпер промежуточных результатов TSE (Бразилия)")
    ap.add_argument("--loop", action="store_true", help="крутиться циклически с --interval секунд")
    ap.add_argument("--once", action="store_true", help="один проход (режим по умолчанию)")
    ap.add_argument("--interval", type=int, default=900, help="интервал опроса, сек (по умолчанию 900 = 15 мин)")
    ap.add_argument("--turno", type=int, default=2, choices=[1, 2],
                    help="тур (по умолчанию 2 — второй тур 25.10.2026)")
    ap.add_argument("--election", type=str, default=None,
                    help="явный код выборов (например 6258); иначе берётся из индекса по --turno")
    ap.add_argument("--cargo", type=str, default="1",
                    help="код должности: 1=Presidente, 3=Governador, 5=Senador, 6=Dep.Federal, 7=Dep.Estadual, 8=Dep.Distrital")
    ap.add_argument("--uf", type=str, default="br",
                    help="'br' (по умолч.) — только страна; 'all' — страна + 27 штатов; "
                         "'sp,mg' — конкретные штаты (страна добавляется всегда)")
    ap.add_argument("--data-dir", type=str, default=None, help="каталог данных (по умолчанию ../data рядом со скриптом)")
    ap.add_argument("--delay", type=float, default=0.5, help="пауза между запросами, сек")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    data_dir = Path(args.data_dir) if args.data_dir else here.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    log = make_logger(data_dir / "scraper.log")

    # блокировка от параллельных запусков (cron + loop одновременно и т.п.)
    lock_path = data_dir / ".scraper.lock"
    lock_fh = open(lock_path, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("Другой экземпляр скрипта уже работает — выход.")
        sys.exit(0)

    state_path = data_dir / "state.json"
    state = load_state(state_path)

    log(f"=== старт: turno={args.turno} cargo={args.cargo} uf={args.uf} "
        f"режим={'loop каждые %d сек' % args.interval if args.loop else 'once'} ===")
    try:
        with make_client() as client:  # один пул соединений на всё время работы
            while True:
                try:
                    run_cycle(args, client, data_dir, state, log)
                except Exception as e:
                    log(f"ОШИБКА прохода: {e!r}")
                save_state(state_path, state)
                if not args.loop:
                    break
                # спим интервалом по 30 сек, чтобы можно было прервать Ctrl-C быстро
                for _ in range(args.interval // 30):
                    time.sleep(30)
    except KeyboardInterrupt:
        log("Остановлено пользователем (Ctrl-C).")
    finally:
        save_state(state_path, state)
        log("=== завершение ===")


if __name__ == "__main__":
    main()
