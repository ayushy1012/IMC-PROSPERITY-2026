from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "PAST_DATA_ROUND1"
OUTPUT_DIR = ROOT / "Round1_Analysis" / "output"
INFERENCES_PATH = ROOT / "Round1_Analysis" / "physics_signal_inferences.md"

OSMIUM = "ASH_COATED_OSMIUM"
PEPPER = "INTARIAN_PEPPER_ROOT"

OSM_WINDOW = 128
OSM_KEEP_BINS = 3
IPR_WINDOW = 64
IPR_KEEP_BINS = 2


def load_prices() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(DATA_DIR.glob("prices_round_1_day_*.csv")):
        day = int(path.stem.split("_")[-1])
        frame = pd.read_csv(path, sep=";")
        frame["day"] = day
        frames.append(frame)
    prices = pd.concat(frames, ignore_index=True)
    return prices[
        (prices["mid_price"] > 0)
        & (prices["ask_price_1"] > 0)
        & (prices["bid_price_1"] > 0)
    ].copy()


def lowpass_reconstruction(series: np.ndarray, keep_bins: int) -> np.ndarray:
    spectrum = np.fft.rfft(series)
    filtered = np.zeros_like(spectrum)
    filtered[: min(len(filtered), keep_bins + 1)] = spectrum[: min(len(filtered), keep_bins + 1)]
    return np.fft.irfft(filtered, n=len(series))


def detrend_linear(series: np.ndarray) -> tuple[np.ndarray, float, float]:
    x = np.arange(len(series), dtype=float)
    slope, intercept = np.polyfit(x, series, 1)
    trend = intercept + slope * x
    return series - trend, slope, intercept


def spectral_energy_split(series: np.ndarray) -> dict[str, float]:
    centered = series - np.mean(series)
    spectrum = np.fft.rfft(centered)
    power = np.abs(spectrum) ** 2
    power = power[1:]
    total = float(power.sum())
    if total <= 0:
        return {
            "dominant_bin": 0,
            "dominant_period_samples": math.nan,
            "low_ratio": 0.0,
            "mid_ratio": 0.0,
            "high_ratio": 0.0,
        }
    dominant_offset = int(np.argmax(power)) + 1
    dominant_period = len(series) / dominant_offset if dominant_offset > 0 else math.nan
    return {
        "dominant_bin": dominant_offset,
        "dominant_period_samples": dominant_period,
        "low_ratio": float(power[:5].sum() / total),
        "mid_ratio": float(power[5:20].sum() / total),
        "high_ratio": float(power[20:].sum() / total),
    }


def build_forward_returns(prices: pd.DataFrame) -> pd.DataFrame:
    df = prices.sort_values(["product", "day", "timestamp"]).copy()
    df["fwd5"] = df.groupby(["product", "day"])["mid_price"].shift(-5) - df["mid_price"]
    return df


