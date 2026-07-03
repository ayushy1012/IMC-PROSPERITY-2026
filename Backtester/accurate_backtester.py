"""
Accurate backtester for Prosperity 4 — wraps prosperity4bt with:
  - Custom --limit flags for Round 3+ products
  - --round and --engine options
  - Support for official .json log files and CSV data folders

Usage:
  python accurate_backtester.py <trader.py> <data_folder_or_log.json> [options]

Example:
  python accurate_backtester.py Trader/366046.py ROUND_3 --round 3 --engine queue --no-out \\
    --limit HYDROGEL_PACK:200 --limit VELVETFRUIT_EXTRACT:200 \\
    --limit VEV_4000:300 --limit VEV_4500:300 --limit VEV_5000:300 \\
    --limit VEV_5100:300 --limit VEV_5200:300 --limit VEV_5300:300 \\
    --limit VEV_5400:300 --limit VEV_5500:300 --limit VEV_6000:300 \\
    --limit VEV_6500:300
"""
import argparse
import json
import sys
import os
from pathlib import Path
from collections import defaultdict

# Patch limits BEFORE importing runner internals
import prosperity4bt.runner as runner
import prosperity4bt.__main__ as bt_main
from prosperity4bt.models import TradeMatchingMode


def parse_args():
    parser = argparse.ArgumentParser(description="Round 3 accurate backtester")
    parser.add_argument("algorithm", type=Path, help="Path to the trader .py file")
    parser.add_argument("data", type=Path, help="Path to data folder or official .json log")
    parser.add_argument("--tte", type=int, default=None, help="Force a specific TTE value")

    parser.add_argument("--round", type=int, default=3, dest="round_num", help="Round number (default: 3)")

    parser.add_argument("--engine", choices=["auto", "queue", "legacy"], default="auto")

    parser.add_argument("--match-trades", type=str, default="all",
                        choices=["all", "worse", "none"])
    parser.add_argument("--limit", action="append", default=[],
                        help="Override product limit as PRODUCT:LIMIT. Repeatable.")
    parser.add_argument("--no-out", action="store_true", help="Skip saving output log")

    parser.add_argument("--out", type=Path, default=None, help="Output log path")

    parser.add_argument("--print", dest="print_output", action="store_true")

    parser.add_argument("--no-progress", action="store_true")

    parser.add_argument("--merge-pnl", action="store_true")

    parser.add_argument("--day", type=int, default=None, help="Run only this day number")

    return parser.parse_args()


def apply_limits(limit_args):
    """Parse --limit PRODUCT:LIMIT flags and patch runner.LIMITS."""
    for item in limit_args:
        parts = item.split(":")
        if len(parts) == 2:
            product, limit = parts[0], int(parts[1])
            runner.LIMITS[product] = limit
            print(f"  Limit: {product} = {limit}")


def find_days(data_path, round_num):
    """Find available days in a data folder."""
    days = []
    for d in range(20):
        prices = data_path / f"round{round_num}" / f"prices_round_{round_num}_day_{d}.csv"
        if not prices.exists():
            prices = data_path / f"prices_round_{round_num}_day_{d}.csv"
        if prices.exists():
            days.append(d)
    return days


def main():
    args = parse_args()

    print(f"Algorithm: {args.algorithm}")
    print(f"Data: {args.data}")
    print(f"Round: {args.round_num}")

    # Apply custom limits
    if args.limit:
        apply_limits(args.limit)

    # Parse algorithm
    trader_module = bt_main.parse_algorithm(args.algorithm)
    trader_cls = trader_module.Trader

    # Determine trade matching mode
    match_mode = TradeMatchingMode[args.match_trades]

    # Determine data source
    data_path = args.data
    file_reader = None

    if data_path.suffix.lower() == ".json":
        # Official log file — not directly supported by this wrapper,
        # just use the CSV data approach
        print(f"JSON log detected: {data_path}")
        print("Note: JSON log replay requires the full accurate_backtester.")
        print("Falling back to CSV data mode if available.")
        sys.exit(1)

    # CSV data folder
    # Check if data is directly in the folder or in round<N>/ subfolder
    round_subdir = data_path / f"round{args.round_num}"
    if round_subdir.exists():
        # Data is in the expected structure: data/round3/prices_...
        file_reader = bt_main.FileSystemReader(data_path)
    else:
        # Data is directly in the folder: ROUND_3/prices_...
        # Need to create the expected structure via symlinks
        import tempfile
        tmpdir = Path(data_path) / f"_bt_tmp"
        tmpdir.mkdir(exist_ok=True)
        link_dir = tmpdir / f"round{args.round_num}"
        if not link_dir.exists():
            link_dir.symlink_to(data_path.resolve())
        file_reader = bt_main.FileSystemReader(tmpdir)

    # Find days to run
    if args.day is not None:
        days = [args.day]
    else:
        days = find_days(data_path, args.round_num)
        if not days:
            # Try with the reader
            days = []
            for d in range(20):
                try:
                    if bt_main.has_day_data(file_reader, args.round_num, d):
                        days.append(d)
                except:
                    pass

    if not days:
        print("ERROR: No data found for the specified round.")
        sys.exit(1)

    print(f"Days: {days}")
    print()

    # Run backtests
    results = []
    total_pnl = defaultdict(float)

    for day in days:
        print(f"{'=' * 60}")
        print(f"Round {args.round_num} Day {day}")
        print(f"{'=' * 60}")

        # Fix TTE for historical data backtesting!
        # The data has Day 0 = TTE 8, Day 1 = TTE 7, Day 2 = TTE 6
        if args.tte is not None:
            historical_tte = args.tte
            print(f"Injecting FORCED TTE = {historical_tte} into trader module...")
        else:
            historical_tte = 8 - day
            print(f"Injecting historical TTE = {historical_tte} into trader module...")
            
        if hasattr(trader_module, 'TTE'):
            trader_module.TTE = historical_tte

        trader = trader_cls()

        try:
            result = runner.run_backtest(
                trader,
                file_reader,
                args.round_num,
                day,
                print_output=args.print_output,
                trade_matching_mode=match_mode,
                no_names=False,
                show_progress_bar=not args.no_progress,
            )
        except Exception as e:
            print(f"ERROR on day {day}: {e}")
            import traceback
            traceback.print_exc()
            continue

        results.append(result)

        # Print per-product PnL using activity_logs
        last_ts = result.activity_logs[-1].timestamp if result.activity_logs else None
        day_total = 0
        for row in reversed(result.activity_logs):
            if row.timestamp != last_ts:
                break
            product = row.columns[2]
            pnl = row.columns[-1]
            print(f"  {product:<30} {pnl:>10.1f}")
            total_pnl[product] += pnl
            day_total += pnl
        print(f"  {'TOTAL':<30} {day_total:>10.1f}")
        print()

        # Save log if requested
        if not args.no_out and args.out:
            bt_main.write_output(result, args.out)

    # Overall summary
    if len(days) > 1:
        print(f"{'=' * 60}")
        print(f"OVERALL SUMMARY ({len(days)} days)")
        print(f"{'=' * 60}")
        grand = 0
        for product in sorted(total_pnl):
            print(f"  {product:<30} {total_pnl[product]:>10.1f}")
            grand += total_pnl[product]
        print(f"  {'GRAND TOTAL':<30} {grand:>10.1f}")


if __name__ == "__main__":
    main()
