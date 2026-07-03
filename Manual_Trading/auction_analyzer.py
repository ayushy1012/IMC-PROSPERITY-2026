"""
Manual Trading Auction Analyzer
================================
For each product, simulate every possible clearing price to find:
1. What clearing price the exchange will pick (max volume, then highest price)
2. How many units YOU get at each possible bid/ask price
3. Your profit = (buyback_price - clearing_price) * units_acquired - fees
"""

# ── DRYLAND FLAX ──────────────────────────────────────────────────────
# Buyback: 30/unit, no fees
# Strategy: We want to BUY flax at the auction and sell to guild at 30
#           So we submit a BID (buy order)

print("=" * 70)
print("  🌾 DRYLAND FLAX ANALYSIS")
print("=" * 70)
print("  Buyback price: 30/unit, no fees")
print("  Our strategy: BID (buy) at auction → sell to guild at 30")
print()

# Existing order book
flax_bids = [(30, 30000), (29, 5000), (28, 12000), (27, 28000)]  # Others wanting to BUY
flax_asks = [(28, 40000), (31, 20000), (32, 20000), (33, 30000)]  # Others wanting to SELL

print("  Existing Bids (buyers):  ", flax_bids)
print("  Existing Asks (sellers): ", flax_asks)
print()

# The auction finds a clearing price that maximizes volume
# At clearing price P:
#   - All bids >= P get filled (buyers willing to pay P or more)
#   - All asks <= P get filled (sellers willing to sell at P or less)
#   - Volume = min(total_bid_volume_at_or_above_P, total_ask_volume_at_or_below_P)

def compute_clearing(bids, asks, our_side, our_price, our_qty, product_name):
    """
    Simulate the auction with our order added.
    our_side: 'bid' or 'ask'
    Returns (clearing_price, our_fill_qty, total_volume)
    """
    # Add our order
    if our_side == 'bid':
        all_bids = bids + [(our_price, our_qty)]
        all_asks = asks[:]
    else:
        all_bids = bids[:]
        all_asks = asks + [(our_price, our_qty)]
    
    # Collect all unique prices
    all_prices = sorted(set(p for p, v in all_bids + all_asks))
    
    best_vol = -1
    best_price = -1
    
    for P in all_prices:
        # Total bid volume at or above P
        bid_vol = sum(v for p, v in all_bids if p >= P)
        # Total ask volume at or below P
        ask_vol = sum(v for p, v in all_asks if p <= P)
        # Traded volume
        traded = min(bid_vol, ask_vol)
        
        if traded > best_vol or (traded == best_vol and P > best_price):
            best_vol = traded
            best_price = P
    
    # Now compute our fill at the clearing price
    # Allocation: price priority first, then time priority (we are LAST)
    clearing = best_price
    
    if our_side == 'bid':
        if our_price < clearing:
            our_fill = 0  # Our bid is below clearing, we don't participate
        else:
            # Total ask volume at or below clearing
            total_supply = sum(v for p, v in all_asks if p <= clearing)
            # Total bid volume above clearing (filled before us)
            senior_demand = sum(v for p, v in bids if p > clearing)
            # Bids AT clearing price (same price tier)
            same_tier_others = sum(v for p, v in bids if p == clearing)
            # We are last in time at our price tier
            if our_price > clearing:
                # We are in a higher price tier, filled before same-tier
                remaining = total_supply - senior_demand
                # But there might be others above clearing too
                # Actually, let's redo: all bids >= clearing get filled
                # Price priority: higher bids fill first
                remaining_supply = total_supply
                our_fill = 0
                # Sort all bids by price desc, we are last at our price
                bid_queue = []
                for p, v in bids:
                    if p >= clearing:
                        bid_queue.append((p, v, 'other'))
                if our_price >= clearing:
                    bid_queue.append((our_price, our_qty, 'us'))
                # Sort: higher price first, for same price, others before us
                bid_queue.sort(key=lambda x: (-x[0], 0 if x[2] == 'other' else 1))
                
                for price, vol, who in bid_queue:
                    fill = min(vol, remaining_supply)
                    if who == 'us':
                        our_fill = fill
                    remaining_supply -= fill
                    if remaining_supply <= 0:
                        break
            else:
                # Our price equals clearing
                remaining_supply = total_supply
                bid_queue = []
                for p, v in bids:
                    if p >= clearing:
                        bid_queue.append((p, v, 'other'))
                bid_queue.append((our_price, our_qty, 'us'))
                bid_queue.sort(key=lambda x: (-x[0], 0 if x[2] == 'other' else 1))
                
                our_fill = 0
                for price, vol, who in bid_queue:
                    fill = min(vol, remaining_supply)
                    if who == 'us':
                        our_fill = fill
                    remaining_supply -= fill
                    if remaining_supply <= 0:
                        break
    else:  # our_side == 'ask'
        if our_price > clearing:
            our_fill = 0
        else:
            total_demand = sum(v for p, v in all_bids if p >= clearing)
            ask_queue = []
            for p, v in asks:
                if p <= clearing:
                    ask_queue.append((p, v, 'other'))
            if our_price <= clearing:
                ask_queue.append((our_price, our_qty, 'us'))
            # Lower ask price = higher priority
            ask_queue.sort(key=lambda x: (x[0], 0 if x[2] == 'other' else 1))
            
            remaining_demand = total_demand
            our_fill = 0
            for price, vol, who in ask_queue:
                fill = min(vol, remaining_demand)
                if who == 'us':
                    our_fill = fill
                remaining_demand -= fill
                if remaining_demand <= 0:
                    break
    
    return clearing, our_fill, best_vol


