"""
Manual Trading Auction – EXHAUSTIVE Brute Force (FIXED)
========================================================
Tests EVERY SINGLE (price, quantity) combination.
Fixed fill allocation logic for bids above clearing price.

Usage:
    cd /Users/dmitt/Desktop/Prosperity
    .venv/bin/python3 Manual_Trading/bruteforce_exhaustive.py
"""

import time

# ══════════════════════════════════════════════════════════════════════
#  ORDER BOOKS — Update these if the website order book changes
# ══════════════════════════════════════════════════════════════════════

FLAX_BIDS = [(30, 30000), (29, 5000), (28, 12000), (27, 28000)]
FLAX_ASKS = [(28, 40000), (31, 20000), (32, 20000), (33, 30000)]
FLAX_BUYBACK = 30
FLAX_FEE = 0.0

MUSH_BIDS = [(20, 43000), (19, 17000), (18, 6000), (17, 5000),
             (16, 10000), (15, 5000), (14, 10000), (13, 7000)]
MUSH_ASKS = [(12, 20000), (13, 25000), (14, 35000), (15, 6000),
             (16, 5000), (17, 0), (18, 10000), (19, 12000)]
MUSH_BUYBACK = 20
MUSH_FEE = 0.10

PRICE_MIN = 1
PRICE_MAX = 50
QTY_MAX = 200000


# ══════════════════════════════════════════════════════════════════════
#  AUCTION ENGINE (correct fill logic)
# ══════════════════════════════════════════════════════════════════════

def precompute(bids, asks):
    """Pre-compute sorted bid list and cumulative ask volumes."""
    # Sort existing bids descending by price for fill queue
    sorted_bids = sorted(bids, key=lambda x: -x[0])
    # Pre-compute cumulative ask volumes for each price
    all_prices = sorted(set(p for p, _ in bids + asks) | set(range(PRICE_MIN, PRICE_MAX + 1)))
    cum_asks = {}
    for P in all_prices:
        cum_asks[P] = sum(v for p, v in asks if p <= P)
    # Pre-compute cumulative bid volumes WITHOUT our order
    cum_bids_base = {}
    for P in all_prices:
        cum_bids_base[P] = sum(v for p, v in bids if p >= P)
    return sorted_bids, all_prices, cum_bids_base, cum_asks


def simulate(sorted_bids, all_prices, cum_bids_base, cum_asks,
             our_price, our_qty, buyback, fee):
    """
    Simulate placing a BID at (our_price, our_qty).
    Returns (profit, clearing, fill).
    """
    # ── Step 1: Find clearing price ──
    best_vol = -1
    best_price = -1
    for P in all_prices:
        cb = cum_bids_base[P] + (our_qty if our_price >= P else 0)
        ca = cum_asks.get(P, 0)
        traded = min(cb, ca)
        if traded > best_vol or (traded == best_vol and P > best_price):
            best_vol = traded
            best_price = P
    clearing = best_price

    # ── Step 2: Compute our fill ──
    if our_price < clearing:
        return 0.0, clearing, 0

    supply = cum_asks.get(clearing, 0)
    if supply <= 0:
        return 0.0, clearing, 0

    # Walk the fill queue: all bids >= clearing, price-descending.
    # At each price level, existing orders fill before us (time priority).
    remaining = supply
    our_fill = 0

    # Collect all price levels with bids at or above clearing
    # For each level, we know the existing volume and whether we're at that level
    # Process highest price first
    price_levels = set(p for p, _ in sorted_bids if p >= clearing)
    if our_price >= clearing:
        price_levels.add(our_price)
    price_levels = sorted(price_levels, reverse=True)

    for pl in price_levels:
        if remaining <= 0:
            break
        # Fill existing bids at this level
        existing_vol = sum(v for p, v in sorted_bids if p == pl)
        filled = min(existing_vol, remaining)
        remaining -= filled
        # Fill our order at this level (we are LAST at our price)
        if pl == our_price and remaining > 0:
            our_fill = min(our_qty, remaining)
            remaining -= our_fill

    profit = (buyback - fee - clearing) * our_fill
    return profit, clearing, our_fill


# ══════════════════════════════════════════════════════════════════════
#  EXHAUSTIVE SEARCH
# ══════════════════════════════════════════════════════════════════════

