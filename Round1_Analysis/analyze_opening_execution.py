from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "PAST_DATA_ROUND1"
OUT_DIR = ROOT / "Round1_Analysis" / "output"
PRODUCT = "INTARIAN_PEPPER_ROOT"


def load_prices() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(DATA_DIR.glob("prices_round_1_day_*.csv")):
        day = int(path.stem.split("_")[-1])
        df = pd.read_csv(path, sep=";")
        df["day"] = day
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df = df[(df["product"] == PRODUCT) & (df["mid_price"] > 0)].copy()
    df = df.sort_values(["day", "timestamp"]).reset_index(drop=True)
    return df


def build_markouts(df: pd.DataFrame) -> pd.DataFrame:
    for horizon in [1, 2, 5, 10, 20, 50]:
        df[f"ask_markout_{horizon}"] = (
            df.groupby("day")["mid_price"].shift(-horizon) - df["ask_price_1"]
        )
        df[f"bid_markout_{horizon}"] = (
            df.groupby("day")["mid_price"].shift(-horizon) - df["bid_price_1"]
        )
    df["spread"] = df["ask_price_1"] - df["bid_price_1"]
    return df


def save_opening_stats(df: pd.DataFrame) -> None:
    rows: list[dict[str, float | int]] = []
    for ticks in [10, 20, 30, 50]:
        for day, group in df.groupby("day"):
            early = group.head(ticks)
            row = {
                "day": day,
                "opening_ticks": ticks,
                "avg_half_spread": (early["spread"] / 2.0).mean(),
                "open_to_last_mid_move": early["mid_price"].iloc[-1] - early["mid_price"].iloc[0],
                "open_min_mid_move": early["mid_price"].min() - early["mid_price"].iloc[0],
            }
            for horizon in [1, 2, 5, 10, 20, 50]:
                row[f"avg_ask_markout_{horizon}"] = early[f"ask_markout_{horizon}"].mean()
                row[f"avg_bid_markout_{horizon}"] = early[f"bid_markout_{horizon}"].mean()
            rows.append(row)
    pd.DataFrame(rows).round(4).to_csv(OUT_DIR / "opening_execution_stats.csv", index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prices = load_prices()
    marked = build_markouts(prices)
    save_opening_stats(marked)
    print(f"Saved opening execution stats to {OUT_DIR / 'opening_execution_stats.csv'}")


if __name__ == "__main__":
    main()