# ── Flax: Try every possible bid price ───────────────────────────────
print("  === Trying every BID price (we buy, then sell to guild at 30) ===")
print(f"  {'Bid':>5} {'Qty':>8} {'Clear':>7} {'Fill':>8} {'Profit':>10}")
print(f"  {'─'*5} {'─'*8} {'─'*7} {'─'*8} {'─'*10}")

best_flax_profit = -float('inf')
best_flax_config = None

for bid_price in range(25, 35):
    for qty in [10000, 20000, 30000, 40000, 50000, 60000, 80000, 100000]:
        clearing, fill, total_vol = compute_clearing(
            flax_bids, flax_asks, 'bid', bid_price, qty, 'FLAX'
        )
        profit = (30 - clearing) * fill  # Buy at clearing, sell at 30
        if profit > best_flax_profit:
            best_flax_profit = profit
            best_flax_config = (bid_price, qty, clearing, fill, profit)

    # Print best qty for this price
    clearing, fill, total_vol = compute_clearing(
        flax_bids, flax_asks, 'bid', bid_price, best_flax_config[1] if best_flax_config else 50000, 'FLAX'
    )
    profit = (30 - clearing) * fill
    print(f"  {bid_price:>5} {best_flax_config[1] if best_flax_config else 0:>8,} {clearing:>7} {fill:>8,} {profit:>10,}")

print(f"\n  🏆 BEST FLAX: Bid {best_flax_config[0]} x {best_flax_config[1]:,} → "
      f"Clearing: {best_flax_config[2]}, Fill: {best_flax_config[3]:,}, "
      f"Profit: ${best_flax_config[4]:,}")


# ── EMBER MUSHROOM ────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("  🍄 EMBER MUSHROOM ANALYSIS")
print("=" * 70)
print("  Buyback price: 20/unit, fee: 0.10/unit")
print("  Our strategy: BID (buy) at auction → sell to guild at 20 - 0.10")
print()

mush_bids = [(20, 43000), (19, 17000), (18, 6000), (17, 5000),
             (16, 10000), (15, 5000), (14, 10000), (13, 7000)]
mush_asks = [(12, 20000), (13, 25000), (14, 35000), (15, 6000),
             (16, 5000), (17, 0), (18, 10000), (19, 12000)]

print("  Existing Bids: ", mush_bids)
print("  Existing Asks: ", mush_asks)
print()

print("  === Trying every BID price (we buy, then sell to guild at 20-0.10) ===")
print(f"  {'Bid':>5} {'Qty':>8} {'Clear':>7} {'Fill':>8} {'Profit':>10}")
print(f"  {'─'*5} {'─'*8} {'─'*7} {'─'*8} {'─'*10}")

best_mush_profit = -float('inf')
best_mush_config = None
MUSH_FEE = 0.10

for bid_price in range(10, 25):
    for qty in [10000, 20000, 30000, 40000, 50000, 60000, 80000, 100000, 150000]:
        clearing, fill, total_vol = compute_clearing(
            mush_bids, mush_asks, 'bid', bid_price, qty, 'MUSHROOM'
        )
        profit = (20 - MUSH_FEE - clearing) * fill
        if profit > best_mush_profit:
            best_mush_profit = profit
            best_mush_config = (bid_price, qty, clearing, fill, profit)
    
    # Print using the overall best qty
    clearing, fill, total_vol = compute_clearing(
        mush_bids, mush_asks, 'bid', bid_price, best_mush_config[1] if best_mush_config else 50000, 'MUSHROOM'
    )
    profit = (20 - MUSH_FEE - clearing) * fill
    print(f"  {bid_price:>5} {best_mush_config[1] if best_mush_config else 0:>8,} {clearing:>7} {fill:>8,} {profit:>10,}")

print(f"\n  🏆 BEST MUSHROOM: Bid {best_mush_config[0]} x {best_mush_config[1]:,} → "
      f"Clearing: {best_mush_config[2]}, Fill: {best_mush_config[3]:,}, "
      f"Profit: ${best_mush_config[4]:,.0f}")


# ── COMBINED ──────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("  💰 COMBINED OPTIMAL STRATEGY")
print("=" * 70)
print(f"  Flax:     Bid {best_flax_config[0]} x {best_flax_config[1]:,}  →  Profit: ${best_flax_config[4]:,}")
print(f"  Mushroom: Bid {best_mush_config[0]} x {best_mush_config[1]:,}  →  Profit: ${best_mush_config[4]:,.0f}")
print(f"  TOTAL:    ${best_flax_config[4] + best_mush_config[4]:,.0f}")
print("=" * 70)