def exhaustive_search(name, existing_bids, existing_asks, buyback, fee):
    sorted_bids, all_prices, cum_bids_base, cum_asks = precompute(
        existing_bids, existing_asks
    )

    best_profit = -float('inf')
    best_config = None
    total = PRICE_MAX * QTY_MAX
    checked = 0
    start = time.time()

    # Also track ALL unique (clearing, fill, profit) combos to show top results
    top_results = {}  # (price, clearing, fill, profit) -> min qty

    print(f"  Searching {PRICE_MAX} prices × {QTY_MAX:,} quantities = {total:,} combos...")

    for price in range(PRICE_MIN, PRICE_MAX + 1):
        for qty in range(1, QTY_MAX + 1):
            profit, clearing, fill = simulate(
                sorted_bids, all_prices, cum_bids_base, cum_asks,
                price, qty, buyback, fee
            )
            if profit > best_profit:
                best_profit = profit
                best_config = (price, qty, clearing, fill, profit)

            # Track unique outcomes (keep smallest qty for each)
            key = (price, clearing, fill, profit)
            if key not in top_results or qty < top_results[key]:
                top_results[key] = qty

        checked += QTY_MAX
        elapsed = time.time() - start
        pct = checked / total * 100
        rate = checked / elapsed if elapsed > 0 else 0
        eta = (total - checked) / rate if rate > 0 else 0
        print(f"    Price {price:>3}/{PRICE_MAX} | "
              f"{pct:5.1f}% | "
              f"{rate:,.0f}/s | "
              f"ETA: {eta:.0f}s | "
              f"Best: ${best_profit:,.0f}", end='\r')

    elapsed = time.time() - start
    print(f"\n  ✅ {total:,} combos in {elapsed:.1f}s ({total/elapsed:,.0f}/s)")

    # Print top 25 unique results
    ranked = sorted(top_results.items(), key=lambda x: -x[0][3])[:25]
    print(f"\n  {'Rank':>4} {'Price':>5} {'MinQty':>8} {'Clear':>5} {'Fill':>8} {'Profit':>12}")
    print(f"  {'─'*4} {'─'*5} {'─'*8} {'─'*5} {'─'*8} {'─'*12}")
    for i, ((price, clearing, fill, profit), min_qty) in enumerate(ranked, 1):
        marker = " ◄ BEST" if i == 1 else ""
        print(f"  {i:>4} {price:>5} {min_qty:>8,} {clearing:>5} {fill:>8,} ${profit:>11,.0f}{marker}")

    return best_config


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    total_sims = PRICE_MAX * QTY_MAX * 2
    print("=" * 70)
    print("  EXHAUSTIVE AUCTION BRUTE FORCE (FIXED)")
    print(f"  Solution space: {total_sims:,} total simulations")
    print("=" * 70)

    # ── Verification first ──
    print("\n  ── Quick verification of known-good cases ──")
    sb, ap, cb, ca = precompute(FLAX_BIDS, FLAX_ASKS)
    p, c, f = simulate(sb, ap, cb, ca, 30, 9999, 30, 0.0)
    print(f"  Flax BID 30×9999:  clearing={c}, fill={f:,}, profit=${p:,.0f}")
    p, c, f = simulate(sb, ap, cb, ca, 29, 4999, 30, 0.0)
    print(f"  Flax BID 29×4999:  clearing={c}, fill={f:,}, profit=${p:,.0f}")
    p, c, f = simulate(sb, ap, cb, ca, 29, 5000, 30, 0.0)
    print(f"  Flax BID 29×5000:  clearing={c}, fill={f:,}, profit=${p:,.0f}")

    sb, ap, cb, ca = precompute(MUSH_BIDS, MUSH_ASKS)
    p, c, f = simulate(sb, ap, cb, ca, 19, 40000, 20, 0.10)
    print(f"  Mush BID 19×40000: clearing={c}, fill={f:,}, profit=${p:,.0f}")
    p, c, f = simulate(sb, ap, cb, ca, 18, 35000, 20, 0.10)
    print(f"  Mush BID 18×35000: clearing={c}, fill={f:,}, profit=${p:,.0f}")

    # ── FLAX ──
    print(f"\n  🌾 DRYLAND FLAX (Buyback={FLAX_BUYBACK}, Fee={FLAX_FEE})")
    flax = exhaustive_search("FLAX", FLAX_BIDS, FLAX_ASKS, FLAX_BUYBACK, FLAX_FEE)
    print(f"  🏆 BEST: BID price={flax[0]}, qty={flax[1]:,}")
    print(f"           Clearing={flax[2]}, Fill={flax[3]:,}, Profit=${flax[4]:,.0f}")

    # ── MUSHROOM ──
    print(f"\n  🍄 EMBER MUSHROOM (Buyback={MUSH_BUYBACK}, Fee={MUSH_FEE})")
    mush = exhaustive_search("MUSHROOM", MUSH_BIDS, MUSH_ASKS, MUSH_BUYBACK, MUSH_FEE)
    print(f"  🏆 BEST: BID price={mush[0]}, qty={mush[1]:,}")
    print(f"           Clearing={mush[2]}, Fill={mush[3]:,}, Profit=${mush[4]:,.0f}")

    # ── FINAL ──
    print(f"\n{'='*70}")
    print(f"  💰 OPTIMAL ORDERS (EXHAUSTIVELY VERIFIED)")
    print(f"{'='*70}")
    print(f"  🌾 FLAX:      BID price={flax[0]}, qty={flax[1]:,}")
    print(f"                Clearing={flax[2]}, Fill={flax[3]:,}, Profit=${flax[4]:,.0f}")
    print(f"  🍄 MUSHROOM:  BID price={mush[0]}, qty={mush[1]:,}")
    print(f"                Clearing={mush[2]}, Fill={mush[3]:,}, Profit=${mush[4]:,.0f}")
    print(f"  ──────────────────────────────────────────")
    print(f"  💰 TOTAL PROFIT: ${flax[4] + mush[4]:,.0f}")
    print(f"{'='*70}")
