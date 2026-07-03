import json
import csv
from collections import defaultdict

d = json.load(open("logs/297945.json"))
activities = d["activitiesLog"].strip().split("\n")

reader = csv.reader(activities, delimiter=";")
header = next(reader)

ts_idx = header.index("timestamp")
prod_idx = header.index("product")
pnl_idx = header.index("profit_and_loss")

trades = []
for line in open("logs/297945.log").readlines():
    if "timestamp" in line and "symbol" in line:
        try:
            trade = json.loads(line)
            if "symbol" in trade and "quantity" in trade:
                trades.append(trade)
        except:
            pass

prod_pos = defaultdict(int)
max_pos = defaultdict(int)
min_pos = defaultdict(int)
buy_vol = defaultdict(int)
sell_vol = defaultdict(int)
pnl_over_time = defaultdict(list)

for t in trades:
    prod = t["symbol"]
    qty = t["quantity"]
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
    pnl = float(row[pnl_idx]) if row[pnl_idx] else 0.0
    pnl_over_time[prod].append((ts, pnl))

print("=== Position Analysis ===")
for p in max_pos.keys():
    print(f"{p}: Max Pos {max_pos[p]}, Min Pos {min_pos[p]}")
    print(f"  Buys: {buy_vol[p]}, Sells: {sell_vol[p]}")
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
