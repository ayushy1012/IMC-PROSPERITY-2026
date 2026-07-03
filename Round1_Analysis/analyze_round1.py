from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "PAST_DATA_ROUND1"
OUTPUT_DIR = ROOT / "Round1_Analysis" / "output"
CACHE_DIR = ROOT / ".matplotlib_cache"

os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OSMIUM = "ASH_COATED_OSMIUM"
PEPPER = "INTARIAN_PEPPER_ROOT"


def load_prices() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(DATA_DIR.glob("prices_round_1_day_*.csv")):
        day = int(path.stem.split("_")[-1])
        df = pd.read_csv(path, sep=";")
        df["day"] = day
        frames.append(df)
    prices = pd.concat(frames, ignore_index=True)
    prices = prices[
        (prices["mid_price"] > 0)
        & (prices["ask_price_1"] > 0)
        & (prices["bid_price_1"] > 0)
    ].copy()
    return prices


def load_trades() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(DATA_DIR.glob("trades_round_1_day_*.csv")):
        day = int(path.stem.split("_")[-1])
        df = pd.read_csv(path, sep=";")
        df["day"] = day
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def build_features(prices: pd.DataFrame) -> pd.DataFrame:
    df = prices.sort_values(["product", "day", "timestamp"]).copy()

    bid_vol = df["bid_volume_1"].fillna(0.0)
    ask_vol = df["ask_volume_1"].fillna(0.0)
    denom = bid_vol + ask_vol

    df["spread"] = df["ask_price_1"] - df["bid_price_1"]
    df["obi1"] = np.where(denom > 0, (bid_vol - ask_vol) / denom, 0.0)
    df["microprice"] = np.where(
        denom > 0,
        (df["bid_price_1"] * ask_vol + df["ask_price_1"] * bid_vol) / denom,
        df["mid_price"],
    )
    df["micro_dev"] = df["microprice"] - df["mid_price"]

    df["ret1"] = df.groupby(["product", "day"])["mid_price"].diff()
    df["fwd1"] = df.groupby(["product", "day"])["mid_price"].shift(-1) - df["mid_price"]
    df["fwd5"] = df.groupby(["product", "day"])["mid_price"].shift(-5) - df["mid_price"]
    df["ema20"] = df.groupby(["product", "day"])["mid_price"].transform(
        lambda s: s.ewm(span=20, adjust=False).mean()
    )
    df["dev20"] = df["mid_price"] - df["ema20"]

    day_start = (
        df.groupby(["product", "day"], as_index=False)
        .first()[["product", "day", "timestamp", "mid_price"]]
        .rename(columns={"timestamp": "start_ts", "mid_price": "start_mid"})
    )
    df = df.merge(day_start, on=["product", "day"], how="left")

    df["trend_fair"] = np.where(
        df["product"] == PEPPER,
        df["start_mid"] + 0.001 * (df["timestamp"] - df["start_ts"]),
        np.nan,
    )
    df["pepper_resid"] = np.where(
        df["product"] == PEPPER,
        df["mid_price"] - df["trend_fair"],
        np.nan,
    )

    return df


def save_day_summary(df: pd.DataFrame, trades: pd.DataFrame) -> None:
    summary = (
        df.groupby(["product", "day"], as_index=False)
        .agg(
            rows=("mid_price", "size"),
            mid_mean=("mid_price", "mean"),
            mid_std=("mid_price", "std"),
            spread_mean=("spread", "mean"),
            spread_median=("spread", "median"),
            mid_start=("mid_price", "first"),
            mid_end=("mid_price", "last"),
        )
        .round(4)
    )
    trade_summary = (
        trades.groupby(["symbol", "day"], as_index=False)
        .agg(trade_count=("price", "size"), trade_volume=("quantity", "sum"))
        .rename(columns={"symbol": "product"})
    )
    summary = summary.merge(trade_summary, on=["product", "day"], how="left")
    summary.to_csv(OUTPUT_DIR / "day_summary.csv", index=False)


