"""
Custom backtester for Round 3 Prosperity 4.
Simulates our round3_trader.py against historical order book data.

Matching engine: simple aggressive-only matching.
- If our buy order price >= best ask, we get filled at ask price.
- If our sell order price <= best bid, we get filled at bid price.
- Passive orders NOT filled (conservative estimate).
"""
import csv
import sys
import os
import math
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Trader'))

from datamodel import Order, OrderDepth, TradingState, Listing, Observation
from round3_trader import Trader

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'ROUND_3')

POSITION_LIMITS = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    "VEV_4000": 300, "VEV_4500": 300,
    "VEV_5000": 300, "VEV_5100": 300,
    "VEV_5200": 300, "VEV_5300": 300,
    "VEV_5400": 300, "VEV_5500": 300,
    "VEV_6000": 300, "VEV_6500": 300,
}

def load_ticks(day):
    """Load price ticks grouped by timestamp."""
    path = os.path.join(DATA_DIR, f"prices_round_3_day_{day}.csv")
    ticks = defaultdict(dict)
    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            ts = int(row["timestamp"])
            prod = row["product"]
            ticks[ts][prod] = row
    return dict(sorted(ticks.items()))


def build_order_depth(row):
    """Build an OrderDepth from a CSV row."""
    od = OrderDepth()
    for i in range(1, 4):
        bp = row.get(f"bid_price_{i}", "")
        bv = row.get(f"bid_volume_{i}", "")
        ap = row.get(f"ask_price_{i}", "")
        av = row.get(f"ask_volume_{i}", "")
        if bp and bv:
            try:
                od.buy_orders[int(float(bp))] = int(bv)
            except:
                pass
        if ap and av:
            try:
                od.sell_orders[int(float(ap))] = -abs(int(av))
            except:
                pass
    return od


def match_orders(orders, depth, position, limit):
    """
    Match orders against the book. Conservative: only match aggressive orders.
    Returns (fills, new_position) where fills = [(price, qty), ...].
    """
    fills = []
    pos = position
    
    if not depth.sell_orders or not depth.buy_orders:
        return fills, pos
    
    best_ask = min(depth.sell_orders.keys())
    best_bid = max(depth.buy_orders.keys())
    
    for order in orders:
        if order.quantity > 0:  # Buy order
            if order.price >= best_ask:
                # Aggressive buy — fill at best ask
                max_buy = min(order.quantity, limit - pos)
                if max_buy > 0:
                    available = abs(depth.sell_orders.get(best_ask, 0))
                    fill_qty = min(max_buy, available)
                    if fill_qty > 0:
                        fills.append((best_ask, fill_qty))
                        pos += fill_qty
        elif order.quantity < 0:  # Sell order
            if order.price <= best_bid:
                # Aggressive sell — fill at best bid
                max_sell = min(abs(order.quantity), limit + pos)
                if max_sell > 0:
                    available = depth.buy_orders.get(best_bid, 0)
                    fill_qty = min(max_sell, available)
                    if fill_qty > 0:
                        fills.append((best_bid, -fill_qty))
                        pos -= fill_qty
    
    return fills, pos


def run_backtest(day, trader, trader_data, positions, print_trades=False):
    """Run one day of backtesting. Returns (pnl_by_product, trader_data, positions)."""
    ticks = load_ticks(day)
    
    pnl = defaultdict(float)
    total_fills = defaultdict(int)
    
    listings = {}
    for prod in POSITION_LIMITS:
        listings[prod] = Listing(prod, prod, 1)
    
    obs = Observation({}, {})
    
    for ts, products in ticks.items():
        order_depths = {}
        for prod, row in products.items():
            order_depths[prod] = build_order_depth(row)
        
        state = TradingState(
            traderData=trader_data,
            timestamp=ts,
            listings=listings,
            order_depths=order_depths,
            own_trades={},
            market_trades={},
            position=dict(positions),
            observations=obs,
        )
        
        result, conversions, trader_data = trader.run(state)
        
        # Match orders
        for prod, orders in result.items():
            if not orders or prod not in order_depths:
                continue
            
            limit = POSITION_LIMITS.get(prod, 0)
            fills, new_pos = match_orders(
                orders, order_depths[prod], positions.get(prod, 0), limit
            )
            
            for fill_price, fill_qty in fills:
                # PnL: buying costs money (negative), selling earns money (positive)
                pnl[prod] -= fill_price * fill_qty  # fill_qty negative for sells
                total_fills[prod] += abs(fill_qty)
                if print_trades:
                    side = "BUY" if fill_qty > 0 else "SELL"
                    print(f"  ts={ts} {prod}: {side} {abs(fill_qty)} @ {fill_price}")
            
            positions[prod] = new_pos
    
    # Mark-to-market: value remaining positions at last mid price
    last_ts = max(ticks.keys())
    for prod, pos in positions.items():
        if pos != 0 and prod in ticks[last_ts]:
            row = ticks[last_ts][prod]
            bp1 = row.get("bid_price_1", "")
            ap1 = row.get("ask_price_1", "")
            if bp1 and ap1:
                mid = 0.5 * (float(bp1) + float(ap1))
                pnl[prod] += pos * mid
    
    return pnl, trader_data, positions, total_fills


def main():
    print("=" * 80)
    print("ROUND 3 CUSTOM BACKTESTER")
    print("=" * 80)
    
    trader = Trader()
    trader_data = ""
    
    for day in range(3):
        positions = defaultdict(int)
        pnl, trader_data_day, positions_day, fills = run_backtest(
            day, trader, "", positions
        )
        
        print(f"\n{'─' * 60}")
        print(f"DAY {day} RESULTS (aggressive-only matching)")
        print(f"{'─' * 60}")
        
        day_total = 0
        for prod in sorted(pnl.keys()):
            if pnl[prod] != 0 or fills.get(prod, 0) > 0:
                print(f"  {prod:<25} PnL: {pnl[prod]:>10.1f}  fills: {fills.get(prod, 0):>5}")
                day_total += pnl[prod]
        
        print(f"  {'TOTAL':<25} PnL: {day_total:>10.1f}")
    
    # Also run all 3 days with carry-over state
    print(f"\n{'=' * 60}")
    print(f"3-DAY CONTINUOUS RUN (state carries over)")
    print(f"{'=' * 60}")
    
    trader2 = Trader()
    td2 = ""
    total_pnl = defaultdict(float)
    total_fills2 = defaultdict(int)
    
    for day in range(3):
        positions2 = defaultdict(int)
        pnl2, td2, positions2, fills2 = run_backtest(day, trader2, td2, positions2)
        for p, v in pnl2.items():
            total_pnl[p] += v
        for p, v in fills2.items():
            total_fills2[p] += v
    
    grand_total = 0
    for prod in sorted(total_pnl.keys()):
        if total_pnl[prod] != 0:
            print(f"  {prod:<25} PnL: {total_pnl[prod]:>10.1f}  fills: {total_fills2.get(prod, 0):>5}")
            grand_total += total_pnl[prod]
    
    print(f"  {'GRAND TOTAL':<25} PnL: {grand_total:>10.1f}")
    print()


if __name__ == "__main__":
    main()
