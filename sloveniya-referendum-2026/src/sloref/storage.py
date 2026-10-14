"""Storage: latest versions, change snapshots, trends, log.

Layout inside the data directory:
  latest/<referendum>/<file>             — latest version (overwritten)
  raw/<date>/<time>/<referendum>/<file>  — snapshot of changed files only
  latest/<referendum>/_state.json        — signature of the latest figures (for trends)
  timeseries.csv                         — timeline of nationwide figures
  scrape.log                             — log
"""

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

from sloref.config import LOG_NAME, TIMESERIES_NAME
from sloref.models import Aggregates

TIMESERIES_COLUMNS = [
    "poll_time_utc", "referendum", "source_datum",
    "turnout_case", "electorate", "voters", "turnout_pct",
    "counted_pct", "ballots", "valid", "invalid",
    "za", "za_pct", "proti", "proti_pct",
]


def fmt_pct(x: float | None) -> str:
    return "" if x is None else f"{x * 100:.2f}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.latest = self.root / "latest"
        self.raw = self.root / "raw"
        self.timeseries = self.root / TIMESERIES_NAME
        self.logfile = self.root / LOG_NAME
        for d in (self.latest, self.raw, self.root):
            d.mkdir(parents=True, exist_ok=True)

    # --- log ---------------------------------------------------------------

    def log(self, msg: str) -> None:
        line = f"[{dt.datetime.now().isoformat(timespec='seconds')}] {msg}"
        print(line, flush=True)
        try:
            with open(self.logfile, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    # --- files --------------------------------------------------------------

    def save_file(self, ref_key: str, fname: str, data: bytes,
                  poll_stamp: str) -> bool:
        """Saves the file: a raw/ snapshot only if the content changed,
        latest/ is updated always. Returns True if the file changed."""
        latest_path = self.latest / ref_key / fname
        changed = (not latest_path.exists()) or \
                  sha256(latest_path.read_bytes()) != sha256(data)

        if changed:
            snapshot_dir = self.raw / poll_stamp[:10] / poll_stamp[11:16] / ref_key
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            (snapshot_dir / fname).write_bytes(data)

        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_bytes(data)
        return changed

    def read_latest(self, ref_key: str, fname: str) -> bytes | None:
        path = self.latest / ref_key / fname
        return path.read_bytes() if path.exists() else None

    # --- trends -------------------------------------------------------------

    def aggregates(self, ref_key: str) -> Aggregates:
        from sloref.models import extract_aggregates
        return extract_aggregates(
            ref_key,
            self.read_latest(ref_key, "rezultati.json"),
            self.read_latest(ref_key, "udelezba.json"),
        )

    def append_timeseries(self, agg: Aggregates, poll_time_utc: str) -> bool:
        """Appends a row to timeseries.csv if the figures changed since
        the last time. Returns True if a row was added."""
        state_path = self.latest / agg.referendum / "_state.json"
        signature = agg.signature()

        if state_path.exists():
            try:
                if json.loads(state_path.read_text(encoding="utf-8"))["sig"] == signature:
                    return False
            except (ValueError, KeyError, OSError):
                pass

        new_file = not self.timeseries.exists()
        with open(self.timeseries, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            if new_file:
                w.writerow(TIMESERIES_COLUMNS)
            w.writerow([
                poll_time_utc, agg.referendum, agg.source_datum or "",
                agg.turnout_case or "", agg.electorate or "", agg.voters or "",
                fmt_pct(agg.turnout_pct), fmt_pct(agg.counted_pct),
                agg.ballots or "", agg.valid or "", agg.invalid or "",
                agg.za or "", fmt_pct(agg.za_pct),
                agg.proti or "", fmt_pct(agg.proti_pct),
            ])

        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({"sig": signature}, ensure_ascii=False),
                              encoding="utf-8")
        return True