def save_signal_summary(df: pd.DataFrame) -> None:
    rows: list[dict[str, float | str | int]] = []
    for (product, day), group in df.groupby(["product", "day"]):
        group = group.dropna(subset=["fwd1", "fwd5"])
        for feature in ["ret1", "obi1", "micro_dev", "dev20"]:
            rows.append(
                {
                    "product": product,
                    "day": day,
                    "feature": feature,
                    "corr_fwd1": group[[feature, "fwd1"]].corr().iloc[0, 1],
                    "corr_fwd5": group[[feature, "fwd5"]].corr().iloc[0, 1],
                }
            )
        if product == PEPPER:
            rows.append(
                {
                    "product": product,
                    "day": day,
                    "feature": "pepper_resid",
                    "corr_fwd1": group[["pepper_resid", "fwd1"]].corr().iloc[0, 1],
                    "corr_fwd5": group[["pepper_resid", "fwd5"]].corr().iloc[0, 1],
                }
            )
    pd.DataFrame(rows).round(6).to_csv(OUTPUT_DIR / "signal_summary.csv", index=False)


def save_quantile_markouts(df: pd.DataFrame) -> None:
    tables: list[pd.DataFrame] = []
    configs = [
        (OSMIUM, "obi1"),
        (OSMIUM, "micro_dev"),
        (OSMIUM, "dev20"),
        (PEPPER, "pepper_resid"),
        (PEPPER, "obi1"),
        (PEPPER, "micro_dev"),
    ]
    for product, feature in configs:
        group = df[df["product"] == product].dropna(subset=[feature, "fwd1", "fwd5"]).copy()
        group["bucket"] = pd.qcut(group[feature], 10, duplicates="drop")
        summary = (
            group.groupby("bucket", observed=False)[["fwd1", "fwd5"]]
            .mean()
            .reset_index()
            .assign(product=product, feature=feature)
        )
        tables.append(summary)
    pd.concat(tables, ignore_index=True).round(4).to_csv(
        OUTPUT_DIR / "quantile_markouts.csv",
        index=False,
    )


def save_pepper_trend_summary(df: pd.DataFrame) -> None:
    pepper = df[df["product"] == PEPPER].copy()
    rows: list[dict[str, float | int]] = []
    for day, group in pepper.groupby("day"):
        x = group["timestamp"].to_numpy(dtype=float)
        y = group["mid_price"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        residual = y - (intercept + slope * x)
        rows.append(
            {
                "day": day,
                "slope": slope,
                "intercept": intercept,
                "resid_mean": residual.mean(),
                "resid_std": residual.std(),
                "resid_min": residual.min(),
                "resid_max": residual.max(),
            }
        )
    pd.DataFrame(rows).round(6).to_csv(OUTPUT_DIR / "pepper_trend_summary.csv", index=False)


def save_regressions(df: pd.DataFrame) -> None:
    rows: list[dict[str, float | str]] = []

    osmium = df[df["product"] == OSMIUM].dropna(subset=["fwd1"]).copy()
    x_osm = np.column_stack(
        [
            np.ones(len(osmium)),
            osmium["micro_dev"].to_numpy(),
            osmium["obi1"].to_numpy(),
            osmium["dev20"].to_numpy(),
        ]
    )
    y_osm = osmium["fwd1"].to_numpy()
    coef_osm = np.linalg.pinv(x_osm) @ y_osm
    for name, value in zip(["bias", "micro_dev", "obi1", "dev20"], coef_osm):
        rows.append({"product": OSMIUM, "target": "fwd1", "term": name, "coef": value})

    pepper = df[df["product"] == PEPPER].dropna(subset=["fwd1"]).copy()
    x_pepper = np.column_stack(
        [
            np.ones(len(pepper)),
            pepper["micro_dev"].to_numpy(),
            pepper["obi1"].to_numpy(),
            pepper["pepper_resid"].to_numpy(),
        ]
    )
    y_pepper = pepper["fwd1"].to_numpy()
    coef_pepper = np.linalg.pinv(x_pepper) @ y_pepper
    for name, value in zip(["bias", "micro_dev", "obi1", "pepper_resid"], coef_pepper):
        rows.append({"product": PEPPER, "target": "fwd1", "term": name, "coef": value})

    pd.DataFrame(rows).round(6).to_csv(OUTPUT_DIR / "regression_coefficients.csv", index=False)


def plot_mid_paths(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    osmium = df[df["product"] == OSMIUM]
    pepper = df[df["product"] == PEPPER]

    for day, group in osmium.groupby("day"):
        axes[0].plot(group["timestamp"], group["mid_price"], label=f"day {day}")
    axes[0].set_title("ASH_COATED_OSMIUM mid path")
    axes[0].set_ylabel("mid")
    axes[0].legend()

    for day, group in pepper.groupby("day"):
        axes[1].plot(group["timestamp"], group["mid_price"], label=f"day {day}")
    axes[1].set_title("INTARIAN_PEPPER_ROOT mid path")
    axes[1].set_xlabel("timestamp")
    axes[1].set_ylabel("mid")
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "mid_paths.png", dpi=160)
    plt.close(fig)


def plot_pepper_residuals(df: pd.DataFrame) -> None:
    pepper = df[df["product"] == PEPPER]
    fig, ax = plt.subplots(figsize=(12, 4))
    for day, group in pepper.groupby("day"):
        ax.plot(group["timestamp"], group["pepper_resid"], label=f"day {day}")
    ax.axhline(0.0, color="black", linewidth=1, alpha=0.6)
    ax.set_title("INTARIAN_PEPPER_ROOT detrended residual")
    ax.set_xlabel("timestamp")
    ax.set_ylabel("residual")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "pepper_detrended_residuals.png", dpi=160)
    plt.close(fig)


