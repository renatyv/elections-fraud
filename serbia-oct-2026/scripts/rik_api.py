# -*- coding: utf-8 -*-
"""
Клиент JSON-API Республики избирательной комиссии Сербии (РИК).

Эндпоинты найдены реверс-инжинирингом официального портала результатов
https://www.rik.parlament.gov.rs/542645/rezultati/ (js/minified.*.js).
Только стандартная библиотека Python.
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://www.rik.parlament.gov.rs"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
    "(elections-research; scrape every 15 min)"
)

ELECTION_TYPE_PARLIAMENTARY = 2  # 2 = Парламентарни, 3 = Локални, 7 = Покрајински


def _post(path: str, data: dict, timeout: float = 30.0,
          retries: int = 3, backoff: float = 2.0) -> bytes:
    """POST c X-Requested-With (как это делает фронтенд портала РИК)."""
    body = urllib.parse.urlencode(data).encode("utf-8")
    last_err = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            BASE_URL + path,
            data=body,
            headers={
                "User-Agent": USER_AGENT,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": BASE_URL + "/542645/rezultati/",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff * attempt)
    raise RuntimeError(f"RIK API {path} failed after {retries} attempts: {last_err}")


def get_elections(election_type: int = ELECTION_TYPE_PARLIAMENTARY) -> dict:
    """Список кампаний: {id тура (str): название}. Напр. {'680072': 'Парламентарни 2026'}."""
    payload = json.loads(_post("/get-elections/", {"election_type": election_type}))
    return payload.get("rounds", {})


def get_regions(election_type: int, election_round: int) -> dict:
    """Регионы тура: {'regions': {id: название}, 'data_id': {id: код NUTS2 или None}}."""
    payload = json.loads(_post("/get-regions/", {
        "election_type": election_type,
        "election_round": election_round,
    }))
    return payload


def get_municipalities(election_type: int, election_round: int, election_region: int) -> list:
    """
    Муниципалитеты региона. Эндпоинт возвращает HTML <option data-id=".." value="..">Название</option>.
    -> [{'value': '1', 'unit_id': '70092', 'name': 'Градска општина Барајево'}, ...]
    """
    html = _post("/get-municipalities/", {
        "election_type": election_type,
        "election_round": election_round,
        "election_region": election_region,
    }).decode("utf-8", errors="replace")
    out = []
    for m in re.finditer(
        r'<option[^>]*data-id="([^"]*)"[^>]*value="([^"]*)"[^>]*>(.*?)</option>', html, re.S
    ):
        name = re.sub(r"\s+", " ", m.group(3)).strip()
        if m.group(2) != "0":  # value="0" — техническая опция «весь регион»
            out.append({"value": m.group(2), "unit_id": m.group(1), "name": name})
    return out


def get_election_stations(election_type: int, election_round: int,
                          election_region: int, election_municipality: int) -> list:
    """Участки муниципалитета: [{'id': '159091', 'name': '1 - МК "АРНАЈЕВО"'}, ...]."""
    payload = json.loads(_post("/get-election-stations/", {
        "election_type": election_type,
        "election_round": election_round,
        "election_region": election_region,
        "election_municipality": election_municipality,
    }))
    stations = payload.get("election_stations", {})
    return [{"id": sid, "name": name} for sid, name in stations.items()]


def get_results(election_type: int, election_round: int, region: int = 0,
                municipality: int = 0, election_station: int = 0) -> dict:
    """
    Результаты для уровня: страна (0/0/0), регион (region), муниципалитет
    (region+municipality) или участок (region+municipality+election_station).

    Ответ:
      stat_sum_numbers: total_voters, available (проголосовало), number_of_stations,
        processed_stations, datetime (момент данных РИК, '-' пока данных нет),
        election_title
      table_data: [{'count_number', 'list_name', 'won_number', 'won_percent', 'list_image'}, ...]
      processed_config / sum_config: конфиги диаграмм (явка; действительные/
        недействительные бюллетени — числа лежат в data.datasets[0].data)
      minute_from_election_station: HTML со ссылками на PDF-протоколы участка (RG-2)
    """
    return json.loads(_post("/get_results/", {
        "should_update_pies": 1,
        "type": election_type,
        "election_round": election_round,
        "region": region,
        "municipality": municipality,
        "election_station": election_station,
    }))


# ---------- разбор значений ----------

def parse_int(value) -> int:
    """'3.820.746' -> 3820746; '0'/'-'/None -> 0."""
    if value is None:
        return 0
    s = str(value).strip().replace(".", "").replace(",", "")
    if not s or not s.lstrip("-").isdigit():
        return 0
    return int(s)


def parse_float(value) -> float:
    try:
        return round(float(str(value).strip().replace(",", ".")), 2)
    except (TypeError, ValueError):
        return 0.0


def parse_rik_datetime(value: str):
    """'09.01.2024 20:21:00' -> '2024-01-09T20:21:00' (локальное время РИК, CET/CEST)."""
    if not value or value.strip() == "-":
        return None
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2}):(\d{2})", value.strip())
    if not m:
        return None
    d, mo, y, h, mi, s = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}"


def ballots_from_sum_config(results: dict) -> tuple:
    """(действительные, недействительные) из конфига круговой диаграммы."""
    try:
        data = results["sum_config"]["data"]["datasets"][0]["data"]
        return parse_int(data[0]), parse_int(data[1])
    except (KeyError, IndexError, TypeError):
        return 0, 0


def normalize_results(results: dict, level_type: str, level_id: str,
                      level_name: str, election_round: int,
                      snapshot_ts: str) -> dict:
    """Приводит ответ get_results к плоской структуре для CSV/JSON-снапшотов."""
    ssn = results.get("stat_sum_numbers", {})
    valid, invalid = ballots_from_sum_config(results)
    registered = parse_int(ssn.get("total_voters"))
    turnout = parse_int(ssn.get("available"))
    total_st = parse_int(ssn.get("number_of_stations"))
    proc_st = parse_int(ssn.get("processed_stations"))
    return {
        "snapshot_ts": snapshot_ts,
        "election_round": election_round,
        "level_type": level_type,       # national | region | municipality | station
        "level_id": level_id,
        "level_name": level_name,
        "rik_datetime": parse_rik_datetime(ssn.get("datetime", "")),
        "election_title": ssn.get("election_title", ""),
        "registered_voters": registered,
        "turnout_voters": turnout,
        "turnout_pct": round(turnout / registered * 100, 2) if registered else 0.0,
        "total_stations": total_st,
        "processed_stations": proc_st,
        "processed_pct": round(proc_st / total_st * 100, 2) if total_st else 0.0,
        "valid_ballots": valid,
        "invalid_ballots": invalid,
        "lists": [
            {
                "list_no": row.get("count_number"),
                "list_name": row.get("list_name", "").strip(),
                "votes": parse_int(row.get("won_number")),
                "percent": parse_float(row.get("won_percent")),
            }
            for row in results.get("table_data", [])
        ],
    }
