"""
Manual Trading – Detailed Clearing Price Walkthrough
=====================================================
Step-by-step audit of how the clearing price is determined at each level.
"""

print("=" * 70)
print("  🌾 DRYLAND FLAX – STEP BY STEP CLEARING ANALYSIS")
print("=" * 70)
print()
print("  Buyback: 30/unit, no fees")
print()

# Existing book
flax_bids = {30: 30000, 29: 5000, 28: 12000, 27: 28000}
flax_asks = {28: 40000, 31: 20000, 32: 20000, 33: 30000}

print("  WITHOUT our order:")
print(f"  {'Price':>6} │ {'Cum Bid ≥P':>12} │ {'Cum Ask ≤P':>12} │ {'Traded Vol':>12}")
print(f"  {'─'*6}─┼─{'─'*12}─┼─{'─'*12}─┼─{'─'*12}")
for P in sorted(set(list(flax_bids.keys()) + list(flax_asks.keys()))):
    cum_bid = sum(v for p, v in flax_bids.items() if p >= P)
    cum_ask = sum(v for p, v in flax_asks.items() if p <= P)
    traded = min(cum_bid, cum_ask)
    marker = " ◄" if traded == max(min(sum(v for p, v in flax_bids.items() if p >= pp), sum(v for p, v in flax_asks.items() if p <= pp)) for pp in set(list(flax_bids.keys()) + list(flax_asks.keys()))) else ""
    print(f"  {P:>6} │ {cum_bid:>12,} │ {cum_ask:>12,} │ {traded:>12,}{marker}")

print()
print("  Key insight: At P=28, bids≥28 = 47k, asks≤28 = 40k → traded = 40k")
print("  At P=29, bids≥29 = 35k, asks≤29 = 40k → traded = 35k")  
print("  At P=30, bids≥30 = 30k, asks≤30 = 40k → traded = 30k")
print("  → Current clearing = 28 (max volume = 40k)")
print()

# Now: what if WE bid at 29?
print("  WITH our BID at 29 (various quantities):")
print()
for our_qty in [5000, 10000, 20000, 40000, 50000, 60000, 100000]:
    bids_with_us = dict(flax_bids)
    bids_with_us[29] = bids_with_us.get(29, 0) + our_qty
    
    best_vol = -1
    best_price = -1
    table = []
    for P in sorted(set(list(bids_with_us.keys()) + list(flax_asks.keys()))):
        cum_bid = sum(v for p, v in bids_with_us.items() if p >= P)
        cum_ask = sum(v for p, v in flax_asks.items() if p <= P)
        traded = min(cum_bid, cum_ask)
        table.append((P, cum_bid, cum_ask, traded))
        if traded > best_vol or (traded == best_vol and P > best_price):
            best_vol = traded
            best_price = P
    
    # Our fill at clearing
    clearing = best_price
    if 29 < clearing:
        our_fill = 0
    else:
        total_supply = sum(v for p, v in flax_asks.items() if p <= clearing)
        # Bids above clearing (filled first)
        filled_above = sum(v for p, v in flax_bids.items() if p > clearing)
        # Bids AT clearing: others have time priority
        others_at = flax_bids.get(clearing, 0)
        remaining = total_supply - filled_above - others_at
        our_fill = max(0, min(our_qty, remaining))
    
    profit = (30 - clearing) * our_fill
    print(f"  Us: BID {29} x {our_qty:>7,} → Clear={clearing}, TotalVol={best_vol:,}, OurFill={our_fill:,}, Profit=${profit:,}")

print()
print("  WITH our BID at 30 (various quantities):")
print()
for our_qty in [5000, 10000, 20000, 40000, 50000, 60000, 100000]:
    bids_with_us = dict(flax_bids)
    bids_with_us[30] = bids_with_us.get(30, 0) + our_qty
    
    best_vol = -1
    best_price = -1
    for P in sorted(set(list(bids_with_us.keys()) + list(flax_asks.keys()))):
        cum_bid = sum(v for p, v in bids_with_us.items() if p >= P)
        cum_ask = sum(v for p, v in flax_asks.items() if p <= P)
        traded = min(cum_bid, cum_ask)
        if traded > best_vol or (traded == best_vol and P > best_price):
            best_vol = traded
            best_price = P
    
    clearing = best_price
    if 30 < clearing:
        our_fill = 0
    else:
        total_supply = sum(v for p, v in flax_asks.items() if p <= clearing)
        filled_above = sum(v for p, v in flax_bids.items() if p > clearing)
        others_at = flax_bids.get(clearing, 0)
        remaining = total_supply - filled_above - others_at
        our_fill = max(0, min(our_qty, remaining))
    
    profit = (30 - clearing) * our_fill
    print(f"  Us: BID {30} x {our_qty:>7,} → Clear={clearing}, TotalVol={best_vol:,}, OurFill={our_fill:,}, Profit=${profit:,}")

