"""
Comprehensive Round 3 data analysis.
Validates the assumptions in round3_trader.py:
  1) BS pricing accuracy per strike
  2) Spread distributions
  3) VEV price range and dynamics
  4) HGL price range and dynamics  
  5) Trade flow by product
  6) Deep OTM behavior
"""
import csv, math, sys
from collections import defaultdict

DATA_DIR = "/Users/dmitt/Desktop/Prosperity/ROUND_3"

# ─── BS math ────────────────────────────────────────────────
def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def bs_call(S, K, T, sigma, r=0.0):
    if S <= 0 or sigma <= 0 or T <= 0:
        return max(0.0, S - K)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)

# ─── Load prices ────────────────────────────────────────────
def load_prices(day):
    path = f"{DATA_DIR}/prices_round_3_day_{day}.csv"
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            rows.append(row)
    return rows

def load_trades(day):
    path = f"{DATA_DIR}/trades_round_3_day_{day}.csv"
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            rows.append(row)
    return rows

# ─── 1) Spread analysis per product ────────────────────────
print("=" * 80)
print("SPREAD ANALYSIS")
print("=" * 80)

products = set()
spread_data = defaultdict(list)
mid_data = defaultdict(list)

for day in range(3):
    TTE = 8 - day  # Day 0 -> TTE=8, Day 1 -> TTE=7, Day 2 -> TTE=6
    rows = load_prices(day)
    for r in rows:
        prod = r["product"]
        products.add(prod)
        bp1 = r.get("bid_price_1", "")
        ap1 = r.get("ask_price_1", "")
        if bp1 and ap1:
            try:
                bid = float(bp1)
                ask = float(ap1)
                spread_data[prod].append(ask - bid)
                mid_data[prod].append((day, int(r["timestamp"]), (bid + ask) / 2.0, bid, ask))
            except:
                pass

print(f"\n{'Product':<25} {'Mean Spread':>12} {'Median':>8} {'Min':>6} {'Max':>6} {'Ticks':>8}")
print("-" * 80)
for prod in sorted(spread_data.keys()):
    sp = sorted(spread_data[prod])
    n = len(sp)
    mean_sp = sum(sp) / n
    median_sp = sp[n // 2]
    print(f"{prod:<25} {mean_sp:>12.2f} {median_sp:>8.1f} {sp[0]:>6.1f} {sp[-1]:>6.1f} {n:>8d}")

# ─── 2) VEV price dynamics ─────────────────────────────────
print("\n" + "=" * 80)
print("VEV PRICE DYNAMICS")
print("=" * 80)

vev_mids = mid_data.get("VELVETFRUIT_EXTRACT", [])
if vev_mids:
    for day in range(3):
        day_mids = [m[2] for m in vev_mids if m[0] == day]
        if day_mids:
            print(f"Day {day}: min={min(day_mids):.1f}  max={max(day_mids):.1f}  "
                  f"start={day_mids[0]:.1f}  end={day_mids[-1]:.1f}  "
                  f"mean={sum(day_mids)/len(day_mids):.1f}  ticks={len(day_mids)}")

# ─── 3) HGL price dynamics ─────────────────────────────────
print("\n" + "=" * 80)
print("HYDROGEL_PACK PRICE DYNAMICS")
print("=" * 80)

hgl_mids = mid_data.get("HYDROGEL_PACK", [])
if hgl_mids:
    for day in range(3):
        day_mids = [m[2] for m in hgl_mids if m[0] == day]
        if day_mids:
            print(f"Day {day}: min={min(day_mids):.1f}  max={max(day_mids):.1f}  "
                  f"start={day_mids[0]:.1f}  end={day_mids[-1]:.1f}  "
                  f"mean={sum(day_mids)/len(day_mids):.1f}  ticks={len(day_mids)}")

# ─── 4) BS calibration check ───────────────────────────────
print("\n" + "=" * 80)
print("BLACK-SCHOLES CALIBRATION (σ sweep)")
print("=" * 80)

STRIKES = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500]
OPT_SIGMA_EXISTING = {
    4000: 0.0120, 4500: 0.0120, 5000: 0.0123, 5100: 0.0121,
    5200: 0.0123, 5300: 0.0124, 5400: 0.0116, 5500: 0.0126,
}

