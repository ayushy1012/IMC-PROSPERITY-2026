"""
Comprehensive analysis of 508918.log
Generates all diagnostic plots + deep counterparty analysis + markout + churn detection
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict
import os

OUT = os.path.dirname(os.path.abspath(__file__))

with open('/Users/dmitt/Desktop/Prosperity/logs/508918.log') as f:
    raw = json.load(f)

# ── Parse activities ──
lines = raw['activitiesLog'].strip().split('\n')
header = lines[0].split(';')
activities = []
for line in lines[1:]:
    parts = line.split(';')
    if len(parts) >= len(header):
        activities.append(dict(zip(header, parts)))

products = set()
ts_set = set()
mid_prices = defaultdict(dict)
pnl_series = defaultdict(dict)

for row in activities:
    ts = int(row['timestamp'])
    product = row['product']
    products.add(product)
    ts_set.add(ts)
    try: mid_prices[product][ts] = float(row['mid_price'])
    except: pass
    try: pnl_series[product][ts] = float(row['profit_and_loss'])
    except: pass

timestamps = sorted(ts_set)
products = sorted(products)

# ── Parse trades ──
trades = raw['tradeHistory']
own_trades = [t for t in trades if t['buyer'] == 'SUBMISSION' or t['seller'] == 'SUBMISSION']
market_trades = [t for t in trades if t['buyer'] != 'SUBMISSION' and t['seller'] != 'SUBMISSION']

# ── Parse lambda logs ──
z_vals, mtm_vals, dd_vals, log_ts = [], [], [], []
for entry in raw['logs']:
    log = entry.get('lambdaLog', '')
    if log and 'z=' in log:
        try:
            parts = log.split()
            z_vals.append(float([p for p in parts if p.startswith('z=')][0].split('=')[1]))
            mtm_vals.append(float([p for p in parts if p.startswith('mtm=')][0].split('=')[1]))
            dd_vals.append(float([p for p in parts if p.startswith('dd=')][0].split('=')[1]))
            log_ts.append(entry['timestamp'])
        except: pass

# ══════════════════════════════════════════════════════════
# PLOT 1: Per-product PnL
# ══════════════════════════════════════════════════════════
fig, axes = plt.subplots(4, 3, figsize=(20, 16), sharex=True)
fig.suptitle('508918 — Per-Product PnL Curves', fontsize=16, fontweight='bold')
for idx, product in enumerate(products[:12]):
    ax = axes[idx // 3][idx % 3]
    ts_list = sorted(pnl_series[product].keys())
    pnl_vals = [pnl_series[product][t] for t in ts_list]
    color = 'red' if pnl_vals and pnl_vals[-1] < 0 else 'blue'
    ax.plot(ts_list, pnl_vals, linewidth=1.5, color=color)
    ax.set_title(f'{product}  (final: {pnl_vals[-1]:.0f})', fontsize=10,
                color='red' if pnl_vals[-1] < 0 else 'black')
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'pnl_products_508918.png'), dpi=150)
plt.close()

# ══════════════════════════════════════════════════════════
# PLOT 2: Total PnL + bot state
# ══════════════════════════════════════════════════════════
total_pnl = {}
for ts in timestamps:
    total_pnl[ts] = sum(pnl_series[p].get(ts, 0) for p in products)

fig, axes = plt.subplots(4, 1, figsize=(16, 16), sharex=True)
fig.suptitle('508918 — Overview', fontsize=14, fontweight='bold')

ts_list = sorted(total_pnl.keys())
pnl_vals = [total_pnl[t] for t in ts_list]
axes[0].plot(ts_list, pnl_vals, linewidth=2, color='blue')
axes[0].fill_between(ts_list, pnl_vals, 0, alpha=0.1, color='blue')
axes[0].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
axes[0].set_title(f'Total PnL (final: {pnl_vals[-1]:.0f})')
axes[0].set_ylabel('PnL')
axes[0].grid(True, alpha=0.3)

# V mid price
v_ts = sorted(mid_prices['VELVETFRUIT_EXTRACT'].keys())
v_mids = [mid_prices['VELVETFRUIT_EXTRACT'][t] for t in v_ts]
axes[1].plot(v_ts, v_mids, linewidth=1, color='purple')
axes[1].axhline(y=5247.4, color='orange', linestyle='--', alpha=0.7, label='V_MEAN=5247.4')
axes[1].set_title('V Mid Price')
axes[1].set_ylabel('Price')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

if z_vals:
    axes[2].plot(log_ts, z_vals, linewidth=1.5, color='orange')
    axes[2].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    axes[2].axhline(y=2, color='red', linestyle=':', alpha=0.5)
    axes[2].axhline(y=-2, color='red', linestyle=':', alpha=0.5)
    axes[2].set_title('Z-Score')
    axes[2].set_ylabel('Z')
    axes[2].grid(True, alpha=0.3)

if dd_vals:
    axes[3].plot(log_ts, dd_vals, linewidth=1.5, color='red')
    axes[3].axhline(y=30000, color='red', linestyle='--', alpha=0.5, label='Stop loss')
    axes[3].set_title('Drawdown')
    axes[3].set_ylabel('Drawdown')
    axes[3].legend()
    axes[3].grid(True, alpha=0.3)

axes[3].set_xlabel('Timestamp')
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'overview_508918.png'), dpi=150)
plt.close()

# ══════════════════════════════════════════════════════════
# PLOT 3: V position + trades on V price chart
# ══════════════════════════════════════════════════════════
v_own = sorted([t for t in own_trades if t['symbol'] == 'VELVETFRUIT_EXTRACT'], key=lambda x: x['timestamp'])
fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
fig.suptitle('508918 — VELVETFRUIT_EXTRACT Deep Dive', fontsize=14, fontweight='bold')

# V mid + trades
axes[0].plot(v_ts, v_mids, linewidth=1, color='gray', alpha=0.7)
v_buys = [t for t in v_own if t['buyer'] == 'SUBMISSION']
v_sells = [t for t in v_own if t['seller'] == 'SUBMISSION']
if v_buys:
    axes[0].scatter([t['timestamp'] for t in v_buys], [t['price'] for t in v_buys],
                    marker='^', color='green', s=40, alpha=0.7, label=f'Buy ({sum(t["quantity"] for t in v_buys)} qty)', zorder=5)
if v_sells:
    axes[0].scatter([t['timestamp'] for t in v_sells], [t['price'] for t in v_sells],
                    marker='v', color='red', s=40, alpha=0.7, label=f'Sell ({sum(t["quantity"] for t in v_sells)} qty)', zorder=5)
axes[0].set_title('V Mid Price + Our Trades')
axes[0].set_ylabel('Price')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# V position over time
v_pos = 0
v_pos_ts = [0]
v_pos_vals = [0]
for t in v_own:
    if t['buyer'] == 'SUBMISSION':
        v_pos += t['quantity']
    else:
        v_pos -= t['quantity']
    v_pos_ts.append(t['timestamp'])
    v_pos_vals.append(v_pos)
axes[1].plot(v_pos_ts, v_pos_vals, linewidth=1.5, color='blue')
axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
axes[1].set_title(f'V Position (final: {v_pos})')
axes[1].set_ylabel('Position')
axes[1].grid(True, alpha=0.3)

# V PnL
v_pnl_ts = sorted(pnl_series['VELVETFRUIT_EXTRACT'].keys())
v_pnl_vals = [pnl_series['VELVETFRUIT_EXTRACT'][t] for t in v_pnl_ts]
axes[2].plot(v_pnl_ts, v_pnl_vals, linewidth=1.5, color='green')
axes[2].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
axes[2].set_title(f'V PnL (final: {v_pnl_vals[-1]:.0f})')
axes[2].set_ylabel('PnL')
axes[2].grid(True, alpha=0.3)

axes[2].set_xlabel('Timestamp')
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'v_deep_dive_508918.png'), dpi=150)
plt.close()

# ══════════════════════════════════════════════════════════
# PLOT 4: Per-voucher position trajectories
# ══════════════════════════════════════════════════════════
voucher_prods = ['VEV_5000', 'VEV_5100', 'VEV_5200', 'VEV_5300', 'VEV_5400', 'VEV_5500']
fig, axes = plt.subplots(2, 3, figsize=(18, 8), sharex=True)
fig.suptitle('508918 — Voucher Position Trajectories', fontsize=14, fontweight='bold')
for idx, prod in enumerate(voucher_prods):
    ax = axes[idx // 3][idx % 3]
    prod_trades = sorted([t for t in own_trades if t['symbol'] == prod], key=lambda x: x['timestamp'])
    pos = 0
    pos_ts = [0]
    pos_vals = [0]
    for t in prod_trades:
        if t['buyer'] == 'SUBMISSION':
            pos += t['quantity']
        else:
            pos -= t['quantity']
        pos_ts.append(t['timestamp'])
        pos_vals.append(pos)
    ax.plot(pos_ts, pos_vals, linewidth=1.5)
    final_pnl = pnl_series[prod].get(max(pnl_series[prod].keys()), 0) if pnl_series[prod] else 0
    ax.set_title(f'{prod}  pos={pos}  pnl={final_pnl:.0f}', fontsize=10)
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'voucher_positions_508918.png'), dpi=150)
plt.close()

# ══════════════════════════════════════════════════════════
# PLOT 5: Hydrogel deep dive
# ══════════════════════════════════════════════════════════
h_own = sorted([t for t in own_trades if t['symbol'] == 'HYDROGEL_PACK'], key=lambda x: x['timestamp'])
fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
fig.suptitle('508918 — HYDROGEL_PACK Deep Dive', fontsize=14, fontweight='bold')

h_ts_mid = sorted(mid_prices['HYDROGEL_PACK'].keys())
h_mids = [mid_prices['HYDROGEL_PACK'][t] for t in h_ts_mid]
axes[0].plot(h_ts_mid, h_mids, linewidth=1, color='gray', alpha=0.7)
h_buys = [t for t in h_own if t['buyer'] == 'SUBMISSION']
h_sells = [t for t in h_own if t['seller'] == 'SUBMISSION']
if h_buys:
    axes[0].scatter([t['timestamp'] for t in h_buys], [t['price'] for t in h_buys],
                    marker='^', color='green', s=30, alpha=0.6, label='Buy')
if h_sells:
    axes[0].scatter([t['timestamp'] for t in h_sells], [t['price'] for t in h_sells],
                    marker='v', color='red', s=30, alpha=0.6, label='Sell')
axes[0].set_title('HGL Price + Trades')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

h_pos = 0
h_pos_ts = [0]; h_pos_vals = [0]
for t in h_own:
    if t['buyer'] == 'SUBMISSION': h_pos += t['quantity']
    else: h_pos -= t['quantity']
    h_pos_ts.append(t['timestamp'])
    h_pos_vals.append(h_pos)
axes[1].plot(h_pos_ts, h_pos_vals, linewidth=1.5, color='purple')
axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
axes[1].axhline(y=40, color='red', linestyle=':', alpha=0.5, label='Dead zone')
axes[1].axhline(y=-40, color='red', linestyle=':', alpha=0.5)
axes[1].set_title(f'HGL Position (final: {h_pos})')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

h_pnl_ts = sorted(pnl_series['HYDROGEL_PACK'].keys())
h_pnl_vals = [pnl_series['HYDROGEL_PACK'][t] for t in h_pnl_ts]
axes[2].plot(h_pnl_ts, h_pnl_vals, linewidth=1.5, color='red' if h_pnl_vals[-1] < 0 else 'green')
axes[2].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
axes[2].set_title(f'HGL PnL (final: {h_pnl_vals[-1]:.0f})')
axes[2].grid(True, alpha=0.3)

axes[2].set_xlabel('Timestamp')
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'hydrogel_508918.png'), dpi=150)
plt.close()

# ══════════════════════════════════════════════════════════
# TEXT ANALYSIS
# ══════════════════════════════════════════════════════════
print("=" * 70)
print("508918 ANALYSIS")
print("=" * 70)

# Final PnL
print("\n── FINAL PnL ──")
final_pnl = {}
for p in products:
    ts_list = sorted(pnl_series[p].keys())
    final_pnl[p] = pnl_series[p][ts_list[-1]] if ts_list else 0
for p in sorted(final_pnl.keys(), key=lambda x: final_pnl[x]):
    marker = "🔴" if final_pnl[p] < -100 else "⚠️ " if final_pnl[p] < 100 else "✅"
    print(f"  {marker} {p:<25} {final_pnl[p]:>10.2f}")
print(f"  {'TOTAL':<28} {sum(final_pnl.values()):>10.2f}")

# Trade summary
print(f"\n── TRADE SUMMARY ──")
print(f"  Total trades: {len(trades)}, Own: {len(own_trades)}, Market: {len(market_trades)}")
own_by_product = defaultdict(list)
for t in own_trades: own_by_product[t['symbol']].append(t)

print(f"\n  {'Product':<25} {'#Trades':>7} {'Bought':>8} {'Sold':>8} {'Net':>6} {'AvgBuy':>10} {'AvgSell':>10} {'Spread':>8}")
print("  " + "-" * 95)
for p in sorted(own_by_product.keys()):
    tl = own_by_product[p]
    buys = [t for t in tl if t['buyer'] == 'SUBMISSION']
    sells = [t for t in tl if t['seller'] == 'SUBMISSION']
    bq = sum(t['quantity'] for t in buys)
    sq = sum(t['quantity'] for t in sells)
    ab = sum(t['price']*t['quantity'] for t in buys)/bq if bq else 0
    asell = sum(t['price']*t['quantity'] for t in sells)/sq if sq else 0
    sp = asell - ab if ab and asell else 0
    print(f"  {p:<25} {len(tl):>7} {bq:>8} {sq:>8} {bq-sq:>6} {ab:>10.2f} {asell:>10.2f} {sp:>8.2f}")

# Counterparty
print(f"\n── COUNTERPARTY BREAKDOWN ──")
cp_data = defaultdict(lambda: defaultdict(lambda: {'bought_from': 0, 'sold_to': 0}))
for t in own_trades:
    if t['buyer'] == 'SUBMISSION':
        cp_data[t['seller']][t['symbol']]['bought_from'] += t['quantity']
    else:
        cp_data[t['buyer']][t['symbol']]['sold_to'] += t['quantity']

for cp in sorted(cp_data.keys()):
    print(f"\n  {cp}:")
    for p in sorted(cp_data[cp].keys()):
        d = cp_data[cp][p]
        print(f"    {p:<25} from={d['bought_from']:>5}  to={d['sold_to']:>5}  net={d['bought_from']-d['sold_to']:>5}")

# Markout
print(f"\n── MARKOUT ANALYSIS ──")
print(f"  {'Product':<25} {'Side':>6} {'#':>4} {'AvgMarkout':>12} {'Worst':>8} {'Best':>8}")
print("  " + "-" * 75)
for p in sorted(own_by_product.keys()):
    for side in ['BUY', 'SELL']:
        st = [t for t in own_by_product[p] if (t['buyer']=='SUBMISSION') == (side=='BUY')]
        if not st: continue
        markouts = []
        for t in st:
            mid = mid_prices[p].get(t['timestamp'])
            if mid is not None:
                mo = (mid - t['price']) if side == 'BUY' else (t['price'] - mid)
                markouts.append(mo)
        if markouts:
            avg = np.mean(markouts)
            marker = "❌" if avg < -1 else "⚠️" if avg < 0 else "✅"
            print(f"  {marker} {p:<23} {side:>6} {len(st):>4} {avg:>12.2f} {min(markouts):>8.2f} {max(markouts):>8.2f}")

# Market trades (what the bots are doing without us)
print(f"\n── MARKET TRADES (bot-vs-bot, excluding us) ──")
mkt_by_prod = defaultdict(list)
for t in market_trades: mkt_by_prod[t['symbol']].append(t)
for p in sorted(mkt_by_prod.keys()):
    tl = mkt_by_prod[p]
    vol = sum(t['quantity'] for t in tl)
    if vol > 0:
        avg_p = sum(t['price']*t['quantity'] for t in tl) / vol
        print(f"  {p:<25} {len(tl):>4} trades, {vol:>6} vol, avg={avg_p:.2f}")
        # Who's trading?
        buyers = defaultdict(int)
        sellers = defaultdict(int)
        for t in tl:
            buyers[t['buyer']] += t['quantity']
            sellers[t['seller']] += t['quantity']
        top_buyers = sorted(buyers.items(), key=lambda x: -x[1])[:3]
        top_sellers = sorted(sellers.items(), key=lambda x: -x[1])[:3]
        print(f"    Top buyers:  {', '.join(f'{b}({q})' for b,q in top_buyers)}")
        print(f"    Top sellers: {', '.join(f'{s}({q})' for s,q in top_sellers)}")

# Churn detection: products where we're buying AND selling heavily
print(f"\n── CHURN DETECTION ──")
for p in sorted(own_by_product.keys()):
    buys = [t for t in own_by_product[p] if t['buyer'] == 'SUBMISSION']
    sells = [t for t in own_by_product[p] if t['seller'] == 'SUBMISSION']
    bq = sum(t['quantity'] for t in buys)
    sq = sum(t['quantity'] for t in sells)
    net = abs(bq - sq)
    gross = bq + sq
    if gross > 0:
        churn_ratio = net / gross  # 0 = pure churn, 1 = pure directional
        edge_per_unit = final_pnl.get(p, 0) / gross if gross > 0 else 0
        marker = "🔴" if churn_ratio < 0.3 and edge_per_unit < 1 else "✅"
        print(f"  {marker} {p:<25} gross={gross:>6} net={net:>5} ratio={churn_ratio:.2f} edge/unit={edge_per_unit:.2f}")

# V trajectory
print(f"\n── V TRAJECTORY ──")
v_start = mid_prices['VELVETFRUIT_EXTRACT'].get(0)
v_end = mid_prices['VELVETFRUIT_EXTRACT'].get(max(mid_prices['VELVETFRUIT_EXTRACT'].keys()))
v_min = min(mid_prices['VELVETFRUIT_EXTRACT'].values())
v_max = max(mid_prices['VELVETFRUIT_EXTRACT'].values())
print(f"  Start: {v_start}, End: {v_end}")
print(f"  Min: {v_min}, Max: {v_max}, Range: {v_max-v_min}")
if z_vals:
    print(f"  Z-score: {z_vals[0]:.2f} → {z_vals[-1]:.2f} (min={min(z_vals):.2f} max={max(z_vals):.2f})")

print("\nAll plots saved.")
