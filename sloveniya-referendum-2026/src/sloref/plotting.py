"""Графики трендов на matplotlib (безопасный headless-бэкенд Agg)."""

import matplotlib

matplotlib.use("Agg")  # до импорта pyplot: среда без дисплея

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from sloref.analysis import load_timeseries  # noqa: E402
from sloref.config import REFERENDUMS  # noqa: E402

SERIES = [
    ("turnout_pct", "явка, %", "#4C72B0"),
    ("counted_pct", "посчитано, %", "#55A868"),
    ("za_pct", "ЗА, %", "#C44E52"),
    ("proti_pct", "ПРОТИ, %", "#8172B3"),
]

TITLES = {key: title for key, _slug, title in REFERENDUMS}


def plot_trends(out_dir, data_root=None) -> list:
    """Строит по PNG на референдум из точек timeseries.csv.

    Возвращает список созданных файлов. Один наблюдённый момент — точечный
    график, несколько — линии.
    """
    from pathlib import Path
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_timeseries(data_root)
    created = []
    for ref_key, _slug, _title in REFERENDUMS:
        sub = df[df["referendum"] == ref_key]
        if sub.empty:
            continue
        x = sub["poll_time_utc"]
        single_point = len(sub) == 1
        drawn = 0
        lines = []
        for col, label, color in SERIES:
            if col not in sub.columns:
                continue
            y = pd.to_numeric(sub[col], errors="coerce")
            if not y.notna().any():
                continue
            style = "o" if single_point else "-o"
            lines.append((x, y, style, label, color))
            drawn += 1
        if not drawn:
            continue  # цифр ещё нет — пустой график не строим
        fig, ax = plt.subplots(figsize=(10, 5))
        for x, y, style, label, color in lines:
            ax.plot(x, y, style, label=label, color=color, markersize=3)
        ax.set_title(TITLES.get(ref_key, ref_key), fontsize=10)
        ax.set_ylabel("%")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        fig.autofmt_xdate()
        fig.tight_layout()
        out = out_dir / f"{ref_key}.png"
        fig.savefig(out, dpi=150)
        plt.close(fig)
        created.append(out)
    return created
