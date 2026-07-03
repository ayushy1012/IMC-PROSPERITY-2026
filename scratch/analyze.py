import json
import csv
from collections import defaultdict

with open("logs/297945.log") as f:
    d = json.load(f)

activities = d.get("activitiesLog", "").strip().split("\n")
if not activities or len(activities) < 2:
    print("No activities log found")
    exit(0)

reader = csv.reader(activities, delimiter=";")
header = next(reader)

ts_idx = header.index("timestamp")
prod_idx = header.index("product")
pnl_idx = header.index("profit_and_loss")

trades = d.get("tradeHistory", [])

prod_pos = defaultdict(int)
max_pos = defaultdict(int)
min_pos = defaultdict(int)
buy_vol = defaultdict(int)
sell_vol = defaultdict(int)
pnl_over_time = defaultdict(list)

for t in trades:
    prod = t.get("symbol")
    qty = t.get("quantity", 0)
    if t.get("buyer") == "SUBMISSION":
        prod_pos[prod] += qty
        buy_vol[prod] += qty
    elif t.get("seller") == "SUBMISSION":
        prod_pos[prod] -= qty
        sell_vol[prod] += qty
    max_pos[prod] = max(max_pos[prod], prod_pos[prod])
    min_pos[prod] = min(min_pos[prod], prod_pos[prod])

for row in reader:
    if len(row) < pnl_idx + 1:
        continue
    prod = row[prod_idx]
    ts = int(row[ts_idx])
    try:
        pnl = float(row[pnl_idx]) if row[pnl_idx] else 0.0
    except ValueError:
        pnl = 0.0
    pnl_over_time[prod].append((ts, pnl))

print("=== Position Analysis ===")
for p in pnl_over_time.keys():
    print(f"\n{p}: Max Pos {max_pos[p]}, Min Pos {min_pos[p]}")
    print(f"  Total Buys: {buy_vol[p]}, Total Sells: {sell_vol[p]}")
    pnl_series = pnl_over_time[p]
    if pnl_series:
        final_pnl = pnl_series[-1][1]
        print(f"  Final PnL: {final_pnl}")
        
        max_pnl = 0
        max_drawdown = 0
        for ts, val in pnl_series:
            max_pnl = max(max_pnl, val)
            dd = max_pnl - val
            max_drawdown = max(max_drawdown, dd)
        print(f"  Max Drawdown: {max_drawdown}")
