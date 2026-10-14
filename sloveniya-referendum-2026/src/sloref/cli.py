"""CLI: sloref fetch | summary | plot."""

import argparse
import sys

from sloref import __version__
from sloref.analysis import summary_table
from sloref.config import data_dir
from sloref.httpclient import force_ipv4
from sloref.plotting import plot_trends
from sloref.scraper import poll_once, run_loop
from sloref.storage import Store


def cmd_fetch(args: argparse.Namespace) -> int:
    force_ipv4()
    store = Store(data_dir())
    if args.loop:
        run_loop(store, interval=args.interval, include_volisca=args.volisca)
    else:
        poll_once(store, include_volisca=args.volisca)
    return 0


def cmd_summary(_args: argparse.Namespace) -> int:
    import pandas as pd
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 60)
    store = Store(data_dir())
    print(summary_table(store).to_string(index=False))
    return 0


def cmd_plot(args: argparse.Namespace) -> int:
    out = args.out or (data_dir() / "plots")
    created = plot_trends(out, data_root=data_dir())
    if not created:
        print("No points for plots in timeseries.csv yet "
              "(they appear when the official figures change).")
    for path in created:
        print(path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sloref",
        description="Monitoring of the 11 Oct 2026 Slovenian referendum data "
                    "(source: DVK, volitve.dvk-rs.si)")
    parser.add_argument("--version", action="version",
                        version=f"sloref {__version__}")

    sub = parser.add_subparsers(dest="command")

    p_fetch = sub.add_parser(
        "fetch", help="download the data (a single poll or a loop)")
    p_fetch.add_argument("--loop", action="store_true",
                         help="run in a loop")
    p_fetch.add_argument("--interval", type=int, default=900,
                         help="loop interval in seconds (default 900 = 15 minutes)")
    p_fetch.add_argument("--volisca", action="store_true",
                         help="additionally fetch per-precinct results "
                              "(88 files × 4 referendums)")
    p_fetch.set_defaults(func=cmd_fetch)

    p_summary = sub.add_parser(
        "summary", help="summary table of the current figures for all referendums")
    p_summary.set_defaults(func=cmd_summary)

    p_plot = sub.add_parser(
        "plot", help="PNG trend plots from timeseries.csv")
    p_plot.add_argument("--out", default=None,
                        help="directory for PNGs (default data/plots)")
    p_plot.set_defaults(func=cmd_plot)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
