"""Анализ на pandas: загрузка трендов и сводка текущего состояния."""

from pathlib import Path

import pandas as pd

from sloref.config import REFERENDUMS, TIMESERIES_NAME, data_dir
from sloref.storage import Store


def timeseries_path(data_root: Path | None = None) -> Path:
    root = Path(data_root) if data_root else data_dir()
    return root / TIMESERIES_NAME


def load_timeseries(data_root: Path | None = None) -> pd.DataFrame:
    """Читает data/timeseries.csv в DataFrame; время — в datetime (UTC)."""
    path = timeseries_path(data_root)
    if not path.exists():
        return pd.DataFrame(columns=["poll_time_utc", "referendum"])
    df = pd.read_csv(path, sep=";")
    df["poll_time_utc"] = pd.to_datetime(df["poll_time_utc"], utc=True)
    return df.sort_values(["referendum", "poll_time_utc"]).reset_index(drop=True)


def summary_table(store: Store) -> pd.DataFrame:
    """Текущее состояние каждого референдума из свежескачанных файлов."""
    rows = []
    for ref_key, _slug, title in REFERENDUMS:
        agg = store.aggregates(ref_key)
        rows.append({
            "referendum": ref_key,
            "название": title,
            "обновлено на сервере": agg.source_datum,
            "явка, %": None if agg.turnout_pct is None else round(agg.turnout_pct * 100, 2),
            "посчитано, %": None if agg.counted_pct is None else round(agg.counted_pct * 100, 2),
            "ЗА": agg.za,
            "ЗА, %": None if agg.za_pct is None else round(agg.za_pct * 100, 2),
            "ПРОТИ": agg.proti,
            "ПРОТИ, %": None if agg.proti_pct is None else round(agg.proti_pct * 100, 2),
        })
    return pd.DataFrame(rows)
