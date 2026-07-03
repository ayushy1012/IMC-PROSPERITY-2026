"""
Deeper analysis:
1. OSMIUM: Spread is ~16, NOT 2. This changes everything.
2. IPR: Has a clear +1000/day upward drift. Spread ~13.
3. Both have -0.5 lag-1 autocorrelation (pure mean reversion tick-to-tick)
4. Both have -0.70 dev_from_slow correlation (strong slow EMA mean reversion)
5. Need to analyze: passive fill rates, how much edge we leave by posting at best+1 vs best+2
"""
import pandas as pd
import numpy as np

DATA_DIR = "PAST_DATA_ROUND1"

def load_prices():
    frames = []
    for day in [-2, -1, 0]:
        df = pd.read_csv(f"{DATA_DIR}/prices_round_1_day_{day}.csv", sep=";")
        frames.append(df)
    return pd.concat(frames).sort_values(["day", "timestamp"]).reset_index(drop=True)

def analyze_fill_optimization():
    prices = load_prices()
    
    for product in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
        p = prices[prices["product"] == product].copy()
        p["spread"] = p["ask_price_1"] - p["bid_price_1"]
        p["mid"] = p["mid_price"]
        
        # Filter out broken rows (mid=0)
        p = p[p["mid"] > 0].copy()
        
        print(f"\n{'='*60}")
        print(f"  {product} - FILL OPTIMIZATION ANALYSIS")
        print(f"{'='*60}")
        
        # What fraction of the spread can we capture?
        print(f"\n--- Spread Stats (filtered) ---")
        print(f"  Mean spread: {p['spread'].mean():.2f}")
        print(f"  Median spread: {p['spread'].median():.0f}")
        print(f"  Std spread: {p['spread'].std():.2f}")
        
        # If we post at best_bid+1, how close are we to best_ask?
        # The "gap" tells us how much room there is for improvement
        p["bid_gap_to_ask"] = p["ask_price_1"] - (p["bid_price_1"] + 1)
        p["ask_gap_to_bid"] = (p["ask_price_1"] - 1) - p["bid_price_1"]
        
        print(f"\n--- Posting at best+1 / best-1 ---")
        print(f"  Post bid = best_bid+1: gap to ask = {p['bid_gap_to_ask'].mean():.1f}")
        print(f"  Post ask = best_ask-1: gap to bid = {p['ask_gap_to_bid'].mean():.1f}")
        
        # How often does the next tick's bid move UP to our post level?
        # i.e., if I post at best_bid+1, how often does the next tick's best_bid >= my post?
        p["next_bid"] = p["bid_price_1"].shift(-1)
        p["next_ask"] = p["ask_price_1"].shift(-1)
        
        for offset in [1, 2, 3, 4, 5]:
            post_bid = p["bid_price_1"] + offset
            post_ask = p["ask_price_1"] - offset
            
            # Bid fills if next tick someone sells at our price (next_ask <= post_bid)
            bid_filled = (p["next_ask"] <= post_bid).mean()
            # Ask fills if next tick someone buys at our price (next_bid >= post_ask)
            ask_filled = (p["next_bid"] >= post_ask).mean()
            
            print(f"\n  Offset={offset}:")
            print(f"    Bid at best_bid+{offset}: fill rate = {100*bid_filled:.1f}%")
            print(f"    Ask at best_ask-{offset}: fill rate = {100*ask_filled:.1f}%")
        
        # For IPR specifically: analyze the drift
        if product == "INTARIAN_PEPPER_ROOT":
            print(f"\n--- TREND / DRIFT STRUCTURE ---")
            p["ema_64"] = p["mid"].ewm(span=64, adjust=False).mean()
            p["ema_8"] = p["mid"].ewm(span=8, adjust=False).mean()
            p["trend"] = p["ema_8"] - p["ema_64"]
            
            # What's the per-tick drift?
            p["tick_return"] = p["mid"].diff()
            mean_drift = p["tick_return"].mean()
            print(f"  Mean per-tick drift: {mean_drift:+.4f}")
            print(f"  Per 100 ticks: {100*mean_drift:+.2f}")
            print(f"  Per 1000 ticks (=1 day): ~{1000*mean_drift:+.1f}")
            
            # Fair value should incorporate this drift
            # The advisor says: "estimate what a fair value might look like under current conditions"
            # => fair = slow_ema + drift_adjustment
            # Current IPR_BASE_DRIFT = 2.9891 means the fair is shifted up by ~3 per tick
            print(f"  (Current IPR_BASE_DRIFT = 2.9891)")
            
            # How much does trend_gap predict the DIRECTION of next-50 returns?
            # This tells us if trend-following or mean-reversion is better
            p["ret_50_sign"] = np.sign(p["mid"].shift(-50) - p["mid"])
            p["trend_sign"] = np.sign(p["trend"])
            agreement = (p["ret_50_sign"] == p["trend_sign"]).mean()
            print(f"  Trend direction agrees with 50-tick return: {100*agreement:.1f}%")
            # Since corr is negative, trend is mean-reverting even on 50-tick horizon
            
        # Analyze: what if we post DEEPER into the book?
        # Instead of best+1, post at best+2 or best+3?
        # Advantage: higher fill price on sells, lower on buys
        if product == "ASH_COATED_OSMIUM":
            print(f"\n--- OSMIUM: DEEPER POSTING ---")
            print(f"  With spread=16 and fair=10000, there's massive room in the spread.")
            print(f"  Posting at 9999/10001 wastes 6-7 ticks of potential edge.")
            print(f"  Better: post closer to fair, e.g., 9997/10003 to capture more spread.")
            
            # How much volume sits at each level?
            for level in [1, 2, 3]:
                bp = p[f"bid_price_{level}"].dropna()
                bv = p[f"bid_volume_{level}"].dropna()
                ap = p[f"ask_price_{level}"].dropna()
                av = p[f"ask_volume_{level}"].dropna()
                
                bid_dist = (p["mid"] - bp).mean()
                ask_dist = (ap - p["mid"]).mean()
                print(f"  L{level}: bid {bid_dist:.1f} from mid (vol={bv.mean():.0f}), ask {ask_dist:.1f} from mid (vol={av.mean():.0f})")

analyze_fill_optimization()
