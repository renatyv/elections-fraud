"""Конфигурация: референдумы, файлы данных, пути.

Официальное описание форматов — DVK, «Referendumi 2026 - datoteke s podatki»
(копия в docs/ проекта).
"""

import os
from pathlib import Path

BASE_URL = "https://volitve.dvk-rs.si"

# (ключ, slug на сервере, название)
REFERENDUMS: list[tuple[str, str, str]] = [
    ("preiskava", "referendum-preiskava",
     "Законодательный референдум о ZPPre-B (закон о парламентских расследованиях)"),
    ("socialna_pomoc", "referendum-socialna-pomoc",
     "Консультативный: социальная помощь и общественно-полезный труд"),
    ("volilna_pravica", "referendum-volilna-pravica-tujcev",
     "Консультативный: избирательные права на местных выборах"),
    ("rtv_prispevek", "referendum-rtv-prispevek",
     "Консультативный: отмена обязательного взноса на RTV Slovenija"),
]

BASE_FILES: list[str] = [
    "udelezba.json", "rezultati.json",
    "udelezba.csv", "rezultati.csv",
    "izvoz.xlsx",
]

# volisca_ЕО_ОК.json: 8 избирательных единиц (volilna enota) × 11 округов (okraj)
N_UNITS = 8
N_DISTRICTS = 11


def volisca_files() -> list[str]:
    return [f"volisca_{ee:02d}_{oo:02d}.json"
            for ee in range(1, N_UNITS + 1)
            for oo in range(1, N_DISTRICTS + 1)]


def data_url(slug: str, fname: str) -> str:
    return f"{BASE_URL}/{slug}/data/{fname}"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    override = os.environ.get("SLOREF_DATA_DIR")
    if override:
        return Path(override)
    return project_root() / "data"


# Имена файлов состояния и журнала внутри data/
TIMESERIES_NAME = "timeseries.csv"
LOG_NAME = "scrape.log"
