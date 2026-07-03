"""
Deep analysis of Round 1 PAST_DATA to derive strategy improvements.
Advisor hints focus on:
1. Trend detection (slow-growing pepper root)
2. Fill price optimization (VWAP aware)
3. Order attractiveness / placement
4. Spread dynamics over time
"""
import pandas as pd
import numpy as np
import json

DATA_DIR = "PAST_DATA_ROUND1"

def load_prices():
    frames = []
    for day in [-2, -1, 0]:
        df = pd.read_csv(f"{DATA_DIR}/prices_round_1_day_{day}.csv", sep=";")
        frames.append(df)
    return pd.concat(frames).sort_values(["day", "timestamp"]).reset_index(drop=True)

def load_trades():
    frames = []
    for day in [-2, -1, 0]:
        df = pd.read_csv(f"{DATA_DIR}/trades_round_1_day_{day}.csv", sep=";")
        df["day"] = day
        frames.append(df)
    return pd.concat(frames).sort_values(["day", "timestamp"]).reset_index(drop=True)

def analyze_product(prices, trades, product):
    p = prices[prices["product"] == product].copy()
    t = trades[trades["symbol"] == product].copy() if trades is not None else pd.DataFrame()
    
    p["mid"] = p["mid_price"]
    p["spread"] = p["ask_price_1"] - p["bid_price_1"]
    
    # Microprice
    bid_v1 = p["bid_volume_1"].fillna(0)
    ask_v1 = p["ask_volume_1"].fillna(0)
    total_v1 = bid_v1 + ask_v1
    p["microprice"] = np.where(
        total_v1 > 0,
        (p["ask_price_1"] * bid_v1 + p["bid_price_1"] * ask_v1) / total_v1,
        p["mid"]
    )
    p["micro_dev"] = p["microprice"] - p["mid"]
    
    # OBI
    p["obi_l1"] = np.where(total_v1 > 0, (bid_v1 - ask_v1) / total_v1, 0.0)
    
    # Returns at various horizons
    for h in [1, 5, 10, 20, 50]:
        p[f"ret_{h}"] = p["mid"].shift(-h) - p["mid"]
    
    # EMA
    for span in [8, 36, 64]:
        p[f"ema_{span}"] = p["mid"].ewm(span=span, adjust=False).mean()
    
    p["trend_gap_8_64"] = p["ema_8"] - p["ema_64"]
    p["dev_from_slow"] = p["mid"] - p["ema_64"]
    
    print(f"\n{'='*60}")
    print(f"  {product}")
    print(f"{'='*60}")
    
    print(f"\n--- Basic Stats ---")
    print(f"  Mean Mid:     {p['mid'].mean():.2f}")
    print(f"  Std Mid:      {p['mid'].std():.2f}")
    print(f"  Min Mid:      {p['mid'].min():.2f}")
    print(f"  Max Mid:      {p['mid'].max():.2f}")
    print(f"  Mean Spread:  {p['spread'].mean():.2f}")
    print(f"  Median Spread:{p['spread'].median():.2f}")
    
    print(f"\n--- Spread Distribution ---")
    spread_counts = p["spread"].dropna().value_counts().sort_index().head(10)
    for sp, cnt in spread_counts.items():
        print(f"  Spread={sp:.0f}: {cnt} ticks ({100*cnt/len(p):.1f}%)")
    
    print(f"\n--- Predictive Correlations ---")
    for signal in ["micro_dev", "obi_l1", "trend_gap_8_64", "dev_from_slow"]:
        for h in [1, 5, 10, 20, 50]:
            corr = p[[signal, f"ret_{h}"]].corr().iloc[0, 1]
            if abs(corr) > 0.05:
                print(f"  {signal:20s} -> ret_{h:2d}: {corr:+.4f}")
    
    # Trend analysis: how does the trend_gap evolve per day?
    print(f"\n--- Per-Day Trend Summary ---")
    for day in p["day"].unique():
        dp = p[p["day"] == day]
        start_mid = dp["mid"].iloc[0]
        end_mid = dp["mid"].iloc[-1]
        daily_move = end_mid - start_mid
        mean_trend = dp["trend_gap_8_64"].mean()
        print(f"  Day {day:2d}: Start={start_mid:.1f}, End={end_mid:.1f}, Move={daily_move:+.1f}, AvgTrend={mean_trend:+.2f}")
    
    # Trade data analysis
    if len(t) > 0:
        print(f"\n--- Trade Execution Analysis ---")
        print(f"  Total trades: {len(t)}")
        print(f"  Mean trade price: {t['price'].mean():.2f}")
        print(f"  Mean trade qty:   {t['quantity'].mean():.1f}")
        
        # Match trades to L1 quotes at same timestamp
        merged = t.merge(p[["day", "timestamp", "bid_price_1", "ask_price_1", "mid"]], 
                         left_on=["day", "timestamp"], right_on=["day", "timestamp"], how="left")
        merged["trade_vs_mid"] = merged["price"] - merged["mid"]
        merged["is_buy"] = merged["price"] >= merged["ask_price_1"]
        merged["is_sell"] = merged["price"] <= merged["bid_price_1"]
        
        buys = merged[merged["is_buy"]]
        sells = merged[merged["is_sell"]]
        print(f"  Buy trades (at ask):  {len(buys)}, avg slippage vs mid: {buys['trade_vs_mid'].mean():+.2f}")
        print(f"  Sell trades (at bid): {len(sells)}, avg slippage vs mid: {sells['trade_vs_mid'].mean():+.2f}")
    
    # Volume-weighted price analysis within each tick
    print(f"\n--- Order Book Depth Distribution ---")
    for level in [1, 2, 3]:
        bv = p[f"bid_volume_{level}"].dropna()
        av = p[f"ask_volume_{level}"].dropna()
        if len(bv) > 0:
            print(f"  L{level} Bid Vol: mean={bv.mean():.1f}, median={bv.median():.0f}")
        if len(av) > 0:
            print(f"  L{level} Ask Vol: mean={av.mean():.1f}, median={av.median():.0f}")
    
    # Analyze fill quality: at which prices do the most volume trade?
    if len(t) > 0:
        vwap = (t["price"] * t["quantity"]).sum() / t["quantity"].sum()
        print(f"\n--- Fill Quality ---")
        print(f"  VWAP: {vwap:.2f} (vs mean mid {p['mid'].mean():.2f})")
        print(f"  VWAP - Mean Mid: {vwap - p['mid'].mean():+.2f}")
    
    # Autocorrelation structure
    rets = p["mid"].diff().dropna()
    print(f"\n--- Return Autocorrelation ---")
    for lag in [1, 2, 3, 5, 10]:
        ac = rets.autocorr(lag)
        print(f"  Lag {lag:2d}: {ac:+.4f}")
    
    # How often does the best bid/ask change?
    p["bid_change"] = p["bid_price_1"].diff().abs()
    p["ask_change"] = p["ask_price_1"].diff().abs()
    moves = (p["bid_change"] > 0) | (p["ask_change"] > 0)
    print(f"\n--- Quote Update Frequency ---")
    print(f"  Ticks with L1 move: {moves.sum()} / {len(p)} ({100*moves.sum()/len(p):.1f}%)")
    
    return p

def main():
    prices = load_prices()
    trades = load_trades()
    
    print("Products found:", prices["product"].unique().tolist())
    
    for product in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
        analyze_product(prices, trades, product)

if __name__ == "__main__":
    main()
