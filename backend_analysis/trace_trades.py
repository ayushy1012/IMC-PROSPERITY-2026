"""
Trace trades from the official log.
"""
import json
import io
import csv

LOG_FILE = "logs/115554.log"

with open(LOG_FILE, 'r') as f:
    raw = f.read()

# In 115554.log, there's multiple lines. Let's find marketTrades or parse the whole thing.
# The user's log usually has lines of JSON dicts or a single big dict.
with open(LOG_FILE, 'r') as f:
    try:
        data = json.load(f)
        if isinstance(data, list):
            rows = data
        elif "tradeHistory" in data:
            rows = data["tradeHistory"]
        else:
            print("Unknown JSON format keys:", data.keys())
            rows = []
    except Exception as e:
        # If it's single JSON per line
        # I actually just printed the head earlier. It looks like:
        # {"timestamp":51300,"buyer":"SUBMISSION","seller":"","symbol":"ASH_COATED_OSMIUM","currency":"XIRECS","price":9990.0,"quantity":9}
        f.seek(0)
        rows = []
        for line in f:
            line = line.strip()
            if not line: continue
            if "sandbox logs" in line: break # stop at the end
            try:
                rows.append(json.loads(line))
            except:
                pass


print(f"Total trades parsed: {len(rows)}")
pos = 0
for row in rows[:500]:
    if row.get('symbol') == 'INTARIAN_PEPPER_ROOT':
        ts = row['timestamp']
        if ts > 1500: break
        
        # See if SUBMISSION is buyer or seller
        buyer = row.get('buyer', '')
        seller = row.get('seller', '')
        qty = row.get('quantity', 0)
        price = row.get('price', 0)
        
        if buyer == 'SUBMISSION':
            pos += qty
            print(f"ts={ts} BUY  {qty} @ {price} | pos={pos}")
        elif seller == 'SUBMISSION':
            pos -= qty
            print(f"ts={ts} SELL {qty} @ {price} | pos={pos}")