for K in STRIKES:
    prod_name = f"VEV_{K}"
    opt_mids = mid_data.get(prod_name, [])
    if not opt_mids:
        print(f"{prod_name}: NO DATA")
        continue
    
    # For each day, compute BS error at the existing σ
    for day in range(3):
        TTE = 8 - day
        day_opt = [(t, mid) for (d, t, mid, _, _) in opt_mids if d == day]
        day_vev = {t: mid for (d, t, mid, _, _) in vev_mids if d == day}
        
        if not day_opt:
            continue
        
        errors = []
        sigma = OPT_SIGMA_EXISTING[K]
        for t, opt_mid in day_opt:
            vev_mid = day_vev.get(t)
            if vev_mid is None:
                continue
            bs_fair = bs_call(vev_mid, K, TTE, sigma)
            errors.append(opt_mid - bs_fair)
        
        if errors:
            mean_err = sum(errors) / len(errors)
            std_err = (sum((e - mean_err)**2 for e in errors) / len(errors)) ** 0.5
            max_abs = max(abs(e) for e in errors)
            # Find best σ
            best_sigma = sigma
            best_mean_abs = abs(mean_err)
            for trial_s in [sigma + i * 0.0001 for i in range(-20, 21)]:
                if trial_s <= 0:
                    continue
                trial_errors = []
                for t, opt_mid in day_opt:
                    vev_mid = day_vev.get(t)
                    if vev_mid is None:
                        continue
                    trial_errors.append(opt_mid - bs_call(vev_mid, K, TTE, trial_s))
                if trial_errors:
                    trial_mean = abs(sum(trial_errors) / len(trial_errors))
                    if trial_mean < best_mean_abs:
                        best_mean_abs = trial_mean
                        best_sigma = trial_s
            
            if day == 1:  # Only print Day 1 for brevity
                print(f"{prod_name} Day{day}: mean_err={mean_err:+.3f}  std={std_err:.3f}  "
                      f"max_abs={max_abs:.3f}  used_σ={sigma:.4f}  best_σ={best_sigma:.4f}")

# ─── 5) Trade flow analysis ────────────────────────────────
print("\n" + "=" * 80)
print("TRADE FLOW ANALYSIS")
print("=" * 80)

trade_counts = defaultdict(lambda: {"count": 0, "volume": 0, "prices": []})
for day in range(3):
    trades = load_trades(day)
    for t in trades:
        sym = t.get("symbol", "")
        try:
            qty = int(t.get("quantity", 0))
            px = float(t.get("price", 0))
            trade_counts[sym]["count"] += 1
            trade_counts[sym]["volume"] += qty
            trade_counts[sym]["prices"].append(px)
        except:
            pass

print(f"\n{'Product':<25} {'Trades':>8} {'Volume':>8} {'Avg Qty':>8} {'Min Px':>8} {'Max Px':>8}")
print("-" * 80)
for prod in sorted(trade_counts.keys()):
    tc = trade_counts[prod]
    avg_q = tc["volume"] / tc["count"] if tc["count"] > 0 else 0
    print(f"{prod:<25} {tc['count']:>8} {tc['volume']:>8} {avg_q:>8.1f} "
          f"{min(tc['prices']):>8.1f} {max(tc['prices']):>8.1f}")

# ─── 6) Deep OTM check ─────────────────────────────────────
print("\n" + "=" * 80)
print("DEEP OTM (VEV_6000, VEV_6500) CHECK")
print("=" * 80)

for prod in ["VEV_6000", "VEV_6500"]:
    mids = mid_data.get(prod, [])
    if mids:
        all_mids = [m[2] for m in mids]
        unique_mids = set(all_mids)
        print(f"{prod}: unique mid values = {sorted(unique_mids)[:10]}  "
              f"count={len(all_mids)}")
        
        # Check bids and asks
        all_bids = [m[3] for m in mids]
        all_asks = [m[4] for m in mids]
        print(f"  Bids: min={min(all_bids):.0f}  max={max(all_bids):.0f}  "
              f"Asks: min={min(all_asks):.0f}  max={max(all_asks):.0f}")

# ─── 7) Check for any products the trader might be missing ──
print("\n" + "=" * 80)
print("ALL PRODUCTS IN DATA")
print("=" * 80)
for p in sorted(products):
    n = len(spread_data[p])
    print(f"  {p}: {n} ticks")

# ─── 8) OBI analysis for HGL ───────────────────────────────
print("\n" + "=" * 80)
print("HGL OBI (ORDER BOOK IMBALANCE) SAMPLE")
print("=" * 80)

# Load raw OBI for day 1
day1_prices = load_prices(1)
hgl_obi = []
for r in day1_prices:
    if r["product"] == "HYDROGEL_PACK":
        bp1 = r.get("bid_price_1", "")
        bv1 = r.get("bid_volume_1", "")
        ap1 = r.get("ask_price_1", "")
        av1 = r.get("ask_volume_1", "")
        if bp1 and bv1 and ap1 and av1:
            try:
                bid_q = int(bv1)
                ask_q = int(av1)
                total = bid_q + ask_q
                if total > 0:
                    obi = (bid_q - ask_q) / total
                    hgl_obi.append(obi)
            except:
                pass

if hgl_obi:
    obi_sorted = sorted(hgl_obi)
    print(f"  OBI stats: min={obi_sorted[0]:.4f}  max={obi_sorted[-1]:.4f}  "
          f"mean={sum(hgl_obi)/len(hgl_obi):.4f}  "
          f"p25={obi_sorted[len(obi_sorted)//4]:.4f}  "
          f"p75={obi_sorted[3*len(obi_sorted)//4]:.4f}")

print("\n✅ Analysis complete.")
