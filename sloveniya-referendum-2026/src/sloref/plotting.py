"""Trend plots on matplotlib (safe headless Agg backend)."""

import matplotlib

matplotlib.use("Agg")  # before importing pyplot: display-less environment

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from sloref.analysis import load_timeseries  # noqa: E402
from sloref.config import REFERENDUMS  # noqa: E402

SERIES = [
    ("turnout_pct", "turnout, %", "#4C72B0"),
    ("counted_pct", "counted, %", "#55A868"),
    ("za_pct", "ZA, %", "#C44E52"),
    ("proti_pct", "PROTI, %", "#8172B3"),
]

TITLES = {key: title for key, _slug, title in REFERENDUMS}


def plot_trends(out_dir, data_root=None) -> list:
    """Builds one PNG per referendum from the timeseries.csv points.

    Returns the list of created files. A single observed moment — a point
    plot, several — lines.
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
            continue  # no figures yet — skip the empty plot
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
