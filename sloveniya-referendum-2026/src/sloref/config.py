"""Configuration: referendums, data files, paths.

Official format description — DVK, «Referendumi 2026 - datoteke s podatki»
(copy in the project's docs/).
"""

import os
from pathlib import Path

BASE_URL = "https://volitve.dvk-rs.si"

# (key, slug on the server, title)
REFERENDUMS: list[tuple[str, str, str]] = [
    ("preiskava", "referendum-preiskava",
     "Legislative referendum on ZPPre-B (parliamentary investigation act)"),
    ("socialna_pomoc", "referendum-socialna-pomoc",
     "Advisory: social assistance and community work"),
    ("volilna_pravica", "referendum-volilna-pravica-tujcev",
     "Advisory: voting rights in local elections"),
    ("rtv_prispevek", "referendum-rtv-prispevek",
     "Advisory: abolishing the mandatory RTV Slovenija contribution"),
]

BASE_FILES: list[str] = [
    "udelezba.json", "rezultati.json",
    "udelezba.csv", "rezultati.csv",
    "izvoz.xlsx",
]

# volisca_EE_OO.json: 8 electoral units (volilna enota) × 11 districts (okraj)
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


# State and log file names inside data/
TIMESERIES_NAME = "timeseries.csv"
LOG_NAME = "scrape.log"