# FULL Flax sweep
print()
print("  ═══ FULL FLAX SWEEP ═══")
print(f"  {'Price':>5} {'Qty':>8} {'Clear':>5} {'Fill':>8} {'Profit':>10}")
best_fp = -1
best_fc = None
for bid_p in range(26, 34):
    for qty in [1000, 5000, 10000, 20000, 30000, 40000, 50000, 80000, 100000]:
        bids_with_us = dict(flax_bids)
        bids_with_us[bid_p] = bids_with_us.get(bid_p, 0) + qty
        
        best_vol = -1
        best_price = -1
        for P in sorted(set(list(bids_with_us.keys()) + list(flax_asks.keys()))):
            cum_bid = sum(v for p, v in bids_with_us.items() if p >= P)
            cum_ask = sum(v for p, v in flax_asks.items() if p <= P)
            traded = min(cum_bid, cum_ask)
            if traded > best_vol or (traded == best_vol and P > best_price):
                best_vol = traded
                best_price = P
        
        clearing = best_price
        if bid_p < clearing:
            our_fill = 0
        else:
            total_supply = sum(v for p, v in flax_asks.items() if p <= clearing)
            filled_above = sum(v for p, v in flax_bids.items() if p > clearing)
            others_at = flax_bids.get(clearing, 0)
            remaining = total_supply - filled_above - others_at
            our_fill = max(0, min(qty, remaining))
        
        profit = (30 - clearing) * our_fill
        if profit > best_fp:
            best_fp = profit
            best_fc = (bid_p, qty, clearing, our_fill, profit)

print(f"\n  🏆 BEST FLAX: Bid {best_fc[0]} x {best_fc[1]:,} → Clear={best_fc[2]}, Fill={best_fc[3]:,}, Profit=${best_fc[4]:,}")


# ── MUSHROOM detailed ────────────────────────────────────────────────
print(f"\n{'='*70}")
print("  🍄 EMBER MUSHROOM – STEP BY STEP")
print("=" * 70)
print()

mush_bids = {20: 43000, 19: 17000, 18: 6000, 17: 5000, 16: 10000, 15: 5000, 14: 10000, 13: 7000}
mush_asks = {12: 20000, 13: 25000, 14: 35000, 15: 6000, 16: 5000, 17: 0, 18: 10000, 19: 12000}

print("  WITHOUT our order:")
print(f"  {'Price':>6} │ {'Cum Bid ≥P':>12} │ {'Cum Ask ≤P':>12} │ {'Traded Vol':>12}")
print(f"  {'─'*6}─┼─{'─'*12}─┼─{'─'*12}─┼─{'─'*12}")
for P in sorted(set(list(mush_bids.keys()) + list(mush_asks.keys()))):
    cum_bid = sum(v for p, v in mush_bids.items() if p >= P)
    cum_ask = sum(v for p, v in mush_asks.items() if p <= P)
    traded = min(cum_bid, cum_ask)
    print(f"  {P:>6} │ {cum_bid:>12,} │ {cum_ask:>12,} │ {traded:>12,}")

print()

# Full mushroom sweep
print("  ═══ FULL MUSHROOM SWEEP ═══")
best_mp = -1
best_mc = None
FEE = 0.10
for bid_p in range(10, 25):
    for qty in [5000, 10000, 20000, 30000, 40000, 50000, 60000, 80000, 100000, 150000, 200000]:
        bids_with_us = dict(mush_bids)
        bids_with_us[bid_p] = bids_with_us.get(bid_p, 0) + qty
        
        best_vol = -1
        best_price = -1
        for P in sorted(set(list(bids_with_us.keys()) + list(mush_asks.keys()))):
            cum_bid = sum(v for p, v in bids_with_us.items() if p >= P)
            cum_ask = sum(v for p, v in mush_asks.items() if p <= P)
            traded = min(cum_bid, cum_ask)
            if traded > best_vol or (traded == best_vol and P > best_price):
                best_vol = traded
                best_price = P
        
        clearing = best_price
        if bid_p < clearing:
            our_fill = 0
        else:
            total_supply = sum(v for p, v in mush_asks.items() if p <= clearing)
            filled_above = sum(v for p, v in mush_bids.items() if p > clearing)
            others_at = mush_bids.get(clearing, 0)
            remaining = total_supply - filled_above - others_at
            our_fill = max(0, min(qty, remaining))
        
        profit = (20 - FEE - clearing) * our_fill
        if profit > best_mp:
            best_mp = profit
            best_mc = (bid_p, qty, clearing, our_fill, profit)

print(f"\n  🏆 BEST MUSHROOM: Bid {best_mc[0]} x {best_mc[1]:,} → Clear={best_mc[2]}, Fill={best_mc[3]:,}, Profit=${best_mc[4]:,.0f}")

# ── FINAL ─────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("  💰 FINAL RECOMMENDED ORDERS")
print("=" * 70)
print(f"  🌾 Flax:      BID price={best_fc[0]}, qty={best_fc[1]:,}")
print(f"                Expected clearing={best_fc[2]}, fill={best_fc[3]:,}, profit=${best_fc[4]:,}")
print(f"  🍄 Mushroom:  BID price={best_mc[0]}, qty={best_mc[1]:,}")
print(f"                Expected clearing={best_mc[2]}, fill={best_mc[3]:,}, profit=${best_mc[4]:,.0f}")
print(f"  ─────────────────────────────────────────")
print(f"  💰 TOTAL EXPECTED PROFIT: ${best_fc[4] + best_mc[4]:,.0f}")
print("=" * 70)
