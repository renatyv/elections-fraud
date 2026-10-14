"""Extracting nationwide figures from the DVK JSON files.

The file structure is described in docs/Referendumi_2026_-_datoteke_s_podatki.docx:
percentages are fractions (0.4825), timestamps are Slovenian local time
in Zulu form; while no data is published the files contain only the «datum» field.
"""

import json
from dataclasses import asdict, dataclass


@dataclass
class Aggregates:
    """Nationwide figures of a single referendum."""

    referendum: str
    source_datum: str | None = None      # update stamp on the server
    turnout_case: str | None = None      # turnout snapshot: 11:00 / 16:00 / 19:00
    electorate: int | None = None        # registered voters
    voters: int | None = None            # voted
    turnout_pct: float | None = None     # turnout, fraction
    counted_pct: float | None = None     # fraction of counted ballots
    ballots: int | None = None           # ballots counted
    valid: int | None = None             # valid
    invalid: int | None = None           # invalid
    za: int | None = None                # ZA (yes) votes
    za_pct: float | None = None
    proti: int | None = None             # PROTI (no) votes
    proti_pct: float | None = None

    def signature(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)


def _option(options_list: list | None, st_value: int) -> tuple[int | None, float | None]:
    """From the options array (st: 1=ZA, 0=PROTI) extracts (votes, share)."""
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
