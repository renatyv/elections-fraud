"""Извлечение общенациональных показателей из JSON-файлов DVK.

Структура файлов описана в docs/Referendumi_2026_-_datoteke_s_podatki.docx:
проценты — доли (0.4825), метки времени — словенское локальное время
в Zulu-форме; пока данных нет, в файлах есть только поле «datum».
"""

import json
from dataclasses import asdict, dataclass


@dataclass
class Aggregates:
    """Общенациональные показатели одного референдума."""

    referendum: str
    source_datum: str | None = None      # метка обновления на сервере
    turnout_case: str | None = None      # срез явки: 11:00 / 16:00 / 19:00
    electorate: int | None = None        # избирателей
    voters: int | None = None            # голосовало
    turnout_pct: float | None = None     # явка, доля
    counted_pct: float | None = None     # доля посчитанных бюллетеней
    ballots: int | None = None           # посчитано бюллетеней
    valid: int | None = None             # действительных
    invalid: int | None = None           # недействительных
    za: int | None = None                # голосов ЗА
    za_pct: float | None = None
    proti: int | None = None             # голосов ПРОТИ
    proti_pct: float | None = None

    def signature(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)


def _option(options_list: list | None, st_value: int) -> tuple[int | None, float | None]:
    """Из массива опций (st: 1=ЗА, 0=ПРОТИ) достаёт (голоса, доля)."""
    for opt in options_list or []:
        if opt.get("st") == st_value:
            return opt.get("gl"), opt.get("prc")
    return None, None


def _loads(data: bytes | None) -> dict | None:
    if not data:
        return None
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def extract_aggregates(referendum: str,
                       rezultati_json: bytes | None,
                       udelezba_json: bytes | None) -> Aggregates:
    agg = Aggregates(referendum=referendum)

    rez = _loads(rezultati_json)
    if rez:
        agg.source_datum = rez.get("datum")
        agg.ballots = rez.get("glas")
        agg.valid = rez.get("velj")
        agg.invalid = rez.get("nev")
        agg.za, agg.za_pct = _option(rez.get("slovenija"), 1)
        agg.proti, agg.proti_pct = _option(rez.get("slovenija"), 0)

    ude = _loads(udelezba_json)
    if ude:
        agg.turnout_case = ude.get("cas_udelezba")
        slo = ude.get("slovenija")
        if isinstance(slo, dict):
            agg.electorate = slo.get("upr")
            agg.voters = slo.get("gl")
            agg.turnout_pct = slo.get("prc")

    if agg.ballots and agg.voters:
        agg.counted_pct = agg.ballots / agg.voters
    return agg
