"""
Analyze 508344.log — find where the bot is losing money.
Generates diagnostic graphs for PnL, positions, trade quality, and counterparty flow.
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Load data ──
with open('/Users/dmitt/Desktop/Prosperity/logs/508344.log') as f:
    raw = json.load(f)

# ── Parse activitiesLog (order book snapshots + PnL) ──
lines = raw['activitiesLog'].strip().split('\n')
header = lines[0].split(';')
activities = []
for line in lines[1:]:
    parts = line.split(';')
    if len(parts) >= len(header):
        row = dict(zip(header, parts))
        activities.append(row)

# Build per-product time series: mid_price and PnL
products = set()
ts_set = set()
mid_prices = defaultdict(dict)  # product -> {ts: mid}
pnl_series = defaultdict(dict)  # product -> {ts: pnl}

for row in activities:
    ts = int(row['timestamp'])
    product = row['product']
    products.add(product)
    ts_set.add(ts)
    try:
        mid_prices[product][ts] = float(row['mid_price'])
    except:
        pass
    try:
        pnl_series[product][ts] = float(row['profit_and_loss'])
    except:
        pass

timestamps = sorted(ts_set)
products = sorted(products)

# ── Parse trade history ──
trades = raw['tradeHistory']
print(f"Total trades: {len(trades)}")

# Separate own trades (SUBMISSION) vs market trades
own_trades = [t for t in trades if t['buyer'] == 'SUBMISSION' or t['seller'] == 'SUBMISSION']
market_trades = [t for t in trades if t['buyer'] != 'SUBMISSION' and t['seller'] != 'SUBMISSION']

print(f"Own trades: {len(own_trades)}, Market trades: {len(market_trades)}")

# ── Parse lambda logs ──
lambda_logs = []
for entry in raw['logs']:
    if entry.get('lambdaLog'):
        lambda_logs.append({
            'timestamp': entry['timestamp'],
            'log': entry['lambdaLog']
        })

# ── ANALYSIS 1: Per-product PnL curves ──
fig, axes = plt.subplots(4, 3, figsize=(20, 16), sharex=True)
fig.suptitle('508344 — Per-Product PnL Curves', fontsize=16, fontweight='bold')

for idx, product in enumerate(products[:12]):
    ax = axes[idx // 3][idx % 3]
    ts_list = sorted(pnl_series[product].keys())
    pnl_vals = [pnl_series[product][t] for t in ts_list]
    ax.plot(ts_list, pnl_vals, linewidth=1.5)
    ax.set_title(f'{product}  (final: {pnl_vals[-1]:.0f})', fontsize=10)
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'pnl_per_product.png'), dpi=150)
plt.close()
print("Saved: pnl_per_product.png")

# ── ANALYSIS 2: Aggregate PnL curve ──
total_pnl = {}
for ts in timestamps:
    total_pnl[ts] = sum(pnl_series[p].get(ts, 0) for p in products)

fig, ax = plt.subplots(figsize=(14, 6))
ts_list = sorted(total_pnl.keys())
pnl_vals = [total_pnl[t] for t in ts_list]
ax.plot(ts_list, pnl_vals, linewidth=2, color='blue')
ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax.fill_between(ts_list, pnl_vals, 0, alpha=0.1, color='blue')
ax.set_title(f'508344 — Total PnL Curve (final: {pnl_vals[-1]:.0f})', fontsize=14, fontweight='bold')
ax.set_xlabel('Timestamp')
ax.set_ylabel('PnL')
ax.grid(True, alpha=0.3)

# Mark peak and trough
peak_idx = np.argmax(pnl_vals)
trough_idx = np.argmin(pnl_vals)
ax.annotate(f'Peak: {pnl_vals[peak_idx]:.0f}', xy=(ts_list[peak_idx], pnl_vals[peak_idx]),
            arrowprops=dict(arrowstyle='->', color='green'), fontsize=10, color='green',
            xytext=(ts_list[peak_idx]+2000, pnl_vals[peak_idx]+1000))
ax.annotate(f'Trough: {pnl_vals[trough_idx]:.0f}', xy=(ts_list[trough_idx], pnl_vals[trough_idx]),
            arrowprops=dict(arrowstyle='->', color='red'), fontsize=10, color='red',
            xytext=(ts_list[trough_idx]+2000, pnl_vals[trough_idx]-1000))

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'total_pnl.png'), dpi=150)
plt.close()
print("Saved: total_pnl.png")

# ── ANALYSIS 3: Own trade breakdown — per product ──
own_by_product = defaultdict(list)
for t in own_trades:
    own_by_product[t['symbol']].append(t)

print("\n═══ OWN TRADE SUMMARY ═══")
print(f"{'Product':<25} {'Trades':>6} {'Bought':>8} {'Sold':>8} {'Net':>8} {'Avg Buy':>10} {'Avg Sell':>10} {'Spread':>8}")
print("-" * 100)

product_stats = {}
for product in sorted(own_by_product.keys()):
    trades_list = own_by_product[product]
    buys = [t for t in trades_list if t['buyer'] == 'SUBMISSION']
    sells = [t for t in trades_list if t['seller'] == 'SUBMISSION']
    
    buy_qty = sum(t['quantity'] for t in buys)
    sell_qty = sum(t['quantity'] for t in sells)
    
    avg_buy = sum(t['price'] * t['quantity'] for t in buys) / buy_qty if buy_qty > 0 else 0
    avg_sell = sum(t['price'] * t['quantity'] for t in sells) / sell_qty if sell_qty > 0 else 0
    
    spread = avg_sell - avg_buy if avg_buy > 0 and avg_sell > 0 else 0
    
    product_stats[product] = {
        'trades': len(trades_list), 'buys': buys, 'sells': sells,
        'buy_qty': buy_qty, 'sell_qty': sell_qty,
        'avg_buy': avg_buy, 'avg_sell': avg_sell, 'spread': spread
    }
    
    print(f"{product:<25} {len(trades_list):>6} {buy_qty:>8} {sell_qty:>8} {buy_qty-sell_qty:>8} {avg_buy:>10.2f} {avg_sell:>10.2f} {spread:>8.2f}")

# ── ANALYSIS 4: Counterparty breakdown — who are we trading with? ──
print("\n═══ COUNTERPARTY BREAKDOWN (OWN TRADES) ═══")
cp_buys = defaultdict(lambda: defaultdict(int))   # counterparty -> product -> qty we BOUGHT from them
cp_sells = defaultdict(lambda: defaultdict(int))   # counterparty -> product -> qty we SOLD to them

for t in own_trades:
    if t['buyer'] == 'SUBMISSION':
        cp = t['seller']
        cp_buys[cp][t['symbol']] += t['quantity']
    else:
        cp = t['buyer']
        cp_sells[cp][t['symbol']] += t['quantity']

all_cps = sorted(set(list(cp_buys.keys()) + list(cp_sells.keys())))
for cp in all_cps:
    print(f"\n  {cp}:")
    all_prods = sorted(set(list(cp_buys[cp].keys()) + list(cp_sells[cp].keys())))
    for p in all_prods:
        b = cp_buys[cp].get(p, 0)
        s = cp_sells[cp].get(p, 0)
        print(f"    {p:<25} bought_from={b:>5}  sold_to={s:>5}  net={b-s:>5}")

# ── ANALYSIS 5: Trade timing — when do trades happen? ──
fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
fig.suptitle('508344 — Trade Timing & Quality', fontsize=14, fontweight='bold')

# 5a: Trade count histogram
own_ts = [t['timestamp'] for t in own_trades]
axes[0].hist(own_ts, bins=50, color='steelblue', edgecolor='white', alpha=0.8)
axes[0].set_title('Trade Count Over Time')
axes[0].set_ylabel('# Trades')
axes[0].grid(True, alpha=0.3)

# 5b: Cumulative buy vs sell volume for V
v_own = [t for t in own_trades if t['symbol'] == 'VELVETFRUIT_EXTRACT']
v_buys_cum = []
v_sells_cum = []
v_ts = []
cum_b = cum_s = 0
for t in sorted(v_own, key=lambda x: x['timestamp']):
    if t['buyer'] == 'SUBMISSION':
        cum_b += t['quantity']
    else:
        cum_s += t['quantity']
    v_buys_cum.append(cum_b)
    v_sells_cum.append(cum_s)
    v_ts.append(t['timestamp'])

axes[1].plot(v_ts, v_buys_cum, label='Cum Buys', color='green')
axes[1].plot(v_ts, v_sells_cum, label='Cum Sells', color='red')
axes[1].plot(v_ts, [b-s for b,s in zip(v_buys_cum, v_sells_cum)], label='Net Position', color='blue', linewidth=2)
axes[1].set_title('VELVETFRUIT_EXTRACT — Cumulative Buy/Sell')
axes[1].set_ylabel('Quantity')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

# 5c: V mid price with own trade markers
v_ts_mid = sorted(mid_prices['VELVETFRUIT_EXTRACT'].keys())
v_mids = [mid_prices['VELVETFRUIT_EXTRACT'][t] for t in v_ts_mid]
axes[2].plot(v_ts_mid, v_mids, linewidth=1, color='gray', alpha=0.7, label='V Mid')

v_buy_trades = [t for t in v_own if t['buyer'] == 'SUBMISSION']
v_sell_trades = [t for t in v_own if t['seller'] == 'SUBMISSION']
if v_buy_trades:
    axes[2].scatter([t['timestamp'] for t in v_buy_trades],
                    [t['price'] for t in v_buy_trades],
                    marker='^', color='green', s=30, alpha=0.7, label='Our Buys', zorder=5)
if v_sell_trades:
    axes[2].scatter([t['timestamp'] for t in v_sell_trades],
                    [t['price'] for t in v_sell_trades],
                    marker='v', color='red', s=30, alpha=0.7, label='Our Sells', zorder=5)

axes[2].set_title('VELVETFRUIT_EXTRACT — Mid Price + Our Trades')
axes[2].set_xlabel('Timestamp')
axes[2].set_ylabel('Price')
axes[2].legend()
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'trade_timing.png'), dpi=150)
plt.close()
print("\nSaved: trade_timing.png")

# ── ANALYSIS 6: Hydrogel MM quality ──
h_own = [t for t in own_trades if t['symbol'] == 'HYDROGEL_PACK']
if h_own:
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle('508344 — HYDROGEL_PACK Market Making Quality', fontsize=14, fontweight='bold')
    
    # Position over time
    h_pos = 0
    h_pos_ts = [0]
    h_pos_vals = [0]
    for t in sorted(h_own, key=lambda x: x['timestamp']):
        if t['buyer'] == 'SUBMISSION':
            h_pos += t['quantity']
        else:
            h_pos -= t['quantity']
        h_pos_ts.append(t['timestamp'])
        h_pos_vals.append(h_pos)
    
    axes[0].plot(h_pos_ts, h_pos_vals, linewidth=1.5, color='purple')
    axes[0].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    axes[0].set_title(f'Hydrogel Position (final: {h_pos})')
    axes[0].set_ylabel('Position')
    axes[0].grid(True, alpha=0.3)
    
    # Price vs mid
    h_ts_mid = sorted(mid_prices['HYDROGEL_PACK'].keys())
    h_mids = [mid_prices['HYDROGEL_PACK'][t] for t in h_ts_mid]
    axes[1].plot(h_ts_mid, h_mids, linewidth=1, color='gray', alpha=0.5, label='Mid')
    
    h_buys = [t for t in h_own if t['buyer'] == 'SUBMISSION']
    h_sells = [t for t in h_own if t['seller'] == 'SUBMISSION']
    if h_buys:
        axes[1].scatter([t['timestamp'] for t in h_buys], [t['price'] for t in h_buys],
                       marker='^', color='green', s=20, alpha=0.5, label='Buy')
    if h_sells:
        axes[1].scatter([t['timestamp'] for t in h_sells], [t['price'] for t in h_sells],
                       marker='v', color='red', s=20, alpha=0.5, label='Sell')
    axes[1].set_title('Hydrogel Trades vs Mid Price')
    axes[1].set_xlabel('Timestamp')
    axes[1].set_ylabel('Price')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'hydrogel_mm.png'), dpi=150)
    plt.close()
    print("Saved: hydrogel_mm.png")

# ── ANALYSIS 7: Per-trade markout (did we buy low / sell high?) ──
print("\n═══ MARKOUT ANALYSIS (trade price vs mid at time of trade) ═══")
print(f"{'Product':<25} {'Side':>6} {'Trades':>6} {'Avg Markout':>12} {'Worst':>8} {'Best':>8}")
print("-" * 80)

for product in sorted(own_by_product.keys()):
    for side in ['BUY', 'SELL']:
        if side == 'BUY':
            side_trades = [t for t in own_by_product[product] if t['buyer'] == 'SUBMISSION']
        else:
            side_trades = [t for t in own_by_product[product] if t['seller'] == 'SUBMISSION']
        
        if not side_trades:
            continue
        
        markouts = []
        for t in side_trades:
            mid = mid_prices[product].get(t['timestamp'])
            if mid is not None:
                if side == 'BUY':
                    markout = mid - t['price']  # positive = bought below mid (good)
                else:
                    markout = t['price'] - mid  # positive = sold above mid (good)
                markouts.append(markout)
        
        if markouts:
            avg_mo = np.mean(markouts)
            print(f"{product:<25} {side:>6} {len(side_trades):>6} {avg_mo:>12.2f} {min(markouts):>8.2f} {max(markouts):>8.2f}")

# ── ANALYSIS 8: Lambda log parsing — z-score and drawdown trajectory ──
z_vals = []
mtm_vals = []
dd_vals = []
log_ts = []

for entry in lambda_logs:
    log = entry['log']
    ts = entry['timestamp']
    if log and 'z=' in log:
        try:
            parts = log.split()
            z_str = [p for p in parts if p.startswith('z=')][0]
            mtm_str = [p for p in parts if p.startswith('mtm=')][0]
            dd_str = [p for p in parts if p.startswith('dd=')][0]
            z_vals.append(float(z_str.split('=')[1]))
            mtm_vals.append(float(mtm_str.split('=')[1]))
            dd_vals.append(float(dd_str.split('=')[1]))
            log_ts.append(ts)
        except:
            pass

if z_vals:
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle('508344 — Bot Internal State (from lambdaLog)', fontsize=14, fontweight='bold')
    
    axes[0].plot(log_ts, z_vals, linewidth=1.5, color='orange')
    axes[0].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    axes[0].axhline(y=2, color='red', linestyle=':', alpha=0.5, label='Rush threshold')
    axes[0].axhline(y=-2, color='red', linestyle=':', alpha=0.5)
    axes[0].set_title('Z-Score Over Time')
    axes[0].set_ylabel('Z-Score')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(log_ts, mtm_vals, linewidth=1.5, color='blue')
    axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    axes[1].set_title('Mark-to-Market PnL')
    axes[1].set_ylabel('MTM')
    axes[1].grid(True, alpha=0.3)
    
    axes[2].plot(log_ts, dd_vals, linewidth=1.5, color='red')
    axes[2].axhline(y=30000, color='red', linestyle='--', alpha=0.5, label='Stop loss')
    axes[2].set_title('Drawdown from Peak')
    axes[2].set_ylabel('Drawdown')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    axes[2].set_xlabel('Timestamp')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'bot_state.png'), dpi=150)
    plt.close()
    print("\nSaved: bot_state.png")

# ── FINAL SUMMARY ──
print("\n" + "=" * 60)
print("FINAL PnL SUMMARY")
print("=" * 60)
final_pnl = {}
for product in products:
    ts_list = sorted(pnl_series[product].keys())
    if ts_list:
        final_pnl[product] = pnl_series[product][ts_list[-1]]
    else:
        final_pnl[product] = 0

for p in sorted(final_pnl.keys(), key=lambda x: final_pnl[x]):
    print(f"  {p:<25} {final_pnl[p]:>10.2f}")

total = sum(final_pnl.values())
print(f"  {'TOTAL':<25} {total:>10.2f}")
print(f"\n  Ticks: {len(timestamps)}")
print(f"  Own trades: {len(own_trades)}")
print(f"  Z-score range: {min(z_vals):.2f} to {max(z_vals):.2f}" if z_vals else "  No z-score data")