def plot_feature_markouts(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    configs = [
        (OSMIUM, "obi1", "Osmium OBI"),
        (OSMIUM, "micro_dev", "Osmium micro dev"),
        (OSMIUM, "dev20", "Osmium EMA dev"),
        (PEPPER, "pepper_resid", "Pepper residual"),
        (PEPPER, "obi1", "Pepper OBI"),
        (PEPPER, "micro_dev", "Pepper micro dev"),
    ]

    for ax, (product, feature, title) in zip(axes.flatten(), configs):
        group = df[df["product"] == product].dropna(subset=[feature, "fwd5"]).copy()
        group["bucket"] = pd.qcut(group[feature], 10, duplicates="drop")
        summary = group.groupby("bucket", observed=False)["fwd5"].mean().reset_index()
        ax.bar(range(len(summary)), summary["fwd5"])
        ax.set_title(title)
        ax.set_xlabel("quantile")
        ax.set_ylabel("mean fwd5")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "feature_markouts.png", dpi=160)
    plt.close(fig)


def write_summary_markdown() -> None:
    text = """# Round 1 Analysis Summary

- `ASH_COATED_OSMIUM` is a stationary spread-capture product around 10,000 with strong top-of-book imbalance and short-term mean reversion.
- `INTARIAN_PEPPER_ROOT` has an almost perfectly linear intraday drift of about `0.001` price units per timestamp plus smaller residual mean reversion.
- A pure max-long accumulation in pepper root is already highly profitable on every provided day, so the trader should treat it as a deliberate inventory-carry trade rather than a symmetric market-making product.
- Osmium still benefits from a fair-value maker built from `micro_dev`, `obi1`, and EMA deviation.
"""
    (OUTPUT_DIR / "analysis_summary.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    prices = load_prices()
    trades = load_trades()
    features = build_features(prices)

    save_day_summary(features, trades)
    save_signal_summary(features)
    save_quantile_markouts(features)
    save_pepper_trend_summary(features)
    save_regressions(features)
    plot_mid_paths(features)
    plot_pepper_residuals(features)
    plot_feature_markouts(features)
    write_summary_markdown()

    print(f"Saved analysis outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