def summarize_day_spectra(prices: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for (product, day), group in prices.groupby(["product", "day"]):
        mids = group["mid_price"].to_numpy(dtype=float)
        if product == PEPPER:
            processed, slope, _ = detrend_linear(mids)
            split = spectral_energy_split(processed)
            split["trend_slope"] = slope
        else:
            split = spectral_energy_split(mids)
            split["trend_slope"] = math.nan
        rows.append({"product": product, "day": day, **split})
    return pd.DataFrame(rows)


def rolling_spectral_features(prices: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    prices = build_forward_returns(prices)
    for (product, day), group in prices.groupby(["product", "day"]):
        group = group.sort_values("timestamp").reset_index(drop=True)
        mids = group["mid_price"].to_numpy(dtype=float)
        timestamps = group["timestamp"].to_numpy(dtype=int)
        fwd5 = group["fwd5"].to_numpy(dtype=float)

        if product == OSMIUM:
            window = OSM_WINDOW
            keep_bins = OSM_KEEP_BINS
            for idx in range(window - 1, len(group) - 5):
                window_series = mids[idx - window + 1 : idx + 1]
                lowpass = lowpass_reconstruction(window_series, keep_bins)
                spectrum = np.fft.rfft(window_series - window_series.mean())
                power = np.abs(spectrum[1:]) ** 2
                total_power = float(power.sum())
                low_ratio = float(power[:keep_bins].sum() / total_power) if total_power > 0 else 0.0
                rows.append(
                    {
                        "product": product,
                        "day": day,
                        "timestamp": int(timestamps[idx]),
                        "spectral_dev": float(window_series[-1] - lowpass[-1]),
                        "spectral_slope": float(lowpass[-1] - lowpass[-2]),
                        "spectral_ratio": low_ratio,
                        "fwd5": float(fwd5[idx]),
                    }
                )
            continue

        window = IPR_WINDOW
        keep_bins = IPR_KEEP_BINS
        for idx in range(window - 1, len(group) - 5):
            window_series = mids[idx - window + 1 : idx + 1]
            residual, slope, _ = detrend_linear(window_series)
            lowpass = lowpass_reconstruction(residual, keep_bins)
            spectrum = np.fft.rfft(residual - residual.mean())
            power = np.abs(spectrum[1:]) ** 2
            total_power = float(power.sum())
            low_ratio = float(power[:keep_bins].sum() / total_power) if total_power > 0 else 0.0
            rows.append(
                {
                    "product": product,
                    "day": day,
                    "timestamp": int(timestamps[idx]),
                    "spectral_dev": float(residual[-1] - lowpass[-1]),
                    "spectral_slope": float(lowpass[-1] - lowpass[-2]),
                    "spectral_ratio": low_ratio,
                    "trend_slope": float(slope),
                    "fwd5": float(fwd5[idx]),
                }
            )
    return pd.DataFrame(rows)


def summarize_feature_predictiveness(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for product, group in features.groupby("product"):
        for feature in ["spectral_dev", "spectral_slope", "spectral_ratio"]:
            corr = group[[feature, "fwd5"]].corr().iloc[0, 1]
            rows.append(
                {
                    "product": product,
                    "feature": feature,
                    "corr_fwd5": corr,
                }
            )
    return pd.DataFrame(rows)


def summarize_quantile_markouts(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for product, group in features.groupby("product"):
        bucketed = group.dropna(subset=["spectral_dev", "fwd5"]).copy()
        bucketed["bucket"] = pd.qcut(bucketed["spectral_dev"], 10, duplicates="drop")
        summary = (
            bucketed.groupby("bucket", observed=False)["fwd5"]
            .agg(["mean", "count"])
            .reset_index()
            .rename(columns={"mean": "mean_fwd5"})
        )
        for _, row in summary.iterrows():
            rows.append(
                {
                    "product": product,
                    "bucket": str(row["bucket"]),
                    "mean_fwd5": float(row["mean_fwd5"]),
                    "count": int(row["count"]),
                }
            )
    return pd.DataFrame(rows)


def write_inference_markdown(
    day_summaries: pd.DataFrame,
    feature_summary: pd.DataFrame,
    quantiles: pd.DataFrame,
) -> None:
    osm_day = day_summaries[day_summaries["product"] == OSMIUM]
    pepper_day = day_summaries[day_summaries["product"] == PEPPER]
    osm_corr = feature_summary[
        (feature_summary["product"] == OSMIUM) & (feature_summary["feature"] == "spectral_dev")
    ]["corr_fwd5"].iloc[0]
    pepper_corr = feature_summary[
        (feature_summary["product"] == PEPPER) & (feature_summary["feature"] == "spectral_dev")
    ]["corr_fwd5"].iloc[0]

    osm_low = quantiles[quantiles["product"] == OSMIUM]["mean_fwd5"].iloc[0]
    osm_high = quantiles[quantiles["product"] == OSMIUM]["mean_fwd5"].iloc[-1]
    pepper_low = quantiles[quantiles["product"] == PEPPER]["mean_fwd5"].iloc[0]
    pepper_high = quantiles[quantiles["product"] == PEPPER]["mean_fwd5"].iloc[-1]

    text = f"""# Round 1 Physics Signal Inferences

## Core Read

- `ASH_COATED_OSMIUM` has a genuine low-frequency wave under the book noise. On the full-day spectra, low-frequency energy accounts for `{osm_day["low_ratio"].mean():.3f}` on average, and the dominant period is long (`{osm_day["dominant_period_samples"].median():.1f}` samples median).
- `INTARIAN_PEPPER_ROOT` is the opposite: after removing the linear drift, the residual is almost entirely high-frequency chatter. High-frequency energy averages `{pepper_day["high_ratio"].mean():.3f}` of residual power.
- The most useful spectral feature for both products is the deviation of the live price from a low-pass reconstruction of the recent path.

## Trading Implications

- For `ASH_COATED_OSMIUM`, the filtered wave is tradable mean reversion:
  - `corr(spectral_dev, fwd5) = {osm_corr:.4f}`
  - cheapest decile mean `fwd5 = {osm_low:.3f}`
  - richest decile mean `fwd5 = {osm_high:.3f}`
- For `INTARIAN_PEPPER_ROOT`, the filtered residual is an execution filter, not a macro trend model:
  - `corr(spectral_dev, fwd5) = {pepper_corr:.4f}`
  - cheapest decile mean `fwd5 = {pepper_low:.3f}`
  - richest decile mean `fwd5 = {pepper_high:.3f}`
- Pepper's macro move is still the slow drift. The spectral signal helps decide whether the current print is noisy-rich or noisy-cheap relative to that drift.

## Bot Changes To Keep

- Add a rolling low-pass fair adjustment for osmium and fade excursions away from that filtered wave.
- Keep pepper as a drift-carry product, but gate execution with a detrended spectral residual signal so we buy more readily when the residual is cheap and lean back when it is noisy-rich.
- Do not use the pepper spectral read as a reason to cross the book aggressively at the open; the residual mean reverts, but the opening spread still dominates short-horizon markout.
"""
    INFERENCES_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prices = load_prices()
    day_summaries = summarize_day_spectra(prices)
    features = rolling_spectral_features(prices)
    feature_summary = summarize_feature_predictiveness(features)
    quantiles = summarize_quantile_markouts(features)

    day_summaries.round(6).to_csv(OUTPUT_DIR / "spectral_day_summary.csv", index=False)
    features.round(6).to_csv(OUTPUT_DIR / "spectral_feature_rows.csv", index=False)
    feature_summary.round(6).to_csv(OUTPUT_DIR / "spectral_feature_summary.csv", index=False)
    quantiles.round(6).to_csv(OUTPUT_DIR / "spectral_quantile_markouts.csv", index=False)
    write_inference_markdown(day_summaries, feature_summary, quantiles)

    print(f"Saved spectral analysis outputs to {OUTPUT_DIR}")
    print(f"Saved inference notes to {INFERENCES_PATH}")


if __name__ == "__main__":
    main()
