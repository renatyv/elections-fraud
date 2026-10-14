"""Polling logic: a single fetch cycle and the endless mode."""

import datetime as dt
import time

from sloref.config import BASE_FILES, REFERENDUMS, volisca_files
from sloref.httpclient import FetchError, build_client, fetch
from sloref.storage import Store, fmt_pct

POLITENESS_DELAY = 0.25  # s between requests


def status_line(agg) -> str:
    return (f"  {agg.referendum:<17} datum={agg.source_datum or '—'} | "
            f"turnout={fmt_pct(agg.turnout_pct) or '—'}% "
            f"({agg.voters if agg.voters is not None else '—'} voters) | "
            f"counted={fmt_pct(agg.counted_pct) or '—'}% | "
            f"ZA={agg.za if agg.za is not None else '—'} "
            f"({fmt_pct(agg.za_pct) or '—'}%) | "
            f"PROTI={agg.proti if agg.proti is not None else '—'} "
            f"({fmt_pct(agg.proti_pct) or '—'}%)")


def poll_once(store: Store, include_volisca: bool = False) -> None:
    poll_time = dt.datetime.now(dt.UTC)
    poll_stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    store.log(f"=== Poll {poll_stamp} "
              f"(volisca={'yes' if include_volisca else 'no'}) ===")

    errors = 0
    with build_client() as client:
        for ref_key, slug, _title in REFERENDUMS:
            files = BASE_FILES + (volisca_files() if include_volisca else [])

            changed = failed = pending = 0
            for fname in files:
                try:
                    data = fetch(client, f"{slug}/data/{fname}")
                except FetchError as e:
                    store.log(f"ERROR {ref_key}/{fname}: {e}")
                    errors += 1
                    failed += 1
                    continue
                time.sleep(POLITENESS_DELAY)

                if data is None:
                    pending += 1
                    store.log(f"no data (404): {ref_key}/{fname}")
                    continue

                try:
                    if store.save_file(ref_key, fname, data, poll_stamp):
                        changed += 1
                        store.log(f"updated: {ref_key}/{fname} ({len(data)} bytes)")
                except OSError as e:
                    store.log(f"WRITE ERROR {ref_key}/{fname}: {e}")
                    errors += 1

            agg = store.aggregates(ref_key)
            if store.append_timeseries(agg, poll_time.isoformat(timespec="seconds")):
                store.log(f"new trend point: {ref_key} "
                          f"(nationwide figures changed)")
            store.log(status_line(agg))
            store.log(f"  [{ref_key}] files: updated={changed}, unchanged="
                      f"{len(files) - changed - failed - pending}, "
                      f"not yet={pending}, errors={failed}")

    if errors:
        store.log(f"WARNING: errors during the poll: {errors}")


def run_loop(store: Store, interval: int = 900, include_volisca: bool = False) -> None:
    store.log(f"starting the endless loop, interval {interval} s. Stop: Ctrl+C.")
    while True:
        try:
            poll_once(store, include_volisca)
        except Exception as e:  # noqa: BLE001 — the loop must not crash
            store.log(f"LOOP ERROR (continuing): {e}")
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            store.log("stopped by the user")
            return
