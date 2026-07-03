"""
Trace initial PnL drop by parsing activitiesLog from the official submission log.
Output: per-timestamp PnL + position for both products in the first 5000 timestamps.
"""
import json
import io
import csv

LOG_FILE = "logs/115554.log"

with open(LOG_FILE, 'r') as f:
    raw_json = json.load(f)

activities_csv = raw_json["activitiesLog"]
reader = csv.DictReader(io.StringIO(activities_csv), delimiter=';')

rows = list(reader)
print(f"Total rows: {len(rows)}")
print(f"Columns: {reader.fieldnames}")
print()

# Filter first N timestamps for each product
PRODUCTS = ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]
CUTOFF_TS = 5000

print(f"{'day':>3} {'ts':>6} {'product':>25} {'bid1':>7} {'ask1':>7} {'mid':>9} {'pnl':>10}")
print("-" * 80)

min_pnl = {}  # track per-product minimum PnL

for row in rows:
    ts = int(row['timestamp'])
    product = row['product']
    day = row['day']
    pnl = float(row['profit_and_loss']) if row['profit_and_loss'] else 0.0
    
    if product not in min_pnl:
        min_pnl[product] = 0.0
    min_pnl[product] = min(min_pnl[product], pnl)
    
    if ts <= CUTOFF_TS:
        bid1 = row.get('bid_price_1', '')
        ask1 = row.get('ask_price_1', '')
        mid = row.get('mid_price', '')
        print(f"{day:>3} {ts:>6} {product:>25} {bid1:>7} {ask1:>7} {mid:>9} {pnl:>10.2f}")

print()
print("=== Global minimum PnL per product ===")
for p, v in min_pnl.items():
    print(f"  {p}: {v:.2f}")

print()
# Find at which timestamp each product hits its minimum
print("=== Timestamps of minimum PnL ===")
running_pnl = {}
for row in rows:
    ts = int(row['timestamp'])
    product = row['product']
    pnl = float(row['profit_and_loss']) if row['profit_and_loss'] else 0.0
    if product not in running_pnl:
        running_pnl[product] = {'min': 0, 'min_ts': 0}
    if pnl < running_pnl[product]['min']:
        running_pnl[product]['min'] = pnl
        running_pnl[product]['min_ts'] = ts

for p, v in running_pnl.items():
    print(f"  {p}: min={v['min']:.2f} at ts={v['min_ts']}")
